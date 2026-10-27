"""Tests for the explicitly non-held-out v5 development runner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.bounded_llm_relevance_development import load_development_set
from evaluation.bounded_llm_relevance_v5_development import (
    DEVELOPMENT_ONLY_USAGE,
    V5DevelopmentRelevanceRunner,
    project_plan_or_operation_ids_from_fact_ids,
    reanalyze_v5_development_metrics,
)
from llm.bounded_selection_v5 import BenchmarkLLMClientV5, V5CandidatePackager


class FirstCandidateJSONClient:
    """Fast deterministic double; it never contacts a model backend."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> dict[str, Any]:
        request = json.loads(user_prompt)
        self.calls.append(request)
        return {"selected_fact_ids": [request["allowed_facts"][0]["fact_id"]], "focus": "context"}


def test_v5_development_packager_keeps_expected_ids_and_exposes_source_conditions():
    development_set = load_development_set()
    packager = V5CandidatePackager()
    for question in development_set.questions:
        packaged = packager.package_development_facts(
            agent_name=question["agent_name"],
            facts=question["allowed_facts"],
            question=question["farmer_question"],
        )
        packaged_ids = {fact["fact_id"] for fact in packaged.facts}
        assert set(question["expected_admissible_fact_ids"]).issubset(packaged_ids)
        assert packaged_ids.issubset(set(question["allowed_fact_ids"]))
        assert all("source_document_ids=" in fact["text"] for fact in packaged.facts)
        assert all("does_not_establish=" in fact["text"] for fact in packaged.facts)
        if not question["expected_admissible_fact_ids"]:
            assert packaged.request_sufficiency == "no_candidate_authorizes_requested_farm_action"


def test_v5_development_runner_persists_an_explicitly_nonheldout_result(tmp_path: Path):
    client = FirstCandidateJSONClient()
    runner = V5DevelopmentRelevanceRunner(
        bounded_llm=BenchmarkLLMClientV5(client=client, enabled=True, required=True),
        require_clean_git=False,
    )
    output_dir = tmp_path / "v5-development-iteration"
    summary = runner.run(output_dir=output_dir)

    assert summary.question_count == 96
    assert summary.usage == DEVELOPMENT_ONLY_USAGE
    assert len(client.calls) == 96
    assert client.calls[0]["request_sufficiency"] == "no_candidate_authorizes_requested_farm_action"
    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    aggregate = json.loads((output_dir / "aggregate_development_metrics.json").read_text(encoding="utf-8"))
    assert manifest["usage"] == DEVELOPMENT_ONLY_USAGE
    assert manifest["not_heldout_evaluation"] is True
    assert manifest["final_research_result_permitted"] is False
    assert aggregate["usage"] == DEVELOPMENT_ONLY_USAGE
    assert aggregate["not_heldout_evaluation"] is True
    first = json.loads((output_dir / "per_question" / "DEV_REL_WEATHER_01.json").read_text(encoding="utf-8"))
    assert first["result"]["usage"] == DEVELOPMENT_ONLY_USAGE
    assert first["result"]["not_heldout_evaluation"] is True
    assert first["result"]["selection_contract_version"].startswith("v5")
    assert first["result"]["request_sufficiency"] == "no_candidate_authorizes_requested_farm_action"


def test_source_fact_plan_projection_excludes_a_boundary_only_fertilizer_case():
    questions = {question["question_id"]: question for question in load_development_set().questions}
    boundary_only = questions["DEV_REL_FERTILIZER_01"]
    policy_and_boundary = questions["DEV_REL_FERTILIZER_02"]

    assert project_plan_or_operation_ids_from_fact_ids(
        boundary_only, boundary_only["expected_admissible_fact_ids"]
    ) == ()
    assert project_plan_or_operation_ids_from_fact_ids(
        policy_and_boundary, policy_and_boundary["expected_admissible_fact_ids"]
    ) == (
        "ANCHOR_PF_PB_MANSA_RICE_KHARIF_20251130__fertilizer_policy",
    )


def test_metric_reanalysis_preserves_model_trace_and_writes_a_corrected_sidecar(tmp_path: Path):
    client = FirstCandidateJSONClient()
    run_dir = tmp_path / "v5-development-iteration"
    V5DevelopmentRelevanceRunner(
        bounded_llm=BenchmarkLLMClientV5(client=client, enabled=True, required=True),
        require_clean_git=False,
    ).run(output_dir=run_dir)

    report = reanalyze_v5_development_metrics(run_dir)
    assert report["usage"] == DEVELOPMENT_ONLY_USAGE
    assert "DEV_REL_FERTILIZER_01" in report["changed_question_ids"]
    assert (run_dir / "metric_reanalysis_source_fact_projection.json").is_file()
