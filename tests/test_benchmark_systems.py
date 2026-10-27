"""Regression tests for the evaluation-only architecture systems."""
from __future__ import annotations

import pytest

from data.benchmark_loader import FrozenBenchmarkLoader
from evaluation.benchmark_oracle import BenchmarkEvaluationOracle
from evaluation.benchmark_systems import EVALUATION_ONLY_SYSTEM_IDS, SYSTEM_IDS, build_benchmark_system
from graph.benchmark_workflow import BenchmarkMASWorkflow
from llm.benchmark_llm_client import BenchmarkLLMClient


RICE_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"
ELIGIBLE_DIVERGENCE = "ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331"


def test_a0_factory_returns_the_unchanged_proposed_workflow():
    workflow = build_benchmark_system(
        "A0", loader=FrozenBenchmarkLoader(), bounded_llm=BenchmarkLLMClient(enabled=False)
    )
    assert isinstance(workflow, BenchmarkMASWorkflow)


@pytest.mark.parametrize("system_id", sorted(EVALUATION_ONLY_SYSTEM_IDS))
def test_evaluation_only_systems_are_safe_and_produce_auditable_runs(system_id):
    scenario_id = ELIGIBLE_DIVERGENCE if system_id == "A6" else RICE_ANCHOR
    workflow = build_benchmark_system(
        system_id,
        loader=FrozenBenchmarkLoader(),
        bounded_llm=BenchmarkLLMClient(enabled=False),
    )
    run = workflow.run(scenario_id, verify_raw_hashes=False)

    assert run.scenario_id == scenario_id
    assert run.decision.direct_farm_action_issued is False
    assert run.farmer_message
    assert run.evaluation.direct_farm_action_issued is False
    # The oracle is allowed to fail for a declared evaluation-only system, but
    # it must be able to inspect its complete typed trace without crashing.
    result = BenchmarkEvaluationOracle().evaluate(
        FrozenBenchmarkLoader().load(scenario_id, verify_raw_hashes=False), run
    )
    assert result.scenario_id == scenario_id


def test_declared_ablation_boundaries_are_observable_in_the_trace():
    loader = FrozenBenchmarkLoader()
    a3 = build_benchmark_system("A3", loader=loader, bounded_llm=BenchmarkLLMClient(enabled=False))
    a4 = build_benchmark_system("A4", loader=loader, bounded_llm=BenchmarkLLMClient(enabled=False))
    a5 = build_benchmark_system("A5", loader=loader, bounded_llm=BenchmarkLLMClient(enabled=False))
    a6 = build_benchmark_system("A6", loader=loader, bounded_llm=BenchmarkLLMClient(enabled=False))

    a3_run = a3.run(RICE_ANCHOR, verify_raw_hashes=False)
    a4_run = a4.run(RICE_ANCHOR, verify_raw_hashes=False)
    a5_run = a5.run(RICE_ANCHOR, verify_raw_hashes=False)
    a6_run = a6.run(ELIGIBLE_DIVERGENCE, verify_raw_hashes=False)

    assert not a3_run.retrieved_passages
    assert not any(claim.agent_name == "official_operations_rag_agent" for claim in a3_run.claims)
    assert not any(claim.agent_name == "regional_calendar_operation_window_agent" for claim in a4_run.claims)
    assert not any(claim.agent_name == "crop_district_season_alignment_validator_agent" for claim in a5_run.claims)
    assert not any(claim.agent_name == "evidence_provenance_agent" for claim in a5_run.claims)
    assert a6_run.conflicts
    assert not a6_run.decision.conflict_resolution_records


def test_batch_runner_requires_evaluation_only_for_a1_to_a6(tmp_path):
    from evaluation.benchmark_batch_runner import BenchmarkBatchRunner, ExperimentProtocolError

    with pytest.raises(ExperimentProtocolError, match="evaluation-only"):
        BenchmarkBatchRunner(require_clean_git=False).run(
            configuration_id="E0",
            system_id="A1",
            output_dir=tmp_path / "must-not-run",
            scenario_ids=(RICE_ANCHOR,),
        )
