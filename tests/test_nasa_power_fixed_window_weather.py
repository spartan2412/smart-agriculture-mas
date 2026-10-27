from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_nasa_power_fixed_window_weather import PARAMETERS, power_dates


def test_power_dates_preserve_the_frozen_month_bounds():
    assert power_dates("2025-11-01T00:00:00Z/2025-11-30T23:59:59Z") == ("20251101", "20251130")
    assert PARAMETERS == ("T2M", "PRECTOTCORR", "RH2M", "WS2M")
