from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_nasa_power_water_context import build_features, expected_dates, power_dates


def test_power_dates_and_expected_dates_preserve_exact_window():
    start, end = power_dates("2025-11-01T00:00:00Z/2025-11-03T23:59:59Z")
    assert (start, end) == ("20251101", "20251103")
    assert expected_dates(start, end) == ["20251101", "20251102", "20251103"]


def test_build_features_uses_complete_non_fill_source_series():
    dates = ["20251101", "20251102"]
    values = {
        "T2M": [20, 22], "PRECTOTCORR": [1, 3], "RH2M": [50, 70], "WS2M": [2, 4],
        "ALLSKY_SFC_SW_DWN": [10, 12], "GWETROOT": [40, 60], "GWETTOP": [30, 50], "EVLAND": [2, 1],
    }
    payload = {"properties": {"parameter": {name: dict(zip(dates, series)) for name, series in values.items()}}}
    result = build_features(payload, "20251101", "20251102")
    assert result["water_gwetroot_mean_fraction"] == "50.000"
    assert result["weather_precipitation_total_mm"] == "4.000"
    assert result["water_precipitation_minus_land_evaporation_mm"] == "1.000"
    payload["properties"]["parameter"]["GWETROOT"]["20251102"] = -999.0
    with pytest.raises(ValueError, match="fill value"):
        build_features(payload, "20251101", "20251102")
