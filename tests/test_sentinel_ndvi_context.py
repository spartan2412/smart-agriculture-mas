from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_sentinel_ndvi_context import ndvi, pixel_quality, validate_item


def test_ndvi_and_pixel_quality_are_explicit():
    assert ndvi(2000, 3000) == pytest.approx(0.2)
    assert pixel_quality(4) == ("vegetation", "clear_surface_pixel")
    assert pixel_quality(8) == ("cloud_medium_probability", "non_clear_or_non_land_pixel_context_not_issued")
    with pytest.raises(ValueError, match="cannot produce NDVI"):
        ndvi(0, 0)


def test_item_validation_requires_exact_frozen_identity_datetime_and_quality():
    scenario = {
        "satellite_item_id": "ITEM", "satellite_datetime_utc": "2025-10-20T05:42:51Z",
    }
    item = {
        "id": "ITEM",
        "properties": {
            "datetime": "2025-10-20T05:42:51.000000Z",
            "eo:cloud_cover": 1.0,
            "s2:nodata_pixel_percentage": 0.0,
        },
    }
    assert validate_item(scenario, item) == (1.0, 0.0)
    item["properties"]["eo:cloud_cover"] = 31.0
    with pytest.raises(ValueError, match="cloud/nodata"):
        validate_item(scenario, item)
