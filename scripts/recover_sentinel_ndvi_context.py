"""Recover withheld Sentinel point context without altering frozen scenarios.

This recovery layer considers only candidates already returned in each
scenario's *frozen, same-month* STAC search response.  Candidates are visited
in the benchmark's deterministic ``cloud, nodata, datetime`` order. The first
one that contains the representative coordinate and has a clear SCL surface
pixel is admitted. NDVI is never part of selection.

The original frozen item remains untouched. This is an additive, versioned
recovery record and is intentionally not a crop/parcel observation.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_sentinel_ndvi_context import (  # noqa: E402
    CLEAR_SURFACE_SCL,
    REQUEST_HEADERS,
    SAS_TOKEN_URL,
    STAC_ITEM_BASE,
    ndvi,
    pixel_quality,
    sample_asset,
)
from scripts.collect_sentinel_scene_coverage import feature_sort_key, is_quality_candidate  # noqa: E402


MANIFEST_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "decision_date", "longitude", "latitude",
    "base_satellite_status", "frozen_search_raw_path", "frozen_search_sha256", "candidate_count",
    "selected_candidate_rank", "selected_item_id", "selected_datetime_utc", "selected_cloud_cover_percent",
    "selected_nodata_percent", "item_request_url", "item_raw_path", "item_response_sha256",
    "retrieved_at_utc", "recovery_status", "error",
]
FEATURE_FIELDS = [
    "scenario_id", "satellite_item_id", "satellite_datetime_utc", "satellite_point_scope",
    "satellite_scl_class", "satellite_scl_label", "satellite_pixel_quality_status",
    "satellite_red_dn", "satellite_nir_dn", "satellite_ndvi", "satellite_condition_interpretation",
]
STATUS_FIELDS = [
    "scenario_id", "satellite_recovery_status", "candidate_selection_rule", "recovery_actionability", "restriction_reason",
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


def bytes_hash(value: bytes) -> str:
    return sha256(value).hexdigest()


def raw_relative_path(scenario_id: str) -> Path:
    if not scenario_id.replace("_", "").isalnum():
        raise ValueError("Scenario ID is unsafe for recovery raw filename.")
    return Path("raw") / "sentinel_ndvi_recovery" / f"{scenario_id}.json"


def in_declared_window(value: str, window: str) -> bool:
    try:
        start, end = window.split("/", maxsplit=1)
        normalise = lambda text: datetime.fromisoformat(text.replace("Z", "+00:00"))
        return normalise(start) <= normalise(value) <= normalise(end)
    except ValueError:
        return False


def select_recovery_candidate(
    scenario: Mapping[str, str], search_result: Mapping[str, Any], token: str, timeout_s: float
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None, bytes | None, Dict[str, str], List[str]]:
    """Return the first deterministic clear candidate and its direct item response."""
    features = search_result.get("features")
    if not isinstance(features, list):
        raise ValueError("Frozen source search response has no features list.")
    candidates = sorted(
        [item for item in features if isinstance(item, dict) and is_quality_candidate(item)], key=feature_sort_key
    )
    rejections: List[str] = []
    for rank, candidate in enumerate(candidates, start=1):
        candidate_id = str(candidate.get("id", ""))
        props = candidate.get("properties")
        if not candidate_id or not isinstance(props, dict):
            rejections.append(f"rank_{rank}_malformed_candidate")
            continue
        expected_datetime = str(props.get("datetime", ""))
        if not in_declared_window(expected_datetime, scenario["satellite_window_utc"]):
            rejections.append(f"rank_{rank}_outside_declared_window")
            continue
        item_url = f"{STAC_ITEM_BASE}/{candidate_id}"
        response = requests.get(item_url, headers=REQUEST_HEADERS, timeout=timeout_s)
        response.raise_for_status()
        item = response.json()
        if item.get("id") != candidate_id:
            raise ValueError("Direct Sentinel item ID differs from frozen search candidate ID.")
        item_props = item.get("properties")
        if not isinstance(item_props, dict) or str(item_props.get("datetime", "")) != expected_datetime:
            raise ValueError("Direct Sentinel item datetime differs from frozen search candidate datetime.")
        if not is_quality_candidate(item):
            raise ValueError("Direct Sentinel item no longer passes frozen cloud/nodata gate.")
        assets = item.get("assets")
        if not isinstance(assets, dict):
            raise ValueError("Direct Sentinel item has no assets object.")
        try:
            scl = sample_asset(assets["SCL"], float(scenario["longitude"]), float(scenario["latitude"]), token)
        except ValueError as exc:
            rejections.append(f"rank_{rank}_{type(exc).__name__}")
            continue
        label, quality = pixel_quality(scl)
        if scl not in CLEAR_SURFACE_SCL:
            rejections.append(f"rank_{rank}_scl_{scl}_{label}")
            continue
        red = sample_asset(assets["B04"], float(scenario["longitude"]), float(scenario["latitude"]), token)
        nir = sample_asset(assets["B08"], float(scenario["longitude"]), float(scenario["latitude"]), token)
        return candidate, item, response.content, {
            "rank": str(rank), "scl": str(scl), "label": label, "quality": quality,
            "red": str(red), "nir": str(nir), "ndvi": f"{ndvi(red, nir):.6f}", "count": str(len(candidates)),
        }, rejections
    return None, None, None, {"count": str(len(candidates))}, rejections


def recover_one(
    scenario: Mapping[str, str], base_status: Mapping[str, str], scenario_root: Path, out_dir: Path, token: str, timeout_s: float
) -> tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    scenario_id = scenario["scenario_id"]
    raw_search_path = scenario_root / scenario["satellite_raw_path"]
    manifest = {
        "scenario_id": scenario_id, "site_id": scenario["site_id"], "crop": scenario["crop"], "state": scenario["state"],
        "district": scenario["district"], "decision_date": scenario["decision_date"], "longitude": scenario["longitude"], "latitude": scenario["latitude"],
        "base_satellite_status": base_status["satellite_condition_status"], "frozen_search_raw_path": scenario["satellite_raw_path"],
        "frozen_search_sha256": scenario.get("satellite_response_sha256", ""), "candidate_count": "", "selected_candidate_rank": "",
        "selected_item_id": "", "selected_datetime_utc": "", "selected_cloud_cover_percent": "", "selected_nodata_percent": "",
        "item_request_url": "", "item_raw_path": "", "item_response_sha256": "", "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "recovery_status": "", "error": "",
    }
    feature = {field: "" for field in FEATURE_FIELDS}
    feature["scenario_id"] = scenario_id
    status = {
        "scenario_id": scenario_id, "satellite_recovery_status": "", "candidate_selection_rule": (
            "first_candidate_in_frozen_same_month_STAC_response_sorted_by_cloud_nodata_datetime_that_contains_point_and_has_clear_SCL;_NDVI_not_used_for_selection"
        ), "recovery_actionability": "context_only_not_a_crop_label_or_field_diagnosis", "restriction_reason": "",
    }
    try:
        if not raw_search_path.is_file():
            raise ValueError("Frozen STAC search payload is absent.")
        raw_search = raw_search_path.read_bytes()
        if bytes_hash(raw_search) != scenario["satellite_response_sha256"]:
            raise ValueError("Frozen STAC search payload hash does not match scenario manifest.")
        candidate, item, item_bytes, values, rejections = select_recovery_candidate(
            scenario, json.loads(raw_search), token, timeout_s
        )
        manifest["candidate_count"] = values["count"]
        if candidate is None or item is None or item_bytes is None:
            manifest.update({
                "recovery_status": "not_recovered_no_clear_contained_candidate_in_frozen_window",
                "error": ";".join(rejections),
            })
            status.update({
                "satellite_recovery_status": "not_recovered_no_clear_contained_candidate_in_frozen_window",
                "restriction_reason": "all source-window candidates were cloud/non-clear, out-of-asset, or otherwise unsuitable at the exact coordinate",
            })
            return manifest, feature, status
        props = item["properties"]
        item_id = str(item["id"])
        item_url = f"{STAC_ITEM_BASE}/{item_id}"
        relative_raw = raw_relative_path(scenario_id)
        destination = out_dir / relative_raw
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(item_bytes)
        manifest.update({
            "selected_candidate_rank": values["rank"], "selected_item_id": item_id,
            "selected_datetime_utc": str(props["datetime"]), "selected_cloud_cover_percent": f"{float(props['eo:cloud_cover']):.6f}",
            "selected_nodata_percent": f"{float(props['s2:nodata_pixel_percentage']):.6f}", "item_request_url": item_url,
            "item_raw_path": str(relative_raw), "item_response_sha256": bytes_hash(item_bytes),
            "recovery_status": "recovered_clear_point_ndvi_from_alternate_frozen_window_candidate",
        })
        feature.update({
            "satellite_item_id": item_id, "satellite_datetime_utc": str(props["datetime"]),
            "satellite_point_scope": "documented_representative_cropland_cell",
            "satellite_scl_class": values["scl"], "satellite_scl_label": values["label"],
            "satellite_pixel_quality_status": values["quality"], "satellite_red_dn": values["red"], "satellite_nir_dn": values["nir"],
            "satellite_ndvi": values["ndvi"], "satellite_condition_interpretation": (
                "NDVI is calculated from an alternate Sentinel-2 item already present in the exact frozen same-month STAC response. "
                "The candidate was selected by source quality, containment, and clear SCL only, not NDVI."
            ),
        })
        status.update({
            "satellite_recovery_status": "recovered_clear_point_ndvi_from_alternate_frozen_window_candidate",
            "restriction_reason": "representative-cell context only; not a crop-labelled parcel, field average, observed stage, or disease diagnosis",
        })
    except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        manifest.update({"recovery_status": "recovery_validation_failed", "error": f"{type(exc).__name__}: {exc}"})
        status.update({"satellite_recovery_status": "recovery_validation_failed", "restriction_reason": f"source_or_pixel_validation_failed: {type(exc).__name__}"})
    return manifest, feature, status


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Recover withheld Sentinel context from frozen same-window STAC candidates.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--base-status", type=Path, default=scenarios / "enriched" / "sentinel_ndvi_context_status.csv")
    parser.add_argument("--scenario-root", type=Path, default=scenarios)
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    parser.add_argument("--timeout-s", type=float, default=45.0)
    args = parser.parse_args()
    base_status = {row["scenario_id"]: row for row in read_csv(args.base_status)}
    selected = [
        row for row in read_csv(args.manifest)
        if not base_status[row["scenario_id"]]["satellite_condition_status"].startswith("available")
    ]
    token_response = requests.get(SAS_TOKEN_URL, headers=REQUEST_HEADERS, timeout=args.timeout_s)
    token_response.raise_for_status()
    token = token_response.json().get("token")
    if not isinstance(token, str) or not token:
        raise SystemExit("Planetary Computer did not return an asset token.")
    manifests, features, statuses = [], [], []
    for index, scenario in enumerate(selected, start=1):
        manifest, feature, status = recover_one(scenario, base_status[scenario["scenario_id"]], args.scenario_root, args.out_dir, token, args.timeout_s)
        manifests.append(manifest); features.append(feature); statuses.append(status)
        print(f"[{index}/{len(selected)}] {scenario['scenario_id']}: {manifest['recovery_status']}")
    write_csv(args.out_dir / "sentinel_ndvi_recovery_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "sentinel_ndvi_recovery_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "sentinel_ndvi_recovery_status.csv", STATUS_FIELDS, statuses)
    recovered = sum(row["recovery_status"] == "recovered_clear_point_ndvi_from_alternate_frozen_window_candidate" for row in manifests)
    print(f"Sentinel recovery availability: {recovered}/{len(selected)} withheld base records.")


if __name__ == "__main__":
    main()
