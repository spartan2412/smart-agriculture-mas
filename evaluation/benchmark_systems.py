"""Controlled benchmark systems for architecture baselines and ablations.

Every system consumes the same ``FrozenBenchmarkLoader`` scenario bundle.
Only A0 is the farmer-facing proposed MAS.  A1--A6 are explicitly offline
evaluation systems: they preserve the direct-action prohibition but omit a
declared architectural component so the external oracle can measure the
resulting conformance loss.
"""
from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from agents.benchmark.base import BenchmarkAgent, BenchmarkDecision, BenchmarkEvaluationRecord, RetrievedPassage
from agents.benchmark.benchmark_evaluator import BenchmarkEvaluatorAgent
from agents.benchmark.official_operations_rag import OfficialOperationsRAGAgent
from agents.benchmark.regional_calendar_operation_window import RegionalCalendarOperationWindowAgent
from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario, ScenarioIntegrityError
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult, TypedEvidenceClaim
from graph.benchmark_workflow import BenchmarkMASWorkflow, BenchmarkRun
from llm.benchmark_llm_client import BenchmarkLLMClient


SYSTEM_IDS: Tuple[str, ...] = ("A0", "A1", "A2", "A3", "A4", "A5", "A6")
EVALUATION_ONLY_SYSTEM_IDS = frozenset({"A1", "A2", "A3", "A4", "A5", "A6"})


class _BaselineTraceAgent(BenchmarkAgent):
    """Local helper for transparent baseline-only trace claims."""

    def __init__(self, name: str) -> None:
        self.name = name

    def describe(
        self,
        scenario: FrozenBenchmarkScenario,
        *,
        summary: str,
        reasoning: str,
        source_row: Mapping[str, str],
        source_role: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> TypedEvidenceClaim:
        from agents.benchmark.base import citation_from

        return self._claim(
            scenario,
            decision_domain=DecisionDomain.SYSTEM_SAFETY,
            disposition=ClaimDisposition.CONTEXT,
            allowed_use=AllowedUse.CONTEXT_ONLY,
            claim="An evaluation-only baseline produced a source-bounded trace.",
            summary=summary,
            reasoning=reasoning,
            confidence=1.0,
            source=citation_from(source_row, source_role=source_role),
            quality="evaluation_only_baseline_not_farmer_facing",
            gate_result=GateResult.PASS,
            metadata=dict(metadata or {}),
        )


class _StandaloneBaselineWorkflow:
    """Shared runner shell for non-coordinated A1/A2 baselines."""

    system_id = ""

    def __init__(self, loader: Optional[FrozenBenchmarkLoader] = None) -> None:
        self.loader = loader or FrozenBenchmarkLoader()
        self.evaluator = BenchmarkEvaluatorAgent()

    @staticmethod
    def _evaluation(
        scenario: FrozenBenchmarkScenario,
        decision: BenchmarkDecision,
        claims: Sequence[TypedEvidenceClaim],
    ) -> tuple[BenchmarkEvaluationRecord, Tuple[TypedEvidenceClaim, ...]]:
        evaluator = BenchmarkEvaluatorAgent()
        record = evaluator.evaluate(scenario, decision, claims)
        return record, tuple(claims) + tuple(evaluator.run(scenario, decision=decision, claims=claims))

    def run(
        self,
        scenario_id: str,
        *,
        question: str = "",
        verify_raw_hashes: bool = True,
    ) -> BenchmarkRun:
        if question:
            raise ValueError("Frozen baseline comparisons use the protocol-fixed empty farmer question.")
        scenario = self.loader.load(scenario_id, verify_raw_hashes=verify_raw_hashes)
        return self._run_scenario(scenario)

    def _run_scenario(self, scenario: FrozenBenchmarkScenario) -> BenchmarkRun:
        raise NotImplementedError


class RegionalOperationPlanOnlyBaselineWorkflow(_StandaloneBaselineWorkflow):
    """A1: direct regional-plan rendering without multi-agent coordination."""

    system_id = "A1"

    def __init__(self, loader: Optional[FrozenBenchmarkLoader] = None) -> None:
        super().__init__(loader)
        self.calendar = RegionalCalendarOperationWindowAgent()
        self.trace = _BaselineTraceAgent("regional_operation_plan_only_baseline")

    def _run_scenario(self, scenario: FrozenBenchmarkScenario) -> BenchmarkRun:
        claims = list(self.calendar.run(scenario))
        plan_items = tuple(
            item
            for item in scenario.regional_operation_plan_items
            if item.get("plan_lane") in {
                "regional_calendar",
                "regional_nutrient_policy",
                "regional_crop_protection_policy",
            }
        )
        citations = tuple(sorted({item.get("source_document_id", "") for item in plan_items if item.get("source_document_id")}))
        claims.append(self.trace.describe(
            scenario,
            summary=f"A1 rendered {len(plan_items)} regional plan reference item(s) without agent coordination.",
            reasoning=(
                "This baseline reads only the frozen regional calendar, nutrient, and crop-protection plan "
                "cards. It does not retrieve RAG passages, run contextual agents, detect conflicts, or issue a farm action."
            ),
            source_row=plan_items[0] if plan_items else scenario.manifest,
            source_role="regional_plan_only_baseline_trace",
            metadata={"system_id": self.system_id, "plan_item_ids": tuple(item.get("plan_item_id", "") for item in plan_items)},
        ))
        lines = [
            f"Scenario: {scenario.identity.crop.title()} in {scenario.identity.district}, {scenario.identity.state} ({scenario.identity.decision_date}).",
            "Regional-plan-only baseline: no source-scoped farm operation is issued.",
        ]
        lines.extend(
            f"{item.get('plan_lane', 'regional_plan')}: {item.get('farmer_visible_text', '')}"
            for item in plan_items
        )
        lines.append(f"Evidence trace: {', '.join(citations) or 'no cited source identifier' }.")
        decision = BenchmarkDecision(
            scenario_id=scenario.identity.scenario_id,
            decision_status="regional_plan_only_context",
            direct_farm_action_issued=False,
            operation_text="No source-scoped farm operation is issued by the regional-plan-only baseline.",
            operation_status="regional_plan_reference_only",
            rationale="This comparison removes multi-agent context, retrieval, feasibility, and conflict coordination.",
            uncertainty_reasons=("evaluation_only_baseline_not_farmer_facing",),
            conflict_records=(),
            citations=citations,
            trace_claim_count=len(claims),
            conflict_resolution_records=(),
        )
        evaluation, final_claims = self._evaluation(scenario, decision, claims)
        return BenchmarkRun(
            scenario_id=scenario.identity.scenario_id,
            claims=final_claims,
            retrieved_passages=(),
            conflicts=(),
            decision=decision,
            farmer_message="\n".join(lines),
            evaluation=evaluation,
        )


class CentralizedSourceFilteredRAGBaselineWorkflow(_StandaloneBaselineWorkflow):
    """A2: one source-filtered retriever/planner without MAS decomposition."""

    system_id = "A2"

    def __init__(self, loader: Optional[FrozenBenchmarkLoader] = None) -> None:
        super().__init__(loader)
        self.rag = OfficialOperationsRAGAgent()
        self.trace = _BaselineTraceAgent("centralized_source_filtered_rag_baseline")

    def _run_scenario(self, scenario: FrozenBenchmarkScenario) -> BenchmarkRun:
        passages = self.rag.retrieve(scenario, question="", top_k=5)
        claims = list(self.rag.run(scenario, question="", top_k=5))
        citations = tuple(sorted({passage.source_document_id for passage in passages if passage.source_document_id}))
        claims.append(self.trace.describe(
            scenario,
            summary=f"A2 retrieved {len(passages)} already-admitted passage(s) in one centralized path.",
            reasoning=(
                "This baseline retains the same prefiltered source scope but removes independent context agents, "
                "feasibility, conflict detection, and provenance-aware coordination. Retrieval never authorizes a farm action."
            ),
            source_row=scenario.manifest,
            source_role="centralized_rag_baseline_trace",
            metadata={"system_id": self.system_id, "retrieved_source_ids": citations},
        ))
        decision = BenchmarkDecision(
            scenario_id=scenario.identity.scenario_id,
            decision_status="centralized_rag_context_only",
            direct_farm_action_issued=False,
            operation_text="No source-scoped farm operation is issued by the centralized RAG baseline.",
            operation_status="retrieval_context_only",
            rationale="A single retriever can surface only already-admitted passages; it does not replace MAS safety gates.",
            uncertainty_reasons=("evaluation_only_baseline_not_farmer_facing",),
            conflict_records=(),
            citations=citations,
            trace_claim_count=len(claims),
            conflict_resolution_records=(),
        )
        lines = [
            f"Scenario: {scenario.identity.crop.title()} in {scenario.identity.district}, {scenario.identity.state} ({scenario.identity.decision_date}).",
            "Centralized source-filtered RAG baseline: retrieval context only; no farm operation is issued.",
        ]
        lines.extend(
            f"Retrieved source — {passage.source_document_id}: {passage.text}"
            for passage in passages
        )
        lines.append(f"Evidence trace: {', '.join(citations) or 'no cited source identifier' }.")
        evaluation, final_claims = self._evaluation(scenario, decision, claims)
        return BenchmarkRun(
            scenario_id=scenario.identity.scenario_id,
            claims=final_claims,
            retrieved_passages=passages,
            conflicts=(),
            decision=decision,
            farmer_message="\n".join(lines),
            evaluation=evaluation,
        )


class AblatedBenchmarkMASWorkflow(BenchmarkMASWorkflow):
    """A3--A6: full MAS with one declared architectural component removed."""

    def __init__(
        self,
        system_id: str,
        loader: Optional[FrozenBenchmarkLoader] = None,
        *,
        bounded_llm: Optional[BenchmarkLLMClient] = None,
    ) -> None:
        if system_id not in {"A3", "A4", "A5", "A6"}:
            raise ValueError(f"Unsupported ablation system: {system_id}")
        self.system_id = system_id
        super().__init__(loader=loader, bounded_llm=bounded_llm)

    def _overlay_scenario(self, scenario: FrozenBenchmarkScenario) -> FrozenBenchmarkScenario:
        if self.system_id == "A3":
            return replace(
                scenario,
                retrievable_rag_chunks=(),
                retrievable_operation_passages=(),
                retrievable_postharvest_rag_passages=(),
            )
        if self.system_id == "A4":
            return replace(
                scenario,
                regional_operation_plan_summary=MappingProxyType({
                    "scenario_id": scenario.identity.scenario_id,
                    "plan_status": "withheld_for_evaluation_only_ablation",
                    "plan_summary": "Regional operation plans withheld for A4 evaluation-only ablation.",
                    "total_plan_item_count": "0",
                    "regional_reference_item_count": "0",
                    "conditional_source_quoted_operation_count": "0",
                    "conditional_action_ids": "",
                }),
                regional_operation_plan_items=(),
                action_records=(),
                action_bindings=(),
                retrievable_operation_passages=(),
            )
        return scenario

    def _load_node(self, state):
        payload = super()._load_node(state)
        return {**payload, "scenario": self._overlay_scenario(payload["scenario"])}

    def _gates_node(self, state):
        if self.system_id != "A5":
            return super()._gates_node(state)
        scenario = state["scenario"]
        claims = state.get("claims", ())
        for agent in (self.router, self.metadata_gate):
            gate_claims = tuple(agent.run(scenario))
            blocked = [claim for claim in gate_claims if claim.disposition == ClaimDisposition.BLOCKED]
            if blocked:
                reasons = "; ".join(claim.block_reason or claim.summary for claim in blocked)
                raise ScenarioIntegrityError(
                    f"Benchmark integrity gate {agent.name} blocked {scenario.identity.scenario_id}: {reasons}"
                )
            claims = self._append_claims(scenario, claims, gate_claims)
        return {"claims": claims}

    def _context_node(self, state):
        if self.system_id != "A4":
            return super()._context_node(state)
        scenario = state["scenario"]
        claims = state.get("claims", ())
        question = state.get("question", "")
        # Fertilizer and crop-protection context agents intentionally consume
        # regional plan items. A4 removes that enrichment, so excluding these
        # two dependent roles is the honest ablation rather than making them
        # process a fabricated empty policy row.
        retained_agents = tuple(
            agent
            for agent in self.context_agents
            if agent.name not in {"fertilizer_baseline_agent", "crop_protection_safety_agent"}
        )
        for agent in retained_agents:
            claims = self._append_claims(
                scenario,
                claims,
                self._bound_agent_claims(scenario, agent.name, agent.run(scenario), question=question),
            )
        return {"claims": claims}

    def _operations_node(self, state):
        if self.system_id not in {"A3", "A4"}:
            return super()._operations_node(state)
        scenario = state["scenario"]
        claims = state.get("claims", ())
        operation_agents = (
            (self.postharvest.name, self.postharvest.run(scenario)),
            (self.regulatory.name, self.regulatory.run(scenario)),
        )
        if self.system_id == "A3":
            operation_agents = ((self.calendar.name, self.calendar.run(scenario)), *operation_agents)
        for _agent_name, result in operation_agents:
            claims = self._append_claims(scenario, claims, result)
        return {"claims": claims, "retrieved_passages": ()}

    def _coordinator_node(self, state):
        if self.system_id != "A6":
            return super()._coordinator_node(state)
        scenario = state["scenario"]
        claims = state.get("claims", ())
        passages = state.get("retrieved_passages", ())
        # Preserve detection evidence in the trace but deliberately withhold
        # it from the coordinator. This isolates resolver contribution without
        # generating an unsafe action.
        decision = self.coordinator.coordinate(scenario, claims, passages, ())
        coordinator_claims = self._bound_agent_claims(
            scenario,
            self.coordinator.name,
            self.coordinator.run(scenario, claims=claims, passages=passages, conflicts=()),
            extra_facts=self._plan_priority_facts(scenario),
            question=state.get("question", ""),
        )
        claims = self._append_claims(scenario, claims, coordinator_claims)
        return {"claims": claims, "decision": decision}


def build_benchmark_system(
    system_id: str,
    *,
    loader: Optional[FrozenBenchmarkLoader] = None,
    bounded_llm: Optional[BenchmarkLLMClient] = None,
):
    """Return one protocol-named system without changing the proposed MAS."""
    if system_id == "A0":
        return BenchmarkMASWorkflow(loader=loader, bounded_llm=bounded_llm)
    if system_id == "A1":
        return RegionalOperationPlanOnlyBaselineWorkflow(loader=loader)
    if system_id == "A2":
        return CentralizedSourceFilteredRAGBaselineWorkflow(loader=loader)
    if system_id in {"A3", "A4", "A5", "A6"}:
        return AblatedBenchmarkMASWorkflow(system_id, loader=loader, bounded_llm=bounded_llm)
    raise ValueError(f"Unknown protocol system: {system_id}")
