"""Crop–district–season alignment validator agent."""
from __future__ import annotations

from typing import Any, Mapping

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, internal_trace_citation, stable_unique


class CropDistrictSeasonAlignmentValidatorAgent(BenchmarkAgent):
    """Rechecks join identities at the agent boundary before interpretation."""

    name = "crop_district_season_alignment_validator"
    _IDENTITY_KEYS = ("scenario_id", "site_id", "crop", "state", "district", "season", "decision_date")

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        expected = {
            "scenario_id": scenario.identity.scenario_id,
            "site_id": scenario.identity.site_id,
            "crop": scenario.identity.crop,
            "state": scenario.identity.state,
            "district": scenario.identity.district,
            "season": scenario.identity.season,
            "decision_date": scenario.identity.decision_date,
        }
        rows: tuple[tuple[str, Mapping[str, str]], ...] = (
            ("manifest", scenario.manifest), ("features", scenario.features),
            ("evidence_status", scenario.evidence_status), ("capability_contract", scenario.capability_contract),
            ("regional_calendar", scenario.regional_calendar), ("management_policy", scenario.management_policy),
            ("regional_operation_plan_summary", scenario.regional_operation_plan_summary),
            ("postharvest_logistics_context", scenario.postharvest_logistics_context),
            ("postharvest_site_summary", scenario.postharvest_site_summary),
            ("water_context", scenario.water_context_features), ("satellite_context", scenario.satellite_context_status),
            ("market_context", scenario.market_context_status),
        )
        mismatches: list[str] = []
        checked: list[str] = []
        for label, row in rows:
            for key in self._IDENTITY_KEYS:
                actual = str(row.get(key, "")).strip()
                if not actual:
                    continue
                if actual != expected[key]:
                    mismatches.append(f"{label}.{key}={actual!r}, expected {expected[key]!r}")
                else:
                    checked.append(f"{label}.{key}")
        for row in scenario.rag_scope:
            for key in ("scenario_id", "crop", "state", "district", "decision_date"):
                actual = str(row.get(key, "")).strip()
                if actual and actual != expected[key]:
                    mismatches.append(f"rag_scope.{key}={actual!r}, expected {expected[key]!r}")
        for row in scenario.regional_operation_plan_items:
            for key in self._IDENTITY_KEYS:
                actual = str(row.get(key, "")).strip()
                if actual and actual != expected[key]:
                    mismatches.append(f"regional_operation_plan.{key}={actual!r}, expected {expected[key]!r}")
        for row in scenario.postharvest_plan_items:
            for key in self._IDENTITY_KEYS:
                actual = str(row.get(key, "")).strip()
                if actual and actual != expected[key]:
                    mismatches.append(f"postharvest_plan.{key}={actual!r}, expected {expected[key]!r}")
        for row in scenario.postharvest_rag_scope:
            if row.get("scenario_id") != expected["scenario_id"]:
                mismatches.append(
                    f"postharvest_rag_scope.scenario_id={row.get('scenario_id')!r}, expected {expected['scenario_id']!r}"
                )
        for row in scenario.postharvest_site_facility_context:
            for key in ("site_id", "crop", "state", "district"):
                actual = str(row.get(key, "")).strip()
                if actual and actual != expected[key]:
                    mismatches.append(f"postharvest_facility.{key}={actual!r}, expected {expected[key]!r}")
        source = internal_trace_citation(
            source_document_id="FROZEN_SCENARIO_MANIFEST",
            source_role="cross_layer_identity_validation",
        )
        if mismatches:
            return (
                self._blocked(
                    scenario,
                    decision_domain=DecisionDomain.SYSTEM_SAFETY,
                    claim="Scenario evidence cannot be aligned safely.",
                    summary="Crop, district, season, or decision-date identity mismatch detected.",
                    reason="; ".join(mismatches),
                    source=source,
                    disposition=ClaimDisposition.BLOCKED,
                    metadata={"mismatches": mismatches},
                ),
            )
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="All populated identity fields align with the requested crop, district, season, and decision date.",
                summary="Cross-layer crop–district–season alignment passed.",
                reasoning=(
                    "The validator checked canonical scenario and enrichment rows, plus every "
                    "RAG scope row with a populated identity field."
                ),
                confidence=1.0,
                source=source,
                quality="cross-layer identity validation",
                gate_result=GateResult.PASS,
                metadata={
                    "checked_fields": stable_unique(checked),
                    "rag_scope_rows": len(scenario.rag_scope),
                    "regional_operation_plan_item_count": len(scenario.regional_operation_plan_items),
                    "postharvest_plan_item_count": len(scenario.postharvest_plan_items),
                    "postharvest_rag_scope_count": len(scenario.postharvest_rag_scope),
                    "postharvest_facility_context_count": len(scenario.postharvest_site_facility_context),
                },
            ),
        )
