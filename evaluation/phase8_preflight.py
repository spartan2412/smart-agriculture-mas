"""Apple-GPU preflight for the versioned E2/E3 Phase 8 experiments.

This intentionally does *not* change ``apple_gpu_preflight.py``: that module
and its outputs are part of completed E1 evidence.  The Phase 8 preflight
binds one explicit model artifact to E2 or E3, makes a harmless JSON probe,
and records an observed Apple-GPU residency signal before a relevance or MAS
run can begin.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from typing import Any, Mapping, Optional, Sequence

import config
from evaluation.apple_gpu_preflight import (
    DEFAULT_PILOT_SET_DIR,
    PILOT_MANIFEST_FILENAME,
    _git_metadata,
    _hardware_metadata,
    _probe_ollama,
    _sha256_file,
    load_pilot_set,
)
from evaluation.benchmark_batch_runner import BenchmarkBatchRunner, ExperimentProtocolError
from evaluation.phase8_batch_runner import (
    PHASE8_CONFIGURATION_IDS,
    _canonical_json_hash,
    validate_phase8_artifact_binding,
)
from llm.bounded_selection_v5 import (
    CANDIDATE_PACKAGING_VERSION_V5,
    PROMPT_TEMPLATE_VERSION_V5,
    V5_SELECTION_CONTRACT_VERSION,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE8_PREFLIGHT_VERSION = "1.0"
EVIDENCE_FILENAME = "acceleration_evidence.json"


class Phase8PreflightError(RuntimeError):
    """Raised for a missing or non-verifiable Phase 8 runtime artifact."""


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase8PreflightError(f"Cannot read JSON artifact {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise Phase8PreflightError(f"JSON artifact {path} must contain an object.")
    return value


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _directory_tree_sha256(directory: Path) -> str:
    """Hash exact model contents with path names, rejecting symlink indirection."""
    if not directory.is_dir():
        raise Phase8PreflightError(f"Bound MLX model directory is missing: {directory}")
    digest = sha256()
    # ``snapshot_download(local_dir=...)`` writes transport bookkeeping under
    # ``.cache``. It is not model content and can legitimately differ after a
    # resumed download, so do not let it redefine the bound artifact.
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and ".cache" not in path.relative_to(directory).parts
    )
    if not files:
        raise Phase8PreflightError(f"Bound MLX model directory contains no files: {directory}")
    for path in files:
        if path.is_symlink():
            raise Phase8PreflightError("MLX artifact must be materialized without symlinked model files.")
        relative = path.relative_to(directory).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.stat().st_size.to_bytes(16, "big"))
        with path.open("rb") as source_file:
            while block := source_file.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def _phase8_configuration(protocol: Mapping[str, Any], configuration_id: str) -> Mapping[str, Any]:
    configurations = protocol.get("experiment_configurations", {})
    configuration = configurations.get(configuration_id) if isinstance(configurations, Mapping) else None
    if configuration_id not in PHASE8_CONFIGURATION_IDS or not isinstance(configuration, Mapping):
        raise Phase8PreflightError("Phase 8 preflight supports E2 and E3 only.")
    return configuration


def _probe_e2_ollama(
    *,
    binding: Mapping[str, Any],
    protocol: Mapping[str, Any],
    host: str,
) -> Mapping[str, Any]:
    if config.LLM_BACKEND != "ollama" or config.OLLAMA_MODEL != binding["runtime_model_identifier"]:
        raise Phase8PreflightError("E2 requires LLM_BACKEND=ollama and its exact bound OLLAMA_MODEL tag.")
    runtime_digest = str(binding.get("runtime_digest", ""))
    synthetic_configuration = {
        "ollama_tag": binding["runtime_model_identifier"],
        "installed_model_blob_sha256": binding["model_artifact_sha256"],
        "installed_ollama_model_id_prefix": runtime_digest[:12],
        "quantization": binding["quantization_level"],
    }
    observed = _probe_ollama(
        configuration=synthetic_configuration,
        bounded_policy={
            "temperature": 0.0,
            "max_tokens_per_call": 200,
            "max_selected_facts": protocol["bounded_llm_policy"]["max_selected_facts"],
        },
        host=host,
    )
    observed_model = observed.get("model", {})
    if not isinstance(observed_model, Mapping):  # defensive: private helper is project-owned
        raise Phase8PreflightError("Ollama probe returned no model identity.")
    return {
        **dict(observed),
        "model": {
            **dict(observed_model),
            "runtime_model_identifier": binding["runtime_model_identifier"],
            "model_artifact_sha256": observed_model.get("model_blob_file_sha256"),
            "quantization_level": observed_model.get("quantization"),
        },
    }


def _probe_e3_mlx(*, binding: Mapping[str, Any]) -> Mapping[str, Any]:
    expected_path = Path(str(binding["runtime_model_identifier"])).expanduser().resolve()
    configured_path = Path(config.MLX_MODEL_PATH).expanduser().resolve() if config.MLX_MODEL_PATH else None
    if config.LLM_BACKEND != "mlx-lm" or configured_path != expected_path:
        raise Phase8PreflightError("E3 requires LLM_BACKEND=mlx-lm and its exact bound MLX_MODEL_PATH.")
    actual_hash = _directory_tree_sha256(expected_path)
    if actual_hash != binding["model_artifact_sha256"]:
        raise Phase8PreflightError("The materialized MLX artifact hash differs from the binding document.")
    try:
        import mlx.core as mx
    except ImportError as exc:  # pragma: no cover - platform dependency
        raise Phase8PreflightError("mlx is required for E3 Apple-GPU verification.") from exc
    from llm.mlx_lm_client import MLXLMJSONClient

    try:
        # MLX exposes these top-level calls on current releases.  They observe
        # Metal allocations directly; unlike PyTorch MPS availability, they
        # are runtime evidence for this MLX invocation.
        mx.reset_peak_memory()
        before_bytes = int(mx.get_active_memory())
        client = MLXLMJSONClient(expected_path)
        response = client.generate_json(
            "Return only the requested JSON object.",
            'Return exactly {"preflight":"ok"}.',
            temperature=0.0,
            max_tokens=16,
        )
        active_bytes = int(mx.get_active_memory())
        peak_bytes = int(mx.get_peak_memory())
    except Exception as exc:  # pragma: no cover - depends on external artifact/runtime
        raise Phase8PreflightError(f"MLX Apple-GPU probe failed: {type(exc).__name__}: {exc}") from exc
    gpu_bytes = max(active_bytes, peak_bytes)
    checks = {
        "apple_silicon_host": platform.system() == "Darwin" and platform.machine() == "arm64",
        "model_json_probe_completed": response == {"preflight": "ok"},
        "gpu_memory_observed": gpu_bytes > 0,
        "artifact_hash_matches_binding": actual_hash == binding["model_artifact_sha256"],
    }
    return {
        "backend": "mlx-lm",
        "runtime": {
            "runtime_name": "MLX-LM",
            "mlx_version": getattr(mx, "__version__", None),
            "verification_method": "mlx_generate_then_metal_active_or_peak_memory",
            "default_device": str(mx.default_device()),
        },
        "model": {
            "runtime_model_identifier": str(expected_path),
            "model_artifact_sha256": actual_hash,
            "quantization_level": binding["quantization_level"],
            "base_model_repository": binding["base_model_repository"],
            "base_model_revision_or_commit": binding["base_model_revision_or_commit"],
        },
        "generation_parameters": {
            "benchmark_temperature": 0.0,
            "benchmark_max_tokens_per_call": 200,
            "benchmark_max_selected_facts": 3,
            "probe_temperature": 0.0,
            "probe_max_tokens": 16,
        },
        "acceleration": {
            "requested_runtime": "MLX-LM / Apple GPU",
            "observed_model_resident_in_gpu_memory": gpu_bytes > 0,
            "observed_gpu_resident_bytes": gpu_bytes,
            "active_gpu_bytes_after_probe": active_bytes,
            "peak_gpu_bytes_during_probe": peak_bytes,
            "active_gpu_bytes_before_probe": before_bytes,
            "evidence": "MLX Metal active/peak allocation was observed after loading and generating with the bound model.",
            "pytorch_mps_is_not_runtime_proof": True,
        },
        "probe": {"response": response},
        "checks": checks,
    }


def run_phase8_preflight(
    *,
    configuration_id: str,
    output_dir: Path | str,
    model_artifact_binding: Mapping[str, Any],
    pilot_set_dir: Path | str = DEFAULT_PILOT_SET_DIR,
    project_root: Path | str = PROJECT_ROOT,
    ollama_host: str = "http://localhost:11434",
) -> Mapping[str, Any]:
    """Create an immutable, artifact-bound E2 or E3 GPU-preflight result."""
    root = Path(project_root).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise Phase8PreflightError(f"Refusing to overwrite existing Phase 8 preflight: {destination}")
        destination.rmdir()
    runner = BenchmarkBatchRunner(project_root=root, require_clean_git=False)
    protocol = runner._read_protocol()
    configuration = _phase8_configuration(protocol, configuration_id)
    try:
        normalized = validate_phase8_artifact_binding(protocol, configuration_id, model_artifact_binding)
    except ExperimentProtocolError as exc:
        raise Phase8PreflightError(str(exc)) from exc
    binding = normalized[configuration_id]
    pilot = load_pilot_set(pilot_set_dir, project_root=root)
    if configuration_id == "E2":
        backend_evidence = _probe_e2_ollama(binding=binding, protocol=protocol, host=ollama_host)
    else:
        backend_evidence = _probe_e3_mlx(binding=binding)
    checks = backend_evidence.get("checks", {})
    verified = isinstance(checks, Mapping) and bool(checks) and all(checks.values())
    evidence = {
        "evidence_schema_version": "phase8-1.0",
        "status": "verified" if verified else "not_verified",
        "configuration_id": configuration_id,
        "configuration": {
            **dict(configuration),
            "bounded_llm_runtime": "v5.1",
            "selection_contract_version": V5_SELECTION_CONTRACT_VERSION,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION_V5,
            "candidate_packaging_version": CANDIDATE_PACKAGING_VERSION_V5,
        },
        "recorded_at_utc": _utc_timestamp(),
        "model_artifact_binding_sha256": normalized["binding_document_sha256"],
        "model_artifact_binding": dict(binding),
        "comparison_type": normalized["comparison_type"],
        "hardware": _hardware_metadata(),
        "pilot_set": {
            "path": str(pilot.directory.relative_to(root)),
            "manifest_sha256": _sha256_file(pilot.directory / PILOT_MANIFEST_FILENAME),
            "scenario_file_sha256": pilot.manifest["scenario_file_sha256"],
            "pilot_identity_sha256": pilot.manifest["pilot_identity_sha256"],
            "scenario_count": pilot.manifest["scenario_count"],
            "unique_site_count": pilot.manifest["unique_site_count"],
            "focused_crops": pilot.manifest["focused_crops"],
        },
        "backend_evidence": backend_evidence,
        "artifact_integrity": {
            "frozen_e1_protocol_path": "evaluation/experiment_protocol.json",
            "frozen_e1_protocol_sha256": _sha256_file(root / "evaluation" / "experiment_protocol.json"),
            "preflight_module": "evaluation/phase8_preflight.py",
            "preflight_module_sha256": _sha256_file(Path(__file__).resolve()),
            "phase8_batch_runner_sha256": _sha256_file(root / "evaluation" / "phase8_batch_runner.py"),
            "git": _git_metadata(root),
        },
        "formal_boundary": {
            "not_an_agricultural_benchmark_run": True,
            "does_not_prove_pytorch_mps_for_ollama": True,
            "next_required_run": "Run the matching Phase 8 relevance transfer evaluation and 30-site MAS pilot from a clean committed worktree.",
        },
    }
    destination.mkdir(parents=True, exist_ok=False)
    _atomic_write(destination / EVIDENCE_FILENAME, evidence)
    return evidence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a bound Phase 8 E2/E3 Apple-GPU runtime.")
    parser.add_argument("--configuration", choices=tuple(sorted(PHASE8_CONFIGURATION_IDS)), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-artifact-binding-json", type=Path, required=True)
    parser.add_argument("--pilot-set-dir", type=Path, default=DEFAULT_PILOT_SET_DIR)
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    arguments = parser.parse_args(argv)
    evidence = run_phase8_preflight(
        configuration_id=arguments.configuration,
        output_dir=arguments.output_dir,
        model_artifact_binding=_read_json(arguments.model_artifact_binding_json),
        pilot_set_dir=arguments.pilot_set_dir,
        ollama_host=arguments.ollama_host,
    )
    print(json.dumps({"configuration_id": evidence["configuration_id"], "status": evidence["status"], "output_dir": str(arguments.output_dir.resolve())}, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "verified" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
