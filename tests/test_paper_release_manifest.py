"""Regression checks for the official v2.2 evidence-release manifest."""
from __future__ import annotations

import json

from evaluation import paper_release_manifest


def test_release_manifest_hashes_only_the_explicit_v2_2_archive_set(tmp_path, monkeypatch):
    monkeypatch.setattr(
        paper_release_manifest,
        "_git_metadata",
        lambda _root: {"commit": "f" * 40, "worktree_clean": True, "status": ""},
    )
    for index, (_label, relative) in enumerate(paper_release_manifest.OFFICIAL_ARCHIVES):
        archive = tmp_path / relative
        archive.mkdir(parents=True, exist_ok=True)
        filename = "paper_artifact_manifest.json" if relative.endswith("v2_2-paper-artifacts") else "record.json"
        (archive / filename).write_text(json.dumps({"index": index}) + "\n", encoding="utf-8")

    output = tmp_path / "results/v2_2-paper-artifacts/OFFICIAL_V2_2_RELEASE_MANIFEST.json"
    manifest = paper_release_manifest.build_release_manifest(
        project_root=tmp_path,
        output_file=output,
    )

    assert output.is_file()
    assert manifest["scope"]["official_archive_count"] == len(paper_release_manifest.OFFICIAL_ARCHIVES)
    assert manifest["official_file_count"] == len(paper_release_manifest.OFFICIAL_ARCHIVES)
    assert all(item["path"].startswith("results/v2_2-") for item in manifest["official_archives"])
    assert manifest["scope"]["historical_result_archives_included"] is False
    assert len(manifest["official_evidence_tree_sha256"]) == 64
