"""Collect additive NASA POWER water-context evidence for frozen scenarios.

The existing scenario weather files contain temperature, precipitation, relative
humidity, and wind.  This collector obtains additional public NASA POWER AG
variables for exactly the same representative-cell coordinate and declared
historical decision window:

* ``ALLSKY_SFC_SW_DWN`` — all-sky surface shortwave radiation;
* ``GWETROOT`` and ``GWETTOP`` — NASA POWER modelled root/top-zone wetness;
* ``EVLAND`` — NASA POWER land evaporation; and
* the four original weather variables, so every derived aggregate has one
  source payload and one input window.

The output is explicitly a retrospective, district-scale weather/wetness
context.  ``precipitation_minus_land_evaporation_mm`` is a source-derived
monthly accounting indicator; it is not a field water balance, soil-moisture
measurement, irrigation amount, or forecast.

This script writes only beneath ``data/scenarios/enriched``. It never changes
the frozen 300-scenario benchmark.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = (
    "T2M", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN",
    "GWETROOT", "GWETTOP", "EVLAND",
)
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0 scenario-water-context",
    "Accept": "application/json",
}

MANIFEST_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "decision_date", "decision_window_utc",
    "longitude", "latitude", "source_id", "source_url", "retrieved_at_utc", "http_status",
    "raw_path", "response_sha256", "parameter_keys", "parameter_units", "expected_day_count", "observed_day_count",
    "source_status", "error",
]
FEATURE_FIELDS = [
    "scenario_id", "weather_observed_days", "weather_t2m_mean_c", "weather_precipitation_total_mm",
    "weather_rh2m_mean_percent", "weather_ws2m_mean_m_s", "weather_shortwave_mean_mj_m2_day",
    "water_gwetroot_mean_fraction", "water_gwetroot_min_fraction", "water_gwetroot_max_fraction",
    "water_gwettop_mean_fraction", "water_land_evaporation_total_mm",
    "water_precipitation_minus_land_evaporation_mm", "water_context_interpretation",
]
STATUS_FIELDS = [
    "scenario_id", "weather_source_status", "wetness_source_status", "water_context_status",
    "irrigation_actionability", "restriction_reason",
]
FILL_VALUE = -999.0


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def power_dates(window: str) -> tuple[str, str]:
    try:
        start, end = window.split("/", maxsplit=1)
        return start[:10].replace("-", ""), end[:10].replace("-", "")
    except ValueError as exc:
        raise ValueError(f"Invalid decision window: {window!r}") from exc


def expected_dates(start: str, end: str) -> List[str]:
    from datetime import date, timedelta

    current = date(int(start[:4]), int(start[4:6]), int(start[6:]))
    final = date(int(end[:4]), int(end[4:6]), int(end[6:]))
    dates = []
    while current <= final:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


def raw_relative_path(scenario_id: str) -> Path:
    if not scenario_id.replace("_", "").isalnum():
        raise ValueError(f"Scenario identifier is not safe for a raw filename: {scenario_id!r}")
    return Path("raw") / "nasa_power_water_context" / f"{scenario_id}.json"


def values_for_parameter(parameter: Mapping[str, Any], name: str, dates: Sequence[str]) -> List[float]:
    series = parameter.get(name)
    if not isinstance(series, dict):
        raise ValueError(f"NASA POWER response is missing parameter {name}.")
    if set(series) != set(dates):
        raise ValueError(f"NASA POWER response does not contain a complete daily series for {name}.")
    values: List[float] = []
    for day in dates:
        value = series[day]
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"NASA POWER response has non-numeric {name} value on {day}.") from exc
        if number == FILL_VALUE:
            raise ValueError(f"NASA POWER fill value cannot be used as {name} evidence.")
        values.append(number)
    return values


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("Cannot aggregate an empty source series.")
    return sum(values) / len(values)


def build_features(payload: Mapping[str, Any], start: str, end: str) -> Dict[str, str]:
    parameter = payload.get("properties", {}).get("parameter")
    if not isinstance(parameter, dict):
        raise ValueError("NASA POWER response has no properties.parameter object.")
    dates = expected_dates(start, end)
    values = {name: values_for_parameter(parameter, name, dates) for name in PARAMETERS}
    precipitation = sum(values["PRECTOTCORR"])
    evaporation = sum(values["EVLAND"])
    return {
        "weather_observed_days": str(len(dates)),
        "weather_t2m_mean_c": f"{mean(values['T2M']):.3f}",
        "weather_precipitation_total_mm": f"{precipitation:.3f}",
        "weather_rh2m_mean_percent": f"{mean(values['RH2M']):.3f}",
        "weather_ws2m_mean_m_s": f"{mean(values['WS2M']):.3f}",
        "weather_shortwave_mean_mj_m2_day": f"{mean(values['ALLSKY_SFC_SW_DWN']):.3f}",
        "water_gwetroot_mean_fraction": f"{mean(values['GWETROOT']):.3f}",
        "water_gwetroot_min_fraction": f"{min(values['GWETROOT']):.3f}",
        "water_gwetroot_max_fraction": f"{max(values['GWETROOT']):.3f}",
        "water_gwettop_mean_fraction": f"{mean(values['GWETTOP']):.3f}",
        "water_land_evaporation_total_mm": f"{evaporation:.3f}",
        "water_precipitation_minus_land_evaporation_mm": f"{precipitation - evaporation:.3f}",
        "water_context_interpretation": (
            "NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND "
            "are source-modelled variables; precipitation minus land evaporation is an aggregated "
            "context indicator, not a field water balance, irrigation dose, or forecast."
        ),
    }


def fetch_scenario(scenario: Mapping[str, str], out_dir: Path, timeout_s: float) -> tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    start, end = power_dates(scenario["decision_window_utc"])
    dates = expected_dates(start, end)
    params = {
        "parameters": ",".join(PARAMETERS), "community": "AG",
        "longitude": scenario["longitude"], "latitude": scenario["latitude"],
        "start": start, "end": end, "format": "JSON",
    }
    relative_raw = raw_relative_path(scenario["scenario_id"])
    manifest = {
        "scenario_id": scenario["scenario_id"], "site_id": scenario["site_id"], "crop": scenario["crop"],
        "state": scenario["state"], "district": scenario["district"], "decision_date": scenario["decision_date"],
        "decision_window_utc": scenario["decision_window_utc"], "longitude": scenario["longitude"],
        "latitude": scenario["latitude"], "source_id": "NASA_POWER_AG_DAILY", "source_url": "",
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "http_status": "",
        "raw_path": str(relative_raw), "response_sha256": "NONE", "parameter_keys": "", "parameter_units": "",
        "expected_day_count": str(len(dates)), "observed_day_count": "", "source_status": "", "error": "",
    }
    status = {
        "scenario_id": scenario["scenario_id"], "weather_source_status": "unavailable",
        "wetness_source_status": "unavailable", "water_context_status": "unavailable",
        "irrigation_actionability": "context_only_not_a_field_irrigation_instruction",
        "restriction_reason": "not_evaluated",
    }
    try:
        response = requests.get(POWER_URL, params=params, headers=REQUEST_HEADERS, timeout=timeout_s)
        manifest["source_url"] = response.url
        manifest["http_status"] = str(response.status_code)
        response.raise_for_status()
        payload = response.json()
        features = build_features(payload, start, end)
        source_parameters = payload.get("parameters", {})
        units = []
        for name in PARAMETERS:
            unit = source_parameters.get(name, {}).get("units") if isinstance(source_parameters, dict) else None
            if not unit:
                raise ValueError(f"NASA POWER response is missing unit metadata for {name}.")
            units.append(f"{name}={unit}")
        raw_path = out_dir / relative_raw
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
        manifest.update({
            "response_sha256": sha256(response.content).hexdigest(),
            "parameter_keys": ";".join(PARAMETERS),
            "parameter_units": ";".join(units),
            "observed_day_count": features["weather_observed_days"],
            "source_status": "complete_exact_window_nasa_power_ag_response",
        })
        status.update({
            "weather_source_status": "available_complete_exact_window_nasa_power_ag_response",
            "wetness_source_status": "available_modelled_nasa_power_gwetroot_gwettop",
            "water_context_status": "available_retrospective_context_only",
            "restriction_reason": (
                "historical_observations_and_modelled_wetness_do_not_establish_field_moisture, "
                "irrigation_history, or a decision-time forecast"
            ),
        })
        return manifest, {"scenario_id": scenario["scenario_id"], **features}, status
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        manifest.update({
            "source_status": "nasa_power_water_context_failed",
            "error": f"{type(exc).__name__}: {exc}",
        })
        status["restriction_reason"] = f"source_unavailable_or_invalid: {type(exc).__name__}"
        return manifest, {}, status


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Collect exact-window NASA POWER water context for frozen scenarios.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    parser.add_argument("--scenario-id", action="append", help="Run only an exact scenario ID; repeatable pilot option.")
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--delay-s", type=float, default=0.25)
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.delay_s < 0:
        raise SystemExit("--timeout-s must be positive and --delay-s must be non-negative.")
    rows = read_csv(args.manifest)
    requested = set(args.scenario_id or [])
    selected = [row for row in rows if not requested or row["scenario_id"] in requested]
    missing = requested - {row["scenario_id"] for row in selected}
    if missing:
        raise SystemExit(f"Unknown frozen scenario ID(s): {', '.join(sorted(missing))}")
    if not selected:
        raise SystemExit("No frozen scenarios selected.")

    manifests: List[Dict[str, str]] = []
    features: List[Dict[str, str]] = []
    statuses: List[Dict[str, str]] = []
    for index, scenario in enumerate(selected, start=1):
        manifest, feature, status = fetch_scenario(scenario, args.out_dir, args.timeout_s)
        manifests.append(manifest)
        statuses.append(status)
        if feature:
            features.append(feature)
        print(f"[{index}/{len(selected)}] {scenario['scenario_id']}: {manifest['source_status']}")
        if index != len(selected):
            time.sleep(args.delay_s)

    write_csv(args.out_dir / "nasa_power_water_context_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "nasa_power_water_context_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "nasa_power_water_context_status.csv", STATUS_FIELDS, statuses)
    passed = sum(row["source_status"] == "complete_exact_window_nasa_power_ag_response" for row in manifests)
    print(f"NASA POWER water-context availability: {passed}/{len(selected)}.")
    if passed != len(selected):
        raise SystemExit("One or more scenarios failed the NASA POWER water-context gate; inspect the status audit.")


if __name__ == "__main__":
    main()
