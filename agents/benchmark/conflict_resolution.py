"""Deterministic, provenance-first conflict resolution for benchmark claims.

This module is deliberately a coordinator policy component, not an LLM role.
It can only compare already-admitted claims and never supplies a missing fact
or transforms a conditional operation into a farm instruction.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence, Tuple

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, GateResult, TypedEvidenceClaim

from .base import ConflictRecord, ConflictResolutionRecord, stable_unique


@dataclass(frozen=True)
class ConflictResolutionResult:
    """Coordinator-facing resolution output and claims excluded from decisions."""

    records: Tuple[ConflictResolutionRecord, ...]
    excluded_claim_ids: Tuple[str, ...]


class ConflictResolutionPolicy:
    """Resolve comparable claims by safety, admissibility, and provenance.

    Precedence is intentionally explicit and deterministic:

    1. an opposing, source-scoped safety restriction blocks an action;
    2. blocked, unavailable, or out-of-gate claims cannot win;
    3. otherwise compare gate result, geographic/temporal specificity, source
       provenance, claim disposition, and recorded confidence;
    4. equal-precedence opposing claims are deferred rather than broken by an
       arbitrary confidence or LLM preference.
    """

    _SAFETY_TRUE = {"1", "true", "yes", "required", "blocked"}

    @staticmethod
    def _as_int(value: object, default: int = 0) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _explicit_rank(cls, claim: TypedEvidenceClaim, name: str) -> int | None:
        value = claim.metadata.get(name)
        if value is None or str(value).strip() == "":
            return None
        return cls._as_int(value)

    @classmethod
    def _spatial_rank(cls, claim: TypedEvidenceClaim) -> int:
        explicit = cls._explicit_rank(claim, "resolution_spatial_rank")
        if explicit is not None:
            return explicit
        scope = claim.spatial_scope.lower()
        if "farm parcel" in scope or "surveyed farm" in scope:
            return 5
        if "district" in scope:
            return 4
        if "state" in scope:
            return 3
        if "zone" in scope or "regional" in scope:
            return 2
        return 1

    @classmethod
    def _temporal_rank(cls, claim: TypedEvidenceClaim) -> int:
        explicit = cls._explicit_rank(claim, "resolution_temporal_rank")
        if explicit is not None:
            return explicit
        scope = claim.temporal_scope.lower()
        if "exact" in scope or "decision window" in scope:
            return 4
        if "week" in scope or "date" in scope:
            return 3
        if "season" in scope:
            return 2
        return 1

    @classmethod
    def _source_rank(cls, claim: TypedEvidenceClaim) -> int:
        explicit = cls._explicit_rank(claim, "resolution_source_rank")
        if explicit is not None:
            return explicit
        rank = 0
        if claim.source.source_document_id:
            rank += 1
        if claim.source.official_url:
            rank += 1
        if claim.source.raw_sha256:
            rank += 1
        if claim.source.locator:
            rank += 1
        if claim.metadata.get("source_quote"):
            rank += 1
        return rank

    @staticmethod
    def _disposition_rank(claim: TypedEvidenceClaim) -> int:
        return {
            ClaimDisposition.SUPPORTED_OPERATION: 3,
            ClaimDisposition.CONDITIONAL_OPERATION: 2,
            ClaimDisposition.CONTEXT: 1,
        }.get(claim.disposition, 0)

    @staticmethod
    def _gate_rank(claim: TypedEvidenceClaim) -> int:
        return {
            GateResult.PASS: 2,
            GateResult.NOT_APPLICABLE: 1,
            GateResult.ABSTAIN: 0,
            GateResult.BLOCKED: -1,
        }[claim.gate_result]

    @classmethod
    def _precedence(cls, claim: TypedEvidenceClaim) -> tuple[int, int, int, int, int, int, float]:
        """Return a comparison tuple; no arbitrary ID appears in this score."""
        return (
            cls._gate_rank(claim),
            cls._spatial_rank(claim),
            cls._temporal_rank(claim),
            cls._source_rank(claim),
            cls._disposition_rank(claim),
            int(claim.allowed_use != AllowedUse.UNAVAILABLE),
            claim.confidence,
        )

    @classmethod
    def _is_safety_restriction(cls, claim: TypedEvidenceClaim) -> bool:
        explicit = str(claim.metadata.get("safety_restriction", "")).strip().lower()
        return explicit in cls._SAFETY_TRUE or (
            str(claim.metadata.get("assertion_polarity", "")).strip().lower() == "opposes"
            and (
                claim.gate_result == GateResult.BLOCKED
                or claim.allowed_use == AllowedUse.UNAVAILABLE
                or claim.disposition
                in {ClaimDisposition.BLOCKED, ClaimDisposition.ABSTAIN, ClaimDisposition.NO_DATA}
            )
        )

    @staticmethod
    def _is_inadmissible(claim: TypedEvidenceClaim) -> bool:
        return (
            claim.gate_result == GateResult.BLOCKED
            or claim.allowed_use == AllowedUse.UNAVAILABLE
            or claim.disposition
            in {ClaimDisposition.BLOCKED, ClaimDisposition.ABSTAIN, ClaimDisposition.NO_DATA}
        )

    @staticmethod
    def _conflict_id(conflict: ConflictRecord, claim_ids: Sequence[str]) -> str:
        if conflict.conflict_id:
            return conflict.conflict_id
        payload = {
            "type": conflict.conflict_type,
            "domain": conflict.decision_domain,
            "target": conflict.evidence.get("decision_target", ""),
            "claim_ids": sorted(claim_ids),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _citation_ids(claims: Sequence[TypedEvidenceClaim]) -> Tuple[str, ...]:
        return tuple(sorted(stable_unique([
            claim.source.source_document_id or "" for claim in claims
        ])))

    @staticmethod
    def _claim_ids_for_record(
        conflict: ConflictRecord,
        claims: Sequence[TypedEvidenceClaim],
    ) -> Tuple[str, ...]:
        if conflict.claim_ids:
            return tuple(sorted(stable_unique(conflict.claim_ids)))
        target = conflict.evidence.get("decision_target", "")
        matched = [
            claim.claim_id
            for claim in claims
            if (
                claim.decision_domain.value == conflict.decision_domain
                and (
                    not target
                    or str(claim.metadata.get("decision_target", "")) == target
                )
            )
        ]
        if not matched and conflict.claim_agents:
            matched = [
                claim.claim_id for claim in claims if claim.agent_name in conflict.claim_agents
            ]
        return tuple(sorted(stable_unique(matched)))

    def resolve(
        self,
        scenario: FrozenBenchmarkScenario,
        claims: Sequence[TypedEvidenceClaim],
        conflicts: Sequence[ConflictRecord],
    ) -> ConflictResolutionResult:
        """Produce immutable resolutions without modifying source claims."""
        del scenario  # identities are already enforced by the workflow boundary.
        claims_by_id = {claim.claim_id: claim for claim in claims}
        records: list[ConflictResolutionRecord] = []
        excluded: list[str] = []

        for conflict in conflicts:
            candidate_ids = self._claim_ids_for_record(conflict, claims)
            candidates = [claims_by_id[claim_id] for claim_id in candidate_ids if claim_id in claims_by_id]
            conflict_id = self._conflict_id(conflict, candidate_ids)
            target = conflict.evidence.get("decision_target", "")

            if conflict.conflict_type == "natural_cross_source_context_divergence":
                records.append(ConflictResolutionRecord(
                    conflict_id=conflict_id,
                    conflict_type=conflict.conflict_type,
                    decision_domain=conflict.decision_domain,
                    decision_target=target,
                    status="handled_as_non_action_contextual_divergence",
                    accepted_claim_ids=tuple(claim.claim_id for claim in candidates),
                    rejected_claim_ids=(),
                    downgraded_claim_ids=(),
                    deferred_claim_ids=(),
                    rule_path=(
                        "eligible_natural_divergence",
                        "retain_contextual_sources",
                        "prohibit_action_inference",
                    ),
                    rationale=(
                        "The stored NDVI–weather relation is retained as contextual evidence only; "
                        "it cannot select an agricultural action or override a field-evidence gate."
                    ),
                    citations=self._citation_ids(candidates),
                    direct_farm_action_allowed=False,
                ))
                continue

            if not candidates:
                records.append(ConflictResolutionRecord(
                    conflict_id=conflict_id,
                    conflict_type=conflict.conflict_type,
                    decision_domain=conflict.decision_domain,
                    decision_target=target,
                    status="deferred_missing_claim_reference",
                    accepted_claim_ids=(),
                    rejected_claim_ids=(),
                    downgraded_claim_ids=(),
                    deferred_claim_ids=tuple(candidate_ids),
                    rule_path=("conflict_record", "missing_claim_reference", "safe_defer"),
                    rationale=(
                        "The conflict record does not resolve to an immutable claim in this trace, "
                        "so no contested evidence may influence the decision."
                    ),
                    citations=(),
                    direct_farm_action_allowed=False,
                ))
                excluded.extend(candidate_ids)
                continue

            safety_claims = [claim for claim in candidates if self._is_safety_restriction(claim)]
            if safety_claims:
                accepted = tuple(sorted(claim.claim_id for claim in safety_claims))
                rejected = tuple(sorted(claim.claim_id for claim in candidates if claim.claim_id not in accepted))
                records.append(ConflictResolutionRecord(
                    conflict_id=conflict_id,
                    conflict_type=conflict.conflict_type,
                    decision_domain=conflict.decision_domain,
                    decision_target=target,
                    status="resolved_by_safety_restriction",
                    accepted_claim_ids=accepted,
                    rejected_claim_ids=rejected,
                    downgraded_claim_ids=(),
                    deferred_claim_ids=(),
                    rule_path=(
                        "comparable_domain_and_target",
                        "opposing_safety_restriction",
                        "safety_precedence",
                        "block_contested_action",
                    ),
                    rationale=(
                        "An opposing safety restriction is source-scoped and takes precedence over "
                        "the contested action claim."
                    ),
                    citations=self._citation_ids(safety_claims),
                    direct_farm_action_allowed=False,
                ))
                excluded.extend(rejected)
                continue

            inadmissible = [claim for claim in candidates if self._is_inadmissible(claim)]
            viable = [claim for claim in candidates if claim not in inadmissible]
            if not viable:
                rejected = tuple(sorted(claim.claim_id for claim in candidates))
                records.append(ConflictResolutionRecord(
                    conflict_id=conflict_id,
                    conflict_type=conflict.conflict_type,
                    decision_domain=conflict.decision_domain,
                    decision_target=target,
                    status="deferred_no_admissible_claim",
                    accepted_claim_ids=(),
                    rejected_claim_ids=rejected,
                    downgraded_claim_ids=(),
                    deferred_claim_ids=(),
                    rule_path=("comparable_domain_and_target", "admissibility_gate", "safe_defer"),
                    rationale=(
                        "Every contested claim is blocked, unavailable, or abstained; none may "
                        "influence a decision."
                    ),
                    citations=(),
                    direct_farm_action_allowed=False,
                ))
                excluded.extend(rejected)
                continue

            best_score = max(self._precedence(claim) for claim in viable)
            best = [claim for claim in viable if self._precedence(claim) == best_score]
            polarities = {
                str(claim.metadata.get("assertion_polarity", "")).strip().lower()
                for claim in best
            }
            rejected = tuple(sorted(
                claim.claim_id for claim in candidates if claim not in best
            ))

            if {"supports", "opposes"}.issubset(polarities):
                deferred = tuple(sorted(claim.claim_id for claim in best))
                records.append(ConflictResolutionRecord(
                    conflict_id=conflict_id,
                    conflict_type=conflict.conflict_type,
                    decision_domain=conflict.decision_domain,
                    decision_target=target,
                    status="deferred_equal_precedence",
                    accepted_claim_ids=(),
                    rejected_claim_ids=rejected,
                    downgraded_claim_ids=(),
                    deferred_claim_ids=deferred,
                    rule_path=(
                        "comparable_domain_and_target",
                        "admissibility_gate",
                        "provenance_precedence_tie",
                        "safe_defer",
                    ),
                    rationale=(
                        "Opposing claims have equal admissible provenance precedence; the system "
                        "does not use confidence or an LLM to break the tie."
                    ),
                    citations=self._citation_ids(best),
                    direct_farm_action_allowed=False,
                ))
                excluded.extend((*rejected, *deferred))
                continue

            accepted = tuple(sorted(claim.claim_id for claim in best))
            downgraded = tuple(sorted(
                claim.claim_id for claim in best
                if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
            ))
            direct = any(
                claim.disposition == ClaimDisposition.SUPPORTED_OPERATION
                and claim.gate_result == GateResult.PASS
                and str(claim.metadata.get("assertion_polarity", "supports")).strip().lower() != "opposes"
                for claim in best
            )
            records.append(ConflictResolutionRecord(
                conflict_id=conflict_id,
                conflict_type=conflict.conflict_type,
                decision_domain=conflict.decision_domain,
                decision_target=target,
                status="resolved_by_provenance_precedence",
                accepted_claim_ids=accepted,
                rejected_claim_ids=rejected,
                downgraded_claim_ids=downgraded,
                deferred_claim_ids=(),
                rule_path=(
                    "comparable_domain_and_target",
                    "admissibility_gate",
                    "geographic_temporal_source_precedence",
                    "retain_highest_ranked_claim",
                ),
                rationale=(
                    "The accepted claim has the highest recorded gate, geographic, temporal, and "
                    "source-provenance precedence among the comparable evidence."
                ),
                citations=self._citation_ids(best),
                direct_farm_action_allowed=direct,
            ))
            excluded.extend(rejected)

        return ConflictResolutionResult(
            records=tuple(records),
            excluded_claim_ids=tuple(sorted(stable_unique(excluded))),
        )
