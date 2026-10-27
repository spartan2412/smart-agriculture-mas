"""Build a source-linked regional operation-plan enrichment for frozen scenarios.

The result is deliberately a *regional planning* layer, not a farm-action
layer.  Every scenario receives three source-linked planning references:

* its declared district-scale crop-season-window position;
* its verified regional nutrient-policy reference; and
* its verified regional IPM-policy reference.

Only an already source-quoted operation whose existing scenario binding is
time-, crop-, geography-, and season-valid is added as a conditional operation
item.  The script never promotes an operation to a direct farm action and does
not infer crop stage, soil-test results, diagnosis, threshold, weather
forecast, or farming system.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ITEM_FIELDS = [
    "plan_item_id", "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date",
    "display_order", "plan_lane", "plan_item_type", "item_status", "actionability_status",
    "farmer_visible_label", "farmer_visible_text", "operation_text", "method_text", "dose_text",
    "conditions_text", "missing_evidence", "source_temporal_interpretation", "source_document_id",
    "source_title", "source_provider", "source_url", "source_raw_sha256", "source_location",
    "source_quote", "source_binding_status", "action_id", "action_record_sha256", "plan_item_sha256",
]

SUMMARY_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date", "season_window",
    "season_window_position", "plan_status", "conditional_source_quoted_operation_count",
    "conditional_action_ids", "regional_reference_item_count", "total_plan_item_count", "plan_summary",
    "direct_farm_action_status", "plan_summary_sha256",
]

PROVENANCE_FIELDS = [
    "generated_at_utc", "artifact_role", "input_path", "input_sha256", "input_row_count", "notes",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(row: Mapping[str, str], digest_field: str) -> str:
    payload = {field: row.get(field, "") for field in row if field != digest_field}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def require_exact_ids(
    rows: Sequence[Mapping[str, str]], expected_ids: set[str], label: str
) -> Dict[str, Mapping[str, str]]:
    by_id = {row["scenario_id"]: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != expected_ids:
        raise SystemExit(f"{label} must contain each frozen scenario exactly once.")
    return by_id


def display_position(value: str) -> str:
    return value.replace("_declared_season_window", "").replace("_", " ")


def calendar_item(calendar: Mapping[str, str]) -> Dict[str, str]:
    is_crida = calendar["crop_season_source_id"] == "ICAR_CRIDA_CCP"
    return {
        "plan_item_id": f"{calendar['scenario_id']}__calendar_window",
        "scenario_id": calendar["scenario_id"],
        "site_id": calendar["site_id"],
        "crop": calendar["crop"],
        "state": calendar["state"],
        "district": calendar["district"],
        "season": calendar["season"],
        "decision_date": calendar["decision_date"],
        "display_order": "1",
        "plan_lane": "regional_calendar",
        "plan_item_type": "declared_season_window_context",
        "item_status": "available_regional_planning_context",
        "actionability_status": "regional_planning_context_not_observed_field_stage",
        "farmer_visible_label": "Regional seasonal planning window",
        "farmer_visible_text": (
            f"The declared {calendar['season']} window for this crop and district is {calendar['season_window']}; "
            f"the scenario date falls in the {display_position(calendar['season_window_position'])} part of that window."
        ),
        "operation_text": "",
        "method_text": "",
        "dose_text": "",
        "conditions_text": calendar["calendar_interpretation"],
        "missing_evidence": "actual_crop_stage_not_observed",
        "source_temporal_interpretation": "declared_calendar_window_context_not_a_dated_field_advisory",
        "source_document_id": calendar["crop_season_source_id"],
        "source_title": (
            "District crop profile and sowing-window evidence"
            if is_crida else "ICAR Rabi agro-advisory crop-season evidence"
        ),
        "source_provider": "ICAR-CRIDA" if is_crida else "Indian Council of Agricultural Research",
        "source_url": ";".join(value for value in (calendar["crop_profile_url"], calendar["sowing_window_url"]) if value),
        "source_raw_sha256": ";".join(value for value in (calendar["crop_profile_sha256"], calendar["sowing_window_sha256"]) if value and value != "NONE"),
        "source_location": calendar["crop_season_locator"],
        "source_quote": "",
        "source_binding_status": calendar["calendar_status"],
        "action_id": "",
        "action_record_sha256": "",
    }


def policy_item(policy: Mapping[str, str], kind: str, display_order: int) -> Dict[str, str]:
    if kind == "fertilizer":
        prefix, label, lane = "fertilizer", "Regional nutrient planning reference", "regional_nutrient_policy"
        restriction = policy["fertilizer_actionability"]
        missing = "actual_crop_stage_and_field_soil_test_not_observed"
    elif kind == "protection":
        prefix, label, lane = "protection", "Regional IPM planning reference", "regional_crop_protection_policy"
        restriction = policy["protection_actionability"]
        missing = "dated_diagnosis_or_threshold_event_not_observed"
    else:
        raise ValueError(f"Unsupported policy kind: {kind}")
    return {
        "plan_item_id": f"{policy['scenario_id']}__{prefix}_policy",
        "scenario_id": policy["scenario_id"],
        "site_id": policy["site_id"],
        "crop": policy["crop"],
        "state": policy["state"],
        "district": policy["district"],
        "season": policy["season"],
        "decision_date": policy["decision_date"],
        "display_order": str(display_order),
        "plan_lane": lane,
        "plan_item_type": f"verified_{prefix}_policy_reference",
        "item_status": "available_regional_policy_reference",
        "actionability_status": restriction,
        "farmer_visible_label": label,
        "farmer_visible_text": (
            f"Use the cited {policy['state']} {policy['crop']} regional {prefix} source as a planning reference. "
            "The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order."
        ),
        "operation_text": "",
        "method_text": "",
        "dose_text": "",
        "conditions_text": policy["conditions_and_exclusions"],
        "missing_evidence": missing,
        "source_temporal_interpretation": "verified_regional_policy_reference_not_reclassified_as_a_dated_farm_advisory",
        "source_document_id": policy[f"{prefix}_source_id"],
        "source_title": policy[f"{prefix}_source_title"],
        "source_provider": policy[f"{prefix}_source_provider"],
        "source_url": policy[f"{prefix}_source_url"],
        "source_raw_sha256": policy[f"{prefix}_source_sha256"],
        "source_location": policy[f"{prefix}_locator"],
        "source_quote": "",
        "source_binding_status": policy[f"{prefix}_verification_status"],
        "action_id": "",
        "action_record_sha256": "",
    }


def conditional_operation_item(
    scenario: Mapping[str, str], action: Mapping[str, str], binding: Mapping[str, str], display_order: int
) -> Dict[str, str]:
    return {
        "plan_item_id": f"{scenario['scenario_id']}__operation__{action['action_id']}",
        "scenario_id": scenario["scenario_id"],
        "site_id": scenario["site_id"],
        "crop": scenario["crop"],
        "state": scenario["state"],
        "district": scenario["district"],
        "season": scenario["season"],
        "decision_date": scenario["decision_date"],
        "display_order": str(display_order),
        "plan_lane": "source_quoted_operation",
        "plan_item_type": "time_valid_source_quoted_conditional_operation",
        "item_status": "conditional_operation_pending_unobserved_field_precondition",
        "actionability_status": "not_a_direct_farm_action",
        "farmer_visible_label": "Official conditional operation",
        "farmer_visible_text": action["operation_text"],
        "operation_text": action["operation_text"],
        "method_text": action["method_text"],
        "dose_text": action["dose_text"],
        "conditions_text": action["conditions_text"],
        "missing_evidence": binding["binding_reason"],
        "source_temporal_interpretation": "source_time_crop_geography_and_season_scope_passed; field_precondition_not_observed",
        "source_document_id": action["source_document_id"],
        "source_title": action["source_title"],
        "source_provider": action["provider"],
        "source_url": action["official_url"],
        "source_raw_sha256": action["source_raw_sha256"],
        "source_location": action["source_location"],
        "source_quote": action["source_quote"],
        "source_binding_status": binding["binding_status"],
        "action_id": action["action_id"],
        "action_record_sha256": action["action_record_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build source-linked regional operation planning artifacts.")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data/scenarios/manifests/scenario_manifest.csv")
    parser.add_argument("--calendar", type=Path, default=PROJECT_ROOT / "data/scenarios/enriched/regional_calendar_features.csv")
    parser.add_argument("--policy", type=Path, default=PROJECT_ROOT / "data/scenarios/enriched/management_policy_features.csv")
    parser.add_argument("--actions", type=Path, default=PROJECT_ROOT / "data/scenarios/enriched/official_action_records_all.csv")
    parser.add_argument("--bindings", type=Path, default=PROJECT_ROOT / "data/scenarios/enriched/scenario_official_action_bindings_all.csv")
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "data/scenarios/enriched")
    args = parser.parse_args()

    scenarios = read_csv(args.manifest)
    if not scenarios:
        raise SystemExit("Frozen scenario manifest is empty.")
    scenario_by_id = {row["scenario_id"]: row for row in scenarios}
    if len(scenario_by_id) != len(scenarios):
        raise SystemExit("Frozen scenario manifest has duplicate scenario IDs.")
    scenario_ids = set(scenario_by_id)
    calendar_by_id = require_exact_ids(read_csv(args.calendar), scenario_ids, "Calendar enrichment")
    policy_by_id = require_exact_ids(read_csv(args.policy), scenario_ids, "Policy enrichment")

    actions = read_csv(args.actions)
    action_by_id = {row["action_id"]: row for row in actions}
    if len(action_by_id) != len(actions):
        raise SystemExit("Official action records contain duplicate action IDs.")
    bindings = read_csv(args.bindings)
    expected_pairs = {(scenario_id, action_id) for scenario_id in scenario_ids for action_id in action_by_id}
    binding_by_pair = {(row["scenario_id"], row["action_id"]): row for row in bindings}
    if len(binding_by_pair) != len(bindings) or set(binding_by_pair) != expected_pairs:
        raise SystemExit("Official action bindings do not provide unique full scenario-action coverage.")

    conditionals_by_scenario: Dict[str, List[tuple[Mapping[str, str], Mapping[str, str]]]] = defaultdict(list)
    for (scenario_id, action_id), binding in binding_by_pair.items():
        if binding["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition":
            conditionals_by_scenario[scenario_id].append((action_by_id[action_id], binding))

    plan_items: List[Dict[str, str]] = []
    summaries: List[Dict[str, str]] = []
    for scenario_id in sorted(scenario_ids):
        scenario = scenario_by_id[scenario_id]
        calendar = calendar_by_id[scenario_id]
        policy = policy_by_id[scenario_id]
        if any(calendar[field] != scenario[field] for field in ("site_id", "crop", "state", "district", "season", "decision_date")):
            raise SystemExit(f"Calendar alignment mismatch for {scenario_id}.")
        if any(policy[field] != scenario[field] for field in ("site_id", "crop", "state", "district", "season", "decision_date")):
            raise SystemExit(f"Policy alignment mismatch for {scenario_id}.")

        conditional_pairs = sorted(conditionals_by_scenario[scenario_id], key=lambda pair: pair[0]["action_id"])
        scenario_items = [calendar_item(calendar)]
        for order, (action, binding) in enumerate(conditional_pairs, start=2):
            scenario_items.append(conditional_operation_item(scenario, action, binding, order))
        scenario_items.extend((
            policy_item(policy, "fertilizer", len(scenario_items) + 1),
            policy_item(policy, "protection", len(scenario_items) + 2),
        ))
        for item in scenario_items:
            item["plan_item_sha256"] = canonical_hash(item, "plan_item_sha256")
        plan_items.extend(scenario_items)

        action_ids = [action["action_id"] for action, _ in conditional_pairs]
        conditional_count = len(action_ids)
        summaries.append({
            "scenario_id": scenario_id,
            "site_id": scenario["site_id"],
            "crop": scenario["crop"],
            "state": scenario["state"],
            "district": scenario["district"],
            "season": scenario["season"],
            "decision_date": scenario["decision_date"],
            "season_window": calendar["season_window"],
            "season_window_position": calendar["season_window_position"],
            "plan_status": (
                "regional_plan_with_conditional_source_quoted_operations"
                if conditional_count else "regional_plan_with_calendar_and_policy_references_only"
            ),
            "conditional_source_quoted_operation_count": str(conditional_count),
            "conditional_action_ids": ";".join(action_ids),
            "regional_reference_item_count": "3",
            "total_plan_item_count": str(len(scenario_items)),
            "plan_summary": (
                f"Declared {scenario['season']} seasonal context is available for {scenario['crop']} in "
                f"{scenario['district']}, {scenario['state']}. "
                f"{conditional_count} time-valid source-quoted operation(s) remain conditional because their "
                "field preconditions are not observed; regional nutrient and IPM references are retained for planning."
            ),
            "direct_farm_action_status": "not_issued_no_farm_specific_observation_or_treatment_trigger",
        })
        summaries[-1]["plan_summary_sha256"] = canonical_hash(summaries[-1], "plan_summary_sha256")

    if len({row["plan_item_id"] for row in plan_items}) != len(plan_items):
        raise SystemExit("Regional plan item IDs are not unique.")
    if len(summaries) != len(scenario_ids):
        raise SystemExit("Regional plan summary coverage is incomplete.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "regional_operation_plan_items.csv", ITEM_FIELDS, plan_items)
    write_csv(args.out_dir / "regional_operation_plan_summary.csv", SUMMARY_FIELDS, summaries)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    provenance = [
        {
            "generated_at_utc": generated_at,
            "artifact_role": role,
            "input_path": str(path.relative_to(PROJECT_ROOT)),
            "input_sha256": file_sha256(path),
            "input_row_count": str(len(rows)),
            "notes": note,
        }
        for role, path, rows, note in (
            ("frozen_scenario_manifest", args.manifest, scenarios, "Immutable scenario identity and decision date."),
            ("regional_calendar_features", args.calendar, list(calendar_by_id.values()), "Declared calendar position, never observed crop stage."),
            ("management_policy_features", args.policy, list(policy_by_id.values()), "Regional nutrient and IPM policy references with restrictions."),
            ("official_action_records", args.actions, actions, "Source-quoted operations and their source hashes."),
            ("scenario_official_action_bindings", args.bindings, bindings, "Full scope decisions; only conditional passes become operation-plan items."),
        )
    ]
    write_csv(args.out_dir / "regional_operation_plan_provenance.csv", PROVENANCE_FIELDS, provenance)
    print(
        f"Regional operation plan: {len(summaries)}/{len(scenarios)} scenario summaries, "
        f"{len(plan_items)} source-linked plan items, and "
        f"{sum(len(values) for values in conditionals_by_scenario.values())} conditional operation items."
    )


if __name__ == "__main__":
    main()
