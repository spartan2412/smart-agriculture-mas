"""Run the final immutable v5.1 held-out relevance evaluation exactly once.

This module is intentionally separate from the observed E1-v4 runner and the
v5.1 development runner.  It accepts only the hash-checked final held-out set,
requires the frozen E1 experiment-boundary manifest, persists a complete
selection trace, and reports the thresholds registered *before* any model
call.  It never changes a prompt, candidate, label, source, or threshold.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path
import time
from typing import Any, Mapping, Optional, Sequence

import config
from evaluation.bounded_llm_relevance import (
    PROJECT_ROOT,
    RelevanceBenchmarkError,
    _atomic_write_text,
    _git_metadata,
    _peak_memory_bytes,
    _sha256_file,
    _utc_timestamp,
    aggregate_relevance_metrics,
)
from evaluation.bounded_llm_relevance_heldout import (
    DEFAULT_HELDOUT_SET_DIR,
    HELDOUT_ACCEPTANCE_CRITERIA,
    HELDOUT_USAGE,
    FrozenHeldoutRelevanceSet,
    load_heldout_set,
)
from evaluation.bounded_llm_relevance_v5_development import v5_question_metrics
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
    V5CandidatePackager,
    V5_ROLE_INSTRUCTIONS,
)


FINAL_HELDOUT_RUNNER_VERSION = "1.0"
FINAL_HELDOUT_RUN_USAGE = "final_heldout_evaluation_after_v5_development_freeze"
DEFAULT_EXPERIMENT_MANIFEST_PATH = (
    PROJECT_ROOT / "results" / "e1-v5-heldout-preflight" / "experiment_manifest.json"
)
DEFAULT_FINAL_OUTPUT_DIR = PROJECT_ROOT / "results" / "e1-v5-heldout-final"


@dataclass(frozen=True)
class FinalHeldoutRunSummary:
    """Summary for the one persisted v5.1 held-out model evaluation."""

    output_dir: Path
    question_count: int
    accepted_selection_count: int
    invalid_structured_output_count: int
    fallback_count: int
    all_relevance_thresholds_pass: bool
    usage: str = FINAL_HELDOUT_RUN_USAGE


def _read_json(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise RelevanceBenchmarkError(f"Required final held-out artifact is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RelevanceBenchmarkError(f"Required final held-out artifact is invalid JSON: {path}") from exc
    if not isinstance(value, Mapping):
        raise RelevanceBenchmarkError(f"Required final held-out artifact must be a JSON object: {path}")
    return value


def _project_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise RelevanceBenchmarkError(f"Experiment manifest path escapes the project root: {relative}")
    return candidate


def _assess_acceptance_fail_closed(aggregate: Mapping[str, Any]) -> Mapping[str, Any]:
    """Apply pre-registered thresholds, treating undefined metrics as failure.

    A run in which every response is invalid or falls back has no selected
    facts, so precision is mathematically undefined. That must become an
    explicit failed acceptance check rather than an evaluator exception or an
    implicit pass. The frozen held-out labels and thresholds remain unchanged.
    """
    overall = aggregate.get("overall", {}) if isinstance(aggregate, Mapping) else {}
    thresholds = HELDOUT_ACCEPTANCE_CRITERIA["relevance_thresholds"]

    def at_least(metric: str, threshold: str) -> bool:
        value = overall.get(metric)
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= thresholds[threshold]

    def at_most(metric: str, threshold: str) -> bool:
        value = overall.get(metric)
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value <= thresholds[threshold]

    checks = {
        "fact_selection_precision": at_least("fact_selection_precision", "minimum_fact_selection_precision"),
        "fact_selection_recall": at_least("fact_selection_recall", "minimum_fact_selection_recall"),
        "safe_empty_selection_accuracy": at_least(
            "safe_empty_selection_accuracy", "minimum_safe_empty_selection_accuracy"
        ),
        "passage_precision": at_least("passage_precision", "minimum_passage_precision"),
        "passage_recall": at_least("passage_recall", "minimum_passage_recall"),
        "invalid_structured_output_rate": at_most(
            "invalid_structured_output_rate", "maximum_invalid_structured_output_rate"
        ),
        "fallback_rate": at_most("fallback_rate", "maximum_fallback_rate"),
    }
    return {
        "policy_version": HELDOUT_ACCEPTANCE_CRITERIA["policy_version"],
        "all_relevance_thresholds_pass": all(checks.values()),
        "checks": checks,
        "post_relevance_pilot_gate": HELDOUT_ACCEPTANCE_CRITERIA["post_relevance_pilot_gate"],
        "undefined_metric_policy": "fail_closed",
    }


def load_final_heldout_experiment_manifest(
    path: Path | str = DEFAULT_EXPERIMENT_MANIFEST_PATH,
    *,
    project_root: Path | str = PROJECT_ROOT,
) -> Mapping[str, Any]:
    """Load and verify the frozen pre-model experiment boundary.

    This checks the static environment/evidence identity that was recorded
    before any final held-out model call. The final runner additionally records
    its own source hash and the current clean Git commit in its output manifest.
    """
    root = Path(project_root).resolve()
    manifest_path = Path(path).resolve()
    manifest = _read_json(manifest_path)
    if manifest.get("artifact_type") != "frozen_e1_v5_heldout_experiment_boundary":
        raise RelevanceBenchmarkError("Unsupported final held-out experiment manifest type.")
    if manifest.get("experiment_status") != "frozen_before_final_heldout_model_evaluation":
        raise RelevanceBenchmarkError("Final held-out experiment manifest is not frozen before model evaluation.")
    policy = manifest.get("execution_policy")
    if not isinstance(policy, Mapping) or policy.get("final_heldout_model_calls_completed") != 0:
        raise RelevanceBenchmarkError("Final held-out experiment boundary does not permit the first model evaluation.")
    if policy.get("prompt_or_candidate_tuning_permitted") is not False:
        raise RelevanceBenchmarkError("Final held-out experiment manifest permits forbidden v5.1 tuning.")

    heldout = manifest.get("final_heldout_set")
    if not isinstance(heldout, Mapping):
        raise RelevanceBenchmarkError("Final held-out experiment manifest lacks held-out set identity.")
    expected_files = {
        "manifest_path": "manifest_sha256",
        "questions_path": "questions_sha256",
        "acceptance_criteria_path": "acceptance_criteria_sha256",
    }
    for path_key, hash_key in expected_files.items():
        relative, expected = heldout.get(path_key), heldout.get(hash_key)
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RelevanceBenchmarkError("Final held-out experiment manifest has incomplete set hash metadata.")
        artifact = _project_path(root, relative)
        if not artifact.is_file() or _sha256_file(artifact) != expected:
            raise RelevanceBenchmarkError(f"Final held-out experiment boundary hash differs: {relative}")
    if heldout.get("usage") != HELDOUT_USAGE or heldout.get("question_count") != 96:
        raise RelevanceBenchmarkError("Final held-out experiment manifest names an unsupported question set.")

    runtime = manifest.get("v5_runtime_boundary")
    if not isinstance(runtime, Mapping):
        raise RelevanceBenchmarkError("Final held-out experiment manifest lacks v5 runtime identity.")
    if (
        runtime.get("selection_contract_version") != V5_SELECTION_CONTRACT_VERSION
        or runtime.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION_V5
        or runtime.get("candidate_packaging_version") != CANDIDATE_PACKAGING_VERSION_V5
    ):
        raise RelevanceBenchmarkError("Final held-out experiment manifest differs from the frozen v5.1 contract.")
    runtime_hashes = runtime.get("files_sha256")
    if not isinstance(runtime_hashes, Mapping) or not runtime_hashes:
        raise RelevanceBenchmarkError("Final held-out experiment manifest lacks v5 runtime file hashes.")
    for relative, expected in runtime_hashes.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RelevanceBenchmarkError("Final held-out experiment manifest has malformed runtime file hashes.")
        artifact = _project_path(root, relative)
        if not artifact.is_file() or _sha256_file(artifact) != expected:
            raise RelevanceBenchmarkError(f"Final held-out v5 runtime hash differs: {relative}")

    acceleration = manifest.get("e1_model_and_acceleration_boundary")
    if not isinstance(acceleration, Mapping):
        raise RelevanceBenchmarkError("Final held-out experiment manifest lacks E1 model/acceleration identity.")
    evidence_relative = acceleration.get("acceleration_evidence_path")
    evidence_hash = acceleration.get("acceleration_evidence_sha256")
    if not isinstance(evidence_relative, str) or not isinstance(evidence_hash, str):
        raise RelevanceBenchmarkError("Final held-out experiment manifest lacks acceleration-evidence hash metadata.")
    evidence_path = _project_path(root, evidence_relative)
    if not evidence_path.is_file() or _sha256_file(evidence_path) != evidence_hash:
        raise RelevanceBenchmarkError("Final held-out Apple-GPU acceleration evidence hash differs.")
    evidence = _read_json(evidence_path)
    expected_model = acceleration.get("model")
    observed_model = evidence.get("backend_evidence", {}).get("model", {})
    observed_acceleration = evidence.get("backend_evidence", {}).get("acceleration", {})
    if (
        evidence.get("status") != "verified"
        or evidence.get("configuration_id") != "E1"
        or not isinstance(expected_model, Mapping)
        or not isinstance(observed_model, Mapping)
        or expected_model.get("tag") != observed_model.get("tag")
        or expected_model.get("artifact_sha256") != observed_model.get("model_blob_sha256")
        or expected_model.get("quantization") != observed_model.get("quantization")
        or not isinstance(observed_acceleration, Mapping)
        or not observed_acceleration.get("observed_model_resident_in_gpu_memory")
        or int(observed_acceleration.get("observed_gpu_resident_bytes", 0)) <= 0
    ):
        raise RelevanceBenchmarkError("Final held-out E1 model or Apple-GPU evidence differs from the frozen boundary.")
    return manifest


class V51FinalHeldoutRelevanceRunner:
    """Persist the one final held-out v5.1 relevance evaluation.

    ``test_mode`` exists solely for deterministic unit tests using temporary
    output directories and mocked clients. The command-line entry point never
    enables it, so an actual final evaluation uses only the canonical output
    directory and cannot overwrite a prior result.
    """

    def __init__(
        self,
        *,
        heldout_set: Optional[FrozenHeldoutRelevanceSet] = None,
        heldout_dir: Path | str = DEFAULT_HELDOUT_SET_DIR,
        experiment_manifest_path: Path | str = DEFAULT_EXPERIMENT_MANIFEST_PATH,
        bounded_llm: Optional[BenchmarkLLMClientV5] = None,
        candidate_packager: Optional[V5CandidatePackager] = None,
        project_root: Path | str = PROJECT_ROOT,
        require_clean_git: bool = True,
        test_mode: bool = False,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.heldout_set = heldout_set or load_heldout_set(
            heldout_dir,
            project_root=self.project_root,
            verify_hashes=True,
        )
        self.experiment_manifest_path = Path(experiment_manifest_path).resolve()
        self.experiment_manifest = load_final_heldout_experiment_manifest(
            self.experiment_manifest_path,
            project_root=self.project_root,
        )
        self.bounded_llm = bounded_llm or BenchmarkLLMClientV5(enabled=True, required=False)
        self.candidate_packager = candidate_packager or V5CandidatePackager()
        self.require_clean_git = require_clean_git
        self.test_mode = test_mode
        self._assert_final_set_boundary()

    def _assert_final_set_boundary(self) -> None:
        manifest = self.heldout_set.manifest
        if manifest.get("usage") != FINAL_HELDOUT_RUN_USAGE:
            raise RelevanceBenchmarkError("Final held-out runner accepts only the final held-out usage boundary.")
        policy = manifest.get("label_policy", {})
        if not isinstance(policy, Mapping) or policy.get("heldout_evaluation_permitted") is not True:
            raise RelevanceBenchmarkError("Final held-out runner requires an evaluation-permitted held-out set.")
        if policy.get("v5_prompt_or_candidate_tuning_permitted") is not False:
            raise RelevanceBenchmarkError("Final held-out runner rejects a set permitting v5.1 tuning.")
        if len(self.heldout_set.questions) != 96:
            raise RelevanceBenchmarkError("Final held-out runner requires exactly 96 questions.")
        for question in self.heldout_set.questions:
            if (
                question.get("usage") != FINAL_HELDOUT_RUN_USAGE
                or question.get("selection_contract_version") != V5_SELECTION_CONTRACT_VERSION
                or question.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION_V5
                or question.get("candidate_packaging_version") != CANDIDATE_PACKAGING_VERSION_V5
            ):
                raise RelevanceBenchmarkError("Final held-out question differs from the frozen v5.1 contract.")

    def _assert_bound_e1_runtime(self) -> None:
        boundary = self.experiment_manifest["e1_model_and_acceleration_boundary"]
        if config.LLM_BACKEND != boundary.get("backend"):
            raise RelevanceBenchmarkError("Configured LLM backend differs from the frozen E1 held-out boundary.")
        model = boundary.get("model", {})
        if config.OLLAMA_MODEL != model.get("tag"):
            raise RelevanceBenchmarkError("Configured Ollama model tag differs from the frozen E1 held-out boundary.")

    def _record_for_question(self, question: Mapping[str, Any]) -> Mapping[str, Any]:
        agent_name = str(question["agent_name"])
        packaged = self.candidate_packager.package_development_facts(
            agent_name=agent_name,
            facts=tuple(question["allowed_facts"]),
            question=str(question["farmer_question"]),
        )
        expected_ids = {str(item) for item in question["expected_admissible_fact_ids"]}
        packaged_ids = tuple(str(fact["fact_id"]) for fact in packaged.facts)
        if not expected_ids.issubset(set(packaged_ids)):
            raise RelevanceBenchmarkError(
                f"{question['question_id']} final v5.1 packaging removed an expected source-backed fact."
            )
        started = time.perf_counter()
        result = self.bounded_llm.select_fact_ids(
            agent_name=agent_name,
            scenario_id=str(question["scenario_id"]),
            facts=packaged.facts,
            role_instruction=V5_ROLE_INSTRUCTIONS[agent_name],
            selection_policy=packaged.policy,
            request_sufficiency=packaged.request_sufficiency,
            scenario_context=question["scenario_context"],
            farmer_question=str(question["farmer_question"]),
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        selected_ids = {str(item) for item in result.selected_fact_ids}
        original_ids = {str(item) for item in question["allowed_fact_ids"]}
        if not selected_ids.issubset(original_ids):
            raise RelevanceBenchmarkError(
                f"{question['question_id']} final v5.1 selector returned an ID outside the immutable source-backed set."
            )
        record = dict(
            v5_question_metrics(
                question,
                result,
                latency_ms=elapsed_ms,
                peak_memory_bytes=_peak_memory_bytes(),
            )
        )
        record.update(
            {
                "usage": FINAL_HELDOUT_RUN_USAGE,
                "final_research_result_permitted": True,
                "challenge_tag": question["challenge_tag"],
                "expected_selection_mode": question["expected_selection_mode"],
                "original_allowed_fact_ids": list(question["allowed_fact_ids"]),
                "packaged_candidate_fact_ids": list(packaged_ids),
                "selection_policy": dict(packaged.policy.as_request()),
                "request_sufficiency": packaged.request_sufficiency,
                "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
                "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
                "bounded_llm": result.as_metadata(),
            }
        )
        return {"question": question, "packaged_candidates": list(packaged.facts), "result": record}

    def run(
        self,
        *,
        output_dir: Path | str = DEFAULT_FINAL_OUTPUT_DIR,
    ) -> FinalHeldoutRunSummary:
        if not self.bounded_llm.enabled:
            raise RelevanceBenchmarkError("Final held-out relevance evaluation requires an enabled bounded LLM client.")
        self._assert_bound_e1_runtime()
        git = _git_metadata(self.project_root)
        if self.require_clean_git and git["clean"] != "true":
            raise RelevanceBenchmarkError("A final held-out evaluation requires a clean Git worktree.")
        destination = Path(output_dir).resolve()
        if not self.test_mode and destination != DEFAULT_FINAL_OUTPUT_DIR.resolve():
            raise RelevanceBenchmarkError("Final held-out evaluation may write only to its canonical output directory.")
        if destination.exists():
            raise RelevanceBenchmarkError(f"Refusing to overwrite final held-out output directory: {destination}")
        destination.mkdir(parents=True, exist_ok=False)

        records: list[Mapping[str, Any]] = []
        for question in self.heldout_set.questions:
            payload = self._record_for_question(question)
            records.append(payload["result"])
            _atomic_write_text(
                destination / "per_question" / f"{question['question_id']}.json",
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
        aggregate = dict(aggregate_relevance_metrics(records))
        aggregate.update(
            {
                "usage": FINAL_HELDOUT_RUN_USAGE,
                "final_research_result_permitted": True,
                "interpretation": (
                    "Final held-out v5.1 bounded evidence-selection evaluation. These metrics measure only "
                    "selection quality under frozen source/safety boundaries; they are not farm-outcome accuracy."
                ),
            }
        )
        acceptance = dict(_assess_acceptance_fail_closed(aggregate))
        acceptance.update(
            {
                "artifact_type": "final_heldout_relevance_acceptance_report",
                "usage": FINAL_HELDOUT_RUN_USAGE,
                "question_count": len(records),
                "acceptance_criteria": HELDOUT_ACCEPTANCE_CRITERIA,
                "next_step_if_pass": "Run the separate E1-v5 30-site full-MAS pilot.",
                "next_step_if_fail": (
                    "Report this final held-out outcome. Do not tune v5.1 against this set; any future change "
                    "requires a separately versioned development and held-out protocol."
                ),
            }
        )
        manifest = {
            "runner_version": FINAL_HELDOUT_RUNNER_VERSION,
            "run_type": "final_v5_heldout_bounded_llm_relevance_evaluation",
            "usage": FINAL_HELDOUT_RUN_USAGE,
            "final_research_result_permitted": True,
            "heldout_manifest_sha256": _sha256_file(self.heldout_set.heldout_dir / "manifest.json"),
            "heldout_question_sha256": _sha256_file(self.heldout_set.heldout_dir / "heldout_questions.jsonl"),
            "heldout_acceptance_criteria_sha256": _sha256_file(
                self.heldout_set.heldout_dir / "acceptance_criteria.json"
            ),
            "experiment_manifest_path": str(self.experiment_manifest_path.relative_to(self.project_root)),
            "experiment_manifest_sha256": _sha256_file(self.experiment_manifest_path),
            "experiment_boundary_git": self.experiment_manifest["git_boundary"],
            "runner_sha256": _sha256_file(Path(__file__).resolve()),
            "question_count": len(records),
            "bounded_llm_invocation_count": self.bounded_llm.invocation_count,
            "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
            "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
            "runtime_configuration": {
                "backend": config.LLM_BACKEND,
                "ollama_model": config.OLLAMA_MODEL if config.LLM_BACKEND == "ollama" else None,
                "temperature": 0.0,
                "maximum_tokens_per_call": 200,
            },
            "git": git,
            "completed_at_utc": _utc_timestamp(),
            "all_relevance_thresholds_pass": acceptance["all_relevance_thresholds_pass"],
        }
        _atomic_write_text(
            destination / "aggregate_final_heldout_metrics.json",
            json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write_text(
            destination / "final_acceptance_report.json",
            json.dumps(acceptance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write_text(
            destination / "run_manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        invalid = sum(bool(record["invalid_structured_output"]) for record in records)
        fallback = sum(bool(record["fallback"]) for record in records)
        return FinalHeldoutRunSummary(
            output_dir=destination,
            question_count=len(records),
            accepted_selection_count=sum(record["result_status"] == "accepted" for record in records),
            invalid_structured_output_count=invalid,
            fallback_count=fallback,
            all_relevance_thresholds_pass=bool(acceptance["all_relevance_thresholds_pass"]),
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI for the single final v5.1 held-out model evaluation."""
    parser = argparse.ArgumentParser(
        description="Run the final hash-checked v5.1 held-out relevance evaluation exactly once."
    )
    parser.add_argument(
        "--required",
        action="store_true",
        help="Fail immediately on a model-runtime error instead of recording a visible safe fallback.",
    )
    arguments = parser.parse_args(argv)
    runner = V51FinalHeldoutRelevanceRunner(
        bounded_llm=BenchmarkLLMClientV5(enabled=True, required=arguments.required),
    )
    summary = runner.run()
    print(json.dumps(asdict(summary), default=str, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
