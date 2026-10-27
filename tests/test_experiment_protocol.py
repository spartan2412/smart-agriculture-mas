"""Regression checks for the frozen experiment-protocol snapshot."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = PROJECT_ROOT / "evaluation" / "experiment_protocol.json"


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_protocol_freezes_current_benchmark_and_oracle_boundary():
    protocol = _protocol()

    # Version 1.5 retains the cross-domain context citation rule and adds
    # direct rendering of source-recorded nutrient/IPM policy details.
    assert protocol["protocol_version"] == "1.5"
    assert protocol["benchmark"]["normal_scenario_count"] == 300
    assert protocol["benchmark"]["final_site_count"] == 30
    assert protocol["benchmark"]["direct_farm_actions_permitted"] is False
    assert protocol["oracle"]["oracle_version"] == "1.4"
    assert protocol["oracle"]["normal_scenario_check_count"] == 20
    assert protocol["conflict_evaluation"]["fixture_count"] == 60
    assert protocol["bounded_llm_policy"]["enabled_agent_count"] == 8
    relevance = protocol["source_derived_relevance_benchmark"]
    assert relevance["status"] == "frozen_source_derived_questions_pending_model_runs"
    assert relevance["benchmark_version"] == "1.0"
    assert relevance["question_count"] == 96
    assert relevance["questions_per_role"] == 12
    output_contract = protocol["farmer_output_contract"]
    assert output_contract["version"] == "2.2"
    assert output_contract["bounded_llm_interface_change"] is False


def test_protocol_hash_snapshot_matches_current_frozen_artifacts():
    protocol = _protocol()

    for relative_path, expected_hash in protocol["frozen_artifact_sha256"].items():
        artifact = PROJECT_ROOT / relative_path
        assert artifact.is_file(), relative_path
        assert sha256(artifact.read_bytes()).hexdigest() == expected_hash, relative_path


def test_protocol_requires_a_fair_e2_e3_artifact_binding_and_planned_comparisons():
    protocol = _protocol()
    configurations = protocol["experiment_configurations"]

    assert set(configurations) == {"E0", "E1", "E2", "E3"}
    assert configurations["E0"]["benchmark_llm_enabled"] is False
    assert configurations["E1"]["quantization"] == "Q4_K_M"
    assert configurations["E2"]["artifact_binding_status"] == "required_before_execution"
    assert configurations["E3"]["artifact_binding_status"] == "required_before_execution"
    assert "model_artifact_sha256" in protocol["e2_e3_identical_artifact_gate"]["required_fields"]
    assert {item["id"] for item in protocol["architecture_comparisons"]} == {
        "A0", "A1", "A2", "A3", "A4", "A5", "A6"
    }
