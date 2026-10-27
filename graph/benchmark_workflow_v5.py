"""V5 bounded-selection workflow that preserves the frozen v4 workflow path."""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario
from data.evidence_schema import TypedEvidenceClaim
from graph.benchmark_workflow import BenchmarkMASWorkflow
from llm.bounded_selection_v5 import (
    BenchmarkLLMClientV5,
    PackagedV5Candidates,
    V5CandidatePackager,
    V5_ROLE_INSTRUCTIONS,
)
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES


class BenchmarkMASWorkflowV5(BenchmarkMASWorkflow):
    """Run unchanged deterministic MAS agents with the separate v5 selector.

    Only ``_bounded_selection`` differs from v4. All gate, operation,
    retrieval-admission, conflict, coordinator-decision, renderer, and oracle
    agents are inherited without modification.
    """

    def __init__(
        self,
        loader: Optional[FrozenBenchmarkLoader] = None,
        *,
        bounded_llm: Optional[BenchmarkLLMClientV5] = None,
        candidate_packager: Optional[V5CandidatePackager] = None,
    ) -> None:
        self.v5_candidate_packager = candidate_packager or V5CandidatePackager()
        super().__init__(loader=loader, bounded_llm=bounded_llm or BenchmarkLLMClientV5())
        if set(V5_ROLE_INSTRUCTIONS) != set(BOUND_LLM_AGENT_NAMES):
            raise RuntimeError("v5 role instructions do not match the approved bounded-LLM registry")

    def _bounded_selection(
        self,
        scenario: FrozenBenchmarkScenario,
        agent_name: str,
        claims: Sequence[TypedEvidenceClaim],
        *,
        extra_facts: Sequence[Mapping[str, str]] = (),
        question: str = "",
    ):
        packaged: PackagedV5Candidates = self.v5_candidate_packager.package(
            agent_name=agent_name,
            claims=claims,
            extra_facts=extra_facts,
            question=question,
        )
        return self.bounded_llm.select_fact_ids(
            agent_name=agent_name,
            scenario_id=scenario.identity.scenario_id,
            facts=packaged.facts,
            role_instruction=V5_ROLE_INSTRUCTIONS[agent_name],
            selection_policy=packaged.policy,
            request_sufficiency=packaged.request_sufficiency,
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


def build_benchmark_workflow_v5(
    loader: Optional[FrozenBenchmarkLoader] = None,
    *,
    bounded_llm: Optional[BenchmarkLLMClientV5] = None,
) -> BenchmarkMASWorkflowV5:
    """Construct the separately versioned v5 bounded-selection workflow."""
    return BenchmarkMASWorkflowV5(loader=loader, bounded_llm=bounded_llm)
