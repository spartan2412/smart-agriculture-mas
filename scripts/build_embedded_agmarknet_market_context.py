"""Build market context from the official Agmarknet reports already frozen per scenario.

Every scenario preserves an exact official monthly Agmarknet response under
``data/scenarios/raw/agmarknet``.  That response contains a current-month
price column, plus (when the source published them) prior-month and
same-calendar-month-prior-year columns.  This builder derives no prices: it
only aggregates those source-published market rows, checks the frozen source
hash, and labels absent comparisons as unavailable.

The result is historical market context, never a price forecast or a
sell/hold recommendation.  It is intentionally independent of the optional
network lookback collector, whose expanded API calls can be rate-limited.
"""
from __future__ import annotations

import calendar
import argparse
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_HOST = "api.agmarknet.gov.in"
OFFICIAL_PATH = "/v1/price-trend/wholesale-prices-monthly"

MANIFEST_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "decision_date", "source_url", "raw_path",
    "frozen_payload_sha256", "verified_payload_sha256", "source_commodity_id", "source_state_id",
    "source_district_id", "previous_month_source_status", "same_month_previous_year_source_status",
    "retrieved_at_utc", "source_status", "error",
]
FEATURE_FIELDS = [
    "scenario_id", "market_current_month_price_mean_as_reported",
    "market_previous_month_price_mean_as_reported", "market_previous_month_change_percent",
    "market_same_month_previous_year_price_mean_as_reported", "market_same_month_year_over_year_percent",
    "market_comparison_availability", "market_context_interpretation",
]
STATUS_FIELDS = [
    "scenario_id", "market_source_identity_status", "market_prior_month_status", "market_same_month_prior_year_status",
    "market_context_status", "market_actionability", "restriction_reason",
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


def official_query(url: str) -> Dict[str, str]:
    parsed = urlparse(url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
    required = {"report_mode", "commodity", "state", "district", "year", "month"}
    if parsed.scheme != "https" or parsed.netloc != OFFICIAL_HOST or parsed.path != OFFICIAL_PATH:
        raise ValueError("Frozen market URL is not the official Agmarknet monthly endpoint.")
    if required - set(query):
        raise ValueError("Frozen market URL lacks an exact source identity parameter.")
    return query


def price_key(year: int, month: int) -> str:
    return f"prices_{calendar.month_name[month].casefold()}_{year}"


def as_number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def source_mean(payload: Mapping[str, Any], year: int, month: int) -> float | None:
    if payload.get("success") is not True or not isinstance(payload.get("title"), str):
        raise ValueError("Frozen Agmarknet payload does not identify a successful titled report.")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Frozen Agmarknet payload has no rows list.")
    values = [as_number(row.get(price_key(year, month))) for row in rows if isinstance(row, dict)]
    usable = [value for value in values if value is not None]
    return (sum(usable) / len(usable)) if usable else None


def percentage_change(current: float, previous: float | None) -> str:
    if previous in (None, 0):
        return ""
    return f"{((current - previous) / previous * 100):.3f}"


def build_scenario(scenario: Mapping[str, str], scenario_root: Path) -> tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    scenario_id = scenario["scenario_id"]
    manifest = {
        "scenario_id": scenario_id, "site_id": scenario["site_id"], "crop": scenario["crop"],
        "state": scenario["state"], "district": scenario["district"], "decision_date": scenario["decision_date"],
        "source_url": scenario["market_source_url"], "raw_path": scenario["market_raw_path"],
        "frozen_payload_sha256": scenario["market_current_payload_sha256"], "verified_payload_sha256": "",
        "source_commodity_id": "", "source_state_id": "", "source_district_id": "",
        "previous_month_source_status": "unavailable", "same_month_previous_year_source_status": "unavailable",
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "source_status": "", "error": "",
    }
    status = {
        "scenario_id": scenario_id, "market_source_identity_status": "unavailable", "market_prior_month_status": "unavailable",
        "market_same_month_prior_year_status": "unavailable", "market_context_status": "unavailable",
        "market_actionability": "context_only_not_a_market_sale_instruction", "restriction_reason": "not_evaluated",
    }
    feature = {field: "" for field in FEATURE_FIELDS}
    feature["scenario_id"] = scenario_id
    try:
        query = official_query(scenario["market_source_url"])
        manifest.update({
            "source_commodity_id": query["commodity"], "source_state_id": query["state"], "source_district_id": query["district"],
        })
        decision = date.fromisoformat(scenario["decision_date"])
        if str(decision.year) != query["year"] or str(decision.month) != query["month"]:
            raise ValueError("Frozen source URL month does not match the scenario decision month.")
        raw_path = scenario_root / scenario["market_raw_path"]
        if not raw_path.is_file():
            raise ValueError("Frozen official market payload is absent.")
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        payload_hash = canonical_payload_hash(payload)
        if payload_hash != scenario["market_current_payload_sha256"]:
            raise ValueError("Frozen official market payload hash does not match the scenario manifest.")
        manifest["verified_payload_sha256"] = payload_hash
        current = source_mean(payload, decision.year, decision.month)
        if current is None:
            raise ValueError("Frozen official market report has no current-month price.")
        prior_month_year = decision.year if decision.month > 1 else decision.year - 1
        prior_month = decision.month - 1 or 12
        previous_month_mean = source_mean(payload, prior_month_year, prior_month)
        previous_year_mean = source_mean(payload, decision.year - 1, decision.month)
        if previous_month_mean is not None:
            manifest["previous_month_source_status"] = "available_in_exact_frozen_official_report"
            status["market_prior_month_status"] = "available_in_exact_frozen_official_report"
        else:
            manifest["previous_month_source_status"] = "absent_in_exact_frozen_official_report"
            status["market_prior_month_status"] = "absent_in_exact_frozen_official_report"
        if previous_year_mean is not None:
            manifest["same_month_previous_year_source_status"] = "available_in_exact_frozen_official_report"
            status["market_same_month_prior_year_status"] = "available_in_exact_frozen_official_report"
        else:
            manifest["same_month_previous_year_source_status"] = "absent_in_exact_frozen_official_report"
            status["market_same_month_prior_year_status"] = "absent_in_exact_frozen_official_report"
        comparator_count = int(previous_month_mean is not None) + int(previous_year_mean is not None)
        manifest["source_status"] = "complete_frozen_official_report_context" if comparator_count else "no_comparator_in_frozen_official_report"
        status.update({
            "market_source_identity_status": "verified_exact_frozen_official_report_hash",
            "market_context_status": "available_retrospective_historical_context_only" if comparator_count else "unavailable_no_source_comparator",
            "restriction_reason": (
                "the official monthly report supports historical comparison only; it contains no crop quality, storage cost, quantity, or forecast"
                if comparator_count else "the exact frozen official report has no prior-month or same-month-prior-year price to compare"
            ),
        })
        feature.update({
            "market_current_month_price_mean_as_reported": f"{current:.3f}",
            "market_previous_month_price_mean_as_reported": f"{previous_month_mean:.3f}" if previous_month_mean is not None else "",
            "market_previous_month_change_percent": percentage_change(current, previous_month_mean),
            "market_same_month_previous_year_price_mean_as_reported": f"{previous_year_mean:.3f}" if previous_year_mean is not None else "",
            "market_same_month_year_over_year_percent": percentage_change(current, previous_year_mean),
            "market_comparison_availability": (
                "prior_month_and_same_month_prior_year" if comparator_count == 2 else
                "prior_month_only" if previous_month_mean is not None else
                "same_month_prior_year_only" if previous_year_mean is not None else "no_source_comparator"
            ),
            "market_context_interpretation": (
                "Means and percentage changes use price columns published in the exact frozen official monthly report. "
                "They are retrospective context, not a price forecast or sell/hold instruction."
                if comparator_count else "No source-published prior-month or same-month-prior-year comparator is available."
            ),
        })
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        manifest.update({"source_status": "embedded_market_context_failed", "error": f"{type(exc).__name__}: {exc}"})
        status["restriction_reason"] = f"frozen_source_validation_failed: {type(exc).__name__}"
    return manifest, feature, status


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Build source-backed market context from frozen Agmarknet reports.")
    parser.add_argument("--manifest", type=Path, default=scenarios / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--scenario-root", type=Path, default=scenarios)
    parser.add_argument("--out-dir", type=Path, default=scenarios / "enriched")
    args = parser.parse_args()
    manifests, features, statuses = [], [], []
    for scenario in read_csv(args.manifest):
        manifest, feature, status = build_scenario(scenario, args.scenario_root)
        manifests.append(manifest)
        features.append(feature)
        statuses.append(status)
    write_csv(args.out_dir / "agmarknet_embedded_market_context_manifest.csv", MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "agmarknet_embedded_market_context_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "agmarknet_embedded_market_context_status.csv", STATUS_FIELDS, statuses)
    available = sum(row["source_status"] == "complete_frozen_official_report_context" for row in manifests)
    print(f"Embedded Agmarknet historical context availability: {available}/{len(manifests)}.")


if __name__ == "__main__":
    main()
