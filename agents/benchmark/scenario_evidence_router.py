"""Scenario Evidence Router agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, internal_trace_citation


class ScenarioEvidenceRouterAgent(BenchmarkAgent):
    """Confirms that every benchmark run begins with one frozen bundle."""

    name = "scenario_evidence_router"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="The run is bound to one immutable, source-gated benchmark scenario.",
                summary=f"Loaded frozen scenario {scenario.identity.scenario_id} for {scenario.identity.crop}.",
                reasoning=(
                    "The router accepts only the validated FrozenBenchmarkScenario supplied by "
                    "FrozenBenchmarkLoader; no caller-supplied live evidence is accepted."
                ),
                confidence=1.0,
                source=internal_trace_citation(
                    source_document_id="FROZEN_SCENARIO_MANIFEST",
                    source_role="frozen_runtime_bundle",
                ),
                quality="frozen runtime bundle validated by loader",
                gate_result=GateResult.PASS,
                metadata={
                    "site_id": scenario.identity.site_id,
                    "scenario_status": scenario.manifest.get("scenario_status", ""),
                    "scenario_type": scenario.manifest.get("scenario_type", ""),
                    "regional_operation_plan_status": scenario.regional_operation_plan_summary.get("plan_status", ""),
                    "regional_operation_plan_item_count": len(scenario.regional_operation_plan_items),
                    "retrievable_operation_passage_count": len(scenario.retrievable_operation_passages),
                    "postharvest_context_status": scenario.postharvest_logistics_context.get("context_status", ""),
                    "postharvest_plan_item_count": len(scenario.postharvest_plan_items),
                    "postharvest_exact_crop_rag_passage_count": len(scenario.retrievable_postharvest_rag_passages),
                    "postharvest_facility_context_count": len(scenario.postharvest_site_facility_context),
                },
            ),
        )
