"""Market Evidence agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class MarketEvidenceAgent(BenchmarkAgent):
    """Reports source-published historical price comparisons without a sale instruction."""

    name = "market_evidence_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You prioritize historical Agmarknet evidence that adds a concise, published
market context beside the approved plan. Select only a fact that explicitly
comes from the frozen crop-district-state monthly report and contains a
documented comparison or reported price context.

Prefer an exact source-published comparison over an incomplete, unavailable,
or generic market fact. Keep the report's historical month and geographic scope
central. Choose a market fact only when it makes the farmer message more
informative than the mandatory seasonal and operation cards.

Never infer a current mandi quotation, forecast, lot quality, storage cost,
transport cost, quantity, profitability, or sell/hold recommendation. Return
an empty selection when the source-published comparison is unavailable or not
useful for this scenario.
""".strip()

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        values, status = scenario.market_context_features, scenario.market_context_status
        availability = values.get("market_comparison_availability", "")
        source_record = {
            "source_url": scenario.market_context_manifest.get("source_url", ""),
            "raw_path": scenario.market_context_manifest.get("raw_path", ""),
            "response_sha256": scenario.market_context_manifest.get("verified_payload_sha256", ""),
        }
        source = citation_from(
            source_record,
            source_document_id="AGMARKNET_MONTHLY_REPORT",
            source_role="historical_market_context",
            locator=f"decision date {scenario.identity.decision_date}",
        )
        if not status.get("market_context_status", "").startswith("available_"):
            return (
                self._blocked(
                    scenario,
                    decision_domain=DecisionDomain.MARKET_CONTEXT,
                    claim="Historical market comparison is unavailable in the exact frozen report.",
                    summary="The scenario preserves an unavailable market-comparison status.",
                    reason=status.get("restriction_reason", "market_context_unavailable"),
                    source=source,
                    disposition=ClaimDisposition.NO_DATA,
                    metadata={"market_status": dict(status), "availability": availability},
                ),
            )
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.MARKET_CONTEXT,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="The exact historical Agmarknet report provides a source-published market comparison.",
                summary=(
                    f"Reported monthly mean {values.get('market_current_month_price_mean_as_reported', '')}; "
                    f"prior-month change {values.get('market_previous_month_change_percent', '')}% and "
                    f"year-over-year change {values.get('market_same_month_year_over_year_percent', '')}%."
                ),
                reasoning=(
                    "The comparison comes from the same frozen official report. It contains no "
                    "current lot quality, storage cost, quantity, or forecast and cannot issue sell/hold advice."
                ),
                confidence=0.95,
                source=source,
                quality=status.get("market_context_status", ""),
                gate_result=GateResult.PASS,
                metadata={
                    "availability": availability,
                    "prior_month_status": status.get("market_prior_month_status", ""),
                    "prior_year_status": status.get("market_same_month_prior_year_status", ""),
                    "restriction_reason": status.get("restriction_reason", ""),
                    "price_unit_status": scenario.features.get("market_price_unit_status", ""),
                },
            ),
        )
