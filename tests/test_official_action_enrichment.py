from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_official_action_enrichment import conditional_reason, source_temporal_status
from scripts.collect_official_rag_sources import parse_latest_possible_date, source_is_relevant
from scripts.collect_predecision_sentinel_ndvi_timeseries import evenly_spaced_plan, trend_direction


def test_conservative_source_dates_never_assume_an_early_issue_day():
    assert parse_latest_possible_date("2023") == ("2023-12-31", "year")
    assert parse_latest_possible_date("March 2026") == ("2026-03-31", "month")
    assert parse_latest_possible_date("2021–22") == ("2022-06-30", "season_range")
    assert source_temporal_status("2025-06-01", "2025-08-31", "2026-06-30") == "blocked_source_not_yet_available"
    assert source_temporal_status("2026-07-01", "2025-08-31", "2026-06-30") == "blocked_source_effective_window_ended"
    assert source_temporal_status("2026-04-30", "2025-08-31", "2026-06-30") == "pass_source_time_valid"


def test_regulatory_records_are_collected_without_claiming_crop_scope():
    source = {"source_class": "national_regulatory_record", "crop_scope": "registered crops", "geography_scope": "India national"}
    assert source_is_relevant(source, {"rice"}, {"Punjab"})


def test_action_condition_gate_keeps_missing_farm_facts_explicit():
    assert conditional_reason({"stage": True, "soil": True, "diagnosis": True}) == (
        "actual_crop_stage;soil_test_for_personalised_dose;dated_diagnosis_or_threshold"
    )


def test_temporal_sampling_plan_and_trend_labels_do_not_use_ndvi_for_selection():
    candidates = [{"id": str(index)} for index in range(10)]
    plan = evenly_spaced_plan(candidates, 3)
    assert [row["id"] for row in plan] == ["0", "4", "9"]
    assert trend_direction(0.05) == "increase_at_least_0_05_ndvi"
    assert trend_direction(-0.05) == "decrease_at_least_0_05_ndvi"
    assert trend_direction(0.01) == "change_within_plus_or_minus_0_05_ndvi"
