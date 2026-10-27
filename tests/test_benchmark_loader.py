from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.benchmark_loader import FrozenBenchmarkLoader, ScenarioIntegrityError


ANCHOR_ID = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"
SUPPLEMENT_ID = "SUPPLEMENT_PF_MP_INDORE_SOYBEAN_KHARIF_20240630"


def test_loader_exposes_only_the_300_frozen_scenarios():
    loader = FrozenBenchmarkLoader()
    scenario_ids = loader.scenario_ids()

    assert len(scenario_ids) == 300
    assert ANCHOR_ID in scenario_ids
    assert SUPPLEMENT_ID in scenario_ids


def test_loader_returns_complete_immutable_anchor_bundle_and_verifies_raw_hashes():
    scenario = FrozenBenchmarkLoader().load(ANCHOR_ID, verify_raw_hashes=True)

    assert scenario.identity.crop == "rice"
    assert scenario.identity.district == "Ludhiana"
    assert scenario.representative_cell["worldcover_class"] == "40"
    assert len(scenario.registry_soil_profile) == 6
    assert scenario.registry_weather["weather_status"] == "fixed_window_weather_verified"
    assert scenario.regional_calendar["calendar_status"] == (
        "declared_season_window_position_available_not_field_phenology"
    )
    assert scenario.water_context_status["water_context_status"] == "available_retrospective_context_only"
    assert scenario.market_context_status["market_actionability"] == "context_only_not_a_market_sale_instruction"
    assert scenario.ndvi_timeseries_status["satellite_actionability"].startswith("context_only")
    assert scenario.satellite_context_manifest["source_id"] == "SENTINEL2_L2A_PLANETARY_COMPUTER"
    assert scenario.satellite_context_manifest["item_request_url"].endswith(
        scenario.features["satellite_item_id"]
    )
    assert len(scenario.rag_scope) == 92
    assert len(scenario.action_bindings) == 41
    assert len(scenario.action_records) == 41
    assert len(scenario.exact_week_action_records) == 13
    assert scenario.regional_operation_plan_summary["total_plan_item_count"] == str(
        len(scenario.regional_operation_plan_items)
    )
    assert {
        (card["policy_domain"], card["source_document_id"])
        for card in scenario.regional_policy_detail_cards
    } == {
        ("fertilizer", "PAU_KHARIF_2026"),
        ("crop_protection", "PAU_KHARIF_2026"),
    }
    assert len(scenario.regional_operation_plan_provenance) == 5
    assert scenario.retrievable_operation_passages
    assert scenario.recovered_operation_sources
    assert scenario.postharvest_logistics_context["context_status"] == (
        "available_source_linked_postharvest_context"
    )
    assert scenario.postharvest_handling_profile["crop"] == scenario.identity.crop
    assert len(scenario.postharvest_plan_items) == 2
    assert len(scenario.retrievable_postharvest_rag_passages) == 2
    assert len(scenario.postharvest_site_facility_context) == 3
    assert scenario.postharvest_source_inventory
    assert len(scenario.postharvest_logistics_provenance) == 10
    assert scenario.public_district_kvk_advisory_status["exact_public_district_kvk_advisory_status"].startswith(
        "unavailable_"
    )
    assert scenario.agent_permission("irrigation_action_agent") == (
        "abstain_no_field_moisture_or_decision_time_forecast"
    )
    with pytest.raises(TypeError):
        scenario.manifest["crop"] = "tomato"
    with pytest.raises(TypeError):
        scenario.postharvest_plan_items[0]["crop"] = "tomato"


def test_loader_verifies_supplementary_sentinel_payloads_too():
    scenario = FrozenBenchmarkLoader().load(SUPPLEMENT_ID, verify_raw_hashes=True)

    assert scenario.identity.crop == "soybean"
    assert scenario.manifest["satellite_raw_path"]
    assert scenario.features["satellite_item_id"] == scenario.manifest["satellite_item_id"]
    assert scenario.ndvi_timeseries_observations
    assert scenario.retrievable_rag_chunks
    assert any(row["rag_scope_status"] == "admitted_dated_advisory_to_metadata_filtered_rag" for row in scenario.rag_scope)


def test_loader_fails_closed_for_unknown_scenario():
    with pytest.raises(ScenarioIntegrityError, match="Unknown frozen scenario_id"):
        FrozenBenchmarkLoader().load("NOT_A_FROZEN_SCENARIO", verify_raw_hashes=False)
