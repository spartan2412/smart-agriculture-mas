"""Independently audit the MPKV Maharashtra chickpea operation layer.

The source PDF has a legacy Marathi font.  Rather than trust garbled text
extraction, this audit verifies the original PDF, the exact rendered pages,
and the deliberately small visual-transcription record that is cited by the
action.  It also proves that the action never becomes a direct farm action.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "data" / "scenarios" / "enriched"
FIELDS = ["check", "expected", "actual", "result", "detail"]
SOURCE_ID = "MPKV_KRISHI_DARSHANI_2023"
ACTION_ID = "MPKV_MH_CHICKPEA_HARVEST_AFTER_HARD_PODS"
SOURCE_QUOTE = "हरभरा पीक ११० ते १२० दिवसांमध्ये तयार होते. पीक ओलसर असताना काढणी करू नये. घाटे कडक झाल्यानंतर मग हरभऱ्याची काढणी करून मळणी करावी."
EXPECTED_OPERATION = "Harvest and thresh chickpea only after pods are hard; do not harvest while the crop is wet."


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def check(name: str, expected: int | str, actual: int | str, errors: list[str]) -> dict[str, str]:
    return {
        "check": name,
        "expected": str(expected),
        "actual": str(actual),
        "result": "pass" if not errors else "fail",
        "detail": "; ".join(errors[:5]) or "validated",
    }


def main() -> None:
    scenarios = read_csv(ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    inventory = read_csv(ENRICHED / "mpkv_chickpea_source_inventory.csv")
    actions = read_csv(ENRICHED / "mpkv_chickpea_action_records.csv")
    bindings = read_csv(ENRICHED / "scenario_mpkv_chickpea_action_bindings.csv")
    combined_actions = {row["action_id"]: row for row in read_csv(ENRICHED / "official_action_records_all.csv")}
    combined_bindings = {(row["scenario_id"], row["action_id"]): row for row in read_csv(ENRICHED / "scenario_official_action_bindings_all.csv")}
    rows: list[dict[str, str]] = []

    source_errors: list[str] = []
    if len(inventory) != 1 or inventory[0].get("source_document_id") != SOURCE_ID:
        source_errors.append("expected one MPKV Krishi Darshani 2023 source")
    source = inventory[0] if inventory else {}
    for path_key, hash_key in (
        ("http_metadata_path", "http_metadata_sha256"),
        ("publication_page_raw_path", "publication_page_raw_sha256"),
        ("raw_path", "raw_sha256"),
        ("scope_page_image_path", "scope_page_image_sha256"),
        ("operation_page_image_path", "operation_page_image_sha256"),
        ("extracted_text_path", "extracted_text_sha256"),
    ):
        candidate = ENRICHED / source.get(path_key, "")
        if not candidate.is_file() or digest(candidate) != source.get(hash_key, ""):
            source_errors.append(f"{path_key} hash/path mismatch")
    publication_page = ENRICHED / source.get("publication_page_raw_path", "")
    if publication_page.is_file():
        page_text = publication_page.read_text(encoding="utf-8", errors="replace")
        if "Krishi Darshani 2023" not in page_text or "Annual Diary (Krishidarshani)" not in page_text:
            source_errors.append("official publication page does not identify the 2023 annual technology guide")
    metadata = ENRICHED / source.get("http_metadata_path", "")
    if metadata.is_file():
        http = json.loads(metadata.read_text(encoding="utf-8"))
        if http.get("official_url") != source.get("official_url") or http.get("last_modified_utc") != "2023-06-07T11:01:25Z":
            source_errors.append("original-server Last-Modified provenance does not confirm the 7 June 2023 source date")
    if (
        source.get("publication_date") != "2023-06-07"
        or source.get("original_server_last_modified_utc") != "2023-06-07T11:01:25Z"
        or not source.get("official_url", "").startswith("https://mpkv.ac.in/")
        or source.get("publication_page_url") != "https://mpkv.ac.in/Extension/ExtensionPublication"
    ):
        source_errors.append("missing official MPKV publication provenance")
    rows.append(check("official_pdf_and_hash_linked_visual_provenance", 1, len(inventory), source_errors))

    quote_errors: list[str] = []
    transcript: dict[str, object] = {}
    if source:
        transcript = json.loads((ENRICHED / source["extracted_text_path"]).read_text(encoding="utf-8"))
        sections = dict(transcript.get("sections", []))
        if sections.get("pdf_page_90_visual_operation_transcription") != SOURCE_QUOTE:
            quote_errors.append("stored page-90 transcription differs from cited Marathi source passage")
        if not str(transcript.get("verification_method", "")).startswith("visual_transcription_"):
            quote_errors.append("transcription provenance is not explicitly visual")
    if len(actions) != 1 or actions[0].get("action_id") != ACTION_ID:
        quote_errors.append("expected exactly one MPKV chickpea action")
    elif actions[0].get("source_quote") != SOURCE_QUOTE or actions[0].get("operation_text") != EXPECTED_OPERATION:
        quote_errors.append("action quote or faithful English operation differs from verified transcription")
    elif actions[0].get("requires_actual_crop_stage") != "true" or actions[0].get("requires_field_observation") != "true":
        quote_errors.append("maturity/dryness field-condition gates are missing")
    rows.append(check("source_quoted_operation_and_field_condition_gates", 1, len(actions), quote_errors))

    expected_pairs = {(scenario["scenario_id"], ACTION_ID) for scenario in scenarios}
    actual_pairs = {(binding["scenario_id"], binding["action_id"]) for binding in bindings}
    binding_errors: list[str] = []
    if len(scenarios) != 300 or len({scenario["scenario_id"] for scenario in scenarios}) != 300:
        binding_errors.append("frozen scenario universe is not exactly 300 unique records")
    if len(bindings) != len(actual_pairs) or actual_pairs != expected_pairs:
        binding_errors.append("scenario/action Cartesian coverage or uniqueness failure")
    conditionals = [row for row in bindings if row["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition"]
    expected_conditional_ids = {
        scenario["scenario_id"] for scenario in scenarios
        if scenario["crop"] == "chickpea" and scenario["state"] == "Maharashtra" and scenario["season"] == "rabi" and scenario["decision_date"] >= "2023-06-07"
    }
    if {row["scenario_id"] for row in conditionals} != expected_conditional_ids:
        binding_errors.append("conditional scope is not exactly Maharashtra/chickpea/rabi after publication")
    if any(row["binding_reason"] != "actual_crop_stage;documented_field_condition" for row in conditionals):
        binding_errors.append("conditional MPKV entries lost maturity/dryness gates")
    rows.append(check("full_scope_matrix_and_50_stage_gated_bindings", 300, len(bindings), binding_errors))

    projection_errors: list[str] = []
    if not actions or combined_actions.get(ACTION_ID) != actions[0]:
        projection_errors.append("action changed or missing in combined catalog")
    if not all(combined_bindings.get((row["scenario_id"], row["action_id"])) == row for row in bindings):
        projection_errors.append("binding changed or missing in combined catalog")
    rows.append(check("combined_catalog_projection", 301, int(bool(actions and combined_actions.get(ACTION_ID))) + sum((row["scenario_id"], row["action_id"]) in combined_bindings for row in bindings), projection_errors))

    direct = sum(row["binding_status"] == "source_scoped_eligible" for row in bindings)
    rows.append(check("no_direct_farm_action", 0, direct, [] if direct == 0 else ["unconditionally eligible action found"]))

    audit_path = ENRICHED / "mpkv_chickpea_action_audit.csv"
    with audit_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = ["# MPKV Maharashtra Chickpea Action-Recovery Audit\n\n", "| Check | Expected | Actual | Result |\n| --- | ---: | ---: | --- |\n"]
    report.extend(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['result']} |\n" for row in rows)
    report.extend([
        "\n## Source-verification boundary\n\n",
        "- MPKV's official PDF is retained unchanged with a SHA-256 digest. Its original server response records `Last-Modified: 2023-06-07T11:01:25Z`, and the official publication page names it as Krishi Darshani 2023. The PDF's legacy Marathi font does not yield dependable Unicode extraction.\n",
        "- The admission record therefore retains 160-dpi rasters of the exact statewide-scope and operation pages, each separately hash-checked, and a limited visual transcription of only the cited passages.\n",
        "- The guide is dated 7 June 2023 and is treated as persistent state-level technical guidance after that date, not as a dated weekly advisory.\n",
        "- It binds only Maharashtra chickpea Rabi scenarios and remains conditional on observed hard pods, maturity, and a dry crop; it never becomes a direct farm action.\n",
        "- No frozen scenario was changed.\n",
    ])
    (ENRICHED / "MPKV_CHICKPEA_ACTION_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failures = [row for row in rows if row["result"] != "pass"]
    print(f"MPKV chickpea action-recovery audit: {len(rows) - len(failures)}/{len(rows)} checks passed; {len(conditionals)} conditionally applicable bindings.")
    if failures:
        raise SystemExit("MPKV chickpea action-recovery audit failed.")


if __name__ == "__main__":
    main()
