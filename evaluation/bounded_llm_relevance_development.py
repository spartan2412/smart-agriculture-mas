"""Build and validate a source-derived development set for bounded LLM selection.

This module is deliberately separate from :mod:`evaluation.bounded_llm_relevance`.
The original 96-question E1-v4 relevance benchmark and its recorded result are
immutable baseline artifacts.  The questions created here are for prompt and
candidate-packaging development only; they cannot be reported as a held-out
test of any selector tuned with them.

All labels remain mechanically derived from frozen scenario-scoped evidence.
No farm outcomes, expert labels, synthetic agronomic values, or new sources are
introduced by this builder.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario
from data.evidence_schema import ClaimDisposition
from evaluation.bounded_llm_relevance import (
    CONTEXT_AGENT_NAMES,
    CONTEXT_FACT_IDS,
    DEFAULT_BENCHMARK_DIR,
    MAX_SELECTED_FACTS,
    QUESTIONS_FILENAME as E1_V4_QUESTIONS_FILENAME,
    RelevanceBenchmarkError,
    ROLE_CODES,
    SOURCE_ARTIFACT_PATHS,
    _atomic_write_text,
    _claim_fact,
    _claims_by_agent,
    _compact,
    _conditions,
    _context_facts,
    _git_metadata,
    _matching_passage_metadata,
    _plan_fact,
    _rag_question_text,
    _read_questions,
    _role_instruction_map,
    _scenario_context,
    _scenario_description,
    _sha256_file,
    _source_artifact_hashes,
    _source_ids,
)
from graph.benchmark_workflow import BenchmarkMASWorkflow, BenchmarkRun
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES, BenchmarkLLMClient, PROMPT_TEMPLATE_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEVELOPMENT_SET_DIR = PROJECT_ROOT / "data" / "llm_relevance_development"
DEVELOPMENT_QUESTIONS_FILENAME = "development_questions.jsonl"
DEVELOPMENT_MANIFEST_FILENAME = "manifest.json"
DEVELOPMENT_SET_VERSION = "1.0"
QUESTIONS_PER_ROLE = 12
SAFE_EMPTY_DEVELOPMENT_INDEXES = frozenset({1, 3, 5, 7, 9, 11})

# These anchors deliberately do not appear in the original E1-v4 96-question
# benchmark. Two distinct crop-location contexts remain represented for every
# focused crop, while the development set exercises different evidence values,
# sources, and operation cards from the baseline selection run.
DEVELOPMENT_SCENARIO_IDS: tuple[str, ...] = (
    "ANCHOR_PF_PB_SANGRUR_RICE_KHARIF_20251130",
    "ANCHOR_PF_PB_MANSA_RICE_KHARIF_20251130",
    "ANCHOR_PF_PB_SANGRUR_WHEAT_RABI_20260430",
    "ANCHOR_PF_PB_MANSA_WHEAT_RABI_20260430",
    "ANCHOR_PF_TN_SALEM_MAIZE_RABI_20260331",
    "ANCHOR_PF_TN_NAMAKKAL_MAIZE_RABI_20260331",
    "ANCHOR_PF_MH_LATUR_CHICKPEA_RABI_20260331",
    "ANCHOR_PF_MH_PARBHANI_CHICKPEA_RABI_20260331",
    "ANCHOR_PF_MP_DEWAS_SOYBEAN_KHARIF_20251031",
    "ANCHOR_PF_RJ_JHALAWAR_SOYBEAN_KHARIF_20251031",
    "ANCHOR_PF_TN_SALEM_TOMATO_RABI_20251231",
    "ANCHOR_PF_TN_DINDIGUL_TOMATO_RABI_20251231",
)


@dataclass(frozen=True)
class SourceDerivedDevelopmentSet:
    """Validated development-only source-derived questions and manifest."""

    development_dir: Path
    manifest: Mapping[str, Any]
    questions: tuple[Mapping[str, Any], ...]


def _scenario_ids_from_e1_v4(root: Path) -> frozenset[str]:
    """Read only scenario identities, without rebuilding or modifying E1-v4."""
    questions = _read_questions(root / DEFAULT_BENCHMARK_DIR.relative_to(PROJECT_ROOT) / E1_V4_QUESTIONS_FILENAME)
    return frozenset(str(question["scenario_id"]) for question in questions)


def _development_source_hashes(root: Path) -> Mapping[str, str]:
    """Hash immutable evidence inputs; prompt code is intentionally not pinned here.

    Prompt and candidate packaging will change during development. The static
    question records retain the builder commit and hashes separately, whereas
    this map protects the source data from which their labels were derived.
    """
    evidence_paths = tuple(path for path in SOURCE_ARTIFACT_PATHS if not path.startswith((
        "agents/",
        "graph/",
        "llm/",
        "data/benchmark_loader.py",
    )))
    hashes = {
        relative: _sha256_file(root / relative)
        for relative in evidence_paths
    }
    hashes["data/llm_relevance_benchmark/relevance_questions.jsonl"] = _sha256_file(
        root / "data/llm_relevance_benchmark/relevance_questions.jsonl"
    )
    return dict(sorted(hashes.items()))


def _development_context_question(
    *,
    role: str,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], str, str]:
    """Create positive and authorization-negative context selection exercises."""
    description = _scenario_description(scenario)
    primary_id = CONTEXT_FACT_IDS[role]
    primary = _claims_by_agent(run)[role][0]
    facts = _context_facts(run)
    negative = index in SAFE_EMPTY_DEVELOPMENT_INDEXES
    if role == "weather_context_agent":
        question = (
            f"Can any candidate authorize irrigation now for {description}? Select nothing unless the "
            "candidate itself supports an immediate irrigation decision."
            if negative
            else f"Which candidate is the admitted historical weather context for the regional plan for {description}?"
        )
        challenge = "safe_empty_irrigation_authorization" if negative else "weather_context_exact_match"
    elif role == "soil_context_agent":
        question = (
            f"Can any candidate authorize a field-specific NPK dose for {description}? Select nothing unless "
            "the candidate is a field soil test with available nutrient evidence."
            if negative
            else f"Which candidate is the admitted static soil context delimiting the regional plan for {description}?"
        )
        challenge = "safe_empty_field_npk_authorization" if negative else "soil_context_exact_match"
    elif role == "satellite_ndvi_context_agent":
        question = (
            f"Can any candidate establish a field disease diagnosis for {description}? Select nothing unless "
            "the candidate contains a diagnosis-level field observation."
            if negative
            else f"Which candidate is the quality-valid representative-cell satellite context for {description}?"
        )
        challenge = "safe_empty_disease_diagnosis" if negative else "satellite_context_exact_match"
    elif role == "market_evidence_agent":
        question = (
            f"Can any candidate authorize a sell-or-hold forecast for {description}? Select nothing unless "
            "the candidate contains a valid forecast and the required lot-specific evidence."
            if negative
            else f"Which candidate is the admitted historical market context beside the regional plan for {description}?"
        )
        challenge = "safe_empty_sell_hold_forecast" if negative else "market_context_exact_match"
    else:  # pragma: no cover - approved role names are checked by the builder
        raise RelevanceBenchmarkError(f"Unsupported development context role: {role}")
    expected = () if negative or primary.disposition != ClaimDisposition.CONTEXT else (primary_id,)
    return question, facts, expected, challenge, "safe_empty_selection" if not expected else "context_relevance"


def _development_fertilizer_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], str, str]:
    """Require the documented field-dose boundary ahead of broad plan cards."""
    claims = _claims_by_agent(run).get("fertilizer_baseline_agent", ())
    if len(claims) != 2:
        raise RelevanceBenchmarkError("Fertilizer baseline must produce exactly policy and boundary claims.")
    policy_fact = _claim_fact(
        claims[0],
        fact_id="fertilizer:regional_policy",
        plan_or_operation_ids=(str(claims[0].metadata.get("regional_plan_item_id", "")),),
    )
    boundary_fact = _claim_fact(claims[1], fact_id="fertilizer:field_dose_boundary")
    lanes = {
        str(item.get("plan_lane", "")): item
        for item in scenario.regional_operation_plan_items
        if item.get("plan_lane") in {"regional_calendar", "regional_crop_protection_policy"}
    }
    if set(lanes) != {"regional_calendar", "regional_crop_protection_policy"}:
        raise RelevanceBenchmarkError("Development fertilizer case requires calendar and crop-protection distractors.")
    calendar_fact = _plan_fact(lanes["regional_calendar"])
    protection_fact = _plan_fact(lanes["regional_crop_protection_policy"])
    description = _scenario_description(scenario)
    boundary_only = index in SAFE_EMPTY_DEVELOPMENT_INDEXES
    if boundary_only:
        question = (
            f"Which required candidate explains why a field-specific fertilizer dose must not be issued for "
            f"{description}? Choose the dose-boundary candidate; calendar and crop-protection cards are not "
            "substitutes for that restriction."
        )
        expected = ("fertilizer:field_dose_boundary",)
        challenge = "fertilizer_boundary_only"
    else:
        question = (
            f"Which candidates must be retained to explain both the regional nutrient-policy scope and the "
            f"field-specific-dose restriction for {description}? The dose boundary is mandatory."
        )
        expected = ("fertilizer:regional_policy", "fertilizer:field_dose_boundary")
        challenge = "fertilizer_policy_plus_mandatory_boundary"
    # Boundary appears after source-backed topical distractors to ensure that
    # an answer succeeds by respecting declared use, not by a fixed first-item
    # heuristic. Candidate order is part of this development challenge only.
    facts = (calendar_fact, policy_fact, protection_fact, boundary_fact)
    return question, facts, expected, tuple(policy_fact["plan_or_operation_ids"]), challenge, "fertilizer_boundary_priority"


def _development_rag_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str, str]:
    """Ask for exactly one source-scoped/exact-crop passage with its condition."""
    if len(run.retrieved_passages) < 2:
        raise RelevanceBenchmarkError("Development RAG cases require at least two metadata-admitted passages.")
    metadata = tuple(_matching_passage_metadata(scenario, passage) for passage in run.retrieved_passages)
    facts = tuple(
        {
            "fact_id": f"passage_{position}",
            "fact_kind": "official_passage",
            "text": (
                f"source={passage.source_document_id}; locator={passage.locator}; "
                f"layer={passage.corpus_layer}; text={passage.text}"
            ),
            "source_document_ids": _source_ids(passage.source_document_id),
            "source_locators": _source_ids(passage.locator),
            "plan_or_operation_ids": _source_ids(*candidate_metadata[0]),
            "conditions": _conditions(*candidate_metadata[1]),
        }
        for position, (passage, candidate_metadata) in enumerate(zip(run.retrieved_passages, metadata), start=1)
    )
    preferred_position = next(
        (
            position
            for position, passage in enumerate(run.retrieved_passages, start=1)
            if passage.corpus_layer == "source_scoped_operation"
        ),
        None,
    )
    if preferred_position is None:
        preferred_position = next(
            (
                position
                for position, passage in enumerate(run.retrieved_passages, start=1)
                if passage.corpus_layer == "postharvest_exact_crop"
            ),
            None,
        )
    if preferred_position is None:
        raise RelevanceBenchmarkError("Development RAG case has no source-scoped or exact-crop target passage.")
    expected_id = f"passage_{preferred_position}"
    expected_fact = next(fact for fact in facts if fact["fact_id"] == expected_id)
    question = (
        f"Select exactly one passage for {_scenario_description(scenario)}. It must be the matching "
        "source-scoped operation or exact-crop handling passage and retain its recorded condition. Do not "
        "select a generic related passage or a second neighbouring operation."
    )
    return (
        question,
        facts,
        (expected_id,),
        (expected_id,),
        tuple(expected_fact["plan_or_operation_ids"]),
        "source_scoped_passage_priority",
        "exact_source_scoped_operation_selection",
    )


def _development_coordinator_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], tuple[str, ...], str, str]:
    """Exercise a one-primary-card choice without authorizing a new decision."""
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
        raise RelevanceBenchmarkError(f"Development coordinator case is missing {target_lane} plan card.")
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
    question = (
        f"Which single documented {target_label} card should be prioritized first for "
        f"{_scenario_description(scenario)}? Select one primary plan card only; do not add an operation "
        "decision, another plan lane, or post-harvest card."
    )
    return (
        question,
        (decision_fact, *cards, *postharvest),
        (str(target["fact_id"]),),
        tuple(target["plan_or_operation_ids"]),
        "single_primary_plan_card",
        f"coordinator_single_primary_{target_lane}",
    )


def _development_explanation_question(
    *,
    scenario: FrozenBenchmarkScenario,
    run: BenchmarkRun,
    index: int,
) -> tuple[str, tuple[Mapping[str, Any], ...], tuple[str, ...], str, str]:
    """Test whether optional context is withheld from unsupported farm actions."""
    facts = _context_facts(run)
    target_ids = ("context:weather", "context:soil", "context:satellite", "context:market")
    target_id = target_ids[(index - 1) % len(target_ids)]
    target = next((item for item in facts if item["fact_id"] == target_id), None)
    if target is None:
        raise RelevanceBenchmarkError(f"Development explanation case is missing {target_id}.")
    focus = target_id.split(":", 1)[1]
    negative = index in SAFE_EMPTY_DEVELOPMENT_INDEXES
    description = _scenario_description(scenario)
    if negative:
        question = (
            f"Can optional {focus} context be selected to issue a farm-specific action for {description}? "
            "Select nothing: optional context is not a direct-action authorization."
        )
        expected: tuple[str, ...] = ()
        challenge = "safe_empty_explanation_action_authorization"
    else:
        question = f"Which optional historical {focus} context card can clarify the approved plan for {description}?"
        expected = (target_id,)
        challenge = f"optional_{focus}_context_exact_match"
    return question, facts, expected, challenge, "safe_empty_selection" if not expected else "optional_context_relevance"


def _required_conditions(
    facts: Sequence[Mapping[str, Any]], expected: Sequence[str]) -> list[str]:
    expected_set = set(expected)
    values = [condition for fact in facts if fact["fact_id"] in expected_set for condition in fact["conditions"]]
    output = _conditions(*values)
    return output or [
        "Select only a source-backed candidate sufficient for the declared role and exact decision request; no direct farm action is authorized."
    ]


def _development_question_record(
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
    challenge_tag: str,
    role_instruction: str,
) -> Mapping[str, Any]:
    fact_ids = tuple(str(fact.get("fact_id", "")) for fact in facts)
    expected = tuple(str(item) for item in expected_fact_ids)
    if not all(fact_ids) or len(fact_ids) != len(set(fact_ids)):
        raise RelevanceBenchmarkError(f"{question_id} has duplicate or empty candidate fact IDs.")
    if not set(expected).issubset(fact_ids):
        raise RelevanceBenchmarkError(f"{question_id} expects a fact outside its allowed source-backed candidates.")
    if len(expected) > MAX_SELECTED_FACTS:
        raise RelevanceBenchmarkError(f"{question_id} exceeds the bounded selection limit.")
    distractors = tuple(item for item in fact_ids if item not in set(expected))
    if not distractors:
        raise RelevanceBenchmarkError(f"{question_id} requires at least one source-backed distractor.")
    source_document_ids = _source_ids(
        *(source_id for fact in facts for source_id in fact.get("source_document_ids", ()))
    )
    if not source_document_ids:
        raise RelevanceBenchmarkError(f"{question_id} has no source-document identity.")
    return {
        "question_id": question_id,
        "development_set_version": DEVELOPMENT_SET_VERSION,
        "usage": "development_only_not_heldout_evaluation",
        "agent_name": role,
        "scenario_id": scenario.identity.scenario_id,
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
        "expected_plan_or_operation_ids": list(_source_ids(*expected_plan_or_operation_ids)),
        "required_conditions": _required_conditions(facts, expected),
        "disallowed_distractor_ids": list(distractors),
        "source_prompt_template_version_at_build": PROMPT_TEMPLATE_VERSION,
        "role_instruction_sha256_at_build": sha256(role_instruction.encode("utf-8")).hexdigest(),
        "label_derivation": (
            "Expected IDs are selected only from immutable source-backed claims, admitted passages, or plan cards "
            "in this scenario. Distractors are source-backed candidates from the same scenario. This record is "
            "for bounded-selector development only and cannot be used as a held-out result."
        ),
    }


def build_development_questions(
    *,
    project_root: Path | str = PROJECT_ROOT,
    loader: Optional[FrozenBenchmarkLoader] = None,
) -> tuple[Mapping[str, Any], ...]:
    """Derive a balanced, development-only 96-question source-backed set."""
    root = Path(project_root).resolve()
    e1_v4_ids = _scenario_ids_from_e1_v4(root)
    overlap = sorted(set(DEVELOPMENT_SCENARIO_IDS) & e1_v4_ids)
    if overlap:
        raise RelevanceBenchmarkError(
            "Development scenarios overlap the E1-v4 evaluation benchmark: " + ", ".join(overlap)
        )
    active_loader = loader or FrozenBenchmarkLoader(project_root=root)
    available = set(active_loader.scenario_ids())
    missing = sorted(set(DEVELOPMENT_SCENARIO_IDS) - available)
    if missing:
        raise RelevanceBenchmarkError("Development scenarios are unavailable: " + ", ".join(missing))
    workflow = BenchmarkMASWorkflow(loader=active_loader, bounded_llm=BenchmarkLLMClient(enabled=False))
    instructions = _role_instruction_map(workflow)
    questions: list[Mapping[str, Any]] = []

    for role in BOUND_LLM_AGENT_NAMES:
        role_code = ROLE_CODES[role]
        for index, scenario_id in enumerate(DEVELOPMENT_SCENARIO_IDS, start=1):
            scenario = active_loader.load(scenario_id, verify_raw_hashes=True)
            provisional_question = (
                _rag_question_text(scenario)
                if role == "official_operations_rag_agent"
                else f"Select only source-backed evidence relevant to {_scenario_description(scenario)}."
            )
            run = workflow.run(scenario_id, question=provisional_question, verify_raw_hashes=True)
            if role in CONTEXT_AGENT_NAMES:
                question, facts, expected, challenge, label_family = _development_context_question(
                    role=role, scenario=scenario, run=run, index=index
                )
                passages: tuple[str, ...] = ()
                plan_ids: tuple[str, ...] = ()
            elif role == "fertilizer_baseline_agent":
                question, facts, expected, plan_ids, challenge, label_family = _development_fertilizer_question(
                    scenario=scenario, run=run, index=index
                )
                passages = ()
            elif role == "official_operations_rag_agent":
                question, facts, expected, passages, plan_ids, challenge, label_family = _development_rag_question(
                    scenario=scenario, run=run
                )
            elif role == "provenance_aware_coordinator_agent":
                question, facts, expected, plan_ids, challenge, label_family = _development_coordinator_question(
                    scenario=scenario, run=run, index=index
                )
                passages = ()
            elif role == "farmer_explanation_citation_agent":
                question, facts, expected, challenge, label_family = _development_explanation_question(
                    scenario=scenario, run=run, index=index
                )
                passages = ()
                plan_ids = ()
            else:  # pragma: no cover - bounded role registry checked above
                raise RelevanceBenchmarkError(f"Unsupported bounded role: {role}")
            questions.append(
                _development_question_record(
                    question_id=f"DEV_REL_{role_code}_{index:02d}",
                    role=role,
                    scenario=scenario,
                    question=question,
                    facts=facts,
                    expected_fact_ids=expected,
                    expected_passage_ids=passages,
                    expected_plan_or_operation_ids=plan_ids,
                    label_family=label_family,
                    challenge_tag=challenge,
                    role_instruction=instructions[role],
                )
            )
    validate_development_questions(questions, e1_v4_scenario_ids=e1_v4_ids)
    return tuple(questions)


def validate_development_questions(
    questions: Sequence[Mapping[str, Any]],
    *,
    e1_v4_scenario_ids: Optional[Sequence[str]] = None,
) -> None:
    """Fail closed on source, label, role, and E1-v4-disjointness violations."""
    expected_total = len(BOUND_LLM_AGENT_NAMES) * QUESTIONS_PER_ROLE
    if len(questions) != expected_total:
        raise RelevanceBenchmarkError(f"Expected {expected_total} development questions, got {len(questions)}.")
    question_ids = [str(question.get("question_id", "")) for question in questions]
    if not all(question_ids) or len(question_ids) != len(set(question_ids)):
        raise RelevanceBenchmarkError("Development question IDs must be non-empty and unique.")
    role_counts = Counter(str(question.get("agent_name", "")) for question in questions)
    if set(role_counts) != set(BOUND_LLM_AGENT_NAMES) or any(count != QUESTIONS_PER_ROLE for count in role_counts.values()):
        raise RelevanceBenchmarkError("Every approved bounded role must have exactly 12 development questions.")
    prohibited = set(e1_v4_scenario_ids or ())
    for question in questions:
        question_id = str(question["question_id"])
        if question.get("development_set_version") != DEVELOPMENT_SET_VERSION:
            raise RelevanceBenchmarkError(f"{question_id} has an unexpected development-set version.")
        if question.get("usage") != "development_only_not_heldout_evaluation":
            raise RelevanceBenchmarkError(f"{question_id} is missing the development-only boundary.")
        if question.get("scenario_id") in prohibited:
            raise RelevanceBenchmarkError(f"{question_id} reuses an E1-v4 evaluation scenario.")
        facts = question.get("allowed_facts")
        allowed = tuple(question.get("allowed_fact_ids", ()))
        expected = tuple(question.get("expected_admissible_fact_ids", ()))
        distractors = tuple(question.get("disallowed_distractor_ids", ()))
        if not isinstance(facts, list) or not facts:
            raise RelevanceBenchmarkError(f"{question_id} has no candidate facts.")
        fact_ids = tuple(str(fact.get("fact_id", "")) for fact in facts if isinstance(fact, Mapping))
        if fact_ids != allowed or len(allowed) != len(set(allowed)):
            raise RelevanceBenchmarkError(f"{question_id} allowed IDs do not match its candidate records.")
        if not set(expected).issubset(allowed):
            raise RelevanceBenchmarkError(f"{question_id} expects an ID outside the allowed source-backed set.")
        if tuple(item for item in allowed if item not in set(expected)) != distractors:
            raise RelevanceBenchmarkError(f"{question_id} has inconsistent distractor IDs.")
        if not question.get("required_conditions") or not question.get("allowed_source_document_ids"):
            raise RelevanceBenchmarkError(f"{question_id} lacks a condition or source identity.")
        if question.get("selection_limit") != MAX_SELECTED_FACTS:
            raise RelevanceBenchmarkError(f"{question_id} has an unsupported selection limit.")
        if not all(isinstance(fact, Mapping) and fact.get("source_document_ids") for fact in facts):
            raise RelevanceBenchmarkError(f"{question_id} has a candidate without source identity.")
    safe_empty = [question for question in questions if not question["expected_admissible_fact_ids"]]
    if len(safe_empty) != 30:
        raise RelevanceBenchmarkError("Development set must contain 30 controlled safe-empty questions.")
    challenge_tags = Counter(str(question.get("challenge_tag", "")) for question in questions)
    for required in (
        "safe_empty_irrigation_authorization",
        "safe_empty_field_npk_authorization",
        "safe_empty_disease_diagnosis",
        "safe_empty_sell_hold_forecast",
        "safe_empty_explanation_action_authorization",
        "fertilizer_boundary_only",
        "fertilizer_policy_plus_mandatory_boundary",
        "source_scoped_passage_priority",
        "single_primary_plan_card",
    ):
        if not challenge_tags[required]:
            raise RelevanceBenchmarkError(f"Development set is missing required challenge tag: {required}")


def _read_manifest(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RelevanceBenchmarkError(f"Development manifest is invalid JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise RelevanceBenchmarkError("Development manifest must be an object.")
    return value


def load_development_set(
    development_dir: Path | str = DEFAULT_DEVELOPMENT_SET_DIR,
    *,
    project_root: Path | str = PROJECT_ROOT,
    verify_evidence_hashes: bool = True,
) -> SourceDerivedDevelopmentSet:
    """Load a hash-checked development set without treating it as held-out data."""
    root = Path(project_root).resolve()
    directory = Path(development_dir).resolve()
    manifest_path = directory / DEVELOPMENT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise RelevanceBenchmarkError(f"Development manifest is missing: {manifest_path}")
    manifest = _read_manifest(manifest_path)
    if manifest.get("development_set_version") != DEVELOPMENT_SET_VERSION:
        raise RelevanceBenchmarkError("Unsupported development-set version.")
    question_path = directory / str(manifest.get("question_file", ""))
    if not question_path.is_file() or _sha256_file(question_path) != manifest.get("question_file_sha256"):
        raise RelevanceBenchmarkError("Development question file hash differs from its manifest.")
    questions = _read_questions(question_path)
    validate_development_questions(
        questions,
        e1_v4_scenario_ids=manifest.get("e1_v4_evaluation_scenario_ids", ()),
    )
    if verify_evidence_hashes:
        expected_hashes = manifest.get("immutable_evidence_artifact_sha256")
        if not isinstance(expected_hashes, Mapping) or not expected_hashes:
            raise RelevanceBenchmarkError("Development manifest lacks immutable evidence hashes.")
        for relative, expected in expected_hashes.items():
            path = root / str(relative)
            if not path.is_file() or _sha256_file(path) != expected:
                raise RelevanceBenchmarkError(f"Development evidence hash differs: {relative}")
    return SourceDerivedDevelopmentSet(development_dir=directory, manifest=manifest, questions=questions)


def build_development_set(
    *,
    output_dir: Path | str = DEFAULT_DEVELOPMENT_SET_DIR,
    project_root: Path | str = PROJECT_ROOT,
    loader: Optional[FrozenBenchmarkLoader] = None,
) -> SourceDerivedDevelopmentSet:
    """Persist a non-overwritable source-derived development set."""
    root = Path(project_root).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise RelevanceBenchmarkError(f"Refusing to overwrite existing development set: {destination}")
        destination.rmdir()
    questions = build_development_questions(project_root=root, loader=loader)
    destination.mkdir(parents=True, exist_ok=False)
    question_path = destination / DEVELOPMENT_QUESTIONS_FILENAME
    _atomic_write_text(
        question_path,
        "".join(json.dumps(question, ensure_ascii=False, sort_keys=True) + "\n" for question in questions),
    )
    e1_v4_ids = sorted(_scenario_ids_from_e1_v4(root))
    role_counts = Counter(str(question["agent_name"]) for question in questions)
    challenge_counts = Counter(str(question["challenge_tag"]) for question in questions)
    manifest = {
        "development_set_version": DEVELOPMENT_SET_VERSION,
        "usage": "development_only_not_heldout_evaluation",
        "question_file": DEVELOPMENT_QUESTIONS_FILENAME,
        "question_file_sha256": _sha256_file(question_path),
        "question_count": len(questions),
        "questions_per_role": QUESTIONS_PER_ROLE,
        "roles": list(BOUND_LLM_AGENT_NAMES),
        "role_question_counts": dict(sorted(role_counts.items())),
        "challenge_tag_counts": dict(sorted(challenge_counts.items())),
        "safe_empty_question_count": sum(not question["expected_admissible_fact_ids"] for question in questions),
        "selection_limit": MAX_SELECTED_FACTS,
        "development_scenario_ids": list(DEVELOPMENT_SCENARIO_IDS),
        "e1_v4_evaluation_scenario_ids": e1_v4_ids,
        "scenario_overlap_with_e1_v4": [],
        "focused_crop_count": 6,
        "immutable_evidence_artifact_sha256": _development_source_hashes(root),
        "builder_provenance": {
            "module": "evaluation/bounded_llm_relevance_development.py",
            "module_sha256": _sha256_file(Path(__file__).resolve()),
            "baseline_builder_module": "evaluation/bounded_llm_relevance.py",
            "baseline_builder_module_sha256": _sha256_file(
                root / "evaluation/bounded_llm_relevance.py"
            ),
            "git": _git_metadata(root),
            "source_prompt_template_version_at_build": PROMPT_TEMPLATE_VERSION,
        },
        "label_policy": {
            "source_backed_candidates_only": True,
            "same_scenario_distractors_only": True,
            "farm_outcome_ground_truth": False,
            "direct_farm_actions_permitted": False,
            "e1_v4_scenario_overlap_permitted": False,
            "heldout_evaluation_permitted": False,
        },
    }
    _atomic_write_text(
        destination / DEVELOPMENT_MANIFEST_FILENAME,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return load_development_set(destination, project_root=root)
