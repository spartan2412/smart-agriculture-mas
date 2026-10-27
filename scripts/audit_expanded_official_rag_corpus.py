"""Audit the added ICAR-IISR and ICAR-CRIDA official RAG layer."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from expand_official_rag_corpus import SCOPE_FIELDS, is_admitted


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
AUDIT_FIELDS = ["check", "expected", "actual", "result", "detail"]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def check(name: str, expected: int, actual: int, errors: List[str]) -> Dict[str, str]:
    return {"check": name, "expected": str(expected), "actual": str(actual), "result": "pass" if not errors else "fail", "detail": "; ".join(errors[:5]) if errors else "validated"}


def main() -> None:
    inventory = read_csv(ENRICHED / "expanded_official_rag_source_inventory.csv")
    candidates = read_csv(ENRICHED / "expanded_official_rag_source_candidates.csv")
    chunks = read_csv(ENRICHED / "expanded_official_rag_chunks.csv")
    bindings = read_csv(ENRICHED / "scenario_expanded_rag_scope.csv")
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    admitted = [row for row in inventory if is_admitted(row["admission_status"])]
    audit: List[Dict[str, str]] = []

    candidate_errors: List[str] = []
    if len({row["source_document_id"] for row in candidates}) != len(candidates):
        candidate_errors.append("candidate source IDs are not unique")
    if {row["source_document_id"] for row in inventory} != {row["source_document_id"] for row in candidates}:
        candidate_errors.append("inventory does not cover every candidate exactly once")
    audit.append(check("expanded_source_candidate_coverage", len(candidates), len(inventory), candidate_errors))

    source_errors: List[str] = []
    for source in admitted:
        raw = ENRICHED / source["raw_path"]
        extracted = ENRICHED / source["extracted_text_path"]
        if not raw.is_file() or digest(raw) != source["raw_sha256"] or source["raw_sha256"] != source["expected_raw_sha256"]:
            source_errors.append(f"{source['source_document_id']}: raw source hash mismatch")
            continue
        if not extracted.is_file() or digest(extracted) != source["extracted_text_sha256"]:
            source_errors.append(f"{source['source_document_id']}: extracted text hash mismatch")
            continue
        if source["source_family"] == "ICAR_IISR_WEEKLY_ARCHIVE":
            if not source["issue_start"] or not source["issue_end"] or source["issue_start"] > source["issue_end"]:
                source_errors.append(f"{source['source_document_id']}: invalid weekly issue range")
            discovery = ENRICHED / "raw" / "expanded_official_source_discovery" / f"ICAR_IISR_ARCHIVE_{source['issue_start'][:4]}.html"
            if not discovery.is_file() or digest(discovery) != source["discovery_raw_sha256"]:
                source_errors.append(f"{source['source_document_id']}: frozen archive-discovery hash mismatch")
        if source["source_family"] == "ICAR_CRIDA_FINAL_SITE_CCP" and source["evidence_role"] != "historical_district_context_only":
            source_errors.append(f"{source['source_document_id']}: CRIDA role is not context-only")
    chunk_sources = {row["source_document_id"] for row in chunks}
    if chunk_sources != {row["source_document_id"] for row in admitted}:
        source_errors.append("chunk source set differs from admitted source set")
    audit.append(check("expanded_source_hashes_and_roles", len(admitted), len(admitted), source_errors))

    scope_errors: List[str] = []
    expected_pairs = {(scenario["scenario_id"], source["source_document_id"]) for scenario in scenarios for source in admitted}
    actual_pairs = {(row["scenario_id"], row["source_document_id"]) for row in bindings}
    if len(bindings) != len(actual_pairs) or actual_pairs != expected_pairs:
        scope_errors.append("scenario/source Cartesian scope coverage or uniqueness failure")
    for row in bindings:
        if row["rag_scope_status"].startswith("admitted_dated") and not (
            row["crop_scope_status"].startswith("pass_")
            and row["geography_scope_status"].startswith("pass_")
            and row["temporal_status"].startswith("pass_")
        ):
            scope_errors.append("dated advisory admitted despite failing metadata")
            break
        if row["rag_scope_status"] == "admitted_historical_district_context_only" and (
            not row["crop_scope_status"].startswith("pass_") or not row["geography_scope_status"].startswith("pass_")
            or row["temporal_status"] != "not_time_actionable_historical_context_only"
        ):
            scope_errors.append("historical context admitted outside exact crop/district scope")
            break
    admitted_dated = sum(row["rag_scope_status"].startswith("admitted_dated") for row in bindings)
    historical_context = sum(row["rag_scope_status"] == "admitted_historical_district_context_only" for row in bindings)
    audit.append(check("expanded_metadata_filtered_scenario_scope", len(expected_pairs), len(bindings), scope_errors))

    write_csv(ENRICHED / "expanded_official_rag_audit.csv", AUDIT_FIELDS, audit)
    report = [
        "# Expanded Official RAG Corpus Audit\n\n",
        "| Check | Expected | Actual | Result |\n| --- | ---: | ---: | --- |\n",
    ]
    report.extend(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['result']} |\n" for row in audit)
    report.extend([
        "\n## Interpretation\n\n",
        f"- {len(admitted)} of {len(inventory)} candidates were admitted only after source-byte and scope checks.\n",
        f"- The scenario metadata filter admitted {admitted_dated} exact-week IISR advisory bindings and {historical_context} ICAR-CRIDA historical district-context bindings.\n",
        "- Historical ICAR-CRIDA documents are retrieval context, not current advice or farm-specific operations.\n",
        "- Every rejected document remains in the inventory with its reason; it does not contribute chunks or scenario bindings.\n",
    ])
    (ENRICHED / "EXPANDED_OFFICIAL_RAG_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failures = [row for row in audit if row["result"] != "pass"]
    print(f"Expanded official RAG audit: {len(audit) - len(failures)}/{len(audit)} checks passed; {len(admitted)} admitted sources; {admitted_dated} dated and {historical_context} context bindings.")
    if failures:
        raise SystemExit("Expanded official RAG audit failure; inspect expanded_official_rag_audit.csv.")


if __name__ == "__main__":
    main()
