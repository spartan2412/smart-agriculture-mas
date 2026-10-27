"""Fertilizer Baseline agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class FertilizerBaselineAgent(BenchmarkAgent):
    """Separates a regional policy reference from an unsupported farm dose."""

    name = "fertilizer_baseline_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You prioritize official regional nutrient-policy context for the frozen
crop-region-season plan. Select the plan-reference fact when it explicitly
matches that policy scope. Select the policy-boundary fact when the farmer
message could otherwise make the regional reference sound like an individual
field prescription.

Rank the applicable official policy reference first. Add the boundary only
when it is necessary to preserve the distinction between a regional schedule
and a farm-specific recommendation. Prefer an empty selection to highlighting
an irrelevant nutrient fact.

Never calculate, convert, optimize, or prescribe N, P, or K. Never infer a
field soil test, plant-available nutrients, actual crop stage, prior
application, crop response, or a fertilizer need. A regional schedule is never
permission to issue a farm-specific dose.
""".strip()

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        policy = scenario.management_policy
        detail_card = next(
            card
            for card in scenario.regional_policy_detail_cards
            if card.get("policy_domain") == "fertilizer"
        )
        plan_item = next(
            item for item in scenario.regional_operation_plan_items
            if item.get("plan_lane") == "regional_nutrient_policy"
        )
        source = citation_from(
            plan_item,
            source_document_id=plan_item.get("source_document_id") or policy.get("fertilizer_source_id") or None,
            source_role="regional_fertilizer_policy_plan_reference",
            locator=plan_item.get("source_location") or policy.get("fertilizer_locator") or None,
        )
        baseline = self._claim(
            scenario,
            decision_domain=DecisionDomain.FERTILIZER_BASELINE,
            disposition=ClaimDisposition.CONTEXT,
            allowed_use=AllowedUse.REGIONAL_POLICY_ONLY,
            claim="A crop- and region-scoped fertilizer baseline is available as policy context.",
            summary=(
                f"Regional source {policy.get('fertilizer_source_id', '')} is verified for "
                f"{scenario.identity.crop} in {scenario.identity.state}."
            ),
            reasoning=(
                "The source is a regional baseline. It must not be converted into a farm-specific "
                "dose because the frozen scenario lacks a field soil test and observed crop stage."
            ),
            confidence=0.9,
            source=source,
            quality=policy.get("fertilizer_verification_status", "regional_policy_reference"),
            gate_result=GateResult.PASS,
            metadata={
                "actionability": policy.get("fertilizer_actionability", ""),
                "conditions_and_exclusions": policy.get("conditions_and_exclusions", ""),
                "farm_fertilizer_status": policy.get("farm_fertilizer_status", ""),
                "regional_plan_item_id": plan_item.get("plan_item_id", ""),
                "regional_plan_text": plan_item.get("farmer_visible_text", ""),
                "source_recorded_regional_schedule": detail_card.get("detail_text", ""),
                "source_recorded_schedule_conditions": detail_card.get("applicability_conditions", ""),
                "source_recorded_schedule_boundary": detail_card.get("non_action_boundary", ""),
            },
        )
        blocked = self._blocked(
            scenario,
            decision_domain=DecisionDomain.FERTILIZER_BASELINE,
            claim="No farm-specific fertilizer dose is issued.",
            summary="Regional fertilizer guidance is retained, but a personalized prescription is blocked.",
            reason=policy.get(
                "farm_fertilizer_status", "no_field_soil_test_or_actual_crop_stage_for_fertilizer_prescription"
            ),
            source=source,
            metadata={"required_policy_conditions": policy.get("conditions_and_exclusions", "")},
        )
        return (baseline, blocked)
