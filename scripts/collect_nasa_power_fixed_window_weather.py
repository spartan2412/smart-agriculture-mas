"""Collect co-located NASA POWER weather for fixed benchmark windows.

Each query uses the representative cropland-cell coordinate and the frozen
month attached to the historical market scenario.  It collects public daily
NASA POWER AG data; it does not simulate a live farm-weather feed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Dict, List

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = ("T2M", "PRECTOTCORR", "RH2M", "WS2M")
REQUEST_HEADERS = {"User-Agent": "SmartAgricultureMAS/1.0 fixed-window-weather", "Accept": "application/json"}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def power_dates(window: str) -> tuple[str, str]:
    start, end = window.split("/")
    return start[:10].replace("-", ""), end[:10].replace("-", "")


def build_row(cell: Dict[str, str], timeout_s: float) -> Dict[str, str]:
    start, end = power_dates(cell["decision_window_utc"])
    params = {
        "parameters": ",".join(PARAMETERS), "community": "AG", "longitude": cell["longitude"],
        "latitude": cell["latitude"], "start": start, "end": end, "format": "JSON",
    }
    row = {
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_id": "NASA_POWER", "site_id": cell["site_id"], "crop": cell["crop"],
        "state": cell["state"], "district": cell["district"], "longitude": cell["longitude"],
        "latitude": cell["latitude"], "point_scope": cell["geometry_scope"],
        "fixed_decision_date": cell["fixed_decision_date"], "decision_window_utc": cell["decision_window_utc"],
        "official_url": "", "http_status": "", "response_sha256": "NONE", "day_count": "",
        "parameter_keys": "", "weather_status": "", "notes": "", "error": "",
    }
    try:
        response = requests.get(POWER_URL, params=params, headers=REQUEST_HEADERS, timeout=timeout_s)
        row["official_url"] = response.url
        row["http_status"] = str(response.status_code)
        response.raise_for_status()
        payload = response.json()
        parameter_data = payload.get("properties", {}).get("parameter", {})
        present = [name for name in PARAMETERS if isinstance(parameter_data.get(name), dict)]
        days = len(parameter_data.get(PARAMETERS[0], {})) if present else 0
        row.update({
            "response_sha256": sha256(response.content).hexdigest(), "day_count": str(days),
            "parameter_keys": ";".join(present),
            "weather_status": (
                "fixed_window_weather_verified" if set(present) == set(PARAMETERS) and days > 0
                else "weather_response_incomplete"
            ),
            "notes": "Public NASA POWER AG daily data for the exact representative cell and frozen scenario month.",
        })
    except (requests.RequestException, ValueError, KeyError) as exc:
        row.update({"weather_status": "weather_request_failed", "error": f"{type(exc).__name__}: {exc}"})
    return row


OUTPUT_FIELDS = [
    "retrieved_at_utc", "source_id", "site_id", "crop", "state", "district", "longitude", "latitude",
    "point_scope", "fixed_decision_date", "decision_window_utc", "official_url", "http_status",
    "response_sha256", "day_count", "parameter_keys", "weather_status", "notes", "error",
]


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    parser = argparse.ArgumentParser(description="Collect co-located NASA POWER weather for fixed benchmark windows.")
    parser.add_argument("--cells", type=Path, default=registry / "preflight_representative_cropland_cells.csv")
    parser.add_argument("--out", type=Path, default=registry / "preflight_nasa_power_fixed_window_weather.csv")
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--delay-s", type=float, default=0.2)
    args = parser.parse_args()
    cells = read_csv(args.cells)
    if any(row.get("cell_selection_status") != "public_cropland_cell_inside_documented_district" for row in cells):
        raise SystemExit("Every cell must pass the documented-cropland-cell selection gate before weather collection.")
    rows = []
    for index, cell in enumerate(cells, start=1):
        row = build_row(cell, args.timeout_s)
        rows.append(row)
        print(f"[{index}/{len(cells)}] {cell['site_id']}: {row['weather_status']} ({row['day_count']} days)")
        if index != len(cells):
            time.sleep(args.delay_s)
    with args.out.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(row["weather_status"] == "fixed_window_weather_verified" for row in rows)
    print(f"Wrote {len(rows)} rows to {args.out}; fixed-window weather passed: {passed}/{len(rows)}")


if __name__ == "__main__":
    main()
