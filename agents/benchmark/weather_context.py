"""Weather Context agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class WeatherContextAgent(BenchmarkAgent):
    """Reports the exact historical NASA POWER window as retrospective context."""

    name = "weather_context_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You prioritize retrospective weather context for a source-backed regional
plan. Select only a fact that explicitly describes the frozen decision window
and helps explain the plan's documented seasonal setting or a stated condition.

Rank exact-window, source-reported temperature, precipitation, radiation, or
modelled wetness context ahead of broad or redundant context. Prefer a fact
only when its role is clear from its own text; do not infer agronomic effects
from a number alone. The representative-cell scope and retrospective time
window must remain visible in your interpretation.

Do not select a fact as evidence of current field moisture, irrigation need,
irrigation history, rainfall after the decision date, a forecast, or a
farm-level condition. Return an empty selection when the weather fact does not
materially improve the farmer-facing explanation.
""".strip()

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        values, status = scenario.water_context_features, scenario.water_context_status
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.WEATHER_CONTEXT,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="Historical NASA POWER weather and modelled water variables are available as retrospective context.",
                summary=(
                    f"Historical mean temperature {values.get('weather_t2m_mean_c', '')} °C; "
                    f"precipitation {values.get('weather_precipitation_total_mm', '')} mm; "
                    f"modelled root-zone wetness mean {values.get('water_gwetroot_mean_fraction', '')}."
                ),
                reasoning=(
                    "These are exact-window public observations/model outputs for the representative "
                    "cell. They do not establish current field moisture, irrigation history, or a forecast."
                ),
                confidence=0.95,
                source=citation_from(
                    scenario.manifest,
                    source_document_id="NASA_POWER_HISTORICAL_WINDOW",
                    source_role="historical_weather_and_modelled_water_context",
                ),
                quality=status.get("water_context_status", ""),
                gate_result=GateResult.PASS,
                metadata={
                    "weather_source_status": status.get("weather_source_status", ""),
                    "wetness_source_status": status.get("wetness_source_status", ""),
                    "irrigation_actionability": status.get("irrigation_actionability", ""),
                    "restriction_reason": status.get("restriction_reason", ""),
                    "observed_days": values.get("weather_observed_days", ""),
                },
            ),
        )
