"""Execute stored evaluation-only conflict fixtures against the real resolver.

The runner first loads the referenced frozen scenario.  It then applies only
the fixture's labelled claim overlay in memory; it never writes to or alters
the normal scenario registry, loader, or farmer-facing workflow.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple
from types import MappingProxyType

from agents.benchmark.base import BenchmarkDecision, ConflictRecord
from agents.benchmark.conflict_detection import ConflictDetectionAgent
from agents.benchmark.crop_district_season_alignment_validator import CropDistrictSeasonAlignmentValidatorAgent
from agents.benchmark.provenance_aware_coordinator import ProvenanceAwareCoordinatorAgent
from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario, ScenarioIntegrityError
from data.evidence_schema import ClaimDisposition, TypedEvidenceClaim
from scripts.build_conflict_fixture_registry import (
    EVALUATION_ONLY_LABEL,
    REGISTRY_ROOT,
    canonical_sha256,
    validate_registry,
)


FULL_RESOLVER_SYSTEM_ID = "A0"
CONFLICT_ABLATION_SYSTEM_ID = "A6"
_SUPPORTED_SYSTEM_IDS = frozenset({FULL_RESOLVER_SYSTEM_ID, CONFLICT_ABLATION_SYSTEM_ID})


@dataclass(frozen=True)
class ConflictFixtureRun:
    """Auditable outcome for one stored test-only fixture."""

    fixture_id: str
    base_scenario_id: str
    fixture_family: str
    system_id: str
    coordinator_resolution_enabled: bool
    status: str
    claims: Tuple[TypedEvidenceClaim, ...]
    fixture_conflicts: Tuple[ConflictRecord, ...]
    background_conflicts: Tuple[ConflictRecord, ...]
    conflicts: Tuple[ConflictRecord, ...]
    decision: Optional[BenchmarkDecision]
    fixture_resolution_record_count: int
    full_resolver_policy_match: bool
    expected_match: bool
    detail: str


@dataclass(frozen=True)
class ConflictAblationFixtureResult:
    """Outcome summary for the A6 resolver-withheld counterfactual run.

    ``expected_behavior`` deliberately differs from full-resolver policy
    compliance: A6 is correct only when it preserves detection and safety
    while withholding coordinator resolution.  The separate reference-policy
    fields make that intentional loss observable rather than disguising it as
    a generic failed test.
    """

    schema_version: str
    system_id: str
    coordinator_resolution_enabled: bool
    fixture_count: int
    expected_behavior_passed_fixture_count: int
    full_resolver_policy_passed_fixture_count: int
    coordinator_required_fixture_count: int
    detected_coordinator_fixture_count: int
    resolved_coordinator_fixture_count: int
    unresolved_coordinator_fixture_count: int
    direct_farm_action_fixture_count: int
    records: Tuple[ConflictFixtureRun, ...]

    @property
    def expected_behavior_passed(self) -> bool:
        return self.expected_behavior_passed_fixture_count == self.fixture_count

    @property
    def full_resolver_policy_compliance_rate(self) -> float:
        return (
            self.full_resolver_policy_passed_fixture_count / self.fixture_count
            if self.fixture_count
            else 0.0
        )

    @property
    def coordinator_detection_rate(self) -> float:
        return (
            self.detected_coordinator_fixture_count / self.coordinator_required_fixture_count
            if self.coordinator_required_fixture_count
            else 0.0
        )

    @property
    def coordinator_resolution_rate(self) -> float:
        return (
            self.resolved_coordinator_fixture_count / self.coordinator_required_fixture_count
            if self.coordinator_required_fixture_count
            else 0.0
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "system_id": self.system_id,
            "coordinator_resolution_enabled": self.coordinator_resolution_enabled,
            "fixture_count": self.fixture_count,
            "expected_behavior_passed_fixture_count": self.expected_behavior_passed_fixture_count,
            "expected_behavior_passed": self.expected_behavior_passed,
            "full_resolver_policy_passed_fixture_count": self.full_resolver_policy_passed_fixture_count,
            "full_resolver_policy_compliance_rate": self.full_resolver_policy_compliance_rate,
            "coordinator_required_fixture_count": self.coordinator_required_fixture_count,
            "detected_coordinator_fixture_count": self.detected_coordinator_fixture_count,
            "coordinator_detection_rate": self.coordinator_detection_rate,
            "resolved_coordinator_fixture_count": self.resolved_coordinator_fixture_count,
            "coordinator_resolution_rate": self.coordinator_resolution_rate,
            "unresolved_coordinator_fixture_count": self.unresolved_coordinator_fixture_count,
            "direct_farm_action_fixture_count": self.direct_farm_action_fixture_count,
            "records": [asdict(record) for record in self.records],
        }


class ConflictFixtureRegistry:
    """Read-only registry for the stored counterfactual fixture package."""

    def __init__(self, root: Path = REGISTRY_ROOT) -> None:
        self.root = root
        validate_registry(root)
        with (root / "conflict_fixture_manifest.csv").open(newline="", encoding="utf-8") as handle:
            self._manifest = tuple(csv.DictReader(handle))
        self._rows_by_id = {row["fixture_id"]: row for row in self._manifest}

    @property
    def fixture_ids(self) -> Tuple[str, ...]:
        return tuple(row["fixture_id"] for row in self._manifest)

    def get(self, fixture_id: str) -> Mapping[str, Any]:
        if fixture_id not in self._rows_by_id:
            raise KeyError(f"Unknown conflict fixture: {fixture_id}")
        path = self.root / "fixtures" / f"{fixture_id}.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("fixture_content_sha256") != canonical_sha256(fixture):
            raise ValueError(f"Fixture checksum mismatch: {fixture_id}")
        if fixture.get("fixture_classification") != EVALUATION_ONLY_LABEL:
            raise ValueError(f"Fixture lost evaluation-only classification: {fixture_id}")
        return fixture


class ConflictFixtureRunner:
    """Run controlled provenance cases through A0 or the A6 resolver ablation.

    A6 retains the real detector and all typed fixture claims, but deliberately
    passes no detected conflicts into the coordinator.  This mirrors the A6
    workflow boundary and makes the coordinator's contribution measurable
    without adding synthetic evidence to normal benchmark scenarios.
    """

    def __init__(
        self,
        *,
        registry: Optional[ConflictFixtureRegistry] = None,
        loader: Optional[FrozenBenchmarkLoader] = None,
        system_id: str = FULL_RESOLVER_SYSTEM_ID,
    ) -> None:
        if system_id not in _SUPPORTED_SYSTEM_IDS:
            raise ValueError(
                f"Unsupported fixture-evaluation system {system_id}; expected one of "
                f"{', '.join(sorted(_SUPPORTED_SYSTEM_IDS))}."
            )
        self.registry = registry or ConflictFixtureRegistry()
        self.loader = loader or FrozenBenchmarkLoader()
        self.system_id = system_id
        self.coordinator_resolution_enabled = system_id == FULL_RESOLVER_SYSTEM_ID
        self.detector = ConflictDetectionAgent()
        self.alignment = CropDistrictSeasonAlignmentValidatorAgent()
        self.coordinator = ProvenanceAwareCoordinatorAgent()

    @staticmethod
    def _assert_base_identity(
        scenario: FrozenBenchmarkScenario,
        fixture: Mapping[str, Any],
    ) -> None:
        expected = fixture["base_scenario"]
        actual = scenario.identity
        for field in ("scenario_id", "site_id", "crop", "state", "district", "season", "decision_date"):
            if str(getattr(actual, field)) != str(expected[field]):
                raise ScenarioIntegrityError(
                    f"Fixture {fixture['fixture_id']} base identity mismatch for {field}"
                )

    @staticmethod
    def _claims(fixture: Mapping[str, Any]) -> Tuple[TypedEvidenceClaim, ...]:
        base_id = fixture["base_scenario"]["scenario_id"]
        claims = []
        for blueprint in fixture.get("claims", []):
            values = dict(blueprint)
            values.pop("claim_role", None)
            values["scenario_id"] = base_id
            claims.append(TypedEvidenceClaim(**values))
        return tuple(claims)

    @staticmethod
    def _roles(
        ids: Sequence[str], claims: Sequence[TypedEvidenceClaim], fixture: Mapping[str, Any]
    ) -> set[str]:
        by_id = {claim.claim_id: fixture["claims"][index]["claim_role"] for index, claim in enumerate(claims)}
        return {by_id[claim_id] for claim_id in ids if claim_id in by_id}

    def _reference_policy_match(
        self,
        fixture: Mapping[str, Any],
        claims: Sequence[TypedEvidenceClaim],
        fixture_conflicts: Sequence[ConflictRecord],
        decision: BenchmarkDecision,
        fixture_resolution_records: Sequence[Any],
    ) -> bool:
        """Evaluate the fixture against the unablated A0 policy contract."""
        expected = fixture["expected"]
        matched = len(fixture_conflicts) == int(expected["conflict_count"])
        matched &= decision.direct_farm_action_issued is False

        if fixture["fixture_family"] == "coordinator_resolution":
            if len(fixture_resolution_records) != 1:
                return False
            record = fixture_resolution_records[0]
            matched &= record.status == expected["resolution_status"]
            if "accepted_roles" in expected:
                matched &= self._roles(record.accepted_claim_ids, claims, fixture) == set(expected["accepted_roles"])
            if "rejected_roles" in expected:
                matched &= self._roles(record.rejected_claim_ids, claims, fixture) == set(expected["rejected_roles"])
            if "deferred_roles" in expected:
                matched &= self._roles(record.deferred_claim_ids, claims, fixture) == set(expected["deferred_roles"])
            return bool(matched)

        if fixture["fixture_family"] == "negative_control_no_comparable_conflict":
            matched &= not fixture_resolution_records
            matched &= decision.decision_status == expected["decision_status"]
            return bool(matched)

        raise ValueError(f"Unsupported fixture family: {fixture['fixture_family']}")

    def _expected_mode_match(
        self,
        fixture: Mapping[str, Any],
        fixture_conflicts: Sequence[ConflictRecord],
        decision: BenchmarkDecision,
        fixture_resolution_records: Sequence[Any],
        *,
        full_resolver_policy_match: bool,
    ) -> bool:
        """Check A0 policy, or A6's deliberately resolution-withheld policy."""
        if self.coordinator_resolution_enabled:
            return full_resolver_policy_match

        expected = fixture["expected"]
        matched = len(fixture_conflicts) == int(expected["conflict_count"])
        matched &= decision.direct_farm_action_issued is False
        if fixture["fixture_family"] == "coordinator_resolution":
            # A6 must still receive the detector's eligible conflict, but the
            # coordinator intentionally sees an empty conflict set.
            matched &= not fixture_resolution_records
        elif fixture["fixture_family"] == "negative_control_no_comparable_conflict":
            matched &= not fixture_resolution_records
            matched &= decision.decision_status == expected["decision_status"]
        else:
            raise ValueError(f"Unsupported fixture family: {fixture['fixture_family']}")
        return bool(matched)

    def _run_integrity_fixture(
        self,
        scenario: FrozenBenchmarkScenario,
        fixture: Mapping[str, Any],
    ) -> ConflictFixtureRun:
        overlay = fixture["integrity_overlay"]
        field = overlay["field"]
        actual_value = scenario.manifest.get(field, "")
        if str(actual_value) != str(overlay["base_value"]):
            raise ScenarioIntegrityError(
                f"Fixture {fixture['fixture_id']} does not match its immutable base value for {field}"
            )
        if str(actual_value) == str(overlay["counterfactual_value"]):
            raise ScenarioIntegrityError(
                f"Fixture {fixture['fixture_id']} does not contain a real integrity mutation for {field}"
            )
        mutated_manifest = dict(scenario.manifest)
        mutated_manifest[field] = str(overlay["counterfactual_value"])
        try:
            if field in {"crop", "state", "district", "decision_date"}:
                # Run the production alignment gate over an in-memory manifest
                # mutation. The immutable scenario identity remains unchanged.
                mutated = replace(scenario, manifest=MappingProxyType(mutated_manifest))
                gate_claim = self.alignment.run(mutated)[0]
                if gate_claim.disposition != ClaimDisposition.BLOCKED:
                    raise AssertionError(
                        f"Alignment gate did not block counterfactual {field} mutation"
                    )
            elif field.endswith("sha256"):
                # Reuse the production loader's exact raw-payload verifier;
                # the synthetic hash is never written into a frozen manifest.
                self.loader._verify_scenario_payloads(mutated_manifest)
                raise AssertionError(f"Payload verifier did not block counterfactual {field} mutation")
            else:
                raise AssertionError(f"Unsupported integrity fixture field: {field}")
        except ScenarioIntegrityError:
            pass
        return ConflictFixtureRun(
            fixture_id=fixture["fixture_id"],
            base_scenario_id=scenario.identity.scenario_id,
            fixture_family=fixture["fixture_family"],
            system_id=self.system_id,
            coordinator_resolution_enabled=self.coordinator_resolution_enabled,
            status="blocked_before_conflict_detection_and_coordination",
            claims=(),
            fixture_conflicts=(),
            background_conflicts=(),
            conflicts=(),
            decision=None,
            fixture_resolution_record_count=0,
            full_resolver_policy_match=(
                fixture["expected"]["integrity_status"]
                == "blocked_before_conflict_detection_and_coordination"
            ),
            expected_match=(
                fixture["expected"]["integrity_status"]
                == "blocked_before_conflict_detection_and_coordination"
            ),
            detail=(
                f"Production integrity validation rejected the controlled {field} mismatch before "
                "conflict detection or a coordinator decision could be created."
            ),
        )

    def run(self, fixture_id: str, *, verify_raw_hashes: bool = False) -> ConflictFixtureRun:
        """Run one fixture without modifying the base frozen scenario."""
        fixture = self.registry.get(fixture_id)
        scenario = self.loader.load(
            fixture["base_scenario"]["scenario_id"], verify_raw_hashes=verify_raw_hashes
        )
        self._assert_base_identity(scenario, fixture)
        if fixture["fixture_family"] == "pre_resolution_integrity_rejection":
            return self._run_integrity_fixture(scenario, fixture)

        claims = self._claims(fixture)
        conflicts = self.detector.detect(scenario, claims)
        coordinator_conflicts = conflicts if self.coordinator_resolution_enabled else ()
        decision = self.coordinator.coordinate(scenario, claims, (), coordinator_conflicts)
        fixture_target = fixture.get("decision_target", "")
        fixture_conflicts = tuple(
            conflict
            for conflict in conflicts
            if fixture_target and conflict.evidence.get("decision_target", "") == fixture_target
        )
        background_conflicts = tuple(
            conflict for conflict in conflicts if conflict not in fixture_conflicts
        )
        fixture_resolution_records = tuple(
            record
            for record in decision.conflict_resolution_records
            if fixture_target and record.decision_target == fixture_target
        )
        full_resolver_policy_match = self._reference_policy_match(
            fixture, claims, fixture_conflicts, decision, fixture_resolution_records
        )
        expected_match = self._expected_mode_match(
            fixture,
            fixture_conflicts,
            decision,
            fixture_resolution_records,
            full_resolver_policy_match=full_resolver_policy_match,
        )
        if self.coordinator_resolution_enabled:
            status = "passed" if expected_match else "failed_expected_policy_check"
            detail = (
                "Fixture ran through the typed-claim conflict detector and deterministic coordinator; "
                "it was not added to the normal farmer-facing workflow."
            )
        else:
            status = "passed_expected_ablation_behavior" if expected_match else "failed_expected_ablation_check"
            detail = (
                "Fixture ran through the real typed-claim conflict detector, but A6 deliberately passed no "
                "detected conflicts into the coordinator. It was not added to the normal farmer-facing workflow."
            )

        return ConflictFixtureRun(
            fixture_id=fixture["fixture_id"],
            base_scenario_id=scenario.identity.scenario_id,
            fixture_family=fixture["fixture_family"],
            system_id=self.system_id,
            coordinator_resolution_enabled=self.coordinator_resolution_enabled,
            status=status,
            claims=claims,
            fixture_conflicts=fixture_conflicts,
            background_conflicts=background_conflicts,
            conflicts=conflicts,
            decision=decision,
            fixture_resolution_record_count=len(fixture_resolution_records),
            full_resolver_policy_match=bool(full_resolver_policy_match),
            expected_match=bool(expected_match),
            detail=detail,
        )

    def run_all(self, *, verify_raw_hashes: bool = False) -> Tuple[ConflictFixtureRun, ...]:
        return tuple(
            self.run(fixture_id, verify_raw_hashes=verify_raw_hashes)
            for fixture_id in self.registry.fixture_ids
        )


def summarize_a6_conflict_ablation(
    fixture_runs: Sequence[ConflictFixtureRun],
) -> ConflictAblationFixtureResult:
    """Summarize A6 without calling its intentional non-resolution a failure.

    The output retains the counterfactual A0-policy match rate alongside A6's
    expected-ablation conformance.  A paper can therefore state precisely
    that the detector still saw eligible conflicts while coordinator
    resolution fell from the A0 reference to zero by design.
    """
    runs = tuple(fixture_runs)
    if not runs:
        raise ValueError("A6 conflict-ablation summary requires at least one fixture run.")
    if any(run.system_id != CONFLICT_ABLATION_SYSTEM_ID for run in runs):
        raise ValueError("A6 conflict-ablation summary received a non-A6 fixture run.")
    if any(run.coordinator_resolution_enabled for run in runs):
        raise ValueError("A6 conflict-ablation summary received a resolver-enabled fixture run.")

    coordinator_runs = tuple(run for run in runs if run.fixture_family == "coordinator_resolution")
    detected = sum(1 for run in coordinator_runs if run.fixture_conflicts)
    resolved = sum(1 for run in coordinator_runs if run.fixture_resolution_record_count > 0)
    direct_actions = sum(
        1 for run in runs if run.decision is not None and run.decision.direct_farm_action_issued
    )
    return ConflictAblationFixtureResult(
        schema_version="1.0",
        system_id=CONFLICT_ABLATION_SYSTEM_ID,
        coordinator_resolution_enabled=False,
        fixture_count=len(runs),
        expected_behavior_passed_fixture_count=sum(run.expected_match for run in runs),
        full_resolver_policy_passed_fixture_count=sum(run.full_resolver_policy_match for run in runs),
        coordinator_required_fixture_count=len(coordinator_runs),
        detected_coordinator_fixture_count=detected,
        resolved_coordinator_fixture_count=resolved,
        unresolved_coordinator_fixture_count=len(coordinator_runs) - resolved,
        direct_farm_action_fixture_count=direct_actions,
        records=runs,
    )
