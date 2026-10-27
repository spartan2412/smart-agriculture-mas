"""Audit coverage, identifiers, and source hashes in the additive enrichment layer."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_FIELDS = ["layer", "expected_scenarios", "rows", "unique_scenario_ids", "passing_rows", "unavailable_rows", "result", "detail"]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_payload_hash(payload: Mapping[str, object]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def response_bytes_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def row_ids(rows: Sequence[Mapping[str, str]]) -> set[str]:
    return {row["scenario_id"] for row in rows}


def audit_table(name: str, rows: List[Dict[str, str]], expected: set[str], passing, unavailable) -> Dict[str, str]:
    ids = row_ids(rows)
    missing = len(expected - ids)
    extra = len(ids - expected)
    duplicate_count = len(rows) - len(ids)
    result = "pass" if not missing and not extra and not duplicate_count and len(rows) == len(expected) else "fail"
    return {
        "layer": name, "expected_scenarios": str(len(expected)), "rows": str(len(rows)), "unique_scenario_ids": str(len(ids)),
        "passing_rows": str(sum(bool(passing(row)) for row in rows)), "unavailable_rows": str(sum(bool(unavailable(row)) for row in rows)),
        "result": result, "detail": f"missing={missing}; extra={extra}; duplicate_rows={duplicate_count}",
    }


def verify_raw_hashes(rows: Sequence[Mapping[str, str]], root: Path, path_key: str, hash_key: str, predicate) -> List[str]:
    errors: List[str] = []
    for row in rows:
        if not predicate(row):
            continue
        raw_path = root / row[path_key]
        if not raw_path.is_file():
            errors.append(f"{row['scenario_id']}: missing raw payload")
            continue
        if response_bytes_hash(raw_path) != row[hash_key]:
            errors.append(f"{row['scenario_id']}: payload hash mismatch")
    return errors


def verify_semicolon_raw_hashes(rows: Sequence[Mapping[str, str]], root: Path, path_key: str, hash_key: str) -> List[str]:
    errors: List[str] = []
    for row in rows:
        paths = [value for value in row[path_key].split(";") if value]
        hashes = [value for value in row[hash_key].split(";") if value]
        if len(paths) != 3 or len(hashes) != 3:
            errors.append(f"{row['scenario_id']}: expected three raw market responses")
            continue
        for relative, expected_hash in zip(paths, hashes):
            raw_path = root / relative
            if not raw_path.is_file() or response_bytes_hash(raw_path) != expected_hash:
                errors.append(f"{row['scenario_id']}: missing or mismatched prior-market raw response")
                break
    return errors


def main() -> None:
    scenario_root = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenario_root / "enriched"
    expected = row_ids(read_csv(scenario_root / "manifests" / "scenario_manifest.csv"))
    audit_rows: List[Dict[str, str]] = []

    policy = read_csv(enriched / "management_policy_features.csv")
    calendar = read_csv(enriched / "regional_calendar_features.csv")
    audit_rows.append(audit_table("regional_management_policy", policy, expected, lambda _: True, lambda _: False))
    audit_rows.append(audit_table("regional_calendar", calendar, expected, lambda _: True, lambda _: False))

    nasa = read_csv(enriched / "nasa_power_water_context_manifest.csv")
    nasa_hash_errors = verify_raw_hashes(
        nasa, enriched, "raw_path", "response_sha256", lambda row: row["source_status"] == "complete_exact_window_nasa_power_ag_response"
    )
    nasa_audit = audit_table(
        "nasa_power_water_context", nasa, expected,
        lambda row: row["source_status"] == "complete_exact_window_nasa_power_ag_response", lambda row: row["source_status"] != "complete_exact_window_nasa_power_ag_response",
    )
    nasa_audit["result"] = "fail" if nasa_hash_errors else nasa_audit["result"]
    nasa_audit["detail"] += f"; raw_hash_errors={len(nasa_hash_errors)}"
    audit_rows.append(nasa_audit)

    sentinel = read_csv(enriched / "sentinel_ndvi_context_manifest.csv")
    sentinel_hash_errors = verify_raw_hashes(
        sentinel, enriched, "raw_path", "response_sha256", lambda row: row["source_status"] == "exact_frozen_item_and_metadata_quality_verified"
    )
    sentinel_audit = audit_table(
        "sentinel_scene_context", sentinel, expected,
        lambda row: row["source_status"] == "exact_frozen_item_and_metadata_quality_verified", lambda row: row["source_status"] != "exact_frozen_item_and_metadata_quality_verified",
    )
    sentinel_audit["result"] = "fail" if sentinel_hash_errors else sentinel_audit["result"]
    sentinel_features = read_csv(enriched / "sentinel_ndvi_context_features.csv")
    invalid_feature_ids = row_ids(sentinel_features) - expected
    usable_ndvi = sum(row.get("satellite_ndvi", "") != "" for row in sentinel_features)
    sentinel_audit["result"] = "fail" if invalid_feature_ids else sentinel_audit["result"]
    sentinel_audit["detail"] += (
        f"; raw_hash_errors={len(sentinel_hash_errors)}; representative_cell_ndvi_rows={usable_ndvi}; "
        f"invalid_feature_ids={len(invalid_feature_ids)}; unavailable_is_preserved_not_imputed"
    )
    audit_rows.append(sentinel_audit)

    base_sentinel_status = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_context_status.csv")}
    recovery_expected = {
        scenario_id for scenario_id, row in base_sentinel_status.items()
        if not row["satellite_condition_status"].startswith("available")
    }
    sentinel_recovery = read_csv(enriched / "sentinel_ndvi_recovery_manifest.csv")
    recovery_hash_errors = verify_raw_hashes(
        sentinel_recovery, enriched, "item_raw_path", "item_response_sha256",
        lambda row: row["recovery_status"] == "recovered_clear_point_ndvi_from_alternate_frozen_window_candidate",
    )
    recovery_audit = audit_table(
        "sentinel_same_window_recovery", sentinel_recovery, recovery_expected,
        lambda row: row["recovery_status"] == "recovered_clear_point_ndvi_from_alternate_frozen_window_candidate",
        lambda row: row["recovery_status"] == "not_recovered_no_clear_contained_candidate_in_frozen_window",
    )
    recovery_audit["result"] = "fail" if recovery_hash_errors else recovery_audit["result"]
    recovery_audit["detail"] += f"; raw_hash_errors={len(recovery_hash_errors)}; original_frozen_scene_unchanged"
    audit_rows.append(recovery_audit)

    market = read_csv(enriched / "agmarknet_embedded_market_context_manifest.csv")
    source_manifest = {row["scenario_id"]: row for row in read_csv(scenario_root / "manifests" / "scenario_manifest.csv")}
    market_hash_errors = []
    for row in market:
        scenario = source_manifest[row["scenario_id"]]
        raw_path = scenario_root / scenario["market_raw_path"]
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        if canonical_payload_hash(payload) != row["verified_payload_sha256"]:
            market_hash_errors.append(row["scenario_id"])
    market_audit = audit_table(
        "agmarknet_embedded_market_context", market, expected,
        lambda row: row["source_status"] == "complete_frozen_official_report_context",
        lambda row: row["source_status"] == "no_comparator_in_frozen_official_report",
    )
    market_audit["result"] = "fail" if market_hash_errors else market_audit["result"]
    market_audit["detail"] += f"; raw_hash_errors={len(market_hash_errors)}; unavailable_reports={market_audit['unavailable_rows']}"
    audit_rows.append(market_audit)

    market_status = {row["scenario_id"]: row for row in read_csv(enriched / "agmarknet_embedded_market_context_status.csv")}
    market_recovery_expected = {
        scenario_id for scenario_id, row in market_status.items()
        if row["market_context_status"] == "unavailable_no_source_comparator"
    }
    market_recovery = read_csv(enriched / "market_recovery_feasibility.csv")
    market_recovery_hash_errors = verify_semicolon_raw_hashes(
        market_recovery, enriched, "prior_report_raw_paths", "prior_report_sha256s"
    )
    market_recovery_audit = audit_table(
        "agmarknet_strict_recovery_feasibility", market_recovery, market_recovery_expected,
        lambda row: row["recovery_feasibility_status"] == "possible_two_or_more_strict_prior_prices",
        lambda row: row["recovery_feasibility_status"] == "confirmed_no_strict_prior_price_in_exact_source_months",
    )
    market_recovery_audit["result"] = "fail" if market_recovery_hash_errors else market_recovery_audit["result"]
    market_recovery_audit["detail"] += f"; raw_hash_errors={len(market_recovery_hash_errors)}; no_nearby_mandi_or_cross_district_substitution"
    audit_rows.append(market_recovery_audit)

    contract = read_csv(enriched / "mas_enrichment_contract.csv")
    contract_audit = audit_table(
        "mas_enrichment_contract", contract, expected,
        lambda row: row["mas_output_rule"] == "context_explanation_and_evidence_trace_only_no_direct_farm_action",
        lambda _: False,
    )
    contract_errors = [
        row["scenario_id"] for row in contract
        if row["irrigation_action_agent"] != "abstain_no_field_moisture_or_decision_time_forecast"
        or row["fertilizer_prescription_agent"] != "abstain_no_field_soil_test_or_actual_crop_stage"
        or row["pesticide_treatment_agent"] != "abstain_no_dated_diagnosis_or_threshold_event"
        or row["leaf_vision_agent"] != "abstain_no_aligned_field_leaf_image"
    ]
    contract_audit["result"] = "fail" if contract_errors else contract_audit["result"]
    contract_audit["detail"] += f"; prohibited_direct_action_rows={len(contract_errors)}"
    audit_rows.append(contract_audit)

    write_csv(enriched / "enrichment_audit.csv", AUDIT_FIELDS, audit_rows)
    failed = [row for row in audit_rows if row["result"] != "pass"]
    report = [
        "# Enrichment Audit\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n",
        "This audit checks row identity and source hashes in the additive enrichment layer. An `unavailable` count is not a failure when the source absence is preserved and no value is imputed.\n",
        "| Layer | Passing | Unavailable | Audit result |\n| --- | ---: | ---: | --- |",
    ]
    report.extend(f"| {row['layer']} | {row['passing_rows']} | {row['unavailable_rows']} | {row['result']} |" for row in audit_rows)
    report.append("\n## Interpretation\n")
    report.append("- NASA POWER: all passing records have exact-window raw-response hashes.\n")
    report.append("- Sentinel: a metadata-verified scene is distinct from a usable NDVI pixel. Recovery may use only a clear candidate already present in the original frozen same-month search response; it never overwrites the original selected item.\n")
    report.append("- Agmarknet: historical comparisons come only from columns in the exact frozen official report. The strict recovery check queries only the three earlier same-crop/district months; a missing comparator produces an abstention, not an estimated price.\n")
    report.append("- MAS contract: direct irrigation, fertilizer, pesticide treatment, and leaf-vision actions remain abstentions for every scenario.\n")
    (enriched / "ENRICHMENT_AUDIT.md").write_text("\n".join(report).rstrip() + "\n", encoding="utf-8")
    print(f"Enrichment audit: {len(audit_rows) - len(failed)}/{len(audit_rows)} layers passed.")
    if failed:
        raise SystemExit("Enrichment audit failure; inspect enrichment_audit.csv.")


if __name__ == "__main__":
    main()
