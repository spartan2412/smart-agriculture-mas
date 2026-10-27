"""Conflict Detection agent."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Sequence, Tuple

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult, TypedEvidenceClaim

from .base import BenchmarkAgent, ConflictRecord, citation_from


class ConflictDetectionAgent(BenchmarkAgent):
    """Detects only scoped, same-domain disagreements; it never invents a conflict."""

    name = "conflict_detection_agent"

    @staticmethod
    def _conflict_id(
        conflict_type: str,
        decision_domain: str,
        decision_target: str,
        claim_ids: Sequence[str],
    ) -> str:
        """Create a reproducible conflict identity from immutable claim IDs."""
        payload = {
            "type": conflict_type,
            "domain": decision_domain,
            "target": decision_target,
            "claim_ids": sorted(claim_ids),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def detect(self, scenario: FrozenBenchmarkScenario, claims: Sequence[TypedEvidenceClaim]) -> Tuple[ConflictRecord, ...]:
        conflicts: list[ConflictRecord] = []
        by_target: dict[tuple[str, str], list[TypedEvidenceClaim]] = {}
        for claim in claims:
            target = str(claim.metadata.get("decision_target", "")).strip()
            polarity = str(claim.metadata.get("assertion_polarity", "")).strip()
            if target and polarity:
                by_target.setdefault((claim.decision_domain.value, target), []).append(claim)
        for (domain, target), grouped in by_target.items():
            polarities = {str(item.metadata.get("assertion_polarity")) for item in grouped}
            if {"supports", "opposes"}.issubset(polarities):
                claim_ids = tuple(sorted(item.claim_id for item in grouped))
                conflicts.append(ConflictRecord(
                    conflict_type="same_domain_opposing_assertions",
                    decision_domain=domain,
                    claim_agents=tuple(sorted({item.agent_name for item in grouped})),
                    status="detected",
                    resolution="defer_to_scope_authority_and_safety_policy",
                    evidence={"decision_target": target, "polarities": ",".join(sorted(polarities))},
                    conflict_id=self._conflict_id(
                        "same_domain_opposing_assertions", domain, target, claim_ids
                    ),
                    claim_ids=claim_ids,
                ))
        divergence = scenario.natural_signal_divergence
        if divergence and divergence.get("candidate_status", "") == "eligible_natural_signal_divergence_candidate":
            divergence_claims = tuple(sorted(
                claim.claim_id
                for claim in claims
                if claim.agent_name in {"satellite_ndvi_context_agent", "weather_context_agent"}
            ))
            domain = DecisionDomain.SATELLITE_CONTEXT.value
            conflicts.append(ConflictRecord(
                conflict_type="natural_cross_source_context_divergence",
                decision_domain=domain,
                claim_agents=("satellite_ndvi_context_agent", "weather_context_agent"),
                status=divergence.get("candidate_status", "contextual_candidate"),
                resolution=divergence.get(
                    "coordinator_handling_rule", "retain_as_context_without_forcing_a_conflict"
                ),
                evidence={
                    "cross_source_relation": divergence.get("cross_source_relation", ""),
                    "restriction_reason": divergence.get("restriction_reason", ""),
                },
                conflict_id=self._conflict_id(
                    "natural_cross_source_context_divergence", domain, "", divergence_claims
                ),
                claim_ids=divergence_claims,
            ))
        return tuple(conflicts)

    def run(self, scenario: FrozenBenchmarkScenario, *, claims: Sequence[TypedEvidenceClaim] = (), **_: Any):
        conflicts = self.detect(scenario, claims)
        summary = (
            f"{len(conflicts)} scoped conflict/divergence record(s) retained for coordinator handling."
            if conflicts else "No scoped same-domain conflict is supported by this scenario."
        )
        reasoning = (
            "Only claims with the same declared decision domain and target are compared. "
            "A natural cross-source candidate remains contextual unless its stored rule says otherwise."
            if conflicts else
            "The system does not manufacture a conflict from unrelated evidence types or from required abstentions."
        )
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="Conflict handling is limited to comparable, source-scoped evidence.",
                summary=summary,
                reasoning=reasoning,
                confidence=1.0,
                source=citation_from(
                    scenario.natural_signal_divergence or scenario.manifest,
                    source_document_id="NATURAL_SIGNAL_DIVERGENCE" if scenario.natural_signal_divergence else "FROZEN_SCENARIO_MANIFEST",
                    source_role="conflict_detection_trace",
                ),
                quality="scope-aware conflict detection",
                gate_result=GateResult.PASS,
                metadata={"conflicts": [
                    {"conflict_id": record.conflict_id, "type": record.conflict_type,
                     "domain": record.decision_domain, "claim_ids": record.claim_ids,
                     "status": record.status, "resolution": record.resolution}
                    for record in conflicts
                ]},
            ),
        )
