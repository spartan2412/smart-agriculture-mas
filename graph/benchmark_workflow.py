"""Provenance-constrained LangGraph workflow for IndiaAgriAlignBench.

This graph is intentionally separate from ``graph/workflow.py``.  The legacy
workflow remains the project's Current MAS baseline; this path accepts only a
frozen benchmark ``scenario_id`` and never accepts caller-supplied weather,
soil, market, vision, or action dictionaries.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple, TypedDict

from langgraph.graph import END, StateGraph

from agents.benchmark.action_feasibility import ActionFeasibilityAgent
from agents.benchmark.base import (
    BenchmarkDecision,
    BenchmarkEvaluationRecord,
    ConflictRecord,
    RetrievedPassage,
    validate_claims,
)
from agents.benchmark.benchmark_evaluator import BenchmarkEvaluatorAgent
from agents.benchmark.conflict_detection import ConflictDetectionAgent
from agents.benchmark.crop_district_season_alignment_validator import CropDistrictSeasonAlignmentValidatorAgent
from agents.benchmark.crop_protection_safety import CropProtectionSafetyAgent
from agents.benchmark.evidence_provenance import EvidenceProvenanceAgent
from agents.benchmark.farmer_explanation_citation import FarmerExplanationCitationAgent
from agents.benchmark.fertilizer_baseline import FertilizerBaselineAgent
from agents.benchmark.market_evidence import MarketEvidenceAgent
from agents.benchmark.metadata_gate import MetadataGateAgent
from agents.benchmark.official_operations_rag import OfficialOperationsRAGAgent
from agents.benchmark.postharvest_storage_logistics import PostharvestStorageLogisticsAgent
from agents.benchmark.provenance_aware_coordinator import ProvenanceAwareCoordinatorAgent
from agents.benchmark.regional_calendar_operation_window import RegionalCalendarOperationWindowAgent
from agents.benchmark.regulatory_compliance import RegulatoryComplianceAgent
from agents.benchmark.satellite_ndvi_context import SatelliteNDVIContextAgent
from agents.benchmark.scenario_evidence_router import ScenarioEvidenceRouterAgent
from agents.benchmark.soil_context import SoilContextAgent
from agents.benchmark.uncertainty_abstention import UncertaintyAbstentionAgent
from agents.benchmark.vision_availability import VisionAvailabilityAgent
from agents.benchmark.weather_context import WeatherContextAgent
from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario, ScenarioIntegrityError
from data.evidence_schema import ClaimDisposition, DecisionDomain, TypedEvidenceClaim
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES, BoundedLLMResult, BenchmarkLLMClient


@dataclass(frozen=True)
class BenchmarkRun:
    """Complete, auditable result of one new MAS benchmark execution."""

    scenario_id: str
    claims: Tuple[TypedEvidenceClaim, ...]
    retrieved_passages: Tuple[RetrievedPassage, ...]
    conflicts: Tuple[ConflictRecord, ...]
    decision: BenchmarkDecision
    farmer_message: str
    evaluation: BenchmarkEvaluationRecord


class BenchmarkAgentState(TypedDict, total=False):
    scenario_id: str
    question: str
    verify_raw_hashes: bool
    scenario: FrozenBenchmarkScenario
    claims: Tuple[TypedEvidenceClaim, ...]
    retrieved_passages: Tuple[RetrievedPassage, ...]
    conflicts: Tuple[ConflictRecord, ...]
    decision: BenchmarkDecision
    farmer_message: str
    evaluation: BenchmarkEvaluationRecord
    result: BenchmarkRun


class BenchmarkMASWorkflow:
    """Orchestrates all 21 benchmark roles without modifying the legacy graph."""

    def __init__(
        self,
        loader: Optional[FrozenBenchmarkLoader] = None,
        *,
        bounded_llm: Optional[BenchmarkLLMClient] = None,
    ):
        self.loader = loader or FrozenBenchmarkLoader()
        self.bounded_llm = bounded_llm or BenchmarkLLMClient()

        # Deterministic gate agents (4).
        self.router = ScenarioEvidenceRouterAgent()
        self.alignment = CropDistrictSeasonAlignmentValidatorAgent()
        self.metadata_gate = MetadataGateAgent()
        self.provenance = EvidenceProvenanceAgent()

        # Independently runnable contextual agents (7).
        self.context_agents = (
            WeatherContextAgent(),
            SoilContextAgent(),
            SatelliteNDVIContextAgent(),
            MarketEvidenceAgent(),
            FertilizerBaselineAgent(),
            CropProtectionSafetyAgent(),
            VisionAvailabilityAgent(),
        )

        # Calendar/RAG/postharvest/regulatory/feasibility path (5).
        self.calendar = RegionalCalendarOperationWindowAgent()
        self.official_rag = OfficialOperationsRAGAgent()
        self.postharvest = PostharvestStorageLogisticsAgent()
        self.regulatory = RegulatoryComplianceAgent()
        self.feasibility = ActionFeasibilityAgent()

        # Safety/coordinator path (3).
        self.uncertainty = UncertaintyAbstentionAgent()
        self.conflicts = ConflictDetectionAgent()
        self.coordinator = ProvenanceAwareCoordinatorAgent()

        # Explanation/evaluation path (2).
        self.explanation = FarmerExplanationCitationAgent()
        self.evaluator = BenchmarkEvaluatorAgent()
        self._bounded_agents_by_name = {
            agent.name: agent
            for agent in (
                *self.context_agents,
                self.official_rag,
                self.coordinator,
                self.explanation,
            )
            if agent.name in BOUND_LLM_AGENT_NAMES
        }
        if set(self._bounded_agents_by_name) != set(BOUND_LLM_AGENT_NAMES):
            raise RuntimeError("bounded LLM agent registry does not match configured roles")
        self.graph = self._build_graph()

    def _bound_agent_claims(
        self,
        scenario: FrozenBenchmarkScenario,
        agent_name: str,
        claims: Sequence[TypedEvidenceClaim],
        *,
        extra_facts: Sequence[Mapping[str, str]] = (),
        question: str = "",
    ) -> Tuple[TypedEvidenceClaim, ...]:
        """Attach one bounded-LLM selection trace without changing claim facts.

        The LLM receives only identifiers and text already present in the
        validated scenario/claim trace. Its response can select allowed IDs but
        cannot add a fact, citation, action, condition, or gate outcome.
        """
        if agent_name not in BOUND_LLM_AGENT_NAMES:
            return tuple(claims)
        result = self._bounded_selection(
            scenario,
            agent_name,
            claims,
            extra_facts=extra_facts,
            question=question,
        )
        return self._annotate_bounded_selection(claims, result)

    def _bounded_selection(
        self,
        scenario: FrozenBenchmarkScenario,
        agent_name: str,
        claims: Sequence[TypedEvidenceClaim],
        *,
        extra_facts: Sequence[Mapping[str, str]] = (),
        question: str = "",
    ) -> BoundedLLMResult:
        """Make one selection over immutable claims and approved extra facts."""
        if agent_name not in BOUND_LLM_AGENT_NAMES:
            raise ValueError(f"{agent_name} is not an enabled bounded-LLM role")
        facts: list[dict[str, str]] = []
        for index, claim in enumerate(claims, start=1):
            facts.append(
                {
                    "fact_id": f"claim_{index}",
                    "text": (
                        f"domain={claim.decision_domain.value}; disposition={claim.disposition.value}; "
                        f"allowed_use={claim.allowed_use.value}; summary={claim.summary}; "
                        f"citation={claim.source.source_document_id or 'none'}"
                    ),
                }
            )
        seen_ids = {fact["fact_id"] for fact in facts}
        for fact in extra_facts:
            fact_id, text = str(fact.get("fact_id", "")).strip(), str(fact.get("text", "")).strip()
            if fact_id and text and fact_id not in seen_ids:
                facts.append({"fact_id": fact_id, "text": text})
                seen_ids.add(fact_id)
        role_instruction = self._bounded_agents_by_name[agent_name].llm_selection_instruction
        return self.bounded_llm.select_fact_ids(
            agent_name=agent_name,
            scenario_id=scenario.identity.scenario_id,
            facts=facts,
            role_instruction=role_instruction,
            scenario_context={
                "crop": scenario.identity.crop,
                "state": scenario.identity.state,
                "district": scenario.identity.district,
                "season": scenario.identity.season,
                "decision_date": scenario.identity.decision_date,
                "decision_window_utc": scenario.identity.decision_window_utc,
                "geometry_scope": scenario.identity.geometry_scope,
            },
            farmer_question=question,
        )

    @staticmethod
    def _annotate_bounded_selection(
        claims: Sequence[TypedEvidenceClaim],
        result: BoundedLLMResult,
    ) -> Tuple[TypedEvidenceClaim, ...]:
        annotated: list[TypedEvidenceClaim] = []
        for claim in claims:
            metadata = dict(claim.metadata)
            metadata["bounded_llm"] = result.as_metadata()
            annotated.append(claim.model_copy(update={"metadata": metadata}))
        return tuple(annotated)

    @staticmethod
    def _reorder_passages(
        passages: Sequence[RetrievedPassage],
        selected_fact_ids: Sequence[str],
    ) -> Tuple[RetrievedPassage, ...]:
        """Re-rank only passages admitted by deterministic retrieval."""
        by_id = {f"passage_{index}": passage for index, passage in enumerate(passages, start=1)}
        selected = [by_id[item] for item in selected_fact_ids if item in by_id]
        selected_ids = {item for item in selected_fact_ids if item in by_id}
        return tuple(selected + [
            passage
            for index, passage in enumerate(passages, start=1)
            if f"passage_{index}" not in selected_ids
        ])

    @staticmethod
    def _plan_priority_facts(
        scenario: FrozenBenchmarkScenario,
    ) -> Tuple[Mapping[str, str], ...]:
        """Expose only frozen farmer-visible plan cards for coordinator ordering."""
        supported_lanes = {
            "regional_calendar",
            "regional_nutrient_policy",
            "regional_crop_protection_policy",
        }
        regional_cards = tuple(
            {
                "fact_id": f"plan:{item.get('plan_item_id', '')}",
                "text": (
                    f"lane={item.get('plan_lane', '')}; "
                    f"source={item.get('source_document_id', '')}; "
                    f"text={item.get('farmer_visible_text', '')}"
                ),
            }
            for item in scenario.regional_operation_plan_items
            if item.get("plan_lane") in supported_lanes and item.get("plan_item_id")
        )
        postharvest_cards = tuple(
            {
                "fact_id": f"postharvest:{item.get('plan_item_id', '')}",
                "text": (
                    f"lane={item.get('plan_lane', '')}; "
                    f"source={item.get('source_document_id', '')}; "
                    f"condition={item.get('missing_observation', '')}; "
                    f"text={item.get('operation_text', '')}"
                ),
            }
            for item in scenario.postharvest_plan_items
            if item.get("plan_item_id")
        )
        return regional_cards + postharvest_cards

    @staticmethod
    def _presentation_facts(
        claims: Sequence[TypedEvidenceClaim],
    ) -> Tuple[Mapping[str, str], ...]:
        """Expose optional, approved context cards for LLM presentation order."""
        domains = {
            DecisionDomain.WEATHER_CONTEXT: "context:weather",
            DecisionDomain.SOIL_CONTEXT: "context:soil",
            DecisionDomain.SATELLITE_CONTEXT: "context:satellite",
            DecisionDomain.MARKET_CONTEXT: "context:market",
        }
        facts: list[Mapping[str, str]] = []
        for claim in claims:
            fact_id = domains.get(claim.decision_domain)
            if not fact_id or claim.disposition != ClaimDisposition.CONTEXT:
                continue
            # A context role that accepted a bounded selection but did not
            # select its own claim is not promoted to the optional farmer
            # layer. Disabled or rejected calls preserve the canonical fallback.
            bounded = claim.metadata.get("bounded_llm", {})
            if (
                claim.agent_name in BOUND_LLM_AGENT_NAMES
                and bounded.get("status") == "accepted"
                and "claim_1" not in bounded.get("selected_fact_ids", ())
            ):
                continue
            facts.append({"fact_id": fact_id, "text": claim.summary})
        return tuple(facts)

    @staticmethod
    def _append_claims(
        scenario: FrozenBenchmarkScenario,
        current: Sequence[TypedEvidenceClaim],
        additions: Sequence[TypedEvidenceClaim],
    ) -> Tuple[TypedEvidenceClaim, ...]:
        return validate_claims(scenario, tuple(current) + tuple(additions))

    def _load_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = self.loader.load(
            state["scenario_id"], verify_raw_hashes=state.get("verify_raw_hashes", True)
        )
        return {"scenario": scenario, "claims": ()}

    def _gates_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = state["scenario"]
        claims = state.get("claims", ())
        for agent in (self.router, self.alignment, self.metadata_gate, self.provenance):
            gate_claims = validate_claims(scenario, agent.run(scenario))
            blocked = [
                claim
                for claim in gate_claims
                if claim.disposition == ClaimDisposition.BLOCKED
            ]
            if blocked:
                reasons = "; ".join(claim.block_reason or claim.summary for claim in blocked)
                raise ScenarioIntegrityError(
                    f"Benchmark integrity gate {agent.name} blocked {scenario.identity.scenario_id}: {reasons}"
                )
            claims = self._append_claims(scenario, claims, gate_claims)
        return {"claims": claims}

    def _context_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = state["scenario"]
        claims = state.get("claims", ())
        question = state.get("question", "")
        # These roles share no mutable state.  Map preserves agent order when
        # collecting results, keeping benchmark traces reproducible.
        with ThreadPoolExecutor(max_workers=len(self.context_agents)) as executor:
            agent_results = tuple(
                executor.map(lambda agent: (agent, agent.run(scenario)), self.context_agents)
            )
        for agent, result in agent_results:
            claims = self._append_claims(
                scenario,
                claims,
                self._bound_agent_claims(
                    scenario,
                    agent.name,
                    result,
                    question=question,
                ),
            )
        return {"claims": claims}

    def _operations_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = state["scenario"]
        claims = state.get("claims", ())
        question = state.get("question", "")
        passages = self.official_rag.retrieve(scenario, question=question, top_k=5)
        rag_claims = self._bound_agent_claims(
            scenario,
            self.official_rag.name,
            self.official_rag.run(scenario, question=question, top_k=5),
            extra_facts=tuple(
                {
                    "fact_id": f"passage_{index}",
                    "text": (
                        f"source={passage.source_document_id}; locator={passage.locator}; "
                        f"layer={passage.corpus_layer}; text={passage.text}"
                    ),
                }
                for index, passage in enumerate(passages, start=1)
            ),
            question=question,
        )
        rag_selection = rag_claims[0].metadata["bounded_llm"]["selected_fact_ids"]
        passages = self._reorder_passages(passages, rag_selection)
        operation_results = (
            (self.calendar.name, self.calendar.run(scenario)),
            (self.official_rag.name, rag_claims),
            (self.postharvest.name, self.postharvest.run(scenario)),
            (self.regulatory.name, self.regulatory.run(scenario)),
            (self.feasibility.name, self.feasibility.run(scenario)),
        )
        for _agent_name, result in operation_results:
            claims = self._append_claims(scenario, claims, result)
        return {"claims": claims, "retrieved_passages": passages}

    def _safety_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = state["scenario"]
        claims = state.get("claims", ())
        claims = self._append_claims(scenario, claims, self.uncertainty.run(scenario, claims=claims))
        conflicts = self.conflicts.detect(scenario, claims)
        claims = self._append_claims(scenario, claims, self.conflicts.run(scenario, claims=claims))
        return {"claims": claims, "conflicts": conflicts}

    def _coordinator_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = state["scenario"]
        claims = state.get("claims", ())
        passages = state.get("retrieved_passages", ())
        conflicts = state.get("conflicts", ())
        decision = self.coordinator.coordinate(scenario, claims, passages, conflicts)
        coordinator_claims = self._bound_agent_claims(
            scenario,
            self.coordinator.name,
            self.coordinator.run(scenario, claims=claims, passages=passages, conflicts=conflicts),
            extra_facts=(
                {
                    "fact_id": "decision:operation",
                    "text": (
                        f"status={decision.decision_status}; operation_status={decision.operation_status}; "
                        f"direct_farm_action_issued={decision.direct_farm_action_issued}; "
                        f"citations={','.join(decision.citations)}"
                    ),
                },
                *self._plan_priority_facts(scenario),
            ),
            question=state.get("question", ""),
        )
        claims = self._append_claims(scenario, claims, coordinator_claims)
        return {"claims": claims, "decision": decision}

    def _output_node(self, state: BenchmarkAgentState) -> dict[str, Any]:
        scenario = state["scenario"]
        claims = state.get("claims", ())
        decision = state["decision"]
        coordinator_claim = next(
            claim for claim in reversed(claims)
            if claim.agent_name == self.coordinator.name
        )
        coordinator_selection = tuple(
            coordinator_claim.metadata.get("bounded_llm", {}).get("selected_fact_ids", ())
        )
        presentation_result = self._bounded_selection(
            scenario,
            self.explanation.name,
            (),
            extra_facts=self._presentation_facts(claims),
            question=state.get("question", ""),
        )
        use_presentation_selection = presentation_result.status == "accepted"
        message = self.explanation.render(
            scenario,
            decision,
            claims,
            retrieved_passages=state.get("retrieved_passages", ()),
            question=state.get("question", ""),
            coordinator_selected_fact_ids=coordinator_selection,
            presentation_selected_fact_ids=presentation_result.selected_fact_ids,
            use_presentation_selection=use_presentation_selection,
        )
        explanation_claims = self._annotate_bounded_selection(
            self.explanation.run(
                scenario,
                decision=decision,
                claims=claims,
                message=message,
                retrieved_passages=state.get("retrieved_passages", ()),
                question=state.get("question", ""),
                coordinator_selected_fact_ids=coordinator_selection,
                presentation_selected_fact_ids=presentation_result.selected_fact_ids,
                use_presentation_selection=use_presentation_selection,
            ),
            presentation_result,
        )
        claims = self._append_claims(scenario, claims, explanation_claims)
        evaluation = self.evaluator.evaluate(scenario, decision, claims)
        claims = self._append_claims(
            scenario,
            claims,
            self.evaluator.run(scenario, decision=decision, claims=claims),
        )
        message = str(explanation_claims[0].metadata["farmer_message"])
        result = BenchmarkRun(
            scenario_id=scenario.identity.scenario_id,
            claims=claims,
            retrieved_passages=tuple(state.get("retrieved_passages", ())),
            conflicts=tuple(state.get("conflicts", ())),
            decision=decision,
            farmer_message=message,
            evaluation=evaluation,
        )
        return {"claims": claims, "evaluation": evaluation, "farmer_message": message, "result": result}

    def _build_graph(self):
        graph = StateGraph(BenchmarkAgentState)
        graph.add_node("load_frozen_scenario", self._load_node)
        graph.add_node("run_integrity_gates", self._gates_node)
        graph.add_node("run_context_agents", self._context_node)
        graph.add_node("run_operations_path", self._operations_node)
        graph.add_node("run_safety_and_conflict_path", self._safety_node)
        graph.add_node("coordinate_provenance", self._coordinator_node)
        graph.add_node("render_and_evaluate", self._output_node)
        graph.set_entry_point("load_frozen_scenario")
        graph.add_edge("load_frozen_scenario", "run_integrity_gates")
        graph.add_edge("run_integrity_gates", "run_context_agents")
        graph.add_edge("run_context_agents", "run_operations_path")
        graph.add_edge("run_operations_path", "run_safety_and_conflict_path")
        graph.add_edge("run_safety_and_conflict_path", "coordinate_provenance")
        graph.add_edge("coordinate_provenance", "render_and_evaluate")
        graph.add_edge("render_and_evaluate", END)
        return graph.compile()

    def run(
        self,
        scenario_id: str,
        *,
        question: str = "",
        verify_raw_hashes: bool = True,
    ) -> BenchmarkRun:
        """Execute every benchmark role for one source-gated scenario."""
        state = self.graph.invoke(
            {
                "scenario_id": scenario_id,
                "question": question,
                "verify_raw_hashes": verify_raw_hashes,
            }
        )
        return state["result"]


def build_benchmark_workflow(
    loader: Optional[FrozenBenchmarkLoader] = None,
    *,
    bounded_llm: Optional[BenchmarkLLMClient] = None,
) -> BenchmarkMASWorkflow:
    """Factory mirroring the legacy ``build_workflow`` entry point without altering it."""
    return BenchmarkMASWorkflow(loader=loader, bounded_llm=bounded_llm)
