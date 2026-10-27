from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_supplementary_scenarios import (
    CandidateMonth,
    anchor_temporal_relation,
    candidate_months,
    market_scenario,
    market_summary,
    parse_season_window,
)


def test_parse_season_window_handles_calendar_and_cross_year_ranges():
    assert parse_season_window("Jun-Nov") == {6, 7, 8, 9, 10, 11}
    assert parse_season_window("Nov-Apr") == {11, 12, 1, 2, 3, 4}
    with pytest.raises(ValueError, match="Invalid"):
        parse_season_window("monsoon")


def test_candidate_months_are_newest_first_inside_the_final_window_and_exclude_anchor():
    site = {"crop": "wheat", "fixed_decision_date": "2026-04-30", "season_window": "Nov-Apr"}

    candidates = list(candidate_months(site))[:7]

    assert [candidate.decision_date for candidate in candidates] == [
        "2026-03-31", "2026-02-28", "2026-01-31", "2025-12-31",
        "2025-11-30", "2025-04-30", "2025-03-31",
    ]
    assert [candidate.rank for candidate in candidates] == list(range(1, 8))


def test_tomato_fixed_cutoff_allows_only_the_documented_post_anchor_rabi_months():
    site = {"crop": "tomato", "fixed_decision_date": "2025-12-31", "season_window": "Oct-Mar"}

    candidates = list(candidate_months(site))[:5]

    assert [candidate.decision_date for candidate in candidates] == [
        "2026-03-31", "2026-02-28", "2026-01-31", "2025-11-30", "2025-10-31",
    ]
    assert anchor_temporal_relation(site, candidates[0]) == "post_anchor_same_declared_season_historical_context"
    assert anchor_temporal_relation(site, candidates[3]) == "pre_anchor_historical_context"


def test_market_summary_requires_the_dynamic_month_specific_report_identity():
    candidate = CandidateMonth(2024, 10, 1)
    scenario = market_scenario("soybean", candidate)
    payload = {
        "success": True,
        "title": "Market-wise Wholesale Prices Monthly Analysis for Soyabean in Indore, Madhya Pradesh – October, 2024",
        "rows": [{"prices_october_2024": 4200}, {"prices_october_2024": 4400}],
    }

    result = market_summary(payload, scenario, "Madhya Pradesh", "Indore")

    assert result["market_priced_market_count"] == 2
    assert result["market_price_mean_as_reported"] == "4300.000"
    payload["title"] = "Market-wise report for September, 2024"
    with pytest.raises(ValueError, match="identity"):
        market_summary(payload, scenario, "Madhya Pradesh", "Indore")
