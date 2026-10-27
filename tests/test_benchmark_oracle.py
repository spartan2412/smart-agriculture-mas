"""Regression tests for the source-derived benchmark evaluation oracle."""
from __future__ import annotations

from dataclasses import replace

from data.benchmark_loader import FrozenBenchmarkLoader
from evaluation.benchmark_oracle import BenchmarkEvaluationOracle
from evaluation.conflict_fixture_runner import ConflictFixtureRunner
from graph.benchmark_workflow import BenchmarkMASWorkflow


RICE_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"
ELIGIBLE_DIVERGENCE = "ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331"


def _completed_run(scenario_id: str = RICE_ANCHOR):
    scenario = FrozenBenchmarkLoader().load(scenario_id, verify_raw_hashes=False)
    run = BenchmarkMASWorkflow().run(scenario_id, verify_raw_hashes=False)
    return scenario, run


def _checks(result):
    return {check.name: check for check in result.checks}


def test_oracle_accepts_a_normal_frozen_run_and_emits_json_ready_result_schema():
    scenario, run = _completed_run()
    result = BenchmarkEvaluationOracle().evaluate(scenario, run)

    assert result.overall_passed
    assert not result.failing_check_names
    assert len(result.structural_fingerprint) == 64
    assert set(result.metric_values()) == {
        "input_lineage_integrity",
        "stable_claim_identity_fidelity",
        "claim_scope_contract_compliance",
        "citation_traceability",
        "context_source_provenance_binding",
        "rag_scope_compliance",
        "operation_binding_and_condition_compliance",
        "conditional_operation_completeness",
        "source_quote_locator_hash_fidelity",
        "grounded_plan_coverage",
        "plan_and_selected_operation_citation_coverage",
        "farmer_message_condition_and_citation_fidelity",
        "farmer_message_source_detail_and_facility_fidelity",
        "unsupported_action_prevention_and_agent_permissions",
        "abstention_reason_coverage",
        "conflict_trace_completeness_and_exclusion",
        "conflict_resolution_citation_fidelity",
        "natural_ndvi_weather_divergence_policy",
        "vision_no_data_boundary",
        "bounded_llm_trace_compliance",
        "overall_structural_pass",
    }
    assert result.as_dict()["overall_passed"] is True


def test_oracle_rejects_market_claim_that_borrows_the_weather_source_url():
    """Context claims must retain their own domain's frozen source provenance."""
    scenario, run = _completed_run(ELIGIBLE_DIVERGENCE)
    claims = list(run.claims)
    market_index = next(
        index
        for index, claim in enumerate(claims)
        if claim.agent_name == "market_evidence_agent"
    )
    market_claim = claims[market_index]
    claims[market_index] = market_claim.model_copy(
        update={
            "source": market_claim.source.model_copy(
                update={"official_url": scenario.manifest["weather_source_url"]}
            )
        }
    )

    checks = _checks(
        BenchmarkEvaluationOracle().evaluate(scenario, replace(run, claims=tuple(claims)))
    )

    assert not checks["context_source_provenance_binding"].passed


def test_oracle_accepts_a_real_non_action_ndvi_weather_divergence_trace():
    scenario, run = _completed_run(ELIGIBLE_DIVERGENCE)
    result = BenchmarkEvaluationOracle().evaluate(scenario, run)

    assert len(run.conflicts) == 1
    assert result.overall_passed
    assert _checks(result)["conflict_trace_completeness_and_exclusion"].passed


def test_oracle_rejects_unknown_decision_citation_and_out_of_scope_passage():
    scenario, run = _completed_run()
    bad_decision = replace(run.decision, citations=("UNADMITTED_TEST_SOURCE",))
    bad_passage = replace(
        run.retrieved_passages[0],
        source_document_id="UNADMITTED_TEST_SOURCE",
        official_url="https://example.invalid/unadmitted",
    )
    bad_run = replace(
        run,
        decision=bad_decision,
        retrieved_passages=(bad_passage, *run.retrieved_passages[1:]),
    )
    checks = _checks(BenchmarkEvaluationOracle().evaluate(scenario, bad_run))

    assert not checks["citation_traceability"].passed
    assert not checks["rag_scope_compliance"].passed


def test_oracle_rejects_direct_action_and_lost_condition_trace():
    scenario, run = _completed_run()
    claims = list(run.claims)
    conditional_index = next(
        index
        for index, claim in enumerate(claims)
        if claim.agent_name == "action_feasibility_agent"
    )
    claims[conditional_index] = claims[conditional_index].model_copy(update={"block_reason": None})
    bad_run = replace(
        run,
        claims=tuple(claims),
        decision=replace(run.decision, direct_farm_action_issued=True),
    )
    checks = _checks(BenchmarkEvaluationOracle().evaluate(scenario, bad_run))

    assert not checks["operation_binding_and_condition_compliance"].passed
    assert not checks["unsupported_action_prevention_and_agent_permissions"].passed


def test_oracle_rejects_dropped_conditional_operation_and_tampered_source_quote():
    scenario, run = _completed_run()
    claims = list(run.claims)
    action_index = next(
        index
        for index, claim in enumerate(claims)
        if claim.agent_name == "action_feasibility_agent"
    )
    claims.pop(action_index)
    postharvest_index = next(
        index
        for index, claim in enumerate(claims)
        if claim.agent_name == "postharvest_storage_logistics_agent"
        and claim.disposition.value == "conditional_operation"
    )
    tampered_metadata = dict(claims[postharvest_index].metadata)
    tampered_metadata["source_quote"] = "tampered quotation"
    claims[postharvest_index] = claims[postharvest_index].model_copy(
        update={"metadata": tampered_metadata}
    )

    checks = _checks(BenchmarkEvaluationOracle().evaluate(scenario, replace(run, claims=tuple(claims))))

    assert not checks["conditional_operation_completeness"].passed
    assert not checks["source_quote_locator_hash_fidelity"].passed


def test_oracle_rejects_farmer_message_that_loses_selected_condition_or_source():
    scenario, run = _completed_run()
    selected = next(
        claim
        for claim in run.claims
        if claim.disposition.value == "conditional_operation"
        and claim.claim == run.decision.operation_text
    )
    condition = selected.metadata["conditions_text"]
    source_id = selected.source.source_document_id
    bad_message = run.farmer_message.replace(condition, "condition omitted").replace(source_id, "source omitted")
    checks = _checks(BenchmarkEvaluationOracle().evaluate(scenario, replace(run, farmer_message=bad_message)))

    assert not checks["farmer_message_condition_and_citation_fidelity"].passed


def test_oracle_rejects_farmer_message_that_hides_a_source_recorded_plan_detail_or_facility():
    scenario, run = _completed_run()
    plan_item = next(item for item in scenario.regional_operation_plan_items if item.get("conditions_text"))
    facility = scenario.postharvest_site_facility_context[0]
    bad_message = (
        run.farmer_message
        .replace(plan_item["conditions_text"], "condition omitted")
        .replace(facility["candidate_name"], "facility omitted")
    )

    checks = _checks(BenchmarkEvaluationOracle().evaluate(scenario, replace(run, farmer_message=bad_message)))

    assert not checks["farmer_message_source_detail_and_facility_fidelity"].passed


def test_oracle_rejects_stale_claim_identity_and_scope_mutation():
    scenario, run = _completed_run()
    claims = list(run.claims)
    original = claims[0]
    raw = original.model_dump(mode="python")
    raw["source"] = original.source
    raw["claim"] = "Tampered claim text that retains the stale original claim ID."
    raw["spatial_scope"] = "unscoped alternate location"
    claims[0] = type(original).model_construct(**raw)

    checks = _checks(BenchmarkEvaluationOracle().evaluate(scenario, replace(run, claims=tuple(claims))))

    assert not checks["stable_claim_identity_fidelity"].passed
    assert not checks["claim_scope_contract_compliance"].passed


def test_oracle_checks_repeatability_and_all_controlled_fixture_outcomes():
    scenario, first = _completed_run()
    _, second = _completed_run()
    divergence_scenario, divergence_run = _completed_run(ELIGIBLE_DIVERGENCE)
    oracle = BenchmarkEvaluationOracle()
    repeatability = oracle.evaluate_repeatability(first, second)
    fixture_runs = ConflictFixtureRunner().run_all(verify_raw_hashes=False)
    fixtures = oracle.evaluate_fixture_runs(fixture_runs)
    incomplete_fixtures = oracle.evaluate_fixture_runs(fixture_runs[:1])
    aggregate = oracle.aggregate((oracle.evaluate(scenario, first), oracle.evaluate(scenario, second)))
    stratified = oracle.aggregate_stratified((
        (scenario, oracle.evaluate(scenario, first)),
        (divergence_scenario, oracle.evaluate(divergence_scenario, divergence_run)),
    ))

    assert repeatability.passed
    assert fixtures.all_passed
    assert fixtures.coverage_passed
    assert not incomplete_fixtures.coverage_passed
    assert not incomplete_fixtures.all_passed
    assert fixtures.fixture_count == 60
    assert fixtures.passed_fixture_count == 60
    assert dict(fixtures.family_counts) == {
        "coordinator_resolution": 48,
        "negative_control_no_comparable_conflict": 6,
        "pre_resolution_integrity_rejection": 6,
    }
    assert aggregate.scenario_count == 2
    assert aggregate.overall_structural_pass_rate == 1.0
    assert stratified.scenario_count == 2
    crop_strata = {
        stratum.stratum_value: stratum
        for stratum in stratified.strata
        if stratum.stratum_name == "crop"
    }
    assert set(crop_strata) == {"rice", "chickpea"}
    assert all(stratum.overall_structural_pass_rate == 1.0 for stratum in crop_strata.values())
