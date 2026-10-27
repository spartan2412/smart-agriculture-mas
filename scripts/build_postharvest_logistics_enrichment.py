"""Build the fourth enrichment: source-scoped post-harvest logistics context.

This builder deliberately keeps two different evidence clocks separate:

* crop-handling operations are source-quoted technical references, always
  conditional on a harvested lot and the source's stated maturity/moisture/
  quality condition; and
* NHB and WDRA infrastructure records are a collection-date directory, not
  evidence that a facility had capacity, accepted a commodity, or was reachable
  on a historical scenario date.

The output is therefore useful for a regional post-harvest planning agent while
remaining unsuitable for booking, dispatch, sell/hold, or farm-specific action.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import http.cookiejar
import io
import json
import math
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
RAW = ENRICHED / "raw" / "postharvest_logistics"
UTC_NOW = lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()

NHB_GIS_URL = "https://nhb.gov.in/Handlers/GeoIndiaHandlerGis.ashx"
NHB_COMPONENTS_URL = "https://nhb.gov.in/Handlers/GeoIndiaHandler.ashx"
NHB_REPORT_URL = "https://nhb.gov.in/IcapMap/ICAPMap_rpt.aspx"
WDRA_REGISTRY_URL = "https://wdra.gov.in/registered-wh-public"
MOFPI_COLD_CHAIN_URL = "https://mofpi.gov.in/en/Schemes/about-cold-chain"
TNAU_TOMATO_URL = "https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html"
OSRM_ROUTE_BASE_URL = "https://router.project-osrm.org/route/v1/driving"

STATE_CODES = {
    "Madhya Pradesh": "23",
    "Maharashtra": "27",
    "Punjab": "3",
    "Rajasthan": "8",
    "Tamil Nadu": "33",
}
STATE_ALIASES = {"Maharastra": "Maharashtra"}

SOURCE_FIELDS = [
    "source_document_id", "source_title", "provider", "source_url", "source_kind",
    "raw_path", "raw_sha256", "retrieved_at_utc", "temporal_interpretation", "allowed_use",
]
PROFILE_FIELDS = [
    "profile_id", "crop", "commodity_class", "profile_title", "operation_count", "source_document_ids",
    "profile_scope", "farmer_output_status", "not_supported", "profile_sha256",
]
OPERATION_FIELDS = [
    "operation_id", "profile_id", "crop", "operation_lane", "display_order", "operation_text",
    "method_or_parameter", "conditions_text", "missing_observation", "actionability_status",
    "source_document_id", "source_title", "source_provider", "source_url", "source_raw_path",
    "source_raw_sha256", "source_location", "source_quote", "temporal_interpretation", "operation_sha256",
]
FACILITY_FIELDS = [
    "facility_id", "project_name", "state", "district", "latitude", "longitude", "source_document_id",
    "source_url", "source_raw_path", "source_raw_sha256", "retrieved_at_utc", "record_semantics",
    "not_supported", "facility_sha256",
]
WAREHOUSE_FIELDS = [
    "warehouse_id", "warehouse_manager", "warehouse_name", "wdra_warehouse_id", "address", "district",
    "state", "capacity_mt", "registration_date", "registration_valid_upto", "contact_number",
    "registry_status", "source_document_id", "source_url", "source_raw_path", "source_raw_sha256",
    "retrieved_at_utc", "record_semantics", "not_supported", "warehouse_sha256",
]
INFRASTRUCTURE_FIELDS = [
    "state", "component", "component_code", "project_count", "reported_capacity", "reported_capacity_unit",
    "source_document_id", "source_url", "source_raw_path", "source_raw_sha256", "retrieved_at_utc",
    "record_semantics", "not_supported", "infrastructure_sha256",
]
SITE_CONTEXT_FIELDS = [
    "site_context_id", "site_id", "crop", "state", "district", "commodity_class", "context_kind",
    "candidate_rank", "candidate_id", "candidate_name", "candidate_district", "candidate_state",
    "candidate_capacity_mt", "candidate_registry_status", "geodesic_km", "source_document_id",
    "source_url", "source_raw_sha256", "temporal_interpretation", "allowed_use", "not_supported",
    "site_context_sha256",
]
ROUTE_FIELDS = [
    "route_context_id", "site_id", "crop", "state", "district", "candidate_id", "candidate_name",
    "source_document_id", "route_request_url", "raw_path", "raw_sha256", "road_distance_km",
    "road_duration_minutes", "retrieved_at_utc", "record_semantics", "not_supported", "route_sha256",
]
ROUTE_MANIFEST_FIELDS = ["route_context_id", "route_request_url", "raw_path", "raw_sha256", "retrieved_at_utc"]
SUMMARY_FIELDS = [
    "site_id", "crop", "state", "district", "commodity_class", "profile_id", "handling_operation_count",
    "facility_candidate_count", "warehouse_candidate_count", "static_road_route_count", "infrastructure_context_status", "summary_text",
    "temporal_interpretation", "allowed_use", "not_supported", "site_summary_sha256",
]
SCENARIO_ITEM_FIELDS = [
    "plan_item_id", "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date",
    "profile_id", "operation_id", "display_order", "plan_lane", "farmer_visible_label", "operation_text",
    "method_or_parameter", "conditions_text", "missing_observation", "item_status", "actionability_status",
    "source_document_id", "source_title", "source_url", "source_raw_sha256", "source_location", "source_quote",
    "temporal_interpretation", "allowed_use", "not_supported", "plan_item_sha256",
]
SCENARIO_CONTEXT_FIELDS = [
    "scenario_id", "site_id", "crop", "state", "district", "season", "decision_date", "profile_id",
    "postharvest_plan_item_count", "facility_candidate_count", "warehouse_candidate_count", "static_road_route_count",
    "context_status", "temporal_interpretation", "allowed_use", "not_supported", "context_sha256",
]
RAG_PASSAGE_FIELDS = [
    "passage_id", "source_document_id", "crop", "title", "provider", "source_url", "source_raw_sha256",
    "source_location", "text", "allowed_use", "not_supported", "passage_sha256",
]
RAG_SCOPE_FIELDS = [
    "scenario_id", "passage_id", "crop_scope_status", "allowed_use", "not_supported", "scope_sha256",
]
PROVENANCE_FIELDS = ["generated_at_utc", "artifact_role", "input_path", "input_sha256", "input_row_count", "notes"]


# These are source quotations/transcriptions, not generated agronomy.  The
# companion conditions state only the observation that would be required before
# someone could act on a specific lot.
OPERATION_SPECS = [
    {
        "operation_id": "POSTHARVEST_RICE_HARVEST_MATURITY", "crop": "rice", "lane": "harvest_readiness",
        "order": 1, "text": "Harvest at proper maturity and variety-wise; avoid night harvesting.", "method": "",
        "conditions": "Use only when the rice crop's proper variety-specific maturity is actually observed.",
        "missing": "actual_crop_maturity_and_harvest_readiness_not_observed", "source": "PAU_KHARIF_2026",
        "location": "pdf_page_9", "quote": "Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.",
    },
    {
        "operation_id": "POSTHARVEST_RICE_DRY_AND_STORE", "crop": "rice", "lane": "dry_storage",
        "order": 2, "text": "Dry the harvested produce well before storage; keep produce intended for storage in appropriate bins.",
        "method": "The cited Punjab package states an optimum paddy storage moisture content of 12%.",
        "conditions": "Only after harvest and a lot-specific moisture/quality check; this does not establish the actual lot moisture.",
        "missing": "harvested_lot_moisture_and_storage_condition_not_observed", "source": "PAU_KHARIF_2026",
        "location": "pdf_page_20", "quote": "Dry the produce well and store separately in disinfested bins. The produce kept for home use should be dried thoroughly in the sun for about a week and stored in bins or kept in a heap inside the room. The optimum moisture content for storage is 12 per cent.",
    },
    {
        "operation_id": "POSTHARVEST_WHEAT_HARVEST_AND_THRESH", "crop": "wheat", "lane": "harvest_readiness",
        "order": 1, "text": "Harvest and thresh wheat as soon as it is fully ripe to avoid shattering losses.", "method": "",
        "conditions": "Only when full wheat maturity is actually observed.", "missing": "actual_crop_maturity_not_observed",
        "source": "PAU_RABI_2025_26", "location": "pdf_page_25",
        "quote": "Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering. Delayed harvesting results in high grain losses.",
    },
    {
        "operation_id": "POSTHARVEST_WHEAT_DRY_BEFORE_STORAGE", "crop": "wheat", "lane": "dry_storage",
        "order": 2, "text": "Dry grain before storage when its moisture exceeds the cited threshold.",
        "method": "The cited Punjab package gives a 10% grain-moisture threshold.",
        "conditions": "Only after a lot-specific moisture measurement; the benchmark does not contain one.",
        "missing": "harvested_lot_moisture_not_observed", "source": "PAU_RABI_2025_26", "location": "pdf_page_25",
        "quote": "In case the grain contains more than 10 per cent moisture, it should be dried before storing, otherwise it would be spoiled by moulds and excessive heat that develops during storage.",
    },
    {
        "operation_id": "POSTHARVEST_MAIZE_HARVEST_AND_SHELL", "crop": "maize", "lane": "harvest_readiness",
        "order": 1, "text": "Harvest maize when the husk cover has dried and turned brown; shell within the cited moisture range.",
        "method": "The cited ICAR reference gives a 15–20% shelling moisture range.",
        "conditions": "Only after observing husk condition and measuring grain moisture; neither is present in the scenario.",
        "missing": "actual_husk_condition_and_harvested_lot_moisture_not_observed", "source": "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "location": "pdf_page_151", "quote": "Maize is ready for harvesting even when the stacks and leaves are somewhat green, but the husk cover has dried and turned brown. Shell Maize when the moisture content ranges between 15-20%.",
    },
    {
        "operation_id": "POSTHARVEST_MAIZE_DRY_EARS", "crop": "maize", "lane": "dry_storage",
        "order": 2, "text": "Dry maize ears after harvest before the next handling step.",
        "method": "The cited ICAR reference says ears should preferably be dried for 3–4 days after harvest.",
        "conditions": "Only after actual harvest; local drying conditions and lot moisture remain unobserved.",
        "missing": "actual_harvest_status_lot_moisture_and_drying_conditions_not_observed", "source": "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "location": "pdf_page_151", "quote": "The Maize ears should preferably be dried for 3-4 days after harvesting to improve grain recoveries and reduce breakage losses.",
    },
    {
        "operation_id": "POSTHARVEST_CHICKPEA_HARVEST_DRY_HARD_PODS", "crop": "chickpea", "lane": "harvest_readiness",
        "order": 1, "text": "Harvest and thresh chickpea only after pods are hard; do not harvest while the crop is wet.", "method": "",
        "conditions": "Only when hard pods and crop dryness are actually observed.",
        "missing": "actual_pod_hardness_and_crop_dryness_not_observed", "source": "MPKV_KRISHI_DARSHANI_2023",
        "location": "pdf_page_90_visual_operation_transcription",
        "quote": "हरभरा पीक ११० ते १२० दिवसांमध्ये तयार होते. पीक ओलसर असताना काढणी करू नये. घाटे कडक झाल्यानंतर मग हरभऱ्याची काढणी करून मळणी करावी.",
    },
    {
        "operation_id": "POSTHARVEST_SOYBEAN_HARVEST_YELLOW_PODS", "crop": "soybean", "lane": "harvest_readiness",
        "order": 1, "text": "Harvest soybean when 90% of pods have changed colour to yellow.", "method": "",
        "conditions": "Only when the 90% yellow-pod maturity condition is actually observed.",
        "missing": "actual_pod_maturity_not_observed", "source": "ICAR_IISR_SOYBEAN_BULLETIN_2023", "location": "pdf_page_33",
        "quote": "When 90% of the pods changes its color to yellow, it is the right indication to go for harvesting.",
    },
    {
        "operation_id": "POSTHARVEST_SOYBEAN_THRESH_AT_QUOTED_SPEED", "crop": "soybean", "lane": "threshing",
        "order": 2, "text": "Use the cited threshing speed to reduce mechanical damage when threshing soybean.",
        "method": "350–400 rpm.", "conditions": "Only after harvest and when the actual threshing system is known.",
        "missing": "actual_harvest_status_and_thresher_configuration_not_observed", "source": "ICAR_IISR_SOYBEAN_BULLETIN_2023", "location": "pdf_page_33",
        "quote": "To maintain viability of seed and to avoid loss/mechanical damage, threshing should be done at 350-400 rpm.",
    },
    {
        "operation_id": "POSTHARVEST_SOYBEAN_DRY_AND_PROTECT_FROM_RAIN", "crop": "soybean", "lane": "dry_storage",
        "order": 3, "text": "Sun-dry harvested soybean before threshing; if threshing is delayed, protect it from rain.", "method": "",
        "conditions": "Only after actual harvest and with documented drying/storage conditions.",
        "missing": "actual_harvest_status_drying_condition_and_storage_condition_not_observed", "source": "ICAR_IISR_WEEKLY_SOYBEAN_20230925", "location": "pdf_page_1",
        "quote": "The harvested crop must be threshed after sun drying. If the threshing is to be done later, it should be stored at safe place protecting from rains.",
    },
    {
        "operation_id": "POSTHARVEST_TOMATO_SELECT_MATURITY_FOR_MARKET", "crop": "tomato", "lane": "harvest_readiness",
        "order": 1, "text": "Match tomato harvest maturity to the intended market and transport distance.",
        "method": "The cited TNAU source distinguishes firm mature-green fruit for distant shipping from turning-pink/half-ripe fruit for fresh consumption.",
        "conditions": "Only after observing fruit maturity and knowing the intended market; neither is in the scenario.",
        "missing": "actual_fruit_maturity_and_intended_market_not_observed", "source": "TNAU_TOMATO_POSTHARVEST_HARVESTING",
        "location": "html_paragraphs_171_to_173", "quote": "Generally, firm mature green fruits are best suited for shipping or distant marketing. For fresh consumption, tomatoes are harvested at the turning pink or half ripe stage.",
    },
    {
        "operation_id": "POSTHARVEST_TOMATO_GRADE_SOUND_FRUIT", "crop": "tomato", "lane": "grading",
        "order": 2, "text": "Remove damaged, rotten, and cracked tomatoes before grading sound fruit.", "method": "",
        "conditions": "Only after a harvested lot is available for physical inspection.",
        "missing": "actual_harvested_lot_quality_not_observed", "source": "TNAU_TOMATO_POSTHARVEST_HARVESTING",
        "location": "html_paragraph_176", "quote": "Damaged, rotten and cracked fruit are removed. Healthy, attractive, clean and bright fruits are preferred.",
    },
    {
        "operation_id": "POSTHARVEST_TOMATO_PACK_WITH_PROTECTION_AND_AIRFLOW", "crop": "tomato", "lane": "packing_transport",
        "order": 3, "text": "Use packing that protects tomatoes from crushing and permits air circulation.",
        "method": "The cited source describes plastic crates for local markets and rigid packing that protects fruit while allowing circulation.",
        "conditions": "Only after lot grade, destination, pack format, and transport arrangement are known.",
        "missing": "actual_lot_grade_destination_packaging_and_transport_availability_not_observed", "source": "TNAU_TOMATO_POSTHARVEST_HARVESTING",
        "location": "html_paragraph_178", "quote": "Plastic crates are more convenient for handling since they can be stacked one above the other. The contoured rim keeps the product safe and allows sufficient air circulation. The packing should be rigid enough to protect the fruits from being crushed.",
    },
    {
        "operation_id": "POSTHARVEST_TOMATO_STORAGE_TEMPERATURE_CONTEXT", "crop": "tomato", "lane": "cold_chain",
        "order": 4, "text": "Use the cited storage-temperature guidance only after maturity and cold-chain feasibility are known.",
        "method": "The cited TNAU source gives 12–15°C as an ideal storage range and 13°C with 90–95% relative humidity to slow ripening.",
        "conditions": "Only for a harvested lot with observed maturity and verified facility temperature/humidity capability.",
        "missing": "actual_fruit_maturity_and_verified_cold_chain_capability_not_observed", "source": "TNAU_TOMATO_POSTHARVEST_HARVESTING",
        "location": "html_paragraph_180", "quote": "Temperature between 12–15 oC is ideal for storage. A temperature of 13 oC and 90–95% relative humidity is recommended to slow down ripening.",
    },
]

SOURCE_SPECS = {
    "PAU_KHARIF_2026": {
        "title": "Package of Practices for Crops of Punjab — Kharif 2026", "provider": "Punjab Agricultural University",
        "url": "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf", "kind": "crop_handling_reference",
        "raw": ENRICHED / "raw" / "official_rag_sources" / "PAU_KHARIF_2026.pdf",
        "temporal": "Punjab crop technical reference; not a lot-level observation.",
    },
    "PAU_RABI_2025_26": {
        "title": "Package of Practices for Crops of Punjab — Rabi 2025–26", "provider": "Punjab Agricultural University",
        "url": "https://pau.edu/content/ccil/pf/pp_rabi.pdf", "kind": "crop_handling_reference",
        "raw": ENRICHED / "raw" / "official_rag_sources" / "PAU_RABI_2025_26.pdf",
        "temporal": "Punjab crop technical reference; not a lot-level observation.",
    },
    "ICAR_RABI_STATE_ADVISORIES_2021_22": {
        "title": "ICAR Rabi Agro-Advisory for Farmers 2021–22", "provider": "Indian Council of Agricultural Research",
        "url": "https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf", "kind": "crop_handling_reference",
        "raw": ENRICHED / "raw" / "official_rag_sources" / "ICAR_RABI_STATE_ADVISORIES_2021_22.pdf",
        "temporal": "National crop technical reference; not a district-week advisory or lot-level observation.",
    },
    "MPKV_KRISHI_DARSHANI_2023": {
        "title": "Krishi Darshani 2023", "provider": "Mahatma Phule Krishi Vidyapeeth",
        "url": "https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf", "kind": "crop_handling_reference",
        "raw": ENRICHED / "raw" / "mpkv_krishi_darshani_sources" / "MPKV_KRISHI_DARSHANI_2023.pdf",
        "temporal": "Maharashtra crop technical reference; not a lot-level observation.",
    },
    "ICAR_IISR_SOYBEAN_BULLETIN_2023": {
        "title": "Improved Technologies and Recommendations for Maximizing Soybean Productivity", "provider": "ICAR–Indian Institute of Soybean Research",
        "url": "https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf", "kind": "crop_handling_reference",
        "raw": ENRICHED / "raw" / "official_rag_sources" / "ICAR_IISR_SOYBEAN_BULLETIN_2023.pdf",
        "temporal": "Soybean technical reference; not a lot-level observation.",
    },
    "ICAR_IISR_WEEKLY_SOYBEAN_20230925": {
        "title": "ICAR-IISR weekly soybean advisory, 25 Sep–01 Oct 2023", "provider": "ICAR–Indian Institute of Soybean Research",
        "url": "https://icar-nsri.res.in/pdfdoc/Advisory2023/25%20Sept-1Oct%202023.pdf", "kind": "crop_handling_reference",
        "raw": ENRICHED / "raw" / "expanded_official_rag_sources" / "ICAR_IISR_WEEKLY_SOYBEAN_20230925.pdf",
        "temporal": "Dated soybean advisory; the handling quotation remains conditional on actual harvest and lot conditions.",
    },
    "TNAU_TOMATO_POSTHARVEST_HARVESTING": {
        "title": "TNAU tomato harvesting and post-harvest techniques", "provider": "Tamil Nadu Agricultural University",
        "url": TNAU_TOMATO_URL, "kind": "crop_handling_reference", "raw": RAW / "tnau_tomato_harvest.html",
        "temporal": "Tamil Nadu tomato technical reference; not a lot-level observation.",
    },
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    result = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def row_hash(row: Mapping[str, str], field: str) -> str:
    payload = {key: value for key, value in row.items() if key != field}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def raw_relative(path: Path) -> str:
    return str(path.relative_to(ENRICHED))


def fetch(url: str, output: Path, *, data: bytes | None = None, headers: Mapping[str, str] | None = None, opener=None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    request_headers = {"User-Agent": "SmartAgricultureMAS-research/1.0 (+public-source-audit)"}
    if headers:
        request_headers.update(headers)
    request = Request(url, data=data, headers=request_headers)
    response = (opener.open(request, timeout=60) if opener else urlopen(request, timeout=60))
    with response, output.open("wb") as handle:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            handle.write(block)


def ensure_raw_sources(refresh: bool) -> Dict[str, Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    network_sources = {
        "TNAU_TOMATO_POSTHARVEST_HARVESTING": (TNAU_TOMATO_URL, SOURCE_SPECS["TNAU_TOMATO_POSTHARVEST_HARVESTING"]["raw"]),
        "MOFPI_COLD_CHAIN_COMPONENTS": (MOFPI_COLD_CHAIN_URL, RAW / "mofpi_cold_chain_components.html"),
        "NHB_ICAP_GEO_FACILITIES": (NHB_GIS_URL, RAW / "nhb_icap_geocoded_projects.csv"),
    }
    for source_id, (url, output) in network_sources.items():
        if refresh or not output.exists():
            fetch(url, output)
    component_path = RAW / "nhb_icap_state_components.json"
    if refresh or not component_path.exists():
        fetch(
            NHB_COMPONENTS_URL, component_path,
            data=urlencode({"CommandName": "GetTotalComponentsData", "StateCode": "All"}).encode("utf-8"),
            headers={"Referer": NHB_REPORT_URL, "X-Requested-With": "XMLHttpRequest"},
        )

    for state, code in STATE_CODES.items():
        warehouse_path = RAW / f"wdra_registered_warehouses_{state.lower().replace(' ', '_')}.html"
        if refresh or not warehouse_path.exists():
            retrieve_wdra_state(state, code, warehouse_path)

    raw_paths = {source_id: Path(spec["raw"]) for source_id, spec in SOURCE_SPECS.items()}
    raw_paths.update({
        "MOFPI_COLD_CHAIN_COMPONENTS": RAW / "mofpi_cold_chain_components.html",
        "NHB_ICAP_GEO_FACILITIES": RAW / "nhb_icap_geocoded_projects.csv",
        "NHB_ICAP_STATE_COMPONENTS": component_path,
    })
    raw_paths.update({
        f"WDRA_REGISTERED_WAREHOUSES_{state.upper().replace(' ', '_')}": RAW / f"wdra_registered_warehouses_{state.lower().replace(' ', '_')}.html"
        for state in STATE_CODES
    })
    missing = [f"{source_id}: {path}" for source_id, path in raw_paths.items() if not path.is_file()]
    if missing:
        raise SystemExit("Required source snapshots are missing: " + "; ".join(missing))
    return raw_paths


def retrieve_wdra_state(state: str, code: str, output: Path) -> None:
    """Fetch WDRA's public interactive registry with its session-bound form token."""
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    landing = RAW / f"wdra_landing_{state.lower().replace(' ', '_')}.html"
    fetch(WDRA_REGISTRY_URL, landing, opener=opener)
    page = landing.read_text(encoding="utf-8", errors="replace")
    action_match = re.search(r'<form action="([^"]*processWarehouseListReport[^"]*)"', page, re.IGNORECASE)
    date_match = re.search(
        r'name="_in_gov_wdra_warehouse_publiclist_portlet_WarehousePubliclistPortlet_INSTANCE_faio_formDate"[^>]*value="([^"]*)"',
        page,
        re.IGNORECASE,
    )
    if not action_match or not date_match:
        raise SystemExit(f"WDRA form tokens were not found for {state}; public registry format changed.")
    action = unescape(action_match.group(1))
    form_prefix = "_in_gov_wdra_warehouse_publiclist_portlet_WarehousePubliclistPortlet_INSTANCE_faio_"
    payload = urlencode({
        f"{form_prefix}formDate": date_match.group(1),
        f"{form_prefix}selectStateName": code,
        f"{form_prefix}GoButton": "Submit",
    }).encode("utf-8")
    fetch(action, output, data=payload, opener=opener)
    if "resultTableId" not in output.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit(f"WDRA registry did not return a warehouse table for {state}.")


def normal_state(value: str) -> str:
    return STATE_ALIASES.get(value.strip(), value.strip())


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]*>", " ", value)
    return " ".join(unescape(value).replace("\xa0", " ").split())


def parse_wdra(path: Path, state: str, source_id: str) -> List[Dict[str, str]]:
    html = path.read_text(encoding="utf-8", errors="replace")
    table = re.search(r'<table[^>]+id="resultTableId"[^>]*>(.*?)</table>', html, re.IGNORECASE | re.DOTALL)
    if not table:
        raise SystemExit(f"WDRA response has no registry table: {path}")
    rows: List[Dict[str, str]] = []
    for index, fragment in enumerate(re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(1), re.IGNORECASE | re.DOTALL), start=1):
        cells = [clean_html(value) for value in re.findall(r"<td[^>]*>(.*?)</td>", fragment, re.IGNORECASE | re.DOTALL)]
        # WDRA currently emits an empty twelfth display column after the 11
        # published registry fields.  Keep the documented fields and ignore
        # that non-data column without treating it as a warehouse attribute.
        if len(cells) < 11:
            continue
        manager, name, wdra_id, address, district, row_state, capacity, registered, valid_until, phone, status = cells[:11]
        row = {
            "warehouse_id": f"WDRA_{normal_state(row_state).upper().replace(' ', '_')}_{wdra_id or index}",
            "warehouse_manager": manager, "warehouse_name": name, "wdra_warehouse_id": wdra_id, "address": address,
            "district": district, "state": normal_state(row_state), "capacity_mt": capacity, "registration_date": registered,
            "registration_valid_upto": valid_until, "contact_number": phone, "registry_status": status,
            "source_document_id": source_id, "source_url": WDRA_REGISTRY_URL, "source_raw_path": raw_relative(path),
            "source_raw_sha256": digest(path), "retrieved_at_utc": UTC_NOW(),
            "record_semantics": "WDRA public registry record captured on collection date; registration metadata only.",
            "not_supported": "No historical scenario-date vacancy, commodity acceptance, booking, lot quality, price, or transport availability is asserted.",
        }
        row["warehouse_sha256"] = row_hash(row, "warehouse_sha256")
        rows.append(row)
    if not rows:
        raise SystemExit(f"WDRA table contained no parseable rows for {state}.")
    if {row["state"] for row in rows} != {state}:
        raise SystemExit(f"WDRA state mismatch while parsing {state}.")
    return rows


def parse_nhb_facilities(path: Path) -> List[Dict[str, str]]:
    # The public GIS handler occasionally pads an otherwise complete CSV body
    # with NUL bytes.  Preserve that response file byte-for-byte for audit, but
    # remove only the padding in memory before parsing it as CSV.
    payload = path.read_bytes().replace(b"\x00", b"")
    csv.field_size_limit(10 * 1024 * 1024)
    source_rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig", errors="replace"))))
    records: List[Dict[str, str]] = []
    relevant_states = set(STATE_CODES)
    for index, item in enumerate(source_rows, start=1):
        state = normal_state(item.get("StateName", ""))
        if state not in relevant_states:
            continue
        try:
            latitude, longitude = float(item["latitude"]), float(item["longitude"])
        except (KeyError, ValueError):
            continue
        row = {
            "facility_id": f"NHB_ICAP_{state.upper().replace(' ', '_')}_{index:05d}",
            "project_name": item.get("NameofProject", ""), "state": state, "district": item.get("DistrictName", ""),
            "latitude": f"{latitude:.6f}", "longitude": f"{longitude:.6f}",
            "source_document_id": "NHB_ICAP_GEO_FACILITIES", "source_url": NHB_GIS_URL,
            "source_raw_path": raw_relative(path), "source_raw_sha256": digest(path), "retrieved_at_utc": UTC_NOW(),
            "record_semantics": "NHB ICAP mapped project location captured on collection date; project type/capacity is not exposed by this GIS response.",
            "not_supported": "No claim of commodity compatibility, temperature capability, operational status, vacancy, booking, or historical scenario-date availability.",
        }
        row["facility_sha256"] = row_hash(row, "facility_sha256")
        records.append(row)
    if not records:
        raise SystemExit("NHB ICAP facility CSV had no valid records in benchmark states.")
    return records


def parse_nhb_components(path: Path) -> List[Dict[str, str]]:
    source_rows = json.loads(path.read_text(encoding="utf-8"))
    records: List[Dict[str, str]] = []
    for item in source_rows:
        state = normal_state(str(item.get("StateName", "")))
        if state not in STATE_CODES:
            continue
        row = {
            "state": state, "component": str(item.get("Component", "")), "component_code": str(item.get("ComponentCode", "")),
            "project_count": str(item.get("totalproject", "")), "reported_capacity": str(item.get("Capacity", "")),
            "reported_capacity_unit": "NHB-reported component capacity; units vary by component and are not normalised here.",
            "source_document_id": "NHB_ICAP_STATE_COMPONENTS", "source_url": NHB_REPORT_URL,
            "source_raw_path": raw_relative(path), "source_raw_sha256": digest(path), "retrieved_at_utc": UTC_NOW(),
            "record_semantics": "NHB ICAP state aggregate captured on collection date.",
            "not_supported": "No district allocation, commodity compatibility, live capacity, vacancy, booking, or historical scenario-date availability.",
        }
        row["infrastructure_sha256"] = row_hash(row, "infrastructure_sha256")
        records.append(row)
    if {row["state"] for row in records} != set(STATE_CODES):
        raise SystemExit("NHB state-component response does not cover every benchmark state.")
    return records


def distance_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius = 6371.0088
    delta_lat, delta_lon = math.radians(lat_b - lat_a), math.radians(lon_b - lon_a)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(math.radians(lat_a)) * math.cos(math.radians(lat_b)) * math.sin(delta_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def source_inventory(raw_paths: Mapping[str, Path]) -> List[Dict[str, str]]:
    static = {
        **SOURCE_SPECS,
        "MOFPI_COLD_CHAIN_COMPONENTS": {
            "title": "MoFPI Integrated Cold Chain and Value Addition Infrastructure — scheme context", "provider": "Ministry of Food Processing Industries",
            "url": MOFPI_COLD_CHAIN_URL, "kind": "cold_chain_scheme_context", "raw": raw_paths["MOFPI_COLD_CHAIN_COMPONENTS"],
            "temporal": "Current scheme context; not facility availability evidence.",
        },
        "NHB_ICAP_GEO_FACILITIES": {
            "title": "NHB Integrated Cold Chain Availability Platform — mapped project locations", "provider": "National Horticulture Board",
            "url": NHB_GIS_URL, "kind": "collection_date_facility_directory", "raw": raw_paths["NHB_ICAP_GEO_FACILITIES"],
            "temporal": "Collection-date infrastructure directory; not scenario-date availability evidence.",
        },
        "NHB_ICAP_STATE_COMPONENTS": {
            "title": "NHB Integrated Cold Chain Availability Platform — state component summary", "provider": "National Horticulture Board",
            "url": NHB_REPORT_URL, "kind": "collection_date_infrastructure_summary", "raw": raw_paths["NHB_ICAP_STATE_COMPONENTS"],
            "temporal": "Collection-date aggregate infrastructure summary; not scenario-date availability evidence.",
        },
    }
    for state in STATE_CODES:
        source_id = f"WDRA_REGISTERED_WAREHOUSES_{state.upper().replace(' ', '_')}"
        static[source_id] = {
            "title": f"WDRA public list of registered warehouses — {state}", "provider": "Warehousing Development and Regulatory Authority",
            "url": WDRA_REGISTRY_URL, "kind": "collection_date_warehouse_registry", "raw": raw_paths[source_id],
            "temporal": "Collection-date registration directory; not scenario-date occupancy or lot acceptance evidence.",
        }
    records = []
    for source_id, spec in static.items():
        raw = Path(spec["raw"])
        row = {
            "source_document_id": source_id, "source_title": spec["title"], "provider": spec["provider"], "source_url": spec["url"],
            "source_kind": spec["kind"], "raw_path": raw_relative(raw), "raw_sha256": digest(raw), "retrieved_at_utc": UTC_NOW(),
            "temporal_interpretation": spec["temporal"],
            "allowed_use": "Source-cited technical handling or collection-date infrastructure context only; never a direct farm or booking instruction.",
        }
        records.append(row)
    return sorted(records, key=lambda row: row["source_document_id"])


def operation_rows(sources: Mapping[str, Mapping[str, str]]) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    profile_ids = {crop: f"POSTHARVEST_{crop.upper()}_PROFILE_V1" for crop in {item["crop"] for item in OPERATION_SPECS}}
    for spec in OPERATION_SPECS:
        source = sources[spec["source"]]
        row = {
            "operation_id": spec["operation_id"], "profile_id": profile_ids[spec["crop"]], "crop": spec["crop"],
            "operation_lane": spec["lane"], "display_order": str(spec["order"]), "operation_text": spec["text"],
            "method_or_parameter": spec["method"], "conditions_text": spec["conditions"], "missing_observation": spec["missing"],
            "actionability_status": "conditional_postharvest_planning_reference_not_direct_farm_action",
            "source_document_id": spec["source"], "source_title": source["source_title"], "source_provider": source["provider"],
            "source_url": source["source_url"], "source_raw_path": source["raw_path"], "source_raw_sha256": source["raw_sha256"],
            "source_location": spec["location"], "source_quote": spec["quote"], "temporal_interpretation": source["temporal_interpretation"],
        }
        row["operation_sha256"] = row_hash(row, "operation_sha256")
        records.append(row)
    return sorted(records, key=lambda row: (row["crop"], int(row["display_order"])))


def profile_rows(operations: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    grouped: Dict[str, List[Mapping[str, str]]] = {}
    for operation in operations:
        grouped.setdefault(operation["crop"], []).append(operation)
    class_by_crop = {"tomato": "perishable_horticultural", "rice": "dry_grain", "wheat": "dry_grain", "maize": "dry_grain", "chickpea": "pulse", "soybean": "oilseed"}
    records = []
    for crop, values in sorted(grouped.items()):
        row = {
            "profile_id": values[0]["profile_id"], "crop": crop, "commodity_class": class_by_crop[crop],
            "profile_title": f"Source-quoted {crop} post-harvest handling profile", "operation_count": str(len(values)),
            "source_document_ids": ";".join(sorted({item["source_document_id"] for item in values})),
            "profile_scope": "Technical crop-handling context only, bound to this benchmark crop; all operations retain their stated lot-level condition.",
            "farmer_output_status": "conditional_plan_items_available_no_direct_farm_action", 
            "not_supported": "No assertion of harvest readiness, lot moisture, grade, ripeness, storage duration, facility availability, booking, transport availability, freight, or sell/hold decision.",
        }
        row["profile_sha256"] = row_hash(row, "profile_sha256")
        records.append(row)
    return records


def site_context_rows(
    sites: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]], warehouses: Sequence[Mapping[str, str]],
) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    for site in sites:
        crop, state, district = site["crop"], site["state"], site["district"]
        commodity_class = "perishable_horticultural" if crop == "tomato" else ("pulse" if crop == "chickpea" else "oilseed" if crop == "soybean" else "dry_grain")
        if crop == "tomato":
            candidates = []
            for facility in facilities:
                if facility["state"] != state:
                    continue
                km = distance_km(float(site["latitude"]), float(site["longitude"]), float(facility["latitude"]), float(facility["longitude"]))
                candidates.append((km, facility))
            for rank, (km, facility) in enumerate(sorted(candidates, key=lambda pair: (pair[0], pair[1]["facility_id"]))[:3], start=1):
                row = {
                    "site_context_id": f"{site['site_id']}__nhb_{rank}", "site_id": site["site_id"], "crop": crop, "state": state,
                    "district": district, "commodity_class": commodity_class, "context_kind": "nhb_mapped_project_proximity",
                    "candidate_rank": str(rank), "candidate_id": facility["facility_id"], "candidate_name": facility["project_name"],
                    "candidate_district": facility["district"], "candidate_state": facility["state"], "candidate_capacity_mt": "",
                    "candidate_registry_status": "location_record_only", "geodesic_km": f"{km:.2f}",
                    "source_document_id": facility["source_document_id"], "source_url": facility["source_url"], "source_raw_sha256": facility["source_raw_sha256"],
                    "temporal_interpretation": "Collection-date mapped-project context; geodesic distance is derived from public coordinates, not a road route or travel-time estimate.",
                    "allowed_use": "Use only to present source-linked regional infrastructure context after verifying product/service fit directly.",
                    "not_supported": "No claim that the project is a suitable cold-store, has a required temperature, accepts tomato, is operating, has capacity, can be booked, or was available on the scenario date.",
                }
                row["site_context_sha256"] = row_hash(row, "site_context_sha256")
                records.append(row)
        else:
            candidates = [item for item in warehouses if item["state"] == state and item["district"].casefold() == district.casefold()]
            candidates.sort(key=lambda item: (-float(item["capacity_mt"] or 0), item["warehouse_id"]))
            for rank, warehouse in enumerate(candidates[:3], start=1):
                row = {
                    "site_context_id": f"{site['site_id']}__wdra_{rank}", "site_id": site["site_id"], "crop": crop, "state": state,
                    "district": district, "commodity_class": commodity_class, "context_kind": "wdra_registered_warehouse_district_match",
                    "candidate_rank": str(rank), "candidate_id": warehouse["warehouse_id"], "candidate_name": warehouse["warehouse_name"],
                    "candidate_district": warehouse["district"], "candidate_state": warehouse["state"], "candidate_capacity_mt": warehouse["capacity_mt"],
                    "candidate_registry_status": warehouse["registry_status"], "geodesic_km": "",
                    "source_document_id": warehouse["source_document_id"], "source_url": warehouse["source_url"], "source_raw_sha256": warehouse["source_raw_sha256"],
                    "temporal_interpretation": "Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.",
                    "allowed_use": "Use only as a named, source-linked district registry candidate after verifying commodity acceptance and availability directly.",
                    "not_supported": "No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.",
                }
                row["site_context_sha256"] = row_hash(row, "site_context_sha256")
                records.append(row)
    return sorted(records, key=lambda row: (row["site_id"], int(row["candidate_rank"])))


def static_route_rows(
    sites: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]], contexts: Sequence[Mapping[str, str]], refresh: bool,
) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Collect static OSRM geometry for the tomato/NHB candidate links only.

    This is deliberately a small, cacheable collection (15 requests for the
    current benchmark), not a live routing feature.  It therefore carries no
    traffic, vehicle, freight, booking, or commodity-fit semantics.
    """
    site_by_id = {row["site_id"]: row for row in sites}
    facility_by_id = {row["facility_id"]: row for row in facilities}
    records: List[Dict[str, str]] = []
    manifest: List[Dict[str, str]] = []
    for context in contexts:
        if context["context_kind"] != "nhb_mapped_project_proximity":
            continue
        site, facility = site_by_id[context["site_id"]], facility_by_id[context["candidate_id"]]
        route_id = f"{site['site_id']}__{facility['facility_id']}"
        request_url = (
            f"{OSRM_ROUTE_BASE_URL}/{site['longitude']},{site['latitude']};{facility['longitude']},{facility['latitude']}"
            "?overview=false&steps=false"
        )
        raw = RAW / "osrm_routes" / f"{route_id}.json"
        if refresh or not raw.exists():
            fetch(request_url, raw)
        payload = json.loads(raw.read_text(encoding="utf-8"))
        routes = payload.get("routes", [])
        if payload.get("code") != "Ok" or len(routes) != 1:
            raise SystemExit(f"OSRM did not return one route for {route_id}.")
        route = routes[0]
        row = {
            "route_context_id": route_id, "site_id": site["site_id"], "crop": site["crop"], "state": site["state"],
            "district": site["district"], "candidate_id": facility["facility_id"], "candidate_name": facility["project_name"],
            "source_document_id": "OSRM_STATIC_ROUTE_CONTEXT", "route_request_url": request_url,
            "raw_path": raw_relative(raw), "raw_sha256": digest(raw),
            "road_distance_km": f"{float(route['distance']) / 1000:.2f}", "road_duration_minutes": f"{float(route['duration']) / 60:.1f}",
            "retrieved_at_utc": UTC_NOW(),
            "record_semantics": "Static OSRM road-geometry estimate captured at collection time for an NHB mapped-project coordinate pair.",
            "not_supported": "No live traffic, road closure, vehicle availability, cold-chain suitability, commodity acceptance, freight, booking, dispatch, or historical scenario-date route/availability claim.",
        }
        row["route_sha256"] = row_hash(row, "route_sha256")
        records.append(row)
        manifest.append({
            "route_context_id": route_id, "route_request_url": request_url, "raw_path": raw_relative(raw),
            "raw_sha256": digest(raw), "retrieved_at_utc": row["retrieved_at_utc"],
        })
    if len(records) != len([row for row in contexts if row["context_kind"] == "nhb_mapped_project_proximity"]):
        raise SystemExit("Every NHB tomato-site candidate must have exactly one static route record.")
    return sorted(records, key=lambda row: row["route_context_id"]), sorted(manifest, key=lambda row: row["route_context_id"])


def summaries(
    sites: Sequence[Mapping[str, str]], profiles: Sequence[Mapping[str, str]], operations: Sequence[Mapping[str, str]], contexts: Sequence[Mapping[str, str]], routes: Sequence[Mapping[str, str]],
) -> List[Dict[str, str]]:
    profiles_by_crop = {row["crop"]: row for row in profiles}
    operation_count = {crop: len([item for item in operations if item["crop"] == crop]) for crop in profiles_by_crop}
    records = []
    for site in sites:
        values = [row for row in contexts if row["site_id"] == site["site_id"]]
        facility_count = len([row for row in values if row["context_kind"] == "nhb_mapped_project_proximity"])
        warehouse_count = len([row for row in values if row["context_kind"] == "wdra_registered_warehouse_district_match"])
        route_count = len([row for row in routes if row["site_id"] == site["site_id"]])
        kind = "NHB mapped-project proximity" if site["crop"] == "tomato" else "WDRA district-matched warehouse registry"
        coverage = facility_count if site["crop"] == "tomato" else warehouse_count
        status = "source_linked_candidate_context_available" if coverage else "no_district_candidate_in_collection_date_public_registry"
        row = {
            "site_id": site["site_id"], "crop": site["crop"], "state": site["state"], "district": site["district"],
            "commodity_class": profiles_by_crop[site["crop"]]["commodity_class"], "profile_id": profiles_by_crop[site["crop"]]["profile_id"],
            "handling_operation_count": str(operation_count[site["crop"]]), "facility_candidate_count": str(facility_count), "warehouse_candidate_count": str(warehouse_count), "static_road_route_count": str(route_count),
            "infrastructure_context_status": status,
            "summary_text": f"{operation_count[site['crop']]} source-quoted {site['crop']} handling references; {coverage} {kind} candidate(s) in the collection-date public registry; {route_count} static road-geometry context record(s).",
            "temporal_interpretation": "Handling references are conditional technical context; infrastructure candidates are collection-date context, not historical scenario-date availability.",
            "allowed_use": "Rank and explain post-harvest planning references; preserve source and condition.",
            "not_supported": "No direct farm action may be issued from this summary alone: do not issue harvest, storage, dispatch, booking, sell/hold, or transport-availability instructions.",
        }
        row["site_summary_sha256"] = row_hash(row, "site_summary_sha256")
        records.append(row)
    return sorted(records, key=lambda row: row["site_id"])


def scenario_rows(
    scenarios: Sequence[Mapping[str, str]], profiles: Sequence[Mapping[str, str]], operations: Sequence[Mapping[str, str]], summaries_by_site: Mapping[str, Mapping[str, str]],
) -> tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    profile_by_crop = {row["crop"]: row for row in profiles}
    operations_by_crop: Dict[str, List[Mapping[str, str]]] = {}
    for operation in operations:
        operations_by_crop.setdefault(operation["crop"], []).append(operation)
    items: List[Dict[str, str]] = []
    contexts: List[Dict[str, str]] = []
    passages: Dict[str, Dict[str, str]] = {}
    scope: List[Dict[str, str]] = []
    for scenario in scenarios:
        profile = profile_by_crop[scenario["crop"]]
        selected = sorted(operations_by_crop[scenario["crop"]], key=lambda item: int(item["display_order"]))
        for operation in selected:
            item = {
                "plan_item_id": f"{scenario['scenario_id']}__postharvest__{operation['operation_id']}", "scenario_id": scenario["scenario_id"],
                "site_id": scenario["site_id"], "crop": scenario["crop"], "state": scenario["state"], "district": scenario["district"],
                "season": scenario["season"], "decision_date": scenario["decision_date"], "profile_id": profile["profile_id"],
                "operation_id": operation["operation_id"], "display_order": operation["display_order"], "plan_lane": operation["operation_lane"],
                "farmer_visible_label": operation["operation_lane"].replace("_", " ").title(), "operation_text": operation["operation_text"],
                "method_or_parameter": operation["method_or_parameter"], "conditions_text": operation["conditions_text"],
                "missing_observation": operation["missing_observation"], "item_status": "conditional_postharvest_operation_pending_lot_observation",
                "actionability_status": operation["actionability_status"], "source_document_id": operation["source_document_id"],
                "source_title": operation["source_title"], "source_url": operation["source_url"], "source_raw_sha256": operation["source_raw_sha256"],
                "source_location": operation["source_location"], "source_quote": operation["source_quote"],
                "temporal_interpretation": operation["temporal_interpretation"],
                "allowed_use": "Farmer-facing conditional regional/technical operation plan item with its source and condition preserved.",
                "not_supported": "Not a direct farm action and not evidence of current lot state, facility availability, booking, dispatch, freight, or sell/hold outcome.",
            }
            item["plan_item_sha256"] = row_hash(item, "plan_item_sha256")
            items.append(item)
            passage_id = f"POSTHARVEST_PASSAGE__{operation['operation_id']}"
            if passage_id not in passages:
                passage = {
                    "passage_id": passage_id, "source_document_id": operation["source_document_id"], "crop": operation["crop"],
                    "title": operation["source_title"], "provider": operation["source_provider"], "source_url": operation["source_url"],
                    "source_raw_sha256": operation["source_raw_sha256"], "source_location": operation["source_location"],
                    "text": operation["source_quote"],
                    "allowed_use": "Retrieve only after crop scope passes; return as conditional post-harvest technical context.",
                    "not_supported": "Not a source of lot state, historical facility availability, booking, dispatch, freight, or sell/hold decision.",
                }
                passage["passage_sha256"] = row_hash(passage, "passage_sha256")
                passages[passage_id] = passage
            scope_row = {
                "scenario_id": scenario["scenario_id"], "passage_id": passage_id, "crop_scope_status": "pass_exact_crop",
                "allowed_use": "Post-harvest conditional technical context only.",
                "not_supported": "Do not retrieve as a farm-specific action or as infrastructure availability evidence.",
            }
            scope_row["scope_sha256"] = row_hash(scope_row, "scope_sha256")
            scope.append(scope_row)
        summary = summaries_by_site[scenario["site_id"]]
        context = {
            "scenario_id": scenario["scenario_id"], "site_id": scenario["site_id"], "crop": scenario["crop"], "state": scenario["state"],
            "district": scenario["district"], "season": scenario["season"], "decision_date": scenario["decision_date"],
            "profile_id": profile["profile_id"], "postharvest_plan_item_count": str(len(selected)),
            "facility_candidate_count": summary["facility_candidate_count"], "warehouse_candidate_count": summary["warehouse_candidate_count"], "static_road_route_count": summary["static_road_route_count"],
            "context_status": "available_source_linked_postharvest_context",
            "temporal_interpretation": "Technical handling context plus collection-date infrastructure registry context; neither is decision-time farm observation.",
            "allowed_use": "May support prioritised conditional post-harvest plan presentation and source-filtered retrieval.",
            "not_supported": "No direct farm action, lot readiness, facility availability, booking, dispatch, freight, storage duration, or sell/hold recommendation.",
        }
        context["context_sha256"] = row_hash(context, "context_sha256")
        contexts.append(context)
    return items, contexts, sorted(passages.values(), key=lambda row: row["passage_id"]), scope


def provenance(rows: Sequence[Mapping[str, str]], role: str, path: Path, notes: str) -> Dict[str, str]:
    return {"generated_at_utc": UTC_NOW(), "artifact_role": role, "input_path": raw_relative(path) if path.is_relative_to(ENRICHED) else str(path.relative_to(PROJECT_ROOT)), "input_sha256": digest(path), "input_row_count": str(len(rows)), "notes": notes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build source-scoped post-harvest storage and logistics enrichment.")
    parser.add_argument("--refresh", action="store_true", help="Refresh collection-date public registry snapshots before rebuilding.")
    args = parser.parse_args()

    raw_paths = ensure_raw_sources(args.refresh)
    sources = source_inventory(raw_paths)
    source_by_id = {row["source_document_id"]: row for row in sources}
    operations = operation_rows(source_by_id)
    profiles = profile_rows(operations)
    facilities = parse_nhb_facilities(raw_paths["NHB_ICAP_GEO_FACILITIES"])
    infrastructure = parse_nhb_components(raw_paths["NHB_ICAP_STATE_COMPONENTS"])
    warehouses: List[Dict[str, str]] = []
    for state in STATE_CODES:
        source_id = f"WDRA_REGISTERED_WAREHOUSES_{state.upper().replace(' ', '_')}"
        warehouses.extend(parse_wdra(raw_paths[source_id], state, source_id))
    warehouses.sort(key=lambda row: row["warehouse_id"])

    sites = read_csv(PROJECT_ROOT / "data" / "registry" / "final_study_sites.csv")
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    if len(sites) != 30 or len({row["site_id"] for row in sites}) != 30:
        raise SystemExit("Frozen study-site registry must contain exactly 30 unique sites.")
    if len(scenarios) != 300 or len({row["scenario_id"] for row in scenarios}) != 300:
        raise SystemExit("Frozen scenario manifest must contain exactly 300 unique scenarios.")
    site_by_id = {row["site_id"]: row for row in sites}
    if any(scenario["site_id"] not in site_by_id for scenario in scenarios):
        raise SystemExit("A frozen scenario references an unknown study site.")

    site_context = site_context_rows(sites, facilities, warehouses)
    routes, route_manifest = static_route_rows(sites, facilities, site_context, args.refresh)
    route_manifest_path = RAW / "osrm_route_manifest.csv"
    write_csv(route_manifest_path, ROUTE_MANIFEST_FIELDS, route_manifest)
    sources.append({
        "source_document_id": "OSRM_STATIC_ROUTE_CONTEXT", "source_title": "OSRM public static road-route service", "provider": "OpenStreetMap contributors / Project OSRM",
        "source_url": OSRM_ROUTE_BASE_URL, "source_kind": "collection_date_static_route_context", "raw_path": raw_relative(route_manifest_path),
        "raw_sha256": digest(route_manifest_path), "retrieved_at_utc": UTC_NOW(),
        "temporal_interpretation": "Collection-date static road geometry only; not historic routing or live traffic evidence.",
        "allowed_use": "Static road distance/duration context for an NHB mapped-project coordinate pair only; never a dispatch or booking instruction.",
    })
    sources.sort(key=lambda row: row["source_document_id"])
    site_summaries = summaries(sites, profiles, operations, site_context, routes)
    site_summary_by_id = {row["site_id"]: row for row in site_summaries}
    items, scenario_context, passages, scope = scenario_rows(scenarios, profiles, operations, site_summary_by_id)

    outputs = [
        ("postharvest_source_inventory.csv", SOURCE_FIELDS, sources),
        ("postharvest_handling_profiles.csv", PROFILE_FIELDS, profiles),
        ("postharvest_operation_library.csv", OPERATION_FIELDS, operations),
        ("postharvest_nhb_facility_records.csv", FACILITY_FIELDS, facilities),
        ("postharvest_wdra_warehouse_records.csv", WAREHOUSE_FIELDS, warehouses),
        ("postharvest_nhb_state_infrastructure.csv", INFRASTRUCTURE_FIELDS, infrastructure),
        ("postharvest_site_facility_context.csv", SITE_CONTEXT_FIELDS, site_context),
        ("postharvest_static_route_context.csv", ROUTE_FIELDS, routes),
        ("postharvest_site_summary.csv", SUMMARY_FIELDS, site_summaries),
        ("scenario_postharvest_plan_items.csv", SCENARIO_ITEM_FIELDS, items),
        ("scenario_postharvest_logistics_context.csv", SCENARIO_CONTEXT_FIELDS, scenario_context),
        ("postharvest_rag_passages.csv", RAG_PASSAGE_FIELDS, passages),
        ("scenario_postharvest_rag_scope.csv", RAG_SCOPE_FIELDS, scope),
    ]
    for filename, fields, rows in outputs:
        write_csv(ENRICHED / filename, fields, rows)

    input_rows = [
        provenance(sources, "source_inventory", raw_paths["NHB_ICAP_GEO_FACILITIES"], "Source inventory includes crop handling, NHB, MoFPI, and WDRA evidence."),
        provenance(facilities, "nhb_facility_records", raw_paths["NHB_ICAP_GEO_FACILITIES"], "Mapped projects only; no capacity/availability inference."),
        provenance(infrastructure, "nhb_state_components", raw_paths["NHB_ICAP_STATE_COMPONENTS"], "State aggregate components only."),
        provenance(routes, "osrm_static_routes", route_manifest_path, "Static road geometry only; no live-routing, capacity, or dispatch semantics."),
    ]
    for state in STATE_CODES:
        source_id = f"WDRA_REGISTERED_WAREHOUSES_{state.upper().replace(' ', '_')}"
        state_rows = [row for row in warehouses if row["state"] == state]
        input_rows.append(provenance(state_rows, f"wdra_registry_{state.lower().replace(' ', '_')}", raw_paths[source_id], "Public registry metadata only; no occupancy or commodity inference."))
    input_rows.append(provenance(scenarios, "frozen_scenario_manifest", PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv", "Immutable scenario identities used for the 300 bindings."))
    write_csv(ENRICHED / "postharvest_logistics_provenance.csv", PROVENANCE_FIELDS, input_rows)

    print(
        "Post-harvest logistics enrichment built: "
        f"{len(profiles)} profiles, {len(operations)} source-quoted operations, {len(facilities)} NHB mapped facilities, "
        f"{len(warehouses)} WDRA warehouse records, {len(items)} scenario plan items, and {len(scenario_context)} scenario contexts."
    )


if __name__ == "__main__":
    main()
