from io import BytesIO
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_soilgrids_wcs_profiles import (
    NO_DATA_VALUE,
    build_wcs_params,
    decode_single_pixel_geotiff,
    extract_metadata_title,
    fetch_profile_value,
)


def test_wcs_request_is_a_one_pixel_epsg_4326_request():
    params = build_wcs_params("/map/phh2o.map", "phh2o_0-5cm_mean", 74.0, 20.0)

    assert params["CRS"] == "EPSG:4326"
    assert params["BBOX"] == "73.999000,19.999000,74.001000,20.001000"
    assert params["WIDTH"] == "1"
    assert params["HEIGHT"] == "1"
    assert params["FORMAT"] == "GEOTIFF_INT16"


def test_decode_single_pixel_geotiff_keeps_raw_value():
    image = Image.new("I", (1, 1), 70)
    buffer = BytesIO()
    image.save(buffer, format="TIFF")

    assert decode_single_pixel_geotiff(buffer.getvalue()) == 70


def test_soilgrids_nodata_value_is_not_a_valid_profile_measurement():
    assert NO_DATA_VALUE == -32768


def test_metadata_title_is_extracted_without_implicit_unit_conversion():
    xml = b"<gmd:title><gco:CharacterString>pH in H2O 0-5cm mean (pH*10)</gco:CharacterString></gmd:title>"

    assert extract_metadata_title(xml) == "pH in H2O 0-5cm mean (pH*10)"


def test_representative_cell_coordinates_and_scope_are_used_when_present(monkeypatch):
    def fake_metadata(*_args, **_kwargs):
        return ("200", "hash", "title", "https://example.invalid/metadata")

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "image/tiff"}
        content = b"II*fake"

        def raise_for_status(self):
            return None

    monkeypatch.setattr("scripts.collect_soilgrids_wcs_profiles.requests.get", lambda *_a, **_k: FakeResponse())
    monkeypatch.setattr("scripts.collect_soilgrids_wcs_profiles.decode_single_pixel_geotiff", lambda _content: 70)
    row = fetch_profile_value(
        {"site_id": "SITE", "crop": "rice", "state": "Punjab", "district": "Ludhiana"},
        {"longitude": "75.100000", "latitude": "30.200000", "geometry_scope": "documented_representative_cell"},
        "phh2o", fake_metadata(), timeout_s=1,
    )
    assert row["longitude"] == "75.10000"
    assert row["point_scope"] == "public_worldcover_cropland_documented_representative_cell"
