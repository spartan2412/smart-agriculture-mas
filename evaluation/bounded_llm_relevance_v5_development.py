"""Run the v5 bounded selector on the source-derived development set only.

This module is deliberately separate from the frozen E1-v4 runner.  Every
persisted output is marked ``development_only_not_heldout_evaluation`` and is
therefore unsuitable for a final model-quality claim.  The runner evaluates
the v5 prompt and candidate packaging while retaining the original immutable
source-derived question IDs, labels, conditions, and source identities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import json
import time
from typing import Any, Mapping, Optional, Sequence

import config
from evaluation.bounded_llm_relevance import (
    PROJECT_ROOT,
    RelevanceBenchmarkError,
    _atomic_write_text,
    _git_metadata,
    _peak_memory_bytes,
    _question_metrics,
    _sha256_file,
    _utc_timestamp,
    aggregate_relevance_metrics,
)
from evaluation.bounded_llm_relevance_development import (
    DEFAULT_DEVELOPMENT_SET_DIR,
    SourceDerivedDevelopmentSet,
    load_development_set,
)
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
    V5CandidatePackager,
    V5_ROLE_INSTRUCTIONS,
)


V5_DEVELOPMENT_RUNNER_VERSION = "1.1"
DEVELOPMENT_ONLY_USAGE = "development_only_not_heldout_evaluation"
V5_PLAN_OPERATION_METRIC_VERSION = "source_fact_projection_v1"
DEFAULT_METRIC_REANALYSIS_FILENAME = "metric_reanalysis_source_fact_projection.json"


@dataclass(frozen=True)
class V5DevelopmentRunSummary:
    """Summary of a persisted v5 development iteration."""

    output_dir: Path
    question_count: int
    accepted_selection_count: int
    invalid_structured_output_count: int
    fallback_count: int
    usage: str = DEVELOPMENT_ONLY_USAGE


def project_plan_or_operation_ids_from_fact_ids(
    question: Mapping[str, Any],
    fact_ids: Sequence[str],
) -> tuple[str, ...]:
    """Project plan/operation IDs only from the selected source-backed facts.

    A question may carry a regional policy identifier as explanatory metadata
    even when its expected answer is exclusively a farm-dose *boundary* fact.
    The boundary has no plan identifier by design. Projecting identifiers from
    the expected fact IDs avoids grading that correct boundary selection as a
    missing regional-plan choice.
    """
    by_id = {
        str(fact.get("fact_id", "")): fact
        for fact in question.get("allowed_facts", ())
        if isinstance(fact, Mapping) and str(fact.get("fact_id", "")).strip()
    }
    requested = tuple(str(fact_id) for fact_id in fact_ids)
    unknown = sorted(set(requested) - set(by_id))
    if unknown:
        raise RelevanceBenchmarkError(
            f"{question.get('question_id', '<unknown>')} projects an unknown source-backed fact: {', '.join(unknown)}"
        )
    return tuple(
        sorted(
            {
                str(plan_or_operation_id)
                for fact_id in requested
                for plan_or_operation_id in by_id[fact_id].get("plan_or_operation_ids", ())
                if str(plan_or_operation_id).strip()
            }
        )
    )


def v5_question_metrics(
    question: Mapping[str, Any],
    result: Any,
    *,
    latency_ms: int,
    peak_memory_bytes: int,
) -> Mapping[str, Any]:
    """Compute relevance metrics with v5 source-fact plan projection semantics."""
    record = dict(
        _question_metrics(
            question,
            result,
            latency_ms=latency_ms,
            peak_memory_bytes=peak_memory_bytes,
        )
    )
    legacy_expected = list(record["expected_plan_or_operation_ids"])
    source_fact_expected = list(
        project_plan_or_operation_ids_from_fact_ids(
            question,
            tuple(str(item) for item in question["expected_admissible_fact_ids"]),
        )
    )
    source_fact_selected = list(
        project_plan_or_operation_ids_from_fact_ids(
            question,
            tuple(str(item) for item in result.selected_fact_ids),
        )
    )
    record.update(
        {
            "legacy_declared_expected_plan_or_operation_ids": legacy_expected,
            "expected_plan_or_operation_ids": source_fact_expected,
            "selected_plan_or_operation_ids": source_fact_selected,
            "plan_or_operation_metric_version": V5_PLAN_OPERATION_METRIC_VERSION,
        }
    )
    return record


def reanalyze_v5_development_metrics(
    run_dir: Path | str,
    *,
    output_path: Optional[Path | str] = None,
) -> Mapping[str, Any]:
    """Write a transparent corrected metric sidecar for an existing v5 run.

    The original model selection, per-question trace, and aggregate are left
    untouched. The sidecar simply reapplies the source-fact projection to the
    already persisted selected IDs.
    """
    directory = Path(run_dir).resolve()
    manifest_path = directory / "run_manifest.json"
    if not manifest_path.is_file():
        raise RelevanceBenchmarkError(f"v5 development run manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("usage") != DEVELOPMENT_ONLY_USAGE:
        raise RelevanceBenchmarkError("Metric reanalysis accepts only development-only v5 runs.")
    payload_paths = sorted((directory / "per_question").glob("*.json"))
    if not payload_paths:
        raise RelevanceBenchmarkError("v5 development run has no per-question records to reanalyze.")
    corrected_records: list[Mapping[str, Any]] = []
    changed_question_ids: list[str] = []
    for path in payload_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        question = payload.get("question")
        result = payload.get("result")
        if not isinstance(question, Mapping) or not isinstance(result, Mapping):
            raise RelevanceBenchmarkError(f"Malformed v5 per-question record: {path}")
        corrected = dict(result)
        legacy_expected = list(
            corrected.get(
                "legacy_declared_expected_plan_or_operation_ids",
                corrected.get("expected_plan_or_operation_ids", ()),
            )
        )
        expected = list(
            project_plan_or_operation_ids_from_fact_ids(
                question,
                tuple(str(item) for item in question["expected_admissible_fact_ids"]),
            )
        )
        selected = list(
            project_plan_or_operation_ids_from_fact_ids(
                question,
                tuple(str(item) for item in corrected.get("selected_fact_ids", ())),
            )
        )
        corrected.update(
            {
                "legacy_declared_expected_plan_or_operation_ids": legacy_expected,
                "expected_plan_or_operation_ids": expected,
                "selected_plan_or_operation_ids": selected,
                "plan_or_operation_metric_version": V5_PLAN_OPERATION_METRIC_VERSION,
            }
        )
        if legacy_expected != expected:
            changed_question_ids.append(str(question["question_id"]))
        corrected_records.append(corrected)
    corrected_aggregate = dict(aggregate_relevance_metrics(corrected_records))
    original_aggregate_path = directory / "aggregate_development_metrics.json"
    original_aggregate = (
        json.loads(original_aggregate_path.read_text(encoding="utf-8"))
        if original_aggregate_path.is_file()
        else {}
    )
    report = {
        "artifact_type": "v5_development_metric_reanalysis",
        "usage": DEVELOPMENT_ONLY_USAGE,
        "not_heldout_evaluation": True,
        "final_research_result_permitted": False,
        "metric_version": V5_PLAN_OPERATION_METRIC_VERSION,
        "target_run_manifest_sha256": _sha256_file(manifest_path),
        "question_count": len(corrected_records),
        "method": (
            "Project expected and selected plan/operation IDs from their corresponding immutable "
            "source-backed fact IDs. Do not use a broad explanatory policy ID when the expected fact is "
            "only a safety boundary with no plan/operation ID."
        ),
        "changed_question_ids": changed_question_ids,
        "legacy_overall_plan_or_operation_selection_accuracy": (
            original_aggregate.get("overall", {}).get("plan_or_operation_selection_accuracy")
        ),
        "corrected_overall_plan_or_operation_selection_accuracy": corrected_aggregate["overall"].get(
            "plan_or_operation_selection_accuracy"
        ),
        "corrected_aggregate": corrected_aggregate,
    }
    destination = (
        Path(output_path).resolve()
        if output_path is not None
        else directory / DEFAULT_METRIC_REANALYSIS_FILENAME
    )
    if destination.exists():
        raise RelevanceBenchmarkError(f"Refusing to overwrite metric reanalysis: {destination}")
    _atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report


class V5DevelopmentRelevanceRunner:
    """Evaluate v5 selection behavior without creating a held-out result."""

    def __init__(
        self,
        *,
        development_set: Optional[SourceDerivedDevelopmentSet] = None,
        development_dir: Path | str = DEFAULT_DEVELOPMENT_SET_DIR,
        bounded_llm: Optional[BenchmarkLLMClientV5] = None,
        candidate_packager: Optional[V5CandidatePackager] = None,
        project_root: Path | str = PROJECT_ROOT,
        require_clean_git: bool = True,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.development_set = development_set or load_development_set(
            development_dir,
            project_root=self.project_root,
        )
        self.bounded_llm = bounded_llm or BenchmarkLLMClientV5(enabled=True, required=False)
        self.candidate_packager = candidate_packager or V5CandidatePackager()
        self.require_clean_git = require_clean_git
        self._assert_development_only()

    def _assert_development_only(self) -> None:
        manifest = self.development_set.manifest
        if manifest.get("usage") != DEVELOPMENT_ONLY_USAGE:
            raise RelevanceBenchmarkError("v5 development runner accepts only a development-only set.")
        if manifest.get("label_policy", {}).get("heldout_evaluation_permitted") is not False:
            raise RelevanceBenchmarkError("v5 development runner refuses a set permitted for held-out evaluation.")
        if any(question.get("usage") != DEVELOPMENT_ONLY_USAGE for question in self.development_set.questions):
            raise RelevanceBenchmarkError("Every v5 development question must carry the development-only usage marker.")

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
                f"{question['question_id']} v5 packaging removed an expected source-backed fact."
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
                f"{question['question_id']} v5 selector returned an ID outside the immutable source-backed set."
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
                "usage": DEVELOPMENT_ONLY_USAGE,
                "not_heldout_evaluation": True,
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
        return {
            "question": question,
            "packaged_candidates": list(packaged.facts),
            "result": record,
        }

    def run(self, *, output_dir: Path | str) -> V5DevelopmentRunSummary:
        if not self.bounded_llm.enabled:
            raise RelevanceBenchmarkError("v5 development evaluation requires an enabled bounded LLM client.")
        git = _git_metadata(self.project_root)
        if self.require_clean_git and git["clean"] != "true":
            raise RelevanceBenchmarkError("A persisted v5 development run requires a clean Git worktree.")
        destination = Path(output_dir).resolve()
        if destination.exists():
            raise RelevanceBenchmarkError(f"Refusing to overwrite v5 development output directory: {destination}")
        destination.mkdir(parents=True, exist_ok=False)

        records: list[Mapping[str, Any]] = []
        for question in self.development_set.questions:
            payload = self._record_for_question(question)
            record = payload["result"]
            records.append(record)
            _atomic_write_text(
                destination / "per_question" / f"{question['question_id']}.json",
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )

        aggregate = dict(aggregate_relevance_metrics(records))
        aggregate["usage"] = DEVELOPMENT_ONLY_USAGE
        aggregate["not_heldout_evaluation"] = True
        aggregate["interpretation"] = (
            "Development diagnostics for v5 prompt/candidate-packaging iteration only; "
            "not a final, held-out, or paper model-quality result."
        )
        manifest = {
            "runner_version": V5_DEVELOPMENT_RUNNER_VERSION,
            "run_type": "v5_bounded_llm_development_iteration",
            "usage": DEVELOPMENT_ONLY_USAGE,
            "not_heldout_evaluation": True,
            "final_research_result_permitted": False,
            "interpretation": (
                "This artifact may guide v5 prompt and candidate-packaging changes. "
                "It must not be reported as a held-out evaluation or final E1 result."
            ),
            "development_manifest_sha256": _sha256_file(
                self.development_set.development_dir / "manifest.json"
            ),
            "development_question_sha256": _sha256_file(
                self.development_set.development_dir / "development_questions.jsonl"
            ),
            "development_set_usage": self.development_set.manifest["usage"],
            "question_count": len(records),
            "bounded_llm_invocation_count": self.bounded_llm.invocation_count,
            "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
            "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
            "runtime_configuration": {
                "backend": config.LLM_BACKEND,
                "ollama_model": config.OLLAMA_MODEL if config.LLM_BACKEND == "ollama" else None,
            },
            "git": git,
            "completed_at_utc": _utc_timestamp(),
        }
        _atomic_write_text(
            destination / "aggregate_development_metrics.json",
            json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write_text(
            destination / "run_manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        invalid = sum(bool(record["invalid_structured_output"]) for record in records)
        fallback = sum(bool(record["fallback"]) for record in records)
        return V5DevelopmentRunSummary(
            output_dir=destination,
            question_count=len(records),
            accepted_selection_count=sum(record["result_status"] == "accepted" for record in records),
            invalid_structured_output_count=invalid,
            fallback_count=fallback,
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI for one explicitly non-held-out v5 development iteration."""
    parser = argparse.ArgumentParser(
        description="Run v5 bounded selection on the development-only relevance set."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output-dir", type=Path, help="Destination for a new v5 development iteration.")
    mode.add_argument("--reanalyze-run", type=Path, help="Existing v5 development run to reanalyze without LLM calls.")
    parser.add_argument("--development-dir", type=Path, default=DEFAULT_DEVELOPMENT_SET_DIR)
    parser.add_argument(
        "--required",
        action="store_true",
        help="Fail immediately on an LLM error instead of recording a safe fallback.",
    )
    arguments = parser.parse_args(argv)
    if arguments.reanalyze_run is not None:
        if arguments.required:
            parser.error("--required is only valid while running a model iteration.")
        report = reanalyze_v5_development_metrics(arguments.reanalyze_run)
        print(json.dumps(report, default=str, indent=2, sort_keys=True))
        return 0
    runner = V5DevelopmentRelevanceRunner(
        development_dir=arguments.development_dir,
        bounded_llm=BenchmarkLLMClientV5(enabled=True, required=arguments.required),
    )
    summary = runner.run(output_dir=arguments.output_dir)
    print(json.dumps(asdict(summary), default=str, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
