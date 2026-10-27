"""Audit whether market abstentions have an earlier same-source comparator.

Only the three calendar months strictly before the scenario decision month are
queried. Reports must preserve the exact frozen commodity--district--state
title identity. Raw public responses are saved even when the requested price
column is empty, so a genuine off-market period is evidence rather than an
unexplained blank.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_URL = "https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly"
REQUEST_HEADERS = {
    "Origin": "https://agmarknet.gov.in", "Referer": "https://agmarknet.gov.in/",
    "User-Agent": "SmartAgricultureMAS/1.0 market-recovery-feasibility", "Accept": "application/json",
}
FIELDS = [
    "scenario_id", "crop", "state", "district", "decision_date", "current_report_url", "lookback_months",
    "prior_report_urls", "prior_report_raw_paths", "prior_report_sha256s", "prior_month_results",
    "usable_prior_price_months", "recovery_feasibility_status", "retrieved_at_utc", "error",
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


def previous_months(decision_date: str, count: int = 3) -> List[Tuple[int, int]]:
    current = date.fromisoformat(decision_date).replace(day=1)
    result = []
    for _ in range(count):
        month = current.month - 1 or 12
        year = current.year - 1 if current.month == 1 else current.year
        result.append((year, month))
        current = current.replace(year=year, month=month)
    return list(reversed(result))


def official_query(url: str) -> Dict[str, str]:
    parsed = urlparse(url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
    required = {"report_mode", "commodity", "state", "district"}
    if parsed.scheme != "https" or parsed.netloc != "api.agmarknet.gov.in" or parsed.path != "/v1/price-trend/wholesale-prices-monthly":
        raise ValueError("Scenario market URL is not the official monthly Agmarknet endpoint.")
    if required - set(query):
        raise ValueError("Scenario market URL lacks an exact identity query parameter.")
    return query


def title_prefix(title: str) -> str:
    return title.split("–", maxsplit=1)[0].strip().casefold()


def has_requested_price(payload: Mapping[str, Any], year: int, month: int, expected_prefix: str) -> bool:
    if payload.get("success") is not True or title_prefix(str(payload.get("title", ""))) != expected_prefix:
        raise ValueError("Returned report does not preserve the frozen crop/district/state identity.")
    key = f"prices_{date(year, month, 1).strftime('%B').casefold()}_{year}"
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Returned report has no rows list.")
    return any(isinstance(row, dict) and row.get(key) is not None for row in rows)


def relative_raw_path(scenario_id: str, year: int, month: int) -> Path:
    return Path("raw") / "agmarknet_market_recovery" / f"{scenario_id}_{year:04d}{month:02d}.json"


def fetch_with_backoff(query: Mapping[str, str], year: int, month: int, timeout_s: float) -> tuple[str, bytes, Dict[str, Any]]:
    for attempt in range(1, 4):
        response = requests.get(REPORT_URL, params={**query, "year": year, "month": month}, headers=REQUEST_HEADERS, timeout=timeout_s)
        if response.status_code not in {429, 503}:
            response.raise_for_status()
            return response.url, response.content, response.json()
        if attempt < 3:
            time.sleep(5 * attempt)
    response.raise_for_status()
    raise AssertionError("unreachable")


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Check strict prior-month market recovery for current abstentions.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--market-status", type=Path, default=scenarios / "enriched" / "agmarknet_embedded_market_context_status.csv")
    parser.add_argument("--scenario-root", type=Path, default=scenarios)
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    parser.add_argument("--delay-s", type=float, default=2.0)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    args = parser.parse_args()
    if args.delay_s < 0 or args.timeout_s <= 0:
        raise SystemExit("delay must be non-negative and timeout must be positive")
    status_by_id = {row["scenario_id"]: row for row in read_csv(args.market_status)}
    selected = [
        row for row in read_csv(args.manifest)
        if status_by_id[row["scenario_id"]]["market_context_status"] == "unavailable_no_source_comparator"
    ]
    output = []
    for index, scenario in enumerate(selected, start=1):
        row = {
            "scenario_id": scenario["scenario_id"], "crop": scenario["crop"], "state": scenario["state"],
            "district": scenario["district"], "decision_date": scenario["decision_date"], "current_report_url": scenario["market_source_url"],
            "lookback_months": "3", "prior_report_urls": "", "prior_report_raw_paths": "", "prior_report_sha256s": "",
            "prior_month_results": "", "usable_prior_price_months": "0", "recovery_feasibility_status": "", "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "error": "",
        }
        try:
            current = json.loads((args.scenario_root / scenario["market_raw_path"]).read_text(encoding="utf-8"))
            prefix = title_prefix(str(current.get("title", "")))
            query = official_query(scenario["market_source_url"])
            urls, paths, hashes, results = [], [], [], []
            usable = 0
            for year, month in previous_months(scenario["decision_date"]):
                url, content, payload = fetch_with_backoff(query, year, month, args.timeout_s)
                relative = relative_raw_path(scenario["scenario_id"], year, month)
                destination = args.out_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                available = has_requested_price(payload, year, month, prefix)
                usable += int(available)
                urls.append(url); paths.append(str(relative)); hashes.append(sha256(content).hexdigest())
                results.append(f"{year:04d}-{month:02d}={'reported_price' if available else 'no_reported_price'}")
                time.sleep(args.delay_s)
            row.update({
                "prior_report_urls": ";".join(urls), "prior_report_raw_paths": ";".join(paths),
                "prior_report_sha256s": ";".join(hashes), "prior_month_results": ";".join(results),
                "usable_prior_price_months": str(usable),
                "recovery_feasibility_status": (
                    "possible_two_or_more_strict_prior_prices" if usable >= 2 else
                    "partial_one_strict_prior_price_no_trend" if usable == 1 else
                    "confirmed_no_strict_prior_price_in_exact_source_months"
                ),
            })
        except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            row.update({"recovery_feasibility_status": "market_recovery_check_failed", "error": f"{type(exc).__name__}: {exc}"})
        output.append(row)
        print(f"[{index}/{len(selected)}] {scenario['scenario_id']}: {row['recovery_feasibility_status']}")
    write_csv(args.out_dir / "market_recovery_feasibility.csv", FIELDS, output)
    recovered = sum(row["recovery_feasibility_status"] == "possible_two_or_more_strict_prior_prices" for row in output)
    print(f"Market strict-recovery feasibility: {recovered}/{len(output)}.")


if __name__ == "__main__":
    main()
