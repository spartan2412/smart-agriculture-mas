from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_agmarknet_historical_market_evidence import (
    SCENARIOS,
    resolve_location,
    scenario_for_crop,
    source_district_name,
)


def test_frozen_scenarios_keep_crop_forms_and_last_day_dates_explicit():
    assert scenario_for_crop("rice").commodity_label == "Paddy(Common)"
    assert scenario_for_crop("rice").mapping_kind == "paddy_market_form_for_rice_crop"
    assert scenario_for_crop("maize").decision_date == "2026-03-31"
    assert scenario_for_crop("tomato").price_key == "prices_december_2025"
    assert set(SCENARIOS) == {"rice", "wheat", "maize", "chickpea", "soybean", "tomato"}


def test_location_resolution_requires_exact_source_location_with_documented_alias():
    states = [{
        "id": 28,
        "state_name": "Punjab",
        "districts": [{"id": 454, "district_name": "Bhatinda"}],
    }]

    assert source_district_name("Punjab", "Bathinda") == "Bhatinda"
    assert resolve_location(states, "Punjab", "Bathinda") == (28, "Punjab", 454, "Bhatinda")
