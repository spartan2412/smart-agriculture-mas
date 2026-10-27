"""Source-scoped post-harvest storage and logistics context agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from, compact_text


class PostharvestStorageLogisticsAgent(BenchmarkAgent):
    """Expose only conditional crop handling and collection-date logistics context.

    The fourth enrichment deliberately does not contain lot observations, live
    facility availability, booking status, vehicle availability, freight, or a
    sell/hold outcome.  This role therefore turns its source-linked records
    into conditional plan cards and contextual infrastructure facts, never a
    dispatch, storage, or harvest instruction.
    """

    name = "postharvest_storage_logistics_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        context = scenario.postharvest_logistics_context
        summary = scenario.postharvest_site_summary
        plan_items = tuple(sorted(
            scenario.postharvest_plan_items,
            key=lambda item: (int(item.get("display_order", "0")), item.get("plan_item_id", "")),
        ))
        if (
            context.get("context_status") != "available_source_linked_postharvest_context"
            or not plan_items
        ):
            return (
                self._blocked(
                    scenario,
                    decision_domain=DecisionDomain.POSTHARVEST_LOGISTICS,
                    claim="No source-linked post-harvest plan is available for this scenario.",
                    summary="The post-harvest enrichment is unavailable or has no crop-scoped plan item.",
                    reason="no_crop_scoped_postharvest_plan_item",
                    disposition=ClaimDisposition.NO_DATA,
                    metadata={"postharvest_context_status": context.get("context_status", "")},
                ),
            )
        claims = []
        for item in plan_items:
            claims.append(self._claim(
                scenario,
                decision_domain=DecisionDomain.POSTHARVEST_LOGISTICS,
                disposition=ClaimDisposition.CONDITIONAL_OPERATION,
                allowed_use=AllowedUse.CONDITIONAL_OPERATION_ONLY,
                claim=f"Post-harvest plan — {item.get('farmer_visible_label', 'technical handling')}: {item.get('operation_text', '')}",
                summary=(
                    f"{item.get('farmer_visible_label', 'Post-harvest handling')}: "
                    f"source-quoted technical reference, pending {item.get('missing_observation', 'the stated lot observation')}"
                ),
                reasoning=(
                    f"{item.get('conditions_text', '')} The frozen scenario does not contain the required "
                    "lot/harvest observation, so this remains a conditional planning reference rather than a farm action."
                ),
                confidence=0.95,
                source=citation_from(item, source_role="source_quoted_conditional_postharvest_operation"),
                quality="crop-scoped source-quoted technical handling reference",
                gate_result=GateResult.ABSTAIN,
                block_reason=item.get("missing_observation", "required lot observation is not recorded"),
                metadata={
                    "plan_item_id": item.get("plan_item_id", ""),
                    "operation_id": item.get("operation_id", ""),
                    "plan_lane": item.get("plan_lane", ""),
                    "method_or_parameter": item.get("method_or_parameter", ""),
                    "conditions_text": item.get("conditions_text", ""),
                    "source_quote": compact_text(item.get("source_quote", ""), limit=700),
                    "missing_observation": item.get("missing_observation", ""),
                    "item_status": item.get("item_status", ""),
                    "actionability_status": item.get("actionability_status", ""),
                    "decision_target": f"postharvest:{item.get('operation_id', '')}",
                    "assertion_polarity": "supports",
                    "direct_farm_action_issued": False,
                },
            ))
        facility_context = scenario.postharvest_site_facility_context
        route_context = scenario.postharvest_static_route_context
        context_source = facility_context[0] if facility_context else scenario.postharvest_handling_profile
        claims.append(self._claim(
            scenario,
            decision_domain=DecisionDomain.POSTHARVEST_LOGISTICS,
            disposition=ClaimDisposition.CONTEXT,
            allowed_use=AllowedUse.CONTEXT_ONLY,
            claim="Source-linked post-harvest infrastructure context is available for planning, not for booking or dispatch.",
            summary=summary.get("summary_text", "Source-linked infrastructure candidate context is available."),
            reasoning=(
                "Named infrastructure records are collection-date public-directory context. They do not establish "
                "commodity acceptance, lot suitability, capacity, vacancy, booking, live traffic, vehicle availability, "
                "freight, or historical scenario-date availability."
            ),
            confidence=0.9,
            source=citation_from(context_source, source_role="collection_date_postharvest_infrastructure_context"),
            quality="source-linked collection-date infrastructure registry context",
            gate_result=GateResult.PASS,
            metadata={
                "profile_id": context.get("profile_id", ""),
                "handling_operation_count": len(plan_items),
                "facility_candidate_count": len([
                    row for row in facility_context if row.get("context_kind") == "nhb_mapped_project_proximity"
                ]),
                "warehouse_candidate_count": len([
                    row for row in facility_context if row.get("context_kind") == "wdra_registered_warehouse_district_match"
                ]),
                "static_road_route_count": len(route_context),
                "state_infrastructure_record_count": len(scenario.postharvest_state_infrastructure),
                "infrastructure_context_status": summary.get("infrastructure_context_status", ""),
                "not_supported": summary.get("not_supported", ""),
                "direct_farm_action_issued": False,
            },
        ))
        return tuple(claims)
