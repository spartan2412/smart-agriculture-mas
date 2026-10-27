"""Persistent, fail-closed batch execution for the frozen benchmark MAS.

This module is intentionally downstream of the 21-agent workflow.  It does
not generate agricultural evidence or modify a decision.  Its only role is to
execute immutable scenario IDs, evaluate completed traces with the independent
oracle, and persist reproducible artifacts for later paper tables.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping, Optional, Sequence

import config
from data.benchmark_loader import FrozenBenchmarkLoader
from evaluation.apple_gpu_preflight import (
    AppleGPUPreflightError,
    load_pilot_set,
    validate_acceleration_evidence,
)
from evaluation.benchmark_oracle import BenchmarkEvaluationOracle
from evaluation.benchmark_systems import EVALUATION_ONLY_SYSTEM_IDS, SYSTEM_IDS, build_benchmark_system
from evaluation.conflict_fixture_runner import (
    CONFLICT_ABLATION_SYSTEM_ID,
    FULL_RESOLVER_SYSTEM_ID,
    ConflictFixtureRunner,
    summarize_a6_conflict_ablation,
)
from graph.benchmark_workflow import BenchmarkRun
from graph.benchmark_workflow_v5 import BenchmarkMASWorkflowV5
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
)
from llm.benchmark_llm_client import BenchmarkLLMClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL_PATH = PROJECT_ROOT / "evaluation" / "experiment_protocol.json"
V51_FINAL_HELDOUT_ACCEPTANCE_PATH = PROJECT_ROOT / "results" / "e1-v5-heldout-final" / "final_acceptance_report.json"
V51_FINAL_HELDOUT_RUN_MANIFEST_PATH = PROJECT_ROOT / "results" / "e1-v5-heldout-final" / "run_manifest.json"


class ExperimentProtocolError(RuntimeError):
    """Raised when a requested batch violates the frozen experiment protocol."""


class BatchRunError(RuntimeError):
    """Raised after a batch writes a failure record and stops fail-closed."""


@dataclass(frozen=True)
class BatchRunSummary:
    """Small caller-facing summary; full details remain in persisted JSON."""

    run_id: str
    configuration_id: str
    system_id: str
    evaluation_only: bool
    scenario_count: int
    fully_passing_scenario_count: int
    output_dir: Path
    fixture_count: int = 0


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _jsonable(value: Any) -> Any:
    """Convert frozen dataclasses, Pydantic models, enums, and mappings to JSON.

    The benchmark trace contains only project-owned typed objects.  Keeping
    this conversion explicit prevents ``default=str`` from silently turning an
    unexpected object into an unauditable string.
    """
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return _jsonable(value.as_dict())
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if is_dataclass(value):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported batch-artifact value: {type(value).__name__}")


def _atomic_json_write(path: Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    """Write one complete JSON artifact or leave no partially-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_git(project_root: Path, *arguments: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *arguments], cwd=project_root, text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ExperimentProtocolError(f"Unable to inspect Git state: {exc}") from exc


def _peak_memory_bytes() -> int:
    """Return process peak RSS in bytes on macOS and Linux."""
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _frozen_pilot_scenario_ids_from_csv(path: Path | str) -> tuple[str, ...]:
    """Resolve only the protocol's exact 30-site pilot CSV, never an arbitrary subset."""
    pilot = load_pilot_set(project_root=PROJECT_ROOT)
    expected = (pilot.directory / str(pilot.manifest["scenario_file"])).resolve()
    supplied = Path(path).resolve()
    if supplied != expected:
        raise ExperimentProtocolError(
            f"--pilot-scenario-set must be the frozen pilot CSV: {expected}"
        )
    return tuple(sorted(str(row["scenario_id"]) for row in pilot.rows))


class BenchmarkBatchRunner:
    """Execute a protocol-bound set of normal frozen scenarios serially.

    Real runs require a clean committed repository.  Tests can deliberately
    set ``require_clean_git=False`` because their temporary output and
    uncommitted implementation edits are not research artifacts.
    """

    def __init__(
        self,
        *,
        project_root: Path | str = PROJECT_ROOT,
        protocol_path: Path | str = DEFAULT_PROTOCOL_PATH,
        loader: Optional[FrozenBenchmarkLoader] = None,
        oracle: Optional[BenchmarkEvaluationOracle] = None,
        require_clean_git: bool = True,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.protocol_path = Path(protocol_path).resolve()
        self.loader = loader or FrozenBenchmarkLoader(project_root=self.project_root)
        self.oracle = oracle or BenchmarkEvaluationOracle()
        self.require_clean_git = require_clean_git

    def _read_protocol(self) -> Mapping[str, Any]:
        if not self.protocol_path.is_file():
            raise ExperimentProtocolError(f"Experiment protocol is missing: {self.protocol_path}")
        try:
            protocol = json.loads(self.protocol_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ExperimentProtocolError(f"Experiment protocol is not valid JSON: {exc}") from exc
        if protocol.get("protocol_version") not in {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}:
            raise ExperimentProtocolError("Unsupported experiment protocol version.")
        if protocol.get("benchmark", {}).get("normal_scenario_count") != 300:
            raise ExperimentProtocolError("Protocol no longer names the frozen 300-scenario benchmark.")
        if protocol.get("oracle", {}).get("oracle_version") != self.oracle.version:
            raise ExperimentProtocolError("Protocol oracle version differs from the installed oracle.")
        return protocol

    def _verify_protocol_hashes(self, protocol: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
        expected_hashes = protocol.get("frozen_artifact_sha256")
        if not isinstance(expected_hashes, Mapping) or not expected_hashes:
            raise ExperimentProtocolError("Protocol has no frozen artifact hash snapshot.")
        observed: list[dict[str, str]] = []
        for relative, expected in sorted(expected_hashes.items()):
            if not isinstance(relative, str) or not isinstance(expected, str):
                raise ExperimentProtocolError("Protocol artifact hash mapping is malformed.")
            path = (self.project_root / relative).resolve()
            if self.project_root not in path.parents or not path.is_file():
                raise ExperimentProtocolError(f"Frozen protocol artifact is missing or outside project: {relative}")
            actual = _sha256_file(path)
            if actual != expected:
                raise ExperimentProtocolError(
                    f"Frozen protocol artifact hash mismatch for {relative}: expected {expected}, got {actual}"
                )
            observed.append({"path": relative, "sha256": actual})
        return tuple(observed)

    def _git_metadata(self) -> Mapping[str, Any]:
        commit = _run_git(self.project_root, "rev-parse", "HEAD")
        status = _run_git(self.project_root, "status", "--porcelain", "--untracked-files=all")
        clean = not status
        if self.require_clean_git and not clean:
            raise ExperimentProtocolError(
                "A research batch requires a clean Git worktree. Commit or stash unrelated changes first."
            )
        return {"commit": commit, "clean_at_start": clean, "status_at_start": status}

    @staticmethod
    def _hardware_metadata() -> Mapping[str, Any]:
        torch_mps: Mapping[str, Any]
        try:
            import torch  # Imported only for metadata; it is not an LLM runtime dependency.

            torch_mps = {
                "torch_version": str(torch.__version__),
                "mps_built": bool(torch.backends.mps.is_built()),
                "mps_available": bool(torch.backends.mps.is_available()),
            }
        except Exception as exc:  # pragma: no cover - dependency/platform dependent
            torch_mps = {"status": "unavailable", "error": type(exc).__name__}
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "torch_mps": torch_mps,
        }

    @staticmethod
    def _runtime_environment() -> Mapping[str, Any]:
        """Record non-secret settings that affect bounded-model execution."""
        return {
            "LLM_BACKEND": config.LLM_BACKEND,
            "OLLAMA_MODEL": config.OLLAMA_MODEL,
            "BENCHMARK_LLM_ENABLED": config.BENCHMARK_LLM_ENABLED,
            "BENCHMARK_LLM_REQUIRED": config.BENCHMARK_LLM_REQUIRED,
            "BENCHMARK_LLM_MAX_SELECTED_FACTS": config.BENCHMARK_LLM_MAX_SELECTED_FACTS,
            "RAG_TOP_K": config.RAG_TOP_K,
        }

    def _validate_configuration(
        self,
        protocol: Mapping[str, Any],
        configuration_id: str,
        *,
        acceleration_evidence: Optional[Mapping[str, Any]],
        model_artifact_binding: Optional[Mapping[str, Any]],
    ) -> tuple[Mapping[str, Any], Any, Mapping[str, Any], Mapping[str, Any]]:
        configurations = protocol.get("experiment_configurations", {})
        configuration = configurations.get(configuration_id) if isinstance(configurations, Mapping) else None
        if not isinstance(configuration, Mapping):
            raise ExperimentProtocolError(f"Unknown frozen experiment configuration: {configuration_id}")

        backend = configuration.get("backend")
        enabled = bool(configuration.get("benchmark_llm_enabled"))
        required = bool(configuration.get("benchmark_llm_required"))
        evidence = dict(acceleration_evidence or {})
        if backend == "none":
            if enabled:
                raise ExperimentProtocolError("A deterministic configuration cannot enable bounded LLM calls.")
            evidence = {"status": "not_applicable", "reason": "deterministic configuration"}
            return configuration, BenchmarkLLMClient(enabled=False, required=False), evidence, {}

        if not enabled:
            raise ExperimentProtocolError("An LLM backend configuration must enable bounded LLM calls.")
        if configuration_id == "E1":
            if config.LLM_BACKEND != "ollama" or config.OLLAMA_MODEL != configuration.get("ollama_tag"):
                raise ExperimentProtocolError(
                    "E1 requires LLM_BACKEND=ollama and the protocol-bound OLLAMA_MODEL."
                )
            selector_runtime = configuration.get("bounded_llm_runtime")
            if selector_runtime != "v5.1":
                raise ExperimentProtocolError("E1 must use the frozen v5.1 bounded-selector runtime.")
            self._validate_final_v51_heldout_gate(protocol)
            normalized_binding: Mapping[str, Any] = {
                "ollama_tag": configuration["ollama_tag"],
                "model_artifact_sha256": configuration["installed_model_blob_sha256"],
                "quantization": configuration["quantization"],
                "bounded_llm_runtime": selector_runtime,
                "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
                "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
            }
        else:
            bundle = dict(model_artifact_binding or {})
            bindings = bundle.get("configurations")
            if not isinstance(bindings, Mapping) or set(bindings) != {"E2", "E3"}:
                raise ExperimentProtocolError(
                    f"{configuration_id} requires one binding document with exactly E2 and E3 entries."
                )
            e2_binding = bindings["E2"]
            e3_binding = bindings["E3"]
            if not isinstance(e2_binding, Mapping) or not isinstance(e3_binding, Mapping):
                raise ExperimentProtocolError("E2/E3 artifact-binding entries must be JSON objects.")
            required_fields = protocol.get("e2_e3_identical_artifact_gate", {}).get("required_fields", [])
            missing = [
                f"{configuration_key}.{field}"
                for configuration_key, binding in (("E2", e2_binding), ("E3", e3_binding))
                for field in required_fields
                if not binding.get(field)
            ]
            if missing:
                raise ExperimentProtocolError(
                    f"{configuration_id} cannot run before model-artifact binding records: {', '.join(missing)}"
                )
            mismatched = [
                field for field in required_fields if e2_binding[field] != e3_binding[field]
            ]
            if mismatched:
                raise ExperimentProtocolError(
                    "E2/E3 cannot be labelled a runtime-only comparison because their immutable model "
                    f"bindings differ: {', '.join(mismatched)}"
                )
            normalized_binding = {
                "comparison_type": "runtime_only",
                "E2": dict(e2_binding),
                "E3": dict(e3_binding),
            }
            if configuration_id == "E3":
                raise ExperimentProtocolError(
                    "E3 is blocked until an MLX-LM adapter is added to the bounded LLM client. "
                    "The runner refuses to substitute Ollama for MLX-LM."
                )
            if config.LLM_BACKEND != "ollama":
                raise ExperimentProtocolError("E2 requires LLM_BACKEND=ollama.")

        try:
            validate_acceleration_evidence(
                evidence,
                protocol=protocol,
                configuration_id=configuration_id,
                project_root=self.project_root,
            )
        except AppleGPUPreflightError as exc:
            raise ExperimentProtocolError(
                f"{configuration_id} requires verified Apple-GPU acceleration evidence from its matching pilot: {exc}"
            ) from exc

        if configuration_id == "E1":
            return configuration, BenchmarkLLMClientV5(enabled=True, required=required), evidence, normalized_binding
        return configuration, BenchmarkLLMClient(enabled=True, required=required), evidence, normalized_binding

    def _validate_final_v51_heldout_gate(self, protocol: Mapping[str, Any]) -> None:
        """Require the persisted, accepted final v5.1 result before an E1 MAS run.

        This deliberately validates the *completed* held-out evidence rather
        than merely checking that the question set exists.  It prevents the
        batch runner from silently falling back to v4 or from treating a
        development-only selector result as approval for the full MAS pilot.
        """
        gate = protocol.get("final_v51_relevance_gate")
        if not isinstance(gate, Mapping):
            raise ExperimentProtocolError("E1 lacks the final v5.1 held-out relevance gate.")
        required_values = {
            "status": "accepted_final_heldout_result",
            "acceptance_report_path": str(V51_FINAL_HELDOUT_ACCEPTANCE_PATH.relative_to(self.project_root)),
            "run_manifest_path": str(V51_FINAL_HELDOUT_RUN_MANIFEST_PATH.relative_to(self.project_root)),
            "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
            "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
            "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
        }
        if any(gate.get(key) != value for key, value in required_values.items()):
            raise ExperimentProtocolError("E1 final v5.1 held-out gate differs from the frozen runtime boundary.")

        for key, path in (
            ("acceptance_report_sha256", V51_FINAL_HELDOUT_ACCEPTANCE_PATH),
            ("run_manifest_sha256", V51_FINAL_HELDOUT_RUN_MANIFEST_PATH),
        ):
            expected_hash = gate.get(key)
            if not isinstance(expected_hash, str) or not path.is_file() or _sha256_file(path) != expected_hash:
                raise ExperimentProtocolError(f"E1 final v5.1 held-out artifact hash differs: {path.name}")

        try:
            acceptance = json.loads(V51_FINAL_HELDOUT_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
            run_manifest = json.loads(V51_FINAL_HELDOUT_RUN_MANIFEST_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExperimentProtocolError(f"Cannot read final v5.1 held-out result: {exc}") from exc
        if (
            acceptance.get("all_relevance_thresholds_pass") is not True
            or acceptance.get("usage") != "final_heldout_evaluation_after_v5_development_freeze"
            or run_manifest.get("bounded_llm_invocation_count") != 96
            or run_manifest.get("runtime_configuration", {}).get("backend") != "ollama"
            or run_manifest.get("runtime_configuration", {}).get("ollama_model") != "qwen2.5:7b-instruct"
            or run_manifest.get("runtime_configuration", {}).get("temperature") != 0.0
            or run_manifest.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION_V5
            or run_manifest.get("selection_contract_version") != V5_SELECTION_CONTRACT_VERSION
            or run_manifest.get("candidate_packaging_version") != CANDIDATE_PACKAGING_VERSION_V5
        ):
            raise ExperimentProtocolError("E1 requires an accepted final v5.1 held-out relevance result.")

    def _build_workflow(
        self,
        *,
        configuration: Mapping[str, Any],
        system_id: str,
        bounded_llm: Any,
    ) -> Any:
        """Select the explicitly versioned runtime without changing E0/A0 history."""
        if configuration.get("bounded_llm_runtime") == "v5.1":
            if system_id != FULL_RESOLVER_SYSTEM_ID:
                raise ExperimentProtocolError("The v5.1 bounded runtime is approved only for the full A0 MAS path.")
            if not isinstance(bounded_llm, BenchmarkLLMClientV5):
                raise ExperimentProtocolError("The E1 v5.1 runtime requires BenchmarkLLMClientV5.")
            return BenchmarkMASWorkflowV5(loader=self.loader, bounded_llm=bounded_llm)
        return build_benchmark_system(system_id, loader=self.loader, bounded_llm=bounded_llm)

    def _select_scenarios(self, scenario_ids: Optional[Iterable[str]]) -> tuple[str, ...]:
        available = self.loader.scenario_ids()
        selected = tuple(available if scenario_ids is None else scenario_ids)
        if not selected:
            raise ExperimentProtocolError("A batch must contain at least one frozen scenario ID.")
        if len(selected) != len(set(selected)):
            raise ExperimentProtocolError("A batch cannot contain a duplicate scenario ID.")
        unknown = sorted(set(selected) - set(available))
        if unknown:
            raise ExperimentProtocolError(f"Batch requested unknown frozen scenario IDs: {', '.join(unknown)}")
        return tuple(sorted(selected))

    def _validate_bounded_llm_population(
        self,
        protocol: Mapping[str, Any],
        configuration: Mapping[str, Any],
        selected_ids: Sequence[str],
    ) -> None:
        """Allow only the frozen 30-site pilot or all 300 for LLM experiments."""
        if configuration.get("backend") == "none":
            return
        population_size = len(selected_ids)
        if population_size == 300:
            return
        preflight = protocol.get("apple_gpu_pilot_preflight", {})
        if (
            not isinstance(preflight, Mapping)
            or preflight.get("pilot_scenario_count") != 30
            or preflight.get("pilot_unique_site_count") != 30
        ):
            raise ExperimentProtocolError("The frozen 30-site Apple-GPU pilot protocol is invalid.")
        try:
            pilot = load_pilot_set(project_root=self.project_root)
        except AppleGPUPreflightError as exc:
            raise ExperimentProtocolError(f"Cannot load frozen Apple-GPU pilot scenarios: {exc}") from exc
        pilot_ids = tuple(sorted(str(row["scenario_id"]) for row in pilot.rows))
        if population_size != len(pilot_ids) or tuple(selected_ids) != pilot_ids:
            raise ExperimentProtocolError(
                "Bounded-LLM experiments may use only all 300 scenarios or the exact frozen 30-site Apple-GPU pilot set."
            )

    def _prepare_output_dir(self, output_dir: Path | str) -> Path:
        path = Path(output_dir).resolve()
        if path.exists():
            raise BatchRunError(f"Refusing to overwrite existing batch output directory: {path}")
        path.mkdir(parents=True, exist_ok=False)
        return path

    @staticmethod
    def _validate_system(
        protocol: Mapping[str, Any],
        system_id: str,
        *,
        evaluation_only: bool,
        include_conflict_fixtures: bool,
    ) -> Mapping[str, Any]:
        systems = {
            str(item.get("id")): item
            for item in protocol.get("architecture_comparisons", ())
            if isinstance(item, Mapping) and item.get("id")
        }
        if system_id not in SYSTEM_IDS or system_id not in systems:
            raise ExperimentProtocolError(f"Unknown protocol architecture system: {system_id}")
        if system_id in EVALUATION_ONLY_SYSTEM_IDS and not evaluation_only:
            raise ExperimentProtocolError(
                f"{system_id} is evaluation-only. Pass evaluation_only=True to persist its expected oracle failures."
            )
        if system_id == "A0" and evaluation_only:
            raise ExperimentProtocolError("A0 is the proposed MAS and must not be labelled evaluation-only.")
        if include_conflict_fixtures and system_id not in {
            FULL_RESOLVER_SYSTEM_ID,
            CONFLICT_ABLATION_SYSTEM_ID,
        }:
            raise ExperimentProtocolError(
                "The 60 fixture suite is available only for A0 or the A6 conflict-resolution ablation."
            )
        return systems[system_id]

    @staticmethod
    def _scenario_artifact(
        *,
        scenario: Any,
        run: BenchmarkRun,
        oracle_result: Any,
        elapsed_ms: int,
        peak_memory_bytes: int,
    ) -> Mapping[str, Any]:
        return {
            "scenario_identity": _jsonable(scenario.identity),
            "benchmark_run": _jsonable(run),
            "scenario_oracle_result": _jsonable(oracle_result),
            "runtime": {
                "elapsed_ms": elapsed_ms,
                "process_peak_memory_bytes": peak_memory_bytes,
            },
        }

    def run(
        self,
        *,
        configuration_id: str,
        output_dir: Path | str,
        system_id: str = "A0",
        evaluation_only: bool = False,
        scenario_ids: Optional[Iterable[str]] = None,
        include_conflict_fixtures: bool = False,
        acceleration_evidence: Optional[Mapping[str, Any]] = None,
        model_artifact_binding: Optional[Mapping[str, Any]] = None,
    ) -> BatchRunSummary:
        """Run selected immutable scenarios and persist every completed trace.

        ``scenario_ids=None`` is the full 300-scenario population.  A subset
        is permitted only for smoke tests and the later documented 30-scenario
        GPU pilots; its manifest records the exact selected IDs.
        """
        protocol = self._read_protocol()
        observed_hashes = self._verify_protocol_hashes(protocol)
        git_metadata = self._git_metadata()
        system = self._validate_system(
            protocol,
            system_id,
            evaluation_only=evaluation_only,
            include_conflict_fixtures=include_conflict_fixtures,
        )
        configuration, bounded_llm, acceleration, normalized_binding = self._validate_configuration(
            protocol,
            configuration_id,
            acceleration_evidence=acceleration_evidence,
            model_artifact_binding=model_artifact_binding,
        )
        selected_ids = self._select_scenarios(scenario_ids)
        self._validate_bounded_llm_population(protocol, configuration, selected_ids)
        destination = self._prepare_output_dir(output_dir)
        run_id = destination.name
        workflow = self._build_workflow(
            configuration=configuration,
            system_id=system_id,
            bounded_llm=bounded_llm,
        )

        protocol_hash = _sha256_file(self.protocol_path)
        started_at = _utc_timestamp()
        manifest: dict[str, Any] = {
            "run_id": run_id,
            "status": "running",
            "started_at_utc": started_at,
            "configuration_id": configuration_id,
            "configuration": dict(configuration),
            "system_id": system_id,
            "system": dict(system),
            "evaluation_only": evaluation_only,
            "normal_scenario_ids": list(selected_ids),
            "normal_scenario_count": len(selected_ids),
            "include_conflict_fixtures": include_conflict_fixtures,
            "protocol": {
                "path": str(self.protocol_path.relative_to(self.project_root)),
                "sha256": protocol_hash,
                "version": protocol["protocol_version"],
                "verified_artifacts": observed_hashes,
            },
            "git": git_metadata,
            "runtime_environment": self._runtime_environment(),
            "hardware": self._hardware_metadata(),
            "apple_gpu_acceleration": acceleration,
            "bounded_llm": {
                "enabled": bounded_llm.enabled,
                "required": bounded_llm.required,
                "runtime": configuration.get("bounded_llm_runtime", "v4"),
                "max_selected_facts": (
                    "role_specific_v5_policy"
                    if configuration.get("bounded_llm_runtime") == "v5.1"
                    else bounded_llm.max_selected_facts
                ),
                "prompt_template_version": (
                    PROMPT_TEMPLATE_VERSION_V5
                    if configuration.get("bounded_llm_runtime") == "v5.1"
                    else "bounded-selection-v4-structured-relevance-prompts"
                ),
                "selection_contract_version": (
                    V5_SELECTION_CONTRACT_VERSION
                    if configuration.get("bounded_llm_runtime") == "v5.1"
                    else None
                ),
                "candidate_packaging_version": (
                    CANDIDATE_PACKAGING_VERSION_V5
                    if configuration.get("bounded_llm_runtime") == "v5.1"
                    else None
                ),
            },
            "model_artifact_binding": _jsonable(normalized_binding),
        }
        _atomic_json_write(destination / "run_manifest.json", manifest)

        completed: list[tuple[Any, Any]] = []
        try:
            for sequence, scenario_id in enumerate(selected_ids, start=1):
                started = time.perf_counter()
                scenario = self.loader.load(scenario_id, verify_raw_hashes=True)
                run = workflow.run(scenario_id, question="", verify_raw_hashes=True)
                result = self.oracle.evaluate(scenario, run)
                elapsed_ms = round((time.perf_counter() - started) * 1000)
                artifact = self._scenario_artifact(
                    scenario=scenario,
                    run=run,
                    oracle_result=result,
                    elapsed_ms=elapsed_ms,
                    peak_memory_bytes=_peak_memory_bytes(),
                )
                _atomic_json_write(destination / "scenarios" / f"{scenario_id}.json", artifact)
                completed.append((scenario, result))
                _atomic_json_write(
                    destination / "progress.json",
                    {
                        "run_id": run_id,
                        "status": "running",
                        "completed_scenario_count": len(completed),
                        "total_scenario_count": len(selected_ids),
                        "last_completed_scenario_id": scenario_id,
                        "last_sequence": sequence,
                    },
                )
                if not result.overall_passed and not evaluation_only:
                    raise BatchRunError(
                        f"Oracle failure for {scenario_id}: {', '.join(result.failing_check_names)}"
                    )

            aggregate = self.oracle.aggregate(result for _, result in completed)
            stratified = self.oracle.aggregate_stratified(completed)
            _atomic_json_write(destination / "aggregate_oracle_result.json", aggregate.as_dict())
            _atomic_json_write(destination / "stratified_oracle_result.json", stratified.as_dict())

            fixture_count = 0
            if include_conflict_fixtures:
                fixture_runner = ConflictFixtureRunner(loader=self.loader, system_id=system_id)
                fixture_runs = fixture_runner.run_all(verify_raw_hashes=True)
                _atomic_json_write(destination / "conflict_fixture_runs.json", _jsonable(fixture_runs))
                if system_id == FULL_RESOLVER_SYSTEM_ID:
                    fixture_result = self.oracle.evaluate_fixture_runs(fixture_runs)
                    _atomic_json_write(destination / "fixture_oracle_result.json", fixture_result.as_dict())
                    if not fixture_result.all_passed:
                        raise BatchRunError("The stored A0 conflict-fixture oracle did not fully pass.")
                    fixture_count = fixture_result.fixture_count
                else:
                    ablation_result = summarize_a6_conflict_ablation(fixture_runs)
                    _atomic_json_write(
                        destination / "conflict_ablation_result.json", ablation_result.as_dict()
                    )
                    if not ablation_result.expected_behavior_passed:
                        raise BatchRunError(
                            "The A6 fixture ablation did not preserve its documented detection-and-safety boundary."
                        )
                    fixture_count = ablation_result.fixture_count

            batch_status = (
                "completed"
                if aggregate.fully_passing_scenario_count == aggregate.scenario_count
                else "completed_evaluation_only_with_oracle_failures"
            )
            manifest.update(
                {
                    "status": batch_status,
                    "completed_at_utc": _utc_timestamp(),
                    "bounded_llm_invocation_count": bounded_llm.invocation_count,
                    "fully_passing_scenario_count": aggregate.fully_passing_scenario_count,
                    "fixture_count": fixture_count,
                }
            )
            _atomic_json_write(destination / "run_manifest.json", manifest)
            _atomic_json_write(
                destination / "progress.json",
                {
                    "run_id": run_id,
                    "status": batch_status,
                    "completed_scenario_count": len(completed),
                    "total_scenario_count": len(selected_ids),
                    "last_completed_scenario_id": selected_ids[-1],
                    "last_sequence": len(selected_ids),
                },
            )
            _atomic_json_write(
                destination / "batch_summary.json",
                {
                    "run_id": run_id,
                    "configuration_id": configuration_id,
                    "system_id": system_id,
                    "evaluation_only": evaluation_only,
                    "scenario_count": aggregate.scenario_count,
                    "fully_passing_scenario_count": aggregate.fully_passing_scenario_count,
                    "overall_structural_pass_rate": aggregate.overall_structural_pass_rate,
                    "fixture_count": fixture_count,
                    "status": batch_status,
                },
            )
            return BatchRunSummary(
                run_id=run_id,
                configuration_id=configuration_id,
                system_id=system_id,
                evaluation_only=evaluation_only,
                scenario_count=aggregate.scenario_count,
                fully_passing_scenario_count=aggregate.fully_passing_scenario_count,
                output_dir=destination,
                fixture_count=fixture_count,
            )
        except Exception as exc:
            manifest.update(
                {
                    "status": "failed",
                    "failed_at_utc": _utc_timestamp(),
                    "completed_scenario_count": len(completed),
                    "failure": {"type": type(exc).__name__, "message": str(exc)},
                }
            )
            _atomic_json_write(destination / "run_manifest.json", manifest)
            _atomic_json_write(
                destination / "failure.json",
                {
                    "run_id": run_id,
                    "configuration_id": configuration_id,
                    "completed_scenario_count": len(completed),
                    "failure": {"type": type(exc).__name__, "message": str(exc)},
                },
            )
            if isinstance(exc, (ExperimentProtocolError, BatchRunError)):
                raise
            raise BatchRunError(f"Batch stopped while processing frozen scenarios: {exc}") from exc


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI for committed research runs; it deliberately has no dirty-worktree bypass."""
    import argparse

    parser = argparse.ArgumentParser(description="Persist a protocol-bound benchmark MAS batch run.")
    parser.add_argument("--configuration", choices=("E0", "E1", "E2", "E3"), required=True)
    parser.add_argument("--system", choices=SYSTEM_IDS, default="A0")
    parser.add_argument(
        "--evaluation-only",
        action="store_true",
        help="Required for A1-A6; records oracle failures without exposing the system to farmers.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        help=(
            "Optional frozen scenario ID for deterministic smoke tests. Bounded-LLM configurations "
            "accept only the exact 30-site pilot set or all 300 scenarios."
        ),
    )
    parser.add_argument(
        "--pilot-scenario-set",
        type=Path,
        help=(
            "Use the exact frozen 30-site Apple-GPU pilot CSV. This cannot be combined with "
            "--scenario-id and rejects any other CSV path."
        ),
    )
    parser.add_argument(
        "--include-conflict-fixtures",
        action="store_true",
        help=(
            "Also persist the 60 evaluation-only fixture results. Allowed for A0, or for A6 with "
            "--evaluation-only to measure detected-but-unresolved conflicts."
        ),
    )
    parser.add_argument(
        "--acceleration-evidence-json",
        type=Path,
        help="Required for E1-E3: pilot-verified Apple-GPU evidence JSON with status=verified.",
    )
    parser.add_argument(
        "--model-artifact-binding-json",
        type=Path,
        help="Required for E2/E3: one JSON object containing matching E2 and E3 artifact bindings.",
    )
    arguments = parser.parse_args(argv)

    if arguments.pilot_scenario_set is not None and arguments.scenario_ids:
        raise SystemExit("Use either --pilot-scenario-set or --scenario-id, not both.")

    def read_optional_json(path: Optional[Path]) -> Optional[Mapping[str, Any]]:
        if path is None:
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Cannot read JSON input {path}: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise SystemExit(f"JSON input {path} must contain an object.")
        return payload

    scenario_ids = (
        _frozen_pilot_scenario_ids_from_csv(arguments.pilot_scenario_set)
        if arguments.pilot_scenario_set is not None
        else arguments.scenario_ids
    )
    summary = BenchmarkBatchRunner().run(
        configuration_id=arguments.configuration,
        output_dir=arguments.output_dir,
        system_id=arguments.system,
        evaluation_only=arguments.evaluation_only,
        scenario_ids=scenario_ids,
        include_conflict_fixtures=arguments.include_conflict_fixtures,
        acceleration_evidence=read_optional_json(arguments.acceleration_evidence_json),
        model_artifact_binding=read_optional_json(arguments.model_artifact_binding_json),
    )
    print(json.dumps(_jsonable(asdict(summary)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
