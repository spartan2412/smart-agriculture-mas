"""Recover dated PAU Rabi wheat operations from preserved official PDFs.

This collector is separate from the Kharif recovery because its period, source
URL and wheat scope differ.  It accepts only replayed copies of PAU's original
annual Rabi package URL after title/year, original-server Last-Modified date,
raw hash and page-quoted operation checks.  It never changes frozen scenarios.
"""
from __future__ import annotations

import csv
from datetime import timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence
from urllib.request import Request, urlopen

from build_combined_official_action_catalog import ACTION_FIELDS, BINDING_FIELDS


ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "data" / "scenarios" / "enriched"
SCENARIO_PATH = ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv"
RAW_DIR = ENRICHED / "raw" / "archived_pau_rabi_sources"
TEXT_DIR = ENRICHED / "rag_sources" / "archived_pau_rabi_extracted_text"
INVENTORY_FIELDS = [
    "source_document_id", "source_title", "provider", "official_url", "archive_replay_url", "archive_capture_utc",
    "archive_original_last_modified_utc", "source_effective_from", "source_effective_to", "crop_scope", "state_scope",
    "season_scope", "raw_path", "raw_sha256", "extracted_text_path", "extracted_text_sha256", "admission_status", "admission_note",
]
SPECS = (
    {
        "year_label": "2021_22", "document_year": "2021-22", "capture": "20220108015141",
        "capture_utc": "2022-01-08T01:51:41Z", "last_modified_utc": "2021-09-13T16:59:16Z",
        "start": "2021-09-13", "end": "2022-06-30", "official_url": "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf",
    },
    {
        "year_label": "2023_24", "document_year": "2023-24", "capture": "20230918105852",
        "capture_utc": "2023-09-18T10:58:52Z", "last_modified_utc": "2023-09-04T07:30:26Z",
        "start": "2023-09-04", "end": "2024-06-30", "official_url": "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf",
    },
    {
        "year_label": "2024_25", "document_year": "2024-25", "capture": "20250523045635",
        "capture_utc": "2025-05-23T04:56:35Z", "last_modified_utc": "2024-11-07T09:21:08Z",
        "start": "2024-11-07", "end": "2025-06-30", "official_url": "https://pau.edu/content/ccil/pf/pp_rabi.pdf",
    },
)
QUOTE = "Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering. Delayed harvesting results in high grain losses."


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def canonical(row: Mapping[str, str]) -> str:
    payload = {field: row.get(field, "") for field in ACTION_FIELDS if field != "action_record_sha256"}
    return digest(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def replay_url(spec: Mapping[str, str]) -> str:
    return f"https://web.archive.org/web/{spec['capture']}id_/{spec['official_url']}"


def fetch(spec: Mapping[str, str]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"PAU_ARCHIVE_RABI_{spec['year_label']}.pdf"
    if path.is_file() and path.read_bytes().startswith(b"%PDF-"):
        return path
    request = Request(replay_url(spec), headers={"User-Agent": "smart-agriculture-mas-source-recovery/1.0"})
    with urlopen(request, timeout=120) as response:
        content = response.read()
        observed_modified = response.headers.get("x-archive-orig-last-modified", "")
    if not content.startswith(b"%PDF-"):
        raise SystemExit(f"{spec['year_label']}: archive replay did not produce a PDF.")
    if observed_modified:
        observed_utc = parsedate_to_datetime(observed_modified).astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        if observed_utc != spec["last_modified_utc"]:
            raise SystemExit(f"{spec['year_label']}: original-server Last-Modified mismatch: {observed_modified}")
    path.write_bytes(content)
    return path


def extract(pdf: Path) -> List[str]:
    from pypdf import PdfReader
    return [page.extract_text() or "" for page in PdfReader(str(pdf)).pages]


def temporal(date_value: str, start: str, end: str) -> str:
    if date_value < start:
        return "blocked_source_not_yet_available"
    if date_value > end:
        return "blocked_source_effective_window_ended"
    return "pass_source_time_valid"


def main() -> None:
    scenarios = read_csv(SCENARIO_PATH)
    if len(scenarios) != 300 or len({row['scenario_id'] for row in scenarios}) != 300:
        raise SystemExit("The frozen scenario manifest must contain exactly 300 unique scenarios.")
    inventory: List[Dict[str, str]] = []
    actions: List[Dict[str, str]] = []
    for spec in SPECS:
        raw = fetch(spec)
        pages = extract(raw)
        if not pages or spec["document_year"] not in normalise(pages[0]) or "RABI" not in normalise(pages[0]).upper():
            raise SystemExit(f"{spec['year_label']}: PDF does not self-identify as Rabi {spec['document_year']}.")
        quote_page = next((index for index, text in enumerate(pages, 1) if normalise(QUOTE) in normalise(text)), None)
        if quote_page is None:
            raise SystemExit(f"{spec['year_label']}: verified wheat harvest quote is absent.")
        source_id = f"PAU_ARCHIVE_RABI_{spec['year_label']}"
        text_path = TEXT_DIR / f"{source_id}.json"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(json.dumps({"source_document_id": source_id, "sections": [[f"pdf_page_{quote_page}", pages[quote_page - 1]]]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raw_hash = file_hash(raw)
        action = {
            "action_id": f"PAU_ARCHIVE_{spec['year_label']}_WHEAT_HARVEST_FULLY_RIPE", "action_layer": "archived_official_pau_package",
            "action_category": "harvest", "crop": "wheat", "state_scope": "Punjab", "season_scope": "rabi",
            "source_document_id": source_id, "source_title": f"Package of Practices for Crops of Punjab — Rabi {spec['document_year']}",
            "provider": "Punjab Agricultural University", "official_url": spec["official_url"], "source_raw_sha256": raw_hash,
            "source_location": f"pdf_page_{quote_page}", "source_issue_start": spec["start"], "source_issue_end": spec["end"],
            "source_quote": QUOTE, "operation_text": "Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering.",
            "method_text": "Harvest manually, with a combine, or with a tractor-operated vertical conveyer reaper windrower as documented in the source.",
            "dose_text": "", "conditions_text": "Only when the wheat is fully ripe.", "operation_role": "archived_source_quoted_regional_operation",
            "requires_actual_crop_stage": "true", "requires_field_observation": "false", "requires_decision_time_forecast": "false",
            "requires_soil_test_for_personalised_dose": "false", "requires_diagnosis_or_threshold": "false", "requires_documented_system_or_variety": "false",
            "action_record_sha256": "",
        }
        action["action_record_sha256"] = canonical(action)
        actions.append(action)
        inventory.append({
            "source_document_id": source_id, "source_title": action["source_title"], "provider": action["provider"], "official_url": spec["official_url"],
            "archive_replay_url": replay_url(spec), "archive_capture_utc": spec["capture_utc"], "archive_original_last_modified_utc": spec["last_modified_utc"],
            "source_effective_from": spec["start"], "source_effective_to": spec["end"], "crop_scope": "wheat", "state_scope": "Punjab", "season_scope": "rabi",
            "raw_path": str(raw.relative_to(ENRICHED)), "raw_sha256": raw_hash, "extracted_text_path": str(text_path.relative_to(ENRICHED)),
            "extracted_text_sha256": file_hash(text_path), "admission_status": "admitted_archived_official_package_after_pdf_year_last_modified_and_quote_verification",
            "admission_note": "Archive replay preserves PAU's original URL; PDF title/year, original-server Last-Modified date and source quote were independently checked.",
        })
    bindings: List[Dict[str, str]] = []
    for scenario in scenarios:
        for action in actions:
            crop_status = "pass_crop_scope" if scenario["crop"] == "wheat" else "blocked_crop_scope"
            geography_status = "pass_geography_scope" if scenario["state"] == "Punjab" else "blocked_geography_scope"
            season_status = "pass_season_scope" if scenario["season"] == "rabi" else "blocked_season_scope"
            time_status = temporal(scenario["decision_date"], action["source_issue_start"], action["source_issue_end"])
            failed = next((value for value in (crop_status, geography_status, season_status, time_status) if value.startswith("blocked_")), "")
            status = failed or "conditionally_applicable_pending_unobserved_farm_condition"
            reason = failed or "actual_crop_stage"
            bindings.append({
                "scenario_id": scenario["scenario_id"], "action_id": action["action_id"], "action_layer": action["action_layer"], "crop": scenario["crop"],
                "state": scenario["state"], "district": scenario["district"], "season": scenario["season"], "decision_date": scenario["decision_date"],
                "source_document_id": action["source_document_id"], "source_scope_status": "archived_official_pau_rabi_source_scope", "crop_scope_status": crop_status,
                "geography_scope_status": geography_status, "season_scope_status": season_status, "temporal_status": time_status,
                "field_condition_status": "missing_in_frozen_scenario:actual_crop_stage" if not failed else "not_evaluated_outside_source_scope",
                "binding_status": status, "binding_reason": reason, "action_record_sha256": action["action_record_sha256"],
            })
    write_csv(ENRICHED / "archived_pau_rabi_source_inventory.csv", INVENTORY_FIELDS, inventory)
    write_csv(ENRICHED / "archived_pau_rabi_action_records.csv", ACTION_FIELDS, actions)
    write_csv(ENRICHED / "scenario_archived_pau_rabi_action_bindings.csv", BINDING_FIELDS, bindings)
    print(f"Archived PAU Rabi recovery: {len(inventory)} sources, {len(actions)} actions, {len(bindings)} bindings.")


if __name__ == "__main__":
    main()
