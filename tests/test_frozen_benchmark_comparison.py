"""Regression checks for the persisted A0--A6 comparison report."""
from __future__ import annotations

import json

from evaluation.frozen_benchmark_comparison import build_comparison, load_comparison_inputs


def test_frozen_architecture_comparison_validates_and_writes_paper_tables(tmp_path):
    loaded = load_comparison_inputs()

    assert [system.spec.system_id for system in loaded] == ["A0", "A1", "A2", "A3", "A4", "A5", "A6"]
    assert all(system.aggregate["scenario_count"] == 300 for system in loaded)
    assert loaded[0].aggregate["fully_passing_scenario_count"] == 300
    assert loaded[3].aggregate["fully_passing_scenario_count"] == 71
    assert loaded[5].aggregate["fully_passing_scenario_count"] == 300

    output_dir = tmp_path / "architecture-comparison"
    summary = build_comparison(output_dir=output_dir, render_figures=False)

    assert summary["system_count"] == 7
    assert summary["scenario_count"] == 300
    assert summary["table_count"] == 6
    assert summary["figure_count"] == 0
    for filename in (
        "TABLE_0_BENCHMARK_COMPOSITION.md",
        "TABLE_1_SYSTEM_COMPARISON.md",
        "TABLE_2_KEY_ORACLE_ABLATIONS.md",
        "TABLE_3_CONTROLLED_FIXTURE_PROTOCOLS.md",
        "TABLE_4_CROP_STRATIFICATION.md",
        "TABLE_5_DISTRICT_STRATIFICATION.md",
        "benchmark_composition.csv",
        "district_stratified_key_metrics.csv",
        "comparison_manifest.json",
    ):
        assert (output_dir / filename).is_file()

    manifest = json.loads((output_dir / "comparison_manifest.json").read_text(encoding="utf-8"))
    assert manifest["normal_scenario_count"] == 300
    assert manifest["systems"] == ["A0", "A1", "A2", "A3", "A4", "A5", "A6"]
    assert len(manifest["source_artifacts"]) == 32
    assert "comparison_manifest.json" in manifest["generated_outputs"]

