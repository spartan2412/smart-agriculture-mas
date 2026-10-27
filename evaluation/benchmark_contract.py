"""Versioned evaluation boundary for the provenance-constrained benchmark.

The contract deliberately separates structural evidence/safety evaluation from
field-outcome accuracy.  The latter cannot be claimed from the frozen public
scenario evidence, which contains no farm-level outcome labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


EVALUATION_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class BenchmarkEvaluationContract:
    """Paper-facing commitments that later runners and metrics must respect."""

    version: str
    benchmark_population: str
    primary_structural_metrics: Tuple[str, ...]
    conflict_metrics: Tuple[str, ...]
    prohibited_outcome_claims: Tuple[str, ...]
    resolution_policy: Tuple[str, ...]


BENCHMARK_EVALUATION_CONTRACT = BenchmarkEvaluationContract(
    version=EVALUATION_CONTRACT_VERSION,
    benchmark_population="300 frozen, source-gated India agricultural scenarios",
    primary_structural_metrics=(
        "scenario_loader_integrity_pass_rate",
        "citation_coverage",
        "abstention_reason_coverage",
        "unsupported_direct_action_rate",
        "operation_binding_compliance_rate",
    ),
    conflict_metrics=(
        "eligible_conflict_detection_rate",
        "conflict_resolution_trace_completeness",
        "provenance_precedence_compliance_rate",
        "safe_defer_rate_for_equal_precedence_conflicts",
        "rejected_claim_exclusion_rate",
    ),
    prohibited_outcome_claims=(
        "field_action_accuracy",
        "farm_irrigation_accuracy",
        "fertilizer_dose_accuracy",
        "pesticide_treatment_accuracy",
        "disease_diagnosis_accuracy",
        "calibration_or_brier_score_without_outcome_labels",
    ),
    resolution_policy=(
        "compare_only_same_domain_same_target_claims",
        "safety_restriction_precedes_contested_action",
        "blocked_or_unavailable_claim_cannot_win",
        "rank_by_gate_spatial_temporal_source_then_disposition",
        "defer_equal_precedence_opposition",
        "bounded_llm_cannot_resolve_or_override_conflicts",
    ),
)
