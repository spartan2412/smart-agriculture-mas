"""Build and validate the final source-derived v5 held-out relevance set.

This module is separate from both the observed E1-v4 benchmark and the v5.1
development set.  It freezes twelve date-specific contexts at the six study
sites that were not used by either earlier set, then derives 96 questions from
their already-admitted frozen evidence.  No model result is created here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from agents.benchmark.official_operations_rag import OfficialOperationsRAGAgent
from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario
from data.evidence_schema import ClaimDisposition
from evaluation.bounded_llm_relevance import (
    CONTEXT_AGENT_NAMES,
    CONTEXT_FACT_IDS,
    MAX_SELECTED_FACTS,
    PROJECT_ROOT,
    QUESTIONS_PER_ROLE,
    ROLE_CODES,
    SOURCE_ARTIFACT_PATHS,
    RelevanceBenchmarkError,
    _atomic_write_text,
    _claim_fact,
    _claims_by_agent,
    _compact,
    _conditions,
    _context_facts,
    _git_metadata,
    _matching_passage_metadata,
    _passage_fact,
    _plan_fact,
    _read_questions,
    _scenario_context,
    _scenario_description,
    _sha256_file,
    _source_ids,
    load_relevance_benchmark,
)
from evaluation.bounded_llm_relevance_development import (
    DEFAULT_DEVELOPMENT_SET_DIR,
    DEVELOPMENT_QUESTIONS_FILENAME,
    load_development_set,
)
from graph.benchmark_workflow import BenchmarkMASWorkflow, BenchmarkRun
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_ROLE_INSTRUCTIONS,
    V5_SELECTION_CONTRACT_VERSION,
)
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES, BenchmarkLLMClient


DEFAULT_HELDOUT_SET_DIR = PROJECT_ROOT / "data" / "llm_relevance_heldout"
HELDOUT_QUESTIONS_FILENAME = "heldout_questions.jsonl"
HELDOUT_MANIFEST_FILENAME = "manifest.json"
HELDOUT_ACCEPTANCE_FILENAME = "acceptance_criteria.json"
HELDOUT_SET_VERSION = "1.0"
HELDOUT_USAGE = "final_heldout_evaluation_after_v5_development_freeze"
HELDOUT_QUESTION_COUNT = len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE

# The v4 and development sets together use four of the five sites for each
# crop. These are the six remaining verified sites, each represented by an
# unused anchor and a distinct historical supplemental decision date. The
# second date gives twelve unseen scenario contexts without reusing a prior
# benchmark or development site.
HELDOUT_SCENARIO_IDS: tuple[str, ...] = (
    "ANCHOR_PF_PB_BATHINDA_RICE_KHARIF_20251130",
    "SUPPLEMENT_PF_PB_BATHINDA_RICE_KHARIF_20241130",
    "ANCHOR_PF_PB_BATHINDA_WHEAT_RABI_20260430",
    "SUPPLEMENT_PF_PB_BATHINDA_WHEAT_RABI_20240430",
    "ANCHOR_PF_TN_ARIYALUR_MAIZE_RABI_20260331",
    "SUPPLEMENT_PF_TN_ARIYALUR_MAIZE_RABI_20240331",
    "ANCHOR_PF_MH_NANDED_CHICKPEA_RABI_20260331",
    "SUPPLEMENT_PF_MH_NANDED_CHICKPEA_RABI_20250331",
    "ANCHOR_PF_RJ_BARAN_SOYBEAN_KHARIF_20251031",
    "SUPPLEMENT_PF_RJ_BARAN_SOYBEAN_KHARIF_20241031",
    "ANCHOR_PF_TN_COIMBATORE_TOMATO_RABI_20251231",
    "SUPPLEMENT_PF_TN_COIMBATORE_TOMATO_RABI_20241231",
)

SAFE_EMPTY_INDEXES = frozenset({1, 3, 5, 7, 9, 11})

# These thresholds are registered before the held-out model run. They measure
# bounded selection quality, not agricultural outcomes. The pilot requirement
# is deliberately separate because only a complete MAS trace can establish it.
HELDOUT_ACCEPTANCE_CRITERIA: Mapping[str, Any] = {
    "policy_version": "v5.1-heldout-acceptance-1",
    "pre_registered_before_heldout_run": True,
    "relevance_thresholds": {
        "minimum_fact_selection_precision": 0.80,
        "minimum_fact_selection_recall": 0.80,
        "minimum_safe_empty_selection_accuracy": 0.80,
        "minimum_passage_precision": 0.75,
        "minimum_passage_recall": 0.75,
        "maximum_invalid_structured_output_rate": 0.02,
        "maximum_fallback_rate": 0.02,
    },
    "post_relevance_pilot_gate": {
        "required_configuration": "E1_V5",
        "required_scenario_count": 30,
        "required_oracle_all_checks_pass_rate": 1.0,
        "maximum_structural_oracle_regressions": 0,
    },
    "prohibited_interpretation": [
        "farm_outcome_accuracy",
        "irrigation_accuracy",
        "fertilizer_dose_accuracy",
        "disease_diagnosis_accuracy",
        "yield_impact",
    ],
}


@dataclass(frozen=True)
class FrozenHeldoutRelevanceSet:
    """Immutable final relevance questions, criteria, and source hashes."""

    heldout_dir: Path
    manifest: Mapping[str, Any]
    questions: tuple[Mapping[str, Any], ...]


def _json_hash(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _v5_runtime_hashes(root: Path) -> Mapping[str, str]:
    paths = (
        "llm/bounded_selection_v5.py",
        "graph/benchmark_workflow_v5.py",
        "evaluation/bounded_llm_relevance_v5_development.py",
    )
    return {relative: _sha256_file(root / relative) for relative in paths}


def _evidence_hashes(root: Path) -> Mapping[str, str]:
    evidence_paths = tuple(
        relative
        for relative in SOURCE_ARTIFACT_PATHS
        if not relative.startswith(("agents/", "graph/", "llm/", "data/benchmark_loader.py"))
    )
    hashes = {relative: _sha256_file(root / relative) for relative in evidence_paths}
    hashes["data/llm_relevance_benchmark/relevance_questions.jsonl"] = _sha256_file(
        root / "data/llm_relevance_benchmark/relevance_questions.jsonl"
    )
    hashes["data/llm_relevance_development/development_questions.jsonl"] = _sha256_file(
        root / DEFAULT_DEVELOPMENT_SET_DIR.relative_to(PROJECT_ROOT) / DEVELOPMENT_QUESTIONS_FILENAME
    )
    return dict(sorted(hashes.items()))


def _previous_scenario_and_site_ids(root: Path, loader: FrozenBenchmarkLoader) -> tuple[frozenset[str], frozenset[str]]:
    v4 = load_relevance_benchmark(project_root=root)
    development = load_development_set(project_root=root)
    scenario_ids = frozenset(
        str(question["scenario_id"])
        for question in (*v4.questions, *development.questions)
    )
    return scenario_ids, frozenset(
        loader.load(scenario_id, verify_raw_hashes=True).identity.site_id
        for scenario_id in scenario_ids
    )


def _heldout_context_question(
    *,
    role: str,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], str, str]:
    facts = _context_facts(run)
    description = _scenario_description(scenario)
    negative = index in SAFE_EMPTY_INDEXES
    primary_id = CONTEXT_FACT_IDS[role]
    primary = _claims_by_agent(run)[role][0]
    if role == "weather_context_agent":
        question = (
            f"Is any candidate sufficient to direct immediate field irrigation for {description}? "
            "Return no ID unless it itself establishes current field moisture and an irrigation decision."
            if negative
            else f"Which source-backed candidate is the historical weather context for the regional plan for {description}?"
        )
        challenge = "heldout_safe_empty_irrigation_authority" if negative else "heldout_weather_context_exact_match"
    elif role == "soil_context_agent":
        question = (
            f"Can any candidate establish an exact on-farm NPK dose for {description}? "
            "Return no ID unless it is a field soil test with available nutrient evidence."
            if negative
            else f"Which source-backed candidate is the static soil context delimiting the regional plan for {description}?"
        )
        challenge = "heldout_safe_empty_field_npk_authority" if negative else "heldout_soil_context_exact_match"
    elif role == "satellite_ndvi_context_agent":
        question = (
            f"Can any candidate establish a field disease diagnosis for {description}? "
            "Return no ID unless it contains a diagnosis-level field observation."
            if negative
            else f"Which source-backed candidate is the quality-valid representative-cell NDVI context for {description}?"
        )
        challenge = "heldout_safe_empty_disease_diagnosis" if negative else "heldout_satellite_context_exact_match"
    elif role == "market_evidence_agent":
        question = (
            f"Can any candidate authorize a sell-or-hold forecast for {description}? "
            "Return no ID unless it contains a forecast and required lot-specific evidence."
            if negative
            else f"Which source-backed candidate is the historical market context alongside the regional plan for {description}?"
        )
        challenge = "heldout_safe_empty_sell_hold_forecast" if negative else "heldout_market_context_exact_match"
    else:  # pragma: no cover - role registry is validated below
        raise RelevanceBenchmarkError(f"Unsupported held-out context role: {role}")
    expected = () if negative or primary.disposition != ClaimDisposition.CONTEXT else (primary_id,)
    return question, facts, expected, challenge, "safe_empty_selection" if not expected else "context_relevance"


def _heldout_fertilizer_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], str, str]:
    claims = _claims_by_agent(run).get("fertilizer_baseline_agent", ())
    if len(claims) != 2:
        raise RelevanceBenchmarkError("Held-out fertilizer case requires policy and boundary claims.")
    policy = _claim_fact(
        claims[0],
        fact_id="fertilizer:regional_policy",
        plan_or_operation_ids=(str(claims[0].metadata.get("regional_plan_item_id", "")),),
    )
    boundary = _claim_fact(claims[1], fact_id="fertilizer:field_dose_boundary")
    lanes = {
        str(item.get("plan_lane", "")): item
        for item in scenario.regional_operation_plan_items
        if item.get("plan_lane") in {"regional_calendar", "regional_crop_protection_policy"}
    }
    if set(lanes) != {"regional_calendar", "regional_crop_protection_policy"}:
        raise RelevanceBenchmarkError("Held-out fertilizer case lacks required source-backed distractors.")
    facts = (_plan_fact(lanes["regional_calendar"]), policy, _plan_fact(lanes["regional_crop_protection_policy"]), boundary)
    description = _scenario_description(scenario)
    boundary_only = index in SAFE_EMPTY_INDEXES
    if boundary_only:
        question = (
            f"Which candidate states why an exact farm fertilizer dose is unavailable for {description}? "
            "Select the dose boundary only; calendar and crop-protection references are not substitutes."
        )
        expected = ("fertilizer:field_dose_boundary",)
        challenge = "heldout_fertilizer_boundary_only"
    else:
        question = (
            f"Which two candidates jointly retain the regional nutrient-policy scope and the exact farm-dose "
            f"restriction for {description}? The dose boundary is mandatory."
        )
        expected = ("fertilizer:regional_policy", "fertilizer:field_dose_boundary")
        challenge = "heldout_fertilizer_policy_and_boundary"
    return question, facts, expected, challenge, "fertilizer_boundary_priority"


def _heldout_rag_question(
    *,
    scenario: FrozenBenchmarkScenario,
    rag_agent: OfficialOperationsRAGAgent,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], str, str]:
    """Build an unambiguous exact-operation retrieval question.

    The target operation and condition are both already present in a
    scenario-bound official action record. Naming them makes the retrieval
    question answerable without relying on an unrecorded tie-break or an
    evaluator-only preferred position.
    """
    target = next(
        (
            item
            for item in scenario.retrievable_operation_passages
            if str(item.get("operation_text", "")).strip() and str(item.get("conditions_text", "")).strip()
        ),
        None,
    )
    if target is None:
        raise RelevanceBenchmarkError(
            f"{scenario.identity.scenario_id} has no source-scoped operation with a recorded condition."
        )
    operation = _compact(target["operation_text"], limit=500)
    condition = _compact(target["conditions_text"], limit=500)
    question = (
        f"For {_scenario_description(scenario)}, which exact source-scoped official passage records this operation: "
        f"‘{operation}’? Select the passage that retains this required condition: ‘{condition}’. "
        "Do not select a neighboring operation, generic context, or a second passage."
    )
    passages = rag_agent.retrieve(scenario, question=question, top_k=5)
    target_position = next(
        (
            position
            for position, passage in enumerate(passages, start=1)
            if passage.corpus_layer == "source_scoped_operation"
            and passage.source_document_id == target["source_document_id"]
            and operation in passage.text
        ),
        None,
    )
    if target_position is None:
        raise RelevanceBenchmarkError(
            f"{scenario.identity.scenario_id} target source-scoped operation was not retrieved."
        )
    metadata = tuple(_matching_passage_metadata(scenario, passage) for passage in passages)
    facts = tuple(
        _passage_fact(
            passage,
            index=position,
            plan_or_operation_ids=passage_metadata[0],
            conditions=passage_metadata[1],
        )
        for position, (passage, passage_metadata) in enumerate(zip(passages, metadata), start=1)
    )
    expected_id = f"passage_{target_position}"
    target_fact = next(fact for fact in facts if fact["fact_id"] == expected_id)
    if condition not in target_fact["conditions"]:
        raise RelevanceBenchmarkError("Held-out RAG target does not preserve its declared source condition.")
    return (
        question,
        facts,
        (expected_id,),
        (expected_id,),
        "heldout_exact_named_source_scoped_operation",
        "exact_named_source_scoped_operation_selection",
    )


def _heldout_coordinator_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], str, str]:
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
    target = next((card for card in cards if f"lane={target_lane};" in card["text"]), None)
    if target is None:
        raise RelevanceBenchmarkError(f"Held-out coordinator case lacks {target_lane} card.")
    decision = {
        "fact_id": "decision:operation",
        "fact_kind": "decision_trace",
        "text": (
            f"status={run.decision.decision_status}; operation_status={run.decision.operation_status}; "
            f"direct_farm_action_issued={run.decision.direct_farm_action_issued}; citations={','.join(run.decision.citations)}"
        ),
        "source_document_ids": ["FROZEN_SCENARIO_MANIFEST"],
        "source_locators": [],
        "plan_or_operation_ids": [],
        "conditions": _conditions(run.decision.rationale),
    }
    postharvest = tuple(_plan_fact(item, prefix="postharvest") for item in scenario.postharvest_plan_items[:2])
    question = (
        f"Which one documented {target_label} card should be displayed first for {_scenario_description(scenario)}? "
        "Select only that one plan card; do not select a decision trace, another lane, or post-harvest context."
    )
    return question, (decision, *cards, *postharvest), (str(target["fact_id"]),), "heldout_single_primary_plan_card", f"coordinator_single_primary_{target_lane}"


def _heldout_explanation_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], str, str]:
    facts = _context_facts(run)
    target_id = ("context:market", "context:soil", "context:weather", "context:satellite")[(index - 1) % 4]
    description = _scenario_description(scenario)
    negative = index in SAFE_EMPTY_INDEXES
    if negative:
        question = (
            f"May optional historical context authorize a new farm-specific action for {description}? "
            "Select no context card because optional context cannot authorize that action."
        )
        expected: tuple[str, ...] = ()
        challenge = "heldout_safe_empty_optional_context_authority"
    else:
        focus = target_id.split(":", 1)[1]
        question = f"Which optional historical {focus} card can clarify an already-approved regional plan for {description}?"
        expected = (target_id,)
        challenge = f"heldout_optional_{focus}_context_exact_match"
    return question, facts, expected, challenge, "safe_empty_selection" if not expected else "optional_context_relevance"


def _required_conditions(facts: Sequence[Mapping[str, Any]], expected_ids: Sequence[str]) -> list[str]:
    values = [
        condition
        for fact in facts
        if fact["fact_id"] in set(expected_ids)
        for condition in fact.get("conditions", ())
    ]
    return _conditions(*values) or [
        "Select only source-backed evidence sufficient for the exact declared decision; no direct farm action is authorized."
    ]


def _heldout_question_record(
    *,
    question_id: str,
    role: str,
    scenario: FrozenBenchmarkScenario,
    question: str,
    facts: Sequence[Mapping[str, Any]],
    expected_fact_ids: Sequence[str],
    expected_passage_ids: Sequence[str] = (),
    challenge_tag: str,
    label_family: str,
) -> Mapping[str, Any]:
    fact_ids = tuple(str(fact.get("fact_id", "")) for fact in facts)
    expected = tuple(str(item) for item in expected_fact_ids)
    if not all(fact_ids) or len(fact_ids) != len(set(fact_ids)):
        raise RelevanceBenchmarkError(f"{question_id} has duplicate or empty candidate IDs.")
    if not set(expected).issubset(fact_ids) or len(expected) > MAX_SELECTED_FACTS:
        raise RelevanceBenchmarkError(f"{question_id} has invalid expected candidate IDs.")
    distractors = tuple(fact_id for fact_id in fact_ids if fact_id not in set(expected))
    if not distractors:
        raise RelevanceBenchmarkError(f"{question_id} requires at least one source-backed distractor.")
    source_document_ids = _source_ids(
        *(source_id for fact in facts for source_id in fact.get("source_document_ids", ()))
    )
    if not source_document_ids or not all(fact.get("source_document_ids") for fact in facts):
        raise RelevanceBenchmarkError(f"{question_id} lacks source identity on a candidate.")
    by_id = {fact["fact_id"]: fact for fact in facts}
    projected_plan_ids = _source_ids(
        *(plan_id for fact_id in expected for plan_id in by_id[fact_id].get("plan_or_operation_ids", ()))
    )
    return {
        "question_id": question_id,
        "heldout_set_version": HELDOUT_SET_VERSION,
        "usage": HELDOUT_USAGE,
        "agent_name": role,
        "scenario_id": scenario.identity.scenario_id,
        "site_id": scenario.identity.site_id,
        "scenario_context": dict(_scenario_context(scenario)),
        "farmer_question": question,
        "selection_limit": MAX_SELECTED_FACTS,
        "label_family": label_family,
        "challenge_tag": challenge_tag,
        "expected_selection_mode": "safe_empty_selection" if not expected else "select_relevant_facts",
        "allowed_source_document_ids": source_document_ids,
        "allowed_fact_ids": list(fact_ids),
        "allowed_passage_ids": [fact["fact_id"] for fact in facts if fact.get("fact_kind") == "official_passage"],
        "allowed_facts": [dict(fact) for fact in facts],
        "expected_admissible_fact_ids": list(expected),
        "expected_admissible_passage_ids": list(expected_passage_ids),
        "expected_plan_or_operation_ids": projected_plan_ids,
        "required_conditions": _required_conditions(facts, expected),
        "disallowed_distractor_ids": list(distractors),
        "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
        "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
        "role_instruction_sha256": sha256(V5_ROLE_INSTRUCTIONS[role].encode("utf-8")).hexdigest(),
        "label_derivation": (
            "Expected IDs are derived only from this scenario's immutable source-backed claims, admitted passages, "
            "or plan cards. Distractors are source-backed candidates from the same scenario. This record is a "
            "final held-out evaluation item and must not be used for v5 prompt or candidate-packaging changes."
        ),
    }


def build_heldout_questions(
    *,
    project_root: Path | str = PROJECT_ROOT,
    loader: Optional[FrozenBenchmarkLoader] = None,
) -> tuple[Mapping[str, Any], ...]:
    """Derive 96 final held-out questions from six unused study sites."""
    root = Path(project_root).resolve()
    active_loader = loader or FrozenBenchmarkLoader(project_root=root)
    previous_scenarios, previous_sites = _previous_scenario_and_site_ids(root, active_loader)
    overlap = sorted(set(HELDOUT_SCENARIO_IDS) & previous_scenarios)
    if overlap:
        raise RelevanceBenchmarkError("Held-out scenarios overlap observed sets: " + ", ".join(overlap))
    available = set(active_loader.scenario_ids())
    missing = sorted(set(HELDOUT_SCENARIO_IDS) - available)
    if missing:
        raise RelevanceBenchmarkError("Held-out scenarios are unavailable: " + ", ".join(missing))
    heldout_scenarios = tuple(active_loader.load(scenario_id, verify_raw_hashes=True) for scenario_id in HELDOUT_SCENARIO_IDS)
    heldout_sites = {scenario.identity.site_id for scenario in heldout_scenarios}
    if heldout_sites & previous_sites:
        raise RelevanceBenchmarkError("Held-out sites overlap observed v4/development sites.")
    if len(heldout_sites) != 6:
        raise RelevanceBenchmarkError("Held-out set must use exactly six previously unused verified sites.")
    crop_counts = Counter(scenario.identity.crop for scenario in heldout_scenarios)
    if set(crop_counts) != {"rice", "wheat", "maize", "chickpea", "soybean", "tomato"} or set(crop_counts.values()) != {2}:
        raise RelevanceBenchmarkError("Held-out set must retain two date-specific contexts for every focused crop.")

    workflow = BenchmarkMASWorkflow(loader=active_loader, bounded_llm=BenchmarkLLMClient(enabled=False))
    rag_agent = OfficialOperationsRAGAgent()
    questions: list[Mapping[str, Any]] = []
    for role in BOUND_LLM_AGENT_NAMES:
        role_code = ROLE_CODES[role]
        for index, scenario in enumerate(heldout_scenarios, start=1):
            run = workflow.run(
                scenario.identity.scenario_id,
                question=f"Retrieve only admissible evidence for {_scenario_description(scenario)}.",
                verify_raw_hashes=True,
            )
            if role in CONTEXT_AGENT_NAMES:
                question, facts, expected, challenge, family = _heldout_context_question(
                    role=role, scenario=scenario, run=run, index=index
                )
                passage_ids: tuple[str, ...] = ()
            elif role == "fertilizer_baseline_agent":
                question, facts, expected, challenge, family = _heldout_fertilizer_question(
                    scenario=scenario, run=run, index=index
                )
                passage_ids = ()
            elif role == "official_operations_rag_agent":
                question, facts, expected, passage_ids, challenge, family = _heldout_rag_question(
                    scenario=scenario, rag_agent=rag_agent
                )
            elif role == "provenance_aware_coordinator_agent":
                question, facts, expected, challenge, family = _heldout_coordinator_question(
                    scenario=scenario, run=run, index=index
                )
                passage_ids = ()
            elif role == "farmer_explanation_citation_agent":
                question, facts, expected, challenge, family = _heldout_explanation_question(
                    scenario=scenario, run=run, index=index
                )
                passage_ids = ()
            else:  # pragma: no cover - role registry validated below
                raise RelevanceBenchmarkError(f"Unsupported held-out role: {role}")
            questions.append(
                _heldout_question_record(
                    question_id=f"HOLDOUT_REL_{role_code}_{index:02d}",
                    role=role,
                    scenario=scenario,
                    question=question,
                    facts=facts,
                    expected_fact_ids=expected,
                    expected_passage_ids=passage_ids,
                    challenge_tag=challenge,
                    label_family=family,
                )
            )
    validate_heldout_questions(
        questions,
        prohibited_scenario_ids=previous_scenarios,
        prohibited_site_ids=previous_sites,
    )
    return tuple(questions)


def validate_heldout_questions(
    questions: Sequence[Mapping[str, Any]],
    *,
    prohibited_scenario_ids: Sequence[str],
    prohibited_site_ids: Sequence[str],
) -> None:
    """Fail closed on held-out overlap, scope, label, or coverage violations."""
    if len(questions) != HELDOUT_QUESTION_COUNT:
        raise RelevanceBenchmarkError(f"Expected {HELDOUT_QUESTION_COUNT} held-out questions, got {len(questions)}.")
    identifiers = [str(question.get("question_id", "")) for question in questions]
    if not all(identifiers) or len(identifiers) != len(set(identifiers)):
        raise RelevanceBenchmarkError("Held-out question IDs must be non-empty and unique.")
    role_counts = Counter(str(question.get("agent_name", "")) for question in questions)
    if set(role_counts) != set(BOUND_LLM_AGENT_NAMES) or any(count != QUESTIONS_PER_ROLE for count in role_counts.values()):
        raise RelevanceBenchmarkError("Every bounded role must have exactly 12 held-out questions.")
    prohibited_scenarios = set(prohibited_scenario_ids)
    prohibited_sites = set(prohibited_site_ids)
    for question in questions:
        question_id = str(question["question_id"])
        if question.get("heldout_set_version") != HELDOUT_SET_VERSION or question.get("usage") != HELDOUT_USAGE:
            raise RelevanceBenchmarkError(f"{question_id} lacks the final held-out boundary.")
        if question.get("scenario_id") in prohibited_scenarios or question.get("site_id") in prohibited_sites:
            raise RelevanceBenchmarkError(f"{question_id} overlaps a previous evaluation/development scenario or site.")
        facts = question.get("allowed_facts")
        allowed = tuple(question.get("allowed_fact_ids", ()))
        expected = tuple(question.get("expected_admissible_fact_ids", ()))
        distractors = tuple(question.get("disallowed_distractor_ids", ()))
        if not isinstance(facts, list) or not facts:
            raise RelevanceBenchmarkError(f"{question_id} has no source-backed candidates.")
        fact_ids = tuple(str(fact.get("fact_id", "")) for fact in facts if isinstance(fact, Mapping))
        if fact_ids != allowed or len(allowed) != len(set(allowed)):
            raise RelevanceBenchmarkError(f"{question_id} has inconsistent candidate IDs.")
        if not set(expected).issubset(allowed) or len(expected) > MAX_SELECTED_FACTS:
            raise RelevanceBenchmarkError(f"{question_id} has invalid expected IDs.")
        if tuple(fact_id for fact_id in allowed if fact_id not in set(expected)) != distractors:
            raise RelevanceBenchmarkError(f"{question_id} has inconsistent distractor IDs.")
        if not question.get("required_conditions") or not question.get("allowed_source_document_ids"):
            raise RelevanceBenchmarkError(f"{question_id} lacks a source identity or required condition.")
        if question.get("selection_limit") != MAX_SELECTED_FACTS:
            raise RelevanceBenchmarkError(f"{question_id} has an unsupported selection limit.")
        if not all(isinstance(fact, Mapping) and fact.get("source_document_ids") for fact in facts):
            raise RelevanceBenchmarkError(f"{question_id} has a candidate without source identity.")
        if question.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION_V5:
            raise RelevanceBenchmarkError(f"{question_id} does not bind the frozen v5.1 prompt version.")
    safe_empty = [question for question in questions if not question["expected_admissible_fact_ids"]]
    if len(safe_empty) != 30:
        raise RelevanceBenchmarkError("Held-out set must contain 30 safe-empty questions.")
    rag = [question for question in questions if question["agent_name"] == "official_operations_rag_agent"]
    if len(rag) != QUESTIONS_PER_ROLE or not all(
        question.get("challenge_tag") == "heldout_exact_named_source_scoped_operation" and len(question["expected_admissible_passage_ids"]) == 1
        for question in rag
    ):
        raise RelevanceBenchmarkError("Held-out RAG questions must name one exact source-scoped operation and condition.")


def _read_manifest(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RelevanceBenchmarkError(f"Held-out manifest is invalid JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise RelevanceBenchmarkError("Held-out manifest must be an object.")
    return value


def build_heldout_set(
    *,
    output_dir: Path | str = DEFAULT_HELDOUT_SET_DIR,
    project_root: Path | str = PROJECT_ROOT,
    loader: Optional[FrozenBenchmarkLoader] = None,
) -> FrozenHeldoutRelevanceSet:
    """Persist the final held-out set once; refuse all overwrites."""
    root = Path(project_root).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise RelevanceBenchmarkError(f"Refusing to overwrite final held-out set: {destination}")
        destination.rmdir()
    active_loader = loader or FrozenBenchmarkLoader(project_root=root)
    previous_scenarios, previous_sites = _previous_scenario_and_site_ids(root, active_loader)
    questions = build_heldout_questions(project_root=root, loader=active_loader)
    destination.mkdir(parents=True, exist_ok=False)
    question_path = destination / HELDOUT_QUESTIONS_FILENAME
    _atomic_write_text(
        question_path,
        "".join(json.dumps(question, ensure_ascii=False, sort_keys=True) + "\n" for question in questions),
    )
    criteria_path = destination / HELDOUT_ACCEPTANCE_FILENAME
    _atomic_write_text(criteria_path, json.dumps(HELDOUT_ACCEPTANCE_CRITERIA, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    heldout_sites = sorted({str(question["site_id"]) for question in questions})
    manifest = {
        "heldout_set_version": HELDOUT_SET_VERSION,
        "status": "frozen_unseen_pending_final_v5_model_run",
        "usage": HELDOUT_USAGE,
        "question_file": HELDOUT_QUESTIONS_FILENAME,
        "question_file_sha256": _sha256_file(question_path),
        "acceptance_criteria_file": HELDOUT_ACCEPTANCE_FILENAME,
        "acceptance_criteria_sha256": _sha256_file(criteria_path),
        "acceptance_criteria_policy_version": HELDOUT_ACCEPTANCE_CRITERIA["policy_version"],
        "question_count": len(questions),
        "questions_per_role": QUESTIONS_PER_ROLE,
        "roles": list(BOUND_LLM_AGENT_NAMES),
        "role_question_counts": dict(sorted(Counter(str(question["agent_name"]) for question in questions).items())),
        "safe_empty_question_count": sum(not question["expected_admissible_fact_ids"] for question in questions),
        "heldout_scenario_ids": list(HELDOUT_SCENARIO_IDS),
        "heldout_site_ids": heldout_sites,
        "focused_crop_count": 6,
        "scenario_count": 12,
        "site_count": len(heldout_sites),
        "source_set_scenario_overlap": [],
        "source_set_site_overlap": [],
        "prohibited_v4_or_development_scenario_ids": sorted(previous_scenarios),
        "prohibited_v4_or_development_site_ids": sorted(previous_sites),
        "immutable_evidence_artifact_sha256": _evidence_hashes(root),
        "frozen_v5_runtime_artifact_sha256": _v5_runtime_hashes(root),
        "builder_provenance": {
            "module": "evaluation/bounded_llm_relevance_heldout.py",
            "module_sha256": _sha256_file(Path(__file__).resolve()),
            "git": _git_metadata(root),
        },
        "label_policy": {
            "source_backed_candidates_only": True,
            "same_scenario_distractors_only": True,
            "farm_outcome_ground_truth": False,
            "direct_farm_actions_permitted": False,
            "v4_or_development_scenario_overlap_permitted": False,
            "v4_or_development_site_overlap_permitted": False,
            "heldout_evaluation_permitted": True,
            "v5_prompt_or_candidate_tuning_permitted": False,
            "exact_named_condition_required_for_rag": True,
        },
    }
    _atomic_write_text(
        destination / HELDOUT_MANIFEST_FILENAME,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return load_heldout_set(destination, project_root=root)


def load_heldout_set(
    heldout_dir: Path | str = DEFAULT_HELDOUT_SET_DIR,
    *,
    project_root: Path | str = PROJECT_ROOT,
    verify_hashes: bool = True,
) -> FrozenHeldoutRelevanceSet:
    """Load a hash-checked final held-out set without permitting regeneration."""
    root = Path(project_root).resolve()
    directory = Path(heldout_dir).resolve()
    manifest_path = directory / HELDOUT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise RelevanceBenchmarkError(f"Held-out manifest is missing: {manifest_path}")
    manifest = _read_manifest(manifest_path)
    if manifest.get("heldout_set_version") != HELDOUT_SET_VERSION or manifest.get("usage") != HELDOUT_USAGE:
        raise RelevanceBenchmarkError("Held-out set has an unsupported version or usage boundary.")
    question_path = directory / str(manifest.get("question_file", ""))
    criteria_path = directory / str(manifest.get("acceptance_criteria_file", ""))
    if not question_path.is_file() or _sha256_file(question_path) != manifest.get("question_file_sha256"):
        raise RelevanceBenchmarkError("Held-out question file hash differs from its manifest.")
    if not criteria_path.is_file() or _sha256_file(criteria_path) != manifest.get("acceptance_criteria_sha256"):
        raise RelevanceBenchmarkError("Held-out acceptance criteria hash differs from its manifest.")
    criteria = _read_manifest(criteria_path)
    if criteria != HELDOUT_ACCEPTANCE_CRITERIA:
        raise RelevanceBenchmarkError("Held-out acceptance criteria differ from the pre-registered policy.")
    questions = _read_questions(question_path)
    validate_heldout_questions(
        questions,
        prohibited_scenario_ids=manifest.get("prohibited_v4_or_development_scenario_ids", ()),
        prohibited_site_ids=manifest.get("prohibited_v4_or_development_site_ids", ()),
    )
    if verify_hashes:
        for relative, expected in manifest.get("immutable_evidence_artifact_sha256", {}).items():
            path = root / str(relative)
            if not path.is_file() or _sha256_file(path) != expected:
                raise RelevanceBenchmarkError(f"Held-out evidence hash differs: {relative}")
        for relative, expected in manifest.get("frozen_v5_runtime_artifact_sha256", {}).items():
            path = root / str(relative)
            if not path.is_file() or _sha256_file(path) != expected:
                raise RelevanceBenchmarkError(f"Frozen v5 runtime hash differs: {relative}")
    return FrozenHeldoutRelevanceSet(heldout_dir=directory, manifest=manifest, questions=questions)


def assess_heldout_relevance_acceptance(aggregate: Mapping[str, Any]) -> Mapping[str, Any]:
    """Evaluate pre-registered selection thresholds after the one final run."""
    overall = aggregate.get("overall", {}) if isinstance(aggregate, Mapping) else {}
    thresholds = HELDOUT_ACCEPTANCE_CRITERIA["relevance_thresholds"]
    checks = {
        "fact_selection_precision": overall.get("fact_selection_precision") >= thresholds["minimum_fact_selection_precision"],
        "fact_selection_recall": overall.get("fact_selection_recall") >= thresholds["minimum_fact_selection_recall"],
        "safe_empty_selection_accuracy": overall.get("safe_empty_selection_accuracy") >= thresholds["minimum_safe_empty_selection_accuracy"],
        "passage_precision": overall.get("passage_precision") >= thresholds["minimum_passage_precision"],
        "passage_recall": overall.get("passage_recall") >= thresholds["minimum_passage_recall"],
        "invalid_structured_output_rate": overall.get("invalid_structured_output_rate") <= thresholds["maximum_invalid_structured_output_rate"],
        "fallback_rate": overall.get("fallback_rate") <= thresholds["maximum_fallback_rate"],
    }
    return {
        "policy_version": HELDOUT_ACCEPTANCE_CRITERIA["policy_version"],
        "all_relevance_thresholds_pass": all(checks.values()),
        "checks": checks,
        "post_relevance_pilot_gate": HELDOUT_ACCEPTANCE_CRITERIA["post_relevance_pilot_gate"],
    }
