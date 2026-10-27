"""Official Operations RAG agent."""
from __future__ import annotations

from typing import Any, Tuple

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, RetrievedPassage, citation_from, compact_text, lexical_tokens, stable_unique


class OfficialOperationsRAGAgent(BenchmarkAgent):
    """Retrieve only scenario-admitted corpus and conditional-operation passages."""

    name = "official_operations_rag_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You rank only supplied, already-admitted official passages for the frozen
scenario and the stated question. First identify the question's actual topic,
then select the passages that directly address that topic while retaining their
recorded crop, geography, season, date, source, and condition boundaries.

Rank by this order: (1) an exact source-quoted passage addressing the question;
(2) a scenario-scoped operation passage with its recorded condition; (3) an
exact-crop post-harvest passage when the question concerns harvest, drying,
storage, grading, packing, or logistics; and (4) a generic metadata-admitted
context passage. Within the same evidence class, prefer the most specific fact
and then preserve original allowed-fact order. For a broad or unanswered
question, leave the canonical deterministic ranking unchanged by selecting no
ID.

Never retrieve, cite, summarize, or use any source outside the supplied IDs.
Never treat collection-date facility or route context as availability, booking,
dispatch, freight, or sell/hold evidence. Never relax a source-time,
geography, crop, season, regulatory, lot-condition, or field-condition gate.
Retrieval relevance never authorizes a farm action.
""".strip()

    def retrieve(self, scenario: FrozenBenchmarkScenario, *, question: str = "", top_k: int = 5) -> Tuple[RetrievedPassage, ...]:
        """Lexically rank prefiltered chunks; ranking cannot resurrect a blocked source."""
        query = " ".join(part for part in (
            question, scenario.identity.crop, scenario.identity.state,
            scenario.identity.district, scenario.identity.season,
        ) if part)
        query_tokens = lexical_tokens(query)
        passages: list[RetrievedPassage] = []
        for chunk in scenario.retrievable_rag_chunks:
            overlap = len(query_tokens & lexical_tokens(chunk.get("text", "")))
            role_boost = 0.05 if "operation" in chunk.get("evidence_role", "") else 0.0
            passages.append(RetrievedPassage(
                source_document_id=chunk.get("source_document_id", ""),
                source_title=chunk.get("source_title", ""),
                official_url=chunk.get("official_url", ""),
                locator=chunk.get("location", ""),
                text=compact_text(chunk.get("text", ""), limit=900),
                score=overlap / max(1, len(query_tokens)) + role_boost,
                source_raw_sha256=chunk.get("source_raw_sha256") or None,
                corpus_layer="official_rag",
            ))
        # Recovery sources are intentionally not injected into the generic RAG
        # corpus: their validated use is limited to the specific source-quoted
        # operations bound to this scenario. The loader creates these passages
        # only from regional-plan items whose action binding already passed its
        # crop, geography, season, and source-time gates.
        for item in scenario.retrievable_operation_passages:
            text = " ".join(part for part in (
                item.get("operation_text", ""),
                item.get("method_text", ""),
                item.get("dose_text", ""),
                item.get("conditions_text", ""),
                item.get("source_quote", ""),
            ) if part)
            overlap = len(query_tokens & lexical_tokens(text))
            passages.append(RetrievedPassage(
                source_document_id=item.get("source_document_id", ""),
                source_title=item.get("source_title", ""),
                official_url=item.get("source_url", ""),
                locator=item.get("source_location", ""),
                text=compact_text(text, limit=900),
                score=overlap / max(1, len(query_tokens)) + 0.15,
                source_raw_sha256=item.get("source_raw_sha256") or None,
                corpus_layer="source_scoped_operation",
            ))
        # Fourth-enrichment handling passages are deliberately outside the
        # generic corpus.  The loader admits them only through an exact-crop
        # scenario scope, so a post-harvest query cannot retrieve a passage
        # from another crop or turn a collection-date infrastructure record
        # into a booking/dispatch claim.
        for passage in scenario.retrievable_postharvest_rag_passages:
            text = passage.get("text", "")
            overlap = len(query_tokens & lexical_tokens(text))
            passages.append(RetrievedPassage(
                source_document_id=passage.get("source_document_id", ""),
                source_title=passage.get("title", ""),
                official_url=passage.get("source_url", ""),
                locator=passage.get("source_location", ""),
                text=compact_text(text, limit=900),
                score=overlap / max(1, len(query_tokens)) + 0.20,
                source_raw_sha256=passage.get("source_raw_sha256") or None,
                corpus_layer="postharvest_exact_crop",
            ))
        return tuple(sorted(passages, key=lambda item: (-item.score, item.source_document_id, item.locator))[:max(0, top_k)])

    def run(self, scenario: FrozenBenchmarkScenario, **kwargs: Any):
        question, top_k = str(kwargs.get("question", "")), int(kwargs.get("top_k", 5))
        passages = self.retrieve(scenario, question=question, top_k=top_k)
        if not passages:
            return (
                self._blocked(
                    scenario,
                    decision_domain=DecisionDomain.OFFICIAL_OPERATION,
                    claim="No official RAG passage is metadata-admitted for this scenario.",
                    summary="The prefiltered RAG view is empty; no unrestricted retrieval fallback is used.",
                    reason="no_metadata_admitted_official_rag_chunk",
                    disposition=ClaimDisposition.NO_DATA,
                    metadata={"scope_decisions": len(scenario.rag_scope)},
                ),
            )
        first = passages[0]
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.OFFICIAL_OPERATION,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONDITIONAL_OPERATION_ONLY,
                claim="Metadata-admitted official passages are available for controlled operational reasoning.",
                summary=(
                    f"Retrieved {len(passages)} scope-admitted passage(s) from "
                    f"{len(stable_unique([item.source_document_id for item in passages]))} source(s)."
                ),
                reasoning=(
                    "Corpus chunks are metadata filtered first. Recovered operation passages enter only "
                    "after their full source binding passes. Post-harvest passages require an exact-crop "
                    "scenario scope; retrieval does not itself authorize a farm action, booking, or dispatch."
                ),
                confidence=0.9,
                source=citation_from({
                    "source_document_id": first.source_document_id, "official_url": first.official_url,
                    "source_raw_sha256": first.source_raw_sha256 or "", "source_location": first.locator,
                }, source_role="metadata_admitted_official_rag"),
                quality="metadata-admitted official RAG passages",
                gate_result=GateResult.PASS,
                metadata={
                    "question": compact_text(question, limit=300),
                    "passages": [{
                        "source_document_id": item.source_document_id,
                        "locator": item.locator,
                        "score": round(item.score, 6),
                        "corpus_layer": item.corpus_layer,
                    } for item in passages],
                    "blocked_scope_count": sum(1 for row in scenario.rag_scope if not row.get("rag_scope_status", "").startswith("admitted_")),
                    "source_scoped_operation_passage_count": len(scenario.retrievable_operation_passages),
                    "postharvest_exact_crop_passage_count": len(scenario.retrievable_postharvest_rag_passages),
                    "postharvest_scope_decision_count": len(scenario.postharvest_rag_scope),
                },
            ),
        )
