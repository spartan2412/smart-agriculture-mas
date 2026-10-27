from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_anchor_scenarios import market_features, weather_features


def test_weather_features_reject_missing_or_fill_values_and_summarise_complete_series():
    payload = {
        "properties": {
            "parameter": {
                "T2M": {"20250101": 20.0, "20250102": 22.0},
                "PRECTOTCORR": {"20250101": 1.0, "20250102": 3.0},
                "RH2M": {"20250101": 50.0, "20250102": 70.0},
                "WS2M": {"20250101": 2.0, "20250102": 4.0},
            }
        }
    }

    result = weather_features(payload, 2)

    assert result["weather_t2m_mean_c"] == "21.000"
    assert result["weather_precipitation_total_mm"] == "4.000"
    payload["properties"]["parameter"]["T2M"]["20250102"] = -999.0
    with pytest.raises(ValueError, match="fill value"):
        weather_features(payload, 2)


def test_market_features_accepts_only_the_exact_frozen_report_identity():
    payload = {
        "success": True,
        "title": "Frozen report",
        "rows": [
            {"market": "A", "prices_november_2025": 100.0},
            {"market": "B", "prices_november_2025": 300.0},
        ],
    }

    result = market_features(payload, "rice", "Frozen report")

    assert result["market_priced_market_count"] == 2
    assert result["market_price_mean_as_reported"] == "200.000"
    with pytest.raises(ValueError, match="identity"):
        market_features(payload, "rice", "Different report")
