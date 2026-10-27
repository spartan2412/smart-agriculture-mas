"""Regression tests for the separately versioned v5 bounded selector."""
from __future__ import annotations

import json
from typing import Any

from agents.benchmark.fertilizer_baseline import FertilizerBaselineAgent
from agents.benchmark.weather_context import WeatherContextAgent
from data.benchmark_loader import FrozenBenchmarkLoader
from graph.benchmark_workflow import BenchmarkMASWorkflow
from graph.benchmark_workflow_v5 import BenchmarkMASWorkflowV5
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
    V5CandidatePackager,
    V5_ROLE_INSTRUCTIONS,
)
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES


RICE_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"


class RecordingV5Client:
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.response = response

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt, **kwargs})
        if self.response is not None:
            return dict(self.response)
        request = json.loads(user_prompt)
        return {"selected_fact_ids": [request["allowed_facts"][0]["fact_id"]], "focus": "context"}


def test_v5_contract_covers_every_approved_bounded_role():
    packager = V5CandidatePackager()
    assert set(V5_ROLE_INSTRUCTIONS) == set(BOUND_LLM_AGENT_NAMES)
    assert packager.policy_for("official_operations_rag_agent").maximum_selected_fact_ids == 1
    assert packager.policy_for("provenance_aware_coordinator_agent").maximum_selected_fact_ids == 1
    assert packager.policy_for("fertilizer_baseline_agent").maximum_selected_fact_ids == 2


def test_v5_candidate_packaging_exposes_boundaries_and_removes_irrelevant_fertilizer_cards():
    loader = FrozenBenchmarkLoader()
    scenario = loader.load(RICE_ANCHOR, verify_raw_hashes=True)
    claims = FertilizerBaselineAgent().run(scenario)
    extras = BenchmarkMASWorkflow._plan_priority_facts(scenario)
    packaged = V5CandidatePackager().package(
        agent_name="fertilizer_baseline_agent",
        claims=claims,
        extra_facts=extras,
        question="Why is a field-specific fertilizer dose not issued?",
    )
    ids = [fact["fact_id"] for fact in packaged.facts]
    assert ids[:2] == ["claim_2", "claim_1"]
    assert all("regional_calendar" not in fact["text"] for fact in packaged.facts)
    assert all("regional_crop_protection_policy" not in fact["text"] for fact in packaged.facts)
    assert "allowed_use=unavailable" in packaged.facts[0]["text"]
    assert "does_not_establish=" in packaged.facts[0]["text"]


def test_v5_weather_prompt_requires_sufficiency_and_can_return_empty():
    scenario = FrozenBenchmarkLoader().load(RICE_ANCHOR, verify_raw_hashes=True)
    packaged = V5CandidatePackager().package(
        agent_name="weather_context_agent",
        claims=WeatherContextAgent().run(scenario),
        extra_facts=(),
        question="Can this evidence authorize irrigation now?",
    )
    client = RecordingV5Client({"selected_fact_ids": [], "focus": "restriction"})
    selector = BenchmarkLLMClientV5(client=client, enabled=True, required=True)
    result = selector.select_fact_ids(
        agent_name="weather_context_agent",
        scenario_id=RICE_ANCHOR,
        facts=packaged.facts,
        role_instruction=V5_ROLE_INSTRUCTIONS["weather_context_agent"],
        selection_policy=packaged.policy,
        farmer_question="Can this evidence authorize irrigation now?",
    )
    assert result.status == "accepted"
    assert result.selected_fact_ids == ()
    request = json.loads(client.calls[0]["user_prompt"])
    assert request["selection_contract_version"] == V5_SELECTION_CONTRACT_VERSION
    assert request["candidate_packaging_version"] == CANDIDATE_PACKAGING_VERSION_V5
    assert "SUFFICIENCY-FIRST RULE" in client.calls[0]["system_prompt"]
    assert "ACTION-AUTHORIZATION CHECK" in client.calls[0]["system_prompt"]
    assert "allowed_use=context_only" in request["allowed_facts"][0]["text"]


def test_v5_rag_and_coordinator_packages_enforce_one_primary_candidate():
    scenario = FrozenBenchmarkLoader().load(RICE_ANCHOR, verify_raw_hashes=True)
    workflow = BenchmarkMASWorkflow()
    question = "Which exact source-scoped rice operation should be prioritized?"
    passages = workflow.official_rag.retrieve(scenario, question=question, top_k=5)
    rag = V5CandidatePackager().package(
        agent_name="official_operations_rag_agent",
        claims=workflow.official_rag.run(scenario, question=question, top_k=5),
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
    assert rag.policy.maximum_selected_fact_ids == 1
    assert "candidate_kind=source_scoped_operation" in rag.facts[0]["text"]

    coordinator = V5CandidatePackager().package(
        agent_name="provenance_aware_coordinator_agent",
        claims=(),
        extra_facts=(
            {"fact_id": "decision:operation", "text": "status=conditional"},
            *workflow._plan_priority_facts(scenario),
        ),
        question="Which seasonal calendar card should be prioritized?",
    )
    assert coordinator.policy.maximum_selected_fact_ids == 1
    assert all(fact["fact_id"].startswith("plan:") for fact in coordinator.facts)

    double = RecordingV5Client(
        {"selected_fact_ids": [rag.facts[0]["fact_id"], rag.facts[1]["fact_id"]], "focus": "source"}
    )
    result = BenchmarkLLMClientV5(client=double, enabled=True, required=True).select_fact_ids(
        agent_name="official_operations_rag_agent",
        scenario_id=RICE_ANCHOR,
        facts=rag.facts,
        role_instruction=V5_ROLE_INSTRUCTIONS["official_operations_rag_agent"],
        selection_policy=rag.policy,
        farmer_question=question,
    )
    assert result.status == "rejected_invalid_selection"
    assert result.selected_fact_ids == ()


def test_v5_rejects_an_unknown_id_without_changing_the_deterministic_decision():
    double = RecordingV5Client({"selected_fact_ids": ["fabricated_fact"], "focus": "source"})
    workflow = BenchmarkMASWorkflowV5(
        bounded_llm=BenchmarkLLMClientV5(client=double, enabled=True, required=True)
    )
    deterministic = BenchmarkMASWorkflow().run(RICE_ANCHOR, verify_raw_hashes=True)
    bounded = workflow.run(RICE_ANCHOR, verify_raw_hashes=True)
    assert bounded.decision == deterministic.decision
    assert bounded.farmer_message == deterministic.farmer_message
    assert len(double.calls) == 8
    assert {
        claim.metadata["bounded_llm"]["status"]
        for claim in bounded.claims
        if claim.agent_name in BOUND_LLM_AGENT_NAMES
    } == {"rejected_invalid_selection"}


def test_v5_workflow_records_its_separate_prompt_contract_without_mutating_v4():
    double = RecordingV5Client()
    selector = BenchmarkLLMClientV5(client=double, enabled=True, required=True)
    run = BenchmarkMASWorkflowV5(bounded_llm=selector).run(RICE_ANCHOR, verify_raw_hashes=True)
    assert len(double.calls) == 8
    assert selector.invocation_count == 8
    metadata = [
        claim.metadata["bounded_llm"]
        for claim in run.claims
        if claim.agent_name in BOUND_LLM_AGENT_NAMES
    ]
    assert {item["prompt_template_version"] for item in metadata} == {PROMPT_TEMPLATE_VERSION_V5}
    assert {item["selection_contract_version"] for item in metadata} == {V5_SELECTION_CONTRACT_VERSION}
    assert all(item["selection_is_safety_non_authoritative"] for item in metadata)
