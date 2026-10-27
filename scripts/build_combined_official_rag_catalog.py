"""Create one normalized, metadata-first view over both official RAG layers."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from expand_official_rag_corpus import is_admitted


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
CATALOG_FIELDS = [
    "source_document_id", "corpus_layer", "source_title", "provider", "source_class", "evidence_role",
    "geography_scope", "crop_scope", "management_scope", "official_url", "issue_start", "issue_end",
    "source_period", "source_date_precision", "raw_path", "source_raw_sha256", "extracted_text_path",
    "extracted_text_sha256", "admission_status", "usage_restriction",
]
CHUNK_FIELDS = [
    "chunk_id", "source_document_id", "corpus_layer", "source_title", "provider", "source_class", "evidence_role",
    "geography_scope", "crop_scope", "management_scope", "official_url", "issue_start", "issue_end",
    "source_period", "location", "chunk_index", "text", "source_raw_sha256",
]
SCOPE_FIELDS = [
    "scenario_id", "source_document_id", "corpus_layer", "crop", "state", "district", "season", "decision_date",
    "evidence_role", "crop_scope_status", "geography_scope_status", "temporal_status", "rag_scope_status", "restriction_reason",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    base_sources = [row for row in read_csv(ENRICHED / "official_rag_source_inventory.csv") if row["retrieval_status"].endswith("_admitted_to_rag")]
    expanded_sources = [row for row in read_csv(ENRICHED / "expanded_official_rag_source_inventory.csv") if is_admitted(row["admission_status"])]
    catalog: List[Dict[str, str]] = []
    for row in base_sources:
        role = "regulatory_lookup_only" if row["source_class"] == "national_regulatory_record" else "frozen_regional_policy_context"
        restriction = "Registration/label context only; never a treatment recommendation." if role == "regulatory_lookup_only" else "Apply the existing crop, registry-geography and effective-date metadata gate before ranking."
        catalog.append({
            "source_document_id": row["source_document_id"], "corpus_layer": "initial_verified_action_rag",
            "source_title": row["source_title"], "provider": row["provider"], "source_class": row["source_class"],
            "evidence_role": role, "geography_scope": row["geography_scope"], "crop_scope": row["crop_scope"],
            "management_scope": row["management_scope"], "official_url": row["official_url"],
            "issue_start": row["source_latest_possible_date"], "issue_end": "", "source_period": row["expected_issue_date"],
            "source_date_precision": row["source_date_precision"], "raw_path": row["raw_path"], "source_raw_sha256": row["raw_sha256"],
            "extracted_text_path": row["extracted_text_path"], "extracted_text_sha256": row["extracted_text_sha256"],
            "admission_status": row["retrieval_status"], "usage_restriction": restriction,
        })
    for row in expanded_sources:
        restriction = "Exact issue week, crop and Central-Zone state must pass before ranking." if row["evidence_role"] == "dated_weekly_advisory" else "Historical district context only; never current advice or a direct farm operation."
        catalog.append({
            "source_document_id": row["source_document_id"], "corpus_layer": "expanded_icariisr_crida",
            "source_title": row["source_title"], "provider": row["provider"], "source_class": row["source_class"],
            "evidence_role": row["evidence_role"], "geography_scope": row["geography_scope"], "crop_scope": row["crop_scope"],
            "management_scope": row["management_scope"], "official_url": row["official_url"],
            "issue_start": row["issue_start"], "issue_end": row["issue_end"], "source_period": row["source_period"],
            "source_date_precision": row["source_date_precision"], "raw_path": row["raw_path"], "source_raw_sha256": row["raw_sha256"],
            "extracted_text_path": row["extracted_text_path"], "extracted_text_sha256": row["extracted_text_sha256"],
            "admission_status": row["admission_status"], "usage_restriction": restriction,
        })
    if len({row["source_document_id"] for row in catalog}) != len(catalog):
        raise SystemExit("Source ID collision across official RAG layers.")
    write_csv(ENRICHED / "official_rag_corpus_catalog.csv", CATALOG_FIELDS, catalog)

    chunks: List[Dict[str, str]] = []
    for row in read_csv(ENRICHED / "official_rag_chunks.csv"):
        chunks.append({
            "chunk_id": row["chunk_id"], "source_document_id": row["source_document_id"], "corpus_layer": "initial_verified_action_rag",
            "source_title": row["source_title"], "provider": row["provider"], "source_class": row["source_class"],
            "evidence_role": "regulatory_lookup_only" if row["source_class"] == "national_regulatory_record" else "frozen_regional_policy_context",
            "geography_scope": row["geography_scope"], "crop_scope": row["crop_scope"], "management_scope": row["management_scope"],
            "official_url": row["official_url"], "issue_start": row["source_latest_possible_date"], "issue_end": "", "source_period": row["expected_issue_date"],
            "location": row["location"], "chunk_index": row["chunk_index"], "text": row["text"], "source_raw_sha256": row["source_raw_sha256"],
        })
    for row in read_csv(ENRICHED / "expanded_official_rag_chunks.csv"):
        chunks.append({**row, "corpus_layer": "expanded_icariisr_crida"})
    if len({row["chunk_id"] for row in chunks}) != len(chunks):
        raise SystemExit("Chunk ID collision across official RAG layers.")
    write_csv(ENRICHED / "official_rag_corpus_all_chunks.csv", CHUNK_FIELDS, chunks)

    scope: List[Dict[str, str]] = []
    for row in read_csv(ENRICHED / "scenario_rag_scope.csv"):
        scope.append({
            "scenario_id": row["scenario_id"], "source_document_id": row["source_document_id"], "corpus_layer": "initial_verified_action_rag",
            "crop": row["crop"], "state": row["state"], "district": row["district"], "season": row["season"], "decision_date": row["decision_date"],
            "evidence_role": "regulatory_lookup_only" if row["source_class"] == "national_regulatory_record" else "frozen_regional_policy_context",
            "crop_scope_status": row["crop_scope_status"], "geography_scope_status": row["geography_scope_status"],
            "temporal_status": row["source_temporal_status"], "rag_scope_status": row["rag_scope_status"], "restriction_reason": row["restriction_reason"],
        })
    for row in read_csv(ENRICHED / "scenario_expanded_rag_scope.csv"):
        scope.append({**row, "corpus_layer": "expanded_icariisr_crida", "season": ""})
    if len({(row["scenario_id"], row["source_document_id"]) for row in scope}) != len(scope):
        raise SystemExit("Scenario/source scope collision across official RAG layers.")
    write_csv(ENRICHED / "scenario_official_rag_scope_all.csv", SCOPE_FIELDS, scope)
    print(f"Combined official RAG catalog: {len(catalog)} sources, {len(chunks)} chunks, {len(scope)} metadata-scope rows.")


if __name__ == "__main__":
    main()
