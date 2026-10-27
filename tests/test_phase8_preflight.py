"""Small deterministic checks for Phase 8 preflight artifact integrity."""
from __future__ import annotations

from evaluation.phase8_preflight import _directory_tree_sha256


def test_mlx_artifact_hash_excludes_resumable_download_bookkeeping(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "weights.safetensors").write_bytes(b"weights")
    initial = _directory_tree_sha256(model)
    cache = model / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "metadata").write_text("transport-state", encoding="utf-8")

    assert _directory_tree_sha256(model) == initial
