"""Audit the regional operation-plan enrichment without changing frozen data."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_FIELDS = ["check", "expected", "actual", "result", "detail"]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_hash(row: Mapping[str, str], digest_field: str) -> str:
    payload = {field: row.get(field, "") for field in row if field != digest_field}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def audit_row(check: str, expected: int | str, actual: int | str, errors: List[str]) -> Dict[str, str]:
    return {
        "check": check,
        "expected": str(expected),
        "actual": str(actual),
        "result": "pass" if not errors else "fail",
        "detail": "; ".join(errors[:6]) if errors else "validated",
    }


def main() -> None:
    enriched = PROJECT_ROOT / "data/scenarios/enriched"
    scenarios = read_csv(PROJECT_ROOT / "data/scenarios/manifests/scenario_manifest.csv")
    calendar = read_csv(enriched / "regional_calendar_features.csv")
    policy = read_csv(enriched / "management_policy_features.csv")
    actions = read_csv(enriched / "official_action_records_all.csv")
    bindings = read_csv(enriched / "scenario_official_action_bindings_all.csv")
    items = read_csv(enriched / "regional_operation_plan_items.csv")
    summaries = read_csv(enriched / "regional_operation_plan_summary.csv")

    scenario_by_id = {row["scenario_id"]: row for row in scenarios}
    scenario_ids = set(scenario_by_id)
    calendar_by_id = {row["scenario_id"]: row for row in calendar}
    policy_by_id = {row["scenario_id"]: row for row in policy}
    action_by_id = {row["action_id"]: row for row in actions}
    conditional_bindings = {
        (row["scenario_id"], row["action_id"]): row
        for row in bindings
        if row["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition"
    }
    audit: List[Dict[str, str]] = []

    coverage_errors: List[str] = []
    summary_by_id = {row["scenario_id"]: row for row in summaries}
    if len(summary_by_id) != len(summaries) or set(summary_by_id) != scenario_ids:
        coverage_errors.append("summary does not cover every frozen scenario exactly once")
    if len(calendar_by_id) != len(calendar) or set(calendar_by_id) != scenario_ids:
        coverage_errors.append("calendar input does not cover every frozen scenario exactly once")
    if len(policy_by_id) != len(policy) or set(policy_by_id) != scenario_ids:
        coverage_errors.append("policy input does not cover every frozen scenario exactly once")
    audit.append(audit_row("summary_coverage", len(scenarios), len(summaries), coverage_errors))

    baseline_items = [row for row in items if row["plan_item_type"] != "time_valid_source_quoted_conditional_operation"]
    conditional_items = [row for row in items if row["plan_item_type"] == "time_valid_source_quoted_conditional_operation"]
    item_errors: List[str] = []
    if len({row["plan_item_id"] for row in items}) != len(items):
        item_errors.append("plan item IDs are not unique")
    expected_baseline_ids = {
        f"{scenario_id}__calendar_window" for scenario_id in scenario_ids
    } | {
        f"{scenario_id}__fertilizer_policy" for scenario_id in scenario_ids
    } | {
        f"{scenario_id}__protection_policy" for scenario_id in scenario_ids
    }
    actual_baseline_ids = {row["plan_item_id"] for row in baseline_items}
    if actual_baseline_ids != expected_baseline_ids:
        item_errors.append("every scenario must contain exactly the three non-action planning references")
    expected_total = len(expected_baseline_ids) + len(conditional_bindings)
    if len(items) != expected_total:
        item_errors.append("plan-item count does not equal baseline plus conditional binding coverage")
    audit.append(audit_row("plan_item_coverage_and_uniqueness", expected_total, len(items), item_errors))

    baseline_errors: List[str] = []
    for item in baseline_items:
        scenario_id = item["scenario_id"]
        scenario = scenario_by_id.get(scenario_id)
        if scenario is None:
            baseline_errors.append("baseline item references unknown scenario")
            break
        if any(item[field] != scenario[field] for field in ("site_id", "crop", "state", "district", "season", "decision_date")):
            baseline_errors.append(f"{scenario_id}: baseline identity mismatch")
            break
        if item["plan_item_type"] == "declared_season_window_context":
            source = calendar_by_id[scenario_id]
            if item["source_document_id"] != source["crop_season_source_id"] or item["source_binding_status"] != source["calendar_status"]:
                baseline_errors.append(f"{scenario_id}: calendar provenance mismatch")
                break
        elif item["plan_item_type"] == "verified_fertilizer_policy_reference":
            source = policy_by_id[scenario_id]
            if item["source_document_id"] != source["fertilizer_source_id"] or item["source_raw_sha256"] != source["fertilizer_source_sha256"]:
                baseline_errors.append(f"{scenario_id}: fertilizer provenance mismatch")
                break
        elif item["plan_item_type"] == "verified_protection_policy_reference":
            source = policy_by_id[scenario_id]
            if item["source_document_id"] != source["protection_source_id"] or item["source_raw_sha256"] != source["protection_source_sha256"]:
                baseline_errors.append(f"{scenario_id}: protection provenance mismatch")
                break
        else:
            baseline_errors.append(f"{scenario_id}: unknown baseline item type")
            break
    audit.append(audit_row("baseline_reference_provenance", len(baseline_items), len(baseline_items), baseline_errors))

    operation_errors: List[str] = []
    actual_conditional_pairs = {(row["scenario_id"], row["action_id"]): row for row in conditional_items}
    if len(actual_conditional_pairs) != len(conditional_items) or set(actual_conditional_pairs) != set(conditional_bindings):
        operation_errors.append("operation items must equal the existing conditionally applicable bindings exactly")
    for key, item in actual_conditional_pairs.items():
        action = action_by_id.get(item["action_id"])
        binding = conditional_bindings.get(key)
        if action is None or binding is None:
            operation_errors.append(f"{key}: missing action or conditional binding")
            break
        if item["source_raw_sha256"] != action["source_raw_sha256"] or item["source_quote"] != action["source_quote"]:
            operation_errors.append(f"{key}: operation source provenance mismatch")
            break
        if item["source_binding_status"] != binding["binding_status"] or item["missing_evidence"] != binding["binding_reason"]:
            operation_errors.append(f"{key}: field-precondition trace mismatch")
            break
        if item["actionability_status"] != "not_a_direct_farm_action":
            operation_errors.append(f"{key}: unsupported direct action status")
            break
    audit.append(audit_row("conditional_operation_scope_and_provenance", len(conditional_bindings), len(conditional_items), operation_errors))

    hash_errors = []
    for item in items:
        if canonical_hash(item, "plan_item_sha256") != item["plan_item_sha256"]:
            hash_errors.append(f"{item['plan_item_id']}: plan-item hash mismatch")
            break
    for summary in summaries:
        if canonical_hash(summary, "plan_summary_sha256") != summary["plan_summary_sha256"]:
            hash_errors.append(f"{summary['scenario_id']}: summary hash mismatch")
            break
        count = sum(1 for item in conditional_items if item["scenario_id"] == summary["scenario_id"])
        if int(summary["conditional_source_quoted_operation_count"]) != count:
            hash_errors.append(f"{summary['scenario_id']}: conditional operation count mismatch")
            break
        if summary["direct_farm_action_status"] != "not_issued_no_farm_specific_observation_or_treatment_trigger":
            hash_errors.append(f"{summary['scenario_id']}: direct farm action was incorrectly issued")
            break
    audit.append(audit_row("content_hashes_and_direct_action_guard", len(items) + len(summaries), len(items) + len(summaries), hash_errors))

    write_csv(enriched / "regional_operation_plan_audit.csv", AUDIT_FIELDS, audit)
    report = [
        "# Regional Operation Plan Audit\n\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n\n",
        "| Check | Expected | Actual | Result |\n| --- | ---: | ---: | --- |\n",
    ]
    report.extend(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['result']} |\n" for row in audit)
    report.extend([
        "\n## Interpretation\n\n",
        "- Every frozen scenario has one calendar, one regional nutrient-policy, and one regional IPM-policy planning reference.\n",
        "- A source-quoted operation appears only when the pre-existing crop, geography, season, and source-time binding passed; it remains conditional on the recorded missing field precondition.\n",
        "- No plan item is a direct irrigation, fertilizer, pesticide, diagnosis, or other farm-specific action.\n",
    ])
    (enriched / "REGIONAL_OPERATION_PLAN_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failed = [row for row in audit if row["result"] != "pass"]
    print(f"Regional operation-plan audit: {len(audit) - len(failed)}/{len(audit)} checks passed.")
    if failed:
        raise SystemExit("Regional operation-plan audit failed; inspect regional_operation_plan_audit.csv.")


if __name__ == "__main__":
    main()
