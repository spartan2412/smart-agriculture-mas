"""Regression tests for the read-only final Phase 7 comparison package."""
from __future__ import annotations

import json

from evaluation.final_phase7_comparison import build_phase7_comparison


def test_phase7_comparison_validates_persisted_results_and_writes_package(tmp_path):
    output_dir = tmp_path / "phase7"
    summary = build_phase7_comparison(output_dir=output_dir, render_figures=False)

    assert summary["scenario_count"] == 300
    assert summary["e0_full_oracle_pass_count"] == 300
    assert summary["e1_full_oracle_pass_count"] == 300
    assert summary["e1_bounded_llm_call_count"] == 2400
    assert summary["heldout_question_count"] == 96
    assert summary["architecture_system_count"] == 7
    assert summary["qualitative_case_count"] == 6

    for filename in (
        "README.md",
        "TABLE_6_E0_E1_RUNTIME_AND_SAFETY.md",
        "TABLE_7_E1_V5_BOUNDED_LLM_RUNTIME.md",
        "TABLE_8_E1_V5_FINAL_HELDOUT_RELEVANCE.md",
        "TABLE_9_PAIRED_OUTPUT_BOUNDARY.md",
        "QUALITATIVE_FARMER_MESSAGE_CASES.md",
        "e0_e1_paired_trace_comparison.csv",
        "e1_v5_final_heldout_relevance.csv",
        "phase7_comparison_manifest.json",
    ):
        assert (output_dir / filename).is_file()

    manifest = json.loads((output_dir / "phase7_comparison_manifest.json").read_text(encoding="utf-8"))
    assert manifest["population"] == "same_frozen_300_scenarios_for_E0_and_E1"
    assert manifest["final_heldout_relevance"]["acceptance_passed"] is True
    assert manifest["paired_output_summary"]["e1_fallback_count"] == 0
    assert len(manifest["shared_frozen_data_hashes"]) >= 20

    assert (output_dir / "architecture-ablation" / "TABLE_3_CONTROLLED_FIXTURE_PROTOCOLS.md").is_file()
