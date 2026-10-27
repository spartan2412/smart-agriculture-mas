"""Tests for the final v5.1 held-out runner using no real model calls."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import pytest

from evaluation.bounded_llm_relevance import RelevanceBenchmarkError
from evaluation.bounded_llm_relevance_heldout import load_heldout_set
from evaluation.bounded_llm_relevance_v5_heldout import (
    DEFAULT_EXPERIMENT_MANIFEST_PATH,
    V51FinalHeldoutRelevanceRunner,
    load_final_heldout_experiment_manifest,
)
from llm.bounded_selection_v5 import BenchmarkLLMClientV5, V5CandidatePackager


@pytest.fixture
def archived_acceleration_experiment_manifest() -> Path:
    """Redirect the historical preflight record without changing its hash."""
    manifest = json.loads(DEFAULT_EXPERIMENT_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["e1_model_and_acceleration_boundary"]["acceleration_evidence_path"] = (
        "results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/"
        "e1-apple-gpu-preflight/acceleration_evidence.json"
    )
    path = DEFAULT_EXPERIMENT_MANIFEST_PATH.parent / ".pytest-archived-experiment-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


class ScriptedJSONClient:
    """Offline deterministic double keyed by immutable role/scenario identity."""

    def __init__(self, selections: Mapping[tuple[str, str], Any], *, raise_errors: bool = False) -> None:
        self.selections = selections
        self.raise_errors = raise_errors
        self.calls: list[Mapping[str, Any]] = []

    def generate_json(self, _system_prompt: str, user_prompt: str, **_: Any) -> Any:
        request = json.loads(user_prompt)
        self.calls.append(request)
        if self.raise_errors:
            raise RuntimeError("offline_test_backend_failure")
        selected = self.selections[(request["agent_name"], request["scenario_id"])]
        if selected == "invalid_schema":
            return {"selected_fact_ids": "not-a-list"}
        return {"selected_fact_ids": selected, "focus": "context"}


def _expected_selections() -> Mapping[tuple[str, str], list[str]]:
    return {
        (question["agent_name"], question["scenario_id"]): list(question["expected_admissible_fact_ids"])
        for question in load_heldout_set().questions
    }


def _runner(
    client: ScriptedJSONClient,
    *,
    required: bool = True,
    experiment_manifest_path: Path = DEFAULT_EXPERIMENT_MANIFEST_PATH,
) -> V51FinalHeldoutRelevanceRunner:
    return V51FinalHeldoutRelevanceRunner(
        bounded_llm=BenchmarkLLMClientV5(client=client, enabled=True, required=required),
        experiment_manifest_path=experiment_manifest_path,
        require_clean_git=False,
        test_mode=True,
    )


def test_final_heldout_runner_persists_correct_and_safe_empty_mocked_selections(
    tmp_path: Path,
    archived_acceleration_experiment_manifest: Path,
):
    selections = _expected_selections()
    client = ScriptedJSONClient(selections)
    output = tmp_path / "correct-final-heldout"
    summary = _runner(client, experiment_manifest_path=archived_acceleration_experiment_manifest).run(output_dir=output)

    aggregate = json.loads((output / "aggregate_final_heldout_metrics.json").read_text(encoding="utf-8"))
    acceptance = json.loads((output / "final_acceptance_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    safe_empty = json.loads((output / "per_question" / "HOLDOUT_REL_WEATHER_01.json").read_text(encoding="utf-8"))

    assert summary.question_count == 96
    assert summary.accepted_selection_count == 96
    assert summary.invalid_structured_output_count == 0
    assert summary.fallback_count == 0
    assert summary.all_relevance_thresholds_pass is True
    assert len(client.calls) == 96
    assert aggregate["overall"]["fact_selection_precision"] == 1.0
    assert aggregate["overall"]["safe_empty_selection_accuracy"] == 1.0
    assert acceptance["all_relevance_thresholds_pass"] is True
    assert manifest["final_research_result_permitted"] is True
    assert safe_empty["result"]["expected_fact_ids"] == []
    assert safe_empty["result"]["selected_fact_ids"] == []


def test_final_heldout_runner_records_invalid_json_as_visible_nonaccepted_output(
    tmp_path: Path,
    archived_acceleration_experiment_manifest: Path,
):
    selections = {key: "invalid_schema" for key in _expected_selections()}
    output = tmp_path / "invalid-final-heldout"
    summary = _runner(
        ScriptedJSONClient(selections),
        experiment_manifest_path=archived_acceleration_experiment_manifest,
    ).run(output_dir=output)
    aggregate = json.loads((output / "aggregate_final_heldout_metrics.json").read_text(encoding="utf-8"))
    acceptance = json.loads((output / "final_acceptance_report.json").read_text(encoding="utf-8"))

    assert summary.accepted_selection_count == 0
    assert summary.invalid_structured_output_count == 96
    assert aggregate["overall"]["invalid_structured_output_rate"] == 1.0
    assert acceptance["all_relevance_thresholds_pass"] is False
    assert acceptance["checks"]["invalid_structured_output_rate"] is False


def test_final_heldout_runner_records_visible_fallbacks_without_model_access(
    tmp_path: Path,
    archived_acceleration_experiment_manifest: Path,
):
    client = ScriptedJSONClient(_expected_selections(), raise_errors=True)
    output = tmp_path / "fallback-final-heldout"
    summary = _runner(
        client,
        required=False,
        experiment_manifest_path=archived_acceleration_experiment_manifest,
    ).run(output_dir=output)
    aggregate = json.loads((output / "aggregate_final_heldout_metrics.json").read_text(encoding="utf-8"))
    acceptance = json.loads((output / "final_acceptance_report.json").read_text(encoding="utf-8"))

    assert summary.accepted_selection_count == 0
    assert summary.fallback_count == 96
    assert aggregate["overall"]["fallback_rate"] == 1.0
    assert acceptance["all_relevance_thresholds_pass"] is False
    assert acceptance["checks"]["fallback_rate"] is False


def test_final_heldout_runner_records_an_irrelevant_but_allowed_selection(
    tmp_path: Path,
    archived_acceleration_experiment_manifest: Path,
):
    questions = load_heldout_set().questions
    selections = dict(_expected_selections())
    packager = V5CandidatePackager()
    target = next(question for question in questions if question["agent_name"] == "official_operations_rag_agent")
    packaged = packager.package_development_facts(
        agent_name=target["agent_name"],
        facts=target["allowed_facts"],
        question=target["farmer_question"],
    )
    irrelevant = next(
        fact["fact_id"]
        for fact in packaged.facts
        if fact["fact_id"] not in set(target["expected_admissible_fact_ids"])
    )
    selections[(target["agent_name"], target["scenario_id"])] = [irrelevant]
    output = tmp_path / "irrelevant-final-heldout"
    _runner(
        ScriptedJSONClient(selections),
        experiment_manifest_path=archived_acceleration_experiment_manifest,
    ).run(output_dir=output)
    record = json.loads((output / "per_question" / f"{target['question_id']}.json").read_text(encoding="utf-8"))

    assert record["result"]["result_status"] == "accepted"
    assert record["result"]["selected_fact_ids"] == [irrelevant]
    assert record["result"]["fact_intersection_count"] == 0


def test_final_heldout_experiment_manifest_rejects_changed_runtime_hash(tmp_path: Path):
    altered = json.loads(DEFAULT_EXPERIMENT_MANIFEST_PATH.read_text(encoding="utf-8"))
    altered["v5_runtime_boundary"]["files_sha256"]["llm/bounded_selection_v5.py"] = "0" * 64
    path = tmp_path / "altered-experiment-manifest.json"
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(RelevanceBenchmarkError, match="v5 runtime hash differs"):
        load_final_heldout_experiment_manifest(path)


def test_heldout_loader_rejects_changed_source_or_acceptance_criteria(tmp_path: Path):
    source = Path("data/llm_relevance_heldout").resolve()
    copied = tmp_path / "heldout-copy"
    shutil.copytree(source, copied)
    altered_manifest = json.loads((copied / "manifest.json").read_text(encoding="utf-8"))
    source_key = next(iter(altered_manifest["immutable_evidence_artifact_sha256"]))
    altered_manifest["immutable_evidence_artifact_sha256"][source_key] = "0" * 64
    (copied / "manifest.json").write_text(json.dumps(altered_manifest), encoding="utf-8")
    with pytest.raises(RelevanceBenchmarkError, match="Held-out evidence hash differs"):
        load_heldout_set(copied)

    shutil.rmtree(copied)
    shutil.copytree(source, copied)
    criteria_path = copied / "acceptance_criteria.json"
    criteria = json.loads(criteria_path.read_text(encoding="utf-8"))
    criteria["relevance_thresholds"]["minimum_fact_selection_precision"] = 0.99
    criteria_path.write_text(json.dumps(criteria), encoding="utf-8")
    with pytest.raises(RelevanceBenchmarkError, match="acceptance criteria hash differs"):
        load_heldout_set(copied)


def test_final_runner_rejects_noncanonical_real_output_directory_without_test_mode(
    tmp_path: Path,
    archived_acceleration_experiment_manifest: Path,
):
    runner = V51FinalHeldoutRelevanceRunner(
        bounded_llm=BenchmarkLLMClientV5(
            client=ScriptedJSONClient(_expected_selections()), enabled=True, required=True
        ),
        experiment_manifest_path=archived_acceleration_experiment_manifest,
        require_clean_git=False,
        test_mode=False,
    )
    with pytest.raises(RelevanceBenchmarkError, match="canonical output directory"):
        runner.run(output_dir=tmp_path / "attempted-second-final-output")
