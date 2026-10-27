"""Focused tests for the Phase 9 result-pair verifier."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from evaluation.reproducibility_verification import (
    ReproducibilityVerificationError,
    verify_fixture_reproducibility,
    verify_reference_artifact_hashes,
    verify_run_reproducibility,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _artifact(scenario_id: str, *, selected: str = "claim_1") -> dict[str, object]:
    selection = {
        "status": "accepted",
        "selected_fact_ids": [selected],
        "prompt_sha256": "prompt",
        "prompt_template_version": "v5",
        "selection_contract_version": "contract",
        "candidate_packaging_version": "packaging",
        "request_sufficiency": "scope",
        "selection_policy": {"mode": "one"},
        "selection_is_safety_non_authoritative": True,
    }
    roles = (
        "weather_context_agent",
        "soil_context_agent",
        "satellite_ndvi_context_agent",
        "market_evidence_agent",
        "fertilizer_baseline_agent",
        "official_operations_rag_agent",
        "provenance_aware_coordinator_agent",
        "farmer_explanation_citation_agent",
    )
    claims = [
        {
            "agent_name": role,
            "claim_id": f"claim_{index}",
            "metadata": {
                "bounded_llm": {
                    **selection,
                    "selected_fact_ids": [selected if index == 1 else f"claim_{index}"],
                }
            },
        }
        for index, role in enumerate(roles, start=1)
    ]
    run = {"scenario_id": scenario_id, "claims": claims, "decision": {"status": "safe"}, "farmer_message": "plan", "retrieved_passages": [], "conflicts": []}
    oracle = {"structural_fingerprint": "fingerprint", "checks": [{"name": "scope", "passed": True}]}
    return {"scenario_identity": {"scenario_id": scenario_id}, "benchmark_run": run, "scenario_oracle_result": oracle, "runtime": {"elapsed_ms": 1}}


def _manifest(configuration_id: str, artifact_rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "status": "completed",
        "configuration_id": configuration_id,
        "git": {"clean_at_start": True},
        "protocol": {"verified_artifacts": artifact_rows},
    }


def _build_run(root: Path, *, configuration: str, artifact: dict[str, object], source_row: dict[str, str]) -> None:
    _write_json(root / "run_manifest.json", _manifest(configuration, [source_row]))
    scenario_id = artifact["scenario_identity"]["scenario_id"]
    _write_json(root / "scenarios" / f"{scenario_id}.json", artifact)


def test_reference_hashes_report_live_artifact_status(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("frozen", encoding="utf-8")
    manifest = _manifest("E0", [{"path": "source.txt", "sha256": sha256(source.read_bytes()).hexdigest()}])
    checks = verify_reference_artifact_hashes(manifest, project_root=tmp_path)
    assert len(checks) == 1
    assert checks[0].passed is True
    source.write_text("changed", encoding="utf-8")
    assert verify_reference_artifact_hashes(manifest, project_root=tmp_path)[0].passed is False


def test_e0_requires_exact_semantic_trace_but_ignores_runtime_telemetry(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("frozen", encoding="utf-8")
    source_row = {"path": "source.txt", "sha256": sha256(source.read_bytes()).hexdigest()}
    reference = tmp_path / "reference"
    reproduction = tmp_path / "reproduction"
    reference_artifact = _artifact("S1")
    reproduction_artifact = _artifact("S1")
    reproduction_artifact["runtime"] = {"elapsed_ms": 99999, "process_peak_memory_bytes": 123}
    _build_run(reference, configuration="E0", artifact=reference_artifact, source_row=source_row)
    _build_run(reproduction, configuration="E0", artifact=reproduction_artifact, source_row=source_row)

    result = verify_run_reproducibility(
        configuration_id="E0",
        reference_directory=reference,
        reproduction_directory=reproduction,
        project_root=tmp_path,
        expected_scenario_count=1,
    )
    assert result.all_required_checks_passed is True
    assert result.semantic_trace_match_count == 1


def test_e1_reports_bounded_selection_change_as_a_failed_reproduction(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("frozen", encoding="utf-8")
    source_row = {"path": "source.txt", "sha256": sha256(source.read_bytes()).hexdigest()}
    reference = tmp_path / "reference"
    reproduction = tmp_path / "reproduction"
    _build_run(reference, configuration="E1", artifact=_artifact("S1", selected="claim_1"), source_row=source_row)
    _build_run(reproduction, configuration="E1", artifact=_artifact("S1", selected="claim_2"), source_row=source_row)

    result = verify_run_reproducibility(
        configuration_id="E1",
        reference_directory=reference,
        reproduction_directory=reproduction,
        project_root=tmp_path,
        expected_scenario_count=1,
    )
    assert result.bounded_selection_match_count == 0
    assert result.all_required_checks_passed is False


def test_fixture_reproduction_requires_exact_completed_60_record_outputs(tmp_path):
    reference = tmp_path / "reference"
    reproduction = tmp_path / "reproduction"
    semantic = {"fixture_count": 60, "all_passed": True, "records": [{"fixture_id": "F1"}]}
    trace = [{
        "fixture_id": "F1",
        "base_scenario_id": "S1",
        "fixture_family": "coordinator_resolution",
        "status": "passed",
        "expected_match": True,
        "claims": [],
        "conflicts": [],
        "fixture_conflicts": [],
        "background_conflicts": [],
        "decision": {"status": "safe"},
    }]
    for directory in (reference, reproduction):
        _write_json(directory / "fixture_oracle_result.json", semantic)
        _write_json(directory / "conflict_fixture_runs.json", trace)
    result = verify_fixture_reproducibility(
        fixture_suite="conflict",
        reference_directory=reference,
        reproduction_directory=reproduction,
    )
    assert result.all_required_checks_passed is True
    assert result.normalised_policy_trace_match is True
    changed = [dict(trace[0])]
    changed[0]["status"] = "failed"
    _write_json(reproduction / "conflict_fixture_runs.json", changed)
    assert verify_fixture_reproducibility(
        fixture_suite="conflict",
        reference_directory=reference,
        reproduction_directory=reproduction,
    ).all_required_checks_passed is False
