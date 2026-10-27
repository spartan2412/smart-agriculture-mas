"""Audit the evidence-first, source-scoped replacement pool.

This is intentionally *not* a final-site admission script.  It proves only
the gates whose evidence is already fixed without selecting a fake crop point:
crop/season, historical same-district market, and crop- and region-compatible
fertilizer/protection bundles.  Location, weather, soil, and Sentinel gates
remain visible blockers until they are collected at a documented crop cell.

Run from the repository root:

    python scripts/build_source_scoped_preflight_audit.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
from typing import Dict, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERIFIED_SOURCE_STATUS = "dated_source_semantics_verified"
FERTILIZER_STATUS = "regional_baseline_source_verified"
PROTECTION_STATUS = "regional_trigger_and_PPQS_match_verified"
CCP_PROFILE_STATUS = "historical_official_crop_profile_keyword_found"
CCP_SOWING_STATUS = "historical_official_sowing_window_keyword_found"
MARKET_STATUS = "same_crop_historical_district_market_report_available"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def by_site(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {row["site_id"]: row for row in rows}


def split_ids(value: str) -> List[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def source_verified(source_ids: Iterable[str], source_snapshot: Dict[str, Dict[str, str]]) -> bool:
    return all(
        source_id in source_snapshot
        and source_snapshot[source_id].get("source_status") == VERIFIED_SOURCE_STATUS
        for source_id in source_ids
    )


def find_bundle(site: Dict[str, str], bundles: Iterable[Dict[str, str]]) -> Dict[str, str] | None:
    matches = []
    for bundle in bundles:
        states = {normalise(value) for value in split_ids(bundle["states"])}
        if (
            bundle["crop"].casefold() == site["crop"].casefold()
            and normalise(site["state"]) in states
            and bundle["season"].casefold() == site["proposed_season"].casefold()
        ):
            matches.append(bundle)
    return matches[0] if len(matches) == 1 else None


def gate(value: bool) -> str:
    return "pass" if value else "fail"


OUTPUT_FIELDS = [
    "site_id", "crop", "state", "district", "management_bundle_id",
    "crop_season_gate", "historical_market_gate", "fertilizer_policy_gate",
    "protection_policy_gate", "management_provenance_gate", "candidate_location_gate",
    "fixed_decision_window_gate", "weather_gate", "soil_gate", "satellite_gate",
    "preflight_status", "blocking_gates", "interpretation",
]


def build_row(
    site: Dict[str, str],
    ccp: Dict[str, str],
    market: Dict[str, str],
    bundles: Iterable[Dict[str, str]],
    source_snapshot: Dict[str, Dict[str, str]],
) -> Dict[str, str]:
    bundle = find_bundle(site, bundles)
    bundle_id = bundle["management_bundle_id"] if bundle else "NONE"
    expected_fertilizer = bundle["fertilizer_source_id"] if bundle else ""
    expected_protection = bundle["protection_source_id"] if bundle else ""
    expected_ppqs = split_ids(bundle["ppqs_source_id"]) if bundle else []
    source_ids_match = bool(bundle) and (
        site["management_fertilizer_source_id"] == expected_fertilizer
        and site["management_protection_source_id"] == expected_protection
    )
    source_dates_ok = bool(bundle) and source_verified(
        [expected_fertilizer, expected_protection, *expected_ppqs], source_snapshot
    )
    if bundle and bundle["crop_season_source_id"] == "ICAR_CRIDA_CCP":
        crop_season_ok = (
            ccp.get("crop_presence_status") == CCP_PROFILE_STATUS
            and ccp.get("sowing_window_status") == CCP_SOWING_STATUS
        )
    elif bundle:
        crop_season_ok = source_verified([bundle["crop_season_source_id"]], source_snapshot)
    else:
        crop_season_ok = False
    fertilizer_ok = bool(bundle) and (
        bundle["fertilizer_verification_status"] == FERTILIZER_STATUS
        and source_verified([expected_fertilizer], source_snapshot)
    )
    protection_ok = bool(bundle) and (
        bundle["protection_verification_status"] == PROTECTION_STATUS
        and source_verified([expected_protection, *expected_ppqs], source_snapshot)
    )
    market_ok = market.get("historical_market_status") == MARKET_STATUS
    provenance_ok = source_ids_match and source_dates_ok
    gates = {
        "crop_season_gate": gate(crop_season_ok),
        "historical_market_gate": gate(market_ok),
        "fertilizer_policy_gate": gate(fertilizer_ok),
        "protection_policy_gate": gate(protection_ok),
        "management_provenance_gate": gate(provenance_ok),
        # These are deliberately not inferred from a district boundary or a
        # current response.  The next collector supplies them at the selected
        # documented representative crop cell and fixed decision window.
        "candidate_location_gate": "not_started",
        "fixed_decision_window_gate": "not_started",
        "weather_gate": "not_started",
        "soil_gate": "not_started",
        "satellite_gate": "not_started",
    }
    blockers = [name for name, status in gates.items() if status != "pass"]
    prerequisite_gates = (
        "crop_season_gate", "historical_market_gate", "fertilizer_policy_gate",
        "protection_policy_gate", "management_provenance_gate",
    )
    source_preflight_passed = all(gates[name] == "pass" for name in prerequisite_gates)
    return {
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"],
        "district": site["district"],
        "management_bundle_id": bundle_id,
        **gates,
        "preflight_status": (
            "ready_for_documented_location_window_preflight"
            if source_preflight_passed
            else "rejected_or_incomplete_source_preflight"
        ),
        "blocking_gates": ";".join(blockers) if blockers else "NONE",
        "interpretation": (
            "All source-scoped prerequisite gates pass; this remains a candidate until a documented crop location and co-located time-window evidence pass."
            if source_preflight_passed
            else "Do not promote this row: at least one source-scoped prerequisite gate failed."
        ),
    }


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    parser = argparse.ArgumentParser(description="Build the evidence-first source-scoped preflight audit.")
    parser.add_argument("--sites", type=Path, default=registry / "source_scoped_preflight_pool.csv")
    parser.add_argument("--ccp", type=Path, default=registry / "preflight_icar_crida_ccp_coverage.csv")
    parser.add_argument("--market", type=Path, default=registry / "preflight_agmarknet_historical_market_coverage.csv")
    parser.add_argument("--bundles", type=Path, default=registry / "preflight_management_bundle_catalog.csv")
    parser.add_argument("--sources", type=Path, default=registry / "regional_management_source_snapshot.csv")
    parser.add_argument("--out", type=Path, default=registry / "source_scoped_preflight_audit.csv")
    args = parser.parse_args()

    sites = read_csv(args.sites)
    ccp = by_site(read_csv(args.ccp))
    market = by_site(read_csv(args.market))
    bundles = read_csv(args.bundles)
    source_snapshot = {
        row["source_document_id"]: row for row in read_csv(args.sources)
    }
    site_ids = {site["site_id"] for site in sites}
    if set(ccp) != site_ids or set(market) != site_ids:
        raise SystemExit("Preflight CCP and historical-market artifacts must exactly match the source-scoped pool.")
    rows = [build_row(site, ccp[site["site_id"]], market[site["site_id"]], bundles, source_snapshot) for site in sites]
    with args.out.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    ready = sum(row["preflight_status"] == "ready_for_documented_location_window_preflight" for row in rows)
    print(f"Wrote {len(rows)} rows to {args.out}; source-scoped prerequisite gates passed: {ready}/{len(rows)}")


if __name__ == "__main__":
    main()
