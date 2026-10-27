"""Versioned E2/E3 execution path that preserves completed E0/E1 artifacts.

The original ``benchmark_batch_runner.py`` is hash-locked by E0/E1 manifests.
This module subclasses it instead of changing it.  E2 is a 14B Ollama capacity
experiment; E3 is an MLX-LM deployment experiment.  Both use the frozen v5.1
selection contract, but E3 is labelled ``deployment_backend`` unless all
artifact-binding fields truly match.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import config
from evaluation.benchmark_batch_runner import (
    BenchmarkBatchRunner,
    ExperimentProtocolError,
    _frozen_pilot_scenario_ids_from_csv,
)
from evaluation.apple_gpu_preflight import PILOT_MANIFEST_FILENAME, load_pilot_set
from evaluation.conflict_fixture_runner import FULL_RESOLVER_SYSTEM_ID
from graph.benchmark_workflow_v5 import BenchmarkMASWorkflowV5
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
    BenchmarkLLMClientV5,
)


PHASE8_RUNNER_VERSION = "1.0"
PHASE8_CONFIGURATION_IDS = frozenset({"E2", "E3"})
_RUNTIME_ONLY = "runtime_only"
_DEPLOYMENT_BACKEND = "deployment_backend"


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_json_hash(value: Any) -> str:
    """Hash a binding by content rather than its whitespace or key order."""
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_phase8_artifact_binding(
    protocol: Mapping[str, Any],
    configuration_id: str,
    model_artifact_binding: Optional[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Validate E2/E3 binding metadata before either model is invoked.

    A ``runtime_only`` comparison requires byte-identical artifact fields.
    ``deployment_backend`` accepts backend-native artifacts, but only with an
    explicit non-equivalence limitation.  It must never be reported as a pure
    runtime effect.  This allows an honest operational E3 experiment when an
    Ollama GGUF artifact and an MLX artifact cannot be proven byte-equivalent.
    """
    if configuration_id not in PHASE8_CONFIGURATION_IDS:
        raise ExperimentProtocolError("Phase 8 supports E2 and E3 only.")
    bundle = dict(model_artifact_binding or {})
    bindings = bundle.get("configurations")
    if not isinstance(bindings, Mapping) or set(bindings) != {"E2", "E3"}:
        raise ExperimentProtocolError(
            f"{configuration_id} requires one binding document with exactly E2 and E3 entries."
        )
    e2, e3 = bindings["E2"], bindings["E3"]
    if not isinstance(e2, Mapping) or not isinstance(e3, Mapping):
        raise ExperimentProtocolError("E2/E3 artifact-binding entries must be JSON objects.")
    required = tuple(protocol.get("e2_e3_identical_artifact_gate", {}).get("required_fields", ()))
    if not required:
        raise ExperimentProtocolError("Frozen protocol does not define E2/E3 artifact fields.")
    missing = [
        f"{identifier}.{field}"
        for identifier, binding in (("E2", e2), ("E3", e3))
        for field in required
        if not binding.get(field)
    ]
    if missing:
        raise ExperimentProtocolError(
            "Phase 8 cannot run before model-artifact binding records: " + ", ".join(missing)
        )
    for identifier, binding in (("E2", e2), ("E3", e3)):
        if not str(binding.get("runtime_model_identifier", "")).strip():
            raise ExperimentProtocolError(f"{identifier}.runtime_model_identifier is required.")
        generation = binding.get("generation_parameters")
        expected_generation = {
            "temperature": 0.0,
            "maximum_tokens_per_call": 200,
            "maximum_selected_facts": 3,
            "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
            "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
        }
        if generation != expected_generation:
            raise ExperimentProtocolError(
                f"{identifier}.generation_parameters must match the frozen v5.1 selection runtime exactly."
            )

    comparison_type = str(bundle.get("comparison_type", _RUNTIME_ONLY))
    if comparison_type not in {_RUNTIME_ONLY, _DEPLOYMENT_BACKEND}:
        raise ExperimentProtocolError("comparison_type must be runtime_only or deployment_backend.")
    if comparison_type == _RUNTIME_ONLY:
        mismatched = [field for field in required if e2[field] != e3[field]]
        if mismatched:
            raise ExperimentProtocolError(
                "E2/E3 cannot be labelled runtime_only because immutable bindings differ: "
                + ", ".join(mismatched)
            )
    else:
        # A non-equivalent backend comparison still needs to remain within the
        # same published model family and capacity.  Revision/tokenizer/
        # quantization differences are recorded rather than concealed; a
        # strict equality check belongs exclusively to ``runtime_only``.
        baseline_fields = ("base_model_repository", "parameter_count")
        mismatched = [field for field in baseline_fields if e2[field] != e3[field]]
        if mismatched:
            raise ExperimentProtocolError(
                "E2/E3 deployment-backend comparison requires the same base model family and parameter count: "
                + ", ".join(mismatched)
            )
        limitations = bundle.get("comparison_limitations")
        if not isinstance(limitations, list) or not any(
            "not runtime-only" in str(item).lower() or "not byte-equivalent" in str(item).lower()
            for item in limitations
        ):
            raise ExperimentProtocolError(
                "E2/E3 deployment-backend binding must explicitly state that it is not runtime-only."
            )
    return {
        "comparison_type": comparison_type,
        "comparison_limitations": list(bundle.get("comparison_limitations", ())),
        "E2": dict(e2),
        "E3": dict(e3),
        "binding_document_sha256": _canonical_json_hash(bundle),
        "phase8_runner_version": PHASE8_RUNNER_VERSION,
        "phase8_runner_path": "evaluation/phase8_batch_runner.py",
        "phase8_runner_sha256": _sha256_file(Path(__file__).resolve()),
    }


def validate_phase8_acceleration_evidence(
    evidence: Mapping[str, Any],
    *,
    configuration_id: str,
    binding: Mapping[str, Any],
    binding_document_sha256: Optional[str] = None,
    project_root: Optional[Path | str] = None,
) -> None:
    """Require a Phase 8 probe for the same runtime/artifact binding."""
    if evidence.get("status") != "verified" or evidence.get("configuration_id") != configuration_id:
        raise ExperimentProtocolError("Phase 8 requires matching verified acceleration evidence.")
    hardware = evidence.get("hardware")
    if not isinstance(hardware, Mapping) or hardware.get("system") != "Darwin" or hardware.get("machine") != "arm64":
        raise ExperimentProtocolError("Phase 8 acceleration evidence must come from Apple-Silicon macOS.")
    if int(hardware.get("unified_memory_bytes", 0)) <= 0:
        raise ExperimentProtocolError("Phase 8 acceleration evidence lacks unified-memory capacity.")
    backend = evidence.get("backend_evidence")
    if not isinstance(backend, Mapping):
        raise ExperimentProtocolError("Phase 8 acceleration evidence lacks backend details.")
    expected_backend = "ollama" if configuration_id == "E2" else "mlx-lm"
    if backend.get("backend") != expected_backend:
        raise ExperimentProtocolError("Phase 8 acceleration evidence backend differs from configuration.")
    acceleration = backend.get("acceleration")
    checks = backend.get("checks")
    if (
        not isinstance(acceleration, Mapping)
        or not acceleration.get("observed_model_resident_in_gpu_memory")
        or int(acceleration.get("observed_gpu_resident_bytes", 0)) <= 0
        or not isinstance(checks, Mapping)
        or not checks
        or not all(checks.values())
    ):
        raise ExperimentProtocolError("Phase 8 acceleration evidence lacks an observed GPU model probe.")
    model = backend.get("model")
    if not isinstance(model, Mapping):
        raise ExperimentProtocolError("Phase 8 acceleration evidence lacks model identity.")
    if model.get("runtime_model_identifier") != binding["runtime_model_identifier"]:
        raise ExperimentProtocolError("Phase 8 preflight model identifier differs from the bound artifact.")
    if model.get("model_artifact_sha256") != binding["model_artifact_sha256"]:
        raise ExperimentProtocolError("Phase 8 preflight model artifact hash differs from the binding.")
    if model.get("quantization_level") != binding["quantization_level"]:
        raise ExperimentProtocolError("Phase 8 preflight quantization level differs from the binding.")
    if binding_document_sha256 is not None and evidence.get("model_artifact_binding_sha256") != binding_document_sha256:
        raise ExperimentProtocolError("Phase 8 preflight binding hash differs from the supplied binding document.")
    if project_root is not None:
        root = Path(project_root).resolve()
        pilot = evidence.get("pilot_set")
        frozen_pilot = load_pilot_set(project_root=root)
        if not isinstance(pilot, Mapping) or (
            pilot.get("scenario_count") != 30
            or pilot.get("unique_site_count") != 30
            or pilot.get("pilot_identity_sha256") != frozen_pilot.manifest["pilot_identity_sha256"]
            or pilot.get("scenario_file_sha256") != frozen_pilot.manifest["scenario_file_sha256"]
            or pilot.get("manifest_sha256") != _sha256_file(frozen_pilot.directory / PILOT_MANIFEST_FILENAME)
        ):
            raise ExperimentProtocolError("Phase 8 acceleration evidence does not bind the frozen 30-site pilot.")


class Phase8BatchRunner(BenchmarkBatchRunner):
    """E2/E3 runner that leaves the hash-locked E0/E1 class untouched."""

    @staticmethod
    def _runtime_environment() -> Mapping[str, Any]:
        environment = dict(BenchmarkBatchRunner._runtime_environment())
        environment["MLX_MODEL_PATH"] = config.MLX_MODEL_PATH
        environment["phase8_runner_version"] = PHASE8_RUNNER_VERSION
        return environment

    def _validate_configuration(
        self,
        protocol: Mapping[str, Any],
        configuration_id: str,
        *,
        acceleration_evidence: Optional[Mapping[str, Any]],
        model_artifact_binding: Optional[Mapping[str, Any]],
    ) -> tuple[Mapping[str, Any], Any, Mapping[str, Any], Mapping[str, Any]]:
        if configuration_id not in PHASE8_CONFIGURATION_IDS:
            raise ExperimentProtocolError("Use BenchmarkBatchRunner for E0/E1; Phase8BatchRunner is E2/E3 only.")
        configurations = protocol.get("experiment_configurations", {})
        base_configuration = configurations.get(configuration_id) if isinstance(configurations, Mapping) else None
        if not isinstance(base_configuration, Mapping) or not base_configuration.get("benchmark_llm_enabled"):
            raise ExperimentProtocolError(f"{configuration_id} is not an enabled bounded-LLM configuration.")
        self._validate_final_v51_heldout_gate(protocol)
        normalized_binding = validate_phase8_artifact_binding(
            protocol, configuration_id, model_artifact_binding
        )
        active_binding = normalized_binding[configuration_id]
        evidence = dict(acceleration_evidence or {})
        validate_phase8_acceleration_evidence(
            evidence,
            configuration_id=configuration_id,
            binding=active_binding,
            binding_document_sha256=str(normalized_binding["binding_document_sha256"]),
            project_root=self.project_root,
        )

        configuration = dict(base_configuration)
        configuration.update(
            {
                "bounded_llm_runtime": "v5.1",
                "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
                "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
                "phase8_comparison_type": normalized_binding["comparison_type"],
            }
        )
        required = bool(configuration.get("benchmark_llm_required"))
        if configuration_id == "E2":
            if config.LLM_BACKEND != "ollama":
                raise ExperimentProtocolError("E2 requires LLM_BACKEND=ollama.")
            if config.OLLAMA_MODEL != active_binding["runtime_model_identifier"]:
                raise ExperimentProtocolError("E2 OLLAMA_MODEL differs from the bound runtime model identifier.")
            client = BenchmarkLLMClientV5(enabled=True, required=required)
        else:
            if config.LLM_BACKEND != "mlx-lm":
                raise ExperimentProtocolError("E3 requires LLM_BACKEND=mlx-lm.")
            configured_path = str(Path(config.MLX_MODEL_PATH).expanduser().resolve()) if config.MLX_MODEL_PATH else ""
            if configured_path != active_binding["runtime_model_identifier"]:
                raise ExperimentProtocolError("E3 MLX_MODEL_PATH differs from the bound runtime model identifier.")
            from llm.mlx_lm_client import MLXLMJSONClient

            client = BenchmarkLLMClientV5(client=MLXLMJSONClient(), enabled=True, required=required)
        return configuration, client, evidence, normalized_binding

    def _build_workflow(
        self,
        *,
        configuration: Mapping[str, Any],
        system_id: str,
        bounded_llm: Any,
    ) -> Any:
        if system_id != FULL_RESOLVER_SYSTEM_ID:
            raise ExperimentProtocolError("Phase 8 uses only the full A0 MAS path.")
        if configuration.get("bounded_llm_runtime") != "v5.1" or not isinstance(bounded_llm, BenchmarkLLMClientV5):
            raise ExperimentProtocolError("Phase 8 requires the frozen v5.1 bounded selector.")
        return BenchmarkMASWorkflowV5(loader=self.loader, bounded_llm=bounded_llm)


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON input {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SystemExit(f"JSON input {path} must contain an object.")
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bound E2 or E3 Phase 8 MAS batch.")
    parser.add_argument("--configuration", choices=tuple(sorted(PHASE8_CONFIGURATION_IDS)), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pilot-scenario-set", type=Path)
    parser.add_argument("--acceleration-evidence-json", type=Path, required=True)
    parser.add_argument("--model-artifact-binding-json", type=Path, required=True)
    arguments = parser.parse_args(argv)
    scenario_ids = (
        _frozen_pilot_scenario_ids_from_csv(arguments.pilot_scenario_set)
        if arguments.pilot_scenario_set is not None
        else None
    )
    summary = Phase8BatchRunner().run(
        configuration_id=arguments.configuration,
        output_dir=arguments.output_dir,
        system_id=FULL_RESOLVER_SYSTEM_ID,
        scenario_ids=scenario_ids,
        acceleration_evidence=_read_json(arguments.acceleration_evidence_json),
        model_artifact_binding=_read_json(arguments.model_artifact_binding_json),
    )
    print(json.dumps(summary.__dict__, default=str, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
