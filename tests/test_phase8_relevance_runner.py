"""Tests for the isolated Phase 8 relevance-transfer runner."""
from __future__ import annotations

import json

from evaluation.phase8_batch_runner import Phase8BatchRunner
from evaluation.phase8_relevance_runner import Phase8RelevanceRunner
from llm.bounded_selection_v5 import BenchmarkLLMClientV5


class _SafeEmptyJSONClient:
    """A deterministic test double; selection quality is not under test here."""

    def generate_json(self, *_args, **_kwargs):
        return {"selected_fact_ids": []}


def test_phase8_transfer_runner_persists_all_frozen_questions_without_claiming_a_new_heldout_protocol(
    tmp_path, monkeypatch
):
    selector = BenchmarkLLMClientV5(client=_SafeEmptyJSONClient(), enabled=True, required=True)
    configuration = {
        "backend": "ollama",
        "bounded_llm_runtime": "v5.1",
        "benchmark_llm_enabled": True,
    }
    binding = {
        "comparison_type": "deployment_backend",
        "comparison_limitations": ["Backend-native artifacts are not runtime-only or byte-equivalent."],
        "binding_document_sha256": "test-binding",
        "E2": {"runtime_model_identifier": "test-qwen-14b"},
        "E3": {"runtime_model_identifier": "test-mlx-14b"},
    }
    monkeypatch.setattr(
        Phase8BatchRunner,
        "_validate_configuration",
        lambda self, _protocol, _configuration_id, **_kwargs: (
            configuration,
            selector,
            {"status": "verified"},
            binding,
        ),
    )

    runner = Phase8RelevanceRunner(
        configuration_id="E2",
        acceleration_evidence={"status": "verified"},
        model_artifact_binding={"unused": "mocked"},
        require_clean_git=False,
    )
    summary = runner.run(output_dir=tmp_path / "phase8-transfer")

    manifest = json.loads((summary.output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    acceptance = json.loads((summary.output_dir / "acceptance_report.json").read_text(encoding="utf-8"))
    assert summary.question_count == 96
    assert manifest["configuration_id"] == "E2"
    assert manifest["new_heldout_protocol"] is False
    assert acceptance["new_heldout_protocol"] is False
    assert len(list((summary.output_dir / "per_question").glob("*.json"))) == 96
