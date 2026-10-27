"""Soil Context agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class SoilContextAgent(BenchmarkAgent):
    """Reports static SoilGrids profile evidence without inventing available N/P/K."""

    name = "soil_context_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You prioritize static SoilGrids context only when it helps delimit the scope
of an approved regional plan. Select a fact when it clearly identifies a
stable, source-backed property of the documented representative cell and adds
useful context beyond the mandatory plan cards.

Prefer a direct property/scope fact over a vague interpretation. Do not select
a soil fact merely because it contains a value. Treat the result as a gridded
predictor for a representative cell, with its stated depth and resolution,
rather than as an individual field measurement.

Never treat it as a soil test, current moisture measurement, plant-available
N/P/K measurement, fertility diagnosis, or proof of a soil constraint. Never
calculate or justify a fertilizer dose. Return an empty selection when static
soil context would not improve the explanation.
""".strip()

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        profile = scenario.registry_soil_profile
        if not profile:
            return (
                self._blocked(
                    scenario,
                    decision_domain=DecisionDomain.SOIL_CONTEXT,
                    claim="Static soil context is unavailable.",
                    summary="No SoilGrids profile is attached to the frozen site.",
                    reason="missing_registry_soilgrids_profile",
                    disposition=ClaimDisposition.NO_DATA,
                ),
            )
        property_values = {row.get("property_id", "unknown"): row.get("raw_value", "") for row in profile}
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SOIL_CONTEXT,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="Static SoilGrids predictors are available for the documented representative cell.",
                summary=(
                    f"Six frozen 0–5 cm SoilGrids properties are present: "
                    f"{', '.join(sorted(property_values))}."
                ),
                reasoning=(
                    "The values are static gridded predictors for a representative cell. They are "
                    "not a field soil test, current soil moisture, or available farm N/P/K measurement."
                ),
                confidence=0.9,
                source=citation_from(
                    profile[0], source_document_id="SOILGRIDS", source_role="static_gridded_soil_context"
                ),
                quality="static 0–5 cm SoilGrids WCS profile",
                gate_result=GateResult.PASS,
                metadata={
                    "property_raw_values": property_values,
                    "property_count": len(profile),
                    "restriction": "not_field_soil_test_or_available_npk",
                },
                spatial_scope=(
                    f"documented representative cropland cell; static gridded prediction; "
                    f"not a field soil-test sample in {scenario.identity.district}, {scenario.identity.state}"
                ),
            ),
        )
