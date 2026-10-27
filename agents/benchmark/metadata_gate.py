"""Metadata Gate agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class MetadataGateAgent(BenchmarkAgent):
    """Makes every capability permission and mandatory abstention explicit."""

    name = "metadata_gate"
    _CONTEXT_FIELDS = (
        "weather_water_context", "soil_context", "satellite_context", "market_context",
        "regional_calendar_context", "fertilizer_policy_context", "crop_protection_policy_context",
    )
    _ACTION_FIELDS = (
        "irrigation_action_agent", "fertilizer_prescription_agent", "pesticide_treatment_agent",
        "crop_stage_agent", "disease_diagnosis_agent", "leaf_vision_agent",
    )

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        context_permissions = {field: scenario.agent_permission(field) for field in self._CONTEXT_FIELDS}
        action_permissions = {field: scenario.agent_permission(field) for field in self._ACTION_FIELDS}
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="Only contextual evidence may be used; farm-specific action domains remain gated.",
                summary=(
                    f"{len(context_permissions)} contextual permissions available; "
                    f"{len(action_permissions)} direct-action/stage/vision restrictions retained."
                ),
                reasoning=(
                    "The capability contract permits historical, static, representative-cell, and "
                    "regional-policy context but does not authorize irrigation, farm fertilizer, "
                    "pesticide treatment, diagnosis, observed stage, or leaf-vision claims."
                    " The post-harvest layer is limited to conditional technical handling references "
                    "and collection-date infrastructure context; it cannot issue harvest, booking, "
                    "storage, dispatch, transport, or sell/hold instructions."
                ),
                confidence=1.0,
                source=citation_from(
                    scenario.capability_contract,
                    source_document_id="MAS_ENRICHMENT_CONTRACT",
                    source_role="per_scenario_permission_gate",
                ),
                quality="per-scenario capability contract",
                gate_result=GateResult.PASS,
                metadata={
                    "context_permissions": context_permissions,
                    "restricted_action_permissions": action_permissions,
                    "mas_output_rule": scenario.agent_permission("mas_output_rule"),
                    "postharvest_context_status": scenario.postharvest_logistics_context.get("context_status", ""),
                    "postharvest_allowed_use": scenario.postharvest_logistics_context.get("allowed_use", ""),
                    "postharvest_not_supported": scenario.postharvest_logistics_context.get("not_supported", ""),
                },
            ),
        )
