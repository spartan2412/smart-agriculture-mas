"""Collect immutable, official documents for the action-RAG enrichment.

The frozen scenario benchmark is never modified.  This collector only admits
documents already enumerated in the registry's verified source snapshot.  A
download is eligible for the RAG corpus only when its bytes reproduce the
registry's SHA-256 hash.  Newer or changed remote documents are recorded as
hash drift and are deliberately excluded rather than being treated as a
historical source.

The resulting corpus is a *source corpus*, not an action engine: temporal and
crop/location applicability are applied later, per scenario.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence

import requests
from pypdf import PdfReader
from io import BytesIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0 official-action-rag-collector",
    "Accept": "application/pdf,text/html,application/xhtml+xml,*/*;q=0.8",
}
SOURCE_FIELDS = [
    "source_document_id", "source_title", "provider", "source_class", "geography_scope", "crop_scope",
    "management_scope", "official_url", "expected_issue_date", "expected_sha256", "retrieved_at_utc",
    "http_status", "content_type", "raw_path", "raw_sha256", "extracted_text_path", "extracted_text_sha256",
    "source_latest_possible_date", "source_date_precision", "temporal_status", "retrieval_status", "error",
]
CHUNK_FIELDS = [
    "chunk_id", "source_document_id", "source_title", "provider", "source_class", "geography_scope",
    "crop_scope", "management_scope", "official_url", "expected_issue_date", "source_latest_possible_date",
    "location", "chunk_index", "text", "source_raw_sha256",
]
SELECTION_AUDIT_FIELDS = [
    "source_document_id", "source_title", "source_status", "source_class", "crop_scope", "geography_scope",
    "selection_status", "selection_reason",
]


class VisibleTextParser(HTMLParser):
    """Small dependency-free HTML-to-text extractor for official static pages."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.casefold() in {"script", "style", "noscript"}:
            self._hidden_depth += 1
        if tag.casefold() in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1
        if tag.casefold() in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)

    def text(self) -> str:
        return normalise_text(" ".join(self.parts))


def normalise_text(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n[ \t]*\n+", "\n", value)
    return value.strip()


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def source_is_relevant(source: Mapping[str, str], crops: set[str], states: set[str]) -> bool:
    if source["source_class"] == "national_regulatory_record":
        return True
    crop_scope = {value.strip().casefold() for value in source["crop_scope"].split(";") if value.strip()}
    if not crop_scope.intersection(crops):
        return False
    scope = source["geography_scope"].casefold()
    state_terms = {state.casefold() for state in states}
    return "india national" in scope or "central zone" in scope or any(term in scope for term in state_terms)


def parse_latest_possible_date(value: str) -> tuple[str, str]:
    """Return a conservative source-availability date and precision.

    When the registry reports only a year or a month, historical action binding
    may use the source only after the final possible day of that period.  This
    avoids asserting that an undated 2023 document was already available in
    January 2023.
    """
    value = value.strip()
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        return datetime.strptime(value, "%d.%m.%Y").date().isoformat(), "day"
    if re.fullmatch(r"\d{4}", value):
        return date(int(value), 12, 31).isoformat(), "year"
    match = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", value)
    if match:
        try:
            month = list(calendar.month_name).index(match.group(1).title())
        except ValueError:
            return "", "unparseable"
        year = int(match.group(2))
        return date(year, month, calendar.monthrange(year, month)[1]).isoformat(), "month"
    match = re.fullmatch(r"\d{4}[–-]\d{2}", value)
    if match:
        start = int(value[:4])
        return date(start + 1, 6, 30).isoformat(), "season_range"
    return "", "unparseable"


def raw_extension(content_type: str, url: str) -> str:
    if "pdf" in content_type.casefold() or url.casefold().split("?", maxsplit=1)[0].endswith(".pdf"):
        return ".pdf"
    return ".html"


def extract_text(content: bytes, extension: str) -> List[tuple[str, str]]:
    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = normalise_text(page.extract_text() or "")
            if text:
                pages.append((f"pdf_page_{index}", text))
        if not pages:
            raise ValueError("PDF contains no extractable text.")
        return pages
    parser = VisibleTextParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    text = parser.text()
    if not text:
        raise ValueError("HTML contains no visible extractable text.")
    return [("html_document", text)]


def chunk_text(text: str, size: int = 1200) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    current: List[str] = []
    current_length = 0
    for word in words:
        projected = current_length + len(word) + (1 if current else 0)
        if current and projected > size:
            chunks.append(" ".join(current))
            current, current_length = [], 0
        current.append(word)
        current_length += len(word) + (1 if current_length else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks


def safe_source_stem(source_id: str) -> str:
    if not re.fullmatch(r"[A-Z0-9_]+", source_id):
        raise ValueError(f"Unsafe source identifier: {source_id!r}")
    return source_id


def admit_verified_content(
    source: Mapping[str, str], record: Dict[str, str], content: bytes, extension: str,
    out_dir: Path, retrieval_status: str,
) -> tuple[Dict[str, str], List[Dict[str, str]]]:
    """Persist and extract source bytes whose hash already matches the registry.

    A previously verified local raw copy is an immutable cache, not a substitute
    for source verification: it is admitted only when its SHA-256 equals the
    frozen hash in the registry.  This preserves reproducibility when an
    official host is temporarily unavailable or has an invalid TLS certificate.
    """
    source_id = source["source_document_id"]
    stem = safe_source_stem(source_id)
    actual_hash = sha256(content).hexdigest()
    if actual_hash != source["sha256"]:
        raise ValueError("source bytes differ from the frozen registry source hash")
    raw_relative = Path("raw") / "official_rag_sources" / f"{stem}{extension}"
    raw_path = out_dir / raw_relative
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)
    sections = extract_text(content, extension)
    text_relative = Path("rag_sources") / "extracted_text" / f"{stem}.json"
    text_path = out_dir / text_relative
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(json.dumps({"source_document_id": source_id, "sections": sections}, ensure_ascii=False), encoding="utf-8")
    record.update({
        "raw_path": str(raw_relative), "raw_sha256": actual_hash,
        "extracted_text_path": str(text_relative),
        "extracted_text_sha256": sha256(text_path.read_bytes()).hexdigest(),
        "retrieval_status": retrieval_status,
    })
    chunks: List[Dict[str, str]] = []
    for location, section_text in sections:
        for index, value in enumerate(chunk_text(section_text), start=1):
            chunks.append({
                "chunk_id": f"{source_id}:{location}:{index:03d}",
                "source_document_id": source_id,
                "source_title": source["source_title"],
                "provider": source["provider"],
                "source_class": source["source_class"],
                "geography_scope": source["geography_scope"],
                "crop_scope": source["crop_scope"],
                "management_scope": source["management_scope"],
                "official_url": source["official_url"],
                "expected_issue_date": source["expected_issue_date"],
                "source_latest_possible_date": record["source_latest_possible_date"],
                "location": location,
                "chunk_index": str(index), "text": value, "source_raw_sha256": actual_hash,
            })
    return record, chunks


def collect_source(source: Mapping[str, str], out_dir: Path, timeout_s: float) -> tuple[Dict[str, str], List[Dict[str, str]]]:
    source_id = source["source_document_id"]
    stem = safe_source_stem(source_id)
    latest_date, precision = parse_latest_possible_date(source["expected_issue_date"])
    record: Dict[str, str] = {
        "source_document_id": source_id,
        "source_title": source["source_title"],
        "provider": source["provider"],
        "source_class": source["source_class"],
        "geography_scope": source["geography_scope"],
        "crop_scope": source["crop_scope"],
        "management_scope": source["management_scope"],
        "official_url": source["official_url"],
        "expected_issue_date": source["expected_issue_date"],
        "expected_sha256": source["sha256"],
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "http_status": "",
        "content_type": "",
        "raw_path": "",
        "raw_sha256": "",
        "extracted_text_path": "",
        "extracted_text_sha256": "",
        "source_latest_possible_date": latest_date,
        "source_date_precision": precision,
        "temporal_status": "source_date_precision_unavailable" if not latest_date else "source_date_available_for_binding",
        "retrieval_status": "",
        "error": "",
    }
    try:
        response = requests.get(source["official_url"], headers=REQUEST_HEADERS, timeout=timeout_s)
        record["http_status"] = str(response.status_code)
        record["content_type"] = response.headers.get("Content-Type", "")
        response.raise_for_status()
        content = response.content
        actual_hash = sha256(content).hexdigest()
        record["raw_sha256"] = actual_hash
        if actual_hash != source["sha256"]:
            record["retrieval_status"] = "hash_drift_rejected_not_admitted_to_rag"
            record["error"] = "downloaded bytes differ from the frozen registry source hash"
            return record, []
        extension = raw_extension(record["content_type"], source["official_url"])
        return admit_verified_content(
            source, record, content, extension, out_dir, "exact_frozen_hash_verified_admitted_to_rag"
        )
    except (requests.RequestException, ValueError, OSError) as exc:
        extension = raw_extension("", source["official_url"])
        cached_path = out_dir / "raw" / "official_rag_sources" / f"{stem}{extension}"
        if cached_path.is_file():
            try:
                cached_content = cached_path.read_bytes()
                if sha256(cached_content).hexdigest() == source["sha256"]:
                    record["error"] = f"live retrieval failed; immutable cache reverified: {type(exc).__name__}: {exc}"
                    return admit_verified_content(
                        source, record, cached_content, extension, out_dir,
                        "cached_frozen_hash_reverified_admitted_to_rag",
                    )
            except (ValueError, OSError) as cached_exc:
                record["error"] = f"{type(exc).__name__}: {exc}; cache read failed: {type(cached_exc).__name__}: {cached_exc}"
        record["retrieval_status"] = "source_retrieval_or_extraction_failed"
        if not record["error"]:
            record["error"] = f"{type(exc).__name__}: {exc}"
        return record, []


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect hash-verified official documents for the action-RAG corpus.")
    parser.add_argument("--source-snapshot", type=Path, default=PROJECT_ROOT / "data" / "registry" / "regional_management_source_snapshot.csv")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "data" / "scenarios" / "enriched")
    parser.add_argument("--source-id", action="append", help="Collect only an exact source ID; repeatable.")
    parser.add_argument("--timeout-s", type=float, default=90.0)
    args = parser.parse_args()
    if args.timeout_s <= 0:
        raise SystemExit("--timeout-s must be positive.")
    scenarios = read_csv(args.manifest)
    if not scenarios:
        raise SystemExit("Scenario manifest is empty.")
    crops = {row["crop"].casefold() for row in scenarios}
    states = {row["state"] for row in scenarios}
    requested = set(args.source_id or [])
    snapshot = read_csv(args.source_snapshot)
    selection_audit: List[Dict[str, str]] = []
    for row in snapshot:
        if row["source_status"] != "dated_source_semantics_verified":
            status, reason = "excluded_registry_source_status", row["source_status"]
        elif source_is_relevant(row, crops, states):
            status, reason = "selected_for_hash_verified_retrieval", "crop and registry geography overlap the study"
        else:
            status, reason = "excluded_outside_study_scope", "no crop and registry-geography overlap with the study"
        selection_audit.append({
            "source_document_id": row["source_document_id"], "source_title": row["source_title"],
            "source_status": row["source_status"], "source_class": row["source_class"], "crop_scope": row["crop_scope"],
            "geography_scope": row["geography_scope"], "selection_status": status, "selection_reason": reason,
        })
    sources = [row for row in snapshot if row["source_status"] == "dated_source_semantics_verified" and source_is_relevant(row, crops, states)]
    if requested:
        sources = [row for row in sources if row["source_document_id"] in requested]
        missing = requested - {row["source_document_id"] for row in sources}
        if missing:
            raise SystemExit(f"Unknown or inapplicable source ID(s): {', '.join(sorted(missing))}")
    if not sources:
        raise SystemExit("No verified, relevant official sources selected.")
    records, chunks = [], []
    for index, source in enumerate(sources, start=1):
        record, source_chunks = collect_source(source, args.out_dir, args.timeout_s)
        records.append(record)
        chunks.extend(source_chunks)
        print(f"[{index}/{len(sources)}] {source['source_document_id']}: {record['retrieval_status']}")
    write_csv(args.out_dir / "official_rag_source_inventory.csv", SOURCE_FIELDS, records)
    write_csv(args.out_dir / "official_rag_chunks.csv", CHUNK_FIELDS, chunks)
    write_csv(args.out_dir / "official_rag_source_selection_audit.csv", SELECTION_AUDIT_FIELDS, selection_audit)
    admitted = sum(row["retrieval_status"].endswith("_admitted_to_rag") for row in records)
    print(f"Official source corpus availability: {admitted}/{len(records)} verified documents; {len(chunks)} chunks.")
    if not admitted:
        raise SystemExit("No source documents were admitted to the RAG corpus.")


if __name__ == "__main__":
    main()
