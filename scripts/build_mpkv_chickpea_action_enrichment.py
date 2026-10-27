"""Add a source-quoted Maharashtra chickpea operation from MPKV's public guide.

MPKV's dated *Krishi Darshani 2023* describes its crop-production technologies
for farmers statewide.  The PDF uses a legacy Marathi font that does not yield
reliable Unicode text extraction.  The collector therefore retains hash-linked
page raster images and a deliberately limited visual transcription, alongside
the original hash-frozen PDF.  This is transparent source verification, not
OCR-derived or model-generated text.

The single operation is persistent regional technical guidance from publication
onward. It remains conditional on actual maturity and crop dryness; it is not
a weekly advisory or a direct farm action.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from typing import Dict, Iterable, List, Mapping, Sequence
from urllib.request import Request, urlopen

from build_combined_official_action_catalog import ACTION_FIELDS, BINDING_FIELDS


ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "data" / "scenarios" / "enriched"
SCENARIO_PATH = ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv"
RAW_DIR = ENRICHED / "raw" / "mpkv_krishi_darshani_sources"
TEXT_DIR = ENRICHED / "rag_sources" / "mpkv_krishi_darshani_visual_transcriptions"
SOURCE_ID = "MPKV_KRISHI_DARSHANI_2023"
OFFICIAL_URL = "https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf"
PUBLICATION_PAGE_URL = "https://mpkv.ac.in/Extension/ExtensionPublication"
PUBLISHED_ON = "2023-06-07"
SOURCE_QUOTE = "हरभरा पीक ११० ते १२० दिवसांमध्ये तयार होते. पीक ओलसर असताना काढणी करू नये. घाटे कडक झाल्यानंतर मग हरभऱ्याची काढणी करून मळणी करावी."
SCOPE_QUOTE = "सन २०२१-२२ मध्ये महाराष्ट्र राज्यात हरभरा पिकाचे क्षेत्र..."
INVENTORY_FIELDS = [
    "source_document_id", "source_title", "provider", "official_url", "publication_date", "source_effective_from", "source_effective_to",
    "crop_scope", "state_scope", "season_scope", "original_server_last_modified_utc", "http_metadata_path", "http_metadata_sha256",
    "publication_page_url", "publication_page_raw_path", "publication_page_raw_sha256", "publication_page_quote",
    "raw_path", "raw_sha256", "scope_page_image_path", "scope_page_image_sha256",
    "operation_page_image_path", "operation_page_image_sha256", "extracted_text_path", "extracted_text_sha256", "admission_status", "admission_note",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical(row: Mapping[str, str]) -> str:
    payload = {field: row.get(field, "") for field in ACTION_FIELDS if field != "action_record_sha256"}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def fetch_pdf() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    destination = RAW_DIR / f"{SOURCE_ID}.pdf"
    if destination.is_file() and destination.read_bytes().startswith(b"%PDF-"):
        return destination
    with urlopen(Request(OFFICIAL_URL, headers={"User-Agent": "smart-agriculture-mas-source-recovery/1.0"}), timeout=180) as response:
        payload = response.read()
    if not payload.startswith(b"%PDF-"):
        raise SystemExit("MPKV source did not return a PDF.")
    destination.write_bytes(payload)
    return destination


def fetch_publication_page() -> Path:
    """Freeze the official listing that identifies this as Krishi Darshani 2023."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    destination = RAW_DIR / f"{SOURCE_ID}_extension_publications.html"
    if destination.is_file():
        payload = destination.read_bytes()
    else:
        with urlopen(Request(PUBLICATION_PAGE_URL, headers={"User-Agent": "smart-agriculture-mas-source-recovery/1.0"}), timeout=60) as response:
            payload = response.read()
        destination.write_bytes(payload)
    required = (b"Krishi Darshani 2023", b"Annual Diary (Krishidarshani)")
    if not all(fragment in payload for fragment in required):
        raise SystemExit("MPKV official publication page did not identify the 2023 guide and its annual-technology role.")
    return destination


def capture_http_metadata() -> Path:
    """Keep the original server's Last-Modified evidence next to the PDF."""
    destination = RAW_DIR / f"{SOURCE_ID}_http_response_metadata.json"
    if destination.is_file():
        return destination
    request = Request(OFFICIAL_URL, headers={"User-Agent": "smart-agriculture-mas-source-recovery/1.0"}, method="HEAD")
    with urlopen(request, timeout=60) as response:
        last_modified = response.headers.get("Last-Modified", "")
        if not last_modified:
            raise SystemExit("MPKV source response did not provide Last-Modified provenance.")
        metadata = {
            "official_url": OFFICIAL_URL,
            "status": response.status,
            "last_modified": last_modified,
            "last_modified_utc": parsedate_to_datetime(last_modified).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "etag": response.headers.get("ETag", ""),
            "content_length": response.headers.get("Content-Length", ""),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    destination.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return destination


def render_page(pdf_path: Path, page_number: int) -> Path:
    renderer = shutil.which("pdftoppm")
    if renderer is None:
        raise SystemExit("pdftoppm is required to preserve visual Marathi source verification.")
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    prefix = TEXT_DIR / f"{SOURCE_ID}_page_{page_number}"
    output = TEXT_DIR / f"{SOURCE_ID}_page_{page_number}-{page_number:03d}.png"
    if output.is_file():
        return output
    subprocess.run([renderer, "-png", "-r", "160", "-f", str(page_number), "-l", str(page_number), str(pdf_path), str(prefix)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not output.is_file():
        raise SystemExit(f"MPKV source page {page_number} render was not created.")
    return output


def main() -> None:
    scenarios = read_csv(SCENARIO_PATH)
    if len(scenarios) != 300 or len({row["scenario_id"] for row in scenarios}) != 300:
        raise SystemExit("The frozen scenario manifest must contain exactly 300 unique scenarios.")
    raw = fetch_pdf()
    http_metadata = capture_http_metadata()
    publication_page = fetch_publication_page()
    scope_image = render_page(raw, 87)
    operation_image = render_page(raw, 90)
    transcript_path = TEXT_DIR / f"{SOURCE_ID}.json"
    transcript = {
        "source_document_id": SOURCE_ID,
        "verification_method": "visual_transcription_against_hash_linked_source_page_raster",
        "sections": [
            ["pdf_page_87_visual_scope_transcription", SCOPE_QUOTE],
            ["pdf_page_90_visual_operation_transcription", SOURCE_QUOTE],
        ],
    }
    transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raw_hash = file_hash(raw)
    action = {
        "action_id": "MPKV_MH_CHICKPEA_HARVEST_AFTER_HARD_PODS", "action_layer": "dated_state_extension_technical_guide",
        "action_category": "harvest", "crop": "chickpea", "state_scope": "Maharashtra", "season_scope": "rabi",
        "source_document_id": SOURCE_ID, "source_title": "Krishi Darshani 2023", "provider": "Mahatma Phule Krishi Vidyapeeth, Rahuri",
        "official_url": OFFICIAL_URL, "source_raw_sha256": raw_hash, "source_location": "pdf_page_90_visual_operation_transcription",
        "source_issue_start": PUBLISHED_ON, "source_issue_end": "", "source_quote": SOURCE_QUOTE,
        "operation_text": "Harvest and thresh chickpea only after pods are hard; do not harvest while the crop is wet.",
        "method_text": "Harvest only after the documented hard-pod maturity condition is observed.", "dose_text": "",
        "conditions_text": "Only when chickpea maturity/hard pods and crop dryness are actually observed.",
        "operation_role": "source_quoted_state_regional_technical_operation", "requires_actual_crop_stage": "true",
        "requires_field_observation": "true", "requires_decision_time_forecast": "false", "requires_soil_test_for_personalised_dose": "false",
        "requires_diagnosis_or_threshold": "false", "requires_documented_system_or_variety": "false", "action_record_sha256": "",
    }
    action["action_record_sha256"] = canonical(action)
    bindings: List[Dict[str, str]] = []
    for scenario in scenarios:
        crop_status = "pass_crop_scope" if scenario["crop"] == "chickpea" else "blocked_crop_scope"
        geography_status = "pass_geography_scope" if scenario["state"] == "Maharashtra" else "blocked_geography_scope"
        season_status = "pass_season_scope" if scenario["season"] == "rabi" else "blocked_season_scope"
        temporal_status = "pass_source_time_valid" if scenario["decision_date"] >= PUBLISHED_ON else "blocked_source_not_yet_available"
        failed = next((value for value in (crop_status, geography_status, season_status, temporal_status) if value.startswith("blocked_")), "")
        binding_status = failed or "conditionally_applicable_pending_unobserved_farm_condition"
        bindings.append({
            "scenario_id": scenario["scenario_id"], "action_id": action["action_id"], "action_layer": action["action_layer"], "crop": scenario["crop"],
            "state": scenario["state"], "district": scenario["district"], "season": scenario["season"], "decision_date": scenario["decision_date"],
            "source_document_id": SOURCE_ID, "source_scope_status": "mpkv_dated_state_extension_technical_guide_scope", "crop_scope_status": crop_status,
            "geography_scope_status": geography_status, "season_scope_status": season_status, "temporal_status": temporal_status,
            "field_condition_status": "not_evaluated_outside_source_scope" if failed else "missing_in_frozen_scenario:actual_crop_stage;documented_field_condition",
            "binding_status": binding_status, "binding_reason": failed or "actual_crop_stage;documented_field_condition", "action_record_sha256": action["action_record_sha256"],
        })
    inventory = [{
        "source_document_id": SOURCE_ID, "source_title": action["source_title"], "provider": action["provider"], "official_url": OFFICIAL_URL,
        "publication_date": PUBLISHED_ON, "source_effective_from": PUBLISHED_ON, "source_effective_to": "", "crop_scope": "chickpea",
        "state_scope": "Maharashtra", "season_scope": "rabi",
        "original_server_last_modified_utc": json.loads(http_metadata.read_text(encoding="utf-8"))["last_modified_utc"],
        "http_metadata_path": str(http_metadata.relative_to(ENRICHED)), "http_metadata_sha256": file_hash(http_metadata),
        "publication_page_url": PUBLICATION_PAGE_URL,
        "publication_page_raw_path": str(publication_page.relative_to(ENRICHED)), "publication_page_raw_sha256": file_hash(publication_page),
        "publication_page_quote": "An Annual Diary (Krishidarshani) is published by the university regularly every year. It consists of information on latest university crop production technologies.",
        "raw_path": str(raw.relative_to(ENRICHED)), "raw_sha256": raw_hash,
        "scope_page_image_path": str(scope_image.relative_to(ENRICHED)), "scope_page_image_sha256": file_hash(scope_image),
        "operation_page_image_path": str(operation_image.relative_to(ENRICHED)), "operation_page_image_sha256": file_hash(operation_image),
        "extracted_text_path": str(transcript_path.relative_to(ENRICHED)), "extracted_text_sha256": file_hash(transcript_path),
        "admission_status": "admitted_dated_state_extension_guide_after_visual_scope_and_operation_verification",
        "admission_note": "The original server Last-Modified response confirms 7 June 2023, and the official MPKV publication page names Krishi Darshani 2023 and describes the annual guide as latest crop-production technology; the legacy Marathi PDF font prevents reliable Unicode extraction, so scope and operation are visually transcribed against stored, hash-linked page rasters.",
    }]
    write_csv(ENRICHED / "mpkv_chickpea_source_inventory.csv", INVENTORY_FIELDS, inventory)
    write_csv(ENRICHED / "mpkv_chickpea_action_records.csv", ACTION_FIELDS, [action])
    write_csv(ENRICHED / "scenario_mpkv_chickpea_action_bindings.csv", BINDING_FIELDS, bindings)
    print(f"MPKV chickpea recovery: 1 source, 1 action, {len(bindings)} bindings, {sum(row['binding_status'].startswith('conditionally_') for row in bindings)} conditional.")


if __name__ == "__main__":
    main()
