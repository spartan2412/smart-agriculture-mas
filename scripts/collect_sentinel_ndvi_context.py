"""Collect point-based Sentinel-2 NDVI context for frozen scenarios.

Each scenario already names a quality-gated Sentinel-2 L2A item. This collector
retrieves that exact item from Microsoft Planetary Computer, verifies that its
identity/date/cloud metadata still match the frozen manifest, then samples the
red (B04), near-infrared (B08), and scene-classification (SCL) COGs at the
documented representative cropland coordinate. It stores the item metadata
response and its hash, not an unauditable derived image.

The result is a single representative-cell NDVI context value. It is *not* a
crop-labelled parcel observation, a field-average index, crop-stage evidence,
or a disease diagnosis. The Planetary Computer's signed asset URLs are
short-lived and are deliberately excluded from saved outputs.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import requests
import rasterio
from rasterio.warp import transform

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAC_ITEM_BASE = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items"
SAS_TOKEN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a"
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0 scenario-ndvi-context",
    "Accept": "application/geo+json",
}
SCL_LABELS = {
    0: "no_data", 1: "saturated_or_defective", 2: "topographic_shadow", 3: "cloud_shadow",
    4: "vegetation", 5: "not_vegetated", 6: "water", 7: "unclassified",
    8: "cloud_medium_probability", 9: "cloud_high_probability", 10: "thin_cirrus", 11: "snow_or_ice",
}
CLEAR_SURFACE_SCL = {4, 5}
# Keep these source-quality limits local so this collector runs both as
# ``python scripts/...`` and as ``python -m scripts...`` without relying on a
# package import path.
MAX_CLOUD_COVER = 30.0
MAX_NODATA_PERCENT = 10.0

MANIFEST_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "decision_date", "longitude", "latitude",
    "source_id", "item_request_url", "retrieved_at_utc", "http_status", "raw_path", "response_sha256",
    "satellite_item_id", "satellite_datetime_utc", "scene_cloud_cover_percent", "scene_nodata_percent",
    "source_status", "error",
]
FEATURE_FIELDS = [
    "scenario_id", "satellite_item_id", "satellite_datetime_utc", "satellite_point_scope",
    "satellite_scl_class", "satellite_scl_label", "satellite_pixel_quality_status",
    "satellite_red_dn", "satellite_nir_dn", "satellite_ndvi", "satellite_condition_interpretation",
]
STATUS_FIELDS = [
    "scenario_id", "scene_identity_status", "scene_quality_status", "pixel_quality_status",
    "satellite_condition_status", "satellite_actionability", "restriction_reason",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def raw_relative_path(scenario_id: str) -> Path:
    if not scenario_id.replace("_", "").isalnum():
        raise ValueError(f"Scenario identifier is not safe for a raw filename: {scenario_id!r}")
    return Path("raw") / "sentinel_ndvi_context" / f"{scenario_id}.json"


def signed_href(href: str, token: str) -> str:
    if not href.startswith("https://"):
        raise ValueError("Sentinel asset does not use a trusted HTTPS href.")
    return href + ("&" if "?" in href else "?") + token


def as_float(value: Any, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Sentinel item has no numeric {label} value.") from exc


def expected_datetime_matches(observed: str, frozen: str) -> bool:
    """Compare exact UTC instants while tolerating equivalent trailing zeros."""
    try:
        from datetime import datetime

        normalise = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
        return normalise(observed) == normalise(frozen)
    except ValueError:
        return False


def validate_item(scenario: Mapping[str, str], item: Mapping[str, Any]) -> Tuple[float, float]:
    if item.get("id") != scenario["satellite_item_id"]:
        raise ValueError("STAC item identifier differs from the frozen manifest.")
    properties = item.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("STAC item has no properties object.")
    observed_datetime = str(properties.get("datetime", ""))
    if not expected_datetime_matches(observed_datetime, scenario["satellite_datetime_utc"]):
        raise ValueError("STAC item datetime differs from the frozen manifest.")
    cloud = as_float(properties.get("eo:cloud_cover"), "eo:cloud_cover")
    nodata = as_float(properties.get("s2:nodata_pixel_percentage"), "s2:nodata_pixel_percentage")
    if cloud > MAX_CLOUD_COVER or nodata > MAX_NODATA_PERCENT:
        raise ValueError("STAC item fails the frozen scene cloud/nodata quality gate.")
    return cloud, nodata


def sample_asset(asset: Mapping[str, Any], longitude: float, latitude: float, token: str) -> int:
    href = asset.get("href")
    if not isinstance(href, str):
        raise ValueError("Sentinel item is missing an asset href.")
    vsicurl_url = "/vsicurl/" + signed_href(href, token)
    environment = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_TIMEOUT": "20",
        "GDAL_HTTP_CONNECTTIMEOUT": "10",
        "CPL_VSIL_CURL_CACHE_SIZE": "0",
    }
    with rasterio.Env(**environment):
        with rasterio.open(vsicurl_url) as dataset:
            if dataset.crs is None:
                raise ValueError("Sentinel asset has no coordinate reference system.")
            xs, ys = transform("EPSG:4326", dataset.crs, [longitude], [latitude])
            x, y = xs[0], ys[0]
            if not (dataset.bounds.left <= x <= dataset.bounds.right and dataset.bounds.bottom <= y <= dataset.bounds.top):
                raise ValueError("Representative coordinate falls outside the selected Sentinel asset.")
            value = next(dataset.sample([(x, y)]))[0]
            number = int(value)
            if dataset.nodata is not None and number == int(dataset.nodata):
                raise ValueError("Representative coordinate is a Sentinel asset no-data pixel.")
            return number


def ndvi(red: int, nir: int) -> float:
    denominator = nir + red
    if denominator <= 0:
        raise ValueError("Sentinel red/NIR values cannot produce NDVI.")
    return (nir - red) / denominator


def pixel_quality(scl: int) -> Tuple[str, str]:
    label = SCL_LABELS.get(scl, "unknown")
    if scl in CLEAR_SURFACE_SCL:
        return label, "clear_surface_pixel"
    return label, "non_clear_or_non_land_pixel_context_not_issued"


def fetch_scenario(
    scenario: Mapping[str, str], out_dir: Path, token: str, timeout_s: float
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    scenario_id = scenario["scenario_id"]
    request_url = f"{STAC_ITEM_BASE}/{scenario['satellite_item_id']}"
    relative_raw = raw_relative_path(scenario_id)
    manifest = {
        "scenario_id": scenario_id, "site_id": scenario["site_id"], "crop": scenario["crop"],
        "state": scenario["state"], "district": scenario["district"], "decision_date": scenario["decision_date"],
        "longitude": scenario["longitude"], "latitude": scenario["latitude"], "source_id": "SENTINEL2_L2A_PLANETARY_COMPUTER",
        "item_request_url": request_url, "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "http_status": "", "raw_path": str(relative_raw), "response_sha256": "NONE",
        "satellite_item_id": scenario["satellite_item_id"], "satellite_datetime_utc": scenario["satellite_datetime_utc"],
        "scene_cloud_cover_percent": "", "scene_nodata_percent": "", "source_status": "", "error": "",
    }
    status = {
        "scenario_id": scenario_id, "scene_identity_status": "unavailable", "scene_quality_status": "unavailable",
        "pixel_quality_status": "unavailable", "satellite_condition_status": "unavailable",
        "satellite_actionability": "context_only_not_a_crop_label_or_field_diagnosis", "restriction_reason": "not_evaluated",
    }
    try:
        response = requests.get(request_url, headers=REQUEST_HEADERS, timeout=timeout_s)
        manifest["http_status"] = str(response.status_code)
        response.raise_for_status()
        item = response.json()
        cloud, nodata = validate_item(scenario, item)
        assets = item.get("assets")
        if not isinstance(assets, dict):
            raise ValueError("STAC item has no assets object.")
        red = sample_asset(assets["B04"], float(scenario["longitude"]), float(scenario["latitude"]), token)
        nir = sample_asset(assets["B08"], float(scenario["longitude"]), float(scenario["latitude"]), token)
        scl = sample_asset(assets["SCL"], float(scenario["longitude"]), float(scenario["latitude"]), token)
        label, quality = pixel_quality(scl)
        raw_path = out_dir / relative_raw
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
        manifest.update({
            "response_sha256": sha256(response.content).hexdigest(),
            "scene_cloud_cover_percent": f"{cloud:.6f}", "scene_nodata_percent": f"{nodata:.6f}",
            "source_status": "exact_frozen_item_and_metadata_quality_verified",
        })
        status.update({
            "scene_identity_status": "pass_exact_frozen_item_and_datetime",
            "scene_quality_status": "pass_frozen_cloud_nodata_gate",
            "pixel_quality_status": quality,
            "satellite_condition_status": (
                "available_clear_surface_point_ndvi_context" if quality == "clear_surface_pixel"
                else "withheld_non_clear_or_non_land_pixel"
            ),
            "restriction_reason": (
                "single_public_representative-cropland-cell signal is not a crop-labelled parcel, "
                "field average, observed stage, or disease diagnosis"
            ),
        })
        feature: Dict[str, str] = {
            "scenario_id": scenario_id, "satellite_item_id": scenario["satellite_item_id"],
            "satellite_datetime_utc": scenario["satellite_datetime_utc"],
            "satellite_point_scope": "documented_representative_cropland_cell",
            "satellite_scl_class": str(scl), "satellite_scl_label": label,
            "satellite_pixel_quality_status": quality, "satellite_red_dn": str(red), "satellite_nir_dn": str(nir),
            "satellite_ndvi": f"{ndvi(red, nir):.6f}" if quality == "clear_surface_pixel" else "",
            "satellite_condition_interpretation": (
                "NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 "
                "L2A scene at the documented representative cropland coordinate."
                if quality == "clear_surface_pixel" else
                "No NDVI is issued because the exact coordinate's Scene Classification Layer does not mark a clear "
                "vegetation or not-vegetated land surface pixel."
            ),
        }
        return manifest, feature, status
    except (requests.RequestException, ValueError, KeyError, TypeError, rasterio.errors.RasterioError) as exc:
        manifest.update({"source_status": "sentinel_ndvi_context_failed", "error": f"{type(exc).__name__}: {exc}"})
        status["restriction_reason"] = f"source_or_pixel_validation_failed: {type(exc).__name__}"
        return manifest, {}, status


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Collect exact-scene Sentinel-2 point NDVI context for frozen scenarios.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    parser.add_argument("--scenario-id", action="append", help="Run only an exact scenario ID; repeatable pilot option.")
    parser.add_argument("--workers", type=int, default=1, help="Bounded concurrent public-asset reads (1-4).")
    parser.add_argument("--timeout-s", type=float, default=45.0)
    args = parser.parse_args()
    if args.timeout_s <= 0 or not 1 <= args.workers <= 4:
        raise SystemExit("--timeout-s must be positive and --workers must be between 1 and 4.")
    rows = read_csv(args.manifest)
    requested = set(args.scenario_id or [])
    selected = [row for row in rows if not requested or row["scenario_id"] in requested]
    missing = requested - {row["scenario_id"] for row in selected}
    if missing:
        raise SystemExit(f"Unknown frozen scenario ID(s): {', '.join(sorted(missing))}")
    if not selected:
        raise SystemExit("No frozen scenarios selected.")
    token_response = requests.get(SAS_TOKEN_URL, headers=REQUEST_HEADERS, timeout=args.timeout_s)
    token_response.raise_for_status()
    token = token_response.json().get("token")
    if not isinstance(token, str) or not token:
        raise SystemExit("Planetary Computer did not return an asset access token.")

    results: Dict[str, Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending = {
            executor.submit(fetch_scenario, scenario, args.out_dir, token, args.timeout_s): scenario["scenario_id"]
            for scenario in selected
        }
        for index, future in enumerate(as_completed(pending), start=1):
            scenario_id = pending[future]
            results[scenario_id] = future.result()
            print(f"[{index}/{len(selected)}] {scenario_id}: {results[scenario_id][0]['source_status']}")

    manifests, features, statuses = [], [], []
    for scenario in selected:
        manifest, feature, status = results[scenario["scenario_id"]]
        manifests.append(manifest)
        statuses.append(status)
        if feature:
            features.append(feature)
    write_csv(args.out_dir / "sentinel_ndvi_context_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "sentinel_ndvi_context_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "sentinel_ndvi_context_status.csv", STATUS_FIELDS, statuses)
    passed = sum(row["source_status"] == "exact_frozen_item_and_metadata_quality_verified" for row in manifests)
    print(f"Sentinel point-context metadata availability: {passed}/{len(selected)}.")
    if passed != len(selected):
        raise SystemExit("One or more scenarios failed the Sentinel item/pixel gate; inspect the status audit.")


if __name__ == "__main__":
    main()
