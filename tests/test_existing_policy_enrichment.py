from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_existing_policy_enrichment import month_sequence, season_position


def test_declared_cross_year_rabi_window_has_stable_month_order():
    assert month_sequence("Nov-Apr") == [11, 12, 1, 2, 3, 4]
    assert season_position(1, 6) == "early_declared_season_window"
    assert season_position(3, 6) == "middle_declared_season_window"
    assert season_position(6, 6) == "late_declared_season_window"


def test_declared_kharif_window_has_stable_month_order():
    assert month_sequence("Jun-Nov") == [6, 7, 8, 9, 10, 11]
