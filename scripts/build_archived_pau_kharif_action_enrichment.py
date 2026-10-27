"""Recover time-valid PAU Kharif rice operations without changing scenarios.

The primary PAU Package of Practices URL is overwritten annually.  This
collector uses publicly replayable Internet Archive captures of that *same*
official URL only when the recovered PDF independently identifies its Kharif
year and its quoted page text.  The archive is preservation infrastructure,
not a substitute publisher: each output retains the original PAU URL, replay
URL, capture timestamp and SHA-256.

The resulting actions remain conditional on observed crop maturity.  No row
is a farm-specific instruction and this script never writes a scenario
manifest, registry record, weather record, or other frozen evidence.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence
from urllib.request import Request, urlopen

from build_combined_official_action_catalog import ACTION_FIELDS, BINDING_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = PROJECT_ROOT / "data" / "scenarios"
ENRICHED = SCENARIOS / "enriched"
RAW_DIR = ENRICHED / "raw" / "archived_pau_kharif_sources"
TEXT_DIR = ENRICHED / "rag_sources" / "archived_pau_kharif_extracted_text"

INVENTORY_FIELDS = [
    "source_document_id", "source_title", "provider", "official_url", "archive_replay_url", "archive_capture_utc",
    "source_effective_from", "source_effective_to", "crop_scope", "state_scope", "season_scope", "raw_path",
    "raw_sha256", "extracted_text_path", "extracted_text_sha256", "admission_status", "admission_note",
]
SOURCE_SPECS = (
    {
        "year": "2023", "capture": "20230918105856", "effective_from": "2023-09-18",
        "effective_to": "2023-12-31", "capture_utc": "2023-09-18T10:58:56Z",
    },
    {
        "year": "2024", "capture": "20240830235813", "effective_from": "2024-08-30",
        "effective_to": "2024-12-31", "capture_utc": "2024-08-30T23:58:13Z",
    },
    {
        "year": "2025", "capture": "20250626143125", "effective_from": "2025-06-26",
        "effective_to": "2025-12-31", "capture_utc": "2025-06-26T14:31:25Z",
    },
)
OFFICIAL_URL = "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def canonical_hash(row: Mapping[str, str], fields: Sequence[str], digest_field: str = "action_record_sha256") -> str:
    payload = {field: row.get(field, "") for field in fields if field != digest_field}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return digest_bytes(encoded)


def replay_url(capture: str) -> str:
    return f"https://web.archive.org/web/{capture}id_/{OFFICIAL_URL}"


def fetch_pdf(spec: Mapping[str, str]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    destination = RAW_DIR / f"PAU_ARCHIVE_KHARIF_{spec['year']}.pdf"
    if destination.is_file() and destination.read_bytes().startswith(b"%PDF-"):
        return destination
    request = Request(replay_url(spec["capture"]), headers={"User-Agent": "smart-agriculture-mas-source-recovery/1.0"})
    with urlopen(request, timeout=90) as response:
        payload = response.read()
    # One preserved response is a gzip member even though the replay content is a PDF.
    if payload.startswith(b"\x1f\x8b"):
        payload = gzip.decompress(payload)
    if not payload.startswith(b"%PDF-"):
        raise SystemExit(f"{spec['year']}: archive replay did not yield a PDF.")
    destination.write_bytes(payload)
    return destination


def extract_pages(pdf_path: Path) -> List[str]:
    try:
        from pypdf import PdfReader
    except ImportError as error:  # pragma: no cover - environment setup error
        raise SystemExit("pypdf is required for archive source verification.") from error
    return [page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages]


def source_actions(spec: Mapping[str, str], source_hash: str) -> List[Dict[str, str]]:
    source_id = f"PAU_ARCHIVE_KHARIF_{spec['year']}"
    title = f"Package of Practices for Crops of Punjab — Kharif {spec['year']}"
    shared = {
        "crop": "rice", "state_scope": "Punjab", "season_scope": "kharif", "source_document_id": source_id,
        "source_title": title, "provider": "Punjab Agricultural University", "official_url": OFFICIAL_URL,
        "source_raw_sha256": source_hash, "source_issue_start": spec["effective_from"],
        "source_issue_end": spec["effective_to"], "requires_actual_crop_stage": "true",
        "requires_field_observation": "false", "requires_decision_time_forecast": "false",
        "requires_soil_test_for_personalised_dose": "false", "requires_diagnosis_or_threshold": "false",
        "requires_documented_system_or_variety": "false", "action_layer": "archived_official_pau_package",
    }
    specs = (
        (
            "RICE_STOP_IRRIGATION_PRE_MATURITY", "irrigation", "Stop irrigation about a fortnight before maturity.",
            "Stop irrigation about a fortnight before maturity.", "", "",
            "Only when the crop is about a fortnight before maturity.",
        ),
        (
            "RICE_HARVEST_AT_PROPER_MATURITY", "harvest",
            "Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.",
            "Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.",
            "Avoid harvesting during night.", "", "Only when proper maturity is observed for the variety.",
        ),
    )
    rows: List[Dict[str, str]] = []
    for suffix, category, quote, operation, method, dose, conditions in specs:
        row = {
            **shared, "action_id": f"PAU_ARCHIVE_{spec['year']}_{suffix}", "action_category": category,
            "source_location": "pdf_page_11", "source_quote": quote, "operation_text": operation,
            "method_text": method, "dose_text": dose, "conditions_text": conditions, "operation_role": "archived_source_quoted_regional_operation",
            "action_record_sha256": "",
        }
        row["action_record_sha256"] = canonical_hash(row, ACTION_FIELDS)
        rows.append(row)
    return rows


def temporal_status(decision_date: str, start: str, end: str) -> str:
    if decision_date < start:
        return "blocked_source_not_yet_available"
    if decision_date > end:
        return "blocked_source_effective_window_ended"
    return "pass_source_time_valid"


def build_bindings(scenarios: Sequence[Mapping[str, str]], actions: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for scenario in scenarios:
        for action in actions:
            crop_status = "pass_crop_scope" if scenario["crop"] == action["crop"] else "blocked_crop_scope"
            geography_status = "pass_geography_scope" if scenario["state"] == action["state_scope"] else "blocked_geography_scope"
            season_status = "pass_season_scope" if scenario["season"] == action["season_scope"] else "blocked_season_scope"
            source_time = temporal_status(scenario["decision_date"], action["source_issue_start"], action["source_issue_end"])
            statuses = (crop_status, geography_status, season_status, source_time)
            blocked = next((status for status in statuses if status.startswith("blocked_")), "")
            if blocked:
                binding_status, reason, field_status = blocked, blocked, "not_evaluated_outside_source_scope"
            else:
                binding_status = "conditionally_applicable_pending_unobserved_farm_condition"
                reason, field_status = "actual_crop_stage", "missing_in_frozen_scenario:actual_crop_stage"
            rows.append({
                "scenario_id": scenario["scenario_id"], "action_id": action["action_id"], "action_layer": action["action_layer"],
                "crop": scenario["crop"], "state": scenario["state"], "district": scenario["district"], "season": scenario["season"],
                "decision_date": scenario["decision_date"], "source_document_id": action["source_document_id"],
                "source_scope_status": "archived_official_pau_kharif_source_scope", "crop_scope_status": crop_status,
                "geography_scope_status": geography_status, "season_scope_status": season_status, "temporal_status": source_time,
                "field_condition_status": field_status, "binding_status": binding_status, "binding_reason": reason,
                "action_record_sha256": action["action_record_sha256"],
            })
    return rows


def main() -> None:
    scenarios = read_csv(SCENARIOS / "manifests" / "scenario_manifest.csv")
    if len(scenarios) != 300 or len({row["scenario_id"] for row in scenarios}) != len(scenarios):
        raise SystemExit("The frozen scenario manifest must contain exactly 300 unique scenarios.")
    inventory: List[Dict[str, str]] = []
    actions: List[Dict[str, str]] = []
    for spec in SOURCE_SPECS:
        pdf_path = fetch_pdf(spec)
        pages = extract_pages(pdf_path)
        title_text = normalise(pages[0] if pages else "")
        if "KHARIF" not in title_text.upper() or spec["year"] not in title_text:
            raise SystemExit(f"{spec['year']}: recovered PDF does not self-identify as Kharif {spec['year']}.")
        if len(pages) < 11:
            raise SystemExit(f"{spec['year']}: recovered PDF lacks verified rice operation page.")
        page_text = pages[10]
        for quote in (
            "Stop irrigation about a fortnight before maturity.",
            "Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.",
        ):
            if normalise(quote) not in normalise(page_text):
                raise SystemExit(f"{spec['year']}: source quote absent from PDF page 11: {quote}")
        source_id = f"PAU_ARCHIVE_KHARIF_{spec['year']}"
        extracted_path = TEXT_DIR / f"{source_id}.json"
        extracted_path.parent.mkdir(parents=True, exist_ok=True)
        extracted_path.write_text(json.dumps({"source_document_id": source_id, "sections": [["pdf_page_11", page_text]]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raw_hash = file_sha256(pdf_path)
        inventory.append({
            "source_document_id": source_id, "source_title": f"Package of Practices for Crops of Punjab — Kharif {spec['year']}",
            "provider": "Punjab Agricultural University", "official_url": OFFICIAL_URL, "archive_replay_url": replay_url(spec["capture"]),
            "archive_capture_utc": spec["capture_utc"], "source_effective_from": spec["effective_from"], "source_effective_to": spec["effective_to"],
            "crop_scope": "rice", "state_scope": "Punjab", "season_scope": "kharif", "raw_path": str(pdf_path.relative_to(ENRICHED)),
            "raw_sha256": raw_hash, "extracted_text_path": str(extracted_path.relative_to(ENRICHED)),
            "extracted_text_sha256": file_sha256(extracted_path), "admission_status": "admitted_archived_official_package_after_pdf_year_and_quote_verification",
            "admission_note": "Archive replay preserves PAU's original official URL; PDF title/year and page-11 source quotes were independently checked.",
        })
        actions.extend(source_actions(spec, raw_hash))
    if len(actions) != 6 or len({row["action_id"] for row in actions}) != 6:
        raise SystemExit("Unexpected archived PAU action catalog size or duplicate action ID.")
    bindings = build_bindings(scenarios, actions)
    if len(bindings) != len(scenarios) * len(actions):
        raise SystemExit("Archived PAU binding coverage is incomplete.")
    write_csv(ENRICHED / "archived_pau_kharif_source_inventory.csv", INVENTORY_FIELDS, inventory)
    write_csv(ENRICHED / "archived_pau_kharif_action_records.csv", ACTION_FIELDS, actions)
    write_csv(ENRICHED / "scenario_archived_pau_kharif_action_bindings.csv", BINDING_FIELDS, bindings)
    print(f"Archived PAU Kharif recovery: {len(inventory)} sources, {len(actions)} actions, {len(bindings)} bindings.")


if __name__ == "__main__":
    main()
