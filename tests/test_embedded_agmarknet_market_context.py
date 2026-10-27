from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_embedded_agmarknet_market_context import official_query, percentage_change, source_mean


def test_source_mean_only_uses_the_requested_source_column():
    payload = {
        "success": True,
        "title": "Market-wise Wholesale Prices Monthly Analysis for Wheat in Ludhiana, Punjab – April, 2026",
        "rows": [{"prices_april_2026": 2000, "prices_march_2026": 1900}, {"prices_april_2026": 2200}],
    }
    assert source_mean(payload, 2026, 4) == 2100.0
    assert source_mean(payload, 2026, 3) == 1900.0
    assert source_mean(payload, 2025, 4) is None


def test_comparison_math_is_blank_without_a_real_reference():
    assert percentage_change(2100.0, 2000.0) == "5.000"
    assert percentage_change(2100.0, None) == ""
    assert percentage_change(2100.0, 0.0) == ""


def test_official_query_requires_the_frozen_identity_parameters():
    url = "https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=1&year=2026&month=4&state=28&district=463"
    assert official_query(url)["district"] == "463"
