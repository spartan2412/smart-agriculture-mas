from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.select_representative_cropland_cells import decision_window, feature_for_district, point_in_geometry


def test_point_in_geometry_handles_polygon_holes_and_multipolygons():
    polygon_with_hole = {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
            [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]],
        ],
    }
    assert point_in_geometry(0.5, 0.5, polygon_with_hole) is True
    assert point_in_geometry(2.0, 2.0, polygon_with_hole) is False
    multi = {"type": "MultiPolygon", "coordinates": [polygon_with_hole["coordinates"], [[[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]]]}
    assert point_in_geometry(5.5, 5.5, multi) is True


def test_decision_window_is_the_full_frozen_observation_month():
    assert decision_window("2025-11-30") == "2025-11-01T00:00:00Z/2025-11-30T23:59:59Z"
    assert decision_window("2026-03-31") == "2026-03-01T00:00:00Z/2026-03-31T23:59:59Z"


def test_documented_beed_to_bid_geometry_alias_is_explicit():
    feature = {"properties": {"shapeName": "Bid"}, "geometry": {"type": "Polygon", "coordinates": []}}
    assert feature_for_district([feature], "Beed") is feature
