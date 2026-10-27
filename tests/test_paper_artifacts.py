"""Regression checks for the Phase 10 paper-artifact generator."""
from __future__ import annotations

import json

from evaluation.paper_artifacts import build_paper_artifacts


def test_phase10_generator_writes_source_traceable_tables_and_figures(tmp_path):
    output_dir = tmp_path / "paper-artifacts"
    result = build_paper_artifacts(output_dir=output_dir, render_figures=True)

    assert result["scenario_count"] == 300
    assert result["table_count"] == 10
    assert result["figure_count"] == 4
    for filename in (
        "README.md",
        "TABLE_1_DATASET_COMPOSITION.md",
        "TABLE_2_AGENT_RESPONSIBILITIES.md",
        "TABLE_3_MAIN_STRUCTURAL_RESULTS.md",
        "TABLE_4_BOUNDED_LLM_RELEVANCE.md",
        "TABLE_5_CONFLICT_RESOLUTION.md",
        "TABLE_6_PROVENANCE_GATE.md",
        "TABLE_7_STRATIFIED_CONFORMANCE.md",
        "TABLE_8_CASE_STUDIES.md",
        "TABLE_9_RUNTIME_AND_BACKEND.md",
        "TABLE_10_14B_TRANSFER_NEGATIVE_RESULTS.md",
        "e2_e3_transfer_negative_results.csv",
        "FIGURE_1_SYSTEM_ARCHITECTURE.png",
        "FIGURE_4_RUNTIME_AND_RELIABILITY.pdf",
    ):
        assert (output_dir / filename).is_file(), filename

    manifest = json.loads((output_dir / "paper_artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["derived_counts"]["scenario_count"] == 300
    assert manifest["derived_counts"]["site_count"] == 30
    assert len(manifest["input_artifacts"]) >= 20
    assert "not agricultural outcome accuracy" in manifest["interpretation_boundary"]
    assert {"commit", "worktree_clean", "status"} <= set(manifest["generation_git"])

    structural = (output_dir / "TABLE_3_MAIN_STRUCTURAL_RESULTS.md").read_text(encoding="utf-8")
    assert "300/300 (100.0%)" in structural
    assert "not** irrigation" in structural

    transfer = (output_dir / "TABLE_10_14B_TRANSFER_NEGATIVE_RESULTS.md").read_text(encoding="utf-8")
    assert "9.4%" in transfer
    assert "25.0%" in transfer
    assert "not a full-MAS" in transfer
