"""Regression checks for the source-scoped fourth enrichment."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def row_hash(row: dict[str, str], field: str) -> str:
    payload = {key: value for key, value in row.items() if key != field}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def test_postharvest_profiles_cover_exactly_the_six_benchmark_crops() -> None:
    profiles = read_csv(ENRICHED / "postharvest_handling_profiles.csv")
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")

    assert len(profiles) == 6
    assert {row["crop"] for row in profiles} == {row["crop"] for row in scenarios}
    assert all(row["farmer_output_status"] == "conditional_plan_items_available_no_direct_farm_action" for row in profiles)
    assert all(row_hash(row, "profile_sha256") == row["profile_sha256"] for row in profiles)


def test_every_operation_is_source_quoted_and_retains_the_lot_condition() -> None:
    sources = {row["source_document_id"]: row for row in read_csv(ENRICHED / "postharvest_source_inventory.csv")}
    operations = read_csv(ENRICHED / "postharvest_operation_library.csv")

    assert len(operations) == 14
    assert len({row["operation_id"] for row in operations}) == len(operations)
    for row in operations:
        source = sources[row["source_document_id"]]
        assert row["source_raw_sha256"] == source["raw_sha256"]
        assert row["source_quote"]
        assert row["missing_observation"]
        assert row["actionability_status"] == "conditional_postharvest_planning_reference_not_direct_farm_action"
        assert row_hash(row, "operation_sha256") == row["operation_sha256"]


def test_every_scenario_has_only_its_crop_scoped_conditional_postharvest_items() -> None:
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    operations = read_csv(ENRICHED / "postharvest_operation_library.csv")
    items = read_csv(ENRICHED / "scenario_postharvest_plan_items.csv")
    contexts = read_csv(ENRICHED / "scenario_postharvest_logistics_context.csv")
    expected = {(scenario["scenario_id"], operation["operation_id"]) for scenario in scenarios for operation in operations if operation["crop"] == scenario["crop"]}

    assert {(row["scenario_id"], row["operation_id"]) for row in items} == expected
    assert len(contexts) == len(scenarios) == 300
    assert {row["scenario_id"] for row in contexts} == {row["scenario_id"] for row in scenarios}
    assert all(row["item_status"] == "conditional_postharvest_operation_pending_lot_observation" for row in items)
    assert all(row["actionability_status"] == "conditional_postharvest_planning_reference_not_direct_farm_action" for row in items)
    assert all(row_hash(row, "plan_item_sha256") == row["plan_item_sha256"] for row in items)
    assert all(row_hash(row, "context_sha256") == row["context_sha256"] for row in contexts)


def test_rag_scope_cannot_leak_a_postharvest_passage_to_another_crop() -> None:
    scenarios = {row["scenario_id"]: row for row in read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")}
    passages = {row["passage_id"]: row for row in read_csv(ENRICHED / "postharvest_rag_passages.csv")}
    scope = read_csv(ENRICHED / "scenario_postharvest_rag_scope.csv")

    assert len(passages) == 14
    assert len(scope) == 700
    for row in scope:
        assert row["crop_scope_status"] == "pass_exact_crop"
        assert passages[row["passage_id"]]["crop"] == scenarios[row["scenario_id"]]["crop"]
        assert row_hash(row, "scope_sha256") == row["scope_sha256"]


def test_facility_and_warehouse_records_are_explicitly_not_live_availability_claims() -> None:
    facilities = read_csv(ENRICHED / "postharvest_nhb_facility_records.csv")
    warehouses = read_csv(ENRICHED / "postharvest_wdra_warehouse_records.csv")
    routes = read_csv(ENRICHED / "postharvest_static_route_context.csv")
    summaries = read_csv(ENRICHED / "postharvest_site_summary.csv")

    assert facilities
    assert warehouses
    assert len(summaries) == 30
    for row in [*facilities, *warehouses]:
        boundary = row["not_supported"].lower()
        assert "historical" in boundary and "availab" in boundary
    assert len(routes) == 15
    for row in routes:
        boundary = row["not_supported"].lower()
        assert all(term in boundary for term in ("traffic", "availability", "booking", "historical"))
        assert row_hash(row, "route_sha256") == row["route_sha256"]
    assert all("No direct farm action" in row["not_supported"] for row in summaries)
