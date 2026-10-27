"""Build strict final admission and a frozen manifest for the source-scoped pool.

The source-scoped preflight pool records the selection inputs for this frozen
benchmark; this builder does not consume an alternative site manifest.
This script admits only source-scoped replacements for which every published
evidence artifact is co-located at the documented representative cropland cell
and fixed decision month. It never alters its source-scoped selection input.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CELL_STATUS = "public_cropland_cell_inside_documented_district"
WEATHER_STATUS = "fixed_window_weather_verified"
SATELLITE_STATUS = "quality_scene_metadata_available"
SOIL_STATUS = "static_wcs_value_collected"
MARKET_STATUS = "same_crop_historical_district_market_report_available"
SOURCE_PREFLIGHT_STATUS = "ready_for_documented_location_window_preflight"
REQUIRED_SOIL_PROPERTIES = {"phh2o", "nitrogen", "clay", "sand", "silt", "ocd"}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def by_site(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {row["site_id"]: row for row in rows}


def gate(value: bool) -> str:
    return "pass" if value else "fail"


def close_coordinate(first: str, second: str) -> bool:
    try:
        return abs(float(first) - float(second)) <= 0.00001
    except (TypeError, ValueError):
        return False


def rows_at_cell(rows: Iterable[Dict[str, str]], cell: Dict[str, str]) -> bool:
    return all(
        close_coordinate(row.get("longitude", ""), cell["longitude"])
        and close_coordinate(row.get("latitude", ""), cell["latitude"])
        for row in rows
    )


def nonempty_hash(value: str) -> bool:
    return bool(value and value != "NONE")


OUTPUT_FIELDS = [
    "site_id", "crop", "state", "district", "candidate_location_gate", "fixed_decision_window_gate",
    "weather_gate", "crop_season_gate", "soil_gate", "satellite_gate", "historical_market_gate",
    "fertilizer_policy_gate", "protection_policy_gate", "management_provenance_gate", "artifact_hash_gate",
    "admission_status", "blocking_gates", "interpretation",
]
MANIFEST_FIELDS = [
    "site_id", "crop", "state", "district", "proposed_season", "season_window", "geometry_scope",
    "longitude", "latitude", "fixed_decision_date", "decision_window_utc", "market_source_id",
    "market_source_url", "market_payload_sha256", "management_bundle_id", "fertilizer_source_id",
    "protection_source_id", "freeze_status", "freeze_note",
]


def build_row(
    site: Dict[str, str], source_preflight: Dict[str, str], cell: Dict[str, str], weather: Dict[str, str],
    soil_rows: List[Dict[str, str]], sentinel: Dict[str, str], market: Dict[str, str]
) -> Dict[str, str]:
    candidate_location = (
        cell.get("geometry_scope") == "documented_representative_cell"
        and cell.get("cell_selection_status") == CELL_STATUS
        and bool(cell.get("longitude")) and bool(cell.get("latitude"))
    )
    fixed_window = (
        bool(cell.get("fixed_decision_date"))
        and bool(cell.get("decision_window_utc"))
        and cell.get("fixed_decision_date") == market.get("benchmark_market_decision_date")
        and cell.get("fixed_decision_date") == weather.get("fixed_decision_date")
        and cell.get("decision_window_utc") == weather.get("decision_window_utc")
        and cell.get("decision_window_utc") == sentinel.get("reference_window_utc")
    )
    weather_ok = weather.get("weather_status") == WEATHER_STATUS and rows_at_cell([weather], cell)
    soil_ok = (
        len(soil_rows) == len(REQUIRED_SOIL_PROPERTIES)
        and {row.get("property_id") for row in soil_rows} == REQUIRED_SOIL_PROPERTIES
        and all(row.get("status") == SOIL_STATUS for row in soil_rows)
        and rows_at_cell(soil_rows, cell)
    )
    satellite_ok = (
        sentinel.get("status") == SATELLITE_STATUS
        and rows_at_cell([sentinel], cell)
        and sentinel.get("reference_window_utc") == cell.get("decision_window_utc")
    )
    source_preflight_ok = source_preflight.get("preflight_status") == SOURCE_PREFLIGHT_STATUS
    artifact_hash_ok = (
        all(nonempty_hash(cell.get(name, "")) for name in ("district_geometry_sha256", "worldcover_raster_sha256"))
        and nonempty_hash(market.get("payload_sha256", ""))
        and nonempty_hash(weather.get("response_sha256", ""))
        and nonempty_hash(sentinel.get("response_sha256", ""))
        and len(soil_rows) == len(REQUIRED_SOIL_PROPERTIES)
        and all(nonempty_hash(row.get("value_tiff_sha256", "")) for row in soil_rows)
    )
    gates = {
        "candidate_location_gate": gate(candidate_location),
        "fixed_decision_window_gate": gate(fixed_window),
        "weather_gate": gate(weather_ok),
        "crop_season_gate": source_preflight.get("crop_season_gate", "fail"),
        "soil_gate": gate(soil_ok),
        "satellite_gate": gate(satellite_ok),
        "historical_market_gate": source_preflight.get("historical_market_gate", "fail"),
        "fertilizer_policy_gate": source_preflight.get("fertilizer_policy_gate", "fail"),
        "protection_policy_gate": source_preflight.get("protection_policy_gate", "fail"),
        "management_provenance_gate": source_preflight.get("management_provenance_gate", "fail"),
        "artifact_hash_gate": gate(artifact_hash_ok),
    }
    failures = [name for name, status in gates.items() if status != "pass"]
    return {
        "site_id": site["site_id"], "crop": site["crop"], "state": site["state"], "district": site["district"],
        **gates,
        "admission_status": "admitted" if not failures and source_preflight_ok else "not_admitted",
        "blocking_gates": ";".join(failures) if failures else "NONE",
        "interpretation": (
            "All source-scoped benchmark gates passed at the fixed representative cropland cell."
            if not failures and source_preflight_ok
            else "Not a final site; one or more explicit gates remain unsatisfied."
        ),
    }


def build_manifest_row(site: Dict[str, str], admission: Dict[str, str], cell: Dict[str, str], market: Dict[str, str], source_preflight: Dict[str, str]) -> Dict[str, str]:
    return {
        "site_id": site["site_id"], "crop": site["crop"], "state": site["state"], "district": site["district"],
        "proposed_season": site["proposed_season"], "season_window": site["season_window"],
        "geometry_scope": cell["geometry_scope"], "longitude": cell["longitude"], "latitude": cell["latitude"],
        "fixed_decision_date": cell["fixed_decision_date"], "decision_window_utc": cell["decision_window_utc"],
        "market_source_id": market["source_id"], "market_source_url": market["official_url"],
        "market_payload_sha256": market["payload_sha256"],
        "management_bundle_id": source_preflight["management_bundle_id"],
        "fertilizer_source_id": site["management_fertilizer_source_id"],
        "protection_source_id": site["management_protection_source_id"],
        "freeze_status": admission["admission_status"],
        "freeze_note": (
            "District-scale representative cropland scenario, not a surveyed farm or crop-type-labelled parcel."
        ),
    }


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    parser = argparse.ArgumentParser(description="Build final admission for the source-scoped replacement pool.")
    parser.add_argument("--sites", type=Path, default=registry / "source_scoped_preflight_pool.csv")
    parser.add_argument("--source-preflight", type=Path, default=registry / "source_scoped_preflight_audit.csv")
    parser.add_argument("--cells", type=Path, default=registry / "preflight_representative_cropland_cells.csv")
    parser.add_argument("--weather", type=Path, default=registry / "preflight_nasa_power_fixed_window_weather.csv")
    parser.add_argument("--soil", type=Path, default=registry / "preflight_soilgrids_wcs_profiles.csv")
    parser.add_argument("--sentinel", type=Path, default=registry / "preflight_sentinel_scene_coverage.csv")
    parser.add_argument("--market", type=Path, default=registry / "preflight_agmarknet_historical_market_coverage.csv")
    parser.add_argument("--out", type=Path, default=registry / "source_scoped_final_site_admission.csv")
    parser.add_argument("--manifest-out", type=Path, default=registry / "final_study_sites.csv")
    args = parser.parse_args()
    sites = read_csv(args.sites)
    source_preflight = by_site(read_csv(args.source_preflight))
    cells = by_site(read_csv(args.cells))
    weather = by_site(read_csv(args.weather))
    sentinel = by_site(read_csv(args.sentinel))
    market = by_site(read_csv(args.market))
    soil_by_site: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in read_csv(args.soil):
        soil_by_site[row["site_id"]].append(row)
    expected = {site["site_id"] for site in sites}
    for label, values in (("source preflight", source_preflight), ("cells", cells), ("weather", weather), ("sentinel", sentinel), ("market", market), ("soil", soil_by_site)):
        if set(values) != expected:
            raise SystemExit(f"{label} artifact site IDs do not exactly match the source-scoped pool.")
    admissions = [
        build_row(site, source_preflight[site["site_id"]], cells[site["site_id"]], weather[site["site_id"]],
                  soil_by_site[site["site_id"]], sentinel[site["site_id"]], market[site["site_id"]])
        for site in sites
    ]
    with args.out.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(admissions)
    admission_by_site = by_site(admissions)
    manifest = [
        build_manifest_row(site, admission_by_site[site["site_id"]], cells[site["site_id"]], market[site["site_id"]], source_preflight[site["site_id"]])
        for site in sites if admission_by_site[site["site_id"]]["admission_status"] == "admitted"
    ]
    with args.manifest_out.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest)
    admitted = sum(row["admission_status"] == "admitted" for row in admissions)
    print(f"Wrote {len(admissions)} admission rows to {args.out}; admitted: {admitted}/{len(admissions)}")
    print(f"Wrote {len(manifest)} frozen final-site rows to {args.manifest_out}")


if __name__ == "__main__":
    main()
