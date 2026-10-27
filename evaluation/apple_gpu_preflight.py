"""Freeze Apple-GPU pilot inputs and verify a local bounded-LLM runtime.

This module deliberately separates *hardware/runtime verification* from the
agricultural benchmark.  It selects the 30 already-admitted anchor scenarios
(one per final study site) and records whether a requested local-model backend
was actually observed using Apple GPU memory.  It neither loads agricultural
evidence nor runs the MAS.

For Ollama, PyTorch MPS availability is intentionally not treated as proof of
acceleration.  The probe invokes Ollama's local API with ``keep_alive`` and
then requires the same model to appear in ``/api/ps`` with non-zero
``size_vram``.  On Apple Silicon this is the runtime's documented GPU-resident
memory field, including unified-memory devices.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import csv
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any, Mapping, Optional, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANCHOR_MANIFEST_PATH = PROJECT_ROOT / "data" / "scenarios" / "manifests" / "anchor_scenario_manifest.csv"
DEFAULT_PILOT_SET_DIR = PROJECT_ROOT / "data" / "pilot_sets" / "apple_gpu_30_anchor_scenarios"
DEFAULT_PROTOCOL_PATH = PROJECT_ROOT / "evaluation" / "experiment_protocol.json"
PILOT_SET_FILENAME = "scenario_ids.csv"
PILOT_MANIFEST_FILENAME = "manifest.json"
EVIDENCE_FILENAME = "acceleration_evidence.json"
PILOT_SET_VERSION = "1.0"
EVIDENCE_SCHEMA_VERSION = "1.0"
EXPECTED_PILOT_SCENARIO_COUNT = 30
EXPECTED_FOCUSED_CROPS = ("rice", "wheat", "maize", "chickpea", "soybean", "tomato")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
OLLAMA_BLOB_RE = re.compile(r"sha256-([a-f0-9]{64})")


class AppleGPUPreflightError(RuntimeError):
    """Raised when frozen pilot inputs or runtime evidence are invalid."""


@dataclass(frozen=True)
class FrozenPilotSet:
    """Validated one-anchor-per-site pilot population."""

    directory: Path
    manifest: Mapping[str, Any]
    rows: tuple[Mapping[str, str], ...]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _git_metadata(project_root: Path) -> Mapping[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True, stderr=subprocess.STDOUT
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=project_root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AppleGPUPreflightError(f"Unable to inspect Git state: {exc}") from exc
    return {"commit": commit, "clean": str(not status).lower()}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise AppleGPUPreflightError(f"Pilot source CSV is missing: {path}")
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def _read_protocol(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise AppleGPUPreflightError(f"Experiment protocol is missing: {path}")
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AppleGPUPreflightError(f"Experiment protocol is invalid JSON: {exc}") from exc
    if protocol.get("protocol_version") not in {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}:
        raise AppleGPUPreflightError("Unsupported experiment protocol version.")
    return protocol


def _pilot_rows_from_anchors(anchor_manifest: Path) -> tuple[dict[str, str], ...]:
    anchors = _read_csv(anchor_manifest)
    if len(anchors) != EXPECTED_PILOT_SCENARIO_COUNT:
        raise AppleGPUPreflightError(
            f"Expected {EXPECTED_PILOT_SCENARIO_COUNT} anchor scenarios, found {len(anchors)}."
        )
    required_fields = {
        "scenario_id",
        "scenario_type",
        "scenario_status",
        "site_id",
        "crop",
        "state",
        "district",
        "season",
        "decision_date",
    }
    missing = sorted(required_fields - set(anchors[0])) if anchors else sorted(required_fields)
    if missing:
        raise AppleGPUPreflightError(f"Anchor manifest lacks pilot fields: {', '.join(missing)}")

    rows: list[dict[str, str]] = []
    for anchor in anchors:
        if anchor["scenario_type"] != "verified_anchor_context":
            raise AppleGPUPreflightError(f"Pilot row is not a verified anchor: {anchor['scenario_id']}")
        if not anchor["scenario_status"].startswith("ready_for_context_evaluation"):
            raise AppleGPUPreflightError(f"Pilot anchor is not admitted: {anchor['scenario_id']}")
        rows.append(
            {
                "scenario_id": anchor["scenario_id"],
                "site_id": anchor["site_id"],
                "crop": anchor["crop"],
                "state": anchor["state"],
                "district": anchor["district"],
                "season": anchor["season"],
                "decision_date": anchor["decision_date"],
                "selection_rule": "one_verified_anchor_per_final_study_site",
            }
        )
    rows.sort(key=lambda item: (item["crop"], item["state"], item["district"], item["scenario_id"]))
    if len({row["scenario_id"] for row in rows}) != EXPECTED_PILOT_SCENARIO_COUNT:
        raise AppleGPUPreflightError("Pilot selection contains duplicate scenario IDs.")
    if len({row["site_id"] for row in rows}) != EXPECTED_PILOT_SCENARIO_COUNT:
        raise AppleGPUPreflightError("Pilot selection must contain exactly one scenario per site.")
    crops = {row["crop"] for row in rows}
    if crops != set(EXPECTED_FOCUSED_CROPS):
        raise AppleGPUPreflightError(f"Pilot crop coverage differs from frozen scope: {sorted(crops)}")
    if any(sum(row["crop"] == crop for row in rows) != 5 for crop in EXPECTED_FOCUSED_CROPS):
        raise AppleGPUPreflightError("Pilot selection must contain five verified sites per focused crop.")
    return tuple(rows)


def build_pilot_set(
    *,
    output_dir: Path | str = DEFAULT_PILOT_SET_DIR,
    anchor_manifest: Path | str = ANCHOR_MANIFEST_PATH,
    project_root: Path | str = PROJECT_ROOT,
) -> FrozenPilotSet:
    """Freeze the 30 verified anchor contexts, refusing to overwrite a set."""
    root = Path(project_root).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise AppleGPUPreflightError(f"Refusing to overwrite frozen pilot set: {destination}")
        destination.rmdir()
    source_manifest = Path(anchor_manifest).resolve()
    rows = _pilot_rows_from_anchors(source_manifest)
    fields = tuple(rows[0])
    # csv.writer preserves deterministic field order and quoting in the durable artifact.
    destination.mkdir(parents=True, exist_ok=False)
    scenario_path = destination / PILOT_SET_FILENAME
    with scenario_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    row_identity = [
        {key: row[key] for key in fields if key != "selection_rule"}
        for row in rows
    ]
    manifest = {
        "pilot_set_version": PILOT_SET_VERSION,
        "status": "frozen_one_anchor_per_verified_site",
        "selection_rule": "one_verified_anchor_per_final_study_site",
        "scenario_count": len(rows),
        "unique_site_count": len({row["site_id"] for row in rows}),
        "focused_crops": list(EXPECTED_FOCUSED_CROPS),
        "per_crop_site_count": 5,
        "scenario_file": PILOT_SET_FILENAME,
        "scenario_file_sha256": _sha256_file(scenario_path),
        "pilot_identity_sha256": _canonical_sha256(row_identity),
        "anchor_manifest_path": str(source_manifest.relative_to(root)),
        "anchor_manifest_sha256": _sha256_file(source_manifest),
        "builder": {
            "module": "evaluation/apple_gpu_preflight.py",
            "module_sha256": _sha256_file(Path(__file__).resolve()),
            "git": _git_metadata(root),
        },
    }
    _atomic_write_text(
        destination / PILOT_MANIFEST_FILENAME,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return load_pilot_set(destination, project_root=root)


def load_pilot_set(
    directory: Path | str = DEFAULT_PILOT_SET_DIR,
    *,
    project_root: Path | str = PROJECT_ROOT,
) -> FrozenPilotSet:
    """Load and verify the immutable one-per-site pilot population."""
    root = Path(project_root).resolve()
    destination = Path(directory).resolve()
    manifest_path = destination / PILOT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise AppleGPUPreflightError(f"Pilot-set manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AppleGPUPreflightError(f"Pilot-set manifest is invalid JSON: {exc}") from exc
    if manifest.get("pilot_set_version") != PILOT_SET_VERSION:
        raise AppleGPUPreflightError("Unsupported pilot-set version.")
    scenario_path = destination / str(manifest.get("scenario_file", ""))
    if not scenario_path.is_file() or _sha256_file(scenario_path) != manifest.get("scenario_file_sha256"):
        raise AppleGPUPreflightError("Pilot scenario-file hash differs from frozen manifest.")
    rows = tuple(_read_csv(scenario_path))
    expected = _pilot_rows_from_anchors(root / str(manifest.get("anchor_manifest_path", "")))
    if tuple(rows) != expected:
        raise AppleGPUPreflightError("Pilot rows differ from the one-per-site frozen anchor selection.")
    row_identity = [
        {key: row[key] for key in rows[0] if key != "selection_rule"}
        for row in rows
    ]
    if _canonical_sha256(row_identity) != manifest.get("pilot_identity_sha256"):
        raise AppleGPUPreflightError("Pilot identity hash differs from frozen manifest.")
    anchor_path = root / str(manifest["anchor_manifest_path"])
    if _sha256_file(anchor_path) != manifest.get("anchor_manifest_sha256"):
        raise AppleGPUPreflightError("Pilot source anchor manifest hash differs from frozen manifest.")
    return FrozenPilotSet(directory=destination, manifest=manifest, rows=rows)


def _run_text(*command: str) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable:{type(exc).__name__}:{str(exc).strip()}"


def _sysctl_value(name: str) -> Optional[str]:
    value = _run_text("sysctl", "-n", name)
    return None if value.startswith("unavailable:") else value


def _hardware_metadata() -> Mapping[str, Any]:
    memory = _sysctl_value("hw.memsize")
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "hardware_model": _sysctl_value("hw.model"),
        "apple_soc": _sysctl_value("machdep.cpu.brand_string"),
        "unified_memory_bytes": int(memory) if memory and memory.isdigit() else None,
        "unified_memory_gib": round(int(memory) / (1024**3), 3) if memory and memory.isdigit() else None,
        "pytorch_mps": {
            "used_as_ollama_acceleration_proof": False,
            "reason": "Ollama uses its own Metal runtime; only Ollama runtime residency is accepted for E1/E2.",
        },
    }


def _ollama_json(host: str, path: str, payload: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
    encoded = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        host.rstrip("/") + path,
        data=encoded,
        headers={"Content-Type": "application/json"} if encoded is not None else {},
    )
    try:
        with urlopen(request, timeout=120) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise AppleGPUPreflightError(f"Ollama API {path} failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(decoded, Mapping):
        raise AppleGPUPreflightError(f"Ollama API {path} did not return a JSON object.")
    return decoded


def _model_blob_from_modelfile(modelfile: str) -> tuple[Optional[Path], Optional[str]]:
    match = OLLAMA_BLOB_RE.search(modelfile or "")
    if not match:
        return None, None
    raw_path = None
    for line in str(modelfile).splitlines():
        if line.startswith("FROM ") and "sha256-" in line:
            raw_path = line.removeprefix("FROM ").strip()
            break
    return (Path(raw_path).expanduser() if raw_path else None), match.group(1)


def _probe_ollama(
    *,
    configuration: Mapping[str, Any],
    bounded_policy: Mapping[str, Any],
    host: str,
) -> Mapping[str, Any]:
    """Perform a harmless JSON probe and require observed GPU residency."""
    model_tag = str(configuration.get("ollama_tag", ""))
    if not model_tag:
        raise AppleGPUPreflightError("Ollama configuration lacks a model tag.")
    started = time.perf_counter()
    version = _ollama_json(host, "/api/version")
    shown = _ollama_json(host, "/api/show", {"name": model_tag, "verbose": False})
    probe_options = {"temperature": 0.0, "num_predict": 16}
    response = _ollama_json(
        host,
        "/api/generate",
        {
            "model": model_tag,
            "prompt": 'Return exactly this JSON object: {"preflight":"ok"}.',
            "format": "json",
            "stream": False,
            "keep_alive": "5m",
            "options": probe_options,
        },
    )
    ps = _ollama_json(host, "/api/ps")
    loaded_models = ps.get("models", [])
    if not isinstance(loaded_models, list):
        loaded_models = []
    resident = next(
        (item for item in loaded_models if isinstance(item, Mapping) and item.get("name") == model_tag),
        None,
    )
    details = shown.get("details", {}) if isinstance(shown.get("details"), Mapping) else {}
    model_info = shown.get("model_info", {}) if isinstance(shown.get("model_info"), Mapping) else {}
    blob_path, blob_sha256 = _model_blob_from_modelfile(str(shown.get("modelfile", "")))
    blob_file_hash = _sha256_file(blob_path) if blob_path and blob_path.is_file() else None
    response_text = str(response.get("response", ""))
    try:
        response_json = json.loads(response_text)
    except json.JSONDecodeError:
        response_json = None
    gpu_resident_bytes = int(resident.get("size_vram", 0)) if isinstance(resident, Mapping) else 0
    protocol_blob = str(configuration.get("installed_model_blob_sha256", ""))
    expected_prefix = str(configuration.get("installed_ollama_model_id_prefix", ""))
    expected_quantization = str(configuration.get("quantization", ""))
    observed_digest = str(resident.get("digest", "")) if isinstance(resident, Mapping) else ""
    checks = {
        "probe_completed": response.get("done") is True and response_json == {"preflight": "ok"},
        "model_loaded_in_ollama": resident is not None,
        "gpu_residency_observed": gpu_resident_bytes > 0,
        "protocol_model_digest_prefix_matches": bool(expected_prefix) and observed_digest.startswith(expected_prefix),
        "protocol_blob_hash_matches": bool(protocol_blob) and blob_sha256 == protocol_blob and blob_file_hash == protocol_blob,
        "protocol_quantization_matches": bool(expected_quantization) and details.get("quantization_level") == expected_quantization,
        "apple_silicon_host": platform.system() == "Darwin" and platform.machine() == "arm64",
    }
    return {
        "backend": "ollama",
        "runtime": {
            "runtime_name": "Ollama",
            "runtime_version": version.get("version"),
            "host": host,
            "verification_method": "local_api_generate_then_api_ps_size_vram",
            "probe_elapsed_ms": round((time.perf_counter() - started) * 1000),
        },
        "model": {
            "tag": model_tag,
            "ollama_digest": observed_digest or None,
            "ollama_digest_prefix": observed_digest[:12] or None,
            "model_blob_sha256": blob_sha256,
            "model_blob_file_sha256": blob_file_hash,
            "base_model_name": model_info.get("general.base_model.0.name"),
            "base_model_repository": model_info.get("general.base_model.0.repo_url"),
            "model_revision_or_commit": "not_exposed_by_local_ollama_metadata",
            "model_revision_status": "unavailable_not_inferred",
            "parameter_count": model_info.get("general.parameter_count"),
            "parameter_size": details.get("parameter_size"),
            "quantization": details.get("quantization_level"),
            "format": details.get("format"),
        },
        "generation_parameters": {
            "benchmark_temperature": bounded_policy.get("temperature"),
            "benchmark_max_tokens_per_call": bounded_policy.get("max_tokens_per_call"),
            "benchmark_max_selected_facts": bounded_policy.get("max_selected_facts"),
            "probe_temperature": probe_options["temperature"],
            "probe_num_predict": probe_options["num_predict"],
            "probe_keep_alive": "5m",
        },
        "acceleration": {
            "requested_runtime": "Ollama Metal / Apple GPU",
            "observed_model_resident_in_gpu_memory": gpu_resident_bytes > 0,
            "observed_gpu_resident_bytes": gpu_resident_bytes,
            "observed_model_bytes": int(resident.get("size", 0)) if isinstance(resident, Mapping) else 0,
            "observed_context_length": int(resident.get("context_length", 0)) if isinstance(resident, Mapping) else 0,
            "evidence": "Ollama /api/ps reported size_vram > 0 for the just-probed configured model.",
            "pytorch_mps_is_not_runtime_proof": True,
        },
        "probe": {
            "response_sha256": sha256(response_text.encode("utf-8")).hexdigest(),
            "response_json_valid": response_json == {"preflight": "ok"},
            "done": response.get("done"),
            "load_duration_ns": response.get("load_duration"),
            "total_duration_ns": response.get("total_duration"),
            "prompt_eval_count": response.get("prompt_eval_count"),
            "eval_count": response.get("eval_count"),
        },
        "checks": checks,
    }


def _pending_backend_evidence(configuration: Mapping[str, Any], reason: str) -> Mapping[str, Any]:
    """Return an explicit non-verified result for an unavailable future runtime."""
    backend = str(configuration.get("backend", ""))
    return {
        "backend": backend,
        "runtime": {"runtime_name": "MLX-LM" if backend == "mlx-lm" else backend},
        "model": {"model_family": configuration.get("model_family")},
        "generation_parameters": {},
        "acceleration": {
            "requested_runtime": "MLX Apple GPU" if backend == "mlx-lm" else "Ollama Metal / Apple GPU",
            "observed_model_resident_in_gpu_memory": False,
            "observed_gpu_resident_bytes": 0,
            "pytorch_mps_is_not_runtime_proof": True,
        },
        "probe": {"not_run_reason": reason},
        "checks": {"runtime_ready": False},
    }


def run_preflight(
    *,
    configuration_id: str,
    output_dir: Path | str,
    pilot_set_dir: Path | str = DEFAULT_PILOT_SET_DIR,
    protocol_path: Path | str = DEFAULT_PROTOCOL_PATH,
    project_root: Path | str = PROJECT_ROOT,
    ollama_host: str = "http://localhost:11434",
) -> Mapping[str, Any]:
    """Write one immutable Apple-GPU preflight result for an experiment configuration."""
    root = Path(project_root).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise AppleGPUPreflightError(f"Refusing to overwrite existing preflight output: {destination}")
        destination.rmdir()
    protocol_file = Path(protocol_path).resolve()
    protocol = _read_protocol(protocol_file)
    configurations = protocol.get("experiment_configurations", {})
    configuration = configurations.get(configuration_id) if isinstance(configurations, Mapping) else None
    if not isinstance(configuration, Mapping) or configuration.get("backend") == "none":
        raise AppleGPUPreflightError(f"{configuration_id} is not an Apple-GPU bounded-LLM configuration.")
    pilot = load_pilot_set(pilot_set_dir, project_root=root)
    hardware = _hardware_metadata()
    if configuration.get("backend") == "ollama":
        backend_evidence = _probe_ollama(
            configuration=configuration,
            bounded_policy=protocol["bounded_llm_policy"],
            host=ollama_host,
        )
    else:
        backend_evidence = _pending_backend_evidence(
            configuration,
            "MLX-LM adapter and bound model artifact are not installed/configured for this preflight.",
        )
    checks = backend_evidence.get("checks", {})
    all_checks_pass = isinstance(checks, Mapping) and bool(checks) and all(checks.values())
    evidence = {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "status": "verified" if all_checks_pass else "not_verified",
        "configuration_id": configuration_id,
        "configuration": dict(configuration),
        "recorded_at_utc": _utc_timestamp(),
        "hardware": hardware,
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
            "protocol_path": str(protocol_file.relative_to(root)),
            "protocol_sha256": _sha256_file(protocol_file),
            "preflight_module": "evaluation/apple_gpu_preflight.py",
            "preflight_module_sha256": _sha256_file(Path(__file__).resolve()),
            "git": _git_metadata(root),
        },
        "formal_boundary": {
            "not_an_agricultural_benchmark_run": True,
            "does_not_prove_pytorch_mps_for_ollama": True,
            "next_required_run": "Run the fixed 30-scenario MAS pilot only from a clean committed worktree.",
        },
    }
    destination.mkdir(parents=True, exist_ok=False)
    _atomic_write_text(
        destination / EVIDENCE_FILENAME,
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return evidence


def validate_acceleration_evidence(
    evidence: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    configuration_id: str,
    project_root: Path | str = PROJECT_ROOT,
) -> None:
    """Validate evidence passed to the batch runner; never trust ``status`` alone."""
    if evidence.get("evidence_schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise AppleGPUPreflightError("Acceleration evidence schema version is unsupported.")
    if evidence.get("status") != "verified" or evidence.get("configuration_id") != configuration_id:
        raise AppleGPUPreflightError("Acceleration evidence is not verified for this configuration.")
    configurations = protocol.get("experiment_configurations", {})
    configuration = configurations.get(configuration_id) if isinstance(configurations, Mapping) else None
    if not isinstance(configuration, Mapping):
        raise AppleGPUPreflightError("Experiment configuration is unknown to acceleration validation.")
    if evidence.get("configuration") != dict(configuration):
        raise AppleGPUPreflightError("Acceleration evidence configuration differs from the frozen protocol.")
    root = Path(project_root).resolve()
    integrity = evidence.get("artifact_integrity", {})
    if not isinstance(integrity, Mapping):
        raise AppleGPUPreflightError("Acceleration evidence lacks preflight artifact integrity metadata.")
    protocol_relative = str(integrity.get("protocol_path", ""))
    preflight_relative = str(integrity.get("preflight_module", ""))
    protocol_path = (root / protocol_relative).resolve()
    preflight_path = (root / preflight_relative).resolve()
    if (
        root not in protocol_path.parents
        or root not in preflight_path.parents
        or not protocol_path.is_file()
        or not preflight_path.is_file()
        or _sha256_file(protocol_path) != integrity.get("protocol_sha256")
        or _sha256_file(preflight_path) != integrity.get("preflight_module_sha256")
    ):
        raise AppleGPUPreflightError("Acceleration evidence was created with changed protocol or preflight code.")
    pilot = evidence.get("pilot_set", {})
    if not isinstance(pilot, Mapping):
        raise AppleGPUPreflightError("Acceleration evidence has no pilot-set identity.")
    if pilot.get("scenario_count") != EXPECTED_PILOT_SCENARIO_COUNT or pilot.get("unique_site_count") != EXPECTED_PILOT_SCENARIO_COUNT:
        raise AppleGPUPreflightError("Acceleration evidence did not use all 30 verified pilot sites.")
    frozen_pilot = load_pilot_set(project_root=root)
    if (
        pilot.get("pilot_identity_sha256") != frozen_pilot.manifest["pilot_identity_sha256"]
        or pilot.get("scenario_file_sha256") != frozen_pilot.manifest["scenario_file_sha256"]
        or pilot.get("manifest_sha256") != _sha256_file(frozen_pilot.directory / PILOT_MANIFEST_FILENAME)
    ):
        raise AppleGPUPreflightError("Acceleration evidence references a different pilot scenario population.")
    hardware = evidence.get("hardware", {})
    if not isinstance(hardware, Mapping) or hardware.get("system") != "Darwin" or hardware.get("machine") != "arm64":
        raise AppleGPUPreflightError("Acceleration evidence is not from an Apple-Silicon macOS host.")
    if not isinstance(hardware.get("unified_memory_bytes"), int) or hardware["unified_memory_bytes"] <= 0:
        raise AppleGPUPreflightError("Acceleration evidence lacks unified-memory capacity.")
    backend = evidence.get("backend_evidence", {})
    if not isinstance(backend, Mapping) or backend.get("backend") != configuration.get("backend"):
        raise AppleGPUPreflightError("Acceleration evidence backend differs from the requested configuration.")
    acceleration = backend.get("acceleration", {})
    checks = backend.get("checks", {})
    if (
        not isinstance(acceleration, Mapping)
        or not acceleration.get("observed_model_resident_in_gpu_memory")
        or int(acceleration.get("observed_gpu_resident_bytes", 0)) <= 0
        or not isinstance(checks, Mapping)
        or not checks
        or not all(checks.values())
    ):
        raise AppleGPUPreflightError("Acceleration evidence lacks an observed GPU-resident model probe.")
    if configuration.get("backend") == "ollama":
        model = backend.get("model", {})
        if not isinstance(model, Mapping):
            raise AppleGPUPreflightError("Ollama acceleration evidence lacks model identity.")
        if model.get("tag") != configuration.get("ollama_tag"):
            raise AppleGPUPreflightError("Ollama acceleration evidence model tag differs from protocol.")
        if model.get("model_blob_sha256") != configuration.get("installed_model_blob_sha256"):
            raise AppleGPUPreflightError("Ollama acceleration evidence blob hash differs from protocol.")
        if model.get("quantization") != configuration.get("quantization"):
            raise AppleGPUPreflightError("Ollama acceleration evidence quantization differs from protocol.")
    generation = backend.get("generation_parameters", {})
    policy = protocol.get("bounded_llm_policy", {})
    if not isinstance(generation, Mapping) or not isinstance(policy, Mapping) or (
        generation.get("benchmark_temperature") != policy.get("temperature")
        or generation.get("benchmark_max_tokens_per_call") != policy.get("max_tokens_per_call")
        or generation.get("benchmark_max_selected_facts") != policy.get("max_selected_facts")
    ):
        raise AppleGPUPreflightError("Acceleration evidence generation settings differ from the frozen policy.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze and verify an Apple-GPU bounded-LLM pilot preflight.")
    parser.add_argument("--configuration", choices=("E1", "E2", "E3"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pilot-set-dir", type=Path, default=DEFAULT_PILOT_SET_DIR)
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    arguments = parser.parse_args(argv)
    evidence = run_preflight(
        configuration_id=arguments.configuration,
        output_dir=arguments.output_dir,
        pilot_set_dir=arguments.pilot_set_dir,
        ollama_host=arguments.ollama_host,
    )
    print(
        json.dumps(
            {
                "configuration_id": evidence["configuration_id"],
                "status": evidence["status"],
                "output_dir": str(arguments.output_dir.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if evidence["status"] == "verified" else 2


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    raise SystemExit(main())
