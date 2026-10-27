"""Build, validate, and run the frozen bounded-LLM relevance benchmark.

The benchmark evaluates only the eight optional bounded-LLM selection roles.
It supplies source-backed, scenario-scoped candidate fact IDs and asks whether
the model selects the pre-labelled relevant IDs without introducing anything
outside the immutable candidate set.  It is deliberately separate from the
18-check structural oracle: the oracle evaluates a completed MAS trace,
whereas this module measures bounded evidence-selection quality.

No record in this module is farm-outcome ground truth.  The labels are derived
from the already-admitted source facts, plan items, operation passages, and
role-specific safety restrictions in the frozen benchmark.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping, Optional, Sequence

from agents.benchmark.base import RetrievedPassage
from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario
from data.evidence_schema import ClaimDisposition, TypedEvidenceClaim
from graph.benchmark_workflow import BenchmarkMASWorkflow, BenchmarkRun
from llm.benchmark_llm_client import (
    BOUND_LLM_AGENT_NAMES,
    PROMPT_TEMPLATE_VERSION,
    BoundedLLMResult,
    BenchmarkLLMClient,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_DIR = PROJECT_ROOT / "data" / "llm_relevance_benchmark"
QUESTIONS_FILENAME = "relevance_questions.jsonl"
MANIFEST_FILENAME = "manifest.json"
BENCHMARK_VERSION = "1.0"
QUESTIONS_PER_ROLE = 12
MAX_SELECTED_FACTS = 3

# The 96-question v4 relevance set is retained only as a historical benchmark
# and as a source of prior IDs for v5 disjointness checks.  Its whole-module
# snapshot includes the farmer renderer and its post-selection workflow call
# even though rendering occurs after relevance selection. Farmer-output v2.2
# changes only that deterministic rendering call; its active v5.1 selector
# contract, prompts, candidate packager, and held-out runtime hashes remain
# separately frozen. All other v4 source artifacts continue to fail closed.
_HISTORICAL_PRESENTATION_ONLY_ARTIFACTS = frozenset({
    "agents/benchmark/farmer_explanation_citation.py",
    "graph/benchmark_workflow.py",
})

# Two immutable anchor contexts per focused crop make every bounded role face
# the same six-crop, multi-district population.  These scenario IDs are a
# frozen evaluation subset, not new agricultural evidence.
CANONICAL_SCENARIO_IDS: tuple[str, ...] = (
    "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130",
    "ANCHOR_PF_PB_PATIALA_RICE_KHARIF_20251130",
    "ANCHOR_PF_PB_LUDHIANA_WHEAT_RABI_20260430",
    "ANCHOR_PF_PB_PATIALA_WHEAT_RABI_20260430",
    "ANCHOR_PF_TN_COIMBATORE_MAIZE_RABI_20260331",
    "ANCHOR_PF_TN_ERODE_MAIZE_RABI_20260331",
    "ANCHOR_PF_MH_JALNA_CHICKPEA_RABI_20260331",
    "ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331",
    "ANCHOR_PF_MP_INDORE_SOYBEAN_KHARIF_20251031",
    "ANCHOR_PF_MP_UJJAIN_SOYBEAN_KHARIF_20251031",
    "ANCHOR_PF_TN_KRISHNAGIRI_TOMATO_RABI_20251231",
    "ANCHOR_PF_TN_DHARMAPURI_TOMATO_RABI_20251231",
)

ROLE_CODES: Mapping[str, str] = {
    "weather_context_agent": "WEATHER",
    "soil_context_agent": "SOIL",
    "satellite_ndvi_context_agent": "SATELLITE",
    "market_evidence_agent": "MARKET",
    "fertilizer_baseline_agent": "FERTILIZER",
    "official_operations_rag_agent": "RAG",
    "provenance_aware_coordinator_agent": "COORDINATOR",
    "farmer_explanation_citation_agent": "EXPLANATION",
}

CONTEXT_AGENT_NAMES: tuple[str, ...] = (
    "weather_context_agent",
    "soil_context_agent",
    "satellite_ndvi_context_agent",
    "market_evidence_agent",
)

CONTEXT_FACT_IDS: Mapping[str, str] = {
    "weather_context_agent": "context:weather",
    "soil_context_agent": "context:soil",
    "satellite_ndvi_context_agent": "context:satellite",
    "market_evidence_agent": "context:market",
}

SOURCE_ARTIFACT_PATHS: tuple[str, ...] = (
    "data/registry/final_study_sites.csv",
    "data/scenarios/manifests/scenario_manifest.csv",
    "data/scenarios/processed/scenario_features.csv",
    "data/scenarios/evidence/scenario_evidence_status.csv",
    "data/scenarios/enriched/mas_enrichment_contract.csv",
    "data/scenarios/enriched/nasa_power_water_context_features.csv",
    "data/scenarios/enriched/sentinel_ndvi_context_features.csv",
    "data/scenarios/enriched/sentinel_ndvi_timeseries_features.csv",
    "data/scenarios/enriched/agmarknet_embedded_market_context_features.csv",
    "data/scenarios/enriched/official_rag_corpus_all_chunks.csv",
    "data/scenarios/enriched/scenario_official_rag_scope_all.csv",
    "data/scenarios/enriched/official_action_records_all.csv",
    "data/scenarios/enriched/scenario_official_action_bindings_all.csv",
    "data/scenarios/enriched/regional_operation_plan_items.csv",
    "data/scenarios/enriched/scenario_postharvest_plan_items.csv",
    "data/scenarios/enriched/scenario_postharvest_rag_scope.csv",
    "data/benchmark_loader.py",
    "graph/benchmark_workflow.py",
    "llm/benchmark_llm_client.py",
    "agents/benchmark/weather_context.py",
    "agents/benchmark/soil_context.py",
    "agents/benchmark/satellite_ndvi_context.py",
    "agents/benchmark/market_evidence.py",
    "agents/benchmark/fertilizer_baseline.py",
    "agents/benchmark/official_operations_rag.py",
    "agents/benchmark/provenance_aware_coordinator.py",
    "agents/benchmark/farmer_explanation_citation.py",
)


class RelevanceBenchmarkError(RuntimeError):
    """Raised when a relevance benchmark artifact is malformed or unsafe."""


@dataclass(frozen=True)
class FrozenRelevanceBenchmark:
    """Validated source-derived question set and its immutable manifest."""

    benchmark_dir: Path
    manifest: Mapping[str, Any]
    questions: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class RelevanceRunSummary:
    """Small summary of one persisted bounded-LLM relevance run."""

    output_dir: Path
    question_count: int
    accepted_selection_count: int
    invalid_structured_output_count: int
    fallback_count: int


def _compact(value: Any, *, limit: int = 900) -> str:
    normalized = " ".join(str(value or "").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "…"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _git_metadata(project_root: Path) -> Mapping[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True, stderr=subprocess.STDOUT
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=project_root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RelevanceBenchmarkError(f"Unable to inspect Git state: {exc}") from exc
    return {"commit": commit, "clean": str(not status).lower()}


def _peak_memory_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _scenario_context(scenario: FrozenBenchmarkScenario) -> Mapping[str, str]:
    identity = scenario.identity
    return {
        "crop": identity.crop,
        "state": identity.state,
        "district": identity.district,
        "season": identity.season,
        "decision_date": identity.decision_date,
        "decision_window_utc": identity.decision_window_utc,
        "geometry_scope": identity.geometry_scope,
    }


def _scenario_description(scenario: FrozenBenchmarkScenario) -> str:
    identity = scenario.identity
    return (
        f"{identity.crop.title()} in {identity.district}, {identity.state}, during the "
        f"{identity.season} decision window ending {identity.decision_date}"
    )


def _source_ids(*values: Any) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value or "").strip()})


def _conditions(*values: Any) -> list[str]:
    return list(dict.fromkeys(_compact(value, limit=500) for value in values if _compact(value, limit=500)))


def _claim_fact(
    claim: TypedEvidenceClaim,
    *,
    fact_id: str,
    plan_or_operation_ids: Sequence[str] = (),
) -> Mapping[str, Any]:
    """Convert one immutable typed claim into one benchmark candidate fact."""
    source_id = claim.source.source_document_id or "FROZEN_SCENARIO_MANIFEST"
    return {
        "fact_id": fact_id,
        "fact_kind": "typed_claim",
        "text": (
            f"domain={claim.decision_domain.value}; disposition={claim.disposition.value}; "
            f"allowed_use={claim.allowed_use.value}; summary={claim.summary}; citation={source_id}"
        ),
        "source_document_ids": _source_ids(source_id),
        "source_locators": _source_ids(claim.source.locator),
        "plan_or_operation_ids": _source_ids(*plan_or_operation_ids),
        "conditions": _conditions(claim.reasoning, claim.block_reason or ""),
    }


def _plan_fact(item: Mapping[str, Any], *, prefix: str = "plan") -> Mapping[str, Any]:
    plan_item_id = str(item.get("plan_item_id", "")).strip()
    if not plan_item_id:
        raise RelevanceBenchmarkError("A regional or post-harvest plan item is missing plan_item_id.")
    text = item.get("farmer_visible_text") or item.get("operation_text") or item.get("source_quote") or ""
    operation_id = str(item.get("operation_id") or item.get("action_id") or "").strip()
    return {
        "fact_id": f"{prefix}:{plan_item_id}",
        "fact_kind": "plan_card",
        "text": (
            f"lane={item.get('plan_lane', '')}; source={item.get('source_document_id', '')}; "
            f"text={_compact(text, limit=900)}"
        ),
        "source_document_ids": _source_ids(item.get("source_document_id")),
        "source_locators": _source_ids(item.get("source_location")),
        "plan_or_operation_ids": _source_ids(plan_item_id, operation_id),
        "conditions": _conditions(item.get("conditions_text", ""), item.get("missing_observation", "")),
    }


def _passage_fact(
    passage: RetrievedPassage,
    *,
    index: int,
    plan_or_operation_ids: Sequence[str],
    conditions: Sequence[str],
) -> Mapping[str, Any]:
    return {
        "fact_id": f"passage_{index}",
        "fact_kind": "official_passage",
        "text": (
            f"source={passage.source_document_id}; locator={passage.locator}; "
            f"layer={passage.corpus_layer}; text={passage.text}"
        ),
        "source_document_ids": _source_ids(passage.source_document_id),
        "source_locators": _source_ids(passage.locator),
        "plan_or_operation_ids": _source_ids(*plan_or_operation_ids),
        "conditions": _conditions(*conditions),
    }


def _claims_by_agent(run: BenchmarkRun) -> Mapping[str, tuple[TypedEvidenceClaim, ...]]:
    grouped: dict[str, list[TypedEvidenceClaim]] = defaultdict(list)
    for claim in run.claims:
        grouped[claim.agent_name].append(claim)
    return {name: tuple(claims) for name, claims in grouped.items()}


def _context_facts(run: BenchmarkRun) -> tuple[Mapping[str, Any], ...]:
    grouped = _claims_by_agent(run)
    facts: list[Mapping[str, Any]] = []
    for agent_name in CONTEXT_AGENT_NAMES:
        claims = grouped.get(agent_name, ())
        if not claims:
            raise RelevanceBenchmarkError(f"No context claim produced by {agent_name}.")
        facts.append(_claim_fact(claims[0], fact_id=CONTEXT_FACT_IDS[agent_name]))
    return tuple(facts)


def _context_target_question(
    *,
    role: str,
    scenario: FrozenBenchmarkScenario,
    index: int,
) -> tuple[str, bool]:
    description = _scenario_description(scenario)
    negative = index in {5, 11}
    if role == "weather_context_agent":
        return (
            (
                f"Can any supplied fact be selected as evidence to issue irrigation now for {description}?"
                if negative
                else f"Which admitted historical weather fact is most relevant for explaining the regional plan for {description}?"
            ),
            negative,
        )
    if role == "soil_context_agent":
        return (
            (
                f"Can any supplied fact be selected to calculate a field-specific NPK dose for {description}?"
                if negative
                else f"Which admitted static soil fact is most relevant for delimiting the regional plan for {description}?"
            ),
            negative,
        )
    if role == "satellite_ndvi_context_agent":
        return (
            (
                f"Can any supplied fact be selected as a field disease diagnosis for {description}?"
                if negative
                else f"Which quality-valid representative-cell satellite fact is most relevant as historical context for {description}?"
            ),
            negative,
        )
    if role == "market_evidence_agent":
        return (
            (
                f"Can any supplied fact be selected to make a sell-or-hold forecast for {description}?"
                if negative
                else f"Which source-published historical market fact is most relevant beside the regional plan for {description}?"
            ),
            negative,
        )
    raise RelevanceBenchmarkError(f"Unsupported context role: {role}")


def _context_question(
    *,
    role: str,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    question, negative = _context_target_question(role=role, scenario=scenario, index=index)
    facts = _context_facts(run)
    primary_id = CONTEXT_FACT_IDS[role]
    grouped = _claims_by_agent(run)
    primary = grouped[role][0]
    expected = () if negative or primary.disposition != ClaimDisposition.CONTEXT else (primary_id,)
    condition_lines = _conditions(primary.reasoning, primary.block_reason or "")
    return question, facts, expected, (), (), "safe_empty_selection" if negative else "context_relevance"


def _fertilizer_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    grouped = _claims_by_agent(run)
    claims = grouped.get("fertilizer_baseline_agent", ())
    if len(claims) != 2:
        raise RelevanceBenchmarkError("Fertilizer baseline must produce exactly policy and boundary claims.")
    policy_fact = _claim_fact(
        claims[0],
        fact_id="fertilizer:regional_policy",
        plan_or_operation_ids=(str(claims[0].metadata.get("regional_plan_item_id", "")),),
    )
    boundary_fact = _claim_fact(claims[1], fact_id="fertilizer:field_dose_boundary")
    plan_lanes = {
        str(item.get("plan_lane", "")): item
        for item in scenario.regional_operation_plan_items
        if item.get("plan_lane") in {"regional_calendar", "regional_crop_protection_policy"}
    }
    distractor_items = tuple(
        _plan_fact(plan_lanes[lane])
        for lane in ("regional_calendar", "regional_crop_protection_policy")
        if lane in plan_lanes
    )
    if len(distractor_items) != 2:
        raise RelevanceBenchmarkError("Fertilizer relevance case requires calendar and IPM plan distractors.")
    description = _scenario_description(scenario)
    boundary_only = index in {5, 11}
    question = (
        f"Which admitted fact should be prioritized to explain why a field-specific fertilizer dose is not issued for {description}?"
        if boundary_only
        else f"Which admitted facts should be prioritized to explain the regional nutrient-plan scope and field-dose limit for {description}?"
    )
    expected = ("fertilizer:field_dose_boundary",) if boundary_only else (
        "fertilizer:regional_policy",
        "fertilizer:field_dose_boundary",
    )
    expected_plan_ids = tuple(policy_fact["plan_or_operation_ids"])
    return (
        question,
        (policy_fact, boundary_fact, *distractor_items),
        expected,
        (),
        expected_plan_ids,
        "fertilizer_boundary" if boundary_only else "regional_nutrient_policy_and_boundary",
    )


def _rag_question_text(scenario: FrozenBenchmarkScenario) -> str:
    description = _scenario_description(scenario)
    if scenario.retrievable_operation_passages:
        return (
            f"Which exact source-quoted crop operation passage and recorded condition are relevant to {description}?"
        )
    return (
        f"Which exact-crop post-harvest handling passage and recorded condition are relevant to {description}?"
    )


def _matching_passage_metadata(
    scenario: FrozenBenchmarkScenario,
    passage: RetrievedPassage,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Recover source-bound operation IDs and conditions for one admitted passage."""
    matches: list[Mapping[str, Any]] = []
    if passage.corpus_layer == "source_scoped_operation":
        matches = [
            item
            for item in scenario.retrievable_operation_passages
            if item.get("source_document_id") == passage.source_document_id
            and str(item.get("operation_text", "")) in passage.text
        ]
    elif passage.corpus_layer == "postharvest_exact_crop":
        matches = [
            item
            for item in scenario.postharvest_plan_items
            if item.get("source_document_id") == passage.source_document_id
            and str(item.get("operation_text", "")) in passage.text
        ]
    identifiers = _source_ids(
        *(item.get("action_id") or item.get("operation_id") or item.get("plan_item_id") for item in matches)
    )
    conditions = _conditions(*(item.get("conditions_text", "") for item in matches))
    return tuple(identifiers), tuple(conditions)


def _rag_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    if len(run.retrieved_passages) < 2:
        raise RelevanceBenchmarkError("RAG relevance cases require at least two metadata-admitted passages.")
    candidate_metadata = tuple(
        _matching_passage_metadata(scenario, passage)
        for passage in run.retrieved_passages
    )
    facts = tuple(
        _passage_fact(
            passage,
            index=index,
            plan_or_operation_ids=metadata[0],
            conditions=metadata[1],
        )
        for index, (passage, metadata) in enumerate(zip(run.retrieved_passages, candidate_metadata), start=1)
    )
    preferred_index = next(
        (
            index
            for index, passage in enumerate(run.retrieved_passages, start=1)
            if passage.corpus_layer == "source_scoped_operation"
        ),
        None,
    )
    if preferred_index is None:
        preferred_index = next(
            (
                index
                for index, passage in enumerate(run.retrieved_passages, start=1)
                if passage.corpus_layer == "postharvest_exact_crop"
            ),
            1,
        )
    expected_id = f"passage_{preferred_index}"
    expected_fact = next(item for item in facts if item["fact_id"] == expected_id)
    return (
        _rag_question_text(scenario),
        facts,
        (expected_id,),
        (expected_id,),
        tuple(expected_fact["plan_or_operation_ids"]),
        "source_scoped_or_exact_crop_passage",
    )


def _coordinator_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    lanes = (
        ("regional_calendar", "seasonal calendar"),
        ("regional_nutrient_policy", "regional nutrient-policy"),
        ("regional_crop_protection_policy", "regional crop-protection"),
    )
    target_lane, target_label = lanes[(index - 1) % len(lanes)]
    cards = tuple(
        _plan_fact(item)
        for item in scenario.regional_operation_plan_items
        if item.get("plan_lane") in {"regional_calendar", "regional_nutrient_policy", "regional_crop_protection_policy"}
    )
    target = next((item for item in cards if f"lane={target_lane};" in item["text"]), None)
    if target is None:
        raise RelevanceBenchmarkError(f"Coordinator case is missing {target_lane} plan card.")
    postharvest = tuple(_plan_fact(item, prefix="postharvest") for item in scenario.postharvest_plan_items[:2])
    decision_fact = {
        "fact_id": "decision:operation",
        "fact_kind": "decision_trace",
        "text": (
            f"status={run.decision.decision_status}; operation_status={run.decision.operation_status}; "
            f"direct_farm_action_issued={run.decision.direct_farm_action_issued}; "
            f"citations={','.join(run.decision.citations)}"
        ),
        "source_document_ids": ["FROZEN_SCENARIO_MANIFEST"],
        "source_locators": [],
        "plan_or_operation_ids": [],
        "conditions": _conditions(run.decision.rationale),
    }
    return (
        f"Which documented {target_label} card should be prioritized first for {_scenario_description(scenario)}?",
        (decision_fact, *cards, *postharvest),
        (str(target["fact_id"]),),
        (),
        tuple(target["plan_or_operation_ids"]),
        f"coordinator_priority_{target_lane}",
    )


def _farmer_explanation_question(
    *,
    role: str,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    context_facts = _context_facts(run)
    target_ids = ("context:weather", "context:soil", "context:satellite", "context:market")
    target_id = target_ids[(index - 1) % len(target_ids)]
    target = next((item for item in context_facts if item["fact_id"] == target_id), None)
    if target is None:
        raise RelevanceBenchmarkError(f"Farmer explanation case is missing {target_id}.")
    direct_action_question = index in {5, 11}
    focus = target_id.split(":", 1)[1]
    question = (
        f"Should optional {focus} context be selected to issue a farm-specific action for {_scenario_description(scenario)}?"
        if direct_action_question
        else f"Which optional historical {focus} context card should be selected to clarify the approved plan for {_scenario_description(scenario)}?"
    )
    expected = () if direct_action_question else (target_id,)
    return (
        question,
        context_facts,
        expected,
        (),
        (),
        "safe_empty_selection" if direct_action_question else f"optional_{focus}_context",
    )


def _role_instruction_map(workflow: BenchmarkMASWorkflow) -> Mapping[str, str]:
    instructions = {
        name: agent.llm_selection_instruction
        for name, agent in workflow._bounded_agents_by_name.items()
    }
    if set(instructions) != set(BOUND_LLM_AGENT_NAMES):
        raise RelevanceBenchmarkError("Bounded role instructions do not match the approved role registry.")
    return instructions


def _question_record(
    *,
    question_id: str,
    role: str,
    scenario: FrozenBenchmarkScenario,
    question: str,
    facts: Sequence[Mapping[str, Any]],
    expected_fact_ids: Sequence[str],
    expected_passage_ids: Sequence[str],
    expected_plan_or_operation_ids: Sequence[str],
    label_family: str,
    role_instruction: str,
) -> Mapping[str, Any]:
    fact_ids = tuple(str(fact.get("fact_id", "")) for fact in facts)
    expected = tuple(str(item) for item in expected_fact_ids)
    if len(fact_ids) != len(set(fact_ids)) or not all(fact_ids):
        raise RelevanceBenchmarkError(f"{question_id} has duplicate or empty candidate fact IDs.")
    if not set(expected).issubset(fact_ids):
        raise RelevanceBenchmarkError(f"{question_id} expects a fact outside its allowed set.")
    if len(expected) > MAX_SELECTED_FACTS:
        raise RelevanceBenchmarkError(f"{question_id} has more expected facts than the bounded selection limit.")
    distractors = tuple(item for item in fact_ids if item not in set(expected))
    if not distractors:
        raise RelevanceBenchmarkError(f"{question_id} must contain at least one source-backed distractor.")
    expected_records = tuple(fact for fact in facts if fact["fact_id"] in set(expected))
    required_conditions = _conditions(*(condition for fact in expected_records for condition in fact["conditions"]))
    if not required_conditions:
        # An empty expected selection still needs an explicit scope condition
        # explaining why selection must abstain.
        required_conditions = [
            "The bounded role may select only source-backed facts relevant to its declared context-only scope; no direct farm action is authorized."
        ]
    source_document_ids = _source_ids(
        *(source_id for fact in facts for source_id in fact.get("source_document_ids", ()))
    )
    if not source_document_ids:
        raise RelevanceBenchmarkError(f"{question_id} contains no source document identity.")
    system_prompt = BenchmarkLLMClient._system_prompt(role, role_instruction)
    return {
        "question_id": question_id,
        "benchmark_version": BENCHMARK_VERSION,
        "agent_name": role,
        "scenario_id": scenario.identity.scenario_id,
        "scenario_context": dict(_scenario_context(scenario)),
        "farmer_question": question,
        "selection_limit": MAX_SELECTED_FACTS,
        "label_family": label_family,
        "expected_selection_mode": "safe_empty_selection" if not expected else "select_relevant_facts",
        "allowed_source_document_ids": source_document_ids,
        "allowed_fact_ids": list(fact_ids),
        "allowed_passage_ids": [
            fact["fact_id"] for fact in facts if fact.get("fact_kind") == "official_passage"
        ],
        "allowed_facts": [dict(fact) for fact in facts],
        "expected_admissible_fact_ids": list(expected),
        "expected_admissible_passage_ids": list(expected_passage_ids),
        "expected_plan_or_operation_ids": list(_source_ids(*expected_plan_or_operation_ids)),
        "required_conditions": required_conditions,
        "disallowed_distractor_ids": list(distractors),
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "role_instruction_sha256": sha256(role_instruction.encode("utf-8")).hexdigest(),
        "system_prompt_sha256": sha256(system_prompt.encode("utf-8")).hexdigest(),
        "label_derivation": (
            "Expected IDs are selected only from immutable source-backed claims, admitted passages, "
            "or plan cards in this scenario. Distractors are other admitted source-backed candidates "
            "from the same scenario and cannot expand the evidence boundary."
        ),
    }


def build_relevance_questions(
    *,
    project_root: Path | str = PROJECT_ROOT,
    loader: Optional[FrozenBenchmarkLoader] = None,
) -> tuple[Mapping[str, Any], ...]:
    """Derive 96 immutable relevance questions from existing frozen evidence."""
    root = Path(project_root).resolve()
    active_loader = loader or FrozenBenchmarkLoader(project_root=root)
    workflow = BenchmarkMASWorkflow(loader=active_loader, bounded_llm=BenchmarkLLMClient(enabled=False))
    instructions = _role_instruction_map(workflow)
    available = set(active_loader.scenario_ids())
    missing = sorted(set(CANONICAL_SCENARIO_IDS) - available)
    if missing:
        raise RelevanceBenchmarkError(f"Canonical relevance scenarios are unavailable: {', '.join(missing)}")

    questions: list[Mapping[str, Any]] = []
    for role in BOUND_LLM_AGENT_NAMES:
        role_code = ROLE_CODES[role]
        for index, scenario_id in enumerate(CANONICAL_SCENARIO_IDS, start=1):
            scenario = active_loader.load(scenario_id, verify_raw_hashes=True)
            # The role-specific question is passed through the deterministic
            # workflow so candidate RAG passages use the exact frozen question
            # context that will later be evaluated.
            provisional_question = (
                _rag_question_text(scenario)
                if role == "official_operations_rag_agent"
                else f"Select only source-backed evidence relevant to {_scenario_description(scenario)}."
            )
            run = workflow.run(scenario_id, question=provisional_question, verify_raw_hashes=True)
            if role in CONTEXT_AGENT_NAMES:
                question, facts, expected, passages, plan_ids, label_family = _context_question(
                    role=role, scenario=scenario, run=run, index=index
                )
            elif role == "fertilizer_baseline_agent":
                question, facts, expected, passages, plan_ids, label_family = _fertilizer_question(
                    scenario=scenario, run=run, index=index
                )
            elif role == "official_operations_rag_agent":
                question, facts, expected, passages, plan_ids, label_family = _rag_question(
                    scenario=scenario, run=run
                )
            elif role == "provenance_aware_coordinator_agent":
                question, facts, expected, passages, plan_ids, label_family = _coordinator_question(
                    scenario=scenario, run=run, index=index
                )
            elif role == "farmer_explanation_citation_agent":
                question, facts, expected, passages, plan_ids, label_family = _farmer_explanation_question(
                    role=role, scenario=scenario, run=run, index=index
                )
            else:  # pragma: no cover - BOUND_LLM_AGENT_NAMES is checked above
                raise RelevanceBenchmarkError(f"Unsupported bounded role: {role}")
            question_id = f"REL_{role_code}_{index:02d}"
            questions.append(
                _question_record(
                    question_id=question_id,
                    role=role,
                    scenario=scenario,
                    question=question,
                    facts=facts,
                    expected_fact_ids=expected,
                    expected_passage_ids=passages,
                    expected_plan_or_operation_ids=plan_ids,
                    label_family=label_family,
                    role_instruction=instructions[role],
                )
            )
    validate_relevance_questions(questions)
    return tuple(questions)


def _source_artifact_hashes(project_root: Path) -> Mapping[str, str]:
    hashes: dict[str, str] = {}
    for relative in SOURCE_ARTIFACT_PATHS:
        path = project_root / relative
        if not path.is_file():
            raise RelevanceBenchmarkError(f"Source artifact is missing: {relative}")
        hashes[relative] = _sha256_file(path)
    return hashes


def build_relevance_benchmark(
    *,
    output_dir: Path | str = DEFAULT_BENCHMARK_DIR,
    project_root: Path | str = PROJECT_ROOT,
    loader: Optional[FrozenBenchmarkLoader] = None,
) -> FrozenRelevanceBenchmark:
    """Persist a fresh benchmark directory; refuse to overwrite a frozen one."""
    root = Path(project_root).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise RelevanceBenchmarkError(f"Refusing to overwrite existing relevance benchmark: {destination}")
        destination.rmdir()
    questions = build_relevance_questions(project_root=root, loader=loader)
    destination.mkdir(parents=True, exist_ok=False)
    question_text = "".join(
        json.dumps(question, ensure_ascii=False, sort_keys=True) + "\n" for question in questions
    )
    _atomic_write_text(destination / QUESTIONS_FILENAME, question_text)
    question_path = destination / QUESTIONS_FILENAME
    source_hashes = _source_artifact_hashes(root)
    role_counts = Counter(str(question["agent_name"]) for question in questions)
    manifest: Mapping[str, Any] = {
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_status": "frozen_source_derived_questions_pending_model_runs",
        "question_file": QUESTIONS_FILENAME,
        "question_file_sha256": _sha256_file(question_path),
        "question_count": len(questions),
        "questions_per_role": QUESTIONS_PER_ROLE,
        "roles": list(BOUND_LLM_AGENT_NAMES),
        "role_question_counts": dict(sorted(role_counts.items())),
        "canonical_scenario_ids": list(CANONICAL_SCENARIO_IDS),
        "focused_crop_count": 6,
        "selection_limit": MAX_SELECTED_FACTS,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "source_artifact_sha256": source_hashes,
        "builder": {
            "module": "evaluation/bounded_llm_relevance.py",
            "module_sha256": _sha256_file(Path(__file__).resolve()),
            "git": _git_metadata(root),
        },
        "label_policy": {
            "source_backed_candidates_only": True,
            "same_scenario_distractors_only": True,
            "farm_outcome_ground_truth": False,
            "direct_farm_actions_permitted": False,
        },
    }
    _atomic_write_text(
        destination / MANIFEST_FILENAME,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return load_relevance_benchmark(destination)


def _read_questions(path: Path) -> tuple[Mapping[str, Any], ...]:
    if not path.is_file():
        raise RelevanceBenchmarkError(f"Relevance question file is missing: {path}")
    questions: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RelevanceBenchmarkError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(item, Mapping):
            raise RelevanceBenchmarkError(f"Question at {path}:{line_number} must be an object.")
        questions.append(item)
    return tuple(questions)


def validate_relevance_questions(questions: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed on label, scope, condition, or distractor inconsistencies."""
    if len(questions) != len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE:
        raise RelevanceBenchmarkError(
            f"Expected {len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE} questions, got {len(questions)}."
        )
    question_ids = [str(question.get("question_id", "")) for question in questions]
    if not all(question_ids) or len(question_ids) != len(set(question_ids)):
        raise RelevanceBenchmarkError("Question IDs must be non-empty and unique.")
    role_counts = Counter(str(question.get("agent_name", "")) for question in questions)
    if set(role_counts) != set(BOUND_LLM_AGENT_NAMES):
        raise RelevanceBenchmarkError("Question roles do not match the eight approved bounded-LLM roles.")
    if any(count != QUESTIONS_PER_ROLE for count in role_counts.values()):
        raise RelevanceBenchmarkError("Every bounded role must have exactly 12 frozen relevance questions.")
    for question in questions:
        question_id = str(question["question_id"])
        facts = question.get("allowed_facts")
        allowed = tuple(question.get("allowed_fact_ids", ()))
        expected = tuple(question.get("expected_admissible_fact_ids", ()))
        distractors = tuple(question.get("disallowed_distractor_ids", ()))
        if not isinstance(facts, list) or not facts:
            raise RelevanceBenchmarkError(f"{question_id} has no allowed facts.")
        fact_ids = tuple(str(fact.get("fact_id", "")) for fact in facts if isinstance(fact, Mapping))
        if tuple(fact_ids) != allowed or len(allowed) != len(set(allowed)):
            raise RelevanceBenchmarkError(f"{question_id} allowed fact IDs do not match its fact records.")
        if not set(expected).issubset(allowed):
            raise RelevanceBenchmarkError(f"{question_id} expects an ID outside its allowed facts.")
        if tuple(item for item in allowed if item not in set(expected)) != distractors:
            raise RelevanceBenchmarkError(f"{question_id} distractors must be the exact non-expected candidate set.")
        if not question.get("allowed_source_document_ids"):
            raise RelevanceBenchmarkError(f"{question_id} is missing source document identities.")
        if not question.get("required_conditions"):
            raise RelevanceBenchmarkError(f"{question_id} is missing a required condition/scope boundary.")
        if question.get("selection_limit") != MAX_SELECTED_FACTS:
            raise RelevanceBenchmarkError(f"{question_id} has an unsupported selection limit.")
        if question.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION:
            raise RelevanceBenchmarkError(f"{question_id} has an unexpected prompt template version.")
        expected_passages = tuple(question.get("expected_admissible_passage_ids", ()))
        allowed_passages = tuple(question.get("allowed_passage_ids", ()))
        if not set(expected_passages).issubset(allowed_passages):
            raise RelevanceBenchmarkError(f"{question_id} expects a passage outside its allowed passage IDs.")
        for fact in facts:
            if not isinstance(fact, Mapping) or not fact.get("source_document_ids"):
                raise RelevanceBenchmarkError(f"{question_id} contains a fact without source identity.")


def _verify_source_artifact_hashes(manifest: Mapping[str, Any], project_root: Path) -> None:
    expected = manifest.get("source_artifact_sha256")
    if not isinstance(expected, Mapping) or not expected:
        raise RelevanceBenchmarkError("Relevance benchmark manifest has no source-artifact hash map.")
    for relative, expected_hash in expected.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise RelevanceBenchmarkError("Relevance source-artifact hash map is malformed.")
        path = (project_root / relative).resolve()
        if project_root not in path.parents or not path.is_file():
            raise RelevanceBenchmarkError(f"Relevance source artifact is missing or outside the project: {relative}")
        if _sha256_file(path) != expected_hash and relative not in _HISTORICAL_PRESENTATION_ONLY_ARTIFACTS:
            raise RelevanceBenchmarkError(
                f"Relevance source artifact hash differs from frozen manifest: {relative}"
            )


def load_relevance_benchmark(
    benchmark_dir: Path | str = DEFAULT_BENCHMARK_DIR,
    *,
    project_root: Path | str = PROJECT_ROOT,
    verify_source_hashes: bool = True,
) -> FrozenRelevanceBenchmark:
    """Load and validate a frozen relevance benchmark directory."""
    directory = Path(benchmark_dir).resolve()
    manifest_path = directory / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise RelevanceBenchmarkError(f"Relevance benchmark manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RelevanceBenchmarkError(f"Relevance benchmark manifest is invalid JSON: {exc}") from exc
    if manifest.get("benchmark_version") != BENCHMARK_VERSION:
        raise RelevanceBenchmarkError("Unsupported relevance benchmark version.")
    if manifest.get("question_count") != len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE:
        raise RelevanceBenchmarkError("Manifest does not name the required 96-question benchmark.")
    question_path = directory / str(manifest.get("question_file", ""))
    if _sha256_file(question_path) != manifest.get("question_file_sha256"):
        raise RelevanceBenchmarkError("Relevance question file hash differs from its frozen manifest.")
    questions = _read_questions(question_path)
    validate_relevance_questions(questions)
    if verify_source_hashes:
        _verify_source_artifact_hashes(manifest, Path(project_root).resolve())
    return FrozenRelevanceBenchmark(benchmark_dir=directory, manifest=manifest, questions=questions)


def _select_projected_plan_ids(
    question: Mapping[str, Any],
    selected_fact_ids: Sequence[str],
) -> tuple[str, ...]:
    by_id = {str(fact["fact_id"]): fact for fact in question["allowed_facts"]}
    return tuple(sorted({
        str(plan_id)
        for fact_id in selected_fact_ids
        for plan_id in by_id.get(str(fact_id), {}).get("plan_or_operation_ids", ())
        if str(plan_id).strip()
    }))


def _question_metrics(
    question: Mapping[str, Any],
    result: BoundedLLMResult,
    *,
    latency_ms: int,
    peak_memory_bytes: int,
) -> Mapping[str, Any]:
    expected = tuple(str(item) for item in question["expected_admissible_fact_ids"])
    selected = tuple(str(item) for item in result.selected_fact_ids)
    expected_set, selected_set = set(expected), set(selected)
    intersection = expected_set & selected_set
    expected_passages = set(str(item) for item in question["expected_admissible_passage_ids"])
    selected_passages = set(selected) & set(str(item) for item in question["allowed_passage_ids"])
    expected_plan_ids = set(str(item) for item in question["expected_plan_or_operation_ids"])
    selected_plan_ids = set(_select_projected_plan_ids(question, selected))
    invalid = result.status.startswith("rejected_invalid")
    fallback = result.status.startswith("fallback")
    return {
        "question_id": question["question_id"],
        "scenario_id": question["scenario_id"],
        "agent_name": question["agent_name"],
        "result_status": result.status,
        "result_error": result.error,
        "prompt_sha256": result.prompt_sha256,
        "expected_fact_ids": list(expected),
        "selected_fact_ids": list(selected),
        "expected_passage_ids": sorted(expected_passages),
        "selected_passage_ids": sorted(selected_passages),
        "expected_plan_or_operation_ids": sorted(expected_plan_ids),
        "selected_plan_or_operation_ids": sorted(selected_plan_ids),
        "fact_intersection_count": len(intersection),
        "selected_fact_count": len(selected_set),
        "expected_fact_count": len(expected_set),
        "passage_intersection_count": len(expected_passages & selected_passages),
        "selected_passage_count": len(selected_passages),
        "expected_passage_count": len(expected_passages),
        "plan_intersection_count": len(expected_plan_ids & selected_plan_ids),
        "selected_plan_count": len(selected_plan_ids),
        "expected_plan_count": len(expected_plan_ids),
        "safe_empty_selection_correct": not expected_set and not selected_set,
        "invalid_structured_output": invalid,
        "fallback": fallback,
        "latency_ms": latency_ms,
        "process_peak_memory_bytes": peak_memory_bytes,
    }


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def aggregate_relevance_metrics(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Aggregate exact selection metrics without converting empty labels to zeros."""
    if not records:
        raise RelevanceBenchmarkError("Cannot aggregate an empty relevance result set.")

    def aggregate_group(items: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        fact_intersection = sum(int(item["fact_intersection_count"]) for item in items)
        selected_fact = sum(int(item["selected_fact_count"]) for item in items)
        expected_fact = sum(int(item["expected_fact_count"]) for item in items)
        passage_intersection = sum(int(item["passage_intersection_count"]) for item in items)
        selected_passage = sum(int(item["selected_passage_count"]) for item in items)
        expected_passage = sum(int(item["expected_passage_count"]) for item in items)
        plan_exact_items = [item for item in items if int(item["expected_plan_count"]) > 0]
        empty_items = [item for item in items if int(item["expected_fact_count"]) == 0]
        latencies = [int(item["latency_ms"]) for item in items]
        invalid_count = sum(bool(item["invalid_structured_output"]) for item in items)
        fallback_count = sum(bool(item["fallback"]) for item in items)
        return {
            "question_count": len(items),
            "fact_selection_precision": _ratio(fact_intersection, selected_fact),
            "fact_selection_recall": _ratio(fact_intersection, expected_fact),
            "top_k_recall": _ratio(fact_intersection, expected_fact),
            "passage_precision": _ratio(passage_intersection, selected_passage),
            "passage_recall": _ratio(passage_intersection, expected_passage),
            "plan_or_operation_selection_accuracy": (
                sum(
                    set(item["selected_plan_or_operation_ids"])
                    == set(item["expected_plan_or_operation_ids"])
                    for item in plan_exact_items
                )
                / len(plan_exact_items)
                if plan_exact_items
                else None
            ),
            "safe_empty_selection_accuracy": (
                sum(bool(item["safe_empty_selection_correct"]) for item in empty_items) / len(empty_items)
                if empty_items
                else None
            ),
            "invalid_structured_output_count": invalid_count,
            "invalid_structured_output_rate": invalid_count / len(items),
            "fallback_count": fallback_count,
            "fallback_rate": fallback_count / len(items),
            "accepted_selection_count": sum(item["result_status"] == "accepted" for item in items),
            "mean_latency_ms": statistics.fmean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": sorted(latencies)[max(0, (len(latencies) * 95 + 99) // 100 - 1)],
            "max_process_peak_memory_bytes": max(int(item["process_peak_memory_bytes"]) for item in items),
        }

    by_agent: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_agent[str(record["agent_name"])].append(record)
    return {
        "overall": aggregate_group(records),
        "by_agent": {
            agent_name: aggregate_group(tuple(by_agent[agent_name]))
            for agent_name in sorted(by_agent)
        },
    }


class BoundedLLMRelevanceRunner:
    """Run a frozen relevance set through a bounded client and persist metrics."""

    def __init__(
        self,
        *,
        benchmark: Optional[FrozenRelevanceBenchmark] = None,
        benchmark_dir: Path | str = DEFAULT_BENCHMARK_DIR,
        bounded_llm: Optional[BenchmarkLLMClient] = None,
        project_root: Path | str = PROJECT_ROOT,
        require_clean_git: bool = True,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.benchmark = benchmark or load_relevance_benchmark(benchmark_dir)
        self.bounded_llm = bounded_llm or BenchmarkLLMClient(enabled=True, required=False)
        self.require_clean_git = require_clean_git

    def _role_instructions(self) -> Mapping[str, str]:
        workflow = BenchmarkMASWorkflow(
            bounded_llm=BenchmarkLLMClient(enabled=False),
        )
        return _role_instruction_map(workflow)

    def run(self, *, output_dir: Path | str) -> RelevanceRunSummary:
        if not self.bounded_llm.enabled:
            raise RelevanceBenchmarkError("Relevance evaluation requires an enabled bounded LLM client.")
        git = _git_metadata(self.project_root)
        if self.require_clean_git and git["clean"] != "true":
            raise RelevanceBenchmarkError("A persisted relevance run requires a clean Git worktree.")
        destination = Path(output_dir).resolve()
        if destination.exists():
            raise RelevanceBenchmarkError(f"Refusing to overwrite relevance output directory: {destination}")
        destination.mkdir(parents=True, exist_ok=False)
        instructions = self._role_instructions()
        records: list[Mapping[str, Any]] = []
        for question in self.benchmark.questions:
            started = time.perf_counter()
            result = self.bounded_llm.select_fact_ids(
                agent_name=str(question["agent_name"]),
                scenario_id=str(question["scenario_id"]),
                facts=tuple(
                    {"fact_id": str(fact["fact_id"]), "text": str(fact["text"])}
                    for fact in question["allowed_facts"]
                ),
                role_instruction=instructions[str(question["agent_name"])],
                scenario_context=question["scenario_context"],
                farmer_question=str(question["farmer_question"]),
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            record = _question_metrics(
                question,
                result,
                latency_ms=elapsed_ms,
                peak_memory_bytes=_peak_memory_bytes(),
            )
            records.append(record)
            _atomic_write_text(
                destination / "per_question" / f"{question['question_id']}.json",
                json.dumps({"question": question, "result": record}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
        aggregate = aggregate_relevance_metrics(records)
        manifest = {
            "benchmark_manifest_sha256": _sha256_file(self.benchmark.benchmark_dir / MANIFEST_FILENAME),
            "benchmark_question_sha256": _sha256_file(self.benchmark.benchmark_dir / QUESTIONS_FILENAME),
            "question_count": len(records),
            "bounded_llm_invocation_count": self.bounded_llm.invocation_count,
            "git": git,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "completed_at_utc": _utc_timestamp(),
        }
        _atomic_write_text(destination / "aggregate_relevance_metrics.json", json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
        _atomic_write_text(destination / "run_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        invalid = sum(bool(record["invalid_structured_output"]) for record in records)
        fallback = sum(bool(record["fallback"]) for record in records)
        return RelevanceRunSummary(
            output_dir=destination,
            question_count=len(records),
            accepted_selection_count=sum(record["result_status"] == "accepted" for record in records),
            invalid_structured_output_count=invalid,
            fallback_count=fallback,
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI for a future clean-commit E1/E2/E3 relevance execution."""
    parser = argparse.ArgumentParser(description="Run the frozen bounded-LLM relevance benchmark.")
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--required",
        action="store_true",
        help="Fail immediately when a bounded LLM call errors instead of recording a safe fallback.",
    )
    arguments = parser.parse_args(argv)
    runner = BoundedLLMRelevanceRunner(
        benchmark_dir=arguments.benchmark_dir,
        bounded_llm=BenchmarkLLMClient(enabled=True, required=arguments.required),
    )
    summary = runner.run(output_dir=arguments.output_dir)
    print(json.dumps(asdict(summary), default=str, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
