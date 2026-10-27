"""Generate the 270 non-synthetic supplementary historical contexts.

The 30 anchor contexts in :mod:`generate_anchor_scenarios` bind one frozen
month to each final study site.  This script adds *nine distinct historic
months per site*, producing 270 further contexts (300 total).  It does not
copy, perturb, interpolate, or simulate any source values.

A month is admitted only when all of these independent checks pass:

* its month falls in the final registry's declared crop-season window;
* the public Agmarknet monthly report binds the registered crop commodity,
  district, state, month, and has one or more reported prices;
* NASA POWER returns a complete daily weather series for the exact
  representative cell and calendar month;
* Microsoft Planetary Computer returns a Sentinel-2 L2A item for that same
  cell/month meeting the pre-declared cloud and nodata thresholds; and
* the static SoilGrids profile and regional management-source bundle still
  pass the frozen registry evidence checks.

The historical month is a public-data *context*, not proof of a particular
farm crop stage, disease event, fertilizer dose, or protection action.  Those
claims remain deliberately unavailable in every generated row.

Candidate selection is deterministic and outcome-independent: enumerate
eligible months newest-first from the registered anchor date back to January
2016, exclude the anchor month, and retain the first nine that pass every
source gate. Candidate failures are preserved in a separate audit CSV.

The only documented exception to the pre-anchor search boundary is tomato:
the public historical market archive supplies only six pre-anchor all-gate
windows for Krishnagiri. The fixed source cutoff therefore includes January
through March 2026, which are real post-anchor months in the same declared
October--March rabi window. Their relation to the anchor is explicit in the
manifest and no source data after March 2026 is considered.

Run from the repository root:

    .venv-macos/bin/python scripts/generate_supplementary_scenarios.py
"""
from __future__ import annotations

import argparse
import calendar
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Sequence
from urllib.parse import urlencode

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_agmarknet_historical_market_evidence import (
    REQUEST_HEADERS as AGMARKNET_HEADERS,
    MarketScenario,
    fetch_state_index,
    payload_hash,
    resolve_location,
    scenario_for_crop,
)
from scripts.collect_sentinel_scene_coverage import (
    MAX_CLOUD_COVER,
    MAX_NODATA_PERCENT,
    REQUEST_HEADERS as SENTINEL_HEADERS,
    STAC_SEARCH_URL,
    build_search_payload,
    feature_sort_key,
    is_quality_candidate,
)
from scripts.generate_anchor_scenarios import (
    EVIDENCE_FIELDS,
    FEATURE_FIELDS,
    MANIFEST_FIELDS,
    NASA_HEADERS,
    SOIL_PROPERTIES,
    SOIL_STATUS,
    VERIFIED_SOURCE_STATUS,
    by_site,
    index_soil,
    management_bundle,
    numeric,
    read_csv,
    weather_features,
    write_csv,
)


TARGET_SUPPLEMENTARY_PER_SITE = 9
# Some exact crop--district Agmarknet series are reported only in a single
# market month per season (for example, Punjab wheat in April).  The 2016
# lower bound provides ten possible Sentinel-era seasons before the latest
# wheat anchor.  It is a fixed source-search horizon, not an attempt to fill
# unavailable months; every older candidate remains subject to every gate.
EARLIEST_CANDIDATE_YEAR = 2016
MAX_SOURCE_ATTEMPTS = 3
SCENARIO_TYPE = "verified_supplementary_historical_context"
READY_STATUS = "ready_for_context_evaluation_with_required_abstentions"
SEASON_MEMBERSHIP_STATUS = "registry_declared_month_range"
SATELLITE_STATUS = "same_month_quality_scene_metadata_available"
MANAGEMENT_TEMPORAL_STATUS = (
    "regional_reference_only_not_a_historical_or_farm_specific_prescription"
)
# This source-time cutoff is used only when a documented public archive cannot
# supply nine pre-anchor contexts. It is not an inferred phenology boundary.
POST_ANCHOR_SOURCE_CUTOFF_BY_CROP = {"tomato": "2026-03-31"}

# Supplementary records expose their date-specific Sentinel request provenance
# in addition to the common anchor-manifest schema.  Keeping the anchor fields
# makes the consolidated 300-row manifest straightforward to consume.
SUPPLEMENTARY_MANIFEST_FIELDS = [
    *MANIFEST_FIELDS,
    "candidate_selection_rank",
    "anchor_temporal_relation",
    "candidate_search_upper_bound",
    "season_membership_status",
    "market_source_commodity_id",
    "market_source_commodity",
    "market_mapping_status",
    "market_source_state",
    "market_source_district",
    "satellite_search_url",
    "satellite_search_payload_sha256",
    "satellite_response_sha256",
    "satellite_raw_path",
    "satellite_window_utc",
    "soil_evidence_status",
    "management_temporal_status",
]
SUPPLEMENTARY_EVIDENCE_FIELDS = [
    *EVIDENCE_FIELDS,
    "season_membership_status",
    "satellite_evidence_status",
    "management_temporal_status",
]
CANDIDATE_REJECTION_FIELDS = [
    "site_id", "crop", "state", "district", "candidate_decision_date",
    "candidate_selection_rank", "failed_gate", "market_source_url",
    "weather_source_url", "satellite_search_url", "reason",
]


@dataclass(frozen=True)
class CandidateMonth:
    """An eligible calendar month evaluated for one registered site."""

    year: int
    month: int
    rank: int

    @property
    def decision_date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{calendar.monthrange(self.year, self.month)[1]:02d}"

    @property
    def start_compact(self) -> str:
        return f"{self.year:04d}{self.month:02d}01"

    @property
    def end_compact(self) -> str:
        return self.decision_date.replace("-", "")

    @property
    def window_utc(self) -> str:
        return (
            f"{self.year:04d}-{self.month:02d}-01T00:00:00Z/"
            f"{self.decision_date}T23:59:59Z"
        )


def parse_season_window(value: str) -> set[int]:
    """Parse a final-registry month range such as ``Nov-Apr`` without guessing."""
    month_lookup = {name.casefold()[:3]: number for number, name in enumerate(calendar.month_abbr) if name}
    try:
        start_text, end_text = (part.strip().casefold()[:3] for part in value.split("-", maxsplit=1))
        start, end = month_lookup[start_text], month_lookup[end_text]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid final-registry season window: {value!r}") from exc
    if start <= end:
        return set(range(start, end + 1))
    return set(range(start, 13)) | set(range(1, end + 1))


def candidate_search_upper_bound(site: Mapping[str, str]) -> date:
    """Return the site-specific frozen maximum source date for the search."""
    anchor = date.fromisoformat(site["fixed_decision_date"])
    configured = POST_ANCHOR_SOURCE_CUTOFF_BY_CROP.get(site["crop"].casefold())
    if configured is None:
        return anchor - timedelta(days=1)
    maximum = date.fromisoformat(configured)
    if maximum <= anchor:
        raise ValueError("A post-anchor source cutoff must be later than its anchor date.")
    return maximum


def anchor_temporal_relation(site: Mapping[str, str], candidate: CandidateMonth) -> str:
    """Describe the candidate date relative to the immutable anchor window."""
    anchor = date.fromisoformat(site["fixed_decision_date"])
    chosen = date.fromisoformat(candidate.decision_date)
    if chosen < anchor:
        return "pre_anchor_historical_context"
    if chosen > anchor:
        return "post_anchor_same_declared_season_historical_context"
    raise ValueError("A supplementary candidate cannot be the anchor date.")


def candidate_months(site: Mapping[str, str]) -> Iterator[CandidateMonth]:
    """Yield eligible source months newest-first under the documented rule."""
    anchor = date.fromisoformat(site["fixed_decision_date"])
    maximum = candidate_search_upper_bound(site)
    allowed_months = parse_season_window(site["season_window"])
    rank = 0
    for year in range(maximum.year, EARLIEST_CANDIDATE_YEAR - 1, -1):
        first_month = maximum.month if year == maximum.year else 12
        for month in range(first_month, 0, -1):
            candidate = date(year, month, calendar.monthrange(year, month)[1])
            if candidate > maximum or candidate == anchor or month not in allowed_months:
                continue
            rank += 1
            yield CandidateMonth(year, month, rank)


def market_scenario(crop: str, candidate: CandidateMonth) -> MarketScenario:
    """Reuse the registered crop-to-source commodity mapping at a new month."""
    registered = scenario_for_crop(crop)
    return MarketScenario(
        candidate.year,
        candidate.month,
        registered.commodity_id,
        registered.commodity_label,
        registered.mapping_kind,
    )


def build_market_url(scenario: MarketScenario, state_id: int, district_id: int) -> str:
    params = {
        "report_mode": "Marketwise",
        "commodity": scenario.commodity_id,
        "year": scenario.year,
        "month": scenario.month,
        "state": state_id,
        "district": district_id,
    }
    return "https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?" + urlencode(params)


def build_weather_url(site: Mapping[str, str], candidate: CandidateMonth) -> str:
    params = {
        "parameters": "T2M,PRECTOTCORR,RH2M,WS2M",
        "community": "AG",
        "longitude": site["longitude"],
        "latitude": site["latitude"],
        "start": candidate.start_compact,
        "end": candidate.end_compact,
        "format": "JSON",
    }
    return "https://power.larc.nasa.gov/api/temporal/daily/point?" + urlencode(params)


def fetch_get_json(url: str, headers: Mapping[str, str], timeout_s: float) -> tuple[bytes, Dict[str, Any], str]:
    last_error: requests.RequestException | None = None
    for attempt in range(1, MAX_SOURCE_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=dict(headers), timeout=timeout_s)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Public source response must be a JSON object.")
            return response.content, payload, response.url
        except requests.RequestException as exc:
            last_error = exc
            if attempt != MAX_SOURCE_ATTEMPTS:
                time.sleep(attempt)
    assert last_error is not None
    raise last_error


def market_summary(
    payload: Mapping[str, Any], scenario: MarketScenario, source_state: str, source_district: str
) -> Dict[str, Any]:
    """Validate the exact source report title and aggregate only reported prices."""
    title = str(payload.get("title", ""))
    required_title_terms = (
        scenario.commodity_label.casefold(),
        source_state.casefold(),
        source_district.casefold(),
        calendar.month_name[scenario.month].casefold(),
        str(scenario.year),
    )
    if payload.get("success") is not True or not all(term in title.casefold() for term in required_title_terms):
        raise ValueError("Agmarknet report identity does not bind the expected crop, district, state, and month.")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Agmarknet report has no rows list.")
    prices = [
        numeric(row[scenario.price_key])
        for row in rows
        if isinstance(row, dict) and row.get(scenario.price_key) is not None
    ]
    if not prices:
        raise ValueError("Agmarknet report has no non-null price for this crop/district/month.")
    return {
        "market_source_price_key": scenario.price_key,
        "market_priced_market_count": len(prices),
        "market_price_mean_as_reported": f"{statistics.fmean(prices):.3f}",
        "market_price_min_as_reported": f"{min(prices):.3f}",
        "market_price_max_as_reported": f"{max(prices):.3f}",
        "market_price_unit_status": "as_reported_by_agmarknet_monthly_API_no_unit_inference",
    }


def fetch_sentinel(
    site: Mapping[str, str], candidate: CandidateMonth, timeout_s: float
) -> tuple[bytes, Dict[str, Any], Dict[str, Any], str]:
    """Return a quality-checked, same-month Sentinel metadata result."""
    payload = build_search_payload(float(site["longitude"]), float(site["latitude"]), candidate.window_utc)
    last_error: requests.RequestException | None = None
    for attempt in range(1, MAX_SOURCE_ATTEMPTS + 1):
        try:
            response = requests.post(STAC_SEARCH_URL, json=payload, headers=SENTINEL_HEADERS, timeout=timeout_s)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("features"), list):
                raise ValueError("Sentinel STAC response has no features list.")
            candidates = [
                feature for feature in result["features"]
                if isinstance(feature, dict) and is_quality_candidate(feature)
            ]
            if not candidates:
                raise ValueError(
                    f"No same-month Sentinel item meets cloud <= {MAX_CLOUD_COVER:g}% and nodata <= {MAX_NODATA_PERCENT:g}% gates."
                )
            selected = min(candidates, key=feature_sort_key)
            return response.content, payload, selected, response.url
        except requests.RequestException as exc:
            last_error = exc
            if attempt != MAX_SOURCE_ATTEMPTS:
                time.sleep(attempt)
    assert last_error is not None
    raise last_error


def static_inputs(
    site: Mapping[str, str],
    soil: Mapping[str, Mapping[str, Mapping[str, str]]],
    bundles: Mapping[str, Dict[str, str]],
    sources: Mapping[str, Dict[str, str]],
) -> tuple[Mapping[str, Dict[str, str]], Dict[str, str]]:
    """Validate the frozen static registry inputs before any network request."""
    if site.get("freeze_status") != "admitted":
        raise ValueError("A supplementary scenario can only use an admitted final site.")
    profile = soil.get(site["site_id"])
    if profile is None or set(profile) != set(SOIL_PROPERTIES):
        raise ValueError("Frozen SoilGrids profile is missing a required property.")
    if any(row.get("status") != SOIL_STATUS for row in profile.values()):
        raise ValueError("Frozen SoilGrids profile does not pass its static-value evidence gate.")
    return profile, management_bundle(site, bundles, sources)


def scenario_identifier(site: Mapping[str, str], candidate: CandidateMonth) -> str:
    return f"SUPPLEMENT_{site['site_id']}_{candidate.end_compact}"


def source_relative_path(source: str, identifier: str) -> Path:
    return Path("raw") / source / f"{identifier}.json"


def raw_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read_cached_json(path: Path) -> tuple[bytes, Dict[str, Any]]:
    """Load a prior all-gate-admitted raw source payload without re-querying it."""
    content = path.read_bytes()
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError(f"Cached source payload is not a JSON object: {path}")
    return content, payload


def has_complete_raw_cache(raw_root: Path, identifier: str) -> bool:
    """Return whether all three raw payloads from a prior admitted collection exist."""
    return all(
        (raw_root / source_relative_path(source, identifier)).is_file()
        for source in ("agmarknet", "nasa_power", "sentinel")
    )


def build_supplementary(
    site: Mapping[str, str],
    candidate: CandidateMonth,
    source_location: tuple[int, str, int, str],
    profile: Mapping[str, Dict[str, str]],
    bundle: Mapping[str, str],
    *,
    raw_root: Path,
    timeout_s: float,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Collect and validate one independent source-aligned historical context."""
    state_id, source_state, district_id, source_district = source_location
    scenario = market_scenario(site["crop"], candidate)
    market_url = build_market_url(scenario, state_id, district_id)
    weather_url = build_weather_url(site, candidate)
    identifier = scenario_identifier(site, candidate)
    raw_paths = {
        "market": source_relative_path("agmarknet", identifier),
        "weather": source_relative_path("nasa_power", identifier),
        "satellite": source_relative_path("sentinel", identifier),
    }
    cached = has_complete_raw_cache(raw_root, identifier)
    if cached:
        market_bytes, market_payload = read_cached_json(raw_root / raw_paths["market"])
        weather_bytes, weather_payload = read_cached_json(raw_root / raw_paths["weather"])
        satellite_bytes, satellite_result = read_cached_json(raw_root / raw_paths["satellite"])
        satellite_query = build_search_payload(
            float(site["longitude"]), float(site["latitude"]), candidate.window_utc
        )
        quality_items = [
            feature for feature in satellite_result.get("features", [])
            if isinstance(feature, dict) and is_quality_candidate(feature)
        ]
        if not quality_items:
            raise ValueError("Cached Sentinel result has no item meeting the declared quality gate.")
        satellite_item = min(quality_items, key=feature_sort_key)
        market_final_url = market_url
        weather_final_url = weather_url
        satellite_final_url = STAC_SEARCH_URL
    else:
        market_bytes, market_payload, market_final_url = fetch_get_json(market_url, AGMARKNET_HEADERS, timeout_s)
        weather_bytes, weather_payload, weather_final_url = fetch_get_json(weather_url, NASA_HEADERS, timeout_s)
        satellite_bytes, satellite_query, satellite_item, satellite_final_url = fetch_sentinel(site, candidate, timeout_s)
    market_values = market_summary(market_payload, scenario, source_state, source_district)
    weather_values = weather_features(weather_payload, calendar.monthrange(candidate.year, candidate.month)[1])
    satellite_properties = satellite_item.get("properties", {})
    if not isinstance(satellite_properties, dict):
        raise ValueError("Selected Sentinel item has no properties object.")
    cloud = satellite_properties.get("eo:cloud_cover")
    nodata = satellite_properties.get("s2:nodata_pixel_percentage")
    if cloud is None or nodata is None:
        raise ValueError("Selected Sentinel item is missing quality metadata.")

    for relative in raw_paths.values():
        (raw_root / relative).parent.mkdir(parents=True, exist_ok=True)
    if not cached:
        (raw_root / raw_paths["market"]).write_bytes(market_bytes)
        (raw_root / raw_paths["weather"]).write_bytes(weather_bytes)
        # Store the exact STAC response rather than only the selected item:
        # it retains the candidate set, query result, and selection audit trail.
        (raw_root / raw_paths["satellite"]).write_bytes(satellite_bytes)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest: Dict[str, Any] = {
        "scenario_id": identifier,
        "scenario_type": SCENARIO_TYPE,
        "scenario_status": READY_STATUS,
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"],
        "district": site["district"],
        "season": site["proposed_season"],
        "season_window": site["season_window"],
        "decision_date": candidate.decision_date,
        "decision_window_utc": candidate.window_utc,
        "geometry_scope": site["geometry_scope"],
        "longitude": site["longitude"],
        "latitude": site["latitude"],
        "weather_source_url": weather_final_url,
        "weather_registry_response_sha256": "",
        "weather_current_response_sha256": sha256(weather_bytes).hexdigest(),
        "weather_raw_path": str(raw_paths["weather"]),
        "market_source_url": market_final_url,
        "market_registry_payload_sha256": "",
        "market_current_payload_sha256": payload_hash(market_payload),
        "market_raw_path": str(raw_paths["market"]),
        "satellite_item_id": str(satellite_item.get("id", "")),
        "satellite_datetime_utc": str(satellite_properties.get("datetime", "")),
        "management_bundle_id": bundle["management_bundle_id"],
        "fertilizer_source_id": bundle["fertilizer_source_id"],
        "protection_source_id": bundle["protection_source_id"],
        "crop_stage_status": "not_observed_no_field_phenology_source",
        "disease_event_status": "not_observed_no_dated_site_event",
        "farm_fertilizer_status": "not_issued_regional_baseline_is_not_a_field_prescription",
        "crop_protection_status": "not_issued_no_dated_diagnosis_or_threshold_event",
        "generation_timestamp_utc": generated_at,
        "candidate_selection_rank": candidate.rank,
        "anchor_temporal_relation": anchor_temporal_relation(site, candidate),
        "candidate_search_upper_bound": candidate_search_upper_bound(site).isoformat(),
        "season_membership_status": SEASON_MEMBERSHIP_STATUS,
        "market_source_commodity_id": scenario.commodity_id,
        "market_source_commodity": scenario.commodity_label,
        "market_mapping_status": scenario.mapping_kind,
        "market_source_state": source_state,
        "market_source_district": source_district,
        "satellite_search_url": satellite_final_url,
        "satellite_search_payload_sha256": sha256(
            json.dumps(satellite_query, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "satellite_response_sha256": sha256(satellite_bytes).hexdigest(),
        "satellite_raw_path": str(raw_paths["satellite"]),
        "satellite_window_utc": candidate.window_utc,
        "soil_evidence_status": "frozen_static_profile_verified",
        "management_temporal_status": MANAGEMENT_TEMPORAL_STATUS,
    }
    features: Dict[str, Any] = {
        "scenario_id": identifier,
        **weather_values,
        **{f"soil_{property_id}_raw": profile[property_id]["raw_value"] for property_id in SOIL_PROPERTIES},
        "satellite_item_id": manifest["satellite_item_id"],
        "satellite_datetime_utc": manifest["satellite_datetime_utc"],
        "satellite_cloud_cover_percent": str(cloud),
        "satellite_nodata_percent": str(nodata),
        "satellite_gsd_m": str(satellite_properties.get("gsd", "")),
        **market_values,
    }
    evidence: Dict[str, Any] = {
        "scenario_id": identifier,
        "crop_stage_status": manifest["crop_stage_status"],
        "disease_event_status": manifest["disease_event_status"],
        "farm_fertilizer_status": manifest["farm_fertilizer_status"],
        "crop_protection_status": manifest["crop_protection_status"],
        "fertilizer_source_id": bundle["fertilizer_source_id"],
        "fertilizer_locator": bundle["fertilizer_locator"],
        "protection_source_id": bundle["protection_source_id"],
        "protection_locator": bundle["protection_locator"],
        "ppqs_source_ids": bundle["ppqs_source_id"],
        "management_conditions_and_exclusions": bundle["conditions_and_exclusions"],
        "evidence_interpretation": (
            "This independent public-data monthly context is source-aligned for weather, market, "
            "soil, and Sentinel metadata. It does not support a disease finding, a treatment, "
            "or a farm-specific fertilizer recommendation."
        ),
        "season_membership_status": SEASON_MEMBERSHIP_STATUS,
        "satellite_evidence_status": SATELLITE_STATUS,
        "management_temporal_status": MANAGEMENT_TEMPORAL_STATUS,
    }
    return manifest, features, evidence


def candidate_rejection(
    site: Mapping[str, str], candidate: CandidateMonth, gate: str, reason: BaseException,
    source_location: tuple[int, str, int, str] | None,
) -> Dict[str, Any]:
    scenario = market_scenario(site["crop"], candidate)
    market_url = ""
    if source_location is not None:
        market_url = build_market_url(scenario, source_location[0], source_location[2])
    return {
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": site["state"],
        "district": site["district"],
        "candidate_decision_date": candidate.decision_date,
        "candidate_selection_rank": candidate.rank,
        "failed_gate": gate,
        "market_source_url": market_url,
        "weather_source_url": build_weather_url(site, candidate),
        "satellite_search_url": STAC_SEARCH_URL,
        "reason": f"{type(reason).__name__}: {reason}",
    }


def classify_gate(error: BaseException) -> str:
    message = str(error).casefold()
    if "agmarknet" in message or "non-null price" in message or "market report" in message:
        return "historical_market"
    if "nasa" in message or "power" in message or "weather" in message or "fill value" in message:
        return "weather"
    if "sentinel" in message or "cloud" in message or "nodata" in message or "stac" in message:
        return "satellite"
    if "soilgrids" in message or "static" in message:
        return "soil"
    if "management" in message or "source snapshot" in message:
        return "management"
    if isinstance(error, requests.RequestException):
        return "public_source_request"
    return "validation"


def complete_site(
    site: Mapping[str, str], source_location: tuple[int, str, int, str],
    profile: Mapping[str, Dict[str, str]], bundle: Mapping[str, str], *, raw_root: Path,
    timeout_s: float, delay_s: float,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Collect the deterministic first nine all-gate-passing months for a site."""
    manifests: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    cached_candidates = [
        candidate for candidate in candidate_months(site)
        if has_complete_raw_cache(raw_root, scenario_identifier(site, candidate))
    ]
    for candidate in cached_candidates:
        try:
            manifest, feature, evidence_row = build_supplementary(
                site, candidate, source_location, profile, bundle, raw_root=raw_root, timeout_s=timeout_s,
            )
            manifests.append(manifest)
            features.append(feature)
            evidence.append(evidence_row)
        except (OSError, ValueError, TypeError, KeyError, requests.RequestException) as exc:
            rejected.append(candidate_rejection(site, candidate, classify_gate(exc), exc, source_location))
    if len(manifests) >= TARGET_SUPPLEMENTARY_PER_SITE:
        selected = sorted(
            zip(manifests, features, evidence),
            key=lambda rows: int(rows[0]["candidate_selection_rank"]),
        )[:TARGET_SUPPLEMENTARY_PER_SITE]
        print(f"  {site['site_id']}: reused {len(selected)} validated raw source bundles")
        return (
            [row[0] for row in selected], [row[1] for row in selected], [row[2] for row in selected], rejected,
        )
    cached_dates = {candidate.decision_date for candidate in cached_candidates}
    for candidate in candidate_months(site):
        if candidate.decision_date in cached_dates:
            continue
        try:
            manifest, feature, evidence_row = build_supplementary(
                site, candidate, source_location, profile, bundle, raw_root=raw_root, timeout_s=timeout_s,
            )
            manifests.append(manifest)
            features.append(feature)
            evidence.append(evidence_row)
            print(
                f"  {site['site_id']} {candidate.decision_date}: admitted "
                f"({len(manifests)}/{TARGET_SUPPLEMENTARY_PER_SITE}, candidate rank {candidate.rank})"
            )
        except (OSError, ValueError, TypeError, KeyError, requests.RequestException) as exc:
            gate = classify_gate(exc)
            rejected.append(candidate_rejection(site, candidate, gate, exc, source_location))
            print(f"  {site['site_id']} {candidate.decision_date}: rejected [{gate}]")
        if len(manifests) == TARGET_SUPPLEMENTARY_PER_SITE:
            return manifests, features, evidence, rejected
        time.sleep(delay_s)
    raise ValueError(
        f"{site['site_id']} supplied only {len(manifests)}/{TARGET_SUPPLEMENTARY_PER_SITE} "
        f"all-gate-passing candidate months since {EARLIEST_CANDIDATE_YEAR}."
    )


def consolidate(
    out_dir: Path,
    supplementary_manifest: Sequence[Mapping[str, Any]],
    supplementary_features: Sequence[Mapping[str, Any]],
    supplementary_evidence: Sequence[Mapping[str, Any]],
) -> None:
    """Create stable 300-row views without mutating the source-specific files."""
    anchor_manifest = read_csv(out_dir / "manifests" / "anchor_scenario_manifest.csv")
    anchor_features = read_csv(out_dir / "processed" / "anchor_scenario_features.csv")
    anchor_evidence = read_csv(out_dir / "evidence" / "anchor_scenario_evidence_status.csv")
    expected_anchor = 30
    if not (len(anchor_manifest) == len(anchor_features) == len(anchor_evidence) == expected_anchor):
        raise ValueError("Expected exactly 30 existing validated anchor rows before consolidation.")
    write_csv(
        out_dir / "manifests" / "scenario_manifest.csv", SUPPLEMENTARY_MANIFEST_FIELDS,
        [*anchor_manifest, *supplementary_manifest],
    )
    write_csv(
        out_dir / "processed" / "scenario_features.csv", FEATURE_FIELDS,
        [*anchor_features, *supplementary_features],
    )
    write_csv(
        out_dir / "evidence" / "scenario_evidence_status.csv", SUPPLEMENTARY_EVIDENCE_FIELDS,
        [*anchor_evidence, *supplementary_evidence],
    )


def validate_outputs(
    out_dir: Path,
    sites: Sequence[Mapping[str, str]],
    manifests: Sequence[Mapping[str, Any]],
    features: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
) -> None:
    """Fail closed if the 270 records or their source-abstention constraints drift."""
    expected = len(sites) * TARGET_SUPPLEMENTARY_PER_SITE
    if not (len(manifests) == len(features) == len(evidence) == expected):
        raise ValueError(f"Expected {expected} supplementary rows in each output artifact.")
    by_id = {row["scenario_id"]: row for row in manifests}
    if len(by_id) != expected:
        raise ValueError("Supplementary scenario IDs are not unique.")
    site_by_id = {site["site_id"]: site for site in sites}
    per_site: Dict[str, List[Mapping[str, Any]]] = {}
    for row in manifests:
        site = site_by_id.get(str(row["site_id"]))
        if site is None:
            raise ValueError("Supplementary manifest contains a site outside final_study_sites.csv.")
        if row["scenario_type"] != SCENARIO_TYPE or row["scenario_status"] != READY_STATUS:
            raise ValueError("Supplementary scenario has an invalid type or readiness status.")
        chosen = date.fromisoformat(str(row["decision_date"]))
        anchor = date.fromisoformat(site["fixed_decision_date"])
        upper_bound = candidate_search_upper_bound(site)
        if chosen == anchor or chosen > upper_bound:
            raise ValueError("Supplementary decision date violates its fixed source search boundary.")
        expected_relation = (
            "pre_anchor_historical_context"
            if chosen < anchor
            else "post_anchor_same_declared_season_historical_context"
        )
        if row["anchor_temporal_relation"] != expected_relation:
            raise ValueError("Supplementary anchor temporal relation is not explicit or is incorrect.")
        if row["candidate_search_upper_bound"] != upper_bound.isoformat():
            raise ValueError("Supplementary source cutoff does not match the fixed selection policy.")
        if chosen.month not in parse_season_window(site["season_window"]):
            raise ValueError("Supplementary decision date falls outside its final-registry season window.")
        if row["season_membership_status"] != SEASON_MEMBERSHIP_STATUS:
            raise ValueError("Supplementary season membership is not explicit.")
        for status_field, expected_status in (
            ("crop_stage_status", "not_observed_no_field_phenology_source"),
            ("disease_event_status", "not_observed_no_dated_site_event"),
            ("farm_fertilizer_status", "not_issued_regional_baseline_is_not_a_field_prescription"),
            ("crop_protection_status", "not_issued_no_dated_diagnosis_or_threshold_event"),
        ):
            if row[status_field] != expected_status:
                raise ValueError(f"Supplementary row violates mandatory abstention: {status_field}.")
        for relative_field, checksum_field, canonical in (
            ("weather_raw_path", "weather_current_response_sha256", False),
            ("market_raw_path", "market_current_payload_sha256", True),
            ("satellite_raw_path", "satellite_response_sha256", False),
        ):
            raw_path = out_dir / str(row[relative_field])
            if not raw_path.is_file():
                raise ValueError(f"Missing raw source payload: {raw_path}")
            if canonical:
                raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
                observed = payload_hash(raw_payload)
            else:
                observed = raw_sha256(raw_path)
            if observed != row[checksum_field]:
                raise ValueError(f"Raw source checksum mismatch for {row['scenario_id']} ({relative_field}).")
        satellite_payload = json.loads((out_dir / str(row["satellite_raw_path"])).read_text(encoding="utf-8"))
        item_ids = {
            str(feature.get("id", ""))
            for feature in satellite_payload.get("features", [])
            if isinstance(feature, dict) and is_quality_candidate(feature)
        }
        if row["satellite_item_id"] not in item_ids:
            raise ValueError("Selected Sentinel item is absent from or fails the raw quality-gated response.")
        per_site.setdefault(str(row["site_id"]), []).append(row)
    if set(per_site) != set(site_by_id) or any(len(rows) != TARGET_SUPPLEMENTARY_PER_SITE for rows in per_site.values()):
        raise ValueError("Each final site must have exactly nine supplementary contexts.")
    feature_ids = {row["scenario_id"] for row in features}
    evidence_ids = {row["scenario_id"] for row in evidence}
    if feature_ids != set(by_id) or evidence_ids != set(by_id):
        raise ValueError("Supplementary manifests, features, and evidence files do not have the same scenario IDs.")


def main() -> None:
    registry = PROJECT_ROOT / "data" / "registry"
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    parser = argparse.ArgumentParser(description="Generate 270 source-gated supplementary historical contexts.")
    parser.add_argument("--sites", type=Path, default=registry / "final_study_sites.csv")
    parser.add_argument("--soil", type=Path, default=registry / "preflight_soilgrids_wcs_profiles.csv")
    parser.add_argument("--bundles", type=Path, default=registry / "preflight_management_bundle_catalog.csv")
    parser.add_argument("--sources", type=Path, default=registry / "regional_management_source_snapshot.csv")
    parser.add_argument("--out-dir", type=Path, default=scenarios)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--delay-s", type=float, default=0.25)
    parser.add_argument("--site", action="append", help="Generate only an exact final site ID (for a controlled preflight).")
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.delay_s < 0:
        raise SystemExit("--timeout-s must be positive and --delay-s must be non-negative.")

    all_sites = read_csv(args.sites)
    selected_ids = set(args.site or [])
    sites = [site for site in all_sites if not selected_ids or site["site_id"] in selected_ids]
    missing = selected_ids - {site["site_id"] for site in sites}
    if missing:
        raise SystemExit(f"Unknown final site IDs: {', '.join(sorted(missing))}")
    if not sites:
        raise SystemExit("No final sites selected.")
    if args.site and len(sites) != len(all_sites):
        print("Controlled preflight mode: consolidated 300-row files will not be written.")

    soil = index_soil(read_csv(args.soil))
    bundles = {row["management_bundle_id"]: row for row in read_csv(args.bundles)}
    sources = {row["source_document_id"]: row for row in read_csv(args.sources)}
    states = fetch_state_index(args.timeout_s)

    manifests: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []
    rejections: List[Dict[str, Any]] = []
    for index, site in enumerate(sites, start=1):
        print(f"[{index}/{len(sites)}] {site['site_id']}")
        profile, bundle = static_inputs(site, soil, bundles, sources)
        location = resolve_location(states, site["state"], site["district"])
        site_manifest, site_features, site_evidence, site_rejections = complete_site(
            site, location, profile, bundle, raw_root=args.out_dir, timeout_s=args.timeout_s, delay_s=args.delay_s,
        )
        manifests.extend(site_manifest)
        features.extend(site_features)
        evidence_rows.extend(site_evidence)
        rejections.extend(site_rejections)

    validate_outputs(args.out_dir, sites, manifests, features, evidence_rows)
    write_csv(args.out_dir / "manifests" / "supplementary_scenario_manifest.csv", SUPPLEMENTARY_MANIFEST_FIELDS, manifests)
    write_csv(args.out_dir / "processed" / "supplementary_scenario_features.csv", FEATURE_FIELDS, features)
    write_csv(args.out_dir / "evidence" / "supplementary_scenario_evidence_status.csv", SUPPLEMENTARY_EVIDENCE_FIELDS, evidence_rows)
    write_csv(args.out_dir / "manifests" / "supplementary_scenario_candidate_rejections.csv", CANDIDATE_REJECTION_FIELDS, rejections)
    if not args.site or len(sites) == len(all_sites):
        consolidate(args.out_dir, manifests, features, evidence_rows)
        total = len(manifests) + 30
        print(f"Generated {len(manifests)} source-gated supplementary scenarios; consolidated total: {total}.")
    else:
        print(f"Generated {len(manifests)} source-gated preflight supplementary scenarios for {len(sites)} site(s).")


if __name__ == "__main__":
    main()
