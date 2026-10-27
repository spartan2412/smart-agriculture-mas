"""Tests for the isolated E2/E3 Phase 8 runner and artifact boundary."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

import config
from evaluation.apple_gpu_preflight import PILOT_MANIFEST_FILENAME, load_pilot_set
from evaluation.benchmark_batch_runner import ExperimentProtocolError
from evaluation.phase8_batch_runner import (
    Phase8BatchRunner,
    _canonical_json_hash,
    validate_phase8_acceleration_evidence,
    validate_phase8_artifact_binding,
)
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _protocol() -> dict:
    return json.loads((PROJECT_ROOT / "evaluation" / "experiment_protocol.json").read_text(encoding="utf-8"))


def _binding(*, comparison_type: str = "runtime_only") -> dict:
    required = _protocol()["e2_e3_identical_artifact_gate"]["required_fields"]
    values = {field: f"bound-{field}" for field in required}
    values["quantization_level"] = "4-bit"
    values["generation_parameters"] = {
        "temperature": 0.0,
        "maximum_tokens_per_call": 200,
        "maximum_selected_facts": 3,
        "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
        "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
    }
    return {
        "comparison_type": comparison_type,
        "comparison_limitations": (
            ["Backend-native artifacts are not runtime-only or byte-equivalent."]
            if comparison_type == "deployment_backend"
            else []
        ),
        "configurations": {
            "E2": {**values, "runtime_model_identifier": "qwen2.5:7b-instruct"},
            "E3": {**values, "runtime_model_identifier": "/tmp/phase8-mlx-model"},
        },
    }


def _evidence(configuration_id: str, binding: dict) -> dict:
    active = binding["configurations"][configuration_id]
    pilot = load_pilot_set()
    return {
        "status": "verified",
        "configuration_id": configuration_id,
        "model_artifact_binding_sha256": _canonical_json_hash(binding),
        "hardware": {"system": "Darwin", "machine": "arm64", "unified_memory_bytes": 1},
        "pilot_set": {
            "scenario_count": 30,
            "unique_site_count": 30,
            "pilot_identity_sha256": pilot.manifest["pilot_identity_sha256"],
            "scenario_file_sha256": pilot.manifest["scenario_file_sha256"],
            "manifest_sha256": sha256((pilot.directory / PILOT_MANIFEST_FILENAME).read_bytes()).hexdigest(),
        },
        "backend_evidence": {
            "backend": "ollama" if configuration_id == "E2" else "mlx-lm",
            "model": {
                "runtime_model_identifier": active["runtime_model_identifier"],
                "model_artifact_sha256": active["model_artifact_sha256"],
                "quantization_level": active["quantization_level"],
            },
            "acceleration": {
                "observed_model_resident_in_gpu_memory": True,
                "observed_gpu_resident_bytes": 1,
            },
            "checks": {"runtime_ready": True},
        },
    }


def test_runtime_only_binding_refuses_any_required_artifact_difference():
    binding = _binding()
    binding["configurations"]["E3"]["model_artifact_sha256"] = "different-artifact"
    with pytest.raises(ExperimentProtocolError, match="cannot be labelled runtime_only"):
        validate_phase8_artifact_binding(_protocol(), "E2", binding)


def test_binding_refuses_generation_settings_that_differ_from_frozen_v51_runtime():
    binding = _binding()
    binding["configurations"]["E2"]["generation_parameters"]["temperature"] = 0.2
    with pytest.raises(ExperimentProtocolError, match="frozen v5.1 selection runtime"):
        validate_phase8_artifact_binding(_protocol(), "E2", binding)


def test_deployment_backend_binding_allows_format_difference_but_not_semantic_difference():
    binding = _binding(comparison_type="deployment_backend")
    binding["configurations"]["E3"]["model_artifact_sha256"] = "backend-native-artifact"
    binding["configurations"]["E3"]["quantization_method"] = "mlx_4bit"
    normalized = validate_phase8_artifact_binding(_protocol(), "E3", binding)
    assert normalized["comparison_type"] == "deployment_backend"

    broken = deepcopy(binding)
    broken["configurations"]["E3"]["parameter_count"] = "different-size"
    with pytest.raises(ExperimentProtocolError, match="base model family and parameter count"):
        validate_phase8_artifact_binding(_protocol(), "E3", broken)


def test_phase8_acceleration_evidence_requires_the_bound_artifact():
    binding = _binding()
    active = binding["configurations"]["E2"]
    evidence = _evidence("E2", binding)
    validate_phase8_acceleration_evidence(evidence, configuration_id="E2", binding=active)

    evidence["backend_evidence"]["model"]["model_artifact_sha256"] = "wrong"
    with pytest.raises(ExperimentProtocolError, match="artifact hash"):
        validate_phase8_acceleration_evidence(evidence, configuration_id="E2", binding=active)


def test_e2_uses_the_v5_selector_without_modifying_the_historical_runner(monkeypatch):
    binding = _binding()
    monkeypatch.setattr(config, "LLM_BACKEND", "ollama")
    monkeypatch.setattr(config, "OLLAMA_MODEL", "qwen2.5:7b-instruct")
    configuration, selector, _evidence_value, normalized = Phase8BatchRunner(
        require_clean_git=False
    )._validate_configuration(
        _protocol(),
        "E2",
        acceleration_evidence=_evidence("E2", binding),
        model_artifact_binding=binding,
    )
    assert isinstance(selector, BenchmarkLLMClientV5)
    assert configuration["bounded_llm_runtime"] == "v5.1"
    assert normalized["phase8_runner_version"] == "1.0"
