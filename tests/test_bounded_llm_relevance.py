"""Regression tests for the frozen bounded-LLM relevance benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from evaluation.bounded_llm_relevance import (
    BoundedLLMRelevanceRunner,
    CANONICAL_SCENARIO_IDS,
    QUESTIONS_PER_ROLE,
    RelevanceBenchmarkError,
    build_relevance_benchmark,
    load_relevance_benchmark,
    validate_relevance_questions,
)
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES, BenchmarkLLMClient


class ExpectedSelectionClient:
    """Offline double returning the frozen expected IDs for each test prompt."""

    def __init__(self, expected: Mapping[tuple[str, str], list[str]]) -> None:
        self.expected = expected

    def generate_json(self, _system_prompt: str, user_prompt: str, **_: Any) -> Mapping[str, Any]:
        request = json.loads(user_prompt)
        return {
            "selected_fact_ids": self.expected[(request["agent_name"], request["scenario_id"])],
            "focus": "context",
        }


@pytest.fixture(scope="module")
def frozen_benchmark(tmp_path_factory):
    output = tmp_path_factory.mktemp("relevance") / "benchmark"
    return build_relevance_benchmark(output_dir=output)


def test_builder_creates_a_balanced_source_derived_96_question_benchmark(frozen_benchmark):
    benchmark = frozen_benchmark

    assert len(benchmark.questions) == len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE
    assert tuple(benchmark.manifest["canonical_scenario_ids"]) == CANONICAL_SCENARIO_IDS
    assert set(benchmark.manifest["role_question_counts"]) == set(BOUND_LLM_AGENT_NAMES)
    assert set(benchmark.manifest["role_question_counts"].values()) == {QUESTIONS_PER_ROLE}
    assert any(not question["expected_admissible_fact_ids"] for question in benchmark.questions)
    assert all(question["required_conditions"] for question in benchmark.questions)
    assert all(question["disallowed_distractor_ids"] for question in benchmark.questions)
    assert all(
        set(question["expected_admissible_fact_ids"]).issubset(question["allowed_fact_ids"])
        for question in benchmark.questions
    )
    assert all(
        set(question["allowed_source_document_ids"])
        == {
            source_id
            for fact in question["allowed_facts"]
            for source_id in fact["source_document_ids"]
        }
        for question in benchmark.questions
    )
    assert set(benchmark.manifest["source_artifact_sha256"])


def test_loader_rejects_any_question_file_hash_tampering(frozen_benchmark):
    path = frozen_benchmark.benchmark_dir / "relevance_questions.jsonl"
    original = path.read_text(encoding="utf-8")
    path.write_text(original + "\n", encoding="utf-8")
    with pytest.raises(RelevanceBenchmarkError, match="hash differs"):
        load_relevance_benchmark(frozen_benchmark.benchmark_dir)
    path.write_text(original, encoding="utf-8")
    assert load_relevance_benchmark(frozen_benchmark.benchmark_dir).questions == frozen_benchmark.questions


def test_validator_rejects_expected_id_outside_immutable_allowed_set(frozen_benchmark):
    altered = [dict(question) for question in frozen_benchmark.questions]
    altered[0]["expected_admissible_fact_ids"] = ["fabricated_fact"]
    with pytest.raises(RelevanceBenchmarkError, match="outside its allowed facts"):
        validate_relevance_questions(altered)


def test_runner_persists_per_question_and_aggregate_metrics_with_an_offline_double(
    frozen_benchmark,
    tmp_path,
):
    expected = {
        (question["agent_name"], question["scenario_id"]): list(question["expected_admissible_fact_ids"])
        for question in frozen_benchmark.questions
    }
    runner = BoundedLLMRelevanceRunner(
        benchmark=frozen_benchmark,
        bounded_llm=BenchmarkLLMClient(
            client=ExpectedSelectionClient(expected), enabled=True, required=True
        ),
        require_clean_git=False,
    )
    output_dir = tmp_path / "result"
    summary = runner.run(output_dir=output_dir)

    aggregate = json.loads((output_dir / "aggregate_relevance_metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert summary.question_count == 96
    assert summary.accepted_selection_count == 96
    assert summary.invalid_structured_output_count == 0
    assert summary.fallback_count == 0
    assert aggregate["overall"]["fact_selection_precision"] == 1.0
    assert aggregate["overall"]["fact_selection_recall"] == 1.0
    assert aggregate["overall"]["safe_empty_selection_accuracy"] == 1.0
    assert manifest["bounded_llm_invocation_count"] == 96
    assert len(list((output_dir / "per_question").glob("*.json"))) == 96
