"""Build a second, provenance-first official RAG layer from public sources.

This deliberately adds two different evidence types without blurring them:

* ICAR-IISR dated weekly soybean advisories.  These can enter retrieval only
  for Central-Zone soybean scenarios inside their stated issue week.
* ICAR-CRIDA district crop-profile, sowing-window and contingency documents
  that the final-site registry already hash-verified.  These are older,
  district-specific context documents; they are never labelled current advice
  and never create a direct farm operation.

The script freezes raw SHA-256 values on first capture.  On a later run it
rejects changed remote bytes and uses a matching local immutable copy when one
exists.  The frozen 300-scenario benchmark and its registry are read only.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence
from urllib.parse import urljoin

import requests

try:  # Support both ``python scripts/name.py`` and package-style test imports.
    from collect_official_rag_sources import REQUEST_HEADERS, chunk_text, extract_text, raw_extension
except ModuleNotFoundError:  # pragma: no cover - exercised by package imports
    from scripts.collect_official_rag_sources import REQUEST_HEADERS, chunk_text, extract_text, raw_extension


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
ARCHIVE_URLS = {
    2021: "https://icar-nsri.res.in/Advisory2021.html",
    2022: "https://icar-nsri.res.in/Advisory2022.html",
    2023: "https://icar-nsri.res.in/Advisory2023.html",
    2024: "https://icar-nsri.res.in/Advisory2024.html",
}
MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
SOURCE_FIELDS = [
    "source_document_id", "source_title", "provider", "source_family", "source_class", "evidence_role",
    "geography_scope", "crop_scope", "management_scope", "official_url", "discovery_url",
    "discovery_raw_sha256", "issue_start", "issue_end", "source_period", "source_date_precision",
    "expected_raw_sha256", "raw_path", "raw_sha256", "extracted_text_path", "extracted_text_sha256",
    "retrieved_at_utc", "http_status", "content_type", "admission_status", "error",
]
CHUNK_FIELDS = [
    "chunk_id", "source_document_id", "source_title", "provider", "source_family", "source_class",
    "evidence_role", "geography_scope", "crop_scope", "management_scope", "official_url", "issue_start",
    "issue_end", "source_period", "location", "chunk_index", "text", "source_raw_sha256",
]
CANDIDATE_FIELDS = [
    "source_document_id", "source_title", "source_family", "source_class", "evidence_role", "geography_scope",
    "crop_scope", "management_scope", "official_url", "discovery_url", "discovery_raw_sha256", "issue_start",
    "issue_end", "source_period", "source_date_precision", "expected_raw_sha256", "candidate_status", "reason",
]
REJECTION_FIELDS = ["source_family", "official_url", "source_label", "rejection_status", "reason"]
SCOPE_FIELDS = [
    "scenario_id", "source_document_id", "crop", "state", "district", "decision_date", "evidence_role",
    "crop_scope_status", "geography_scope_status", "temporal_status", "rag_scope_status", "restriction_reason",
]


class LinkParser(HTMLParser):
    """Dependency-free archive link extractor."""

    def __init__(self) -> None:
        super().__init__()
        self.links: List[tuple[str, str]] = []
        self._href: str | None = None
        self._text: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.casefold() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._href:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def source_stem(value: str) -> str:
    if not re.fullmatch(r"[A-Z0-9_]+", value):
        raise ValueError(f"Unsafe source identifier: {value!r}")
    return value


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def month_number(value: str) -> int:
    key = value.casefold().rstrip(".")
    if key not in MONTHS:
        raise ValueError(f"Unsupported month label {value!r}")
    return MONTHS[key]


def parse_week_range(label: str, year: int) -> tuple[str, str] | None:
    """Parse archive labels such as ``27 Sept- 3 Oct`` conservatively."""
    clean = re.sub(r"\s+", " ", label.replace("–", "-").replace(",", " ")).strip()
    match = re.fullmatch(
        r"(?P<d1>\d{1,2})\s*(?P<m1>[A-Za-z]+)?\s*-\s*(?P<d2>\d{1,2})\s*(?P<m2>[A-Za-z]+)", clean,
    )
    if not match:
        return None
    first_month = match.group("m1") or match.group("m2")
    second_month = match.group("m2") or match.group("m1")
    if not first_month or not second_month:
        return None
    start_month, end_month = month_number(first_month), month_number(second_month)
    start_day, end_day = int(match.group("d1")), int(match.group("d2"))
    try:
        start = date(year, start_month, start_day)
        end_year = year + 1 if end_month < start_month else year
        end = date(end_year, end_month, end_day)
    except ValueError:
        return None
    if end < start or (end - start).days > 8:
        return None
    return start.isoformat(), end.isoformat()


def cached_or_fetched_archive(year: int, archive_url: str, timeout_s: float) -> tuple[bytes, str, str]:
    """Freeze archive-page discovery bytes, refusing a later silent rewrite."""
    target = ENRICHED / "raw" / "expanded_official_source_discovery" / f"ICAR_IISR_ARCHIVE_{year}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    prior = target.read_bytes() if target.is_file() else None
    try:
        response = requests.get(archive_url, headers=REQUEST_HEADERS, timeout=timeout_s)
        response.raise_for_status()
        remote = response.content
        if prior is not None and sha256(remote).hexdigest() != sha256(prior).hexdigest():
            return prior, sha256(prior).hexdigest(), "cached_initial_archive_due_to_remote_hash_drift"
        target.write_bytes(remote)
        return remote, sha256(remote).hexdigest(), "remote_archive_frozen"
    except requests.RequestException:
        if prior is not None:
            return prior, sha256(prior).hexdigest(), "cached_initial_archive_due_to_remote_failure"
        raise


def build_iisr_candidates(timeout_s: float) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    candidates: List[Dict[str, str]] = []
    rejections: List[Dict[str, str]] = []
    seen_urls: set[str] = set()
    for year, archive_url in ARCHIVE_URLS.items():
        content, archive_hash, _ = cached_or_fetched_archive(year, archive_url, timeout_s)
        parser = LinkParser()
        parser.feed(content.decode("utf-8", errors="replace"))
        for label, href in parser.links:
            official_url = urljoin(archive_url, href).replace("\\", "/")
            if not official_url.casefold().endswith(".pdf"):
                continue
            if official_url in seen_urls:
                rejections.append({
                    "source_family": "ICAR_IISR_WEEKLY_ARCHIVE", "official_url": official_url, "source_label": label,
                    "rejection_status": "rejected_duplicate_archive_url", "reason": "The official archive links this same PDF for more than one issue period; no unverified second period is asserted.",
                })
                continue
            # The 2023 archive label says 11-12 while its filename says 11-17.
            # Do not choose between conflicting official strings by assumption.
            if year == 2023 and label == "11-12 September":
                rejections.append({
                    "source_family": "ICAR_IISR_WEEKLY_ARCHIVE", "official_url": official_url, "source_label": label,
                    "rejection_status": "rejected_internally_ambiguous_archive_date", "reason": "Archive label and filename give incompatible issue-end dates.",
                })
                continue
            issue_range = parse_week_range(label, year)
            if issue_range is None:
                rejections.append({
                    "source_family": "ICAR_IISR_WEEKLY_ARCHIVE", "official_url": official_url, "source_label": label,
                    "rejection_status": "rejected_no_exact_week_range", "reason": "A date range could not be parsed without guessing.",
                })
                continue
            seen_urls.add(official_url)
            start, end = issue_range
            candidates.append({
                "source_document_id": f"ICAR_IISR_WEEKLY_SOYBEAN_{start.replace('-', '')}",
                "source_title": f"ICAR-IISR weekly soybean advisory, {label} {year}",
                "provider": "ICAR–Indian Institute of Soybean Research",
                "source_family": "ICAR_IISR_WEEKLY_ARCHIVE", "source_class": "dated_regional_advisory",
                "evidence_role": "dated_weekly_advisory", "geography_scope": "Central soybean zone; Madhya Pradesh and Rajasthan only",
                "crop_scope": "soybean", "management_scope": "crop_establishment;fertilizer;IPM;weather_contingency",
                "official_url": official_url, "discovery_url": archive_url, "discovery_raw_sha256": archive_hash,
                "issue_start": start, "issue_end": end, "source_period": f"{start} to {end}", "source_date_precision": "day_range",
                "expected_raw_sha256": "", "candidate_status": "candidate_from_frozen_official_archive", "reason": "",
            })
    return candidates, rejections


def build_crida_candidates() -> List[Dict[str, str]]:
    rows = read_csv(PROJECT_ROOT / "data" / "registry" / "preflight_icar_crida_ccp_coverage.csv")
    kinds = [
        ("crop_profile", "crop_profile_url", "crop_profile_sha256", "crop_profile_status", "crop_profile_source_period_tokens", "crop profile"),
        ("sowing_window", "sowing_window_url", "sowing_window_sha256", "sowing_window_status", "sowing_window_source_period_tokens", "sowing window"),
        ("contingency", "pest_disease_contingency_url", "pest_disease_contingency_sha256", "pest_disease_contingency_status", "pest_disease_contingency_source_period_tokens", "weather contingency"),
    ]
    grouped: Dict[tuple[str, str, str], List[Dict[str, str]]] = {}
    for row in rows:
        for kind, url_column, hash_column, status_column, _, _ in kinds:
            url, digest, status = row[url_column], row[hash_column], row[status_column]
            if not url or digest in {"", "NONE"} or not status.startswith(("public_pdf_", "historical_official_", "historical_crop_")):
                continue
            grouped.setdefault((kind, url, digest), []).append(row)
    candidates: List[Dict[str, str]] = []
    label_by_kind = {entry[0]: entry[5] for entry in kinds}
    period_column_by_kind = {entry[0]: entry[4] for entry in kinds}
    for (kind, official_url, digest), group in sorted(grouped.items()):
        first = group[0]
        crops = ";".join(sorted({row["crop"] for row in group}))
        sites = ";".join(sorted({row["site_id"] for row in group}))
        period_column = period_column_by_kind[kind]
        periods = sorted({row[period_column] for row in group if row.get(period_column) not in {"", "not_detected"}})
        period = ";".join(periods) if periods else "historical_date_not_extracted"
        identifier = f"ICAR_CRIDA_{first['state_code']}_{slug(first['district'])}_{slug(kind)}"
        candidates.append({
            "source_document_id": identifier,
            "source_title": f"ICAR-CRIDA district {label_by_kind[kind]} document — {first['district']}, {first['state']}",
            "provider": "ICAR–Central Research Institute for Dryland Agriculture",
            "source_family": "ICAR_CRIDA_FINAL_SITE_CCP", "source_class": "district_historical_context",
            "evidence_role": "historical_district_context_only", "geography_scope": f"{first['district']}, {first['state']} district",
            "crop_scope": crops, "management_scope": label_by_kind[kind], "official_url": official_url,
            "discovery_url": "https://icar-crida.res.in/CCP/", "discovery_raw_sha256": "",
            "issue_start": "", "issue_end": "", "source_period": period,
            "source_date_precision": "historical_document_period_or_undated", "expected_raw_sha256": digest,
            "candidate_status": "candidate_from_final_site_frozen_hash", "reason": f"Final-site document for {sites}; static historical context only.",
        })
    return candidates


def persisted_hashes() -> Dict[str, str]:
    path = ENRICHED / "expanded_official_rag_source_inventory.csv"
    if not path.is_file():
        return {}
    return {row["source_document_id"]: row["raw_sha256"] for row in read_csv(path) if row.get("raw_sha256")}


def is_admitted(status: str) -> bool:
    """Use an explicit allow-list; rejected statuses may contain 'admitted'."""
    return status in {
        "admitted_exact_final_site_hash_verified",
        "admitted_initial_hash_frozen",
        "admitted_exact_frozen_hash_verified",
        "admitted_cached_frozen_hash_reverified",
    }


def write_source_bytes(source: Mapping[str, str], content: bytes, content_type: str, retrieved_at: str, admission_status: str) -> tuple[Dict[str, str], List[Dict[str, str]]]:
    stem = source_stem(source["source_document_id"])
    extension = raw_extension(content_type, source["official_url"])
    actual_hash = sha256(content).hexdigest()
    raw_relative = Path("raw") / "expanded_official_rag_sources" / f"{stem}{extension}"
    raw_path = ENRICHED / raw_relative
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)
    sections = extract_text(content, extension)
    text_relative = Path("rag_sources") / "expanded_extracted_text" / f"{stem}.json"
    text_path = ENRICHED / text_relative
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(json.dumps({"source_document_id": source["source_document_id"], "sections": sections}, ensure_ascii=False), encoding="utf-8")
    record = {field: source.get(field, "") for field in SOURCE_FIELDS}
    record.update({
        "raw_path": str(raw_relative), "raw_sha256": actual_hash, "extracted_text_path": str(text_relative),
        "extracted_text_sha256": sha256(text_path.read_bytes()).hexdigest(), "retrieved_at_utc": retrieved_at,
        "admission_status": admission_status, "error": "",
    })
    chunks: List[Dict[str, str]] = []
    for location, section_text in sections:
        for index, text in enumerate(chunk_text(section_text), start=1):
            chunks.append({
                "chunk_id": f"{source['source_document_id']}:{location}:{index:03d}",
                **{field: source.get(field, "") for field in (
                    "source_document_id", "source_title", "provider", "source_family", "source_class", "evidence_role",
                    "geography_scope", "crop_scope", "management_scope", "official_url", "issue_start", "issue_end", "source_period",
                )},
                "location": location, "chunk_index": str(index), "text": text, "source_raw_sha256": actual_hash,
            })
    return record, chunks


def content_scope_is_verified(source: Mapping[str, str], content: bytes) -> tuple[bool, str]:
    """Require content, not merely a link label, to support weekly scope."""
    if source["source_family"] != "ICAR_IISR_WEEKLY_ARCHIVE":
        return True, ""
    try:
        sections = extract_text(content, raw_extension("", source["official_url"]))
    except ValueError as exc:
        return False, f"No extractable weekly-advisory text: {exc}"
    text = " ".join(value for _, value in sections).casefold()
    if "soybean" not in text:
        return False, "Weekly PDF did not contain the crop term soybean."
    if not any(term in text for term in ("madhya pradesh", "rajasthan", "central zone")):
        return False, "Weekly PDF did not expose Central Zone/Madhya Pradesh/Rajasthan scope text."
    return True, ""


def collect_candidate(source: Dict[str, str], known_hashes: Mapping[str, str], timeout_s: float) -> tuple[Dict[str, str], List[Dict[str, str]]]:
    record = {field: source.get(field, "") for field in SOURCE_FIELDS}
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    prior_hash = known_hashes.get(source["source_document_id"], "")
    expected_hash = source["expected_raw_sha256"] or prior_hash
    source["expected_raw_sha256"] = expected_hash
    extension = raw_extension("", source["official_url"])
    cache = ENRICHED / "raw" / "expanded_official_rag_sources" / f"{source_stem(source['source_document_id'])}{extension}"
    try:
        response = requests.get(source["official_url"], headers=REQUEST_HEADERS, timeout=timeout_s)
        record["http_status"] = str(response.status_code)
        record["content_type"] = response.headers.get("Content-Type", "")
        response.raise_for_status()
        content = response.content
        actual_hash = sha256(content).hexdigest()
        if expected_hash and actual_hash != expected_hash:
            record.update({"expected_raw_sha256": expected_hash, "raw_sha256": actual_hash, "retrieved_at_utc": retrieved_at,
                           "admission_status": "rejected_remote_hash_drift", "error": "Remote bytes differ from the frozen expected hash."})
            return record, []
        verified, reason = content_scope_is_verified(source, content)
        if not verified:
            record.update({"expected_raw_sha256": expected_hash or actual_hash, "raw_sha256": actual_hash, "retrieved_at_utc": retrieved_at,
                           "admission_status": "rejected_content_scope_verification_failed", "error": reason})
            return record, []
        source["expected_raw_sha256"] = expected_hash or actual_hash
        status = "admitted_exact_final_site_hash_verified" if source["source_family"] == "ICAR_CRIDA_FINAL_SITE_CCP" else ("admitted_initial_hash_frozen" if not expected_hash else "admitted_exact_frozen_hash_verified")
        output, chunks = write_source_bytes(source, content, record["content_type"], retrieved_at, status)
        output["http_status"] = record["http_status"]
        output["content_type"] = record["content_type"]
        return output, chunks
    except (requests.RequestException, ValueError, OSError) as exc:
        if cache.is_file() and expected_hash and sha256(cache.read_bytes()).hexdigest() == expected_hash:
            content = cache.read_bytes()
            verified, reason = content_scope_is_verified(source, content)
            if verified:
                output, chunks = write_source_bytes(source, content, "", retrieved_at, "admitted_cached_frozen_hash_reverified")
                output["expected_raw_sha256"] = expected_hash
                output["error"] = f"Live retrieval failed; matching immutable cache reused: {type(exc).__name__}: {exc}"
                return output, chunks
            record["error"] = reason
        record.update({"expected_raw_sha256": expected_hash, "retrieved_at_utc": retrieved_at,
                       "admission_status": "rejected_source_retrieval_or_extraction_failure", "error": record.get("error") or f"{type(exc).__name__}: {exc}"})
        return record, []


def scope_rows(scenarios: Sequence[Mapping[str, str]], sources: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for scenario in scenarios:
        for source in sources:
            crop_ok = scenario["crop"] in source["crop_scope"].split(";")
            if source["evidence_role"] == "dated_weekly_advisory":
                geo_ok = scenario["state"] in {"Madhya Pradesh", "Rajasthan"}
                time_ok = source["issue_start"] <= scenario["decision_date"] <= source["issue_end"]
                status = "admitted_dated_advisory_to_metadata_filtered_rag" if crop_ok and geo_ok and time_ok else "blocked_metadata_scope"
                reason = "Weekly advisory passes crop, Central-Zone state and exact issue-week checks." if status.startswith("admitted") else "Weekly advisory is outside the crop, Central-Zone state, or exact issue-week scope."
                temporal = "pass_exact_issue_week" if time_ok else "blocked_outside_exact_issue_week"
                geography = "pass_central_zone_state_scope" if geo_ok else "blocked_central_zone_state_scope"
            else:
                geo_ok = source["geography_scope"].startswith(f"{scenario['district']}, {scenario['state']}")
                status = "admitted_historical_district_context_only" if crop_ok and geo_ok else "blocked_metadata_scope"
                reason = "District historical context only; cannot be converted to current or farm-specific advice." if status.startswith("admitted") else "District/crop does not match this ICAR-CRIDA document."
                temporal = "not_time_actionable_historical_context_only"
                geography = "pass_exact_district_scope" if geo_ok else "blocked_exact_district_scope"
            rows.append({
                "scenario_id": scenario["scenario_id"], "source_document_id": source["source_document_id"], "crop": scenario["crop"],
                "state": scenario["state"], "district": scenario["district"], "decision_date": scenario["decision_date"],
                "evidence_role": source["evidence_role"], "crop_scope_status": "pass_crop_scope" if crop_ok else "blocked_crop_scope",
                "geography_scope_status": geography, "temporal_status": temporal, "rag_scope_status": status, "restriction_reason": reason,
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand the provenance-checked official RAG corpus.")
    parser.add_argument("--timeout-s", type=float, default=90.0)
    args = parser.parse_args()
    if args.timeout_s <= 0:
        raise SystemExit("--timeout-s must be positive.")
    weekly, rejections = build_iisr_candidates(args.timeout_s)
    crida = build_crida_candidates()
    candidates = weekly + crida
    if len({row["source_document_id"] for row in candidates}) != len(candidates):
        raise SystemExit("Expanded source IDs are not unique.")
    write_csv(ENRICHED / "expanded_official_rag_source_candidates.csv", CANDIDATE_FIELDS, candidates)
    write_csv(ENRICHED / "expanded_official_rag_source_rejections.csv", REJECTION_FIELDS, rejections)
    known = persisted_hashes()
    records: List[Dict[str, str]] = []
    chunks: List[Dict[str, str]] = []
    for index, candidate in enumerate(candidates, start=1):
        record, source_chunks = collect_candidate(candidate, known, args.timeout_s)
        records.append(record)
        chunks.extend(source_chunks)
        print(f"[{index}/{len(candidates)}] {candidate['source_document_id']}: {record['admission_status']}")
    write_csv(ENRICHED / "expanded_official_rag_source_inventory.csv", SOURCE_FIELDS, records)
    write_csv(ENRICHED / "expanded_official_rag_chunks.csv", CHUNK_FIELDS, chunks)
    admitted = [row for row in records if is_admitted(row["admission_status"])]
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    bindings = scope_rows(scenarios, admitted)
    write_csv(ENRICHED / "scenario_expanded_rag_scope.csv", SCOPE_FIELDS, bindings)
    print(f"Expanded official corpus: {len(admitted)}/{len(records)} documents admitted; {len(chunks)} chunks; {len(bindings)} scenario-source scope rows; {len(rejections)} discovery rejections.")
    if not admitted:
        raise SystemExit("No expanded official source was admitted.")


if __name__ == "__main__":
    main()
