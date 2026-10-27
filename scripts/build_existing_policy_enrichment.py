"""Build the first, non-network enrichment layer for IndiaAgriAlignBench.

This script never changes the frozen registry or scenario artifacts.  It makes
scenario-level records from evidence already admitted to the benchmark:

* the exact crop-season source and documented seasonal-window position;
* the final fertilizer and crop-protection policy sources, locators, hashes,
  regulatory cross-checks, and conditions; and
* explicit actionability limits.

It deliberately does *not* infer a farm crop stage, a field soil-test result,
a pest diagnosis, an ETL crossing, or a farm treatment.  Those facts are not
present in the public-data benchmark and must remain unavailable.

The older ``regional_management_policy.csv`` is intentionally not an input.
It was built for an earlier site pool, whereas this script uses only the six
final management bundles named by the frozen scenario manifests.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONTHS = {name.casefold(): index for index, name in enumerate(calendar.month_abbr) if name}

CALENDAR_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date",
    "season_window", "season_month_index", "season_month_count", "season_window_position",
    "calendar_status", "crop_stage_status", "crop_season_source_id", "crop_season_locator",
    "crop_profile_url", "crop_profile_sha256", "sowing_window_url", "sowing_window_sha256",
    "calendar_interpretation",
]

POLICY_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date",
    "management_bundle_id", "conditions_and_exclusions",
    "fertilizer_source_id", "fertilizer_locator", "fertilizer_source_title",
    "fertilizer_source_provider", "fertilizer_source_scope", "fertilizer_source_url",
    "fertilizer_source_issue_date", "fertilizer_source_sha256", "fertilizer_source_status",
    "fertilizer_verification_status", "fertilizer_actionability", "farm_fertilizer_status",
    "protection_source_id", "protection_locator", "protection_source_title",
    "protection_source_provider", "protection_source_scope", "protection_source_url",
    "protection_source_issue_date", "protection_source_sha256", "protection_source_status",
    "protection_verification_status", "ppqs_source_ids", "ppqs_source_urls", "ppqs_source_sha256s",
    "ppqs_source_statuses", "ppqs_locator", "dose_alignment_status", "protection_actionability",
    "crop_protection_status", "policy_interpretation",
]

STATUS_FIELDS = [
    "scenario_id", "calendar_enrichment_status", "fertilizer_policy_enrichment_status",
    "protection_policy_enrichment_status", "management_temporal_interpretation",
    "blocking_reason", "enrichment_ready_status",
]

PROVENANCE_FIELDS = [
    "generated_at_utc", "artifact_role", "input_path", "input_sha256", "input_row_count",
    "notes",
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


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def month_sequence(window: str) -> List[int]:
    try:
        start_name, end_name = (part.strip().casefold() for part in window.split("-", maxsplit=1))
        start, end = MONTHS[start_name], MONTHS[end_name]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid declared season window: {window!r}") from exc
    values = [start]
    while values[-1] != end:
        values.append(1 if values[-1] == 12 else values[-1] + 1)
    return values


def season_position(index: int, count: int) -> str:
    """Return a calendar-window position, never an observed crop stage."""
    if not 1 <= index <= count:
        raise ValueError("Season position index falls outside its declared window.")
    if index <= (count + 2) // 3:
        return "early_declared_season_window"
    if index > (2 * count) // 3:
        return "late_declared_season_window"
    return "middle_declared_season_window"


def split_source_ids(value: str) -> List[str]:
    return [source_id.strip() for source_id in value.split(";") if source_id.strip()]


def require_source(source_id: str, source_by_id: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    source = source_by_id.get(source_id)
    if source is None:
        raise ValueError(f"Management source {source_id!r} is absent from the final source snapshot.")
    if source.get("source_status") != "dated_source_semantics_verified":
        raise ValueError(f"Management source {source_id!r} is not verified: {source.get('source_status')!r}.")
    return source


def source_values(source_ids: Sequence[str], source_by_id: Mapping[str, Mapping[str, str]], field: str) -> str:
    return ";".join(str(require_source(source_id, source_by_id).get(field, "")) for source_id in source_ids)


def build_rows(
    manifests: Sequence[Mapping[str, str]],
    evidence_by_id: Mapping[str, Mapping[str, str]],
    bundles_by_id: Mapping[str, Mapping[str, str]],
    sources_by_id: Mapping[str, Mapping[str, str]],
    crop_season_by_site: Mapping[str, Mapping[str, str]],
) -> tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    calendar_rows: List[Dict[str, str]] = []
    policy_rows: List[Dict[str, str]] = []
    status_rows: List[Dict[str, str]] = []

    for scenario in manifests:
        scenario_id = scenario["scenario_id"]
        evidence = evidence_by_id.get(scenario_id)
        if evidence is None:
            raise ValueError(f"Scenario evidence is absent for {scenario_id}.")
        bundle = bundles_by_id.get(scenario["management_bundle_id"])
        if bundle is None:
            raise ValueError(f"Scenario {scenario_id} references a missing management bundle.")
        if bundle["crop"] != scenario["crop"] or scenario["season"] != bundle["season"]:
            raise ValueError(f"Management bundle crop/season mismatch for {scenario_id}.")
        if scenario["state"] not in bundle["states"].split(";"):
            raise ValueError(f"Management bundle state scope mismatch for {scenario_id}.")
        if evidence["fertilizer_source_id"] != bundle["fertilizer_source_id"]:
            raise ValueError(f"Fertilizer-source mismatch for {scenario_id}.")
        if evidence["protection_source_id"] != bundle["protection_source_id"]:
            raise ValueError(f"Protection-source mismatch for {scenario_id}.")

        fertilizer_source = require_source(bundle["fertilizer_source_id"], sources_by_id)
        protection_source = require_source(bundle["protection_source_id"], sources_by_id)
        ppqs_ids = split_source_ids(bundle["ppqs_source_id"])
        for ppqs_id in ppqs_ids:
            require_source(ppqs_id, sources_by_id)

        crop_season = crop_season_by_site.get(scenario["site_id"])
        if crop_season is None:
            raise ValueError(f"Crop-season evidence is absent for {scenario_id}.")
        if crop_season["crop"] != scenario["crop"]:
            raise ValueError(f"Crop-season evidence crop mismatch for {scenario_id}.")

        months = month_sequence(scenario["season_window"])
        decision_month = int(scenario["decision_date"][5:7])
        if decision_month not in months:
            raise ValueError(f"Scenario decision month falls outside declared season for {scenario_id}.")
        month_index = months.index(decision_month) + 1
        window_position = season_position(month_index, len(months))

        calendar_rows.append({
            "scenario_id": scenario_id,
            "site_id": scenario["site_id"],
            "crop": scenario["crop"],
            "state": scenario["state"],
            "district": scenario["district"],
            "season": scenario["season"],
            "decision_date": scenario["decision_date"],
            "season_window": scenario["season_window"],
            "season_month_index": str(month_index),
            "season_month_count": str(len(months)),
            "season_window_position": window_position,
            "calendar_status": "declared_season_window_position_available_not_field_phenology",
            "crop_stage_status": evidence["crop_stage_status"],
            "crop_season_source_id": bundle["crop_season_source_id"],
            "crop_season_locator": bundle["crop_season_locator"],
            "crop_profile_url": crop_season["crop_profile_url"],
            "crop_profile_sha256": crop_season["crop_profile_sha256"],
            "sowing_window_url": crop_season["sowing_window_url"],
            "sowing_window_sha256": crop_season["sowing_window_sha256"],
            "calendar_interpretation": (
                "The position is derived only from the declared district-scale season window and decision month. "
                "It is not an observed sowing date or field phenology stage."
            ),
        })

        policy_rows.append({
            "scenario_id": scenario_id,
            "site_id": scenario["site_id"],
            "crop": scenario["crop"],
            "state": scenario["state"],
            "district": scenario["district"],
            "season": scenario["season"],
            "decision_date": scenario["decision_date"],
            "management_bundle_id": bundle["management_bundle_id"],
            "conditions_and_exclusions": bundle["conditions_and_exclusions"],
            "fertilizer_source_id": bundle["fertilizer_source_id"],
            "fertilizer_locator": bundle["fertilizer_locator"],
            "fertilizer_source_title": fertilizer_source["source_title"],
            "fertilizer_source_provider": fertilizer_source["provider"],
            "fertilizer_source_scope": fertilizer_source["geography_scope"],
            "fertilizer_source_url": fertilizer_source["official_url"],
            "fertilizer_source_issue_date": fertilizer_source["expected_issue_date"],
            "fertilizer_source_sha256": fertilizer_source["sha256"],
            "fertilizer_source_status": fertilizer_source["source_status"],
            "fertilizer_verification_status": bundle["fertilizer_verification_status"],
            "fertilizer_actionability": "regional_policy_reference_only_field_soil_test_and_actual_stage_required",
            "farm_fertilizer_status": evidence["farm_fertilizer_status"],
            "protection_source_id": bundle["protection_source_id"],
            "protection_locator": bundle["protection_locator"],
            "protection_source_title": protection_source["source_title"],
            "protection_source_provider": protection_source["provider"],
            "protection_source_scope": protection_source["geography_scope"],
            "protection_source_url": protection_source["official_url"],
            "protection_source_issue_date": protection_source["expected_issue_date"],
            "protection_source_sha256": protection_source["sha256"],
            "protection_source_status": protection_source["source_status"],
            "protection_verification_status": bundle["protection_verification_status"],
            "ppqs_source_ids": bundle["ppqs_source_id"],
            "ppqs_source_urls": source_values(ppqs_ids, sources_by_id, "official_url"),
            "ppqs_source_sha256s": source_values(ppqs_ids, sources_by_id, "sha256"),
            "ppqs_source_statuses": source_values(ppqs_ids, sources_by_id, "source_status"),
            "ppqs_locator": bundle["ppqs_locator"],
            "dose_alignment_status": bundle["dose_alignment_status"],
            "protection_actionability": "conditional_IPM_policy_only_diagnosis_or_threshold_event_required",
            "crop_protection_status": evidence["crop_protection_status"],
            "policy_interpretation": (
                "Verified crop-region policy and PPQS compatibility evidence are available. These are "
                "contextual references, not proof of a dated field diagnosis, threshold crossing, or treatment need."
            ),
        })

        status_rows.append({
            "scenario_id": scenario_id,
            "calendar_enrichment_status": "pass_declared_window_position_only",
            "fertilizer_policy_enrichment_status": "pass_verified_regional_policy_reference",
            "protection_policy_enrichment_status": "pass_verified_conditional_IPM_policy_reference",
            "management_temporal_interpretation": "reference_policy_not_a_historical_or_farm_specific_prescription",
            "blocking_reason": (
                "field_phenology_soil_test_and_diagnosis_or_threshold_event_are_not_observed"
            ),
            "enrichment_ready_status": "ready_for_contextual_policy_use_with_required_restrictions",
        })

    return calendar_rows, policy_rows, status_rows


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Build immutable existing-policy enrichment for all frozen scenarios.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--evidence", type=Path, default=scenarios / "evidence" / "scenario_evidence_status.csv")
    parser.add_argument("--bundles", type=Path, default=registry / "preflight_management_bundle_catalog.csv")
    parser.add_argument("--sources", type=Path, default=registry / "regional_management_source_snapshot.csv")
    parser.add_argument("--crop-season", type=Path, default=registry / "preflight_icar_crida_ccp_coverage.csv")
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    args = parser.parse_args()

    manifests = read_csv(args.manifest)
    evidence = read_csv(args.evidence)
    bundles = read_csv(args.bundles)
    sources = read_csv(args.sources)
    crop_season = read_csv(args.crop_season)
    if not manifests:
        raise SystemExit("The scenario manifest is empty.")
    evidence_by_id = {row["scenario_id"]: row for row in evidence}
    if len(evidence_by_id) != len(evidence) or set(evidence_by_id) != {row["scenario_id"] for row in manifests}:
        raise SystemExit("Scenario manifest and evidence identifiers must be unique and exactly equal.")
    bundles_by_id = {row["management_bundle_id"]: row for row in bundles}
    sources_by_id = {row["source_document_id"]: row for row in sources}
    crop_season_by_site = {row["site_id"]: row for row in crop_season}
    if len(crop_season_by_site) != len(crop_season):
        raise SystemExit("Crop-season evidence contains duplicate site identifiers.")

    calendar_rows, policy_rows, status_rows = build_rows(
        manifests, evidence_by_id, bundles_by_id, sources_by_id, crop_season_by_site
    )
    if not (len(calendar_rows) == len(policy_rows) == len(status_rows) == len(manifests)):
        raise SystemExit("Enrichment output row count does not equal the frozen manifest row count.")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "regional_calendar_features.csv", CALENDAR_FIELDS, calendar_rows)
    write_csv(args.out_dir / "management_policy_features.csv", POLICY_FIELDS, policy_rows)
    write_csv(args.out_dir / "enrichment_evidence_status.csv", STATUS_FIELDS, status_rows)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    provenance_rows = [
        {
            "generated_at_utc": generated_at,
            "artifact_role": label,
            "input_path": str(path.relative_to(PROJECT_ROOT)),
            "input_sha256": file_sha256(path),
            "input_row_count": str(len(rows)),
            "notes": note,
        }
        for label, path, rows, note in (
            ("frozen_scenario_manifest", args.manifest, manifests, "Immutable scenario identity and source linkage."),
            ("frozen_scenario_evidence", args.evidence, evidence, "Mandatory abstentions and policy references."),
            ("final_management_bundles", args.bundles, bundles, "Final crop-state-season management source bindings."),
            ("verified_management_sources", args.sources, sources, "Official source metadata and frozen source hashes."),
            ("crop_season_evidence", args.crop_season, crop_season, "Official crop profile and sowing-window references."),
        )
    ]
    write_csv(args.out_dir / "enrichment_provenance.csv", PROVENANCE_FIELDS, provenance_rows)
    print(f"Wrote contextual policy enrichment for {len(manifests)}/{len(manifests)} frozen scenarios to {args.out_dir}.")


if __name__ == "__main__":
    main()
