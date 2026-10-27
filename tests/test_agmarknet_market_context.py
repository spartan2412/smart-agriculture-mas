from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_agmarknet_market_context import previous_months, report_mean, source_query


def test_previous_months_are_strictly_before_decision_month_across_year_boundary():
    assert previous_months("2025-01-31", 3) == [(2024, 10), (2024, 11), (2024, 12)]


def test_report_mean_requires_exact_title_identity_and_non_null_month_values():
    payload = {
        "success": True,
        "title": "Market-wise Wholesale Prices Monthly Analysis for Tomato in Nashik, Maharashtra – October, 2024",
        "rows": [{"prices_october_2024": 1000}, {"prices_october_2024": 3000}],
    }
    assert report_mean(payload, 2024, 10, "market-wise wholesale prices monthly analysis for tomato in nashik, maharashtra") == 2000.0
    with pytest.raises(ValueError, match="title"):
        report_mean(payload, 2024, 10, "different title")


def test_source_query_rejects_non_official_or_incomplete_market_urls():
    url = "https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=65&state=27&district=1"
    assert source_query(url)["commodity"] == "65"
    with pytest.raises(ValueError, match="official"):
        source_query("https://example.invalid/market")
