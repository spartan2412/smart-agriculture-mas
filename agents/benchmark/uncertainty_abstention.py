"""Uncertainty / Abstention agent."""
from __future__ import annotations

from typing import Any, Sequence

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult, TypedEvidenceClaim

from .base import BenchmarkAgent, citation_from, stable_unique


class UncertaintyAbstentionAgent(BenchmarkAgent):
    """Aggregates mandatory missing-evidence reasons without hiding them in prose."""

    name = "uncertainty_abstention_agent"

    def run(self, scenario: FrozenBenchmarkScenario, *, claims: Sequence[TypedEvidenceClaim] = (), **_: Any):
        restrictions = stable_unique([
            scenario.agent_permission("irrigation_action_agent"),
            scenario.agent_permission("fertilizer_prescription_agent"),
            scenario.agent_permission("pesticide_treatment_agent"),
            scenario.agent_permission("crop_stage_agent"),
            scenario.agent_permission("disease_diagnosis_agent"),
            scenario.agent_permission("leaf_vision_agent"),
            *(
                claim.block_reason or ""
                for claim in claims
                if claim.decision_domain == DecisionDomain.POSTHARVEST_LOGISTICS
                and claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
            ),
            *(claim.block_reason or "" for claim in claims if claim.disposition in {
                ClaimDisposition.BLOCKED, ClaimDisposition.ABSTAIN, ClaimDisposition.NO_DATA
            }),
        ])
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="Uncertainty and mandatory action abstentions are retained in the decision trace.",
                summary=f"{len(restrictions)} missing-evidence or safety restriction reason(s) are active for this scenario.",
                reasoning=(
                    "The system can describe source-backed context, but direct irrigation, farm "
                    "fertilizer, treatment, diagnosis, stage, and leaf-vision outputs remain gated."
                    " Post-harvest technical items also remain conditional until their stated lot or harvest "
                    "observation is available."
                ),
                confidence=1.0,
                source=citation_from(
                    scenario.capability_contract,
                    source_document_id="MAS_ENRICHMENT_CONTRACT",
                    source_role="per_scenario_uncertainty_policy",
                ),
                quality="explicit abstention policy",
                gate_result=GateResult.PASS,
                metadata={"restriction_reasons": restrictions},
            ),
        )
