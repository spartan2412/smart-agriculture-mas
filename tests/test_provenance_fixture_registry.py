"""Regression tests for evaluation-only provenance/alignment fixtures."""
from __future__ import annotations

from collections import Counter

from evaluation.provenance_fixture_runner import (
    ProvenanceFixtureRegistry,
    ProvenanceFixtureRunner,
    summarize_provenance_fixture_runs,
)
from evaluation.provenance_fixture_oracle import evaluate_provenance_fixture_runs
from graph.benchmark_workflow import BenchmarkMASWorkflow
from scripts.build_provenance_fixture_registry import (
    EVALUATION_ONLY_LABEL,
    validate_registry,
)


EXPECTED_TYPES = {
    "plan_item_crop_scope_mismatch": 10,
    "plan_item_district_scope_mismatch": 10,
    "plan_item_season_scope_mismatch": 10,
    "plan_item_decision_date_scope_mismatch": 10,
    "plan_item_scenario_binding_mismatch": 10,
    "weather_payload_hash_mismatch": 10,
}


def test_provenance_fixture_registry_has_fixed_safe_coverage():
    fixtures = validate_registry()
    type_counts = Counter(fixture["fixture_type"] for fixture in fixtures)
    crop_counts = Counter(fixture["base_scenario"]["crop"] for fixture in fixtures)
    site_counts = Counter(fixture["base_scenario"]["site_id"] for fixture in fixtures)

    assert len(fixtures) == 60
    assert type_counts == EXPECTED_TYPES
    assert set(crop_counts.values()) == {10}
    assert len(site_counts) == 30
    assert set(site_counts.values()) == {2}
    assert all(fixture["fixture_classification"] == EVALUATION_ONLY_LABEL for fixture in fixtures)
    assert all(fixture["controlled_change_only"] is True for fixture in fixtures)
    assert all(fixture["expected"]["direct_farm_action_issued"] is False for fixture in fixtures)


def test_paired_a0_a5_integrity_fixture_protocol_and_oracle_pass():
    runs = ProvenanceFixtureRunner().run_all()
    summary = summarize_provenance_fixture_runs(runs)
    oracle = evaluate_provenance_fixture_runs(runs)

    assert len(runs) == 60
    assert all(run.expected_match for run in runs)
    assert summary.all_passed
    assert summary.a0_alignment_validator_blocked_count == 50
    assert summary.a5_alignment_validator_exposure_count == 50
    assert summary.shared_loader_payload_hash_blocked_count == 10
    assert summary.direct_farm_action_fixture_count == 0
    assert oracle.all_passed
    assert oracle.coverage_passed
    assert oracle.a0_alignment_validator_blocked_count == 50
    assert oracle.a5_alignment_validator_exposure_count == 50
    assert oracle.shared_loader_payload_hash_blocked_count == 10
    assert oracle.direct_farm_action_fixture_count == 0


def test_normal_workflow_cannot_load_provenance_fixture_overlays():
    fixture = ProvenanceFixtureRegistry().get("PAF_1_01_PLAN_ITEM_CROP_SCOPE_MISMATCH")
    run = BenchmarkMASWorkflow().run(fixture["base_scenario"]["scenario_id"], verify_raw_hashes=False)

    assert all(
        claim.metadata.get("fixture_classification") != EVALUATION_ONLY_LABEL
        for claim in run.claims
    )
