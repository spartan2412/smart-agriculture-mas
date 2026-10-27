"""Regression checks for the frozen Apple-GPU pilot preflight boundary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.apple_gpu_preflight import (
    AppleGPUPreflightError,
    build_pilot_set,
    load_pilot_set,
    validate_acceleration_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = PROJECT_ROOT / "evaluation" / "experiment_protocol.json"


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _e1_evidence() -> dict:
    relative = _protocol()["apple_gpu_pilot_preflight"]["e1_acceleration_evidence_path"]
    return json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))


def test_frozen_pilot_set_contains_every_verified_anchor_once():
    pilot = load_pilot_set()

    assert pilot.manifest["scenario_count"] == 30
    assert pilot.manifest["unique_site_count"] == 30
    assert len(pilot.rows) == 30
    assert len({row["scenario_id"] for row in pilot.rows}) == 30
    assert len({row["site_id"] for row in pilot.rows}) == 30
    assert {row["crop"] for row in pilot.rows} == {
        "rice", "wheat", "maize", "chickpea", "soybean", "tomato"
    }
    assert {row["selection_rule"] for row in pilot.rows} == {
        "one_verified_anchor_per_final_study_site"
    }


def test_pilot_set_builder_reproduces_the_frozen_identity(tmp_path):
    rebuilt = build_pilot_set(output_dir=tmp_path / "pilot")
    frozen = load_pilot_set()

    assert rebuilt.manifest["pilot_identity_sha256"] == frozen.manifest["pilot_identity_sha256"]
    assert tuple(rebuilt.rows) == tuple(frozen.rows)


def test_verified_e1_evidence_requires_exact_model_and_pilot_identity():
    protocol = _protocol()
    evidence = _e1_evidence()

    validate_acceleration_evidence(evidence, protocol=protocol, configuration_id="E1")
    assert evidence["status"] == "verified"
    assert evidence["backend_evidence"]["acceleration"]["observed_gpu_resident_bytes"] > 0
    assert evidence["hardware"]["unified_memory_bytes"] > 0
    assert evidence["hardware"]["pytorch_mps"]["used_as_ollama_acceleration_proof"] is False

    altered = json.loads(json.dumps(evidence))
    altered["backend_evidence"]["model"]["quantization"] = "Q8_0"
    with pytest.raises(AppleGPUPreflightError, match="quantization"):
        validate_acceleration_evidence(altered, protocol=protocol, configuration_id="E1")
