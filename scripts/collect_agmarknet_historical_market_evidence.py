"""Collect fixed, public Agmarknet district-market evidence for benchmark sites.

The data.gov.in daily market feed is useful for a current-availability check,
but its records disappear after the relevant marketing period.  It therefore
cannot be the sole market source for a fixed historic benchmark.  Agmarknet
2.0 exposes public monthly price-trend reports whose title binds commodity,
district, state, and month.  This collector stores that immutable report
identity plus a hash of the returned JSON payload.

No account, cookie, or API key is used.  The source scenarios below are
deliberately crop-season specific and must not be silently changed.  A row
passes only when the report contains at least one non-null price for the
declared observation month in the exact registered district.

Run from the repository root:

    python scripts/collect_agmarknet_historical_market_evidence.py \
        --sites data/registry/source_scoped_preflight_pool.csv \
        --out data/registry/preflight_agmarknet_historical_market_coverage.csv
"""
from __future__ import annotations

import argparse
import calendar
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, List, Sequence

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://api.agmarknet.gov.in/v1/"
STATE_INDEX_URL = f"{API_BASE}location/state?page_size=100"
REPORT_URL = f"{API_BASE}price-trend/wholesale-prices-monthly"
REQUEST_HEADERS = {
    # Agmarknet's public API expects browser-origin requests.  These headers
    # do not authenticate a caller and are intentionally recorded nowhere.
    "Origin": "https://agmarknet.gov.in",
    "Referer": "https://agmarknet.gov.in/",
    "User-Agent": "SmartAgricultureMAS/1.0 historical-market-evidence",
    "Accept": "application/json",
}


@dataclass(frozen=True)
class MarketScenario:
    """Frozen crop-specific market observation month and source commodity."""

    year: int
    month: int
    commodity_id: int
    commodity_label: str
    mapping_kind: str

    @property
    def decision_date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{calendar.monthrange(self.year, self.month)[1]:02d}"

    @property
    def price_key(self) -> str:
        return f"prices_{calendar.month_name[self.month].casefold()}_{self.year}"


# The dates are selected inside the stated season and were preflighted
# against every row in source_scoped_preflight_pool.csv.  Rice correctly uses
# the documented paddy market form, not a substituted rice commodity.
SCENARIOS: Dict[str, MarketScenario] = {
    "rice": MarketScenario(2025, 11, 2, "Paddy(Common)", "paddy_market_form_for_rice_crop"),
    "wheat": MarketScenario(2026, 4, 1, "Wheat", "exact_source_commodity"),
    "maize": MarketScenario(2026, 3, 4, "Maize", "exact_source_commodity"),
    "chickpea": MarketScenario(2026, 3, 6, "Bengal Gram(Gram)(Whole)", "exact_source_commodity"),
    "soybean": MarketScenario(2025, 10, 13, "Soyabean", "exact_source_commodity"),
    "tomato": MarketScenario(2025, 12, 65, "Tomato", "exact_source_commodity"),
}


def normalise_name(value: str) -> str:
    """Compare source labels without treating spelling aliases as identical."""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def source_district_name(state: str, district: str) -> str:
    """Return a documented Agmarknet spelling where it differs from registry text."""
    aliases = {
        ("punjab", "bathinda"): "Bhatinda",
    }
    return aliases.get((normalise_name(state), normalise_name(district)), district)


def scenario_for_crop(crop: str) -> MarketScenario:
    try:
        return SCENARIOS[crop.casefold()]
    except KeyError as exc:
        raise ValueError(f"No frozen Agmarknet market scenario exists for crop {crop!r}.") from exc


def fetch_state_index(timeout_s: float) -> List[Dict[str, Any]]:
    response = requests.get(STATE_INDEX_URL, headers=REQUEST_HEADERS, timeout=timeout_s)
    response.raise_for_status()
    payload = response.json()
    states = payload.get("states", [])
    if payload.get("status") != "success" or not isinstance(states, list):
        raise ValueError("Agmarknet state index did not contain a successful states list.")
    return [state for state in states if isinstance(state, dict)]


def resolve_location(
    states: Iterable[Dict[str, Any]], state_name: str, district_name: str
) -> tuple[int, str, int, str]:
    """Resolve only an exact state and documented district spelling."""
    source_district = source_district_name(state_name, district_name)
    state_matches = [
        state for state in states
        if normalise_name(str(state.get("state_name", ""))) == normalise_name(state_name)
    ]
    if len(state_matches) != 1:
        raise ValueError(f"Could not resolve exactly one Agmarknet state for {state_name!r}.")
    state = state_matches[0]
    district_matches = [
        district for district in state.get("districts", [])
        if isinstance(district, dict)
        and normalise_name(str(district.get("district_name", ""))) == normalise_name(source_district)
    ]
    if len(district_matches) != 1:
        raise ValueError(
            f"Could not resolve exactly one Agmarknet district for {district_name!r}, {state_name!r}."
        )
    district = district_matches[0]
    return (
        int(state["id"]),
        str(state["state_name"]).strip(),
        int(district["id"]),
        str(district["district_name"]).strip(),
    )


def query_report(
    scenario: MarketScenario, state_id: int, district_id: int, timeout_s: float
) -> tuple[str, Dict[str, Any]]:
    params = {
        "report_mode": "Marketwise",
        "commodity": scenario.commodity_id,
        "year": scenario.year,
        "month": scenario.month,
        "state": state_id,
        "district": district_id,
    }
    response = requests.get(REPORT_URL, params=params, headers=REQUEST_HEADERS, timeout=timeout_s)
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is not True or not isinstance(payload.get("rows", []), list):
        raise ValueError("Agmarknet market report did not contain a successful rows list.")
    return response.url, payload


def payload_hash(payload: Dict[str, Any]) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def build_coverage_row(site: Dict[str, str], states: List[Dict[str, Any]], timeout_s: float) -> Dict[str, str]:
    scenario = scenario_for_crop(site["crop"])
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    row = {
        "retrieved_at_utc": retrieved_at,
        "source_id": "AGMARKNET_2_HISTORICAL_MARKET",
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"],
        "district": site["district"],
        "benchmark_market_decision_date": scenario.decision_date,
        "source_commodity_id": str(scenario.commodity_id),
        "source_commodity": scenario.commodity_label,
        "market_mapping_status": scenario.mapping_kind,
        "source_state_id": "",
        "source_state": "",
        "source_district_id": "",
        "source_district": "",
        "official_url": "NONE",
        "report_title": "NONE",
        "payload_sha256": "NONE",
        "market_count": "",
        "priced_market_count": "",
        "priced_market_examples": "NONE",
        "query_status": "",
        "historical_market_status": "",
        "notes": "",
    }
    try:
        state_id, source_state, district_id, source_district = resolve_location(
            states, site["state"], site["district"]
        )
        official_url, payload = query_report(scenario, state_id, district_id, timeout_s)
        report_title = str(payload.get("title", ""))
        title_required = (
            scenario.commodity_label.casefold() in report_title.casefold()
            and source_district.casefold() in report_title.casefold()
            and source_state.casefold() in report_title.casefold()
        )
        markets = [item for item in payload["rows"] if isinstance(item, dict)]
        priced = [item for item in markets if item.get(scenario.price_key) is not None]
        examples = sorted({str(item.get("market", "")).strip() for item in priced if item.get("market")})
        row.update({
            "source_state_id": str(state_id),
            "source_state": source_state,
            "source_district_id": str(district_id),
            "source_district": source_district,
            "official_url": official_url,
            "report_title": report_title or "NONE",
            "payload_sha256": payload_hash(payload),
            "market_count": str(len(markets)),
            "priced_market_count": str(len(priced)),
            "priced_market_examples": ";".join(examples) if examples else "NONE",
            "query_status": "ok",
            "historical_market_status": (
                "same_crop_historical_district_market_report_available"
                if title_required and priced
                else "historical_district_report_has_no_accepted_observation"
            ),
            "notes": (
                "Official public monthly report; the source title binds commodity, district, state and month."
                if title_required and priced
                else "The exact district report was returned but did not contain a non-null price for the frozen observation month."
            ),
        })
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        row.update({
            "query_status": "request_failed",
            "historical_market_status": "historical_market_not_evaluated",
            "notes": f"{type(exc).__name__}: {exc}",
        })
    return row


OUTPUT_FIELDS = [
    "retrieved_at_utc", "source_id", "site_id", "crop", "state", "district",
    "benchmark_market_decision_date", "source_commodity_id", "source_commodity",
    "market_mapping_status", "source_state_id", "source_state", "source_district_id",
    "source_district", "official_url", "report_title", "payload_sha256", "market_count",
    "priced_market_count", "priced_market_examples", "query_status", "historical_market_status",
    "notes",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect fixed public Agmarknet district-market evidence for benchmark sites."
    )
    parser.add_argument(
        "--sites",
        type=Path,
        default=PROJECT_ROOT / "data" / "registry" / "source_scoped_preflight_pool.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "data" / "registry" / "preflight_agmarknet_historical_market_coverage.csv",
    )
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--delay-s", type=float, default=0.2)
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.delay_s < 0:
        raise SystemExit("--timeout-s must be positive and --delay-s cannot be negative.")
    with args.sites.open(newline="", encoding="utf-8") as source_file:
        sites = list(csv.DictReader(source_file))
    if not sites:
        raise SystemExit(f"No site rows found in {args.sites}")
    states = fetch_state_index(args.timeout_s)
    rows = []
    for index, site in enumerate(sites, start=1):
        row = build_coverage_row(site, states, args.timeout_s)
        rows.append(row)
        print(
            f"[{index}/{len(sites)}] {site['site_id']}: "
            f"{row['historical_market_status']} ({row['priced_market_count']} markets)"
        )
        if index != len(sites):
            time.sleep(args.delay_s)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(
        row["historical_market_status"] == "same_crop_historical_district_market_report_available"
        for row in rows
    )
    print(f"Wrote {len(rows)} rows to {args.out}; exact historical market reports: {passed}/{len(rows)}")


if __name__ == "__main__":
    main()
