"""Select deterministic public cropland cells for district-scale scenarios.

The research benchmark is district-scale, so it must not fabricate a farm
coordinate.  This collector instead selects one *representative cropland cell*
per admitted-preflight district using only public spatial sources:

* geoBoundaries IND ADM2 2021 for the district polygon; and
* ESA WorldCover 2021 (10 m) for the cropland class (40).

The chosen coordinate is inside the documented district polygon and is a
WorldCover cropland pixel.  It is not asserted to be a surveyed farm or a
crop-type-labelled field.  Crop identity remains established by the separate
district/covered-region crop-season evidence.  The cell merely ensures that
weather, static soil estimates, and Sentinel metadata are co-located.

Run from the repository root:

    python scripts/select_representative_cropland_cells.py
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from PIL import Image
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/"
WORLD_COVER_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
WORLD_COVER_RASTER_URL = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox"
WORLD_COVER_COLLECTION = "esa-worldcover"
WORLD_COVER_CLASS_CROPLAND = 40
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0 representative-cropland-cell",
    "Accept": "application/json,application/geo+json,image/tiff;q=0.9,*/*;q=0.1",
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def sha256_json(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def geometry_bbox(geometry: Dict[str, Any]) -> Tuple[float, float, float, float]:
    positions: List[Tuple[float, float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, (list, tuple)) and len(value) >= 2 and isinstance(value[0], (int, float)):
            positions.append((float(value[0]), float(value[1])))
        elif isinstance(value, (list, tuple)):
            for child in value:
                collect(child)

    collect(geometry.get("coordinates", []))
    if not positions:
        raise ValueError("District geometry contains no coordinate positions.")
    lons, lats = zip(*positions)
    return min(lons), min(lats), max(lons), max(lats)


def point_in_ring(lon: float, lat: float, ring: Sequence[Sequence[float]]) -> bool:
    """Ray-casting point-in-ring test for WGS84 GeoJSON coordinates."""
    inside = False
    if len(ring) < 3:
        return False
    previous = ring[-1]
    for current in ring:
        x1, y1 = float(previous[0]), float(previous[1])
        x2, y2 = float(current[0]), float(current[1])
        crosses = (y1 > lat) != (y2 > lat)
        if crosses:
            intersect_lon = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < intersect_lon:
                inside = not inside
        previous = current
    return inside


def point_in_geometry(lon: float, lat: float, geometry: Dict[str, Any]) -> bool:
    geometry_type = geometry.get("type")
    if geometry_type == "Polygon":
        polygons = [geometry.get("coordinates", [])]
    elif geometry_type == "MultiPolygon":
        polygons = geometry.get("coordinates", [])
    else:
        raise ValueError(f"Unsupported district geometry type {geometry_type!r}.")
    for polygon in polygons:
        if not polygon or not point_in_ring(lon, lat, polygon[0]):
            continue
        if all(not point_in_ring(lon, lat, hole) for hole in polygon[1:]):
            return True
    return False


def feature_for_district(features: Iterable[Dict[str, Any]], district: str) -> Dict[str, Any]:
    # geoBoundaries preserves the source spelling ``Bid`` for Maharashtra's
    # Beed district.  Keep the reconciliation explicit and single-purpose;
    # no fuzzy matching is permitted for a final location gate.
    source_district = {"beed": "Bid"}.get(normalise(district), district)
    matches = [
        feature for feature in features
        if normalise(str(feature.get("properties", {}).get("shapeName", ""))) == normalise(source_district)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one geoBoundaries ADM2 feature for {district!r}; found {len(matches)}."
        )
    return matches[0]


def intersection_bbox(
    first: Tuple[float, float, float, float], second: Sequence[float]
) -> Tuple[float, float, float, float] | None:
    min_lon, min_lat = max(first[0], float(second[0])), max(first[1], float(second[1]))
    max_lon, max_lat = min(first[2], float(second[2])), min(first[3], float(second[3]))
    return (min_lon, min_lat, max_lon, max_lat) if min_lon < max_lon and min_lat < max_lat else None


def fetch_district_geometry(timeout_s: float) -> tuple[Dict[str, Any], Dict[str, Any], str]:
    metadata_response = requests.get(GEOMETRY_METADATA_URL, headers=REQUEST_HEADERS, timeout=timeout_s)
    metadata_response.raise_for_status()
    metadata = metadata_response.json()
    geometry_url = metadata.get("simplifiedGeometryGeoJSON")
    if not isinstance(geometry_url, str) or not geometry_url.startswith("https://"):
        raise ValueError("geoBoundaries metadata did not provide a public simplified GeoJSON URL.")
    geometry_response = requests.get(geometry_url, headers=REQUEST_HEADERS, timeout=timeout_s)
    geometry_response.raise_for_status()
    geometry_document = geometry_response.json()
    features = geometry_document.get("features", [])
    if not isinstance(features, list):
        raise ValueError("geoBoundaries GeoJSON does not contain a features list.")
    return metadata, geometry_document, geometry_url


def worldcover_items(geometry: Dict[str, Any], timeout_s: float) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    payload = {"collections": [WORLD_COVER_COLLECTION], "intersects": geometry, "limit": 20}
    response = requests.post(WORLD_COVER_STAC_URL, json=payload, headers=REQUEST_HEADERS, timeout=timeout_s)
    response.raise_for_status()
    result = response.json()
    features = [feature for feature in result.get("features", []) if isinstance(feature, dict)]
    # Explicitly retain the published 2021 v200 layer rather than allowing an
    # API ordering change to switch the benchmark's land-cover reference.
    items = [feature for feature in features if "2021_v200" in str(feature.get("id", ""))]
    if not items:
        raise ValueError("No ESA WorldCover 2021 v200 item intersects the district geometry.")
    return payload, items


def fetch_cropland_candidates(
    item: Dict[str, Any], district_geometry: Dict[str, Any], district_bbox: Tuple[float, float, float, float],
    *, timeout_s: float, grid_size: int
) -> tuple[str, bytes, List[Tuple[float, float]]]:
    item_bbox = item.get("bbox")
    if not isinstance(item_bbox, list) or len(item_bbox) < 4:
        raise ValueError("WorldCover item lacks a usable bbox.")
    bbox = intersection_bbox(district_bbox, item_bbox)
    if bbox is None:
        return "", b"", []
    item_id = str(item.get("id", ""))
    if not item_id:
        raise ValueError("WorldCover item lacks an identifier.")
    min_lon, min_lat, max_lon, max_lat = bbox
    url = (
        f"{WORLD_COVER_RASTER_URL}/{min_lon:.8f},{min_lat:.8f},{max_lon:.8f},{max_lat:.8f}/"
        f"{grid_size}x{grid_size}.tif"
    )
    response = requests.get(
        url,
        params={"collection": WORLD_COVER_COLLECTION, "item": item_id, "assets": "map"},
        headers=REQUEST_HEADERS,
        timeout=timeout_s,
    )
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    candidates: List[Tuple[float, float]] = []
    # Check every fourth sample: this yields a deterministic spatially
    # distributed candidate set while avoiding a false sub-pixel precision
    # claim for a district-scale representative cell.
    for row in range(2, image.height, 4):
        for column in range(2, image.width, 4):
            value = image.getpixel((column, row))
            land_cover = value[0] if isinstance(value, tuple) else value
            if land_cover != WORLD_COVER_CLASS_CROPLAND:
                continue
            lon = min_lon + (column + 0.5) * (max_lon - min_lon) / image.width
            lat = max_lat - (row + 0.5) * (max_lat - min_lat) / image.height
            if point_in_geometry(lon, lat, district_geometry):
                candidates.append((lon, lat))
    return response.url, response.content, candidates


def select_cell(
    geometry: Dict[str, Any], items: List[Dict[str, Any]], *, timeout_s: float, grid_size: int
) -> tuple[str, str, str, float, float]:
    bbox = geometry_bbox(geometry)
    centre_lon = (bbox[0] + bbox[2]) / 2
    centre_lat = (bbox[1] + bbox[3]) / 2
    all_candidates: List[Tuple[str, str, bytes, float, float]] = []
    for item in items:
        raster_url, content, candidates = fetch_cropland_candidates(
            item, geometry, bbox, timeout_s=timeout_s, grid_size=grid_size
        )
        for lon, lat in candidates:
            all_candidates.append((str(item["id"]), raster_url, content, lon, lat))
    if not all_candidates:
        raise ValueError("No ESA WorldCover cropland sample was found inside the district polygon.")
    # A normalized distance avoids favouring the longer geographic axis of a
    # district and gives a reproducible central representative cell.
    lon_span = max(bbox[2] - bbox[0], 1e-12)
    lat_span = max(bbox[3] - bbox[1], 1e-12)
    selected = min(
        all_candidates,
        key=lambda candidate: (
            ((candidate[3] - centre_lon) / lon_span) ** 2
            + ((candidate[4] - centre_lat) / lat_span) ** 2,
            candidate[0], candidate[3], candidate[4],
        ),
    )
    return selected[0], selected[1], sha256(selected[2]).hexdigest(), selected[3], selected[4]


def decision_window(decision_date: str) -> str:
    year, month, _day = (int(part) for part in decision_date.split("-"))
    end_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01T00:00:00Z/{year:04d}-{month:02d}-{end_day:02d}T23:59:59Z"


OUTPUT_FIELDS = [
    "retrieved_at_utc", "site_id", "crop", "state", "district", "geometry_scope",
    "fixed_decision_date", "decision_window_utc", "cell_selection_status", "longitude", "latitude",
    "district_boundary_id", "district_boundary_year", "district_geometry_url", "district_geometry_sha256",
    "worldcover_collection", "worldcover_item_id", "worldcover_class", "worldcover_raster_url",
    "worldcover_raster_sha256", "selection_method", "notes", "error",
]


def build_row(
    site: Dict[str, str], market: Dict[str, str], metadata: Dict[str, Any], geometry_document: Dict[str, Any],
    geometry_url: str, *, timeout_s: float, grid_size: int
) -> Dict[str, str]:
    decision_date = market.get("benchmark_market_decision_date", "")
    row = {
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "site_id": site["site_id"], "crop": site["crop"], "state": site["state"], "district": site["district"],
        "geometry_scope": "", "fixed_decision_date": decision_date, "decision_window_utc": "",
        "cell_selection_status": "", "longitude": "", "latitude": "",
        "district_boundary_id": str(metadata.get("boundaryID", "")),
        "district_boundary_year": str(metadata.get("boundaryYearRepresented", "")),
        "district_geometry_url": geometry_url, "district_geometry_sha256": sha256_json(geometry_document),
        "worldcover_collection": WORLD_COVER_COLLECTION, "worldcover_item_id": "NONE",
        "worldcover_class": "", "worldcover_raster_url": "NONE", "worldcover_raster_sha256": "NONE",
        "selection_method": "", "notes": "", "error": "",
    }
    try:
        if not decision_date:
            raise ValueError("The historical market evidence has no frozen decision date.")
        feature = feature_for_district(geometry_document.get("features", []), site["district"])
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            raise ValueError("Matched district feature lacks a GeoJSON geometry.")
        _payload, items = worldcover_items(geometry, timeout_s)
        item_id, raster_url, raster_hash, lon, lat = select_cell(
            geometry, items, timeout_s=timeout_s, grid_size=grid_size
        )
        row.update({
            "geometry_scope": "documented_representative_cell",
            "decision_window_utc": decision_window(decision_date),
            "cell_selection_status": "public_cropland_cell_inside_documented_district",
            "longitude": f"{lon:.6f}", "latitude": f"{lat:.6f}",
            "worldcover_item_id": item_id, "worldcover_class": str(WORLD_COVER_CLASS_CROPLAND),
            "worldcover_raster_url": raster_url, "worldcover_raster_sha256": raster_hash,
            "selection_method": "nearest_cropland_sample_to_geoBoundaries_ADM2_bbox_centre_within_polygon",
            "notes": (
                "District-scale representative cropland cell only; not a surveyed farm or a crop-type-labelled field. "
                "Crop identity comes from the separate crop-season and exact district-market evidence."
            ),
        })
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as exc:
        row.update({
            "geometry_scope": "unresolved", "cell_selection_status": "cell_selection_failed",
            "error": f"{type(exc).__name__}: {exc}",
        })
    return row


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    parser = argparse.ArgumentParser(description="Select public representative cropland cells for preflight candidates.")
    parser.add_argument("--sites", type=Path, default=registry / "source_scoped_preflight_pool.csv")
    parser.add_argument("--market", type=Path, default=registry / "preflight_agmarknet_historical_market_coverage.csv")
    parser.add_argument("--out", type=Path, default=registry / "preflight_representative_cropland_cells.csv")
    parser.add_argument("--timeout-s", type=float, default=60.0)
    parser.add_argument("--grid-size", type=int, default=512)
    parser.add_argument("--delay-s", type=float, default=0.2)
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.grid_size < 32 or args.delay_s < 0:
        raise SystemExit("--timeout-s must be positive, --grid-size must be at least 32, and --delay-s cannot be negative.")
    sites = read_csv(args.sites)
    market = {row["site_id"]: row for row in read_csv(args.market)}
    if {site["site_id"] for site in sites} != set(market):
        raise SystemExit("Historical market evidence must exactly match the candidate pool.")
    metadata, geometry_document, geometry_url = fetch_district_geometry(args.timeout_s)
    rows = []
    for index, site in enumerate(sites, start=1):
        row = build_row(
            site, market[site["site_id"]], metadata, geometry_document, geometry_url,
            timeout_s=args.timeout_s, grid_size=args.grid_size,
        )
        rows.append(row)
        print(f"[{index}/{len(sites)}] {site['site_id']}: {row['cell_selection_status']}")
        if index != len(sites):
            time.sleep(args.delay_s)
    with args.out.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    selected = sum(row["cell_selection_status"] == "public_cropland_cell_inside_documented_district" for row in rows)
    print(f"Wrote {len(rows)} rows to {args.out}; representative cropland cells selected: {selected}/{len(rows)}")


if __name__ == "__main__":
    main()
