"""Regression checks for the stored evaluation-only conflict fixture registry."""
from __future__ import annotations

from collections import Counter

from evaluation.conflict_fixture_runner import (
    CONFLICT_ABLATION_SYSTEM_ID,
    ConflictFixtureRegistry,
    ConflictFixtureRunner,
    summarize_a6_conflict_ablation,
)
from graph.benchmark_workflow import BenchmarkMASWorkflow
from scripts.build_conflict_fixture_registry import EVALUATION_ONLY_LABEL, validate_registry


def test_conflict_fixture_registry_has_exact_auditable_coverage():
    fixtures = validate_registry()
    families = Counter(fixture["fixture_family"] for fixture in fixtures)
    crops = Counter(fixture["base_scenario"]["crop"] for fixture in fixtures)
    sites = Counter(fixture["base_scenario"]["site_id"] for fixture in fixtures)

    assert len(fixtures) == 60
    assert families == {
        "coordinator_resolution": 48,
        "pre_resolution_integrity_rejection": 6,
        "negative_control_no_comparable_conflict": 6,
    }
    assert set(crops.values()) == {10}
    assert len(sites) == 30
    assert set(sites.values()) == {2}
    assert all(fixture["fixture_classification"] == EVALUATION_ONLY_LABEL for fixture in fixtures)
    assert all(fixture["controlled_change_only"] is True for fixture in fixtures)


def test_all_stored_fixtures_match_the_real_deterministic_resolver_policy():
    runs = ConflictFixtureRunner().run_all(verify_raw_hashes=False)
    statuses = Counter(run.status for run in runs)

    assert len(runs) == 60
    assert all(run.expected_match for run in runs)
    assert statuses == {
        "passed": 54,
        "blocked_before_conflict_detection_and_coordination": 6,
    }
    assert sum(len(run.fixture_conflicts) for run in runs) == 48
    assert all(run.decision is None for run in runs if run.fixture_family == "pre_resolution_integrity_rejection")
    assert all(not run.decision.direct_farm_action_issued for run in runs if run.decision is not None)


def test_a6_fixture_ablation_detects_conflicts_but_withholds_coordinator_resolution():
    runs = ConflictFixtureRunner(system_id=CONFLICT_ABLATION_SYSTEM_ID).run_all(verify_raw_hashes=False)
    result = summarize_a6_conflict_ablation(runs)
    coordinator_runs = tuple(run for run in runs if run.fixture_family == "coordinator_resolution")

    assert len(runs) == 60
    assert all(run.expected_match for run in runs)
    assert len(coordinator_runs) == 48
    assert all(run.fixture_conflicts for run in coordinator_runs)
    assert all(run.fixture_resolution_record_count == 0 for run in coordinator_runs)
    assert all(not run.full_resolver_policy_match for run in coordinator_runs)
    assert result.expected_behavior_passed
    assert result.coordinator_required_fixture_count == 48
    assert result.detected_coordinator_fixture_count == 48
    assert result.resolved_coordinator_fixture_count == 0
    assert result.unresolved_coordinator_fixture_count == 48
    assert result.full_resolver_policy_passed_fixture_count == 12
    assert result.full_resolver_policy_compliance_rate == 0.2
    assert result.direct_farm_action_fixture_count == 0


def test_normal_workflow_does_not_load_evaluation_only_fixture_claims():
    fixture = ConflictFixtureRegistry().get("CF_RICE_01_SCOPE_DISTRICT_OVER_STATE")
    run = BenchmarkMASWorkflow().run(fixture["base_scenario"]["scenario_id"], verify_raw_hashes=False)

    assert all(
        claim.metadata.get("fixture_classification") != EVALUATION_ONLY_LABEL
        for claim in run.claims
    )
