"""Verify release reproducibility without changing accepted benchmark artifacts.

Phase 9 uses this module *after* a new clean-checkout run has been persisted
to a different directory.  It deliberately does not replay a workflow, alter
an historical result, or grade agricultural correctness.  It verifies three
different, explicit properties:

* the reference run's frozen source/code artifacts still hash to the recorded
  values;
* the new run covers exactly the same frozen scenario population and retains
  every structural-oracle outcome; and
* deterministic traces (E0) and bounded-selector evidence selections (E1)
  reproduce after excluding non-deterministic timing/RSS measurements.

This distinction matters: elapsed time and peak RSS are operational telemetry,
not semantic evidence.  A mismatch in an admitted source, claim, condition,
selection, citation, conflict record, or farmer-facing message is never
silently normalised away.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping, Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NORMAL_SCENARIO_COUNT = 300
EXPECTED_BOUNDED_LLM_ROLES = frozenset(
    {
        "weather_context_agent",
        "soil_context_agent",
        "satellite_ndvi_context_agent",
        "market_evidence_agent",
        "fertilizer_baseline_agent",
        "official_operations_rag_agent",
        "provenance_aware_coordinator_agent",
        "farmer_explanation_citation_agent",
    }
)


class ReproducibilityVerificationError(ValueError):
    """Raised when a result pair cannot support a release reproducibility claim."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ReproducibilityVerificationError(f"Required JSON artifact is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReproducibilityVerificationError(f"Invalid JSON artifact: {path}") from exc


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReproducibilityVerificationError(f"{label} must be a JSON object.")
    return value


def _normalised_claim_metadata(claim: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    metadata = claim.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    bounded = metadata.get("bounded_llm")
    return bounded if isinstance(bounded, Mapping) else None


def _model_selection_view(artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return every bounded selection without timing/error-text noise.

    The bounded selector is allowed only to rank supplied IDs.  Therefore its
    selected IDs, role, prompt hash, and policy are reproducibility-critical;
    elapsed time and backend implementation error strings are not.
    """
    benchmark_run = _mapping(artifact.get("benchmark_run"), "scenario benchmark_run")
    claims = benchmark_run.get("claims")
    if not isinstance(claims, list):
        raise ReproducibilityVerificationError("Scenario benchmark_run.claims must be a list.")
    selections: list[Mapping[str, Any]] = []
    for claim in claims:
        claim_object = _mapping(claim, "benchmark claim")
        bounded = _normalised_claim_metadata(claim_object)
        if bounded is None:
            continue
        selections.append(
            {
                "agent_name": str(claim_object.get("agent_name", "")),
                "claim_id": str(claim_object.get("claim_id", "")),
                "status": bounded.get("status"),
                "selected_fact_ids": list(bounded.get("selected_fact_ids", ())),
                "prompt_sha256": bounded.get("prompt_sha256"),
                "prompt_template_version": bounded.get("prompt_template_version"),
                "selection_contract_version": bounded.get("selection_contract_version"),
                "candidate_packaging_version": bounded.get("candidate_packaging_version"),
                "request_sufficiency": bounded.get("request_sufficiency"),
                "selection_policy": bounded.get("selection_policy"),
                "selection_is_safety_non_authoritative": bounded.get(
                    "selection_is_safety_non_authoritative"
                ),
            }
        )
    return sorted(selections, key=lambda row: (str(row["agent_name"]), str(row["claim_id"])))


def _semantic_trace_view(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    """Retain all semantically relevant output and exclude runtime telemetry only."""
    identity = _mapping(artifact.get("scenario_identity"), "scenario_identity")
    benchmark_run = _mapping(artifact.get("benchmark_run"), "benchmark_run")
    oracle = _mapping(artifact.get("scenario_oracle_result"), "scenario_oracle_result")
    return {
        "scenario_identity": identity,
        "benchmark_run": benchmark_run,
        "scenario_oracle_result": oracle,
    }


def _farmer_decision_view(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    benchmark_run = _mapping(artifact.get("benchmark_run"), "benchmark_run")
    return {
        "farmer_message": benchmark_run.get("farmer_message"),
        "decision": benchmark_run.get("decision"),
        "retrieved_passages": benchmark_run.get("retrieved_passages"),
        "conflicts": benchmark_run.get("conflicts"),
    }


@dataclass(frozen=True)
class ArtifactHashCheck:
    """One reference artifact compared with the live frozen repository file."""

    path: str
    expected_sha256: str
    observed_sha256: str
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioReproducibilityRecord:
    """Per-scenario semantic comparison, deliberately excluding runtime telemetry."""

    scenario_id: str
    structural_fingerprint_match: bool
    oracle_checks_match: bool
    semantic_trace_match: bool
    farmer_decision_match: bool
    bounded_selection_match: Optional[bool]
    reference_structural_fingerprint: str
    reproduced_structural_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunReproducibilityResult:
    """Full comparison for one configuration and its clean-checkout rerun."""

    configuration_id: str
    reference_directory: str
    reproduction_directory: str
    expected_scenario_count: int
    scenario_count: int
    reference_artifact_checks: tuple[ArtifactHashCheck, ...]
    artifact_hashes_match: bool
    scenario_population_match: bool
    structural_fingerprint_match_count: int
    oracle_check_match_count: int
    semantic_trace_match_count: int
    farmer_decision_match_count: int
    bounded_selection_match_count: Optional[int]
    expected_bounded_selection_count: Optional[int]
    all_required_checks_passed: bool
    records: tuple[ScenarioReproducibilityRecord, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "reference_artifact_checks": [check.as_dict() for check in self.reference_artifact_checks],
            "records": [record.as_dict() for record in self.records],
        }


@dataclass(frozen=True)
class FixtureReproducibilityResult:
    """Exact reproducibility result for one 60-record policy-fixture suite."""

    fixture_suite: str
    reference_directory: str
    reproduction_directory: str
    fixture_count: int
    all_passed: bool
    semantic_result_match: bool
    normalised_policy_trace_match: bool
    all_required_checks_passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_reference_artifact_hashes(
    reference_manifest: Mapping[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> tuple[ArtifactHashCheck, ...]:
    """Verify every source/code hash embedded in a persisted reference manifest."""
    protocol = _mapping(reference_manifest.get("protocol"), "reference manifest protocol")
    rows = protocol.get("verified_artifacts")
    if not isinstance(rows, list) or not rows:
        raise ReproducibilityVerificationError("Reference manifest has no verified frozen artifacts.")
    checks: list[ArtifactHashCheck] = []
    for raw in rows:
        row = _mapping(raw, "verified artifact row")
        relative = row.get("path")
        expected = row.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ReproducibilityVerificationError("Reference verified-artifact row is malformed.")
        path = (project_root / relative).resolve()
        if project_root not in path.parents or not path.is_file():
            observed = "missing_or_outside_project"
        else:
            observed = _sha256_file(path)
        checks.append(
            ArtifactHashCheck(
                path=relative,
                expected_sha256=expected,
                observed_sha256=observed,
                passed=observed == expected,
            )
        )
    return tuple(checks)


def verify_fixture_reproducibility(
    *,
    fixture_suite: str,
    reference_directory: Path | str,
    reproduction_directory: Path | str,
) -> FixtureReproducibilityResult:
    """Compare one controlled 60-fixture policy suite without running it.

    Fixture traces are evaluation-only counterfactuals.  Their policy-facing
    fields must be exactly equal.  The normalisation excludes only additive
    reporting fields introduced after the historical reference (for example,
    a system label or a derived resolution-count field) and narrative wording.
    It does not exclude claims, conflicts, decisions, or expected status.
    """
    files = {
        "conflict": ("fixture_oracle_result.json", "conflict_fixture_runs.json"),
        "provenance": ("provenance_fixture_oracle_result.json", "provenance_fixture_result.json"),
    }
    if fixture_suite not in files:
        raise ReproducibilityVerificationError("Fixture suite must be 'conflict' or 'provenance'.")
    reference = Path(reference_directory).resolve()
    reproduction = Path(reproduction_directory).resolve()
    semantic_name, trace_name = files[fixture_suite]
    reference_semantic = _mapping(_read_json(reference / semantic_name), "reference fixture result")
    reproduction_semantic = _mapping(_read_json(reproduction / semantic_name), "reproduced fixture result")
    reference_trace = _read_json(reference / trace_name)
    reproduction_trace = _read_json(reproduction / trace_name)
    fixture_count = reference_semantic.get("fixture_count")
    if fixture_count != 60 or reproduction_semantic.get("fixture_count") != 60:
        raise ReproducibilityVerificationError("A Phase 9 fixture reproduction must contain exactly 60 records.")
    all_passed = reference_semantic.get("all_passed") is True and reproduction_semantic.get("all_passed") is True
    semantic_match = reference_semantic == reproduction_semantic
    trace_match = (
        _normalised_fixture_policy_trace(reference_trace) == _normalised_fixture_policy_trace(reproduction_trace)
        if fixture_suite == "conflict"
        else reference_trace == reproduction_trace
    )
    return FixtureReproducibilityResult(
        fixture_suite=fixture_suite,
        reference_directory=str(reference),
        reproduction_directory=str(reproduction),
        fixture_count=60,
        all_passed=all_passed,
        semantic_result_match=semantic_match,
        normalised_policy_trace_match=trace_match,
        all_required_checks_passed=all_passed and semantic_match and trace_match,
    )


def _normalised_fixture_policy_trace(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Keep only immutable decision-policy fields from a 60-fixture trace.

    Older accepted conflict fixtures predate later additive reporting fields.
    Comparing raw JSON would therefore flag an unchanged policy as different.
    This is a deliberately closed list: a new policy-bearing field must be
    added here explicitly and covered by a regression test.
    """
    if not isinstance(value, list):
        raise ReproducibilityVerificationError("Fixture trace must be a JSON array.")
    required_fields = (
        "fixture_id",
        "base_scenario_id",
        "fixture_family",
        "status",
        "expected_match",
        "claims",
        "conflicts",
        "fixture_conflicts",
        "background_conflicts",
        "decision",
    )
    normalised: list[Mapping[str, Any]] = []
    for item in value:
        row = _mapping(item, "fixture trace record")
        missing = [field for field in required_fields if field not in row]
        if missing:
            raise ReproducibilityVerificationError(
                f"Fixture trace record lacks policy fields: {', '.join(missing)}"
            )
        normalised.append({field: row[field] for field in required_fields})
    return tuple(sorted(normalised, key=lambda row: str(row["fixture_id"])))


def _scenario_artifacts(directory: Path) -> dict[str, Mapping[str, Any]]:
    scenario_directory = directory / "scenarios"
    if not scenario_directory.is_dir():
        raise ReproducibilityVerificationError(f"Run has no scenario artifact directory: {scenario_directory}")
    artifacts: dict[str, Mapping[str, Any]] = {}
    for path in sorted(scenario_directory.glob("*.json")):
        artifact = _mapping(_read_json(path), f"scenario artifact {path.name}")
        identity = _mapping(artifact.get("scenario_identity"), f"scenario identity in {path.name}")
        scenario_id = identity.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise ReproducibilityVerificationError(f"Scenario artifact has no scenario_id: {path}")
        if scenario_id != path.stem or scenario_id in artifacts:
            raise ReproducibilityVerificationError(f"Scenario artifact identity/path is not unique: {path}")
        artifacts[scenario_id] = artifact
    return artifacts


def _assert_completed_manifest(manifest: Mapping[str, Any], label: str, configuration_id: str) -> None:
    if manifest.get("status") != "completed":
        raise ReproducibilityVerificationError(f"{label} run is not completed.")
    if manifest.get("configuration_id") != configuration_id:
        raise ReproducibilityVerificationError(
            f"{label} configuration differs: expected {configuration_id}, got {manifest.get('configuration_id')}"
        )
    git = _mapping(manifest.get("git"), f"{label} git metadata")
    if git.get("clean_at_start") is not True:
        raise ReproducibilityVerificationError(f"{label} was not started from a clean committed Git checkout.")


def verify_run_reproducibility(
    *,
    configuration_id: str,
    reference_directory: Path | str,
    reproduction_directory: Path | str,
    project_root: Path | str = PROJECT_ROOT,
    expected_scenario_count: int = EXPECTED_NORMAL_SCENARIO_COUNT,
) -> RunReproducibilityResult:
    """Compare an accepted run to a later clean-checkout reproduction.

    E0 requires an exact semantic trace for every scenario.  E1 additionally
    requires exact bounded-selection records for each expected role.  Both use
    exact 18-check oracle/fingerprint equality; neither compares runtime
    latency/RSS, timestamps, run-directory names, or Git commits.
    """
    if configuration_id not in {"E0", "E1"}:
        raise ReproducibilityVerificationError("Phase 9 supports accepted E0 and E1 only.")
    root = Path(project_root).resolve()
    reference = Path(reference_directory).resolve()
    reproduction = Path(reproduction_directory).resolve()
    reference_manifest = _mapping(_read_json(reference / "run_manifest.json"), "reference run manifest")
    reproduction_manifest = _mapping(_read_json(reproduction / "run_manifest.json"), "reproduction run manifest")
    _assert_completed_manifest(reference_manifest, "Reference", configuration_id)
    _assert_completed_manifest(reproduction_manifest, "Reproduction", configuration_id)

    artifact_checks = verify_reference_artifact_hashes(reference_manifest, project_root=root)
    reference_artifacts = _scenario_artifacts(reference)
    reproduction_artifacts = _scenario_artifacts(reproduction)
    reference_ids = tuple(sorted(reference_artifacts))
    reproduction_ids = tuple(sorted(reproduction_artifacts))
    population_match = (
        len(reference_ids) == expected_scenario_count
        and len(reproduction_ids) == expected_scenario_count
        and reference_ids == reproduction_ids
    )
    if not population_match:
        raise ReproducibilityVerificationError(
            "Reference and reproduction do not contain the same expected frozen scenario population."
        )

    records: list[ScenarioReproducibilityRecord] = []
    for scenario_id in reference_ids:
        ref = reference_artifacts[scenario_id]
        rerun = reproduction_artifacts[scenario_id]
        ref_oracle = _mapping(ref.get("scenario_oracle_result"), "reference scenario oracle")
        rerun_oracle = _mapping(rerun.get("scenario_oracle_result"), "reproduced scenario oracle")
        ref_structural = str(ref_oracle.get("structural_fingerprint", ""))
        rerun_structural = str(rerun_oracle.get("structural_fingerprint", ""))
        selections_match: Optional[bool] = None
        if configuration_id == "E1":
            selections_match = _model_selection_view(ref) == _model_selection_view(rerun)
        records.append(
            ScenarioReproducibilityRecord(
                scenario_id=scenario_id,
                structural_fingerprint_match=ref_structural == rerun_structural,
                oracle_checks_match=ref_oracle.get("checks") == rerun_oracle.get("checks"),
                semantic_trace_match=_semantic_trace_view(ref) == _semantic_trace_view(rerun),
                farmer_decision_match=_farmer_decision_view(ref) == _farmer_decision_view(rerun),
                bounded_selection_match=selections_match,
                reference_structural_fingerprint=ref_structural,
                reproduced_structural_fingerprint=rerun_structural,
            )
        )

    bounded_matches: Optional[int] = None
    bounded_expected: Optional[int] = None
    if configuration_id == "E1":
        bounded_matches = sum(record.bounded_selection_match is True for record in records)
        bounded_expected = len(records)
        for artifact in reproduction_artifacts.values():
            actual_roles = {
                str(item["agent_name"])
                for item in _model_selection_view(artifact)
                if item.get("status") == "accepted"
            }
            if not EXPECTED_BOUNDED_LLM_ROLES.issubset(actual_roles):
                raise ReproducibilityVerificationError(
                    "E1 reproduction lacks an accepted bounded selection for one or more frozen roles."
                )

    structural_matches = sum(record.structural_fingerprint_match for record in records)
    oracle_matches = sum(record.oracle_checks_match for record in records)
    semantic_matches = sum(record.semantic_trace_match for record in records)
    farmer_matches = sum(record.farmer_decision_match for record in records)
    all_required = (
        all(check.passed for check in artifact_checks)
        and structural_matches == expected_scenario_count
        and oracle_matches == expected_scenario_count
        and semantic_matches == expected_scenario_count
        and farmer_matches == expected_scenario_count
        and (configuration_id == "E0" or bounded_matches == expected_scenario_count)
    )
    return RunReproducibilityResult(
        configuration_id=configuration_id,
        reference_directory=str(reference),
        reproduction_directory=str(reproduction),
        expected_scenario_count=expected_scenario_count,
        scenario_count=len(records),
        reference_artifact_checks=artifact_checks,
        artifact_hashes_match=all(check.passed for check in artifact_checks),
        scenario_population_match=population_match,
        structural_fingerprint_match_count=structural_matches,
        oracle_check_match_count=oracle_matches,
        semantic_trace_match_count=semantic_matches,
        farmer_decision_match_count=farmer_matches,
        bounded_selection_match_count=bounded_matches,
        expected_bounded_selection_count=bounded_expected,
        all_required_checks_passed=all_required,
        records=tuple(records),
    )


def environment_snapshot(*, project_root: Path | str = PROJECT_ROOT) -> Mapping[str, Any]:
    """Capture non-secret, reportable environment facts for the release archive."""
    root = Path(project_root).resolve()

    def command(*args: str) -> Mapping[str, Any]:
        try:
            output = subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.STDOUT).strip()
            return {"command": list(args), "status": "ok", "output": output}
        except (OSError, subprocess.CalledProcessError) as exc:
            return {"command": list(args), "status": "unavailable", "error": type(exc).__name__}

    git_commit = command("git", "rev-parse", "HEAD")
    git_status = command("git", "status", "--porcelain", "--untracked-files=all")
    packages = command(sys.executable, "-m", "pip", "freeze")
    return {
        "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "macos_version": command("sw_vers"),
        "git_commit": git_commit,
        "git_status": {**git_status, "clean": git_status.get("status") == "ok" and not git_status.get("output")},
        "dependency_freeze": packages,
        "ollama_version": command("ollama", "--version"),
    }


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", choices=("E0", "E1"), required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--reproduction-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--conflict-reference-dir", type=Path)
    parser.add_argument("--conflict-reproduction-dir", type=Path)
    parser.add_argument("--provenance-reference-dir", type=Path)
    parser.add_argument("--provenance-reproduction-dir", type=Path)
    arguments = parser.parse_args(argv)
    result = verify_run_reproducibility(
        configuration_id=arguments.configuration,
        reference_directory=arguments.reference_dir,
        reproduction_directory=arguments.reproduction_dir,
    )
    fixture_pairs = (
        ("conflict", arguments.conflict_reference_dir, arguments.conflict_reproduction_dir),
        ("provenance", arguments.provenance_reference_dir, arguments.provenance_reproduction_dir),
    )
    fixture_results: list[FixtureReproducibilityResult] = []
    for suite, reference, reproduction in fixture_pairs:
        if (reference is None) != (reproduction is None):
            raise SystemExit(f"Supply both --{suite}-reference-dir and --{suite}-reproduction-dir, or neither.")
        if reference is not None and reproduction is not None:
            fixture_results.append(
                verify_fixture_reproducibility(
                    fixture_suite=suite,
                    reference_directory=reference,
                    reproduction_directory=reproduction,
                )
            )
    output_dir = arguments.output_dir.resolve()
    if output_dir.exists():
        raise SystemExit(f"Refusing to overwrite an existing reproducibility directory: {output_dir}")
    output_dir.mkdir(parents=True)
    _atomic_json_write(output_dir / f"{arguments.configuration.lower()}_reproducibility_result.json", result.as_dict())
    if fixture_results:
        _atomic_json_write(
            output_dir / "fixture_reproducibility_results.json",
            {"results": [item.as_dict() for item in fixture_results]},
        )
    _atomic_json_write(output_dir / "environment_manifest.json", environment_snapshot())
    print(json.dumps({
        "configuration_id": result.configuration_id,
        "all_required_checks_passed": result.all_required_checks_passed and all(
            item.all_required_checks_passed for item in fixture_results
        ),
        "scenario_count": result.scenario_count,
        "fixture_suite_count": len(fixture_results),
        "output_dir": str(output_dir),
    }, indent=2, sort_keys=True))
    return 0 if result.all_required_checks_passed else 2


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
