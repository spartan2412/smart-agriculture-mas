"""Regional Calendar / Operation Window agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class RegionalCalendarOperationWindowAgent(BenchmarkAgent):
    """States declared regional season-window position without inferring field stage."""

    name = "regional_calendar_operation_window_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        calendar = scenario.regional_calendar
        plan_summary = scenario.regional_operation_plan_summary
        plan_items = scenario.regional_operation_plan_items
        calendar_item = next(
            (item for item in plan_items if item.get("plan_lane") == "regional_calendar"),
            None,
        )
        calendar_claim = self._claim(
            scenario,
            decision_domain=DecisionDomain.REGIONAL_CALENDAR,
            disposition=ClaimDisposition.CONTEXT,
            allowed_use=AllowedUse.REGIONAL_POLICY_ONLY,
            claim="The decision date has a documented position in the declared district-scale crop season window.",
            summary=(
                f"{scenario.identity.crop} in {scenario.identity.district}: "
                f"{calendar.get('season_window_position', '')} of declared {calendar.get('season_window', '')} window."
            ),
            reasoning=(
                "The calendar derives a regional season-window position from CRIDA documents. "
                "It does not observe sowing date, variety, crop stage, or maturity in a field."
            ),
            confidence=0.9,
            source=citation_from(
                calendar,
                source_document_id=calendar.get("crop_season_source_id") or None,
                source_role="district_crop_season_context",
                locator=calendar.get("crop_season_locator") or None,
            ),
            quality=calendar.get("calendar_status", ""),
            gate_result=GateResult.PASS,
            metadata={
                "season_month_index": calendar.get("season_month_index", ""),
                "season_month_count": calendar.get("season_month_count", ""),
                "crop_stage_status": calendar.get("crop_stage_status", ""),
                "calendar_interpretation": calendar.get("calendar_interpretation", ""),
                "regional_plan_summary_id": plan_summary.get("scenario_id", ""),
            },
            temporal_scope=(
                f"declared {scenario.identity.season} season window {calendar.get('season_window', '')}; "
                f"decision date {scenario.identity.decision_date}; not observed field stage"
            ),
        )
        plan_claim = self._claim(
            scenario,
            decision_domain=DecisionDomain.REGIONAL_CALENDAR,
            disposition=ClaimDisposition.CONTEXT,
            allowed_use=AllowedUse.REGIONAL_POLICY_ONLY,
            claim="A source-linked regional operation plan is available for this scenario.",
            summary=plan_summary.get("plan_summary", "Regional plan summary is available."),
            reasoning=(
                "The plan preserves regional calendar, nutrient-policy, and IPM-policy references, "
                "plus only source-scoped conditional operations. It does not observe farm conditions "
                "or issue a direct farm action."
            ),
            confidence=0.95,
            source=citation_from(
                calendar_item or calendar,
                source_document_id=(calendar_item or calendar).get("source_document_id") or calendar.get("crop_season_source_id") or None,
                source_role="source_linked_regional_operation_plan",
                locator=(calendar_item or calendar).get("source_location") or calendar.get("crop_season_locator") or None,
            ),
            quality=plan_summary.get("plan_status", "regional_plan_available"),
            gate_result=GateResult.PASS,
            metadata={
                "plan_status": plan_summary.get("plan_status", ""),
                "total_plan_item_count": plan_summary.get("total_plan_item_count", ""),
                "regional_reference_item_count": plan_summary.get("regional_reference_item_count", ""),
                "conditional_source_quoted_operation_count": plan_summary.get("conditional_source_quoted_operation_count", ""),
                "conditional_action_ids": plan_summary.get("conditional_action_ids", ""),
                "plan_item_ids": tuple(item.get("plan_item_id", "") for item in plan_items),
            },
        )
        return (
            calendar_claim,
            plan_claim,
        )
