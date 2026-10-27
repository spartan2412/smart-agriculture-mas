"""Normalize initial, exact-week, and recovered official action layers for MAS use."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
ACTION_FIELDS = [
    "action_id", "action_layer", "action_category", "crop", "state_scope", "season_scope", "source_document_id",
    "source_title", "provider", "official_url", "source_raw_sha256", "source_location", "source_issue_start",
    "source_issue_end", "source_quote", "operation_text", "method_text", "dose_text", "conditions_text",
    "operation_role", "requires_actual_crop_stage", "requires_field_observation", "requires_decision_time_forecast",
    "requires_soil_test_for_personalised_dose", "requires_diagnosis_or_threshold",
    "requires_documented_system_or_variety", "action_record_sha256",
]
BINDING_FIELDS = [
    "scenario_id", "action_id", "action_layer", "crop", "state", "district", "season", "decision_date",
    "source_document_id", "source_scope_status", "crop_scope_status", "geography_scope_status", "season_scope_status",
    "temporal_status", "field_condition_status", "binding_status", "binding_reason", "action_record_sha256",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    initial_actions = read_csv(ENRICHED / "official_action_records.csv")
    weekly_actions = read_csv(ENRICHED / "exact_week_iisr_action_records.csv")
    archived_actions = read_csv(ENRICHED / "archived_pau_kharif_action_records.csv")
    archived_rabi_actions = read_csv(ENRICHED / "archived_pau_rabi_action_records.csv")
    mpkv_actions = read_csv(ENRICHED / "mpkv_chickpea_action_records.csv")
    actions: List[Dict[str, str]] = []
    for row in initial_actions:
        actions.append({
            **row, "action_layer": "initial_verified_action_rag", "source_issue_start": row["source_effective_from"],
            "source_issue_end": row["source_effective_to"], "operation_role": "initial_source_quoted_operation",
            "requires_decision_time_forecast": "false",
        })
    for row in weekly_actions:
        actions.append({**row, "action_layer": "exact_week_iisr_advisory"})
    actions.extend(archived_actions)
    actions.extend(archived_rabi_actions)
    actions.extend(mpkv_actions)
    if len({row["action_id"] for row in actions}) != len(actions):
        raise SystemExit("Action IDs collide across action layers.")
    write_csv(ENRICHED / "official_action_records_all.csv", ACTION_FIELDS, actions)

    initial_bindings = read_csv(ENRICHED / "scenario_official_action_bindings.csv")
    weekly_bindings = read_csv(ENRICHED / "scenario_exact_week_iisr_action_bindings.csv")
    archived_bindings = read_csv(ENRICHED / "scenario_archived_pau_kharif_action_bindings.csv")
    archived_rabi_bindings = read_csv(ENRICHED / "scenario_archived_pau_rabi_action_bindings.csv")
    mpkv_bindings = read_csv(ENRICHED / "scenario_mpkv_chickpea_action_bindings.csv")
    bindings: List[Dict[str, str]] = []
    for row in initial_bindings:
        bindings.append({
            **row, "action_layer": "initial_verified_action_rag", "source_scope_status": "initial_action_source_scope",
            "temporal_status": row["source_temporal_status"],
        })
    for row in weekly_bindings:
        bindings.append({
            **row, "action_layer": "exact_week_iisr_advisory", "source_scope_status": row["exact_week_source_scope_status"],
        })
    bindings.extend(archived_bindings)
    bindings.extend(archived_rabi_bindings)
    bindings.extend(mpkv_bindings)
    if len({(row["scenario_id"], row["action_id"]) for row in bindings}) != len(bindings):
        raise SystemExit("Scenario/action bindings collide across action layers.")
    write_csv(ENRICHED / "scenario_official_action_bindings_all.csv", BINDING_FIELDS, bindings)
    print(f"Combined official action catalog: {len(actions)} actions and {len(bindings)} scenario-action bindings.")


if __name__ == "__main__":
    main()
