"""Regulatory Compliance agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class RegulatoryComplianceAgent(BenchmarkAgent):
    """Exposes PPQS/CIBRC compatibility only as regulatory context."""

    name = "regulatory_compliance_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        policy = scenario.management_policy
        source_ids = tuple(part.strip() for part in policy.get("ppqs_source_ids", "").split(";") if part.strip())
        source_urls = tuple(part.strip() for part in policy.get("ppqs_source_urls", "").split(";") if part.strip())
        source_hashes = tuple(part.strip() for part in policy.get("ppqs_source_sha256s", "").split(";") if part.strip())
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.REGULATORY_CONTEXT,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.REGULATORY_LOOKUP_ONLY,
                claim="Regulatory crop/problem/formulation compatibility has been retained as an audit-time context check.",
                summary=f"PPQS/CIBRC cross-check sources: {', '.join(source_ids) if source_ids else 'none recorded'}.",
                reasoning=(
                    "Registration compatibility is not a diagnosis, economic-threshold finding, "
                    "or treatment recommendation. It cannot authorize a chemical application."
                ),
                confidence=0.9 if source_ids else 0.0,
                source=citation_from({
                    "source_document_id": source_ids[0] if source_ids else "",
                    "official_url": source_urls[0] if source_urls else "",
                    "source_raw_sha256": source_hashes[0] if source_hashes else "",
                    "source_location": policy.get("ppqs_locator", ""),
                }, source_role="regulatory_lookup_only"),
                quality=policy.get("protection_verification_status", "regulatory_context"),
                gate_result=GateResult.PASS if source_ids else GateResult.NOT_APPLICABLE,
                metadata={
                    "source_ids": source_ids,
                    "dose_alignment_status": policy.get("dose_alignment_status", ""),
                    "policy_restriction": "not_a_treatment_order",
                },
            ),
        )
