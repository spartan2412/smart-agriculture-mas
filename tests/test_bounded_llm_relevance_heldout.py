"""Integrity tests for the final source-derived v5 held-out relevance set."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from evaluation.bounded_llm_relevance import RelevanceBenchmarkError
from evaluation.bounded_llm_relevance_heldout import (
    HELDOUT_ACCEPTANCE_CRITERIA,
    HELDOUT_SCENARIO_IDS,
    load_heldout_set,
)
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES


@pytest.fixture(scope="module")
def heldout_set():
    """Use the immutable final set; its historical builder is not rerun."""
    return load_heldout_set()


def test_frozen_heldout_set_has_balanced_disjoint_source_derived_questions(heldout_set):
    questions = heldout_set.questions
    manifest = heldout_set.manifest
    assert len(questions) == 96
    assert tuple(manifest["heldout_scenario_ids"]) == HELDOUT_SCENARIO_IDS
    assert manifest["scenario_count"] == 12
    assert manifest["site_count"] == 6
    assert manifest["source_set_scenario_overlap"] == []
    assert manifest["source_set_site_overlap"] == []
    assert manifest["safe_empty_question_count"] == 30
    assert set(manifest["role_question_counts"].values()) == {12}
    assert all(question["usage"] == manifest["usage"] for question in questions)
    assert all(question["site_id"] not in manifest["prohibited_v4_or_development_site_ids"] for question in questions)
    rag = [question for question in questions if question["agent_name"] == "official_operations_rag_agent"]
    assert len(rag) == 12
    assert all(question["expected_admissible_passage_ids"] for question in rag)
    assert all("required condition" in question["farmer_question"].lower() for question in rag)
    assert set(question["agent_name"] for question in questions) == set(BOUND_LLM_AGENT_NAMES)


def test_heldout_loader_rejects_question_file_tampering(heldout_set, tmp_path):
    copied = tmp_path / "heldout-copy"
    shutil.copytree(heldout_set.heldout_dir, copied)
    path = copied / "heldout_questions.jsonl"
    original = path.read_text(encoding="utf-8")
    path.write_text(original + "\n", encoding="utf-8")
    with pytest.raises(RelevanceBenchmarkError, match="question file hash differs"):
        load_heldout_set(copied)
    path.write_text(original, encoding="utf-8")
    assert load_heldout_set(copied).questions == heldout_set.questions


def test_heldout_manifest_embeds_pre_registered_thresholds(heldout_set):
    criteria = json.loads((heldout_set.heldout_dir / "acceptance_criteria.json").read_text(encoding="utf-8"))
    assert criteria == HELDOUT_ACCEPTANCE_CRITERIA
    assert criteria["relevance_thresholds"]["minimum_safe_empty_selection_accuracy"] == 0.80
    assert criteria["post_relevance_pilot_gate"]["maximum_structural_oracle_regressions"] == 0
