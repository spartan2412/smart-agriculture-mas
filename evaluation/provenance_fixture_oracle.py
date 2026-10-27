"""Independent oracle for evaluation-only provenance/alignment fixtures.

The normal 18-check benchmark oracle is protocol-frozen for the 300 real
scenarios.  This separate evaluator avoids changing that protocol while
making the A0-versus-A5 integrity-boundary experiment reproducible.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Tuple


PROVENANCE_FIXTURE_ORACLE_VERSION = "1.0"
_EXPECTED_TYPE_COUNTS = {
    "plan_item_crop_scope_mismatch": 10,
    "plan_item_district_scope_mismatch": 10,
    "plan_item_season_scope_mismatch": 10,
    "plan_item_decision_date_scope_mismatch": 10,
    "plan_item_scenario_binding_mismatch": 10,
    "weather_payload_hash_mismatch": 10,
}


@dataclass(frozen=True)
class ProvenanceFixtureOracleRecord:
    """One paired A0/A5 integrity-boundary result from a controlled fixture."""

    fixture_id: str
    base_scenario_id: str
    fixture_type: str
    a0_status: str
    a5_status: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProvenanceFixtureOracleResult:
    """Aggregate safety result; never an agricultural-outcome metric."""

    oracle_version: str
    fixture_count: int
    passed_fixture_count: int
    type_counts: Tuple[Tuple[str, int], ...]
    a0_alignment_validator_blocked_count: int
    a5_alignment_validator_exposure_count: int
    shared_loader_payload_hash_blocked_count: int
    direct_farm_action_fixture_count: int
    records: Tuple[ProvenanceFixtureOracleRecord, ...]

    @property
    def coverage_passed(self) -> bool:
        return dict(self.type_counts) == _EXPECTED_TYPE_COUNTS

    @property
    def all_passed(self) -> bool:
        return (
            self.coverage_passed
            and self.fixture_count == 60
            and self.passed_fixture_count == self.fixture_count
            and self.a0_alignment_validator_blocked_count == 50
            and self.a5_alignment_validator_exposure_count == 50
            and self.shared_loader_payload_hash_blocked_count == 10
            and self.direct_farm_action_fixture_count == 0
            and all(record.passed for record in self.records)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "oracle_version": self.oracle_version,
            "fixture_count": self.fixture_count,
            "passed_fixture_count": self.passed_fixture_count,
            "coverage_passed": self.coverage_passed,
            "all_passed": self.all_passed,
            "type_counts": dict(self.type_counts),
            "a0_alignment_validator_blocked_count": self.a0_alignment_validator_blocked_count,
            "a5_alignment_validator_exposure_count": self.a5_alignment_validator_exposure_count,
            "shared_loader_payload_hash_blocked_count": self.shared_loader_payload_hash_blocked_count,
            "direct_farm_action_fixture_count": self.direct_farm_action_fixture_count,
            "records": [record.as_dict() for record in self.records],
        }


def evaluate_provenance_fixture_runs(
    fixture_runs: Iterable[Any],
) -> ProvenanceFixtureOracleResult:
    """Independently check fixed coverage and expected A0/A5 outcomes.

    The fixture runner stops before downstream agents and the coordinator, so
    this oracle measures only the documented block/exposure policy and the
    zero-direct-action boundary.
    """
    records: list[ProvenanceFixtureOracleRecord] = []
    type_counts: Counter[str] = Counter()
    a0_blocks = 0
    a5_exposures = 0
    payload_blocks = 0
    direct_actions = 0
    for fixture_run in fixture_runs:
        fixture_type = str(fixture_run.fixture_type)
        type_counts[fixture_type] += 1
        a0_status = str(fixture_run.a0_status)
        a5_status = str(fixture_run.a5_status)
        direct_action = bool(fixture_run.direct_farm_action_issued)
        passed = bool(fixture_run.expected_match) and not direct_action
        a0_blocks += a0_status == "blocked_by_alignment_validator"
        a5_exposures += a5_status == "exposed_past_omitted_alignment_validator"
        payload_blocks += (
            a0_status == "blocked_by_loader_payload_hash_verifier"
            and a5_status == "blocked_by_loader_payload_hash_verifier"
        )
        direct_actions += direct_action
        records.append(ProvenanceFixtureOracleRecord(
            fixture_id=str(fixture_run.fixture_id),
            base_scenario_id=str(fixture_run.base_scenario_id),
            fixture_type=fixture_type,
            a0_status=a0_status,
            a5_status=a5_status,
            passed=passed,
            detail=(
                f"a0_expected_match={fixture_run.a0_expected_match}; "
                f"a5_expected_match={fixture_run.a5_expected_match}; "
                f"direct_farm_action_issued={direct_action}"
            ),
        ))
    return ProvenanceFixtureOracleResult(
        oracle_version=PROVENANCE_FIXTURE_ORACLE_VERSION,
        fixture_count=len(records),
        passed_fixture_count=sum(record.passed for record in records),
        type_counts=tuple(sorted(type_counts.items())),
        a0_alignment_validator_blocked_count=a0_blocks,
        a5_alignment_validator_exposure_count=a5_exposures,
        shared_loader_payload_hash_blocked_count=payload_blocks,
        direct_farm_action_fixture_count=direct_actions,
        records=tuple(records),
    )
