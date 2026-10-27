"""Collect strictly pre-decision Agmarknet market context for frozen scenarios.

The frozen benchmark already preserves one exact same-crop/state/district
monthly Agmarknet report for every scenario. This additive collector retrieves
the three *calendar months before* that report using the same source commodity,
state ID, district ID, and report mode. It stores every raw response and
requires the returned report title to preserve the current report's
commodity--district--state title prefix.

The result is a retrospective historical market context, not a sale-timing
forecast. Raw source prices retain the provider's units as reported; only the
unitless percentage change between like-for-like reports is calculated.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_URL = "https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly"
REQUEST_HEADERS = {
    "Origin": "https://agmarknet.gov.in",
    "Referer": "https://agmarknet.gov.in/",
    "User-Agent": "SmartAgricultureMAS/1.0 scenario-market-context",
    "Accept": "application/json",
}

MANIFEST_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "decision_date", "current_report_url",
    "current_report_raw_path", "source_commodity_id", "source_state_id", "source_district_id",
    "lookback_months_requested", "lookback_months_available", "prior_report_urls", "prior_report_raw_paths",
    "prior_report_sha256s", "prior_report_availability", "retrieved_at_utc", "source_status", "error",
]
FEATURE_FIELDS = [
    "scenario_id", "market_current_month_price_mean_as_reported", "market_predecision_month_count",
    "market_predecision_oldest_month", "market_predecision_oldest_price_mean_as_reported",
    "market_predecision_latest_month", "market_predecision_latest_price_mean_as_reported",
    "market_predecision_trend_percent", "market_same_month_previous_year_price_mean_as_reported",
    "market_same_month_year_over_year_percent", "market_context_type", "market_price_unit_status",
    "market_context_interpretation",
]
STATUS_FIELDS = [
    "scenario_id", "current_report_status", "predecision_history_status", "market_context_status",
    "market_actionability", "restriction_reason",
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


def canonical_payload_hash(payload: Mapping[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def previous_months(decision_date: str, count: int) -> List[Tuple[int, int]]:
    if count <= 0:
        raise ValueError("Lookback month count must be positive.")
    current = date.fromisoformat(decision_date).replace(day=1)
    months: List[Tuple[int, int]] = []
    for _ in range(count):
        previous = current.month - 1 or 12
        year = current.year - 1 if current.month == 1 else current.year
        months.append((year, previous))
        current = current.replace(year=year, month=previous)
    return list(reversed(months))


def price_key(year: int, month: int) -> str:
    return f"prices_{calendar.month_name[month].casefold()}_{year}"


def source_query(current_url: str) -> Dict[str, str]:
    parsed = urlparse(current_url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
    required = {"report_mode", "commodity", "state", "district"}
    if parsed.scheme != "https" or parsed.netloc != "api.agmarknet.gov.in" or parsed.path != "/v1/price-trend/wholesale-prices-monthly":
        raise ValueError("Frozen market URL is not the expected official Agmarknet monthly report endpoint.")
    if required - set(query):
        raise ValueError("Frozen market URL is missing a required exact-source query parameter.")
    return query


def title_prefix(title: str) -> str:
    # The official monthly reports use an en dash before the month/year suffix.
    value = title.split("–", maxsplit=1)[0].strip()
    if not value:
        raise ValueError("Agmarknet report has no usable title prefix.")
    return re.sub(r"\s+", " ", value).casefold()


def as_number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def report_mean(payload: Mapping[str, Any], year: int, month: int, expected_prefix: str) -> float:
    if payload.get("success") is not True:
        raise ValueError("Agmarknet report did not return success=true.")
    title = payload.get("title")
    if not isinstance(title, str) or title_prefix(title) != expected_prefix:
        raise ValueError("Agmarknet report title does not preserve the exact commodity/district/state identity.")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Agmarknet report has no rows list.")
    values = [as_number(row.get(price_key(year, month))) for row in rows if isinstance(row, dict)]
    values = [value for value in values if value is not None]
    if not values:
        raise ValueError("Agmarknet report has no non-null price for its requested month.")
    return sum(values) / len(values)


def raw_relative_path(scenario_id: str, year: int, month: int) -> Path:
    if not scenario_id.replace("_", "").isalnum():
        raise ValueError(f"Scenario identifier is not safe for a raw filename: {scenario_id!r}")
    return Path("raw") / "agmarknet_market_context" / f"{scenario_id}_{year:04d}{month:02d}.json"


def fetch_report(query: Mapping[str, str], year: int, month: int, timeout_s: float) -> Tuple[str, bytes, Dict[str, Any]]:
    params = {**query, "year": str(year), "month": str(month)}
    response = requests.get(REPORT_URL, params=params, headers=REQUEST_HEADERS, timeout=timeout_s)
    response.raise_for_status()
    return response.url, response.content, response.json()


def build_scenario(
    scenario: Mapping[str, str], scenario_root: Path, out_dir: Path, lookback: int, timeout_s: float
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    scenario_id = scenario["scenario_id"]
    manifest = {
        "scenario_id": scenario_id, "site_id": scenario["site_id"], "crop": scenario["crop"], "state": scenario["state"],
        "district": scenario["district"], "decision_date": scenario["decision_date"], "current_report_url": scenario["market_source_url"],
        "current_report_raw_path": scenario["market_raw_path"], "source_commodity_id": "", "source_state_id": "", "source_district_id": "",
        "lookback_months_requested": str(lookback), "lookback_months_available": "0", "prior_report_urls": "",
        "prior_report_raw_paths": "", "prior_report_sha256s": "", "prior_report_availability": "",
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_status": "", "error": "",
    }
    status = {
        "scenario_id": scenario_id, "current_report_status": "unavailable", "predecision_history_status": "unavailable",
        "market_context_status": "unavailable", "market_actionability": "context_only_not_a_market_sale_instruction",
        "restriction_reason": "not_evaluated",
    }
    try:
        query = source_query(scenario["market_source_url"])
        manifest.update({
            "source_commodity_id": query["commodity"], "source_state_id": query["state"], "source_district_id": query["district"],
        })
        current_raw = scenario_root / scenario["market_raw_path"]
        if not current_raw.is_file():
            raise ValueError("Frozen current-month market raw payload is absent.")
        current_payload = json.loads(current_raw.read_text(encoding="utf-8"))
        decision = date.fromisoformat(scenario["decision_date"])
        current_mean = report_mean(current_payload, decision.year, decision.month, title_prefix(str(current_payload.get("title", ""))))
        prefix = title_prefix(str(current_payload.get("title", "")))
        try:
            same_month_previous_year_mean = report_mean(current_payload, decision.year - 1, decision.month, prefix)
        except ValueError:
            same_month_previous_year_mean = None
        status["current_report_status"] = "available_frozen_exact_month_report"
        prior = []
        report_records = []
        for year, month in previous_months(scenario["decision_date"], lookback):
            url, content, payload = fetch_report(query, year, month, timeout_s)
            relative_path = raw_relative_path(scenario_id, year, month)
            raw_path = out_dir / relative_path
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(content)
            record = {
                "year": year, "month": month, "url": url, "path": relative_path,
                "hash": canonical_payload_hash(payload), "availability": "",
            }
            try:
                record["mean"] = report_mean(payload, year, month, prefix)
                record["availability"] = "available_exact_same_source_month"
                prior.append(record)
            except ValueError as exc:
                # A market can be genuinely absent in an off-season month. Preserve the
                # exact raw response and make that absence auditable; never impute it.
                record["availability"] = f"unavailable_source_month: {type(exc).__name__}"
            report_records.append(record)
        # Keep the complete audit trail even if fewer than two usable months
        # remain and the scenario must therefore abstain from a trend.
        manifest.update({
            "lookback_months_available": str(len(prior)),
            "prior_report_urls": ";".join(item["url"] for item in report_records),
            "prior_report_raw_paths": ";".join(str(item["path"]) for item in report_records),
            "prior_report_sha256s": ";".join(item["hash"] for item in report_records),
            "prior_report_availability": ";".join(
                f"{item['year']:04d}-{item['month']:02d}={item['availability']}" for item in report_records
            ),
        })
        if len(prior) < 2 and same_month_previous_year_mean is None:
            raise ValueError(
                "Fewer than two exact prior months contain source prices and the exact same-month prior-year comparison is absent."
            )
        oldest = prior[0] if prior else None
        latest = prior[-1] if prior else None
        trend = (
            ((latest["mean"] - oldest["mean"]) / oldest["mean"] * 100)
            if oldest is not None and latest is not None and oldest["mean"]
            else None
        )
        year_over_year = (
            ((current_mean - same_month_previous_year_mean) / same_month_previous_year_mean * 100)
            if same_month_previous_year_mean not in (None, 0)
            else None
        )
        has_monthly_trend = len(prior) >= 2
        manifest.update({
            "source_status": (
                "complete_exact_source_predecision_market_history"
                if len(prior) == lookback
                else (
                    "partial_exact_source_history_source_month_gap"
                    if has_monthly_trend
                    else "available_exact_source_same_month_prior_year_context_no_monthly_trend"
                )
            ),
        })
        status.update({
            "predecision_history_status": (
                "available_exact_same_source_three_prior_months"
                if len(prior) == lookback
                else (
                    "available_exact_same_source_two_or_more_prior_months_with_source_gap"
                    if has_monthly_trend
                    else "unavailable_source_month_gap_same_month_prior_year_available"
                )
            ),
            "market_context_status": (
                "available_retrospective_historical_context_only"
                if has_monthly_trend
                else "available_retrospective_same_month_prior_year_context_only"
            ),
            "restriction_reason": (
                "historical monthly reports preserve no crop quality, storage cost, quantity, or decision-time price forecast"
            ),
        })
        feature = {
            "scenario_id": scenario_id,
            "market_current_month_price_mean_as_reported": f"{current_mean:.3f}",
            "market_predecision_month_count": str(len(prior)),
            "market_predecision_oldest_month": f"{oldest['year']:04d}-{oldest['month']:02d}" if oldest else "",
            "market_predecision_oldest_price_mean_as_reported": f"{oldest['mean']:.3f}" if oldest else "",
            "market_predecision_latest_month": f"{latest['year']:04d}-{latest['month']:02d}" if latest else "",
            "market_predecision_latest_price_mean_as_reported": f"{latest['mean']:.3f}" if latest else "",
            "market_predecision_trend_percent": f"{trend:.3f}" if trend is not None else "",
            "market_same_month_previous_year_price_mean_as_reported": (
                f"{same_month_previous_year_mean:.3f}" if same_month_previous_year_mean is not None else ""
            ),
            "market_same_month_year_over_year_percent": f"{year_over_year:.3f}" if year_over_year is not None else "",
            "market_context_type": (
                "same_source_prior_month_trend_and_optional_same_month_prior_year_comparison"
                if has_monthly_trend
                else "same_source_same_month_prior_year_comparison_only"
            ),
            "market_price_unit_status": "source_unit_not_supplied_per_record_no_conversion_performed",
            "market_context_interpretation": (
                "The source-backed comparison is retrospective historical market context only. It has no crop "
                "quality, storage cost, quantity, or decision-time price forecast and cannot issue a sell/hold instruction."
            ),
        }
        return manifest, feature, status
    except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        manifest.update({"source_status": "market_context_failed", "error": f"{type(exc).__name__}: {exc}"})
        status["restriction_reason"] = f"source_or_identity_validation_failed: {type(exc).__name__}"
        return manifest, {}, status


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Collect strict pre-decision Agmarknet market context for frozen scenarios.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--scenario-root", type=Path, default=scenarios)
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    parser.add_argument("--scenario-id", action="append", help="Run only an exact scenario ID; repeatable pilot option.")
    parser.add_argument("--lookback-months", type=int, default=3)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--delay-s", type=float, default=0.25)
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.delay_s < 0 or args.lookback_months <= 0:
        raise SystemExit("timeout and lookback must be positive; delay must be non-negative.")
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
        manifest, feature, status = build_scenario(
            scenario, args.scenario_root, args.out_dir, args.lookback_months, args.timeout_s
        )
        manifests.append(manifest)
        statuses.append(status)
        if feature:
            features.append(feature)
        print(f"[{index}/{len(selected)}] {scenario['scenario_id']}: {manifest['source_status']}")
        if index != len(selected):
            time.sleep(args.delay_s)
    write_csv(args.out_dir / "agmarknet_market_context_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "agmarknet_market_context_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "agmarknet_market_context_status.csv", STATUS_FIELDS, statuses)
    usable_statuses = {
        "complete_exact_source_predecision_market_history",
        "partial_exact_source_history_source_month_gap",
        "available_exact_source_same_month_prior_year_context_no_monthly_trend",
    }
    passed = sum(row["source_status"] in usable_statuses for row in manifests)
    print(f"Agmarknet historical-context availability: {passed}/{len(selected)} (a source-backed monthly trend or same-month prior-year comparator is required).")
    if passed != len(selected):
        raise SystemExit("One or more scenarios failed the Agmarknet market-context gate; inspect the status audit.")


if __name__ == "__main__":
    main()
