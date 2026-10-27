"""Freeze the official v2.2 paper-evidence release as a hash-checked manifest.

The paper package consumes raw frozen data as well as saved result archives.
This module serves a narrower release purpose: it identifies *only* the
versioned v2.2 result archives that constitute the official paper evidence.
Earlier result generations remain recoverable in the repository but are not
listed here and must not be presented as the final paper result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "results" / "v2_2-paper-artifacts" / "OFFICIAL_V2_2_RELEASE_MANIFEST.json"
)
RELEASE_VERSION = "v2.2-paper-evidence-release-1"

# This is intentionally explicit rather than a filesystem glob. A new result
# directory cannot silently become official paper evidence merely by sharing a
# name prefix.
OFFICIAL_ARCHIVES: tuple[tuple[str, str], ...] = (
    ("E0 deterministic full MAS", "results/v2_2-e0-full-mas"),
    ("E1-v5 30-site Apple-Metal pilot", "results/v2_2-e1-v5-30site-pilot"),
    ("E1-v5 Apple-Metal preflight", "results/v2_2-e1-v5-apple-gpu-preflight"),
    ("E1-v5 full MAS", "results/v2_2-e1-v5-full-mas"),
    ("A1 regional-plan-only baseline", "results/v2_2-a1-regional-plan-only"),
    ("A2 centralized scoped-RAG baseline", "results/v2_2-a2-centralized-rag"),
    ("A3 no scoped-RAG/operation-recovery ablation", "results/v2_2-a3-no-scoped-rag"),
    ("A4 no regional-plan ablation", "results/v2_2-a4-no-regional-plans"),
    ("A5 no provenance/alignment-gate ablation", "results/v2_2-a5-no-provenance-gates"),
    ("A6 no conflict-coordination ablation", "results/v2_2-a6-conflict-ablation"),
    ("Provenance/alignment fixture suite", "results/v2_2-provenance-gate-fixtures"),
    ("Controlled comparison package", "results/v2_2-phase7-controlled-comparison"),
    ("E2 14B Ollama Metal preflight", "results/v2_2-e2-apple-gpu-preflight"),
    ("E2 14B transfer result", "results/v2_2-e2-v5-relevance-14b"),
    ("E3 14B MLX Apple-GPU preflight", "results/v2_2-e3-apple-gpu-preflight"),
    ("E3 14B transfer result", "results/v2_2-e3-v5-relevance-14b-mlx"),
    ("E2/E3 transfer interpretation", "results/v2_2-phase8-e2-e3-relevance-transfer"),
    ("Final clean-checkout reproducibility archive", "results/v2_2-final-reproducibility-2026-10-12"),
    ("Phase 10 paper artifacts", "results/v2_2-paper-artifacts"),
)


class PaperReleaseManifestError(ValueError):
    """Raised when the declared evidence release cannot be safely frozen."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_metadata(root: Path) -> Mapping[str, Any]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.STDOUT
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - environment dependent
        raise PaperReleaseManifestError(f"Unable to inspect Git state: {exc}") from exc
    return {"commit": commit, "worktree_clean": not bool(status), "status": status}


def _relative_file_records(root: Path, archive: Path, output_file: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(item for item in archive.rglob("*") if item.is_file()):
        # A release manifest cannot meaningfully checksum itself. All other
        # Phase 10 files, including the Phase 10 source-input/output manifest,
        # remain in the evidence tree.
        if path.resolve() == output_file.resolve():
            continue
        records.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if not records:
        raise PaperReleaseManifestError(f"Official archive is empty: {archive}")
    return records


def build_release_manifest(
    *,
    project_root: Path | str = PROJECT_ROOT,
    output_file: Path | str = DEFAULT_OUTPUT,
    require_clean_git: bool = True,
) -> Mapping[str, Any]:
    """Hash the fixed v2.2 archive list and write one release manifest."""
    root = Path(project_root).resolve()
    destination = Path(output_file).resolve()
    if root not in destination.parents:
        raise PaperReleaseManifestError("Release manifest must be written inside the project root.")
    if destination.exists():
        raise PaperReleaseManifestError(f"Refusing to overwrite an existing release manifest: {destination}")
    git = _git_metadata(root)
    if require_clean_git and not git["worktree_clean"]:
        raise PaperReleaseManifestError("Official release manifest requires a clean committed worktree.")

    archive_rows: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    for label, relative in OFFICIAL_ARCHIVES:
        if not relative.startswith("results/v2_2-"):
            raise PaperReleaseManifestError(f"Non-v2.2 archive declared official: {relative}")
        archive = (root / relative).resolve()
        if root not in archive.parents or not archive.is_dir():
            raise PaperReleaseManifestError(f"Required official archive is missing: {relative}")
        records = _relative_file_records(root, archive, destination)
        content_sha256 = sha256(_canonical_json(records).encode("utf-8")).hexdigest()
        archive_rows.append(
            {
                "label": label,
                "path": relative,
                "file_count": len(records),
                "total_size_bytes": sum(int(record["size_bytes"]) for record in records),
                "content_sha256": content_sha256,
            }
        )
        all_records.extend(records)

    duplicate_paths = [record["path"] for record in all_records]
    if len(duplicate_paths) != len(set(duplicate_paths)):
        raise PaperReleaseManifestError("Official archive list overlaps or records a file twice.")
    overall_sha256 = sha256(_canonical_json(sorted(all_records, key=lambda row: row["path"])).encode("utf-8")).hexdigest()
    payload = {
        "release_version": RELEASE_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generation_git": git,
        "scope": {
            "official_result_archive_prefix": "results/v2_2-",
            "official_archive_count": len(archive_rows),
            "historical_result_archives_included": False,
            "historical_result_archives_policy": "Earlier result generations are recoverable but are not official paper evidence.",
            "raw_data_policy": "Frozen registry/scenario/enrichment/RAG source artifacts are recorded separately by the Phase 10 paper artifact manifest; this release manifest covers persisted result evidence only.",
        },
        "official_archives": archive_rows,
        "official_file_count": len(all_records),
        "official_total_size_bytes": sum(int(record["size_bytes"]) for record in all_records),
        "official_evidence_tree_sha256": overall_sha256,
        "excluded_self_file": str(destination.relative_to(root)),
        "phase10_manifest": {
            "path": "results/v2_2-paper-artifacts/paper_artifact_manifest.json",
            "sha256": _sha256_file(root / "results/v2_2-paper-artifacts/paper_artifact_manifest.json"),
        },
        "interpretation_boundary": (
            "This is a reproducibility release manifest for persisted v2.2 benchmark evidence. "
            "It does not add agricultural observations, field-outcome labels, or agricultural outcome-accuracy claims."
        ),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)
    result = build_release_manifest(output_file=arguments.output_file)
    print(
        json.dumps(
            {
                "release_version": result["release_version"],
                "official_archive_count": result["scope"]["official_archive_count"],
                "official_file_count": result["official_file_count"],
                "official_evidence_tree_sha256": result["official_evidence_tree_sha256"],
                "output_file": str(Path(arguments.output_file).resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
