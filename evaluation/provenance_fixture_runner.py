"""Evaluate stored provenance/alignment fixtures against A0 and A5.

This module intentionally stops at the integrity boundary.  It loads one real
frozen scenario, applies one labelled mutation only in memory, and records
whether A0 blocks it or A5 exposes it after omitting the alignment validator.
It never invokes downstream agents, the coordinator, or farmer-message
rendering with an invalid bundle.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from data.benchmark_loader import FrozenBenchmarkLoader, FrozenBenchmarkScenario, ScenarioIntegrityError
from evaluation.benchmark_systems import build_benchmark_system
from evaluation.provenance_fixture_oracle import evaluate_provenance_fixture_runs
from llm.benchmark_llm_client import BenchmarkLLMClient
from scripts.build_provenance_fixture_registry import (
    EVALUATION_ONLY_LABEL,
    REGISTRY_ROOT,
    canonical_sha256,
    validate_registry,
)


FULL_MAS_SYSTEM_ID = "A0"
PROVENANCE_ALIGNMENT_ABLATION_SYSTEM_ID = "A5"
SUPPORTED_SYSTEM_IDS = frozenset({FULL_MAS_SYSTEM_ID, PROVENANCE_ALIGNMENT_ABLATION_SYSTEM_ID})
_ALIGNMENT_AGENT = "crop_district_season_alignment_validator"
_PROVENANCE_AGENT = "evidence_provenance_agent"


@dataclass(frozen=True)
class ProvenanceFixtureRun:
    """Auditable paired A0/A5 outcome for one controlled invalid bundle."""

    fixture_id: str
    base_scenario_id: str
    fixture_type: str
    fixture_family: str
    target_layer: str
    a0_status: str
    a5_status: str
    a0_expected_match: bool
    a5_expected_match: bool
    a0_gate_claim_agents: Tuple[str, ...]
    a5_gate_claim_agents: Tuple[str, ...]
    direct_farm_action_issued: bool
    detail: str

    @property
    def expected_match(self) -> bool:
        return self.a0_expected_match and self.a5_expected_match and not self.direct_farm_action_issued

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "expected_match": self.expected_match}


@dataclass(frozen=True)
class ProvenanceFixtureEvaluationResult:
    """Paper-facing aggregate for the separate integrity-fixture protocol."""

    schema_version: str
    fixture_classification: str
    fixture_count: int
    passed_fixture_count: int
    a0_alignment_validator_blocked_count: int
    a5_alignment_validator_exposure_count: int
    shared_loader_payload_hash_blocked_count: int
    direct_farm_action_fixture_count: int
    records: Tuple[ProvenanceFixtureRun, ...]

    @property
    def all_passed(self) -> bool:
        return self.passed_fixture_count == self.fixture_count

    @property
    def a0_alignment_validator_block_rate(self) -> float:
        return self.a0_alignment_validator_blocked_count / 50 if self.fixture_count else 0.0

    @property
    def a5_alignment_validator_exposure_rate(self) -> float:
        return self.a5_alignment_validator_exposure_count / 50 if self.fixture_count else 0.0

    @property
    def shared_loader_payload_hash_block_rate(self) -> float:
        return self.shared_loader_payload_hash_blocked_count / 10 if self.fixture_count else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fixture_classification": self.fixture_classification,
            "fixture_count": self.fixture_count,
            "passed_fixture_count": self.passed_fixture_count,
            "all_passed": self.all_passed,
            "a0_alignment_validator_blocked_count": self.a0_alignment_validator_blocked_count,
            "a0_alignment_validator_block_rate": self.a0_alignment_validator_block_rate,
            "a5_alignment_validator_exposure_count": self.a5_alignment_validator_exposure_count,
            "a5_alignment_validator_exposure_rate": self.a5_alignment_validator_exposure_rate,
            "shared_loader_payload_hash_blocked_count": self.shared_loader_payload_hash_blocked_count,
            "shared_loader_payload_hash_block_rate": self.shared_loader_payload_hash_block_rate,
            "direct_farm_action_fixture_count": self.direct_farm_action_fixture_count,
            "records": [record.as_dict() for record in self.records],
        }


class ProvenanceFixtureRegistry:
    """Read-only access to checksum-verified evaluation-only fixture records."""

    def __init__(self, root: Path = REGISTRY_ROOT) -> None:
        self.root = root
        validate_registry(root)
        manifest_path = root / "provenance_fixture_manifest.csv"
        # Validation checks the complete manifest and every fixture checksum;
        # this read preserves its documented row order for reproducible runs.
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            self._manifest = tuple(csv.DictReader(handle))
        self._rows_by_id = {row["fixture_id"]: row for row in self._manifest}

    @property
    def fixture_ids(self) -> Tuple[str, ...]:
        return tuple(row["fixture_id"] for row in self._manifest)

    def get(self, fixture_id: str) -> Mapping[str, Any]:
        if fixture_id not in self._rows_by_id:
            raise KeyError(f"Unknown provenance fixture: {fixture_id}")
        path = self.root / "fixtures" / f"{fixture_id}.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("fixture_content_sha256") != canonical_sha256(fixture):
            raise ValueError(f"Fixture checksum mismatch: {fixture_id}")
        if fixture.get("fixture_classification") != EVALUATION_ONLY_LABEL:
            raise ValueError(f"Fixture lost evaluation-only classification: {fixture_id}")
        return fixture


class ProvenanceFixtureRunner:
    """Run paired integrity-boundary checks without constructing unsafe decisions."""

    def __init__(
        self,
        *,
        registry: Optional[ProvenanceFixtureRegistry] = None,
        loader: Optional[FrozenBenchmarkLoader] = None,
    ) -> None:
        self.registry = registry or ProvenanceFixtureRegistry()
        self.loader = loader or FrozenBenchmarkLoader()
        disabled_llm = BenchmarkLLMClient(enabled=False, required=False)
        self.a0 = build_benchmark_system(
            FULL_MAS_SYSTEM_ID,
            loader=self.loader,
            bounded_llm=disabled_llm,
        )
        self.a5 = build_benchmark_system(
            PROVENANCE_ALIGNMENT_ABLATION_SYSTEM_ID,
            loader=self.loader,
            bounded_llm=disabled_llm,
        )

    @staticmethod
    def _assert_base_identity(scenario: FrozenBenchmarkScenario, fixture: Mapping[str, Any]) -> None:
        base = fixture["base_scenario"]
        for field in ("scenario_id", "site_id", "crop", "state", "district", "season", "decision_date"):
            if str(getattr(scenario.identity, field)) != str(base[field]):
                raise ScenarioIntegrityError(
                    f"Fixture {fixture['fixture_id']} base identity mismatch for {field}"
                )

    @staticmethod
    def _apply_overlay(
        scenario: FrozenBenchmarkScenario,
        fixture: Mapping[str, Any],
    ) -> FrozenBenchmarkScenario:
        """Return an in-memory copy containing exactly the declared mutation."""
        overlay = fixture["overlay"]
        target_layer = overlay["target_layer"]
        field = overlay["field"]
        base_value = str(overlay["base_value"])
        counterfactual_value = str(overlay["counterfactual_value"])
        if target_layer == "regional_operation_plan_item":
            target_id = overlay["selector"]["plan_item_id"]
            replaced = False
            items = []
            for item in scenario.regional_operation_plan_items:
                if item.get("plan_item_id") != target_id:
                    items.append(item)
                    continue
                if str(item.get(field, "")) != base_value:
                    raise ScenarioIntegrityError(
                        f"Fixture {fixture['fixture_id']} base plan-item value changed for {field}"
                    )
                mutated = dict(item)
                mutated[field] = counterfactual_value
                items.append(MappingProxyType(mutated))
                replaced = True
            if not replaced:
                raise ScenarioIntegrityError(
                    f"Fixture {fixture['fixture_id']} target plan item is unavailable at runtime"
                )
            return replace(scenario, regional_operation_plan_items=tuple(items))
        if target_layer == "manifest":
            if str(scenario.manifest.get(field, "")) != base_value:
                raise ScenarioIntegrityError(
                    f"Fixture {fixture['fixture_id']} base manifest value changed for {field}"
                )
            manifest = dict(scenario.manifest)
            manifest[field] = counterfactual_value
            return replace(scenario, manifest=MappingProxyType(manifest))
        raise ValueError(f"Unsupported fixture target layer: {target_layer}")

    @staticmethod
    def _run_integrity_gates(workflow: Any, scenario: FrozenBenchmarkScenario) -> tuple[str, Tuple[str, ...], str]:
        """Run exactly the production gate node, never any downstream node."""
        try:
            output = workflow._gates_node({"scenario": scenario, "claims": (), "question": ""})
        except ScenarioIntegrityError as exc:
            return "blocked_by_alignment_validator", (), str(exc)
        claim_agents = tuple(claim.agent_name for claim in output["claims"])
        return "passed_integrity_gates", claim_agents, "No integrity gate rejected the controlled overlay."

    def _run_plan_item_fixture(
        self,
        scenario: FrozenBenchmarkScenario,
        fixture: Mapping[str, Any],
    ) -> ProvenanceFixtureRun:
        mutated = self._apply_overlay(scenario, fixture)
        a0_status, a0_agents, a0_detail = self._run_integrity_gates(self.a0, mutated)
        a5_raw_status, a5_agents, a5_detail = self._run_integrity_gates(self.a5, mutated)
        a5_status = (
            "exposed_past_omitted_alignment_validator"
            if a5_raw_status == "passed_integrity_gates"
            and _ALIGNMENT_AGENT not in a5_agents
            and _PROVENANCE_AGENT not in a5_agents
            else a5_raw_status
        )
        expected = fixture["expected"]
        return ProvenanceFixtureRun(
            fixture_id=fixture["fixture_id"],
            base_scenario_id=scenario.identity.scenario_id,
            fixture_type=fixture["fixture_type"],
            fixture_family=fixture["fixture_family"],
            target_layer=fixture["overlay"]["target_layer"],
            a0_status=a0_status,
            a5_status=a5_status,
            a0_expected_match=a0_status == expected["a0_status"],
            a5_expected_match=a5_status == expected["a5_status"],
            a0_gate_claim_agents=a0_agents,
            a5_gate_claim_agents=a5_agents,
            direct_farm_action_issued=False,
            detail=(
                "A0 gate result: " + a0_detail + " A5 gate result: " + a5_detail + " "
                "Evaluation stops at this boundary; no invalid bundle is sent to downstream agents, "
                "the coordinator, or the farmer renderer."
            ),
        )

    def _run_payload_hash_fixture(
        self,
        scenario: FrozenBenchmarkScenario,
        fixture: Mapping[str, Any],
    ) -> ProvenanceFixtureRun:
        """Check the shared loader verifier, which A5 cannot bypass."""
        # First establish that the unchanged frozen payload is verifiable.
        self.loader._verify_scenario_payloads(scenario.manifest)
        mutated = self._apply_overlay(scenario, fixture)
        try:
            self.loader._verify_scenario_payloads(mutated.manifest)
        except ScenarioIntegrityError as exc:
            detail = str(exc)
            status = "blocked_by_loader_payload_hash_verifier"
        else:  # pragma: no cover - would expose a critical integrity regression
            detail = "Loader accepted a counterfactual payload hash."
            status = "payload_hash_mutation_not_blocked"
        expected = fixture["expected"]
        return ProvenanceFixtureRun(
            fixture_id=fixture["fixture_id"],
            base_scenario_id=scenario.identity.scenario_id,
            fixture_type=fixture["fixture_type"],
            fixture_family=fixture["fixture_family"],
            target_layer=fixture["overlay"]["target_layer"],
            a0_status=status,
            a5_status=status,
            a0_expected_match=status == expected["a0_status"],
            a5_expected_match=status == expected["a5_status"],
            a0_gate_claim_agents=(),
            a5_gate_claim_agents=(),
            direct_farm_action_issued=False,
            detail=(
                "The shared frozen-loader raw-payload verifier runs before A0 or A5 workflow gates. " + detail
            ),
        )

    def run(self, fixture_id: str) -> ProvenanceFixtureRun:
        """Evaluate one stored fixture without altering a frozen scenario or source file."""
        fixture = self.registry.get(fixture_id)
        scenario = self.loader.load(fixture["base_scenario"]["scenario_id"], verify_raw_hashes=False)
        self._assert_base_identity(scenario, fixture)
        if fixture["overlay"]["target_layer"] == "regional_operation_plan_item":
            return self._run_plan_item_fixture(scenario, fixture)
        if fixture["overlay"]["target_layer"] == "manifest":
            return self._run_payload_hash_fixture(scenario, fixture)
        raise ValueError(f"Unsupported fixture target layer: {fixture['overlay']['target_layer']}")

    def run_all(self) -> Tuple[ProvenanceFixtureRun, ...]:
        return tuple(self.run(fixture_id) for fixture_id in self.registry.fixture_ids)


def summarize_provenance_fixture_runs(
    fixture_runs: Sequence[ProvenanceFixtureRun],
) -> ProvenanceFixtureEvaluationResult:
    """Aggregate pairwise A0/A5 evidence-boundary behaviour."""
    records = tuple(fixture_runs)
    if len(records) != 60:
        raise ValueError(f"Expected exactly 60 provenance fixture runs, received {len(records)}")
    if any(record.direct_farm_action_issued for record in records):
        raise ValueError("A provenance fixture attempted to issue a direct farm action")
    return ProvenanceFixtureEvaluationResult(
        schema_version="1.0",
        fixture_classification=EVALUATION_ONLY_LABEL,
        fixture_count=len(records),
        passed_fixture_count=sum(record.expected_match for record in records),
        a0_alignment_validator_blocked_count=sum(
            record.a0_status == "blocked_by_alignment_validator" for record in records
        ),
        a5_alignment_validator_exposure_count=sum(
            record.a5_status == "exposed_past_omitted_alignment_validator" for record in records
        ),
        shared_loader_payload_hash_blocked_count=sum(
            record.a0_status == "blocked_by_loader_payload_hash_verifier"
            and record.a5_status == "blocked_by_loader_payload_hash_verifier"
            for record in records
        ),
        direct_farm_action_fixture_count=sum(record.direct_farm_action_issued for record in records),
        records=records,
    )


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/provenance-gate-fixtures"),
        help="Directory for the paired A0/A5 fixture result artifact.",
    )
    args = parser.parse_args()
    runs = ProvenanceFixtureRunner().run_all()
    summary = summarize_provenance_fixture_runs(runs)
    oracle_result = evaluate_provenance_fixture_runs(runs)
    output_path = args.output_dir / "provenance_fixture_result.json"
    _atomic_json_write(output_path, summary.as_dict())
    oracle_path = args.output_dir / "provenance_fixture_oracle_result.json"
    _atomic_json_write(oracle_path, oracle_result.as_dict())
    print(json.dumps({
        "output_path": str(output_path.resolve()),
        "oracle_output_path": str(oracle_path.resolve()),
        "fixture_count": summary.fixture_count,
        "passed_fixture_count": summary.passed_fixture_count,
        "a0_alignment_validator_blocked_count": summary.a0_alignment_validator_blocked_count,
        "a5_alignment_validator_exposure_count": summary.a5_alignment_validator_exposure_count,
        "shared_loader_payload_hash_blocked_count": summary.shared_loader_payload_hash_blocked_count,
        "direct_farm_action_fixture_count": summary.direct_farm_action_fixture_count,
        "oracle_all_passed": oracle_result.all_passed,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
