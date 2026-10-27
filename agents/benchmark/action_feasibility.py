"""Action Feasibility agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from, stable_unique


class ActionFeasibilityAgent(BenchmarkAgent):
    """Converts source-scoped action bindings into conditional or blocked claims."""

    name = "action_feasibility_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        actions = {record["action_id"]: record for record in scenario.action_records}
        bindings = {binding["action_id"]: binding for binding in scenario.action_bindings}
        planned_operations = sorted(
            scenario.retrievable_operation_passages,
            key=lambda item: (int(item.get("display_order", "0")), item.get("plan_item_id", "")),
        )
        conditional, blocked_reasons = [], []
        for plan_item in planned_operations:
            action_id = plan_item.get("action_id", "")
            record, binding = actions.get(action_id), bindings.get(action_id)
            if record is None or binding is None:
                raise ValueError(f"Regional operation-plan item has no action binding: {action_id}")
            status = binding.get("binding_status", "")
            if status != "conditionally_applicable_pending_unobserved_farm_condition":
                raise ValueError(f"Regional operation-plan item lost its conditional binding: {action_id}")
            condition = binding.get("field_condition_status", "unobserved_field_condition")
            conditional.append(self._claim(
                scenario,
                decision_domain=DecisionDomain.OFFICIAL_OPERATION,
                disposition=ClaimDisposition.CONDITIONAL_OPERATION,
                allowed_use=AllowedUse.CONDITIONAL_OPERATION_ONLY,
                claim=plan_item.get("operation_text") or record.get("operation_text", "A source-quoted operation is conditionally available."),
                summary=(
                    f"Conditional {record.get('action_category', 'operation')} from "
                    f"{record.get('source_document_id', '')}: {condition}."
                ),
                reasoning=(
                    "The regional operation plan includes this operation because crop, geography, season, "
                    "and source-time gates passed. The frozen scenario still lacks the field condition required by the source."
                ),
                confidence=0.9,
                source=citation_from(
                    plan_item,
                    source_document_id=record.get("source_document_id") or None,
                    source_role="source_quoted_conditional_operation_plan_item",
                    locator=record.get("source_location") or None,
                ),
                quality=status,
                gate_result=GateResult.ABSTAIN,
                block_reason=condition,
                metadata={
                    "plan_item_id": plan_item.get("plan_item_id", ""),
                    "action_id": action_id,
                    "action_category": record.get("action_category", ""),
                    "source_quote": record.get("source_quote", ""),
                    "method_text": plan_item.get("method_text", "") or record.get("method_text", ""),
                    "dose_text": plan_item.get("dose_text", "") or record.get("dose_text", ""),
                    "conditions_text": plan_item.get("conditions_text", "") or record.get("conditions_text", ""),
                    "binding_reason": binding.get("binding_reason", ""),
                    "temporal_status": binding.get("temporal_status", ""),
                },
            ))
        for binding in scenario.action_bindings:
            if binding.get("binding_status") != "conditionally_applicable_pending_unobserved_farm_condition":
                blocked_reasons.append(binding.get("binding_reason") or binding.get("binding_status", ""))
        if conditional:
            return tuple(conditional)
        reason = "; ".join(stable_unique(blocked_reasons)[:5]) or "no_source_scoped_operation_binding"
        return (
            self._blocked(
                scenario,
                decision_domain=DecisionDomain.OFFICIAL_OPERATION,
                claim="No source-quoted operation is currently feasible as a farm action.",
                summary="All operation bindings are blocked by source scope/time or missing field conditions.",
                reason=reason,
                source=citation_from(scenario.management_policy, source_document_id="OFFICIAL_ACTION_BINDING_MATRIX"),
                disposition=ClaimDisposition.BLOCKED,
                metadata={
                    "binding_count": len(scenario.action_bindings),
                    "binding_statuses": stable_unique([binding.get("binding_status", "") for binding in scenario.action_bindings]),
                    "regional_plan_status": scenario.regional_operation_plan_summary.get("plan_status", ""),
                },
            ),
        )
