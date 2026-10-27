"""Evidence Provenance agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, internal_trace_citation, stable_unique


class EvidenceProvenanceAgent(BenchmarkAgent):
    """Summarizes retained source provenance without re-fetching a source."""

    name = "evidence_provenance_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        raw_sources = {
            "weather": scenario.manifest.get("weather_raw_path", ""),
            "market": scenario.manifest.get("market_raw_path", ""),
            "satellite": scenario.manifest.get("satellite_raw_path", "") or "registry_preflight_sentinel_reference",
        }
        source_ids = stable_unique([
            scenario.manifest.get("fertilizer_source_id", ""),
            scenario.manifest.get("protection_source_id", ""),
            *(row.get("source_document_id", "") for row in scenario.rag_scope),
            *(row.get("source_document_id", "") for row in scenario.regional_operation_plan_items),
            *(row.get("source_document_id", "") for row in scenario.postharvest_plan_items),
            *(row.get("source_document_id", "") for row in scenario.postharvest_site_facility_context),
        ])
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="Every exposed evidence layer has retained source identity and provenance metadata.",
                summary=(
                    f"Trace includes retained weather, market, satellite, management, regional-plan, post-harvest, and "
                    f"{len(source_ids)} scoped document identifiers."
                ),
                reasoning=(
                    "The loader verified retained scenario payloads, relevant recovered-source artifacts, "
                    "regional/post-harvest plan provenance before execution. It exposes only scope-filtered RAG "
                    "chunks, source-scoped operation passages, and exact-crop post-harvest passages."
                ),
                confidence=1.0,
                source=internal_trace_citation(
                    source_document_id="FROZEN_SCENARIO_MANIFEST",
                    source_role="provenance_index",
                ),
                quality="hash-linked frozen provenance",
                gate_result=GateResult.PASS,
                metadata={
                    "raw_source_paths": raw_sources,
                    "scoped_source_document_ids": source_ids,
                    "retrievable_chunk_count": len(scenario.retrievable_rag_chunks),
                    "retrievable_operation_passage_count": len(scenario.retrievable_operation_passages),
                    "regional_operation_plan_status": scenario.regional_operation_plan_summary.get("plan_status", ""),
                    "regional_operation_plan_item_count": len(scenario.regional_operation_plan_items),
                    "regional_operation_plan_input_roles": tuple(
                        row.get("artifact_role", "") for row in scenario.regional_operation_plan_provenance
                    ),
                    "recovered_operation_source_ids": tuple(
                        row.get("source_document_id", "") for row in scenario.recovered_operation_sources
                    ),
                    "total_scope_decisions": len(scenario.rag_scope),
                    "postharvest_source_document_ids": tuple(
                        row.get("source_document_id", "") for row in scenario.postharvest_source_inventory
                    ),
                    "postharvest_provenance_roles": tuple(
                        row.get("artifact_role", "") for row in scenario.postharvest_logistics_provenance
                    ),
                    "postharvest_plan_item_count": len(scenario.postharvest_plan_items),
                    "postharvest_exact_crop_passage_count": len(scenario.retrievable_postharvest_rag_passages),
                    "postharvest_site_facility_context_count": len(scenario.postharvest_site_facility_context),
                    "postharvest_static_route_context_count": len(scenario.postharvest_static_route_context),
                },
            ),
        )
