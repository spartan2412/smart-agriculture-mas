"""Collect quality-gated pre-decision Sentinel-2 point NDVI time series.

This is an additive enrichment of the frozen 300-scenario benchmark. It
reuses an already hash-verified frozen endpoint observation where available,
then queries only older scenes acquired on or before each decision date and
stores the exact STAC search response used for selection. Candidate selection
uses datetime and STAC scene-quality metadata only; NDVI is calculated *after*
selection and is never used to choose a scene. The values describe a
documented representative cell, not a crop-labelled field, crop stage, stress
diagnosis, or irrigation/fertilizer prescription.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import requests
import rasterio


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_sentinel_ndvi_context import (  # noqa: E402
    CLEAR_SURFACE_SCL,
    MAX_CLOUD_COVER,
    MAX_NODATA_PERCENT,
    REQUEST_HEADERS,
    SAS_TOKEN_URL,
    ndvi,
    pixel_quality,
    sample_asset,
)


STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SOURCE_ID = "SENTINEL2_L2A_PLANETARY_COMPUTER_PREDECISION_TIMESERIES"
MANIFEST_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date", "longitude", "latitude",
    "source_id", "stac_search_url", "query_start_utc", "query_end_utc", "candidate_total", "quality_candidate_total", "existing_observation_total",
    "sample_plan_total", "sample_attempt_total", "raw_path", "response_sha256", "retrieved_at_utc", "source_status", "error",
]
ATTEMPT_FIELDS = [
    "scenario_id", "candidate_plan_rank", "satellite_item_id", "satellite_datetime_utc", "scene_cloud_cover_percent",
    "scene_nodata_percent", "candidate_selection_rule", "sampling_status", "satellite_scl_class", "satellite_scl_label",
    "satellite_pixel_quality_status", "error",
]
OBSERVATION_FIELDS = [
    "scenario_id", "observation_rank_by_time", "satellite_item_id", "satellite_datetime_utc", "scene_cloud_cover_percent",
    "scene_nodata_percent", "satellite_point_scope", "satellite_scl_class", "satellite_scl_label",
    "satellite_pixel_quality_status", "satellite_red_dn", "satellite_nir_dn", "satellite_ndvi", "observation_provenance", "evidence_response_sha256",
]
FEATURE_FIELDS = [
    "scenario_id", "observation_count", "first_observation_utc", "last_observation_utc", "time_span_days",
    "first_ndvi", "last_ndvi", "ndvi_change", "ndvi_linear_slope_per_day", "ndvi_trend_direction", "series_interpretation",
]
STATUS_FIELDS = [
    "scenario_id", "ndvi_timeseries_status", "natural_conflict_evidence_eligibility", "satellite_actionability", "restriction_reason",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def raw_relative_path(scenario_id: str) -> Path:
    if not scenario_id.replace("_", "").isalnum():
        raise ValueError(f"Unsafe scenario ID: {scenario_id!r}")
    return Path("raw") / "sentinel_ndvi_predecision_timeseries" / f"{scenario_id}.json"


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def item_metadata(item: Mapping[str, Any]) -> tuple[str, datetime, float, float]:
    item_id = item.get("id")
    properties = item.get("properties")
    if not isinstance(item_id, str) or not isinstance(properties, dict):
        raise ValueError("Malformed STAC feature.")
    observed = properties.get("datetime")
    if not isinstance(observed, str):
        raise ValueError("STAC feature lacks datetime.")
    try:
        cloud = float(properties["eo:cloud_cover"])
        nodata = float(properties["s2:nodata_pixel_percentage"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("STAC feature lacks numeric cloud/nodata metadata.") from exc
    return item_id, parse_datetime(observed), cloud, nodata


def quality_candidates(features: object, decision_end: datetime) -> List[Dict[str, Any]]:
    if not isinstance(features, list):
        raise ValueError("STAC search response lacks a feature list.")
    selected: List[Dict[str, Any]] = []
    for item in features:
        if not isinstance(item, dict):
            continue
        try:
            _, observed, cloud, nodata = item_metadata(item)
        except ValueError:
            continue
        if observed > decision_end or cloud > MAX_CLOUD_COVER or nodata > MAX_NODATA_PERCENT:
            continue
        if not isinstance(item.get("assets"), dict):
            continue
        selected.append(item)
    return sorted(selected, key=lambda item: (item_metadata(item)[1], item_metadata(item)[2], item_metadata(item)[3], item_metadata(item)[0]))


def evenly_spaced_plan(candidates: Sequence[Dict[str, Any]], maximum: int) -> List[Dict[str, Any]]:
    """Choose temporal coverage without looking at SCL, reflectance, or NDVI."""
    if len(candidates) <= maximum:
        return list(candidates)
    indexes = {round(index * (len(candidates) - 1) / (maximum - 1)) for index in range(maximum)}
    return [candidate for index, candidate in enumerate(candidates) if index in indexes]


def linear_slope(points: Sequence[tuple[datetime, float]]) -> float:
    xs = [(value[0] - points[0][0]).total_seconds() / 86400 for value in points]
    ys = [value[1] for value in points]
    x_bar, y_bar = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - x_bar) ** 2 for x in xs)
    if not denominator:
        return 0.0
    return sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / denominator


def trend_direction(change: float) -> str:
    # A modest 0.05 NDVI change threshold is stated, not inferred as a crop
    # threshold. It merely classifies a numerical time-series direction for
    # later conflict analysis; it has no farm-action meaning.
    if change >= 0.05:
        return "increase_at_least_0_05_ndvi"
    if change <= -0.05:
        return "decrease_at_least_0_05_ndvi"
    return "change_within_plus_or_minus_0_05_ndvi"


def fetch_one(
    scenario: Mapping[str, str], existing: Sequence[Mapping[str, str]], out_dir: Path, token: str,
    lookback_days: int, max_samples: int, timeout_s: float,
) -> tuple[Dict[str, str], List[Dict[str, str]], List[Dict[str, str]], Dict[str, str], Dict[str, str]]:
    scenario_id = scenario["scenario_id"]
    decision = date.fromisoformat(scenario["decision_date"])
    start = decision - timedelta(days=lookback_days)
    end = decision
    start_utc = f"{start.isoformat()}T00:00:00Z"
    end_utc = f"{end.isoformat()}T23:59:59Z"
    raw_relative = raw_relative_path(scenario_id)
    manifest = {
        "scenario_id": scenario_id, "site_id": scenario["site_id"], "crop": scenario["crop"], "state": scenario["state"],
        "district": scenario["district"], "season": scenario["season"], "decision_date": scenario["decision_date"],
        "longitude": scenario["longitude"], "latitude": scenario["latitude"], "source_id": SOURCE_ID,
        "stac_search_url": STAC_SEARCH_URL, "query_start_utc": start_utc, "query_end_utc": end_utc,
        "candidate_total": "", "quality_candidate_total": "", "existing_observation_total": str(len(existing)),
        "sample_plan_total": "", "sample_attempt_total": "",
        "raw_path": str(raw_relative), "response_sha256": "NONE",
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "source_status": "", "error": "",
    }
    attempts: List[Dict[str, str]] = []
    observations: List[Dict[str, str]] = [dict(row) for row in existing]
    feature = {field: "" for field in FEATURE_FIELDS}
    feature["scenario_id"] = scenario_id
    status = {
        "scenario_id": scenario_id, "ndvi_timeseries_status": "", "natural_conflict_evidence_eligibility": "",
        "satellite_actionability": "context_only_not_a_crop_label_or_field_diagnosis", "restriction_reason": "",
    }
    try:
        payload = {
            "collections": ["sentinel-2-l2a"], "intersects": {"type": "Point", "coordinates": [float(scenario["longitude"]), float(scenario["latitude"])]},
            "datetime": f"{start_utc}/{end_utc}", "limit": 100,
        }
        response = requests.post(STAC_SEARCH_URL, headers={**REQUEST_HEADERS, "Content-Type": "application/json"}, json=payload, timeout=timeout_s)
        response.raise_for_status()
        raw_bytes = response.content
        raw_path = out_dir / raw_relative
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw_bytes)
        raw_hash = sha256(raw_bytes).hexdigest()
        result = response.json()
        all_features = result.get("features")
        decision_end = datetime.combine(decision, datetime.max.time(), tzinfo=timezone.utc)
        existing_item_ids = {row["satellite_item_id"] for row in observations}
        candidates = [item for item in quality_candidates(all_features, decision_end) if item_metadata(item)[0] not in existing_item_ids]
        plan = evenly_spaced_plan(candidates, max_samples)
        manifest.update({
            "candidate_total": str(len(all_features)) if isinstance(all_features, list) else "0",
            "quality_candidate_total": str(len(candidates)), "sample_plan_total": str(len(plan)),
            "response_sha256": raw_hash, "source_status": "predecision_stac_search_retrieved_and_metadata_filtered",
        })
        for plan_rank, item in enumerate(plan, start=1):
            item_id, observed, cloud, nodata = item_metadata(item)
            attempt = {
                "scenario_id": scenario_id, "candidate_plan_rank": str(plan_rank), "satellite_item_id": item_id,
                "satellite_datetime_utc": observed.isoformat().replace("+00:00", "Z"), "scene_cloud_cover_percent": f"{cloud:.6f}",
                "scene_nodata_percent": f"{nodata:.6f}",
                "candidate_selection_rule": "evenly_spaced_temporal_plan_from_predecision_STAC_candidates_passing_cloud_nodata_metadata;_NDVI_not_used_for_selection",
                "sampling_status": "", "satellite_scl_class": "", "satellite_scl_label": "", "satellite_pixel_quality_status": "", "error": "",
            }
            try:
                assets = item["assets"]
                scl = sample_asset(assets["SCL"], float(scenario["longitude"]), float(scenario["latitude"]), token)
                label, quality = pixel_quality(scl)
                attempt.update({"satellite_scl_class": str(scl), "satellite_scl_label": label, "satellite_pixel_quality_status": quality})
                if scl not in CLEAR_SURFACE_SCL:
                    attempt["sampling_status"] = "withheld_non_clear_or_non_land_pixel"
                    attempts.append(attempt)
                    continue
                red = sample_asset(assets["B04"], float(scenario["longitude"]), float(scenario["latitude"]), token)
                nir = sample_asset(assets["B08"], float(scenario["longitude"]), float(scenario["latitude"]), token)
                attempt["sampling_status"] = "clear_point_ndvi_collected"
                observations.append({
                    "scenario_id": scenario_id, "observation_rank_by_time": "", "satellite_item_id": item_id,
                    "satellite_datetime_utc": observed.isoformat().replace("+00:00", "Z"), "scene_cloud_cover_percent": f"{cloud:.6f}",
                    "scene_nodata_percent": f"{nodata:.6f}", "satellite_point_scope": "documented_representative_cropland_cell",
                    "satellite_scl_class": str(scl), "satellite_scl_label": label, "satellite_pixel_quality_status": quality,
                    "satellite_red_dn": str(red), "satellite_nir_dn": str(nir), "satellite_ndvi": f"{ndvi(red, nir):.6f}",
                    "observation_provenance": "new_predecision_stac_search", "evidence_response_sha256": raw_hash,
                })
            except (ValueError, KeyError, TypeError, rasterio.errors.RasterioError, requests.RequestException) as exc:
                attempt.update({"sampling_status": "asset_or_pixel_validation_failed", "error": f"{type(exc).__name__}: {exc}"})
            attempts.append(attempt)
        observations.sort(key=lambda row: row["satellite_datetime_utc"])
        for rank, observation in enumerate(observations, start=1):
            observation["observation_rank_by_time"] = str(rank)
        manifest["sample_attempt_total"] = str(len(attempts))
        if len(observations) >= 3:
            timeseries_status, eligibility = "available_three_or_more_clear_predecision_observations", "eligible_for_non_action_signal_divergence_analysis"
        elif observations:
            timeseries_status, eligibility = "limited_one_or_two_clear_predecision_observations", "not_eligible_insufficient_time_series"
        else:
            timeseries_status, eligibility = "unavailable_no_clear_sampled_predecision_observation", "not_eligible_no_time_series"
        status.update({
            "ndvi_timeseries_status": timeseries_status, "natural_conflict_evidence_eligibility": eligibility,
            "restriction_reason": "public representative-cell NDVI chronology only; not a parcel crop label, crop stage, disease diagnosis, or farm action trigger",
        })
        if observations:
            points = [(parse_datetime(row["satellite_datetime_utc"]), float(row["satellite_ndvi"])) for row in observations]
            change = points[-1][1] - points[0][1]
            feature.update({
                "observation_count": str(len(points)), "first_observation_utc": observations[0]["satellite_datetime_utc"],
                "last_observation_utc": observations[-1]["satellite_datetime_utc"],
                "time_span_days": f"{(points[-1][0] - points[0][0]).total_seconds() / 86400:.3f}",
                "first_ndvi": f"{points[0][1]:.6f}", "last_ndvi": f"{points[-1][1]:.6f}",
                "ndvi_change": f"{change:.6f}", "ndvi_linear_slope_per_day": f"{linear_slope(points):.8f}" if len(points) > 1 else "",
                "ndvi_trend_direction": trend_direction(change) if len(points) > 1 else "single_observation_no_trend",
                "series_interpretation": "Numerical pre-decision NDVI trajectory at the documented representative cell; no crop-condition or action inference is made.",
            })
    except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        manifest.update({"source_status": "predecision_stac_search_failed", "error": f"{type(exc).__name__}: {exc}"})
        status.update({
            "ndvi_timeseries_status": "unavailable_source_or_validation_failure", "natural_conflict_evidence_eligibility": "not_eligible_no_time_series",
            "restriction_reason": f"source_or_validation_failure:{type(exc).__name__}",
        })
    return manifest, attempts, observations, feature, status


def frozen_context_observations(enriched: Path, scenarios: Sequence[Mapping[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Reuse only existing clear, source-hashed point observations.

    The original benchmark already contains a quality-checked pre-decision
    Sentinel observation for most scenarios (and a bounded recovery observation
    for a few). Reuse eliminates redundant public COG reads while retaining
    the original raw-response hash and provenance.
    """
    decisions = {row["scenario_id"]: row["decision_date"] for row in scenarios}
    base_manifest = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_context_manifest.csv")}
    base_features = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_context_features.csv") if row.get("satellite_ndvi")}
    recovery_manifest = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_recovery_manifest.csv")}
    recovery_features = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_recovery_features.csv") if row.get("satellite_ndvi")}
    result: Dict[str, List[Dict[str, str]]] = {row["scenario_id"]: [] for row in scenarios}
    for scenario_id in result:
        feature, manifest = base_features.get(scenario_id), base_manifest.get(scenario_id)
        provenance = "frozen_exact_context"
        evidence_hash = manifest.get("response_sha256", "") if manifest else ""
        if feature is None:
            feature, manifest = recovery_features.get(scenario_id), recovery_manifest.get(scenario_id)
            provenance = "frozen_same_window_recovery_context"
            evidence_hash = manifest.get("item_response_sha256", "") if manifest else ""
        if feature is None or manifest is None or not evidence_hash or feature["satellite_datetime_utc"][:10] > decisions[scenario_id]:
            continue
        result[scenario_id].append({
            "scenario_id": scenario_id, "observation_rank_by_time": "", "satellite_item_id": feature["satellite_item_id"],
            "satellite_datetime_utc": feature["satellite_datetime_utc"], "scene_cloud_cover_percent": "", "scene_nodata_percent": "",
            "satellite_point_scope": feature["satellite_point_scope"], "satellite_scl_class": feature["satellite_scl_class"],
            "satellite_scl_label": feature["satellite_scl_label"], "satellite_pixel_quality_status": feature["satellite_pixel_quality_status"],
            "satellite_red_dn": feature["satellite_red_dn"], "satellite_nir_dn": feature["satellite_nir_dn"], "satellite_ndvi": feature["satellite_ndvi"],
            "observation_provenance": provenance, "evidence_response_sha256": evidence_hash,
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect quality-gated pre-decision Sentinel NDVI time series.")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "data" / "scenarios" / "enriched")
    parser.add_argument("--existing-context-dir", type=Path, default=PROJECT_ROOT / "data" / "scenarios" / "enriched", help="Existing verified single-scene/recovery enrichment directory.")
    parser.add_argument("--scenario-id", action="append", help="Exact scenario ID, repeatable; use for a pilot.")
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--max-samples", type=int, default=3, help="Maximum newly sampled older scenes; a verified endpoint observation is reused when available.")
    parser.add_argument("--workers", type=int, default=1, help="Bounded public COG request concurrency (1–4).")
    parser.add_argument("--timeout-s", type=float, default=45.0)
    args = parser.parse_args()
    if args.lookback_days < 30 or args.max_samples < 3 or not 1 <= args.workers <= 4 or args.timeout_s <= 0:
        raise SystemExit("lookback must be >=30, max samples >=3, workers 1–4, and timeout positive.")
    scenarios = read_csv(args.manifest)
    requested = set(args.scenario_id or [])
    selected = [row for row in scenarios if not requested or row["scenario_id"] in requested]
    missing = requested - {row["scenario_id"] for row in selected}
    if missing:
        raise SystemExit(f"Unknown frozen scenario ID(s): {', '.join(sorted(missing))}")
    if not selected:
        raise SystemExit("No frozen scenarios selected.")
    frozen_context = frozen_context_observations(args.existing_context_dir, selected)
    token_response = requests.get(SAS_TOKEN_URL, headers=REQUEST_HEADERS, timeout=args.timeout_s)
    token_response.raise_for_status()
    token = token_response.json().get("token")
    if not isinstance(token, str) or not token:
        raise SystemExit("Planetary Computer did not return an asset token.")
    results: Dict[str, tuple[Dict[str, str], List[Dict[str, str]], List[Dict[str, str]], Dict[str, str], Dict[str, str]]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending = {
            executor.submit(
                fetch_one, scenario, frozen_context[scenario["scenario_id"]], args.out_dir, token,
                args.lookback_days, args.max_samples, args.timeout_s,
            ): scenario["scenario_id"]
            for scenario in selected
        }
        for index, future in enumerate(as_completed(pending), start=1):
            scenario_id = pending[future]
            results[scenario_id] = future.result()
            print(f"[{index}/{len(selected)}] {scenario_id}: {results[scenario_id][0]['source_status']}")
    manifests, attempts, observations, features, statuses = [], [], [], [], []
    for scenario in selected:
        manifest, scenario_attempts, scenario_observations, feature, status = results[scenario["scenario_id"]]
        manifests.append(manifest); attempts.extend(scenario_attempts); observations.extend(scenario_observations); features.append(feature); statuses.append(status)
    write_csv(args.out_dir / "sentinel_ndvi_timeseries_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "sentinel_ndvi_timeseries_attempts.csv", ATTEMPT_FIELDS, attempts)
    write_csv(args.out_dir / "sentinel_ndvi_timeseries_observations.csv", OBSERVATION_FIELDS, observations)
    write_csv(args.out_dir / "sentinel_ndvi_timeseries_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "sentinel_ndvi_timeseries_status.csv", STATUS_FIELDS, statuses)
    available = sum(row["ndvi_timeseries_status"].startswith("available_") for row in statuses)
    print(f"Pre-decision NDVI series with three or more clear points: {available}/{len(selected)}.")


if __name__ == "__main__":
    main()
