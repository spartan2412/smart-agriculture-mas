"""Frozen v5.1 relevance-transfer runner for the optional E2/E3 experiments.

The final E1 held-out result remains immutable.  This runner reuses the same
source-derived questions only to compare a *new, untuned* 14B deployment under
the frozen v5.1 selector contract.  Its output is therefore a transfer/model-
capacity measurement, not a new held-out protocol and never a reason to tune
prompts, candidates, labels, or source evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path
import time
from typing import Any, Mapping, Optional, Sequence

from evaluation.benchmark_batch_runner import ExperimentProtocolError
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
from evaluation.bounded_llm_relevance_v5_heldout import _assess_acceptance_fail_closed
from evaluation.phase8_batch_runner import (
    PHASE8_CONFIGURATION_IDS,
    Phase8BatchRunner,
    _canonical_json_hash,
)
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
    V5CandidatePackager,
    V5_ROLE_INSTRUCTIONS,
)


PHASE8_RELEVANCE_RUNNER_VERSION = "1.0"
PHASE8_RELEVANCE_USAGE = "frozen_e1_v51_heldout_set_transfer_evaluation_no_phase8_tuning"


@dataclass(frozen=True)
class Phase8RelevanceRunSummary:
    output_dir: Path
    configuration_id: str
    question_count: int
    accepted_selection_count: int
    invalid_structured_output_count: int
    fallback_count: int
    all_relevance_thresholds_pass: bool
    usage: str = PHASE8_RELEVANCE_USAGE


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelevanceBenchmarkError(f"Cannot read Phase 8 JSON input {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise RelevanceBenchmarkError(f"Phase 8 JSON input {path} must contain an object.")
    return value


class Phase8RelevanceRunner:
    """Evaluate E2/E3 fact selection against the frozen E1 v5.1 question set."""

    def __init__(
        self,
        *,
        configuration_id: str,
        acceleration_evidence: Mapping[str, Any],
        model_artifact_binding: Mapping[str, Any],
        heldout_set: Optional[FrozenHeldoutRelevanceSet] = None,
        heldout_dir: Path | str = DEFAULT_HELDOUT_SET_DIR,
        bounded_llm: Optional[BenchmarkLLMClientV5] = None,
        candidate_packager: Optional[V5CandidatePackager] = None,
        project_root: Path | str = PROJECT_ROOT,
        require_clean_git: bool = True,
    ) -> None:
        if configuration_id not in PHASE8_CONFIGURATION_IDS:
            raise RelevanceBenchmarkError("Phase 8 relevance runner supports E2 and E3 only.")
        self.project_root = Path(project_root).resolve()
        self.configuration_id = configuration_id
        self.heldout_set = heldout_set or load_heldout_set(
            heldout_dir, project_root=self.project_root, verify_hashes=True
        )
        self.candidate_packager = candidate_packager or V5CandidatePackager()
        self.require_clean_git = require_clean_git
        self._assert_frozen_question_boundary()
        try:
            configuration, selector, evidence, normalized_binding = Phase8BatchRunner(
                project_root=self.project_root,
                require_clean_git=False,
            )._validate_configuration(
                Phase8BatchRunner(project_root=self.project_root, require_clean_git=False)._read_protocol(),
                configuration_id,
                acceleration_evidence=acceleration_evidence,
                model_artifact_binding=model_artifact_binding,
            )
        except ExperimentProtocolError as exc:
            raise RelevanceBenchmarkError(f"Phase 8 relevance runtime is not admissible: {exc}") from exc
        self.configuration = configuration
        self.bounded_llm = bounded_llm or selector
        self.acceleration_evidence = dict(evidence)
        self.normalized_binding = dict(normalized_binding)

    def _assert_frozen_question_boundary(self) -> None:
        manifest = self.heldout_set.manifest
        policy = manifest.get("label_policy", {})
        if (
            manifest.get("usage") != HELDOUT_USAGE
            or not isinstance(policy, Mapping)
            or policy.get("v5_prompt_or_candidate_tuning_permitted") is not False
            or len(self.heldout_set.questions) != 96
        ):
            raise RelevanceBenchmarkError("Phase 8 requires the immutable 96-question v5.1 held-out source set.")
        for question in self.heldout_set.questions:
            if (
                question.get("selection_contract_version") != V5_SELECTION_CONTRACT_VERSION
                or question.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION_V5
                or question.get("candidate_packaging_version") != CANDIDATE_PACKAGING_VERSION_V5
            ):
                raise RelevanceBenchmarkError("A Phase 8 relevance question differs from the frozen v5.1 contract.")

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
                f"{question['question_id']} Phase 8 packaging removed an expected source-backed fact."
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
                f"{question['question_id']} Phase 8 selector returned an ID outside the frozen source-backed set."
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
                "usage": PHASE8_RELEVANCE_USAGE,
                "final_research_result_permitted": True,
                "is_new_heldout_protocol": False,
                "phase8_prompt_or_candidate_tuning_permitted": False,
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

    def run(self, *, output_dir: Path | str) -> Phase8RelevanceRunSummary:
        if not self.bounded_llm.enabled:
            raise RelevanceBenchmarkError("Phase 8 relevance evaluation requires an enabled bounded LLM.")
        git = _git_metadata(self.project_root)
        if self.require_clean_git and git["clean"] != "true":
            raise RelevanceBenchmarkError("A persisted Phase 8 relevance result requires a clean Git worktree.")
        destination = Path(output_dir).resolve()
        if destination.exists():
            raise RelevanceBenchmarkError(f"Refusing to overwrite Phase 8 relevance output: {destination}")
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
                "usage": PHASE8_RELEVANCE_USAGE,
                "interpretation": (
                    "Frozen v5.1 source-derived evidence-selection transfer evaluation for a new 14B deployment. "
                    "It measures selection quality only, never farm-outcome accuracy."
                ),
            }
        )
        acceptance = dict(_assess_acceptance_fail_closed(aggregate))
        acceptance.update(
            {
                "artifact_type": "phase8_relevance_transfer_acceptance_report",
                "configuration_id": self.configuration_id,
                "usage": PHASE8_RELEVANCE_USAGE,
                "new_heldout_protocol": False,
                "question_count": len(records),
                "acceptance_criteria": HELDOUT_ACCEPTANCE_CRITERIA,
                "next_step_if_pass": "Run the matching Phase 8 30-site MAS pilot without changing the v5.1 system.",
                "next_step_if_fail": "Report the result; do not tune E2/E3 prompts or candidates against this set.",
            }
        )
        manifest = {
            "runner_version": PHASE8_RELEVANCE_RUNNER_VERSION,
            "run_type": "phase8_v51_frozen_relevance_transfer_evaluation",
            "configuration_id": self.configuration_id,
            "usage": PHASE8_RELEVANCE_USAGE,
            "final_research_result_permitted": True,
            "new_heldout_protocol": False,
            "heldout_manifest_sha256": _sha256_file(self.heldout_set.heldout_dir / "manifest.json"),
            "heldout_question_sha256": _sha256_file(self.heldout_set.heldout_dir / "heldout_questions.jsonl"),
            "heldout_acceptance_criteria_sha256": _sha256_file(
                self.heldout_set.heldout_dir / "acceptance_criteria.json"
            ),
            "phase8_runner_sha256": _sha256_file(Path(__file__).resolve()),
            "phase8_batch_runner_sha256": _sha256_file(
                self.project_root / "evaluation" / "phase8_batch_runner.py"
            ),
            "acceleration_evidence_sha256": _canonical_json_hash(self.acceleration_evidence),
            "model_artifact_binding": self.normalized_binding,
            "question_count": len(records),
            "bounded_llm_invocation_count": self.bounded_llm.invocation_count,
            "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
            "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
            "runtime_configuration": {
                "backend": self.configuration["backend"],
                "runtime_model_identifier": self.normalized_binding[self.configuration_id]["runtime_model_identifier"],
                "temperature": 0.0,
                "maximum_tokens_per_call": 200,
            },
            "git": git,
            "completed_at_utc": _utc_timestamp(),
            "all_relevance_thresholds_pass": acceptance["all_relevance_thresholds_pass"],
        }
        _atomic_write_text(
            destination / "aggregate_relevance_metrics.json",
            json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write_text(
            destination / "acceptance_report.json",
            json.dumps(acceptance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write_text(
            destination / "run_manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        invalid = sum(bool(record["invalid_structured_output"]) for record in records)
        fallback = sum(bool(record["fallback"]) for record in records)
        return Phase8RelevanceRunSummary(
            output_dir=destination,
            configuration_id=self.configuration_id,
            question_count=len(records),
            accepted_selection_count=sum(record["result_status"] == "accepted" for record in records),
            invalid_structured_output_count=invalid,
            fallback_count=fallback,
            all_relevance_thresholds_pass=bool(acceptance["all_relevance_thresholds_pass"]),
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run frozen v5.1 Phase 8 E2/E3 relevance transfer evaluation.")
    parser.add_argument("--configuration", choices=tuple(sorted(PHASE8_CONFIGURATION_IDS)), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--acceleration-evidence-json", type=Path, required=True)
    parser.add_argument("--model-artifact-binding-json", type=Path, required=True)
    parser.add_argument("--required", action="store_true")
    arguments = parser.parse_args(argv)
    runner = Phase8RelevanceRunner(
        configuration_id=arguments.configuration,
        acceleration_evidence=_read_json(arguments.acceleration_evidence_json),
        model_artifact_binding=_read_json(arguments.model_artifact_binding_json),
        bounded_llm=None,
    )
    # The runner normally creates an admissible client via Phase8BatchRunner.
    # ``--required`` changes only error handling, never prompt or candidate data.
    runner.bounded_llm.required = bool(arguments.required)
    summary = runner.run(output_dir=arguments.output_dir)
    print(json.dumps(asdict(summary), default=str, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
