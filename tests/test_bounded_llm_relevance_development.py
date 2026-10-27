"""Tests for the source-derived, non-held-out relevance development set."""
from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.bounded_llm_relevance import RelevanceBenchmarkError
from evaluation.bounded_llm_relevance_development import (
    DEVELOPMENT_SCENARIO_IDS,
    QUESTIONS_PER_ROLE,
    build_development_set,
    load_development_set,
    validate_development_questions,
)
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES


@pytest.fixture(scope="module")
def development_set(tmp_path_factory):
    output = tmp_path_factory.mktemp("relevance-development") / "development-set"
    return build_development_set(output_dir=output)


def test_builder_creates_balanced_disjoint_source_derived_development_questions(development_set):
    questions = development_set.questions
    baseline_ids = set(development_set.manifest["e1_v4_evaluation_scenario_ids"])

    assert len(questions) == len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE
    assert tuple(development_set.manifest["development_scenario_ids"]) == DEVELOPMENT_SCENARIO_IDS
    assert not (set(DEVELOPMENT_SCENARIO_IDS) & baseline_ids)
    assert development_set.manifest["scenario_overlap_with_e1_v4"] == []
    assert development_set.manifest["safe_empty_question_count"] == 30
    assert set(development_set.manifest["role_question_counts"].values()) == {QUESTIONS_PER_ROLE}
    assert all(question["usage"] == "development_only_not_heldout_evaluation" for question in questions)
    assert all(question["required_conditions"] for question in questions)
    assert all(question["disallowed_distractor_ids"] for question in questions)
    assert all(question["scenario_id"] not in baseline_ids for question in questions)


def test_loader_rejects_development_question_hash_tampering(development_set):
    path = development_set.development_dir / "development_questions.jsonl"
    original = path.read_text(encoding="utf-8")
    path.write_text(original + "\n", encoding="utf-8")
    with pytest.raises(RelevanceBenchmarkError, match="hash differs"):
        load_development_set(development_set.development_dir)
    path.write_text(original, encoding="utf-8")
    assert load_development_set(development_set.development_dir).questions == development_set.questions


def test_validator_rejects_e1_v4_scenario_reuse(development_set):
    altered = [dict(question) for question in development_set.questions]
    altered[0]["scenario_id"] = development_set.manifest["e1_v4_evaluation_scenario_ids"][0]
    with pytest.raises(RelevanceBenchmarkError, match="reuses an E1-v4 evaluation scenario"):
        validate_development_questions(
            altered,
            e1_v4_scenario_ids=development_set.manifest["e1_v4_evaluation_scenario_ids"],
        )
