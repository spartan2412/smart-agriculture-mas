from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_market_recovery_feasibility import previous_months


def test_prior_months_cross_the_year_boundary():
    assert previous_months("2026-01-31") == [(2025, 10), (2025, 11), (2025, 12)]
