"""Turn verified official documents into a conservative action/RAG enrichment.

Nothing in this script invents a farming operation.  Every catalogue row uses a
verbatim quote that is checked against a hash-verified extracted source page.
The binder deliberately separates (a) document/crop/place/date applicability
from (b) unobserved farm conditions such as crop stage, diagnosis, soil test,
or documented irrigation system.  A conditional source operation is therefore
not silently promoted into a farm-specific instruction.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ACTION_FIELDS = [
    "action_id", "action_category", "crop", "state_scope", "season_scope", "source_document_id",
    "source_title", "provider", "official_url", "source_raw_sha256", "source_location", "source_quote",
    "operation_text", "method_text", "dose_text", "conditions_text", "requires_actual_crop_stage",
    "requires_field_observation", "requires_soil_test_for_personalised_dose", "requires_diagnosis_or_threshold",
    "requires_documented_system_or_variety", "source_effective_from", "source_effective_to",
    "source_effective_window_basis", "action_record_sha256",
]
BINDING_FIELDS = [
    "scenario_id", "action_id", "crop", "state", "district", "season", "decision_date", "source_document_id",
    "crop_scope_status", "geography_scope_status", "season_scope_status", "source_temporal_status",
    "field_condition_status", "binding_status", "binding_reason", "action_record_sha256",
]
RAG_SCOPE_FIELDS = [
    "scenario_id", "crop", "state", "district", "season", "decision_date", "source_document_id", "source_title",
    "source_class", "official_url", "source_raw_sha256", "source_latest_possible_date", "source_effective_from",
    "source_effective_to", "crop_scope_status", "geography_scope_status", "source_temporal_status",
    "retrieval_status", "rag_scope_status", "restriction_reason",
]

# A blank end date means a technical recommendation is treated as a static
# document from its conservative availability date forward. Annual/weekly and
# package-of-practice publications have an explicit end so later scenarios do
# not accidentally use stale seasonal advice.
SOURCE_WINDOWS = {
    "PAU_KHARIF_2026": ("2026-03-31", "2026-12-31", "named_kharif_2026_package"),
    "PAU_RABI_2025_26": ("2025-08-31", "2026-06-30", "named_rabi_2025_26_package"),
    "TNAU_RICE_NUTRIENT_2023": ("2023-01-31", "", "dated_static_extension_page"),
    "TNAU_RICE_PROTECTION_INDEX_2023": ("2023-01-31", "", "dated_static_extension_page"),
    "TNAU_TOMATO_FERTIGATION_2014": ("2014-10-29", "", "dated_static_extension_document"),
    "TNAU_TOMATO_FRUIT_BORER_2023": ("2023-06-30", "", "dated_static_extension_page"),
    "TNAU_TOMATO_EARLY_BLIGHT_2023": ("2023-06-30", "", "dated_static_extension_page"),
    "TNAU_MAIZE_FAW_2023": ("2023-05-31", "", "dated_static_extension_page"),
    "ICAR_IISR_SOYBEAN_BULLETIN_2023": ("2023-12-31", "", "dated_static_technical_bulletin"),
    "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024": ("2024-07-01", "2024-07-07", "explicit_weekly_advisory_dates"),
    "ICAR_KHARIF_STATE_ADVISORIES_2025": ("2025-05-31", "2025-12-31", "named_kharif_2025_advisory"),
    "ICAR_RABI_STATE_ADVISORIES_2021_22": ("2021-09-30", "2022-06-30", "named_rabi_2021_22_advisory"),
    "CIBRC_INSECTICIDE_2026": ("2026-03-31", "", "dated_regulatory_register_not_prescriptive"),
    "CIBRC_FUNGICIDE_2026": ("2026-03-31", "", "dated_regulatory_register_not_prescriptive"),
}

# Registry metadata is the authority for a document's study geography.  We do
# not expand it based on a phrase found somewhere in a large national PDF.
SOURCE_STATES = {
    "PAU_KHARIF_2026": {"Punjab"}, "PAU_RABI_2025_26": {"Punjab"},
    "TNAU_RICE_NUTRIENT_2023": {"Tamil Nadu"}, "TNAU_RICE_PROTECTION_INDEX_2023": {"Tamil Nadu"},
    "TNAU_TOMATO_FERTIGATION_2014": {"Tamil Nadu"}, "TNAU_TOMATO_FRUIT_BORER_2023": {"Tamil Nadu"},
    "TNAU_TOMATO_EARLY_BLIGHT_2023": {"Tamil Nadu"}, "TNAU_MAIZE_FAW_2023": {"Tamil Nadu"},
    "ICAR_IISR_SOYBEAN_BULLETIN_2023": {"Madhya Pradesh", "Rajasthan"},
    "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024": {"Madhya Pradesh", "Rajasthan"},
    "ICAR_KHARIF_STATE_ADVISORIES_2025": {"Maharashtra", "Rajasthan"},
    "ICAR_RABI_STATE_ADVISORIES_2021_22": {"Madhya Pradesh", "Maharashtra", "Tamil Nadu"},
    "CIBRC_INSECTICIDE_2026": {"India national"}, "CIBRC_FUNGICIDE_2026": {"India national"},
}


# `source_quote` is verified byte-for-byte after whitespace normalisation.  It
# is also the only field from which a downstream system may formulate a direct
# operation.  Pesticidal rows are intentionally retained for corpus coverage,
# but their diagnosis/stage gates prevent treatment output in this benchmark.
ACTION_SPECS = [
    {
        "action_id": "PAU_RICE_STOP_IRRIGATION_PRE_MATURITY", "action_category": "irrigation",
        "crop": "rice", "state_scope": "Punjab", "season_scope": "kharif", "source_document_id": "PAU_KHARIF_2026",
        "source_location": "pdf_page_9", "source_quote": "Stop irrigation about a fortnight before maturity.",
        "operation_text": "Stop irrigation about a fortnight before maturity.", "method_text": "", "dose_text": "",
        "conditions_text": "Only when the crop is about a fortnight before maturity.", "stage": True,
    },
    {
        "action_id": "PAU_RICE_HARVEST_AT_PROPER_MATURITY", "action_category": "harvest",
        "crop": "rice", "state_scope": "Punjab", "season_scope": "kharif", "source_document_id": "PAU_KHARIF_2026",
        "source_location": "pdf_page_9", "source_quote": "Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.",
        "operation_text": "Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.",
        "method_text": "Avoid harvesting during night.", "dose_text": "", "conditions_text": "Only when proper maturity is observed for the variety.", "stage": True,
    },
    {
        "action_id": "PAU_WHEAT_HARVEST_FULLY_RIPE", "action_category": "harvest",
        "crop": "wheat", "state_scope": "Punjab", "season_scope": "rabi", "source_document_id": "PAU_RABI_2025_26",
        "source_location": "pdf_page_25", "source_quote": "Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering. Delayed harvesting results in high grain losses.",
        "operation_text": "Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering.",
        "method_text": "Harvest manually, with a combine, or with a tractor-operated vertical conveyer reaper windrower as documented in the source.",
        "dose_text": "", "conditions_text": "Only when the wheat is fully ripe.", "stage": True,
    },
    {
        "action_id": "IISR_SOYBEAN_BASAL_NUTRIENT_TIMING", "action_category": "fertilizer",
        "crop": "soybean", "state_scope": "Madhya Pradesh;Rajasthan", "season_scope": "kharif", "source_document_id": "ICAR_IISR_SOYBEAN_BULLETIN_2023",
        "source_location": "pdf_page_28", "source_quote": "In soybean, use of fertilizers is recommended only as basal application. Therefore, farmers are advised not to use any fertilizers in standing crop unless being recommended by the scientists.",
        "operation_text": "Use fertilizer only as basal application; do not use fertilizer in a standing crop unless recommended by scientists.",
        "method_text": "Basal application at sowing.", "dose_text": "No farm-specific dose; the source says the dose should be tailored after soil testing.",
        "conditions_text": "Only at sowing and only as a regional baseline; a personalised dose requires a soil test.", "stage": True, "soil": True,
    },
    {
        "action_id": "IISR_SOYBEAN_HARVEST_AT_90_PERCENT_YELLOW_PODS", "action_category": "harvest",
        "crop": "soybean", "state_scope": "Madhya Pradesh;Rajasthan", "season_scope": "kharif", "source_document_id": "ICAR_IISR_SOYBEAN_BULLETIN_2023",
        "source_location": "pdf_page_33", "source_quote": "When 90% of the pods changes its color to yellow, it is the right indication to go for harvesting.",
        "operation_text": "Harvest when 90% of pods change colour to yellow.", "method_text": "", "dose_text": "",
        "conditions_text": "Only when 90% yellow-pod maturity is observed.", "stage": True,
    },
    {
        "action_id": "IISR_SOYBEAN_THRESH_350_TO_400_RPM", "action_category": "post_harvest",
        "crop": "soybean", "state_scope": "Madhya Pradesh;Rajasthan", "season_scope": "kharif", "source_document_id": "ICAR_IISR_SOYBEAN_BULLETIN_2023",
        "source_location": "pdf_page_33", "source_quote": "To maintain viability of seed and to avoid loss/mechanical damage, threshing should be done at 350-400 rpm.",
        "operation_text": "Thresh soybean at 350–400 rpm.", "method_text": "", "dose_text": "350–400 rpm.",
        "conditions_text": "Only after soybean has been harvested and threshing is being performed.", "stage": True,
    },
    {
        "action_id": "IISR_SOYBEAN_SOW_AFTER_MONSOON_100MM", "action_category": "crop_establishment",
        "crop": "soybean", "state_scope": "Madhya Pradesh;Rajasthan", "season_scope": "kharif", "source_document_id": "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024",
        "source_location": "pdf_page_2", "source_quote": "Sowing may be done after the onset of monsoon and receipt of 100 mm rainfall.",
        "operation_text": "Sow after monsoon onset and receipt of 100 mm rainfall.", "method_text": "", "dose_text": "100 mm rainfall threshold.",
        "conditions_text": "Only if sowing has not yet occurred, monsoon onset is documented, and 100 mm rainfall has been received.", "stage": True, "field": True,
    },
    {
        "action_id": "IISR_SOYBEAN_CENTRAL_ZONE_SOWING_NUTRIENTS", "action_category": "fertilizer",
        "crop": "soybean", "state_scope": "Madhya Pradesh;Rajasthan", "season_scope": "kharif", "source_document_id": "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024",
        "source_location": "pdf_page_2", "source_quote": "Farmers are advised to apply the recommended quantity of all the nutrients (25:60:40:20 N:P2O5:K2O:S kg/ha) at the time of sowing only.",
        "operation_text": "Apply the Central Zone regional nutrient baseline at sowing only.", "method_text": "The source permits broadcasting just before sowing or use of a seed-cum-fertilizer drill.",
        "dose_text": "25:60:40:20 N:P2O5:K2O:S kg/ha.", "conditions_text": "Only at actual sowing; this is a regional baseline, not a farm-specific prescription.", "stage": True, "soil": True,
    },
    {
        "action_id": "TNAU_TOMATO_HYBRID_DRIP_FERTIGATION", "action_category": "fertilizer",
        "crop": "tomato", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_TOMATO_FERTIGATION_2014",
        "source_location": "pdf_page_1", "source_quote": "The nutrient requirement for hybrids is 200:250:250 kg of NPK per ha.",
        "operation_text": "Use the documented hybrid-tomato drip-fertigation schedule.",
        "method_text": "The source applies 75% of P as basal and the remaining nutrients through fertigation in stage-specific splits.",
        "dose_text": "200:250:250 kg NPK/ha for hybrids.", "conditions_text": "Only for documented tomato hybrids under the documented drip-fertigation system and known crop stage.", "stage": True, "system": True, "soil": True,
    },
    {
        "action_id": "TNAU_TOMATO_FRUIT_BORER_PHEROMONE_TRAPS", "action_category": "crop_protection_preventive",
        "crop": "tomato", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_TOMATO_FRUIT_BORER_2023",
        "source_location": "html_document", "source_quote": "Setup pheromone trap with Helilure at 12/ha",
        "operation_text": "Set up Helilure pheromone traps.", "method_text": "", "dose_text": "12 traps/ha.",
        "conditions_text": "Only for an existing tomato crop when the implementation stage is documented.", "stage": True,
    },
    {
        "action_id": "TNAU_TOMATO_FRUIT_BORER_REMOVE_INFESTED_FRUIT", "action_category": "crop_protection_response",
        "crop": "tomato", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_TOMATO_FRUIT_BORER_2023",
        "source_location": "html_document", "source_quote": "Collect and destroy the infected fruits and grown up larvae",
        "operation_text": "Collect and destroy infected fruits and grown-up larvae.", "method_text": "", "dose_text": "",
        "conditions_text": "Only when fruit borer infestation/infected fruit is observed.", "stage": True, "diagnosis": True,
    },
    {
        "action_id": "TNAU_TOMATO_EARLY_BLIGHT_REMOVE_DEBRIS", "action_category": "crop_protection_sanitation",
        "crop": "tomato", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_TOMATO_EARLY_BLIGHT_2023",
        "source_location": "html_document", "source_quote": "Removal and destruction of crop debris.",
        "operation_text": "Remove and destroy crop debris.", "method_text": "", "dose_text": "",
        "conditions_text": "Only where relevant crop debris is present and this disease-management measure is applicable.", "field": True,
    },
    {
        "action_id": "TNAU_TOMATO_EARLY_BLIGHT_FUNGICIDE", "action_category": "crop_protection_response",
        "crop": "tomato", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_TOMATO_EARLY_BLIGHT_2023",
        "source_location": "html_document", "source_quote": "Spray Iprodione 50% WP @ 600 g/ac or Azoxystrobin 23% SC @ 200 ml/ac or Mancozeb 35% SC @ 1 kg/ac",
        "operation_text": "Use only the documented early-blight fungicide alternatives after a supported diagnosis.", "method_text": "Spray one of the source-listed formulations.",
        "dose_text": "Iprodione 50% WP 600 g/ac; or Azoxystrobin 23% SC 200 ml/ac; or Mancozeb 35% SC 1 kg/ac.",
        "conditions_text": "Only after a supported early-blight diagnosis and applicable labelled/regulatory verification.", "stage": True, "diagnosis": True,
    },
    {
        "action_id": "TNAU_MAIZE_FAW_PHEROMONE_TRAPS", "action_category": "crop_protection_preventive",
        "crop": "maize", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_MAIZE_FAW_2023",
        "source_location": "html_document", "source_quote": "Set up FAW pheromone traps @ 12 nos./ha",
        "operation_text": "Set up FAW pheromone traps.", "method_text": "", "dose_text": "12 traps/ha.",
        "conditions_text": "Only for an existing maize crop when the implementation stage is documented.", "stage": True,
    },
    {
        "action_id": "TNAU_MAIZE_FAW_EARLY_STAGE_TREATMENT", "action_category": "crop_protection_response",
        "crop": "maize", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "TNAU_MAIZE_FAW_2023",
        "source_location": "html_document", "source_quote": "Spray azadirachtin 1500 ppm @ 2.5 lit/ha or chlorantraniliprole 18.5 SC @ 200ml/ha (or) flubendiamide 480SC@ 250ml/ha at early stage (15 - 20 DAE).",
        "operation_text": "Use a source-listed FAW treatment only at the documented early stage.", "method_text": "Spray one of the listed source formulations.",
        "dose_text": "Azadirachtin 1500 ppm 2.5 L/ha; or chlorantraniliprole 18.5 SC 200 ml/ha; or flubendiamide 480 SC 250 ml/ha.",
        "conditions_text": "Only after supported FAW diagnosis/threshold and confirmed 15–20 days-after-emergence stage, with labelled/regulatory verification.", "stage": True, "diagnosis": True,
    },
    {
        "action_id": "ICAR_RABI_MH_CHICKPEA_SOWING_WINDOW", "action_category": "crop_establishment",
        "crop": "chickpea", "state_scope": "Maharashtra", "season_scope": "rabi", "source_document_id": "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "source_location": "pdf_page_315", "source_quote": "Rainfed chickpea should be sown in first fortnight of October while irrigated chickpea should be sown from last week of October to first week of November.",
        "operation_text": "Use the source's rainfed or irrigated chickpea sowing window.", "method_text": "", "dose_text": "",
        "conditions_text": "Only before sowing and after the farm's rainfed/irrigated regime is documented.", "stage": True, "system": True,
    },
    {
        "action_id": "ICAR_RABI_TN_MAIZE_REGIONAL_NPK", "action_category": "fertilizer",
        "crop": "maize", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "source_location": "pdf_page_390", "source_quote": "Apply 135:62.5:50 kg/ ha N:P2O5:K2O for varieties and 250:75:75 kg/ha for hybrids.",
        "operation_text": "Use the source's variety- or hybrid-specific regional NPK baseline.", "method_text": "", "dose_text": "135:62.5:50 kg/ha for varieties; 250:75:75 kg/ha for hybrids.",
        "conditions_text": "Only with documented variety/hybrid, actual stage, and a soil test for farm-specific adjustment.", "stage": True, "system": True, "soil": True,
    },
    {
        "action_id": "ICAR_RABI_TN_TOMATO_PHEROMONE_TRAPS", "action_category": "crop_protection_preventive",
        "crop": "tomato", "state_scope": "Tamil Nadu", "season_scope": "rabi", "source_document_id": "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "source_location": "pdf_page_395", "source_quote": "Pin-bollworm management: Place pheromone traps @ 40/ha",
        "operation_text": "Place pheromone traps for tomato pin-bollworm management.", "method_text": "", "dose_text": "40 traps/ha.",
        "conditions_text": "Only for an existing tomato crop when the implementation stage and target-pest context are documented.", "stage": True,
    },
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


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def canonical_hash(row: Mapping[str, str], fields: Sequence[str]) -> str:
    payload = {field: row.get(field, "") for field in fields if field != "action_record_sha256"}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def source_temporal_status(value: str, start: str, end: str) -> str:
    if value < start:
        return "blocked_source_not_yet_available"
    if end and value > end:
        return "blocked_source_effective_window_ended"
    return "pass_source_time_valid"


def source_crop_matches(source: Mapping[str, str], crop: str) -> bool:
    values = {value.strip().casefold() for value in source["crop_scope"].split(";")}
    return crop.casefold() in values or "registered crops" in values


def source_geography_status(source_id: str, state: str) -> str:
    allowed = SOURCE_STATES.get(source_id, set())
    return "pass_geography_scope" if "India national" in allowed or state in allowed else "blocked_geography_scope"


def conditional_reason(spec: Mapping[str, object]) -> str:
    required = []
    if spec.get("stage"):
        required.append("actual_crop_stage")
    if spec.get("field"):
        required.append("documented_field_condition")
    if spec.get("soil"):
        required.append("soil_test_for_personalised_dose")
    if spec.get("diagnosis"):
        required.append("dated_diagnosis_or_threshold")
    if spec.get("system"):
        required.append("documented_system_or_variety")
    return ";".join(required) or "no_additional_condition"


def main() -> None:
    scenario_root = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenario_root / "enriched"
    inventory = {row["source_document_id"]: row for row in read_csv(enriched / "official_rag_source_inventory.csv")}
    scenarios = read_csv(scenario_root / "manifests" / "scenario_manifest.csv")
    chunks = read_csv(enriched / "official_rag_chunks.csv")
    source_text: Dict[str, Dict[str, str]] = {}
    for source_id, source in inventory.items():
        extracted = source.get("extracted_text_path", "")
        if not extracted:
            continue
        document = json.loads((enriched / extracted).read_text(encoding="utf-8"))
        source_text[source_id] = {location: text for location, text in document["sections"]}

    actions: List[Dict[str, str]] = []
    for spec in ACTION_SPECS:
        source_id = str(spec["source_document_id"])
        source = inventory.get(source_id)
        if not source or not source["retrieval_status"].endswith("_admitted_to_rag"):
            raise SystemExit(f"Action {spec['action_id']} requires a non-admitted official source: {source_id}")
        location = str(spec["source_location"])
        page = source_text.get(source_id, {}).get(location, "")
        if normalise(str(spec["source_quote"])) not in normalise(page):
            raise SystemExit(f"Action {spec['action_id']} quote is absent from {source_id}:{location}")
        start, end, basis = SOURCE_WINDOWS[source_id]
        row = {
            "action_id": str(spec["action_id"]), "action_category": str(spec["action_category"]),
            "crop": str(spec["crop"]), "state_scope": str(spec["state_scope"]), "season_scope": str(spec["season_scope"]),
            "source_document_id": source_id, "source_title": source["source_title"], "provider": source["provider"],
            "official_url": source["official_url"], "source_raw_sha256": source["raw_sha256"], "source_location": location,
            "source_quote": str(spec["source_quote"]), "operation_text": str(spec["operation_text"]),
            "method_text": str(spec["method_text"]), "dose_text": str(spec["dose_text"]),
            "conditions_text": str(spec["conditions_text"]), "requires_actual_crop_stage": str(bool(spec.get("stage"))).lower(),
            "requires_field_observation": str(bool(spec.get("field"))).lower(),
            "requires_soil_test_for_personalised_dose": str(bool(spec.get("soil"))).lower(),
            "requires_diagnosis_or_threshold": str(bool(spec.get("diagnosis"))).lower(),
            "requires_documented_system_or_variety": str(bool(spec.get("system"))).lower(),
            "source_effective_from": start, "source_effective_to": end, "source_effective_window_basis": basis,
            "action_record_sha256": "",
        }
        row["action_record_sha256"] = canonical_hash(row, ACTION_FIELDS)
        actions.append(row)

    bindings: List[Dict[str, str]] = []
    for scenario in scenarios:
        for action in actions:
            crop_status = "pass_crop_scope" if scenario["crop"] == action["crop"] else "blocked_crop_scope"
            allowed_states = set(action["state_scope"].split(";"))
            geography_status = "pass_geography_scope" if scenario["state"] in allowed_states else "blocked_geography_scope"
            season_status = "pass_season_scope" if scenario["season"] == action["season_scope"] else "blocked_season_scope"
            temporal_status = source_temporal_status(scenario["decision_date"], action["source_effective_from"], action["source_effective_to"])
            matching = all(value.startswith("pass_") for value in (crop_status, geography_status, season_status, temporal_status))
            action_spec = next(item for item in ACTION_SPECS if item["action_id"] == action["action_id"])
            pending = conditional_reason(action_spec)
            if not matching:
                statuses = [crop_status, geography_status, season_status, temporal_status]
                failed = next(value for value in statuses if value.startswith("blocked_"))
                binding_status, reason = failed, failed
                field_status = "not_evaluated_outside_source_scope"
            elif pending != "no_additional_condition":
                binding_status = "conditionally_applicable_pending_unobserved_farm_condition"
                reason = pending
                field_status = "missing_in_frozen_scenario:" + pending
            else:
                binding_status, reason, field_status = "source_scoped_eligible", "no_extra_condition", "not_required"
            bindings.append({
                "scenario_id": scenario["scenario_id"], "action_id": action["action_id"], "crop": scenario["crop"],
                "state": scenario["state"], "district": scenario["district"], "season": scenario["season"],
                "decision_date": scenario["decision_date"], "source_document_id": action["source_document_id"],
                "crop_scope_status": crop_status, "geography_scope_status": geography_status,
                "season_scope_status": season_status, "source_temporal_status": temporal_status,
                "field_condition_status": field_status, "binding_status": binding_status,
                "binding_reason": reason, "action_record_sha256": action["action_record_sha256"],
            })

    # Source-level RAG scope includes every extracted chunk's document.  The
    # retriever can join this table to `official_rag_chunks.csv` by document ID,
    # filtering before semantic ranking instead of retrieving a future or
    # geography-mismatched passage and trying to repair it afterwards.
    chunk_sources = sorted({row["source_document_id"] for row in chunks})
    rag_scope: List[Dict[str, str]] = []
    for scenario in scenarios:
        for source_id in chunk_sources:
            source = inventory[source_id]
            start, end, _ = SOURCE_WINDOWS[source_id]
            crop_status = "pass_crop_scope" if source_crop_matches(source, scenario["crop"]) else "blocked_crop_scope"
            geography_status = source_geography_status(source_id, scenario["state"])
            temporal_status = source_temporal_status(scenario["decision_date"], start, end)
            is_regulatory = source["source_class"] == "national_regulatory_record"
            if not source["retrieval_status"].endswith("_admitted_to_rag"):
                rag_status, restriction = "excluded_source_not_admitted", "source retrieval/hash gate did not pass"
            elif is_regulatory:
                rag_status, restriction = "regulatory_context_only_not_action_retrieval", "registration record; not a treatment recommendation"
            elif all(value.startswith("pass_") for value in (crop_status, geography_status, temporal_status)):
                rag_status, restriction = "admitted_to_metadata_filtered_rag", "source scope and effective window pass"
            else:
                rag_status, restriction = "excluded_by_metadata_filter", ";".join(
                    value for value in (crop_status, geography_status, temporal_status) if value.startswith("blocked_")
                )
            rag_scope.append({
                "scenario_id": scenario["scenario_id"], "crop": scenario["crop"], "state": scenario["state"],
                "district": scenario["district"], "season": scenario["season"], "decision_date": scenario["decision_date"],
                "source_document_id": source_id, "source_title": source["source_title"], "source_class": source["source_class"],
                "official_url": source["official_url"], "source_raw_sha256": source["raw_sha256"],
                "source_latest_possible_date": source["source_latest_possible_date"], "source_effective_from": start,
                "source_effective_to": end, "crop_scope_status": crop_status, "geography_scope_status": geography_status,
                "source_temporal_status": temporal_status, "retrieval_status": source["retrieval_status"],
                "rag_scope_status": rag_status, "restriction_reason": restriction,
            })

    write_csv(enriched / "official_action_records.csv", ACTION_FIELDS, actions)
    write_csv(enriched / "scenario_official_action_bindings.csv", BINDING_FIELDS, bindings)
    write_csv(enriched / "scenario_rag_scope.csv", RAG_SCOPE_FIELDS, rag_scope)
    admitted_docs = len({row["source_document_id"] for row in rag_scope if row["rag_scope_status"] == "admitted_to_metadata_filtered_rag"})
    report = [
        "# Official Action and RAG Enrichment\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n",
        f"- Hash-verified official source documents in chunk corpus: {len(chunk_sources)}\n",
        f"- Verbatim, source-checked operation records: {len(actions)}\n",
        f"- Scenario × operation applicability rows: {len(bindings)}\n",
        f"- Scenario × document metadata-scope rows: {len(rag_scope)}\n",
        "\n## Safety and temporal rules\n",
        "- A source quote must be found in its recorded official page before an action record is written.\n",
        "- Named weekly, seasonal, and package-of-practice documents have explicit effective end dates. A later scenario cannot retrieve them as a current source.\n",
        "- `conditionally_applicable_pending_unobserved_farm_condition` is not an instruction. It records a relevant official operation whose real farm precondition is absent from the frozen benchmark.\n",
        "- CIBRC/PPQS documents are retained as regulatory context and are never used as treatment recommendations.\n",
    ]
    (enriched / "OFFICIAL_RAG_CORPUS.md").write_text("".join(report), encoding="utf-8")
    print(f"Official action enrichment: {len(actions)} source-checked operations; {len(bindings)} scenario bindings; {len(rag_scope)} RAG scope records.")
    print(f"Metadata-filtered RAG has {sum(row['rag_scope_status'] == 'admitted_to_metadata_filtered_rag' for row in rag_scope)} scenario-document admissions across {admitted_docs} documents.")


if __name__ == "__main__":
    main()
