"""Regression checks for the source-linked regional operation-plan enrichment."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def canonical_hash(row: dict[str, str], digest_field: str) -> str:
    payload = {field: value for field, value in row.items() if field != digest_field}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def test_regional_plan_covers_every_frozen_scenario_with_three_baseline_references() -> None:
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    summaries = read_csv(ENRICHED / "regional_operation_plan_summary.csv")
    items = read_csv(ENRICHED / "regional_operation_plan_items.csv")
    scenario_ids = {row["scenario_id"] for row in scenarios}

    assert len(summaries) == len(scenarios) == 300
    assert {row["scenario_id"] for row in summaries} == scenario_ids
    expected_baseline_ids = {
        f"{scenario_id}__calendar_window" for scenario_id in scenario_ids
    } | {
        f"{scenario_id}__fertilizer_policy" for scenario_id in scenario_ids
    } | {
        f"{scenario_id}__protection_policy" for scenario_id in scenario_ids
    }
    actual_baseline_ids = {
        row["plan_item_id"] for row in items
        if row["plan_item_type"] != "time_valid_source_quoted_conditional_operation"
    }
    assert actual_baseline_ids == expected_baseline_ids


def test_regional_plan_operations_equal_existing_conditional_bindings_only() -> None:
    bindings = read_csv(ENRICHED / "scenario_official_action_bindings_all.csv")
    actions = {row["action_id"]: row for row in read_csv(ENRICHED / "official_action_records_all.csv")}
    items = read_csv(ENRICHED / "regional_operation_plan_items.csv")
    expected = {
        (row["scenario_id"], row["action_id"]): row
        for row in bindings
        if row["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition"
    }
    actual = {
        (row["scenario_id"], row["action_id"]): row
        for row in items
        if row["plan_item_type"] == "time_valid_source_quoted_conditional_operation"
    }

    assert set(actual) == set(expected)
    assert len(actual) > 474
    for key, item in actual.items():
        action = actions[item["action_id"]]
        assert item["source_raw_sha256"] == action["source_raw_sha256"]
        assert item["source_quote"] == action["source_quote"]
        assert item["source_binding_status"] == expected[key]["binding_status"]
        assert item["missing_evidence"] == expected[key]["binding_reason"]
        assert item["actionability_status"] == "not_a_direct_farm_action"


def test_regional_plan_hashes_and_direct_action_guard_hold() -> None:
    items = read_csv(ENRICHED / "regional_operation_plan_items.csv")
    summaries = read_csv(ENRICHED / "regional_operation_plan_summary.csv")

    assert all(canonical_hash(row, "plan_item_sha256") == row["plan_item_sha256"] for row in items)
    assert all(canonical_hash(row, "plan_summary_sha256") == row["plan_summary_sha256"] for row in summaries)
    assert {
        row["direct_farm_action_status"] for row in summaries
    } == {"not_issued_no_farm_specific_observation_or_treatment_trigger"}


def test_mpkv_chickpea_guide_is_hash_linked_and_never_promoted_to_a_direct_action() -> None:
    inventory = read_csv(ENRICHED / "mpkv_chickpea_source_inventory.csv")
    actions = read_csv(ENRICHED / "mpkv_chickpea_action_records.csv")
    bindings = read_csv(ENRICHED / "scenario_mpkv_chickpea_action_bindings.csv")

    assert len(inventory) == len(actions) == 1
    source = inventory[0]
    assert source["source_document_id"] == "MPKV_KRISHI_DARSHANI_2023"
    assert source["publication_date"] == "2023-06-07"
    for path_column, hash_column in (
        ("http_metadata_path", "http_metadata_sha256"),
        ("publication_page_raw_path", "publication_page_raw_sha256"),
        ("raw_path", "raw_sha256"),
        ("scope_page_image_path", "scope_page_image_sha256"),
        ("operation_page_image_path", "operation_page_image_sha256"),
        ("extracted_text_path", "extracted_text_sha256"),
    ):
        path = ENRICHED / source[path_column]
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == source[hash_column]

    action = actions[0]
    assert action["action_id"] == "MPKV_MH_CHICKPEA_HARVEST_AFTER_HARD_PODS"
    publication_page = (ENRICHED / source["publication_page_raw_path"]).read_text(encoding="utf-8")
    assert "Krishi Darshani 2023" in publication_page
    assert "Annual Diary (Krishidarshani)" in publication_page
    assert source["original_server_last_modified_utc"] == "2023-06-07T11:01:25Z"
    assert action["state_scope"] == "Maharashtra"
    assert action["requires_actual_crop_stage"] == "true"
    assert action["requires_field_observation"] == "true"
    conditional = [
        row for row in bindings
        if row["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition"
    ]
    assert len(bindings) == 300
    assert len(conditional) == 50
    assert all(
        row["crop"] == "chickpea"
        and row["state"] == "Maharashtra"
        and row["season"] == "rabi"
        and row["decision_date"] >= source["publication_date"]
        and row["binding_reason"] == "actual_crop_stage;documented_field_condition"
        for row in conditional
    )
    assert not any(row["binding_status"] == "source_scoped_eligible" for row in bindings)
