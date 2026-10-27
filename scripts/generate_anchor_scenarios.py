"""Generate evidence-bound anchor scenarios from the frozen final registry.

The frozen registry provides one fully admitted crop--district decision window
per site. This generator re-downloads the exact historic NASA POWER and
Agmarknet requests for those windows, writes their raw public responses, and
creates scenario manifests and aligned feature rows.

It deliberately does not infer crop stage, a disease event, a negative disease
finding, a farm-specific fertilizer dose, or a protection action. Those fields
stay explicitly unavailable unless a separately archived, site/date-compatible
source supports them.

Run from the repository root:

    .venv-macos/bin/python scripts/generate_anchor_scenarios.py
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_agmarknet_historical_market_evidence import REQUEST_HEADERS as AGMARKNET_HEADERS
from scripts.collect_agmarknet_historical_market_evidence import payload_hash, scenario_for_crop


NASA_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0 verified-anchor-scenarios",
    "Accept": "application/json",
}
SOIL_PROPERTIES = ("phh2o", "nitrogen", "clay", "sand", "silt", "ocd")
VERIFIED_SOURCE_STATUS = "dated_source_semantics_verified"
MARKET_STATUS = "same_crop_historical_district_market_report_available"
WEATHER_STATUS = "fixed_window_weather_verified"
SATELLITE_STATUS = "quality_scene_metadata_available"
SOIL_STATUS = "static_wcs_value_collected"


MANIFEST_FIELDS = [
    "scenario_id", "scenario_type", "scenario_status", "site_id", "crop", "state", "district",
    "season", "season_window", "decision_date", "decision_window_utc", "geometry_scope",
    "longitude", "latitude", "weather_source_url", "weather_registry_response_sha256",
    "weather_current_response_sha256", "weather_raw_path", "market_source_url",
    "market_registry_payload_sha256", "market_current_payload_sha256", "market_raw_path",
    "satellite_item_id", "satellite_datetime_utc", "management_bundle_id",
    "fertilizer_source_id", "protection_source_id", "crop_stage_status",
    "disease_event_status", "farm_fertilizer_status", "crop_protection_status",
    "generation_timestamp_utc",
]
FEATURE_FIELDS = [
    "scenario_id", "weather_observed_days", "weather_t2m_mean_c", "weather_t2m_min_c",
    "weather_t2m_max_c", "weather_precipitation_total_mm", "weather_rh2m_mean_percent",
    "weather_ws2m_mean_m_s", "soil_phh2o_raw", "soil_nitrogen_raw", "soil_clay_raw",
    "soil_sand_raw", "soil_silt_raw", "soil_ocd_raw", "satellite_item_id",
    "satellite_datetime_utc", "satellite_cloud_cover_percent", "satellite_nodata_percent",
    "satellite_gsd_m", "market_source_price_key", "market_priced_market_count",
    "market_price_mean_as_reported", "market_price_min_as_reported",
    "market_price_max_as_reported", "market_price_unit_status",
]
EVIDENCE_FIELDS = [
    "scenario_id", "crop_stage_status", "disease_event_status", "farm_fertilizer_status",
    "crop_protection_status", "fertilizer_source_id", "fertilizer_locator",
    "protection_source_id", "protection_locator", "ppqs_source_ids",
    "management_conditions_and_exclusions", "evidence_interpretation",
]
REJECTION_FIELDS = ["site_id", "crop", "state", "district", "rejection_reason"]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def by_site(rows: Iterable[Dict[str, str]], label: str) -> Dict[str, Dict[str, str]]:
    records = list(rows)
    indexed = {row["site_id"]: row for row in records}
    if len(indexed) != len(records):
        raise ValueError(f"{label} contains duplicate site IDs.")
    return indexed


def index_soil(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, Dict[str, str]]]:
    indexed: Dict[str, Dict[str, Dict[str, str]]] = {}
    for row in rows:
        indexed.setdefault(row["site_id"], {})[row["property_id"]] = row
    return indexed


def validate_input_identity(
    sites: Sequence[Dict[str, str]],
    weather: Mapping[str, Dict[str, str]],
    market: Mapping[str, Dict[str, str]],
    soil: Mapping[str, Mapping[str, Dict[str, str]]],
    satellite: Mapping[str, Dict[str, str]],
) -> None:
    expected = {site["site_id"] for site in sites}
    for label, artifact in (
        ("weather", weather), ("market", market), ("soil", soil), ("satellite", satellite)
    ):
        if set(artifact) != expected:
            raise ValueError(f"{label} site IDs do not exactly match final_study_sites.csv.")
    for site_id, properties in soil.items():
        if set(properties) != set(SOIL_PROPERTIES):
            raise ValueError(f"{site_id} does not have exactly the declared SoilGrids properties.")


def numeric(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric source value.")
    result = float(value)
    if result <= -900:
        raise ValueError("NASA POWER fill value cannot be used as an observation.")
    return result


def numeric_series(parameter: Mapping[str, Any], name: str) -> List[float]:
    values = parameter.get(name)
    if not isinstance(values, dict) or not values:
        raise ValueError(f"NASA POWER response is missing {name}.")
    return [numeric(value) for _, value in sorted(values.items())]


def weather_features(payload: Mapping[str, Any], expected_days: int) -> Dict[str, Any]:
    parameter = payload.get("properties", {}).get("parameter")
    if not isinstance(parameter, dict):
        raise ValueError("NASA POWER response has no properties.parameter object.")
    t2m = numeric_series(parameter, "T2M")
    precipitation = numeric_series(parameter, "PRECTOTCORR")
    rh2m = numeric_series(parameter, "RH2M")
    ws2m = numeric_series(parameter, "WS2M")
    if not all(len(values) == expected_days for values in (t2m, precipitation, rh2m, ws2m)):
        raise ValueError("NASA POWER response does not contain a complete frozen-window series.")
    return {
        "weather_observed_days": expected_days,
        "weather_t2m_mean_c": f"{statistics.fmean(t2m):.3f}",
        "weather_t2m_min_c": f"{min(t2m):.3f}",
        "weather_t2m_max_c": f"{max(t2m):.3f}",
        "weather_precipitation_total_mm": f"{sum(precipitation):.3f}",
        "weather_rh2m_mean_percent": f"{statistics.fmean(rh2m):.3f}",
        "weather_ws2m_mean_m_s": f"{statistics.fmean(ws2m):.3f}",
    }


def market_features(payload: Mapping[str, Any], crop: str, expected_title: str) -> Dict[str, Any]:
    scenario = scenario_for_crop(crop)
    if payload.get("success") is not True or payload.get("title") != expected_title:
        raise ValueError("Agmarknet response no longer matches the preflight report identity.")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Agmarknet response has no rows list.")
    prices = [
        numeric(row[scenario.price_key])
        for row in rows
        if isinstance(row, dict) and row.get(scenario.price_key) is not None
    ]
    if not prices:
        raise ValueError("Agmarknet report has no non-null price for the frozen month.")
    return {
        "market_source_price_key": scenario.price_key,
        "market_priced_market_count": len(prices),
        "market_price_mean_as_reported": f"{statistics.fmean(prices):.3f}",
        "market_price_min_as_reported": f"{min(prices):.3f}",
        "market_price_max_as_reported": f"{max(prices):.3f}",
        "market_price_unit_status": "as_reported_by_agmarknet_monthly_API_no_unit_inference",
    }


def fetch_json(url: str, headers: Mapping[str, str], timeout_s: float) -> tuple[bytes, Dict[str, Any]]:
    response = requests.get(url, headers=dict(headers), timeout=timeout_s)
    response.raise_for_status()
    content = response.content
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Public API response must be a JSON object.")
    return content, payload


def management_bundle(
    site: Mapping[str, str],
    bundles: Mapping[str, Dict[str, str]],
    source_snapshot: Mapping[str, Dict[str, str]],
) -> Dict[str, str]:
    bundle = bundles.get(site["management_bundle_id"])
    if bundle is None:
        raise ValueError(f"{site['site_id']} has no management bundle.")
    expected_ids = [
        bundle["fertilizer_source_id"], bundle["protection_source_id"],
        *(source_id.strip() for source_id in bundle["ppqs_source_id"].split(";") if source_id.strip()),
    ]
    if any(source_snapshot.get(source_id, {}).get("source_status") != VERIFIED_SOURCE_STATUS for source_id in expected_ids):
        raise ValueError(f"{site['site_id']} management source snapshot does not pass its verification status.")
    if (
        site["fertilizer_source_id"] != bundle["fertilizer_source_id"]
        or site["protection_source_id"] != bundle["protection_source_id"]
    ):
        raise ValueError(f"{site['site_id']} management source IDs do not match its bundle.")
    return bundle


def scenario_id(site: Mapping[str, str]) -> str:
    return f"ANCHOR_{site['site_id']}_{site['fixed_decision_date'].replace('-', '')}"


def build_anchor(
    site: Dict[str, str],
    weather: Dict[str, str],
    market: Dict[str, str],
    soil: Mapping[str, Dict[str, str]],
    satellite: Dict[str, str],
    bundle: Dict[str, str],
    *,
    raw_root: Path,
    timeout_s: float,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    if site["freeze_status"] != "admitted":
        raise ValueError("Only admitted final sites can generate an anchor scenario.")
    if weather.get("weather_status") != WEATHER_STATUS:
        raise ValueError("Frozen weather evidence is not verified.")
    if market.get("historical_market_status") != MARKET_STATUS:
        raise ValueError("Frozen market evidence is not verified.")
    if satellite.get("status") != SATELLITE_STATUS:
        raise ValueError("Frozen Sentinel evidence is not verified.")
    if any(row.get("status") != SOIL_STATUS for row in soil.values()):
        raise ValueError("Frozen SoilGrids evidence is incomplete.")
    if market["official_url"] != site["market_source_url"]:
        raise ValueError("Final manifest market URL does not match preflight evidence.")
    if weather["fixed_decision_date"] != site["fixed_decision_date"]:
        raise ValueError("Weather decision date does not match final manifest.")
    if market["benchmark_market_decision_date"] != site["fixed_decision_date"]:
        raise ValueError("Market decision date does not match final manifest.")
    for artifact in (weather, satellite):
        if abs(float(artifact["longitude"]) - float(site["longitude"])) > 0.00001:
            raise ValueError("An evidence coordinate does not match the final manifest longitude.")
        if abs(float(artifact["latitude"]) - float(site["latitude"])) > 0.00001:
            raise ValueError("An evidence coordinate does not match the final manifest latitude.")

    current_weather_content, current_weather = fetch_json(weather["official_url"], NASA_HEADERS, timeout_s)
    current_market_content, current_market = fetch_json(market["official_url"], AGMARKNET_HEADERS, timeout_s)
    weather_summary = weather_features(current_weather, int(weather["day_count"]))
    market_summary = market_features(current_market, site["crop"], market["report_title"])
    current_market_hash = payload_hash(current_market)
    if current_market_hash != market["payload_sha256"]:
        raise ValueError("Agmarknet payload hash differs from the frozen historic report.")

    identifier = scenario_id(site)
    weather_raw_relative = Path("raw") / "nasa_power" / f"{identifier}.json"
    market_raw_relative = Path("raw") / "agmarknet" / f"{identifier}.json"
    weather_raw_path = raw_root / weather_raw_relative
    market_raw_path = raw_root / market_raw_relative
    weather_raw_path.parent.mkdir(parents=True, exist_ok=True)
    market_raw_path.parent.mkdir(parents=True, exist_ok=True)
    weather_raw_path.write_bytes(current_weather_content)
    market_raw_path.write_bytes(current_market_content)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = {
        "scenario_id": identifier,
        "scenario_type": "verified_anchor_context",
        "scenario_status": "ready_for_context_evaluation_with_required_abstentions",
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"],
        "district": site["district"],
        "season": site["proposed_season"],
        "season_window": site["season_window"],
        "decision_date": site["fixed_decision_date"],
        "decision_window_utc": site["decision_window_utc"],
        "geometry_scope": site["geometry_scope"],
        "longitude": site["longitude"],
        "latitude": site["latitude"],
        "weather_source_url": weather["official_url"],
        "weather_registry_response_sha256": weather["response_sha256"],
        "weather_current_response_sha256": sha256(current_weather_content).hexdigest(),
        "weather_raw_path": str(weather_raw_relative),
        "market_source_url": market["official_url"],
        "market_registry_payload_sha256": market["payload_sha256"],
        "market_current_payload_sha256": current_market_hash,
        "market_raw_path": str(market_raw_relative),
        "satellite_item_id": satellite["selected_item_id"],
        "satellite_datetime_utc": satellite["selected_datetime_utc"],
        "management_bundle_id": bundle["management_bundle_id"],
        "fertilizer_source_id": bundle["fertilizer_source_id"],
        "protection_source_id": bundle["protection_source_id"],
        "crop_stage_status": "not_observed_no_field_phenology_source",
        "disease_event_status": "not_observed_no_dated_site_event",
        "farm_fertilizer_status": "not_issued_regional_baseline_is_not_a_field_prescription",
        "crop_protection_status": "not_issued_no_dated_diagnosis_or_threshold_event",
        "generation_timestamp_utc": generated_at,
    }
    features = {
        "scenario_id": identifier,
        **weather_summary,
        **{f"soil_{property_id}_raw": soil[property_id]["raw_value"] for property_id in SOIL_PROPERTIES},
        "satellite_item_id": satellite["selected_item_id"],
        "satellite_datetime_utc": satellite["selected_datetime_utc"],
        "satellite_cloud_cover_percent": satellite["selected_cloud_cover_percent"],
        "satellite_nodata_percent": satellite["selected_nodata_percent"],
        "satellite_gsd_m": satellite["selected_gsd_m"],
        **market_summary,
    }
    evidence = {
        "scenario_id": identifier,
        "crop_stage_status": manifest["crop_stage_status"],
        "disease_event_status": manifest["disease_event_status"],
        "farm_fertilizer_status": manifest["farm_fertilizer_status"],
        "crop_protection_status": manifest["crop_protection_status"],
        "fertilizer_source_id": bundle["fertilizer_source_id"],
        "fertilizer_locator": bundle["fertilizer_locator"],
        "protection_source_id": bundle["protection_source_id"],
        "protection_locator": bundle["protection_locator"],
        "ppqs_source_ids": bundle["ppqs_source_id"],
        "management_conditions_and_exclusions": bundle["conditions_and_exclusions"],
        "evidence_interpretation": (
            "This is a public-data context record. It may support contextual analysis only; "
            "agents must abstain from disease treatment and farm-specific fertilizer decisions "
            "until separately archived, date-compatible evidence is available."
        ),
    }
    return manifest, features, evidence


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Generate public-data anchor scenarios from admitted final sites.")
    parser.add_argument("--sites", type=Path, default=registry / "final_study_sites.csv")
    parser.add_argument("--weather", type=Path, default=registry / "preflight_nasa_power_fixed_window_weather.csv")
    parser.add_argument("--market", type=Path, default=registry / "preflight_agmarknet_historical_market_coverage.csv")
    parser.add_argument("--soil", type=Path, default=registry / "preflight_soilgrids_wcs_profiles.csv")
    parser.add_argument("--satellite", type=Path, default=registry / "preflight_sentinel_scene_coverage.csv")
    parser.add_argument("--bundles", type=Path, default=registry / "preflight_management_bundle_catalog.csv")
    parser.add_argument("--sources", type=Path, default=registry / "regional_management_source_snapshot.csv")
    parser.add_argument("--out-dir", type=Path, default=scenarios)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--delay-s", type=float, default=0.2)
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.delay_s < 0:
        raise SystemExit("--timeout-s must be positive and --delay-s must be non-negative.")

    sites = read_csv(args.sites)
    weather = by_site(read_csv(args.weather), "weather")
    market = by_site(read_csv(args.market), "market")
    soil = index_soil(read_csv(args.soil))
    satellite = by_site(read_csv(args.satellite), "satellite")
    validate_input_identity(sites, weather, market, soil, satellite)
    bundles = {row["management_bundle_id"]: row for row in read_csv(args.bundles)}
    source_snapshot = {row["source_document_id"]: row for row in read_csv(args.sources)}

    manifests: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []
    rejections: List[Dict[str, str]] = []
    for index, site in enumerate(sites, start=1):
        try:
            bundle = management_bundle(site, bundles, source_snapshot)
            manifest, feature_row, evidence = build_anchor(
                site, weather[site["site_id"]], market[site["site_id"]], soil[site["site_id"]],
                satellite[site["site_id"]], bundle, raw_root=args.out_dir, timeout_s=args.timeout_s,
            )
            manifests.append(manifest)
            features.append(feature_row)
            evidence_rows.append(evidence)
            print(f"[{index}/{len(sites)}] {site['site_id']}: generated")
        except (OSError, ValueError, requests.RequestException, KeyError, TypeError) as exc:
            rejections.append({
                "site_id": site["site_id"], "crop": site["crop"], "state": site["state"],
                "district": site["district"], "rejection_reason": f"{type(exc).__name__}: {exc}",
            })
            print(f"[{index}/{len(sites)}] {site['site_id']}: rejected ({type(exc).__name__})")
        if index != len(sites):
            time.sleep(args.delay_s)

    write_csv(args.out_dir / "manifests" / "anchor_scenario_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "processed" / "anchor_scenario_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "evidence" / "anchor_scenario_evidence_status.csv", EVIDENCE_FIELDS, evidence_rows)
    write_csv(args.out_dir / "manifests" / "anchor_scenario_rejections.csv", REJECTION_FIELDS, rejections)
    print(f"Generated {len(manifests)}/{len(sites)} anchor scenarios; rejected: {len(rejections)}.")
    if rejections:
        raise SystemExit("One or more source-backed anchor scenarios were rejected; inspect anchor_scenario_rejections.csv.")


if __name__ == "__main__":
    main()
