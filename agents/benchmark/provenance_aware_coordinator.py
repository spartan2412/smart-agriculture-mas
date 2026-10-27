"""Provenance-Aware Coordinator agent."""
from __future__ import annotations

from typing import Any, Sequence

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult, TypedEvidenceClaim

from .base import BenchmarkAgent, BenchmarkDecision, ConflictRecord, RetrievedPassage, compact_text, internal_trace_citation, stable_unique
from .conflict_resolution import ConflictResolutionPolicy


class ProvenanceAwareCoordinatorAgent(BenchmarkAgent):
    """Combines claims deterministically; it has no authority to override a gate."""

    name = "provenance_aware_coordinator_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You prioritize already-approved plan cards for presentation only. The canonical
order is the default and is usually preferable. Select a card only when the
farmer question makes that card materially more relevant than the canonical
order; otherwise select no ID and preserve the deterministic ordering.

For a seasonal question, prioritize the calendar card. For a nutrient or crop
protection question, prioritize only the matching policy card. For a specific
source-quoted crop operation, prioritize its conditional operation card. For a
post-harvest question, prioritize only the matching crop-scoped handling card;
do not promote collection-date facility/route context unless the question asks
for its documented context. Return selected IDs in the desired display order.

Never suppress mandatory cards or reorder a card solely because its wording is
more forceful. Never change the deterministic decision status, source scope,
citation set, conflict handling, missing condition, feasibility, or direct
action permission. A conditional card never becomes a farm instruction.
""".strip()

    def __init__(self, *, conflict_policy: ConflictResolutionPolicy | None = None) -> None:
        self.conflict_policy = conflict_policy or ConflictResolutionPolicy()

    def coordinate(
        self,
        scenario: FrozenBenchmarkScenario,
        claims: Sequence[TypedEvidenceClaim],
        passages: Sequence[RetrievedPassage],
        conflicts: Sequence[ConflictRecord],
    ) -> BenchmarkDecision:
        resolution = self.conflict_policy.resolve(scenario, claims, conflicts)
        excluded_claim_ids = set(resolution.excluded_claim_ids)
        decision_claims = [claim for claim in claims if claim.claim_id not in excluded_claim_ids]
        conditional = [
            claim for claim in decision_claims
            if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
        ]
        supported = [
            claim for claim in decision_claims
            if claim.disposition == ClaimDisposition.SUPPORTED_OPERATION and claim.gate_result == GateResult.PASS
        ]
        uncertainty_reasons = stable_unique([
            *(claim.block_reason or "" for claim in decision_claims if claim.disposition in {
                ClaimDisposition.BLOCKED, ClaimDisposition.ABSTAIN, ClaimDisposition.NO_DATA
            }),
            scenario.agent_permission("irrigation_action_agent"),
            scenario.agent_permission("fertilizer_prescription_agent"),
            scenario.agent_permission("pesticide_treatment_agent"),
        ])
        if supported:
            selected = supported[0]
            status, operation_status, direct = (
                "source_supported_operation", "supported_with_all_recorded_gates_passed", True
            )
            operation, rationale = selected.claim, "A source-quoted operation passed its stored scope and feasibility gates."
        elif conditional:
            selected = conditional[0]
            status, operation_status, direct = (
                "conditional_operation_pending_field_precondition", "not_issued_as_direct_farm_action", False
            )
            operation = selected.claim
            rationale = (
                "A source-quoted post-harvest technical operation is crop scoped, but its stated "
                "lot/harvest precondition is not observed in this frozen scenario."
                if selected.decision_domain == DecisionDomain.POSTHARVEST_LOGISTICS else
                "A source-quoted operation is time/location/crop scoped, but its stated field "
                "precondition is not observed in this frozen scenario."
            )
        else:
            status, operation_status, direct = (
                "context_only_no_direct_farm_action", "no_feasible_source_scoped_operation", False
            )
            operation = "No farm operation is issued from this historical public-data context."
            rationale = (
                "The available evidence supports contextual explanation only; no source-scoped "
                "operation passed all required scenario and field-condition gates."
            )
        # Retrieval order may be presentation-ranked by the bounded LLM, but
        # citation membership and citation order remain deterministic.
        citations = tuple(sorted(stable_unique([
            *(
                claim.source.source_document_id or ""
                for claim in decision_claims
                if claim.source.source_document_id
            ),
            *(passage.source_document_id for passage in passages),
        ])))
        return BenchmarkDecision(
            scenario_id=scenario.identity.scenario_id,
            decision_status=status,
            direct_farm_action_issued=direct,
            operation_text=compact_text(operation, limit=700),
            operation_status=operation_status,
            rationale=compact_text(rationale, limit=700),
            uncertainty_reasons=uncertainty_reasons,
            conflict_records=tuple(conflicts),
            citations=citations,
            trace_claim_count=len(claims),
            conflict_resolution_records=resolution.records,
        )

    def run(
        self,
        scenario: FrozenBenchmarkScenario,
        *,
        claims: Sequence[TypedEvidenceClaim] = (),
        passages: Sequence[RetrievedPassage] = (),
        conflicts: Sequence[ConflictRecord] = (),
        **_: Any,
    ):
        decision = self.coordinate(scenario, claims, passages, conflicts)
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="The coordinator produced a gate-constrained benchmark decision trace.",
                summary=f"Coordinator status: {decision.decision_status}.",
                reasoning=decision.rationale,
                confidence=1.0 if not decision.direct_farm_action_issued else 0.9,
                source=internal_trace_citation(
                    source_document_id="FROZEN_SCENARIO_MANIFEST",
                    source_role="coordinator_trace",
                ),
                quality="deterministic provenance-aware coordination",
                gate_result=GateResult.PASS,
                metadata={
                    "decision_status": decision.decision_status,
                    "operation_status": decision.operation_status,
                    "direct_farm_action_issued": decision.direct_farm_action_issued,
                    "citation_count": len(decision.citations),
                    "conflict_count": len(decision.conflict_records),
                    "conflict_resolution_count": len(decision.conflict_resolution_records),
                    "conflict_resolution_statuses": tuple(
                        record.status for record in decision.conflict_resolution_records
                    ),
                    "excluded_conflicted_claim_count": sum(
                        len(record.rejected_claim_ids) + len(record.deferred_claim_ids)
                        for record in decision.conflict_resolution_records
                    ),
                    "postharvest_plan_item_count": len(scenario.postharvest_plan_items),
                    "postharvest_context_status": scenario.postharvest_logistics_context.get("context_status", ""),
                },
            ),
        )
