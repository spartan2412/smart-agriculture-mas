"""Source-derived structural evaluation oracle for the frozen benchmark MAS.

The oracle is deliberately outside the farmer-facing LangGraph workflow.  It
reads an immutable :class:`FrozenBenchmarkScenario` and a completed
:class:`BenchmarkRun`, then checks whether the run obeyed the frozen evidence,
scope, action, abstention, conflict, and bounded-LLM contracts.  It does not
produce agricultural labels, recommendations, or farm-outcome accuracy.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence, Tuple

from agents.benchmark.base import (
    BenchmarkDecision,
    RetrievedPassage,
    scenario_spatial_scope,
    scenario_temporal_scope,
)
from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import ClaimDisposition, DecisionDomain, GateResult, TypedEvidenceClaim, stable_claim_id
from graph.benchmark_workflow import BenchmarkRun
from llm.benchmark_llm_client import BOUND_LLM_AGENT_NAMES


ORACLE_VERSION = "1.4"


@dataclass(frozen=True)
class OracleCheck:
    """One explicit pass/fail rule, suitable for a paper-facing audit table."""

    name: str
    passed: bool
    expected: str
    observed: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioOracleResult:
    """Read-only structural evaluation result for one normal benchmark run."""

    oracle_version: str
    scenario_id: str
    checks: Tuple[OracleCheck, ...]
    structural_fingerprint: str

    @property
    def overall_passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failing_check_names(self) -> Tuple[str, ...]:
        return tuple(check.name for check in self.checks if not check.passed)

    def metric_values(self) -> dict[str, float]:
        """Return binary, source-derived metric values for aggregation."""
        values = {check.name: float(check.passed) for check in self.checks}
        values["overall_structural_pass"] = float(self.overall_passed)
        return values

    def as_dict(self) -> dict[str, Any]:
        return {
            "oracle_version": self.oracle_version,
            "scenario_id": self.scenario_id,
            "overall_passed": self.overall_passed,
            "failing_check_names": list(self.failing_check_names),
            "structural_fingerprint": self.structural_fingerprint,
            "checks": [check.as_dict() for check in self.checks],
            "metrics": self.metric_values(),
        }


@dataclass(frozen=True)
class AggregateOracleMetric:
    """Aggregate rate for one binary structural metric."""

    name: str
    passed: int
    total: int

    @property
    def rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "total": self.total,
            "rate": self.rate,
        }


@dataclass(frozen=True)
class AggregateOracleResult:
    """Aggregate result schema for a later 300-scenario batch runner."""

    oracle_version: str
    scenario_count: int
    fully_passing_scenario_count: int
    metrics: Tuple[AggregateOracleMetric, ...]

    @property
    def overall_structural_pass_rate(self) -> float:
        return (
            self.fully_passing_scenario_count / self.scenario_count
            if self.scenario_count
            else 0.0
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "oracle_version": self.oracle_version,
            "scenario_count": self.scenario_count,
            "fully_passing_scenario_count": self.fully_passing_scenario_count,
            "overall_structural_pass_rate": self.overall_structural_pass_rate,
            "metrics": [metric.as_dict() for metric in self.metrics],
        }


@dataclass(frozen=True)
class OracleStratumResult:
    """One disaggregated structural audit result.

    A benchmark-wide rate can conceal a weak crop, site, or scenario subset.
    Strata preserve the same binary, source-derived checks without implying a
    farm-outcome label.
    """

    stratum_name: str
    stratum_value: str
    scenario_count: int
    fully_passing_scenario_count: int
    metrics: Tuple[AggregateOracleMetric, ...]

    @property
    def overall_structural_pass_rate(self) -> float:
        return (
            self.fully_passing_scenario_count / self.scenario_count
            if self.scenario_count
            else 0.0
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "stratum_name": self.stratum_name,
            "stratum_value": self.stratum_value,
            "scenario_count": self.scenario_count,
            "fully_passing_scenario_count": self.fully_passing_scenario_count,
            "overall_structural_pass_rate": self.overall_structural_pass_rate,
            "metrics": [metric.as_dict() for metric in self.metrics],
        }


@dataclass(frozen=True)
class StratifiedOracleResult:
    """Complete disaggregated report for a set of scenario oracle results."""

    oracle_version: str
    scenario_count: int
    strata: Tuple[OracleStratumResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "oracle_version": self.oracle_version,
            "scenario_count": self.scenario_count,
            "strata": [stratum.as_dict() for stratum in self.strata],
        }


@dataclass(frozen=True)
class FixtureOracleRecord:
    """One policy-compliance result from the separate fixture runner."""

    fixture_id: str
    base_scenario_id: str
    fixture_family: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FixtureOracleResult:
    """Separate aggregate for controlled policy fixtures, never farm outcomes."""

    oracle_version: str
    fixture_count: int
    passed_fixture_count: int
    family_counts: Tuple[Tuple[str, int], ...]
    records: Tuple[FixtureOracleRecord, ...]

    @property
    def coverage_passed(self) -> bool:
        return dict(self.family_counts) == _EXPECTED_FIXTURE_FAMILY_COUNTS

    @property
    def all_passed(self) -> bool:
        return self.coverage_passed and self.fixture_count == self.passed_fixture_count and all(
            record.passed for record in self.records
        )

    @property
    def compliance_rate(self) -> float:
        return self.passed_fixture_count / self.fixture_count if self.fixture_count else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "oracle_version": self.oracle_version,
            "fixture_count": self.fixture_count,
            "passed_fixture_count": self.passed_fixture_count,
            "compliance_rate": self.compliance_rate,
            "coverage_passed": self.coverage_passed,
            "all_passed": self.all_passed,
            "family_counts": dict(self.family_counts),
            "records": [record.as_dict() for record in self.records],
        }


_SYSTEM_SOURCE_IDS = frozenset({
    "BENCHMARK_COORDINATOR_TRACE",
    "BENCHMARK_EVALUATION_TRACE",
    "FROZEN_SCENARIO_MANIFEST",
    "MAS_ENRICHMENT_CONTRACT",
    "NATURAL_SIGNAL_DIVERGENCE",
    "OFFICIAL_ACTION_BINDING_MATRIX",
})
_CONTEXT_PROVIDER_SOURCE_IDS = frozenset({
    "AGMARKNET_MONTHLY_REPORT",
    "NASA_POWER_HISTORICAL_WINDOW",
    "SENTINEL2_L2A",
    "SOILGRIDS",
})
_RESTRICTED_CONTEXT_AGENTS = frozenset({
    "weather_context_agent",
    "soil_context_agent",
    "satellite_ndvi_context_agent",
    "market_evidence_agent",
    "fertilizer_baseline_agent",
    "crop_protection_safety_agent",
    "vision_availability_agent",
})
_REQUIRED_CAPABILITY_FIELDS = (
    "irrigation_action_agent",
    "fertilizer_prescription_agent",
    "pesticide_treatment_agent",
    "crop_stage_agent",
    "disease_diagnosis_agent",
    "leaf_vision_agent",
)
_EXPECTED_FIXTURE_FAMILY_COUNTS = {
    "coordinator_resolution": 48,
    "negative_control_no_comparable_conflict": 6,
    "pre_resolution_integrity_rejection": 6,
}


def _canonical_value(value: Any) -> Any:
    """Normalize trace values before creating a reproducibility fingerprint."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return _canonical_value(value.model_dump(mode="json"))
    if is_dataclass(value):
        return {
            field.name: _canonical_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_canonical_value(item) for item in value]
    return value


def structural_fingerprint(run: BenchmarkRun) -> str:
    """Hash the observable trace fields that a repeated deterministic run must retain."""
    payload = {
        "scenario_id": run.scenario_id,
        "claims": _canonical_value(run.claims),
        "retrieved_passages": _canonical_value(run.retrieved_passages),
        "conflicts": _canonical_value(run.conflicts),
        "decision": _canonical_value(run.decision),
        "farmer_message": run.farmer_message,
        "evaluation": _canonical_value(run.evaluation),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


class BenchmarkEvaluationOracle:
    """Evaluate frozen-run evidence compliance without inventing outcome labels.

    The expected values are reconstructed from the immutable scenario bundle,
    not inferred from agent prose.  This makes the oracle usable for the full
    MAS, future baselines, and safety ablations while keeping it outside their
    decision paths.
    """

    version = ORACLE_VERSION

    @staticmethod
    def _check(
        name: str,
        passed: bool,
        *,
        expected: str,
        observed: str,
        detail: str,
    ) -> OracleCheck:
        return OracleCheck(
            name=name,
            passed=bool(passed),
            expected=expected,
            observed=observed,
            detail=detail,
        )

    @staticmethod
    def _claim_source_ids(claims: Sequence[TypedEvidenceClaim]) -> set[str]:
        return {
            claim.source.source_document_id
            for claim in claims
            if claim.source.source_document_id
        }

    @staticmethod
    def _scenario_source_ids(scenario: FrozenBenchmarkScenario) -> set[str]:
        """Collect documented source identifiers from immutable scenario evidence."""
        source_ids = set(_SYSTEM_SOURCE_IDS | _CONTEXT_PROVIDER_SOURCE_IDS)
        source_id_fields = {
            "source_document_id",
            "source_id",
            "fertilizer_source_id",
            "protection_source_id",
            "crop_season_source_id",
        }

        def visit(value: Any) -> None:
            if isinstance(value, Mapping):
                for key, item in value.items():
                    if key in source_id_fields and str(item).strip():
                        source_ids.add(str(item).strip())
                    visit(item)
            elif isinstance(value, (tuple, list, set, frozenset)):
                for item in value:
                    visit(item)

        for field in fields(scenario):
            visit(getattr(scenario, field.name))
        return source_ids

    def _identity_and_lineage_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        claim_ids = [claim.claim_id for claim in run.claims]
        correct_identity = (
            run.scenario_id == scenario.identity.scenario_id
            and run.decision.scenario_id == scenario.identity.scenario_id
            and run.evaluation.scenario_id == scenario.identity.scenario_id
            and all(claim.scenario_id == scenario.identity.scenario_id for claim in run.claims)
        )
        unique_claim_ids = len(claim_ids) == len(set(claim_ids))
        sourced_claims_are_traceable = all(
            claim.source.source_document_id is None
            or claim.source.source_document_id in _SYSTEM_SOURCE_IDS
            or bool(claim.source.official_url or claim.source.raw_sha256)
            for claim in run.claims
        )
        passed = correct_identity and unique_claim_ids and sourced_claims_are_traceable
        return self._check(
            "input_lineage_integrity",
            passed,
            expected="one frozen scenario identity, unique claim IDs, and traceable sourced claims",
            observed=(
                f"run={run.scenario_id}; claims={len(run.claims)}; "
                f"unique_claim_ids={unique_claim_ids}; traceable_sources={sourced_claims_are_traceable}"
            ),
            detail=(
                "Checks that the completed trace remains bound to one immutable scenario and that "
                "an external-source claim retains an official URL or raw-hash lineage."
            ),
        )

    def _stable_claim_identity_check(self, run: BenchmarkRun) -> OracleCheck:
        """Recompute every typed-claim identity from its evidence payload."""
        stale_claim_ids = [
            claim.claim_id
            for claim in run.claims
            if claim.claim_id != stable_claim_id(claim.model_dump(mode="python"))
        ]
        return self._check(
            "stable_claim_identity_fidelity",
            not stale_claim_ids,
            expected=(
                "every typed claim ID equals the SHA-256 identity derived from its current immutable evidence "
                "payload, excluding only presentation-only bounded-LLM metadata"
            ),
            observed=f"claims={len(run.claims)}; stale_claim_ids={len(stale_claim_ids)}",
            detail=(
                "Detects a trace in which an evidence field was changed after claim creation without receiving a "
                "new deterministic identity."
            ),
        )

    def _claim_scope_contract_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Keep every claim explicitly scoped to the frozen place and source time context.

        Context roles legitimately use distinct source time semantics: a
        Sentinel chronology, a static soil layer, and a declared crop calendar
        cannot all repeat the decision-window wording. The invariant is
        therefore the immutable site identity plus an explicit bounded source
        time description, rather than identical prose.
        """
        district = scenario.identity.district.lower()
        state = scenario.identity.state.lower()
        temporal_markers = ("historical", "pre-decision", "declared", "static")
        wrong_spatial = [
            claim.claim_id
            for claim in run.claims
            if district not in claim.spatial_scope.lower()
            or state not in claim.spatial_scope.lower()
            or "not" not in claim.spatial_scope.lower()
        ]
        wrong_temporal = [
            claim.claim_id
            for claim in run.claims
            if not claim.temporal_scope.strip()
            or not any(marker in claim.temporal_scope.lower() for marker in temporal_markers)
        ]
        return self._check(
            "claim_scope_contract_compliance",
            not wrong_spatial and not wrong_temporal,
            expected=(
                "every claim explicitly names the frozen district/state, preserves a non-farm limitation, and has "
                "a bounded historical, pre-decision, declared-season, or static source-time scope"
            ),
            observed=(
                f"claims={len(run.claims)}; wrong_spatial={len(wrong_spatial)}; "
                f"wrong_temporal={len(wrong_temporal)}"
            ),
            detail=(
                "Prevents an agent from silently recasting representative-cell evidence as another place or an "
                "unbounded present-time farm observation while allowing valid source-specific time semantics."
            ),
        )

    def _citation_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        trace_source_ids = self._claim_source_ids(run.claims) | {
            passage.source_document_id for passage in run.retrieved_passages if passage.source_document_id
        }
        frozen_source_ids = self._scenario_source_ids(scenario)
        citations = tuple(run.decision.citations)
        absent_from_trace = sorted(set(citations) - trace_source_ids)
        absent_from_frozen_evidence = sorted(set(citations) - frozen_source_ids)
        no_blank = all(citation.strip() for citation in citations)
        passed = not absent_from_trace and not absent_from_frozen_evidence and no_blank
        return self._check(
            "citation_traceability",
            passed,
            expected=(
                "every decision citation originates from an emitted claim/passage and is recognised "
                "by the immutable scenario source inventory"
            ),
            observed=(
                f"decision_citations={len(citations)}; absent_from_trace={','.join(absent_from_trace) or 'none'}; "
                f"absent_from_frozen_evidence={','.join(absent_from_frozen_evidence) or 'none'}; "
                f"blank_citation={not no_blank}"
            ),
            detail=(
                "This is a source-lineage check, not a claim that a citation proves farm-level correctness."
            ),
        )

    def _context_source_provenance_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Ensure context claims retain their own source rather than another domain's URL."""
        expected_urls = {
            "weather_context_agent": str(scenario.manifest.get("weather_source_url", "")),
            "soil_context_agent": str(
                scenario.registry_soil_profile[0].get("value_request_url", "")
                if scenario.registry_soil_profile else ""
            ),
            "satellite_ndvi_context_agent": str(
                scenario.satellite_context_manifest.get("item_request_url", "")
            ),
            "market_evidence_agent": str(scenario.market_context_manifest.get("source_url", "")),
        }
        errors: list[str] = []
        for agent_name, expected_url in expected_urls.items():
            matching = [claim for claim in run.claims if claim.agent_name == agent_name]
            if len(matching) != 1:
                errors.append(f"{agent_name}:claim_count={len(matching)}")
                continue
            observed_url = matching[0].source.official_url or ""
            if observed_url != expected_url:
                errors.append(f"{agent_name}:source_url_mismatch")

        internal_trace_sources = {
            "FROZEN_SCENARIO_MANIFEST",
            "BENCHMARK_COORDINATOR_TRACE",
            "BENCHMARK_EVALUATION_TRACE",
        }
        for claim in run.claims:
            if claim.source.source_document_id in internal_trace_sources and claim.source.official_url:
                errors.append(f"{claim.agent_name}:internal_trace_has_external_url")

        return self._check(
            "context_source_provenance_binding",
            not errors,
            expected=(
                "weather, soil, Sentinel, and market claims cite their exact frozen domain source, while "
                "internal trace claims carry no borrowed public-source URL"
            ),
            observed=f"errors={';'.join(errors) or 'none'}",
            detail=(
                "Prevents a cross-domain request URL from appearing as provenance for an otherwise valid context "
                "claim; this is source-binding integrity, not agricultural outcome accuracy."
            ),
        )

    @staticmethod
    def _passage_key(passage: RetrievedPassage) -> tuple[str, str, str, str | None]:
        return (
            passage.source_document_id,
            passage.official_url,
            passage.locator,
            passage.source_raw_sha256,
        )

    @staticmethod
    def _row_key(row: Mapping[str, str], *, location_field: str) -> tuple[str, str, str, str | None]:
        return (
            row.get("source_document_id", ""),
            row.get("official_url", row.get("source_url", "")),
            row.get(location_field, ""),
            row.get("source_raw_sha256") or None,
        )

    def _rag_scope_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        admitted_generic = {
            self._row_key(row, location_field="location") for row in scenario.retrievable_rag_chunks
        }
        admitted_operation = {
            self._row_key(row, location_field="source_location")
            for row in scenario.retrievable_operation_passages
        }
        admitted_postharvest = {
            self._row_key(row, location_field="source_location")
            for row in scenario.retrievable_postharvest_rag_passages
        }
        admitted_generic_ids = {
            row.get("source_document_id", "")
            for row in scenario.rag_scope
            if row.get("rag_scope_status", "").startswith("admitted_")
        }
        violations: list[str] = []
        for passage in run.retrieved_passages:
            key = self._passage_key(passage)
            if passage.corpus_layer == "official_rag":
                if key not in admitted_generic or passage.source_document_id not in admitted_generic_ids:
                    violations.append(f"official_rag:{passage.source_document_id}:{passage.locator}")
            elif passage.corpus_layer == "source_scoped_operation":
                if key not in admitted_operation:
                    violations.append(f"source_scoped_operation:{passage.source_document_id}:{passage.locator}")
            elif passage.corpus_layer == "postharvest_exact_crop":
                if key not in admitted_postharvest:
                    violations.append(f"postharvest_exact_crop:{passage.source_document_id}:{passage.locator}")
            else:
                violations.append(f"unknown_layer:{passage.corpus_layer}:{passage.source_document_id}")
        return self._check(
            "rag_scope_compliance",
            not violations,
            expected="every retrieved passage is in the scenario's pre-admitted scope for its corpus layer",
            observed=f"retrieved={len(run.retrieved_passages)}; violations={';'.join(violations) or 'none'}",
            detail=(
                "Generic RAG, source-scoped operation, and exact-crop post-harvest passages have separate "
                "allow-lists. Retrieval cannot resurrect a blocked source."
            ),
        )

    def _operation_and_condition_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        bindings = {row.get("action_id", ""): row for row in scenario.action_bindings}
        plan_items = {row.get("plan_item_id", ""): row for row in scenario.regional_operation_plan_items}
        postharvest_items = {
            row.get("plan_item_id", ""): row for row in scenario.postharvest_plan_items
        }
        errors: list[str] = []
        official_conditionals = [
            claim
            for claim in run.claims
            if claim.agent_name == "action_feasibility_agent"
            and claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
        ]
        for claim in official_conditionals:
            action_id = str(claim.metadata.get("action_id", ""))
            plan_item_id = str(claim.metadata.get("plan_item_id", ""))
            binding = bindings.get(action_id)
            plan_item = plan_items.get(plan_item_id)
            if binding is None or plan_item is None:
                errors.append(f"unknown_official_operation:{action_id or plan_item_id}")
                continue
            if binding.get("binding_status") != "conditionally_applicable_pending_unobserved_farm_condition":
                errors.append(f"binding_not_conditional:{action_id}")
            if claim.source.source_document_id != binding.get("source_document_id"):
                errors.append(f"binding_source_mismatch:{action_id}")
            if claim.block_reason != binding.get("field_condition_status"):
                errors.append(f"missing_condition_mismatch:{action_id}")
            if claim.metadata.get("conditions_text", "") != plan_item.get("conditions_text", ""):
                errors.append(f"condition_text_mismatch:{action_id}")

        postharvest_conditionals = [
            claim
            for claim in run.claims
            if claim.agent_name == "postharvest_storage_logistics_agent"
            and claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
        ]
        if len(postharvest_conditionals) != len(postharvest_items):
            errors.append(
                f"postharvest_plan_coverage:{len(postharvest_conditionals)}/{len(postharvest_items)}"
            )
        for claim in postharvest_conditionals:
            item_id = str(claim.metadata.get("plan_item_id", ""))
            item = postharvest_items.get(item_id)
            if item is None:
                errors.append(f"unknown_postharvest_item:{item_id}")
                continue
            if claim.source.source_document_id != item.get("source_document_id"):
                errors.append(f"postharvest_source_mismatch:{item_id}")
            if claim.block_reason != item.get("missing_observation"):
                errors.append(f"postharvest_condition_mismatch:{item_id}")
            if claim.metadata.get("source_quote", "") != item.get("source_quote", ""):
                errors.append(f"postharvest_quote_mismatch:{item_id}")
            if item.get("actionability_status") != "conditional_postharvest_planning_reference_not_direct_farm_action":
                errors.append(f"postharvest_actionability_mismatch:{item_id}")

        return self._check(
            "operation_binding_and_condition_compliance",
            not errors,
            expected=(
                "every conditional operation has a valid scenario binding/source and retains its required "
                "unobserved field or lot condition"
            ),
            observed=(
                f"official_conditionals={len(official_conditionals)}; "
                f"postharvest_conditionals={len(postharvest_conditionals)}; "
                f"errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "Checks canonical action bindings and post-harvest plan items instead of trusting the "
                "agent's wording alone."
            ),
        )

    def _conditional_operation_completeness_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Require every pre-admitted conditional plan item to reach its agent.

        The binding/condition check validates an emitted claim.  This separate
        coverage check catches the opposite failure: a valid source-scoped
        item silently disappearing before coordination.
        """
        expected_official = {
            (str(item.get("action_id", "")), str(item.get("plan_item_id", "")))
            for item in scenario.retrievable_operation_passages
        }
        actual_official_rows = [
            (str(claim.metadata.get("action_id", "")), str(claim.metadata.get("plan_item_id", "")))
            for claim in run.claims
            if claim.agent_name == "action_feasibility_agent"
            and claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
        ]
        actual_official = set(actual_official_rows)
        expected_postharvest = {
            str(item.get("plan_item_id", "")) for item in scenario.postharvest_plan_items
        }
        actual_postharvest_rows = [
            str(claim.metadata.get("plan_item_id", ""))
            for claim in run.claims
            if claim.agent_name == "postharvest_storage_logistics_agent"
            and claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
        ]
        actual_postharvest = set(actual_postharvest_rows)
        missing_official = sorted(expected_official - actual_official)
        unexpected_official = sorted(actual_official - expected_official)
        missing_postharvest = sorted(expected_postharvest - actual_postharvest)
        unexpected_postharvest = sorted(actual_postharvest - expected_postharvest)
        duplicate_official = sorted(
            item for item, count in Counter(actual_official_rows).items() if count != 1
        )
        duplicate_postharvest = sorted(
            item for item, count in Counter(actual_postharvest_rows).items() if count != 1
        )
        passed = not (
            missing_official
            or unexpected_official
            or missing_postharvest
            or unexpected_postharvest
            or duplicate_official
            or duplicate_postharvest
        )
        return self._check(
            "conditional_operation_completeness",
            passed,
            expected=(
                "each pre-admitted official and crop-scoped post-harvest conditional plan item is emitted exactly "
                "once as a conditional claim"
            ),
            observed=(
                f"official={len(actual_official)}/{len(expected_official)}; "
                f"postharvest={len(actual_postharvest)}/{len(expected_postharvest)}; "
                f"missing_official={len(missing_official)}; unexpected_official={len(unexpected_official)}; "
                f"missing_postharvest={len(missing_postharvest)}; "
                f"unexpected_postharvest={len(unexpected_postharvest)}; "
                f"duplicate_official={len(duplicate_official)}; "
                f"duplicate_postharvest={len(duplicate_postharvest)}"
            ),
            detail=(
                "Completeness is checked against the immutable scenario allow-list, so an unscoped operation "
                "cannot improve this metric."
            ),
        )

    def _source_quote_locator_hash_fidelity_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Compare operational claim provenance field-for-field with frozen records."""
        official_items = {
            str(item.get("plan_item_id", "")): item
            for item in scenario.retrievable_operation_passages
        }
        postharvest_items = {
            str(item.get("plan_item_id", "")): item
            for item in scenario.postharvest_plan_items
        }
        errors: list[str] = []

        def compare(claim: TypedEvidenceClaim, item: Mapping[str, str], *, label: str) -> None:
            expected = {
                "source_document_id": item.get("source_document_id", ""),
                "official_url": item.get("source_url", item.get("official_url", "")),
                "raw_sha256": item.get("source_raw_sha256", ""),
                "locator": item.get("source_location", ""),
                "source_quote": item.get("source_quote", ""),
            }
            actual = {
                "source_document_id": claim.source.source_document_id or "",
                "official_url": claim.source.official_url or "",
                "raw_sha256": claim.source.raw_sha256 or "",
                "locator": claim.source.locator or "",
                "source_quote": str(claim.metadata.get("source_quote", "")),
            }
            for field, expected_value in expected.items():
                if expected_value and actual[field] != expected_value:
                    errors.append(f"{label}:{field}")

        claim_count = 0
        for claim in run.claims:
            if claim.disposition != ClaimDisposition.CONDITIONAL_OPERATION:
                continue
            plan_item_id = str(claim.metadata.get("plan_item_id", ""))
            if claim.agent_name == "action_feasibility_agent":
                claim_count += 1
                item = official_items.get(plan_item_id)
                if item is None:
                    errors.append(f"official:unknown_plan_item:{plan_item_id}")
                else:
                    compare(claim, item, label=f"official:{plan_item_id}")
            elif claim.agent_name == "postharvest_storage_logistics_agent":
                claim_count += 1
                item = postharvest_items.get(plan_item_id)
                if item is None:
                    errors.append(f"postharvest:unknown_plan_item:{plan_item_id}")
                else:
                    compare(claim, item, label=f"postharvest:{plan_item_id}")
        return self._check(
            "source_quote_locator_hash_fidelity",
            not errors,
            expected=(
                "every operational claim preserves the immutable source identifier, official URL, raw SHA-256, "
                "locator, and quoted source text"
            ),
            observed=f"operational_claims={claim_count}; errors={';'.join(errors) or 'none'}",
            detail=(
                "This is a field-level provenance-fidelity check. It detects a correct-looking operation that "
                "has been attached to a different source snapshot, location, or quotation."
            ),
        )

    def _plan_citation_coverage_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Ensure mandatory plan and selected-operation sources reach the final decision trace."""
        expected_sources = {
            str(item.get("source_document_id", ""))
            for item in (*scenario.regional_operation_plan_items, *scenario.postharvest_plan_items)
            if item.get("source_document_id", "")
        }
        selected_conditional = next(
            (
                claim
                for claim in run.claims
                if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
                and claim.claim == run.decision.operation_text
            ),
            None,
        )
        if selected_conditional and selected_conditional.source.source_document_id:
            expected_sources.add(selected_conditional.source.source_document_id)
        decision_sources = set(run.decision.citations)
        missing = sorted(expected_sources - decision_sources)
        return self._check(
            "plan_and_selected_operation_citation_coverage",
            not missing,
            expected=(
                "all mandatory regional-plan/post-harvest sources and the selected conditional-operation source "
                "are retained in the coordinator citations"
            ),
            observed=(
                f"required_sources={len(expected_sources)}; decision_citations={len(decision_sources)}; "
                f"missing={','.join(missing) or 'none'}"
            ),
            detail=(
                "The coordinator cannot present a plan card while silently dropping its source identity from the "
                "structured decision trace."
            ),
        )

    def _farmer_message_fidelity_check(
        self,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Check that rendered conditional text retains its exact frozen condition and source ID."""
        message = run.farmer_message
        errors: list[str] = []
        trace_marker = "Evidence trace:"
        if trace_marker not in message:
            errors.append("missing_evidence_trace")
        else:
            trace_text = message.split(trace_marker, 1)[1].splitlines()[0].strip().rstrip(".")
            message_citations = {
                item.strip() for item in trace_text.split(",") if item.strip() and item.strip() != "no cited source identifier"
            }
            unknown_message_citations = sorted(message_citations - set(run.decision.citations))
            if unknown_message_citations:
                errors.append(f"message_citation_not_in_decision:{','.join(unknown_message_citations)}")

        if run.decision.decision_status == "conditional_operation_pending_field_precondition":
            selected = next(
                (
                    claim
                    for claim in run.claims
                    if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
                    and claim.claim == run.decision.operation_text
                ),
                None,
            )
            if selected is None:
                errors.append("selected_conditional_claim_missing")
            else:
                condition = str(selected.metadata.get("conditions_text", "")).strip() or (selected.block_reason or "")
                if not condition or condition not in message:
                    errors.append("selected_condition_not_rendered_verbatim")
                source_id = selected.source.source_document_id or ""
                if not source_id or source_id not in message:
                    errors.append("selected_source_not_rendered")
                if "not issued as a farm action" not in message:
                    errors.append("conditional_status_not_rendered")
        return self._check(
            "farmer_message_condition_and_citation_fidelity",
            not errors,
            expected=(
                "the farmer message contains only decision-trace citation IDs and, for a selected conditional "
                "operation, renders the exact required condition, source ID, and non-direct-action status"
            ),
            observed=f"message_chars={len(message)}; errors={';'.join(errors) or 'none'}",
            detail=(
                "This checks evidence-to-message fidelity; it does not judge whether an unobserved field condition "
                "is true."
            ),
        )

    def _farmer_message_source_detail_and_facility_fidelity_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Require the rendered plan to expose all already-admitted detail.

        This is a presentation-integrity check, not an agricultural outcome
        metric.  It verifies that the farmer-facing message does not replace
        existing source-backed schedule, method, condition, quotation, or
        facility information with a vague instruction to consult a reference.
        """
        message = run.farmer_message
        errors: list[str] = []

        regional_fields = (
            "farmer_visible_text",
            "operation_text",
            "method_text",
            "dose_text",
            "conditions_text",
            "source_quote",
            "source_document_id",
            "source_url",
        )
        for item in scenario.regional_operation_plan_items:
            item_id = str(item.get("plan_item_id", ""))
            for field in regional_fields:
                value = str(item.get(field, "") or "").strip()
                if value and value not in message:
                    errors.append(f"regional_detail_missing:{item_id}:{field}")

        for detail in scenario.regional_policy_detail_cards:
            policy_domain = str(detail.get("policy_domain", ""))
            for field in (
                "detail_text",
                "applicability_conditions",
                "non_action_boundary",
                "source_document_id",
                "source_location",
            ):
                value = str(detail.get(field, "") or "").strip()
                if value and value not in message:
                    errors.append(f"policy_detail_missing:{policy_domain}:{field}")

        postharvest_fields = (
            "operation_text",
            "method_or_parameter",
            "conditions_text",
            "source_quote",
            "source_document_id",
            "source_url",
        )
        for item in scenario.postharvest_plan_items:
            item_id = str(item.get("plan_item_id", ""))
            for field in postharvest_fields:
                value = str(item.get(field, "") or "").strip()
                if value and value not in message:
                    errors.append(f"postharvest_detail_missing:{item_id}:{field}")

        route_by_candidate = {
            str(row.get("candidate_id", "")): row
            for row in scenario.postharvest_static_route_context
            if row.get("candidate_id", "")
        }
        facility_fields = (
            "candidate_id",
            "candidate_name",
            "candidate_district",
            "candidate_state",
            "candidate_registry_status",
            "candidate_capacity_mt",
            "geodesic_km",
            "source_document_id",
            "source_url",
            "temporal_interpretation",
            "not_supported",
        )
        for facility in scenario.postharvest_site_facility_context:
            candidate_id = str(facility.get("candidate_id", ""))
            for field in facility_fields:
                value = str(facility.get(field, "") or "").strip()
                if value and value not in message:
                    errors.append(f"facility_detail_missing:{candidate_id}:{field}")
            route = route_by_candidate.get(candidate_id)
            if route is not None:
                for field in ("road_distance_km", "road_duration_minutes", "route_request_url"):
                    value = str(route.get(field, "") or "").strip()
                    if value and value not in message:
                        errors.append(f"route_detail_missing:{candidate_id}:{field}")

        # Context cards are source-backed historical/static facts, not merely
        # summaries.  Require their retained values and their domain-specific
        # sources to be visible so the farmer never has to perform a separate
        # lookup for information already admitted by the scenario bundle.
        weather = scenario.water_context_features
        for field in (
            "weather_observed_days",
            "weather_t2m_mean_c",
            "weather_precipitation_total_mm",
            "weather_rh2m_mean_percent",
            "weather_ws2m_mean_m_s",
            "weather_shortwave_mean_mj_m2_day",
            "water_gwetroot_mean_fraction",
            "water_gwetroot_min_fraction",
            "water_gwetroot_max_fraction",
            "water_gwettop_mean_fraction",
            "water_land_evaporation_total_mm",
            "water_precipitation_minus_land_evaporation_mm",
            "water_context_interpretation",
        ):
            value = str(weather.get(field, "") or "").strip()
            if value and value not in message:
                errors.append(f"weather_detail_missing:{field}")
        weather_url = str(
            scenario.manifest.get("weather_source_url")
            or scenario.registry_weather.get("official_url", "")
        ).strip()
        if weather_url and weather_url not in message:
            errors.append("weather_source_url_missing")

        for row in scenario.registry_soil_profile:
            property_id = str(row.get("property_id", ""))
            for field in ("metadata_title", "raw_value", "conversion_note", "metadata_request_url"):
                value = str(row.get(field, "") or "").strip()
                if value and value not in message:
                    errors.append(f"soil_detail_missing:{property_id}:{field}")

        context_domains = {
            claim.decision_domain
            for claim in run.claims
            if claim.disposition == ClaimDisposition.CONTEXT
        }
        satellite = scenario.satellite_context_features or {}
        chronology = scenario.ndvi_timeseries_features
        satellite_url = str(scenario.satellite_context_manifest.get("item_request_url", "") or "").strip()
        if DecisionDomain.SATELLITE_CONTEXT in context_domains:
            for label, row, fields in (
                (
                    "satellite",
                    satellite,
                    (
                        "satellite_item_id",
                        "satellite_datetime_utc",
                        "satellite_scl_class",
                        "satellite_scl_label",
                        "satellite_pixel_quality_status",
                        "satellite_red_dn",
                        "satellite_nir_dn",
                        "satellite_ndvi",
                        "satellite_condition_interpretation",
                    ),
                ),
                (
                    "ndvi_chronology",
                    chronology,
                    (
                        "observation_count",
                        "first_observation_utc",
                        "last_observation_utc",
                        "time_span_days",
                        "first_ndvi",
                        "last_ndvi",
                        "ndvi_change",
                        "ndvi_linear_slope_per_day",
                        "ndvi_trend_direction",
                    ),
                ),
            ):
                for field in fields:
                    value = str(row.get(field, "") or "").strip()
                    if value and value not in message:
                        errors.append(f"{label}_detail_missing:{field}")
            for field in ("catalog", "collection"):
                value = str(scenario.registry_sentinel.get(field, "") or "").strip()
                if value and value not in message:
                    errors.append(f"satellite_registry_detail_missing:{field}")
            if satellite_url and satellite_url not in message:
                errors.append("satellite_source_url_missing")
        else:
            # A failing quality gate is visible, but raw pixel values and a
            # limited chronology must not be promoted into farmer context.
            for value in (
                "**Satellite / NDVI context status**",
                str(satellite.get("satellite_item_id", "") or "").strip(),
                str(scenario.satellite_context_status.get("satellite_condition_status", "") or "").strip(),
                str(scenario.satellite_context_status.get("restriction_reason", "") or "").strip(),
                satellite_url,
            ):
                if value and value not in message:
                    errors.append("satellite_unavailable_status_detail_missing")

        market = scenario.market_context_features
        market_source_values = tuple(
            str(
                scenario.manifest.get(manifest_field)
                or scenario.registry_market.get(registry_field, "")
            ).strip()
            for manifest_field, registry_field in (
                ("market_source_commodity", "source_commodity"),
                ("market_source_district", "source_district"),
                ("market_source_state", "source_state"),
                ("market_source_url", "official_url"),
            )
        )
        if DecisionDomain.MARKET_CONTEXT in context_domains:
            market_fields = (
                "market_current_month_price_mean_as_reported",
                "market_previous_month_price_mean_as_reported",
                "market_previous_month_change_percent",
                "market_same_month_previous_year_price_mean_as_reported",
                "market_same_month_year_over_year_percent",
                "market_comparison_availability",
                "market_context_interpretation",
            )
        else:
            # The published decision-month value can remain visible, but a
            # missing comparator cannot be rendered as a market interpretation.
            market_fields = (
                "market_current_month_price_mean_as_reported",
                "market_comparison_availability",
            )
            restriction = str(scenario.market_context_status.get("restriction_reason", "") or "").strip()
            if "**Historical nearest-mandi market context**" not in message:
                errors.append("market_unavailable_status_header_missing")
            if restriction and restriction not in message:
                errors.append("market_unavailable_status_reason_missing")
        for field in market_fields:
            value = str(market.get(field, "") or "").strip()
            if value and value not in message:
                errors.append(f"market_detail_missing:{field}")
        for value in market_source_values:
            if value and value not in message:
                errors.append("market_source_detail_missing")

        rag_questions = {
            str(claim.metadata.get("question", "") or "").strip()
            for claim in run.claims
            if claim.agent_name == "official_operations_rag_agent"
        }
        question = next((item for item in rag_questions if item), "")
        if question:
            if "**Question-specific official evidence excerpts**" not in message:
                errors.append("question_specific_rag_header_missing")
            if question not in message:
                errors.append("question_specific_rag_question_missing")
            seen_passages: set[tuple[str, str, str]] = set()
            expected_passages = []
            for passage in run.retrieved_passages:
                identity = (passage.source_document_id, passage.locator, passage.text)
                if identity not in seen_passages:
                    seen_passages.add(identity)
                    expected_passages.append(passage)
            for passage in expected_passages[:2]:
                for value in (
                    passage.source_document_id,
                    passage.source_title,
                    passage.locator,
                    passage.text,
                    passage.official_url,
                ):
                    if value and value not in message:
                        errors.append(f"question_specific_rag_detail_missing:{passage.source_document_id}")
                        break

        if run.decision.conflict_resolution_records:
            if "**Evidence-resolution note**" not in message:
                errors.append("conflict_explanation_header_missing")
            for record in run.decision.conflict_resolution_records:
                for citation in record.citations:
                    if citation and citation not in message:
                        errors.append(f"conflict_explanation_citation_missing:{citation}")

        placeholders = (
            "Nutrient plan reference:",
            "Crop-protection plan reference:",
        )
        for placeholder in placeholders:
            if placeholder in message:
                errors.append(f"generic_lookup_placeholder:{placeholder}")
        if scenario.postharvest_site_facility_context:
            if "not a live availability, booking" not in message:
                errors.append("facility_live_service_boundary_missing")

        return self._check(
            "farmer_message_source_detail_and_facility_fidelity",
            not errors,
            expected=(
                "all non-empty source-backed plan, facility/route, historical/static-context, question-specific "
                "RAG, and farmer-relevant conflict fields already admitted to the scenario are rendered directly, "
                "with no generic nutrient or crop-protection lookup placeholder"
            ),
            observed=(
                f"regional_items={len(scenario.regional_operation_plan_items)}; "
                f"postharvest_items={len(scenario.postharvest_plan_items)}; "
                f"facility_candidates={len(scenario.postharvest_site_facility_context)}; "
                f"question_specific_rag={bool(question)}; "
                f"conflict_records={len(run.decision.conflict_resolution_records)}; "
                f"errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "The check validates self-contained presentation of frozen evidence. It does not convert a "
                "regional schedule, conditional operation, context datum, or directory entry into a farm action "
                "or live service claim."
            ),
        )

    def _plan_coverage_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        expected_lanes = {
            "regional_calendar",
            "regional_nutrient_policy",
            "regional_crop_protection_policy",
        }
        actual_lanes = {
            item.get("plan_lane", "") for item in scenario.regional_operation_plan_items
        }
        calendar_plan_claims = [
            claim
            for claim in run.claims
            if claim.agent_name == "regional_calendar_operation_window_agent"
            and claim.metadata.get("plan_item_ids")
        ]
        exposed_item_ids = {
            str(item_id)
            for claim in calendar_plan_claims
            for item_id in claim.metadata.get("plan_item_ids", ())
        }
        expected_item_ids = {
            item.get("plan_item_id", "") for item in scenario.regional_operation_plan_items
        }
        errors: list[str] = []
        if not expected_lanes.issubset(actual_lanes):
            errors.append("missing_canonical_regional_plan_lane")
        if exposed_item_ids != expected_item_ids:
            errors.append(f"regional_plan_item_exposure:{len(exposed_item_ids)}/{len(expected_item_ids)}")
        if "Evidence trace:" not in run.farmer_message:
            errors.append("farmer_message_has_no_evidence_trace")
        return self._check(
            "grounded_plan_coverage",
            not errors,
            expected="calendar, nutrient-policy, IPM-policy, and all source-linked plan-item IDs are retained",
            observed=(
                f"regional_lanes={','.join(sorted(actual_lanes))}; "
                f"plan_item_ids={len(exposed_item_ids)}/{len(expected_item_ids)}; "
                f"errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "Measures source-linked plan coverage, not user satisfaction or agronomic outcome quality."
            ),
        )

    def _safety_and_permission_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        unsafe_claims = [
            claim.agent_name
            for claim in run.claims
            if (
                claim.agent_name in _RESTRICTED_CONTEXT_AGENTS
                and claim.disposition
                in {ClaimDisposition.SUPPORTED_OPERATION, ClaimDisposition.CONDITIONAL_OPERATION}
            )
        ]
        support_claims = [
            claim.claim_id
            for claim in run.claims
            if claim.disposition == ClaimDisposition.SUPPORTED_OPERATION
            and claim.gate_result == GateResult.PASS
        ]
        metadata_direct_actions = [
            claim.claim_id
            for claim in run.claims
            if claim.metadata.get("direct_farm_action_issued") is True
        ]
        passed = (
            not run.decision.direct_farm_action_issued
            and not unsafe_claims
            and not support_claims
            and not metadata_direct_actions
            and scenario.capability_contract.get("mas_output_rule", "").endswith("no_direct_farm_action")
        )
        return self._check(
            "unsupported_action_prevention_and_agent_permissions",
            passed,
            expected=(
                "current public-only benchmark issues no direct farm action and restricted context agents "
                "cannot emit an operational claim"
            ),
            observed=(
                f"decision_direct_action={run.decision.direct_farm_action_issued}; "
                f"restricted_operational_agents={','.join(unsafe_claims) or 'none'}; "
                f"supported_operation_claims={len(support_claims)}; "
                f"metadata_direct_actions={len(metadata_direct_actions)}"
            ),
            detail=(
                "This is specific to the frozen benchmark capability contract; it does not prohibit a "
                "future field-evidence benchmark from defining a different safety policy."
            ),
        )

    def _abstention_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        safety_claims = [
            claim
            for claim in run.claims
            if claim.disposition
            in {ClaimDisposition.BLOCKED, ClaimDisposition.ABSTAIN, ClaimDisposition.NO_DATA}
        ]
        missing_reasons = [claim.claim_id for claim in safety_claims if not claim.block_reason]
        expected_restrictions = {
            scenario.agent_permission(field)
            for field in _REQUIRED_CAPABILITY_FIELDS
            if scenario.agent_permission(field)
        }
        uncertainty_claim = next(
            (
                claim
                for claim in run.claims
                if claim.agent_name == "uncertainty_abstention_agent"
            ),
            None,
        )
        reported_restrictions = set(
            uncertainty_claim.metadata.get("restriction_reasons", ())
            if uncertainty_claim is not None
            else ()
        )
        absent_restrictions = sorted(expected_restrictions - reported_restrictions)
        passed = not missing_reasons and not absent_restrictions and uncertainty_claim is not None
        return self._check(
            "abstention_reason_coverage",
            passed,
            expected="every unavailable claim has a reason and every frozen mandatory capability restriction is retained",
            observed=(
                f"safety_claims={len(safety_claims)}; missing_reasons={len(missing_reasons)}; "
                f"missing_contract_restrictions={','.join(absent_restrictions) or 'none'}"
            ),
            detail=(
                "Uses the per-scenario capability contract, not a generic assumption about missing evidence."
            ),
        )

    def _conflict_trace_check(
        self,
        run: BenchmarkRun,
    ) -> OracleCheck:
        claims_by_id = {claim.claim_id: claim for claim in run.claims}
        records_by_conflict_id = {
            record.conflict_id: record for record in run.decision.conflict_resolution_records
        }
        errors: list[str] = []
        if tuple(run.decision.conflict_records) != tuple(run.conflicts):
            errors.append("decision_conflict_records_differ_from_run_trace")
        excluded_claim_ids: set[str] = set()
        for conflict in run.conflicts:
            record = records_by_conflict_id.get(conflict.conflict_id)
            if record is None:
                errors.append(f"missing_resolution:{conflict.conflict_id}")
                continue
            record_ids = set(
                record.accepted_claim_ids
                + record.rejected_claim_ids
                + record.downgraded_claim_ids
                + record.deferred_claim_ids
            )
            if not set(conflict.claim_ids).issubset(record_ids):
                errors.append(f"incomplete_claim_resolution:{conflict.conflict_id}")
            if not record.rule_path or not record.rationale:
                errors.append(f"missing_rule_or_rationale:{conflict.conflict_id}")
            if record.direct_farm_action_allowed:
                errors.append(f"unexpected_direct_action_permission:{conflict.conflict_id}")
            excluded_claim_ids.update(record.rejected_claim_ids)
            excluded_claim_ids.update(record.deferred_claim_ids)

        non_excluded_source_ids = {
            claim.source.source_document_id
            for claim in run.claims
            if claim.claim_id not in excluded_claim_ids and claim.source.source_document_id
        }
        excluded_only_source_ids = {
            claims_by_id[claim_id].source.source_document_id
            for claim_id in excluded_claim_ids
            if claim_id in claims_by_id
            and claims_by_id[claim_id].source.source_document_id
            and claims_by_id[claim_id].source.source_document_id not in non_excluded_source_ids
        }
        leaked_sources = sorted(excluded_only_source_ids & set(run.decision.citations))
        if leaked_sources:
            errors.append(f"rejected_or_deferred_citation_leak:{','.join(leaked_sources)}")
        if len(records_by_conflict_id) != len(run.conflicts):
            errors.append("unexpected_or_duplicate_resolution_record")
        return self._check(
            "conflict_trace_completeness_and_exclusion",
            not errors,
            expected=(
                "each detected conflict has a rule/rationale trace; rejected or deferred evidence cannot "
                "supply an exclusive final citation"
            ),
            observed=(
                f"conflicts={len(run.conflicts)}; resolution_records={len(records_by_conflict_id)}; "
                f"errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "Natural NDVI--weather divergences remain non-action trace records and are evaluated "
                "with the same completeness requirement."
            ),
        )

    def _natural_divergence_policy_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Verify that real NDVI--weather divergences stay contextual and non-actionable."""
        divergence = scenario.natural_signal_divergence or {}
        eligible = (
            divergence.get("candidate_status")
            == "eligible_natural_signal_divergence_candidate"
        )
        natural_conflicts = [
            conflict
            for conflict in run.conflicts
            if conflict.conflict_type == "natural_cross_source_context_divergence"
        ]
        natural_resolutions = [
            record
            for record in run.decision.conflict_resolution_records
            if record.conflict_type == "natural_cross_source_context_divergence"
        ]
        errors: list[str] = []
        if eligible:
            if len(natural_conflicts) != 1:
                errors.append(f"eligible_divergence_conflicts:{len(natural_conflicts)}")
            if len(natural_resolutions) != 1:
                errors.append(f"eligible_divergence_resolutions:{len(natural_resolutions)}")
            elif natural_resolutions[0].status != "handled_as_non_action_contextual_divergence":
                errors.append("eligible_divergence_wrong_resolution_status")
            if any(record.direct_farm_action_allowed for record in natural_resolutions):
                errors.append("eligible_divergence_action_permission")
        elif natural_conflicts or natural_resolutions:
            errors.append("noneligible_divergence_forced_into_conflict")
        if run.decision.direct_farm_action_issued:
            errors.append("direct_action_issued")
        return self._check(
            "natural_ndvi_weather_divergence_policy",
            not errors,
            expected=(
                "only an eligible stored NDVI--weather divergence produces one contextual conflict and one "
                "non-action resolution; it never authorizes a direct farm action"
            ),
            observed=(
                f"eligible={eligible}; conflicts={len(natural_conflicts)}; "
                f"resolutions={len(natural_resolutions)}; errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "Evaluates the 43 natural cross-source candidates as provenance-conflict traces, not as crop "
                "stress diagnoses or labels."
            ),
        )

    def _conflict_resolution_citation_fidelity_check(self, run: BenchmarkRun) -> OracleCheck:
        """Require coordinator resolution citations to derive from the conflict's own claims."""
        claims_by_id = {claim.claim_id: claim for claim in run.claims}
        conflicts_by_id = {conflict.conflict_id: conflict for conflict in run.conflicts}
        decision_citations = set(run.decision.citations)
        errors: list[str] = []
        for record in run.decision.conflict_resolution_records:
            conflict = conflicts_by_id.get(record.conflict_id)
            if conflict is None:
                errors.append(f"unknown_conflict:{record.conflict_id}")
                continue
            participant_sources = {
                claims_by_id[claim_id].source.source_document_id
                for claim_id in conflict.claim_ids
                if claim_id in claims_by_id
                and claims_by_id[claim_id].source.source_document_id
            }
            record_sources = set(record.citations)
            if participant_sources and not record_sources:
                errors.append(f"missing_conflict_citation:{record.conflict_id}")
            if not record_sources.issubset(participant_sources):
                errors.append(f"foreign_conflict_citation:{record.conflict_id}")
            if not record_sources.issubset(decision_citations):
                errors.append(f"conflict_citation_missing_from_decision:{record.conflict_id}")
            if len(record.citations) != len(set(record.citations)):
                errors.append(f"duplicate_conflict_citation:{record.conflict_id}")
        return self._check(
            "conflict_resolution_citation_fidelity",
            not errors,
            expected=(
                "each coordinator resolution cites only source IDs carried by the claims in that conflict and those "
                "IDs remain in the final decision citation trace"
            ),
            observed=(
                f"resolution_records={len(run.decision.conflict_resolution_records)}; "
                f"errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "Prevents a coordinator rationale from borrowing an unrelated source to justify a conflict "
                "resolution."
            ),
        )

    def _vision_boundary_check(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> OracleCheck:
        """Enforce the benchmark's explicit no-aligned-image vision boundary."""
        vision_claims = [
            claim for claim in run.claims if claim.agent_name == "vision_availability_agent"
        ]
        expected_reason = scenario.agent_permission("leaf_vision_agent")
        errors: list[str] = []
        if len(vision_claims) != 1:
            errors.append(f"vision_claim_count:{len(vision_claims)}")
        elif (
            vision_claims[0].disposition != ClaimDisposition.NO_DATA
            or vision_claims[0].allowed_use.value != "unavailable"
            or vision_claims[0].gate_result != GateResult.ABSTAIN
            or vision_claims[0].block_reason != expected_reason
        ):
            errors.append("vision_boundary_violation")
        return self._check(
            "vision_no_data_boundary",
            not errors,
            expected=(
                "one vision availability claim is no_data/unavailable/abstain with the frozen leaf-image "
                "restriction reason"
            ),
            observed=(
                f"vision_claims={len(vision_claims)}; expected_reason={expected_reason}; "
                f"errors={';'.join(errors) or 'none'}"
            ),
            detail=(
                "The legacy PlantVillage model remains outside this benchmark because no field-aligned leaf image "
                "exists for any frozen scenario."
            ),
        )

    def _bounded_llm_check(self, run: BenchmarkRun) -> OracleCheck:
        errors: list[str] = []
        records = []
        for claim in run.claims:
            bounded = claim.metadata.get("bounded_llm")
            if not bounded:
                continue
            records.append(bounded)
            if bounded.get("agent_name") != claim.agent_name:
                errors.append(f"agent_mismatch:{claim.agent_name}")
            if bounded.get("agent_name") not in BOUND_LLM_AGENT_NAMES:
                errors.append(f"unapproved_bounded_agent:{bounded.get('agent_name')}")
            selected = tuple(bounded.get("selected_fact_ids", ()))
            if len(selected) != len(set(selected)) or not all(isinstance(item, str) and item for item in selected):
                errors.append(f"invalid_selected_ids:{claim.agent_name}")
            prompt_hash = str(bounded.get("prompt_sha256", ""))
            if len(prompt_hash) != 64 or any(char not in "0123456789abcdef" for char in prompt_hash):
                errors.append(f"invalid_prompt_hash:{claim.agent_name}")
            if bounded.get("selection_is_safety_non_authoritative") is not True:
                errors.append(f"selection_not_marked_non_authoritative:{claim.agent_name}")
        return self._check(
            "bounded_llm_trace_compliance",
            not errors,
            expected="bounded selection metadata is valid and explicitly safety-non-authoritative when present",
            observed=f"bounded_trace_records={len(records)}; errors={';'.join(errors) or 'none'}",
            detail=(
                "Offline deterministic runs produce disabled bounded-call traces; enabled runs remain "
                "subject to the same non-authoritative metadata contract."
            ),
        )

    def evaluate(
        self,
        scenario: FrozenBenchmarkScenario,
        run: BenchmarkRun,
    ) -> ScenarioOracleResult:
        """Evaluate one completed normal workflow run without mutating it."""
        checks = (
            self._identity_and_lineage_check(scenario, run),
            self._stable_claim_identity_check(run),
            self._claim_scope_contract_check(scenario, run),
            self._citation_check(scenario, run),
            self._context_source_provenance_check(scenario, run),
            self._rag_scope_check(scenario, run),
            self._operation_and_condition_check(scenario, run),
            self._conditional_operation_completeness_check(scenario, run),
            self._source_quote_locator_hash_fidelity_check(scenario, run),
            self._plan_coverage_check(scenario, run),
            self._plan_citation_coverage_check(scenario, run),
            self._farmer_message_fidelity_check(run),
            self._farmer_message_source_detail_and_facility_fidelity_check(scenario, run),
            self._safety_and_permission_check(scenario, run),
            self._abstention_check(scenario, run),
            self._conflict_trace_check(run),
            self._conflict_resolution_citation_fidelity_check(run),
            self._natural_divergence_policy_check(scenario, run),
            self._vision_boundary_check(scenario, run),
            self._bounded_llm_check(run),
        )
        return ScenarioOracleResult(
            oracle_version=self.version,
            scenario_id=scenario.identity.scenario_id,
            checks=checks,
            structural_fingerprint=structural_fingerprint(run),
        )

    def evaluate_repeatability(
        self,
        first: BenchmarkRun,
        second: BenchmarkRun,
    ) -> OracleCheck:
        """Check deterministic trace equality for two runs of the same scenario."""
        first_fingerprint, second_fingerprint = structural_fingerprint(first), structural_fingerprint(second)
        same_scenario = first.scenario_id == second.scenario_id
        return self._check(
            "deterministic_trace_reproducibility",
            same_scenario and first_fingerprint == second_fingerprint,
            expected="two normal runs of the same frozen scenario have the same structural fingerprint",
            observed=(
                f"same_scenario={same_scenario}; first={first_fingerprint}; second={second_fingerprint}"
            ),
            detail=(
                "This compares the observable claims, passages, conflicts, decision, message, and existing "
                "per-run evaluator record; latency is intentionally excluded."
            ),
        )

    def evaluate_fixture_runs(self, fixture_runs: Iterable[Any]) -> FixtureOracleResult:
        """Aggregate controlled resolver-policy results without treating them as farm outcomes."""
        records: list[FixtureOracleRecord] = []
        family_counts: Counter[str] = Counter()
        for fixture_run in fixture_runs:
            family = str(fixture_run.fixture_family)
            family_counts[family] += 1
            decision = fixture_run.decision
            policy_safe = decision is None or not decision.direct_farm_action_issued
            expected_match = bool(fixture_run.expected_match)
            passed = expected_match and policy_safe
            records.append(FixtureOracleRecord(
                fixture_id=str(fixture_run.fixture_id),
                base_scenario_id=str(fixture_run.base_scenario_id),
                fixture_family=family,
                passed=passed,
                detail=(
                    f"runner_status={fixture_run.status}; expected_match={expected_match}; "
                    f"direct_farm_action_issued={False if decision is None else decision.direct_farm_action_issued}"
                ),
            ))
        return FixtureOracleResult(
            oracle_version=self.version,
            fixture_count=len(records),
            passed_fixture_count=sum(record.passed for record in records),
            family_counts=tuple(sorted(family_counts.items())),
            records=tuple(records),
        )

    def aggregate(self, results: Iterable[ScenarioOracleResult]) -> AggregateOracleResult:
        """Aggregate named binary checks for a later batch runner or baseline comparison."""
        materialized = tuple(results)
        metric_counts: Counter[str] = Counter()
        metric_totals: Counter[str] = Counter()
        for result in materialized:
            for name, value in result.metric_values().items():
                metric_totals[name] += 1
                metric_counts[name] += int(value)
        return AggregateOracleResult(
            oracle_version=self.version,
            scenario_count=len(materialized),
            fully_passing_scenario_count=sum(result.overall_passed for result in materialized),
            metrics=tuple(
                AggregateOracleMetric(name=name, passed=metric_counts[name], total=metric_totals[name])
                for name in sorted(metric_totals)
            ),
        )

    @staticmethod
    def _scenario_strata(scenario: FrozenBenchmarkScenario) -> Mapping[str, str]:
        """Return immutable scenario dimensions for mandatory disaggregated reporting."""
        return {
            "crop": scenario.identity.crop,
            "state": scenario.identity.state,
            "district": scenario.identity.district,
            "site_id": scenario.identity.site_id,
            "season": scenario.identity.season,
            "scenario_partition": (
                "anchor" if scenario.identity.scenario_id.startswith("ANCHOR_") else "supplement"
            ),
            "conditional_operation_availability": (
                "available"
                if scenario.retrievable_operation_passages
                else "unavailable"
            ),
            "natural_ndvi_weather_divergence": (
                "eligible"
                if (scenario.natural_signal_divergence or {}).get("candidate_status")
                == "eligible_natural_signal_divergence_candidate"
                else "not_eligible"
            ),
        }

    def aggregate_stratified(
        self,
        scenario_results: Iterable[tuple[FrozenBenchmarkScenario, ScenarioOracleResult]],
    ) -> StratifiedOracleResult:
        """Aggregate all oracle checks by frozen crop, geography, and evidence strata.

        The input is explicit pairs rather than bare results so a later batch
        runner cannot accidentally assign an evaluation to a different crop or
        district when producing a paper table.
        """
        materialized = tuple(scenario_results)
        groups: dict[tuple[str, str], list[ScenarioOracleResult]] = {}
        for scenario, result in materialized:
            if scenario.identity.scenario_id != result.scenario_id:
                raise ValueError(
                    "Stratified oracle aggregation received a scenario/result identity mismatch: "
                    f"{scenario.identity.scenario_id} != {result.scenario_id}"
                )
            for name, value in self._scenario_strata(scenario).items():
                groups.setdefault((name, value), []).append(result)
        strata: list[OracleStratumResult] = []
        for (name, value), results in sorted(groups.items()):
            aggregate = self.aggregate(results)
            strata.append(OracleStratumResult(
                stratum_name=name,
                stratum_value=value,
                scenario_count=aggregate.scenario_count,
                fully_passing_scenario_count=aggregate.fully_passing_scenario_count,
                metrics=aggregate.metrics,
            ))
        return StratifiedOracleResult(
            oracle_version=self.version,
            scenario_count=len(materialized),
            strata=tuple(strata),
        )
