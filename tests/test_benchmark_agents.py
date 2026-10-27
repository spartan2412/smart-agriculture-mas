"""Safety and integration tests for the provenance-constrained benchmark MAS path."""
from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from agents.benchmark import __all__ as BENCHMARK_AGENT_NAMES
from data.benchmark_loader import FrozenBenchmarkLoader, ScenarioIntegrityError
from data.evidence_schema import ClaimDisposition, DecisionDomain
from graph.benchmark_workflow import BenchmarkMASWorkflow


RICE_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"
WHEAT_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_WHEAT_RABI_20260430"
ELIGIBLE_DIVERGENCE = "ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331"
INELIGIBLE_DIVERGENCE = "ANCHOR_PF_MH_NANDED_CHICKPEA_RABI_20260331"
TOMATO_ANCHOR = "ANCHOR_PF_TN_COIMBATORE_TOMATO_RABI_20251231"
MARKET_COMPARATOR_UNAVAILABLE = "ANCHOR_PF_TN_ARIYALUR_MAIZE_RABI_20260331"
SATELLITE_QUALITY_WITHHELD = "SUPPLEMENT_PF_MH_LATUR_CHICKPEA_RABI_20251130"

EXPECTED_RUNTIME_AGENT_NAMES = {
    "scenario_evidence_router",
    "crop_district_season_alignment_validator",
    "metadata_gate",
    "evidence_provenance_agent",
    "weather_context_agent",
    "soil_context_agent",
    "satellite_ndvi_context_agent",
    "market_evidence_agent",
    "fertilizer_baseline_agent",
    "crop_protection_safety_agent",
    "vision_availability_agent",
    "regional_calendar_operation_window_agent",
    "official_operations_rag_agent",
    "postharvest_storage_logistics_agent",
    "regulatory_compliance_agent",
    "action_feasibility_agent",
    "uncertainty_abstention_agent",
    "conflict_detection_agent",
    "provenance_aware_coordinator_agent",
    "farmer_explanation_citation_agent",
    "benchmark_evaluator_agent",
}


def test_benchmark_package_exports_all_twenty_one_roles():
    assert len(BENCHMARK_AGENT_NAMES) == 21


def test_recovered_rice_operation_runs_all_roles_with_required_safety_boundaries():
    run = BenchmarkMASWorkflow().run(
        RICE_ANCHOR,
        question="What evidence is available for rice management?",
        verify_raw_hashes=True,
    )

    assert run.scenario_id == RICE_ANCHOR
    assert len(run.claims) >= 20
    assert all(claim.scenario_id == RICE_ANCHOR for claim in run.claims)
    assert EXPECTED_RUNTIME_AGENT_NAMES <= {claim.agent_name for claim in run.claims}
    assert run.decision.decision_status == "conditional_operation_pending_field_precondition"
    assert not run.decision.direct_farm_action_issued
    assert run.evaluation.outcome == "trace_structurally_safe"
    assert run.evaluation.unsupported_action_count == 0
    assert run.evaluation.abstention_reason_coverage == 1.0

    vision_claim = next(claim for claim in run.claims if claim.agent_name == "vision_availability_agent")
    assert vision_claim.disposition == ClaimDisposition.NO_DATA
    assert vision_claim.block_reason == "abstain_no_aligned_field_leaf_image"

    blocked = [
        claim
        for claim in run.claims
        if claim.disposition
        in {ClaimDisposition.BLOCKED, ClaimDisposition.ABSTAIN, ClaimDisposition.NO_DATA}
    ]
    assert blocked
    assert all(claim.block_reason for claim in blocked)
    assert "not issued as a farm action" in run.farmer_message


def test_conditionally_applicable_operation_never_becomes_direct_farm_action():
    run = BenchmarkMASWorkflow().run(
        WHEAT_ANCHOR,
        question="What source-scoped operation is available?",
        verify_raw_hashes=True,
    )

    conditional = [
        claim for claim in run.claims if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
    ]
    assert conditional
    assert all(claim.block_reason for claim in conditional)
    assert any("actual_crop_stage" in (claim.block_reason or "") for claim in conditional)
    assert run.decision.decision_status == "conditional_operation_pending_field_precondition"
    assert not run.decision.direct_farm_action_issued
    assert run.evaluation.unsupported_action_count == 0
    assert "not issued as a farm action" in run.farmer_message


def test_retrieval_never_returns_a_source_outside_the_admitted_scope():
    workflow = BenchmarkMASWorkflow()
    scenario = workflow.loader.load(RICE_ANCHOR, verify_raw_hashes=True)
    run = workflow.run(RICE_ANCHOR, question="rice nutrient management", verify_raw_hashes=False)
    admitted_ids = {
        row["source_document_id"]
        for row in scenario.rag_scope
        if row["rag_scope_status"].startswith("admitted_")
    }
    source_scoped_operation_ids = {
        row["source_document_id"] for row in scenario.retrievable_operation_passages
    }
    postharvest_operation_ids = {
        row["source_document_id"] for row in scenario.retrievable_postharvest_rag_passages
    }

    assert run.retrieved_passages
    assert source_scoped_operation_ids
    assert all(
        passage.source_document_id in admitted_ids | source_scoped_operation_ids | postharvest_operation_ids
        for passage in run.retrieved_passages
    )
    assert not run.conflicts  # no fabricated conflict for this frozen anchor


def test_postharvest_enrichment_is_loaded_into_agent_and_exact_crop_rag_path():
    workflow = BenchmarkMASWorkflow()
    scenario = workflow.loader.load(RICE_ANCHOR, verify_raw_hashes=True)
    assert all(row["crop_scope_status"] == "pass_exact_crop" for row in scenario.postharvest_rag_scope)
    assert all(row["crop"] == "rice" for row in scenario.retrievable_postharvest_rag_passages)

    run = workflow.run(
        RICE_ANCHOR,
        question="What are the documented rice drying and storage conditions?",
        verify_raw_hashes=False,
    )
    postharvest_claims = [
        claim for claim in run.claims
        if claim.agent_name == "postharvest_storage_logistics_agent"
    ]
    conditional = [
        claim for claim in postharvest_claims
        if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
    ]
    assert len(conditional) == len(scenario.postharvest_plan_items)
    assert all(claim.decision_domain == DecisionDomain.POSTHARVEST_LOGISTICS for claim in postharvest_claims)
    assert all(claim.metadata["direct_farm_action_issued"] is False for claim in postharvest_claims)
    assert any(
        passage.corpus_layer == "postharvest_exact_crop"
        and passage.source_document_id == "PAU_KHARIF_2026"
        for passage in workflow.official_rag.retrieve(scenario, question="rice storage drying", top_k=5)
    )
    assert "Post-harvest plan" in run.farmer_message
    assert "Storage/logistics context:" in run.farmer_message
    assert "dispatch instruction" in run.farmer_message


def test_farmer_output_renders_existing_source_detail_and_facility_rows_without_lookup_placeholders():
    """The renderer must expose already-loaded evidence instead of generic references."""
    workflow = BenchmarkMASWorkflow()
    scenario = workflow.loader.load(TOMATO_ANCHOR, verify_raw_hashes=True)
    question = "What is the source-recorded tomato nutrient schedule and post-harvest handling?"
    run = workflow.run(TOMATO_ANCHOR, question=question, verify_raw_hashes=False)
    message = run.farmer_message

    # The exact, source-recorded nutrient/IPM details are displayed directly.
    assert "200:250:250 kg NPK/ha for hybrids." in message
    assert "75% of P as basal" in message
    assert "Iprodione 50% WP 600 g/ac" in message
    assert "Only after a supported early-blight diagnosis" in message
    assert "Nutrient plan reference:" not in message
    assert "Crop-protection plan reference:" not in message

    # Every stored plan detail is rendered as an immutable source-backed card.
    for item in scenario.regional_operation_plan_items:
        for field in ("conditions_text", "source_document_id", "source_url"):
            value = item.get(field, "")
            if value:
                assert value in message
    for item in scenario.postharvest_plan_items:
        for field in ("operation_text", "method_or_parameter", "conditions_text", "source_document_id", "source_url"):
            value = item.get(field, "")
            if value:
                assert value in message

    # Facility rows are source-linked candidate context, never a booking claim.
    assert "Storage/logistics context: source-linked facility and warehouse candidates" in message
    for facility in scenario.postharvest_site_facility_context:
        assert facility["candidate_name"] in message
        assert facility["source_document_id"] in message
        assert facility["source_url"] in message
        assert facility["not_supported"] in message
    for route in scenario.postharvest_static_route_context:
        assert route["road_distance_km"] in message
        assert route["road_duration_minutes"] in message
    assert "not a live availability, booking" in message

    # Context cards now show all retained source facts rather than a one-line
    # summary, while retaining their non-farm-action boundaries.
    assert "Historical weather and water context" in message
    assert "77.907%" in message
    assert "88.850 mm" in message
    assert "Static SoilGrids context" in message
    assert "pH in H2O 0-5cm mean (pH*10): source-reported raw value 68" in message
    assert "raw_value_divided_by_10_is_pH" in message
    assert "Historical Sentinel-2 / NDVI context" in message
    assert "S2C_MSIL2A_20251208T051221_R019_T43PGN_20251208T081319" in message
    assert "change -0.038104" in message
    assert "Historical nearest-mandi market context" in message
    assert "decision-month mean 4826.805" in message
    assert "prior-month mean 3618.450" in message
    assert "Tomato in Coimbatore, Tamil Nadu" in message

    # Question-specific passages were already metadata-admitted upstream; the
    # renderer exposes two ranked excerpts without issuing a new retrieval.
    assert "Question-specific official evidence excerpts" in message
    assert question in message
    for passage in run.retrieved_passages[:2]:
        assert passage.source_document_id in message
        assert passage.text in message
        assert passage.official_url in message


def test_farmer_output_explains_unavailable_context_without_promoting_invalid_data():
    workflow = BenchmarkMASWorkflow()

    no_comparator = workflow.run(MARKET_COMPARATOR_UNAVAILABLE, verify_raw_hashes=False)
    assert "Source-recorded decision-month mean: 1763.070" in no_comparator.farmer_message
    assert "No historical price comparison is issued" in no_comparator.farmer_message
    assert "no_source_comparator" in no_comparator.farmer_message

    withheld = workflow.run(SATELLITE_QUALITY_WITHHELD, verify_raw_hashes=False)
    assert "Satellite / NDVI context status" in withheld.farmer_message
    assert "withheld_non_clear_or_non_land_pixel" in withheld.farmer_message
    assert "raw scene values and any limited chronology are withheld" in withheld.farmer_message
    # The withheld scene's raw DN/limited-series values never become a plan card.
    assert "red DN 1530" not in withheld.farmer_message
    assert "first/last NDVI 0.663561/0.663561" not in withheld.farmer_message


def test_satellite_context_uses_its_exact_stac_item_citation_not_weather_source():
    """A Sentinel card must never inherit a cross-domain weather URL."""
    run = BenchmarkMASWorkflow().run(ELIGIBLE_DIVERGENCE, verify_raw_hashes=True)
    satellite_claim = next(
        claim for claim in run.claims if claim.agent_name == "satellite_ndvi_context_agent"
    )
    expected_url = (
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/"
        "S2A_MSIL2A_20260306T053251_R062_T43QEB_20260306T103611"
    )
    assert satellite_claim.source.official_url == expected_url
    assert satellite_claim.source.raw_sha256 == "3f3d6083e25844129e27e4b47fde883fe347b28e17ebb9bf7da0e3fdc3d8a53f"
    satellite_card = run.farmer_message.split("**Historical Sentinel-2 / NDVI context", 1)[1].split(
        "**Historical nearest-mandi market context", 1
    )[0]
    assert expected_url in satellite_card
    assert "power.larc.nasa.gov" not in satellite_card


def test_market_context_uses_its_exact_agmarknet_citation_not_weather_source():
    """A market card must never inherit a cross-domain weather URL."""
    workflow = BenchmarkMASWorkflow()
    scenario = workflow.loader.load(ELIGIBLE_DIVERGENCE, verify_raw_hashes=True)
    run = workflow.run(ELIGIBLE_DIVERGENCE, verify_raw_hashes=True)
    market_claim = next(
        claim for claim in run.claims if claim.agent_name == "market_evidence_agent"
    )
    expected_url = scenario.market_context_manifest["source_url"]

    assert market_claim.source.official_url == expected_url
    assert market_claim.source.raw_sha256 == scenario.market_context_manifest["verified_payload_sha256"]
    market_card = run.farmer_message.split("**Historical nearest-mandi market context", 1)[1].split(
        "**What is not established", 1
    )[0]
    assert expected_url in market_card
    assert scenario.manifest["weather_source_url"] not in market_card


def test_farmer_output_renders_source_recorded_policy_detail_without_a_lookup():
    """Nutrient and IPM cards expose the admitted regional details directly."""
    run = BenchmarkMASWorkflow().run(ELIGIBLE_DIVERGENCE, verify_raw_hashes=True)

    assert "N:P2O5:K2O = 25:50:25 kg/ha as basal at sowing" in run.farmer_message
    assert "quinalphos 25% EC at 20 mL/10 L water as an ETL-based option" in run.farmer_message
    assert "This is a source-recorded regional basal reference, not an individual field dose." in run.farmer_message
    assert "This is source-recorded conditional IPM context, not a pesticide order." in run.farmer_message


def test_recovered_operation_enrichments_are_loaded_into_plan_rag_and_feasibility_path():
    workflow = BenchmarkMASWorkflow()
    scenario = workflow.loader.load(ELIGIBLE_DIVERGENCE, verify_raw_hashes=True)

    assert scenario.regional_operation_plan_summary["plan_status"] == (
        "regional_plan_with_conditional_source_quoted_operations"
    )
    assert any(
        item["action_id"] == "MPKV_MH_CHICKPEA_HARVEST_AFTER_HARD_PODS"
        for item in scenario.regional_operation_plan_items
    )
    assert any(
        item["source_document_id"] == "MPKV_KRISHI_DARSHANI_2023"
        for item in scenario.retrievable_operation_passages
    )
    assert [row["source_document_id"] for row in scenario.recovered_operation_sources] == [
        "MPKV_KRISHI_DARSHANI_2023"
    ]

    run = workflow.run(
        ELIGIBLE_DIVERGENCE,
        question="When should chickpea be harvested after pods become hard?",
        verify_raw_hashes=True,
    )
    assert any(
        passage.source_document_id == "MPKV_KRISHI_DARSHANI_2023"
        for passage in run.retrieved_passages
    )
    assert "**Evidence-resolution note**" in run.farmer_message
    assert "Historical NDVI and weather context diverged" in run.farmer_message
    conditional_action_ids = [
        claim.metadata["action_id"]
        for claim in run.claims
        if claim.agent_name == "action_feasibility_agent"
        and claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
    ]
    assert conditional_action_ids == list(dict.fromkeys(conditional_action_ids))
    assert "MPKV_MH_CHICKPEA_HARVEST_AFTER_HARD_PODS" in conditional_action_ids


def test_only_eligible_natural_divergence_candidates_enter_conflict_handling():
    workflow = BenchmarkMASWorkflow()
    eligible = workflow.run(ELIGIBLE_DIVERGENCE, verify_raw_hashes=True)
    ineligible = workflow.run(INELIGIBLE_DIVERGENCE, verify_raw_hashes=True)

    assert len(eligible.conflicts) == 1
    assert eligible.conflicts[0].status == "eligible_natural_signal_divergence_candidate"
    assert not ineligible.conflicts


def test_workflow_stops_before_context_agents_when_an_integrity_gate_blocks():
    class MisalignedLoader(FrozenBenchmarkLoader):
        def load(self, scenario_id, *, verify_raw_hashes=True):
            scenario = super().load(scenario_id, verify_raw_hashes=verify_raw_hashes)
            mismatched_calendar = dict(scenario.regional_calendar)
            mismatched_calendar["crop"] = "fabricated_crop"
            return replace(scenario, regional_calendar=MappingProxyType(mismatched_calendar))

    workflow = BenchmarkMASWorkflow(loader=MisalignedLoader())
    try:
        workflow.run(RICE_ANCHOR, verify_raw_hashes=True)
    except ScenarioIntegrityError as exc:
        assert "crop_district_season_alignment_validator" in str(exc)
    else:
        raise AssertionError("workflow continued after a blocked integrity gate")
