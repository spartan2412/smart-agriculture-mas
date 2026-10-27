"""Crop-Protection Safety agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class CropProtectionSafetyAgent(BenchmarkAgent):
    """Retains conditional regional IPM evidence while blocking treatment orders."""

    name = "crop_protection_safety_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        policy = scenario.management_policy
        detail_card = next(
            card
            for card in scenario.regional_policy_detail_cards
            if card.get("policy_domain") == "crop_protection"
        )
        plan_item = next(
            item for item in scenario.regional_operation_plan_items
            if item.get("plan_lane") == "regional_crop_protection_policy"
        )
        source = citation_from(
            plan_item,
            source_document_id=plan_item.get("source_document_id") or policy.get("protection_source_id") or None,
            source_role="conditional_regional_ipm_policy_plan_reference",
            locator=plan_item.get("source_location") or policy.get("protection_locator") or None,
        )
        context = self._claim(
            scenario,
            decision_domain=DecisionDomain.CROP_PROTECTION_SAFETY,
            disposition=ClaimDisposition.CONTEXT,
            allowed_use=AllowedUse.REGIONAL_POLICY_ONLY,
            claim="Regional crop-protection policy and regulatory cross-check context are available.",
            summary=(
                f"Protection source {policy.get('protection_source_id', '')} has status "
                f"{policy.get('protection_verification_status', '')}."
            ),
            reasoning=(
                "The policy describes diagnosis/threshold-triggered options. It does not prove a "
                "dated disease event, pest threshold, or treatment need at the frozen scenario."
            ),
            confidence=0.9,
            source=source,
            quality=policy.get("protection_verification_status", "regional_conditional_policy"),
            gate_result=GateResult.PASS,
            metadata={
                "ppqs_source_ids": policy.get("ppqs_source_ids", ""),
                "dose_alignment_status": policy.get("dose_alignment_status", ""),
                "protection_actionability": policy.get("protection_actionability", ""),
                "regional_plan_item_id": plan_item.get("plan_item_id", ""),
                "regional_plan_text": plan_item.get("farmer_visible_text", ""),
                "source_recorded_regional_ipm_detail": detail_card.get("detail_text", ""),
                "source_recorded_ipm_conditions": detail_card.get("applicability_conditions", ""),
                "source_recorded_ipm_boundary": detail_card.get("non_action_boundary", ""),
            },
        )
        blocked = self._blocked(
            scenario,
            decision_domain=DecisionDomain.CROP_PROTECTION_SAFETY,
            claim="No pesticide or insecticide treatment is issued.",
            summary="Treatment remains blocked until a dated diagnosis or threshold event exists.",
            reason=policy.get("crop_protection_status", "no_dated_diagnosis_or_threshold_event_for_treatment"),
            source=source,
            metadata={"conditions_and_exclusions": policy.get("conditions_and_exclusions", "")},
        )
        return (context, blocked)
