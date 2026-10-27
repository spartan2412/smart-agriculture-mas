"""Collect auditable static SoilGrids WCS values for benchmark representative cells.

The SoilGrids REST v2 point endpoint was paused by ISRIC as of its 2026-01-27
service notice.  This collector consequently uses the provider's public OGC WCS
maps instead. It requests a one-pixel GeoTIFF around each documented
representative cropland cell recorded in
``preflight_representative_cropland_cells.csv``. Those points are
district-scale benchmark cells, not farm centroids or live soil observations.

Raw values and the official WCS metadata title are retained without an implicit
unit conversion.  The only explicit conversion note is pH, whose metadata says
``pH*10``; its raw value is still retained alongside that note.

Run from the repository root:

    python scripts/collect_soilgrids_wcs_profiles.py

No account or API key is required.  Use the crop filter to keep public requests
small, and ``--append`` to assemble a complete output in batches.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import time
from typing import Dict, List, Tuple
from urllib.parse import urlencode

from PIL import Image
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WCS_URL = "https://maps.isric.org/mapserv"
WCS_VERSION = "1.0.0"
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0",
    "Accept": "image/tiff, application/xml;q=0.8",
}

# Values are deliberately retained in the source's native encoding.  Do not add
# an unreferenced conversion here: the metadata title is evidence for the unit.
PROPERTY_SPECS = {
    "phh2o": {
        "coverage": "phh2o_0-5cm_mean",
        "map": "/map/phh2o.map",
        "conversion_note": "Metadata title states pH*10; raw_value_divided_by_10_is_pH.",
    },
    "nitrogen": {
        "coverage": "nitrogen_0-5cm_mean",
        "map": "/map/nitrogen.map",
        "conversion_note": "Raw value retained; use metadata title before any unit conversion.",
    },
    "clay": {
        "coverage": "clay_0-5cm_mean",
        "map": "/map/clay.map",
        "conversion_note": "Raw value retained; use metadata title before any unit conversion.",
    },
    "sand": {
        "coverage": "sand_0-5cm_mean",
        "map": "/map/sand.map",
        "conversion_note": "Raw value retained; use metadata title before any unit conversion.",
    },
    "silt": {
        "coverage": "silt_0-5cm_mean",
        "map": "/map/silt.map",
        "conversion_note": "Raw value retained; use metadata title before any unit conversion.",
    },
    "ocd": {
        "coverage": "ocd_0-5cm_mean",
        "map": "/map/ocd.map",
        "conversion_note": "Raw value retained; use metadata title before any unit conversion.",
    },
}
TITLE_PATTERN = re.compile(
    r"<gmd:title>\s*<gco:CharacterString>([^<]+)</gco:CharacterString>\s*</gmd:title>",
    re.IGNORECASE,
)
# ISRIC's signed-int GeoTIFF maps use this conventional no-data value.  Retain it
# in the audit record but do not present it as a measured or predicted property.
NO_DATA_VALUE = -32768


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def build_wcs_params(map_path: str, coverage_id: str, lon: float, lat: float) -> Dict[str, str]:
    """Build a small EPSG:4326 one-pixel request around a registered access point."""
    # A 0.002 degree envelope is only a request envelope.  WIDTH/HEIGHT=1 causes
    # WCS to resample it to one source value; it does not establish field extent.
    return {
        "map": map_path,
        "SERVICE": "WCS",
        "VERSION": WCS_VERSION,
        "REQUEST": "GetCoverage",
        "COVERAGE": coverage_id,
        "CRS": "EPSG:4326",
        "BBOX": f"{lon - 0.001:.6f},{lat - 0.001:.6f},{lon + 0.001:.6f},{lat + 0.001:.6f}",
        "WIDTH": "1",
        "HEIGHT": "1",
        "FORMAT": "GEOTIFF_INT16",
    }


def build_metadata_params(map_path: str, coverage_id: str) -> Dict[str, str]:
    return {
        "map": map_path,
        "request": "GetMetadata",
        "layer": coverage_id,
    }


def extract_metadata_title(content: bytes) -> str:
    """Extract the official WCS metadata title, if present."""
    text = content.decode("utf-8", errors="replace")
    matches = TITLE_PATTERN.findall(text)
    return matches[0].strip() if matches else "not_found"


def decode_single_pixel_geotiff(content: bytes) -> int:
    """Decode the requested one-pixel GeoTIFF without altering its source encoding."""
    with Image.open(BytesIO(content)) as image:
        if image.size != (1, 1):
            raise ValueError(f"expected a 1x1 GeoTIFF, received {image.size}")
        value = image.getpixel((0, 0))
    if isinstance(value, tuple):
        raise ValueError("expected a single-band GeoTIFF")
    return int(value)


def prepared_url(params: Dict[str, str]) -> str:
    return f"{WCS_URL}?{urlencode(params)}"


def fetch_metadata(spec: Dict[str, str], *, timeout_s: float) -> Tuple[str, str, str, str]:
    """Return status, digest, extracted title, and a non-sensitive request URL."""
    params = build_metadata_params(spec["map"], spec["coverage"])
    url = prepared_url(params)
    response = requests.get(WCS_URL, params=params, headers=REQUEST_HEADERS, timeout=timeout_s)
    response.raise_for_status()
    return (
        str(response.status_code),
        sha256(response.content).hexdigest(),
        extract_metadata_title(response.content),
        url,
    )


def fetch_profile_value(
    site: Dict[str, str],
    audit: Dict[str, str],
    property_id: str,
    metadata: Tuple[str, str, str, str],
    *,
    timeout_s: float,
) -> Dict[str, str]:
    """Fetch one explicit property at one registered representative point."""
    spec = PROPERTY_SPECS[property_id]
    lon = float(audit.get("longitude") or audit["bbox_center_lon"])
    lat = float(audit.get("latitude") or audit["bbox_center_lat"])
    point_scope = audit.get("point_scope") or (
        "public_worldcover_cropland_documented_representative_cell"
        if audit.get("geometry_scope") == "documented_representative_cell"
        else "geoBoundaries_ADM2_bbox_midpoint_access_test_not_field_centroid"
    )
    request_params = build_wcs_params(spec["map"], spec["coverage"], lon, lat)
    row = {
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_id": "SOILGRIDS",
        "delivery_service": "ISRIC_OGC_WCS_1_0_0",
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"].replace("_", " "),
        "district": site["district"].replace("_", " "),
        "point_scope": point_scope,
        "longitude": f"{lon:.5f}",
        "latitude": f"{lat:.5f}",
        "property_id": property_id,
        "coverage_id": spec["coverage"],
        "depth_interval": "0-5cm",
        "metadata_http_status": metadata[0],
        "metadata_sha256": metadata[1],
        "metadata_title": metadata[2],
        "metadata_request_url": metadata[3],
        "value_request_url": prepared_url(request_params),
        "value_http_status": "",
        "value_tiff_sha256": "NONE",
        "raw_value": "",
        "conversion_note": spec["conversion_note"],
        "status": "",
        "error": "",
    }
    try:
        response = requests.get(
            WCS_URL,
            params=request_params,
            headers=REQUEST_HEADERS,
            timeout=timeout_s,
        )
        row["value_http_status"] = str(response.status_code)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").casefold()
        if "tiff" not in content_type and not response.content.startswith((b"II*", b"MM\x00*")):
            raise ValueError("WCS response is not a GeoTIFF")
        row["value_tiff_sha256"] = sha256(response.content).hexdigest()
        raw_value = decode_single_pixel_geotiff(response.content)
        row["raw_value"] = str(raw_value)
        row["status"] = (
            "source_nodata_at_access_test_point"
            if raw_value == NO_DATA_VALUE
            else "static_wcs_value_collected"
        )
    except (requests.RequestException, ValueError, OSError) as exc:
        row["status"] = "value_unavailable_or_unreadable"
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


OUTPUT_FIELDS = [
    "retrieved_at_utc", "source_id", "delivery_service", "site_id", "crop", "state", "district",
    "point_scope", "longitude", "latitude", "property_id", "coverage_id", "depth_interval",
    "metadata_http_status", "metadata_sha256", "metadata_title", "metadata_request_url",
    "value_request_url", "value_http_status", "value_tiff_sha256", "raw_value", "conversion_note",
    "status", "error",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect static SoilGrids WCS values at benchmark representative cells."
    )
    parser.add_argument("--sites", type=Path, default=PROJECT_ROOT / "data" / "registry" / "source_scoped_preflight_pool.csv")
    parser.add_argument("--audit", type=Path, default=PROJECT_ROOT / "data" / "registry" / "preflight_representative_cropland_cells.csv")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "data" / "registry" / "preflight_soilgrids_wcs_profiles.csv")
    parser.add_argument("--crop", action="append", choices=sorted({"rice", "wheat", "maize", "chickpea", "soybean", "tomato"}))
    parser.add_argument("--property", action="append", choices=sorted(PROPERTY_SPECS))
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--delay-s", type=float, default=0.15)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    args = parser.parse_args()
    if args.delay_s < 0 or args.timeout_s <= 0:
        raise SystemExit("--delay-s must be non-negative and --timeout-s must be positive.")

    sites = read_csv(args.sites)
    audit_by_site = {row["site_id"]: row for row in read_csv(args.audit)}
    if args.crop:
        crops = set(args.crop)
        sites = [site for site in sites if site["crop"] in crops]
    if not sites:
        raise SystemExit("No selected site rows found.")
    missing_audit = [site["site_id"] for site in sites if site["site_id"] not in audit_by_site]
    if missing_audit:
        raise SystemExit(f"Audit coordinates missing for: {', '.join(missing_audit)}")

    property_ids = args.property or list(PROPERTY_SPECS)
    metadata: Dict[str, Tuple[str, str, str, str]] = {}
    for property_id in property_ids:
        try:
            metadata[property_id] = fetch_metadata(PROPERTY_SPECS[property_id], timeout_s=args.timeout_s)
        except requests.RequestException as exc:
            raise SystemExit(f"Unable to retrieve WCS metadata for {property_id}: {exc}") from exc

    rows: List[Dict[str, str]] = []
    total = len(sites) * len(property_ids)
    for number, (site, property_id) in enumerate(
        ((site, property_id) for site in sites for property_id in property_ids), start=1
    ):
        row = fetch_profile_value(
            site, audit_by_site[site["site_id"]], property_id, metadata[property_id], timeout_s=args.timeout_s
        )
        rows.append(row)
        print(f"[{number}/{total}] {site['site_id']} {property_id}: {row['status']} {row['raw_value']}")
        if number != total:
            time.sleep(args.delay_s)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    append_existing = args.append and args.out.exists() and args.out.stat().st_size > 0
    with args.out.open("a" if append_existing else "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        if not append_existing:
            writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
