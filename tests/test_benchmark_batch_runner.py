"""Integration-level persistence checks for the frozen benchmark batch runner."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from evaluation.benchmark_batch_runner import (
    BatchRunError,
    BenchmarkBatchRunner,
    ExperimentProtocolError,
    _frozen_pilot_scenario_ids_from_csv,
)
from evaluation.apple_gpu_preflight import load_pilot_set
from graph.benchmark_workflow_v5 import BenchmarkMASWorkflowV5
from llm.bounded_selection_v5 import BenchmarkLLMClientV5, PROMPT_TEMPLATE_VERSION_V5


RICE_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"
ELIGIBLE_DIVERGENCE = "ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331"


def test_e0_persists_complete_trace_oracle_and_summary_for_a_documented_pilot(tmp_path):
    output_dir = tmp_path / "e0-one-scenario-pilot"
    summary = BenchmarkBatchRunner(require_clean_git=False).run(
        configuration_id="E0",
        output_dir=output_dir,
        scenario_ids=(RICE_ANCHOR,),
    )

    assert summary.scenario_count == 1
    assert summary.fully_passing_scenario_count == 1
    assert summary.system_id == "A0"
    assert summary.evaluation_only is False
    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    scenario = json.loads((output_dir / "scenarios" / f"{RICE_ANCHOR}.json").read_text(encoding="utf-8"))
    aggregate = json.loads((output_dir / "aggregate_oracle_result.json").read_text(encoding="utf-8"))
    stratified = json.loads((output_dir / "stratified_oracle_result.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["configuration_id"] == "E0"
    assert manifest["system_id"] == "A0"
    assert manifest["apple_gpu_acceleration"]["status"] == "not_applicable"
    assert len(manifest["protocol"]["verified_artifacts"]) >= 20
    assert scenario["benchmark_run"]["scenario_id"] == RICE_ANCHOR
    assert scenario["scenario_oracle_result"]["overall_passed"] is True
    assert len(scenario["scenario_oracle_result"]["checks"]) == 20
    assert aggregate["fully_passing_scenario_count"] == 1
    assert stratified["scenario_count"] == 1
    assert json.loads((output_dir / "progress.json").read_text(encoding="utf-8"))["status"] == "completed"


def test_runner_refuses_an_existing_output_directory_and_tampered_protocol_hash(tmp_path):
    existing = tmp_path / "already-exists"
    existing.mkdir()
    runner = BenchmarkBatchRunner(require_clean_git=False)
    with pytest.raises(BatchRunError, match="Refusing to overwrite"):
        runner.run(configuration_id="E0", output_dir=existing, scenario_ids=(RICE_ANCHOR,))

    protocol = json.loads((runner.protocol_path).read_text(encoding="utf-8"))
    protocol["frozen_artifact_sha256"]["data/scenarios/manifests/scenario_manifest.csv"] = "0" * 64
    tampered_protocol = tmp_path / "tampered_protocol.json"
    tampered_protocol.write_text(json.dumps(protocol), encoding="utf-8")
    tampered_runner = BenchmarkBatchRunner(
        protocol_path=tampered_protocol,
        require_clean_git=False,
    )
    with pytest.raises(ExperimentProtocolError, match="hash mismatch"):
        tampered_runner.run(
            configuration_id="E0",
            output_dir=tmp_path / "unreachable-output",
            scenario_ids=(RICE_ANCHOR,),
        )


def test_e2_e3_require_matching_two_configuration_artifact_bindings():
    runner = BenchmarkBatchRunner(require_clean_git=False)
    protocol = runner._read_protocol()
    required_fields = protocol["e2_e3_identical_artifact_gate"]["required_fields"]
    binding = {field: f"bound-{field}" for field in required_fields}

    with pytest.raises(ExperimentProtocolError, match="exactly E2 and E3 entries"):
        runner._validate_configuration(
            protocol,
            "E2",
            acceleration_evidence={"status": "verified"},
            model_artifact_binding=binding,
        )

    mismatched = {"configurations": {"E2": dict(binding), "E3": dict(binding)}}
    mismatched["configurations"]["E3"]["model_artifact_sha256"] = "different-artifact"
    with pytest.raises(ExperimentProtocolError, match="bindings differ"):
        runner._validate_configuration(
            protocol,
            "E2",
            acceleration_evidence={"status": "verified"},
            model_artifact_binding=mismatched,
        )


def test_evaluation_only_baseline_persists_oracle_failures_without_aborting(tmp_path):
    output_dir = tmp_path / "a1-one-scenario-baseline"
    summary = BenchmarkBatchRunner(require_clean_git=False).run(
        configuration_id="E0",
        system_id="A1",
        evaluation_only=True,
        output_dir=output_dir,
        scenario_ids=(RICE_ANCHOR,),
    )

    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    artifact = json.loads((output_dir / "scenarios" / f"{RICE_ANCHOR}.json").read_text(encoding="utf-8"))
    batch_summary = json.loads((output_dir / "batch_summary.json").read_text(encoding="utf-8"))
    assert summary.system_id == "A1"
    assert summary.evaluation_only is True
    assert manifest["status"] == "completed_evaluation_only_with_oracle_failures"
    assert batch_summary["status"] == manifest["status"]
    assert artifact["scenario_oracle_result"]["overall_passed"] is False


def test_a6_persists_the_same_fixture_registry_as_a_detected_unresolved_ablation(tmp_path):
    output_dir = tmp_path / "a6-fixture-ablation"
    summary = BenchmarkBatchRunner(require_clean_git=False).run(
        configuration_id="E0",
        system_id="A6",
        evaluation_only=True,
        output_dir=output_dir,
        scenario_ids=(ELIGIBLE_DIVERGENCE,),
        include_conflict_fixtures=True,
    )

    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((output_dir / "conflict_ablation_result.json").read_text(encoding="utf-8"))
    assert summary.system_id == "A6"
    assert summary.fixture_count == 60
    assert manifest["evaluation_only"] is True
    assert result["system_id"] == "A6"
    assert result["expected_behavior_passed"] is True
    assert result["detected_coordinator_fixture_count"] == 48
    assert result["resolved_coordinator_fixture_count"] == 0
    assert result["full_resolver_policy_passed_fixture_count"] == 12


def test_runner_refuses_conflict_fixtures_for_non_conflict_baselines(tmp_path):
    with pytest.raises(ExperimentProtocolError, match="only for A0 or the A6"):
        BenchmarkBatchRunner(require_clean_git=False).run(
            configuration_id="E0",
            system_id="A1",
            evaluation_only=True,
            output_dir=tmp_path / "a1-fixtures-forbidden",
            scenario_ids=(RICE_ANCHOR,),
            include_conflict_fixtures=True,
        )


def test_bounded_llm_runs_are_limited_to_the_frozen_30_site_pilot_or_all_300():
    runner = BenchmarkBatchRunner(require_clean_git=False)
    protocol = runner._read_protocol()
    configuration = protocol["experiment_configurations"]["E1"]
    pilot_ids = tuple(sorted(row["scenario_id"] for row in load_pilot_set().rows))

    runner._validate_bounded_llm_population(protocol, configuration, pilot_ids)
    with pytest.raises(ExperimentProtocolError, match="exact frozen 30-site"):
        runner._validate_bounded_llm_population(protocol, configuration, pilot_ids[:1])


def test_cli_pilot_set_option_resolves_only_the_frozen_csv(tmp_path):
    pilot = load_pilot_set()
    source_path = pilot.directory / str(pilot.manifest["scenario_file"])

    assert _frozen_pilot_scenario_ids_from_csv(source_path) == tuple(
        sorted(row["scenario_id"] for row in pilot.rows)
    )
    other = tmp_path / "other.csv"
    other.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ExperimentProtocolError, match="frozen pilot CSV"):
        _frozen_pilot_scenario_ids_from_csv(other)


def test_e1_is_gated_by_the_accepted_final_heldout_result_and_uses_v5_runtime():
    """The pilot must never silently run the legacy v4 selector after Phase 3."""
    runner = BenchmarkBatchRunner(require_clean_git=False)
    protocol = runner._read_protocol()
    evidence_path = runner.project_root / protocol["apple_gpu_pilot_preflight"]["e1_acceleration_evidence_path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    configuration, selector, _acceleration, binding = runner._validate_configuration(
        protocol,
        "E1",
        acceleration_evidence=evidence,
        model_artifact_binding=None,
    )
    assert isinstance(selector, BenchmarkLLMClientV5)
    assert configuration["bounded_llm_runtime"] == "v5.1"
    assert binding["prompt_template_version"] == PROMPT_TEMPLATE_VERSION_V5
    workflow = runner._build_workflow(
        configuration=configuration,
        system_id="A0",
        bounded_llm=selector,
    )
    assert isinstance(workflow, BenchmarkMASWorkflowV5)


def test_e1_rejects_a_changed_final_heldout_acceptance_artifact_before_pilot():
    runner = BenchmarkBatchRunner(require_clean_git=False)
    protocol = deepcopy(runner._read_protocol())
    protocol["final_v51_relevance_gate"]["acceptance_report_sha256"] = "0" * 64
    evidence_path = runner.project_root / protocol["apple_gpu_pilot_preflight"]["e1_acceleration_evidence_path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    with pytest.raises(ExperimentProtocolError, match="held-out artifact hash differs"):
        runner._validate_configuration(
            protocol,
            "E1",
            acceleration_evidence=evidence,
            model_artifact_binding=None,
        )
