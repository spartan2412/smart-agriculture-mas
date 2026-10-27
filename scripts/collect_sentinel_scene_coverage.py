"""Verify public Sentinel-2 scene metadata coverage for benchmark representative cells.

This collector queries the Microsoft Planetary Computer STAC API, which exposes
Sentinel-2 L2A metadata without an account.  It records one reproducible,
season-appropriate *reference availability window* per benchmark site. The
result proves only that a usable satellite acquisition may be available at the
documented representative cropland cell. It does not prove crop identity,
field-level coverage, a crop condition, or scenario-date availability.

Run from the repository root:

    python scripts/collect_sentinel_scene_coverage.py
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0",
    "Accept": "application/geo+json",
}
# These windows establish a reproducible source-availability check.  They are
# deliberately not used as labelled crop-observation dates.
REFERENCE_WINDOWS = {
    "kharif": "2025-09-01T00:00:00Z/2025-09-30T23:59:59Z",
    "rabi": "2025-12-01T00:00:00Z/2025-12-31T23:59:59Z",
    "samba": "2025-11-01T00:00:00Z/2025-11-30T23:59:59Z",
}
MAX_CLOUD_COVER = 30.0
MAX_NODATA_PERCENT = 10.0


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def build_search_payload(lon: float, lat: float, window: str) -> Dict[str, Any]:
    return {
        "collections": ["sentinel-2-l2a"],
        "intersects": {"type": "Point", "coordinates": [lon, lat]},
        "datetime": window,
        "limit": 100,
        # This broad source-side ceiling avoids downloading unusably cloudy
        # candidates while preserving enough records for the local quality gate.
        "query": {"eo:cloud_cover": {"lt": 80}},
    }


def as_number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def feature_sort_key(feature: Dict[str, Any]) -> Tuple[float, float, str]:
    properties = feature.get("properties", {})
    cloud = as_number(properties.get("eo:cloud_cover"))
    nodata = as_number(properties.get("s2:nodata_pixel_percentage"))
    return (
        cloud if cloud is not None else float("inf"),
        nodata if nodata is not None else float("inf"),
        str(properties.get("datetime", "")),
    )


def is_quality_candidate(feature: Dict[str, Any]) -> bool:
    properties = feature.get("properties", {})
    cloud = as_number(properties.get("eo:cloud_cover"))
    nodata = as_number(properties.get("s2:nodata_pixel_percentage"))
    return (
        cloud is not None
        and nodata is not None
        and cloud <= MAX_CLOUD_COVER
        and nodata <= MAX_NODATA_PERCENT
    )


def build_coverage_row(site: Dict[str, str], audit: Dict[str, str], *, timeout_s: float) -> Dict[str, str]:
    season = site["proposed_season"].casefold()
    window = audit.get("decision_window_utc") or REFERENCE_WINDOWS[season]
    lon = float(audit.get("longitude") or audit["bbox_center_lon"])
    lat = float(audit.get("latitude") or audit["bbox_center_lat"])
    point_scope = audit.get("point_scope") or (
        "public_worldcover_cropland_documented_representative_cell"
        if audit.get("geometry_scope") == "documented_representative_cell"
        else "geoBoundaries_ADM2_bbox_midpoint_access_test_not_field_centroid"
    )
    payload = build_search_payload(lon, lat, window)
    row = {
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_id": "SENTINEL2_L2A",
        "catalog": "Microsoft_Planetary_Computer_STAC",
        "collection": "sentinel-2-l2a",
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"].replace("_", " "),
        "district": site["district"].replace("_", " "),
        "point_scope": point_scope,
        "longitude": f"{lon:.5f}",
        "latitude": f"{lat:.5f}",
        "reference_window_utc": window,
        "search_payload_sha256": sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "search_http_status": "",
        "response_sha256": "NONE",
        "returned_feature_count": "",
        "quality_candidate_count": "",
        "selected_item_id": "NONE",
        "selected_datetime_utc": "NONE",
        "selected_cloud_cover_percent": "",
        "selected_nodata_percent": "",
        "selected_gsd_m": "",
        "status": "",
        "notes": "",
        "error": "",
    }
    try:
        response = requests.post(
            STAC_SEARCH_URL,
            json=payload,
            headers=REQUEST_HEADERS,
            timeout=timeout_s,
        )
        row["search_http_status"] = str(response.status_code)
        response.raise_for_status()
        row["response_sha256"] = sha256(response.content).hexdigest()
        result = response.json()
        features = result.get("features", [])
        if not isinstance(features, list):
            raise ValueError("STAC response contains a non-list features field")
        features = [feature for feature in features if isinstance(feature, dict)]
        quality_features = [feature for feature in features if is_quality_candidate(feature)]
        row["returned_feature_count"] = str(len(features))
        row["quality_candidate_count"] = str(len(quality_features))
        selected = min(quality_features, key=feature_sort_key) if quality_features else None
        if selected is None:
            row["status"] = (
                "no_scene_in_reference_window"
                if not features
                else "scenes_returned_but_local_quality_gate_not_met"
            )
        else:
            props = selected.get("properties", {})
            row.update({
                "selected_item_id": str(selected.get("id", "NONE")),
                "selected_datetime_utc": str(props.get("datetime", "NONE")),
                "selected_cloud_cover_percent": str(props.get("eo:cloud_cover", "")),
                "selected_nodata_percent": str(props.get("s2:nodata_pixel_percentage", "")),
                "selected_gsd_m": str(props.get("gsd", "")),
                "status": "quality_scene_metadata_available",
                "notes": (
                    "Reference-window availability only; acquire and quality-check an exact scene "
                    "for each scenario date before deriving satellite features."
                ),
            })
    except (requests.RequestException, ValueError) as exc:
        row.update({
            "status": "search_failed",
            "error": f"{type(exc).__name__}: {exc}",
        })
    return row


OUTPUT_FIELDS = [
    "retrieved_at_utc", "source_id", "catalog", "collection", "site_id", "crop", "state", "district",
    "point_scope", "longitude", "latitude", "reference_window_utc", "search_payload_sha256",
    "search_http_status", "response_sha256", "returned_feature_count", "quality_candidate_count",
    "selected_item_id", "selected_datetime_utc", "selected_cloud_cover_percent",
    "selected_nodata_percent", "selected_gsd_m", "status", "notes", "error",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check public Sentinel-2 metadata coverage for registry sites.")
    parser.add_argument("--sites", type=Path, default=PROJECT_ROOT / "data" / "registry" / "source_scoped_preflight_pool.csv")
    parser.add_argument("--audit", type=Path, default=PROJECT_ROOT / "data" / "registry" / "preflight_representative_cropland_cells.csv")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "data" / "registry" / "preflight_sentinel_scene_coverage.csv")
    parser.add_argument("--crop", action="append", choices=sorted({"rice", "wheat", "maize", "chickpea", "soybean", "tomato"}))
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--delay-s", type=float, default=0.2)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    args = parser.parse_args()
    if args.delay_s < 0 or args.timeout_s <= 0:
        raise SystemExit("--delay-s must be non-negative and --timeout-s must be positive.")

    sites = read_csv(args.sites)
    if args.crop:
        selected = set(args.crop)
        sites = [site for site in sites if site["crop"] in selected]
    audit_by_site = {row["site_id"]: row for row in read_csv(args.audit)}
    missing = [site["site_id"] for site in sites if site["site_id"] not in audit_by_site]
    if missing:
        raise SystemExit(f"Audit coordinates missing for: {', '.join(missing)}")

    rows = []
    for index, site in enumerate(sites, start=1):
        row = build_coverage_row(site, audit_by_site[site["site_id"]], timeout_s=args.timeout_s)
        rows.append(row)
        print(
            f"[{index}/{len(sites)}] {site['site_id']}: {row['status']} "
            f"({row['quality_candidate_count']} quality candidates)"
        )
        if index != len(sites):
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
