"""Shared contracts and safe helpers for the benchmark MAS agents.

The classes in this package deliberately do not inherit from the legacy
``BaseAgent``.  Legacy agents consume caller-provided dictionaries and emit
unscoped ``AgentEvidence`` objects; benchmark agents consume only a validated
``FrozenBenchmarkScenario`` and emit immutable ``TypedEvidenceClaim`` records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import (
    AllowedUse,
    ClaimDisposition,
    DecisionDomain,
    GateResult,
    SourceCitation,
    TypedEvidenceClaim,
)


_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


@dataclass(frozen=True)
class RetrievedPassage:
    """A metadata-admitted, lexically ranked official RAG passage."""

    source_document_id: str
    source_title: str
    official_url: str
    locator: str
    text: str
    score: float
    source_raw_sha256: Optional[str]
    corpus_layer: str = "official_rag"


@dataclass(frozen=True)
class ConflictRecord:
    """A scoped disagreement or a non-action contextual divergence."""

    conflict_type: str
    decision_domain: str
    claim_agents: Tuple[str, ...]
    status: str
    resolution: str
    evidence: Mapping[str, str]
    conflict_id: str = ""
    claim_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ConflictResolutionRecord:
    """Deterministic coordinator disposition for one scoped conflict.

    The record makes both the selected evidence and the policy path explicit,
    so a paper result can distinguish a resolved disagreement from a safely
    deferred one.  It is deliberately a coordinator trace object rather than
    a new generative agent output.
    """

    conflict_id: str
    conflict_type: str
    decision_domain: str
    decision_target: str
    status: str
    accepted_claim_ids: Tuple[str, ...]
    rejected_claim_ids: Tuple[str, ...]
    downgraded_claim_ids: Tuple[str, ...]
    deferred_claim_ids: Tuple[str, ...]
    rule_path: Tuple[str, ...]
    rationale: str
    citations: Tuple[str, ...]
    direct_farm_action_allowed: bool


@dataclass(frozen=True)
class BenchmarkDecision:
    """Structured coordinator output before farmer-facing rendering."""

    scenario_id: str
    decision_status: str
    direct_farm_action_issued: bool
    operation_text: str
    operation_status: str
    rationale: str
    uncertainty_reasons: Tuple[str, ...]
    conflict_records: Tuple[ConflictRecord, ...]
    citations: Tuple[str, ...]
    trace_claim_count: int
    conflict_resolution_records: Tuple[ConflictResolutionRecord, ...] = ()


@dataclass(frozen=True)
class BenchmarkEvaluationRecord:
    """Non-ground-truth structural metrics for one benchmark decision trace."""

    scenario_id: str
    claim_count: int
    cited_claim_count: int
    citation_coverage: float
    safety_claim_count: int
    safety_claims_with_reason: int
    abstention_reason_coverage: float
    direct_farm_action_issued: bool
    unsupported_action_count: int
    conflict_record_count: int
    outcome: str


def as_float(value: Any, default: float = 0.0) -> float:
    """Parse frozen CSV values without treating an absent value as a measurement."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def first_value(row: Mapping[str, Any], *keys: str) -> Optional[str]:
    """Return the first non-empty text value from known source-field aliases."""
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def citation_from(
    row: Mapping[str, Any],
    *,
    source_document_id: Optional[str] = None,
    source_role: Optional[str] = None,
    locator: Optional[str] = None,
) -> SourceCitation:
    """Create one valid citation from heterogeneous frozen-record field names."""
    raw_hash = first_value(
        row,
        "source_raw_sha256",
        "source_sha256",
        "response_sha256",
        "satellite_response_sha256",
        "weather_current_response_sha256",
        "market_current_payload_sha256",
        "market_registry_payload_sha256",
        "metadata_sha256",
        "value_tiff_sha256",
        "raw_sha256",
    )
    if raw_hash and not _SHA256_RE.fullmatch(raw_hash):
        raw_hash = None
    return SourceCitation(
        source_document_id=source_document_id
        or first_value(row, "source_document_id", "source_id", "fertilizer_source_id", "protection_source_id"),
        official_url=first_value(
            row,
            "official_url",
            "source_url",
            "weather_source_url",
            "market_source_url",
            "fertilizer_source_url",
            "protection_source_url",
            "crop_profile_url",
            "value_request_url",
        ),
        raw_path=first_value(row, "raw_path", "weather_raw_path", "market_raw_path", "satellite_raw_path"),
        raw_sha256=raw_hash,
        locator=locator or first_value(row, "source_location", "locator", "fertilizer_locator", "protection_locator"),
        source_role=source_role or first_value(row, "evidence_role", "action_role"),
    )


def internal_trace_citation(*, source_document_id: str, source_role: str) -> SourceCitation:
    """Return local MAS-trace provenance without borrowing a public source URL."""
    return SourceCitation(
        source_document_id=source_document_id,
        source_role=source_role,
    )


def scenario_spatial_scope(scenario: FrozenBenchmarkScenario) -> str:
    identity = scenario.identity
    return (
        f"{identity.geometry_scope}; {identity.district}, {identity.state}; "
        f"not a surveyed farm parcel"
    )


def scenario_temporal_scope(scenario: FrozenBenchmarkScenario) -> str:
    return f"historical decision window {scenario.identity.decision_window_utc}"


def compact_text(value: Any, *, limit: int = 500) -> str:
    """Keep frozen text bounded before it enters an agent trace or optional prompt."""
    normalized = " ".join(str(value or "").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "…"


def lexical_tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


class BenchmarkAgent:
    """Base interface for one provenance-constrained MAS role."""

    name = "benchmark_agent"
    uses_llm = False
    # LLM-enabled subclasses own their domain-specific selection instruction.
    # The shared adapter adds non-negotiable schema and safety constraints.
    llm_selection_instruction = ""

    def run(self, scenario: FrozenBenchmarkScenario, **kwargs: Any) -> Tuple[TypedEvidenceClaim, ...]:
        raise NotImplementedError

    def _claim(
        self,
        scenario: FrozenBenchmarkScenario,
        *,
        decision_domain: DecisionDomain,
        disposition: ClaimDisposition,
        allowed_use: AllowedUse,
        claim: str,
        summary: str,
        reasoning: str,
        confidence: float,
        source: SourceCitation,
        quality: str,
        gate_result: GateResult,
        block_reason: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        spatial_scope: Optional[str] = None,
        temporal_scope: Optional[str] = None,
    ) -> TypedEvidenceClaim:
        return TypedEvidenceClaim(
            scenario_id=scenario.identity.scenario_id,
            agent_name=self.name,
            decision_domain=decision_domain,
            disposition=disposition,
            allowed_use=allowed_use,
            claim=compact_text(claim),
            summary=compact_text(summary),
            reasoning=compact_text(reasoning),
            confidence=max(0.0, min(1.0, confidence)),
            source=source,
            spatial_scope=spatial_scope or scenario_spatial_scope(scenario),
            temporal_scope=temporal_scope or scenario_temporal_scope(scenario),
            quality=compact_text(quality),
            gate_result=gate_result,
            block_reason=compact_text(block_reason) if block_reason else None,
            metadata=dict(metadata or {}),
        )

    def _blocked(
        self,
        scenario: FrozenBenchmarkScenario,
        *,
        decision_domain: DecisionDomain,
        claim: str,
        summary: str,
        reason: str,
        source: Optional[SourceCitation] = None,
        disposition: ClaimDisposition = ClaimDisposition.ABSTAIN,
        quality: str = "required evidence unavailable in frozen scenario",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> TypedEvidenceClaim:
        return self._claim(
            scenario,
            decision_domain=decision_domain,
            disposition=disposition,
            allowed_use=AllowedUse.UNAVAILABLE,
            claim=claim,
            summary=summary,
            reasoning=reason,
            confidence=1.0,
            source=source or SourceCitation(source_role="benchmark_safety_gate"),
            quality=quality,
            gate_result=GateResult.ABSTAIN,
            block_reason=reason,
            metadata=metadata,
        )


def validate_claims(
    scenario: FrozenBenchmarkScenario, claims: Iterable[TypedEvidenceClaim]
) -> Tuple[TypedEvidenceClaim, ...]:
    """Defence in depth: agents cannot leak a claim from another scenario."""
    frozen_claims = tuple(claims)
    for claim in frozen_claims:
        if claim.scenario_id != scenario.identity.scenario_id:
            raise ValueError(
                f"{claim.agent_name} emitted a claim for {claim.scenario_id}, "
                f"not {scenario.identity.scenario_id}"
            )
    return frozen_claims


def stable_unique(values: Sequence[str]) -> Tuple[str, ...]:
    """Return a deterministic de-duplicated sequence for traces and citations."""
    return tuple(dict.fromkeys(value for value in values if value))
