from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_sentinel_scene_coverage import (
    MAX_CLOUD_COVER,
    MAX_NODATA_PERCENT,
    build_search_payload,
    is_quality_candidate,
)


def test_search_payload_is_point_and_time_bounded():
    payload = build_search_payload(74.0, 20.0, "2025-09-01T00:00:00Z/2025-09-30T23:59:59Z")

    assert payload["collections"] == ["sentinel-2-l2a"]
    assert payload["intersects"]["coordinates"] == [74.0, 20.0]
    assert payload["limit"] == 100
    assert payload["query"]["eo:cloud_cover"]["lt"] == 80


def test_quality_gate_requires_both_cloud_and_nodata_metadata():
    usable = {"properties": {"eo:cloud_cover": MAX_CLOUD_COVER, "s2:nodata_pixel_percentage": MAX_NODATA_PERCENT}}
    missing_nodata = {"properties": {"eo:cloud_cover": 1}}
    too_cloudy = {"properties": {"eo:cloud_cover": MAX_CLOUD_COVER + 0.1, "s2:nodata_pixel_percentage": 0}}

    assert is_quality_candidate(usable) is True
    assert is_quality_candidate(missing_nodata) is False
    assert is_quality_candidate(too_cloudy) is False
