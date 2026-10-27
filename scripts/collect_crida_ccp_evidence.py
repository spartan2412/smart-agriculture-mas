"""Collect ICAR-CRIDA district Crop Contingency Plan evidence for benchmark sites.

The public ICAR-CRIDA portal serves district PDFs for agriculture profiles, sowing windows, and
pest/disease contingencies. These documents can establish historical district crop evidence and
crop-specific contingency coverage. They are not treated as current, dated disease alerts.

Run from the repository root:

    python scripts/collect_crida_ccp_evidence.py

The output records public URLs, HTTP results, SHA-256 digests, PDF page counts, source-period
tokens, and conservative crop-keyword checks. It contains no credentials and does not claim field
or current-season evidence.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://icar-crida.res.in/CCP"
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0",
    "Accept": "application/pdf",
}

# The current ICAR-CRIDA page uses some legacy state labels, notably OR for Odisha.
STATE_CODES = {
    "Andhra Pradesh": "AP",
    "Bihar": "BR",
    "Haryana": "HR",
    "Karnataka": "KA",
    "Madhya Pradesh": "MP",
    "Maharashtra": "MH",
    "Odisha": "OR",
    "Punjab": "PB",
    "Rajasthan": "RJ",
    "Tamil Nadu": "TN",
    "Telangana": "TG",
    "Uttar Pradesh": "UP",
    "West Bengal": "WB",
}

DOCUMENTS = {
    "crop_profile": "1.7.pdf",
    "sowing_window": "1.12.pdf",
    "pest_disease_contingency": "3.11.pdf",
}

CROP_PATTERNS = {
    "rice": re.compile(r"\b(?:rice|paddy)\b", re.IGNORECASE),
    "wheat": re.compile(r"\bwheat\b", re.IGNORECASE),
    "maize": re.compile(r"\bmaize\b", re.IGNORECASE),
    # Maharashtra CCP tables often use the official short label ``Gram`` for
    # chickpea.  Accept that label, but deliberately exclude green gram and
    # black gram so a pulse table cannot be mistaken for chickpea evidence.
    "chickpea": re.compile(
        r"(?<!green )(?<!black )\b(?:chickpea|chick\s+pea|chana|bengal\s+gram|gram)\b",
        re.IGNORECASE,
    ),
    "soybean": re.compile(r"\b(?:soybean|soyabean)\b", re.IGNORECASE),
    "tomato": re.compile(r"\btomato\b", re.IGNORECASE),
}
PERIOD_PATTERN = re.compile(r"\b(?:19|20)\d{2}\s*[-–]\s*\d{2}\b")


def normalise_location(value: str) -> str:
    return value.replace("_", " ").strip()


def build_document_url(state_code: str, district: str, filename: str) -> str:
    return f"{BASE_URL}/{state_code}/{district}/{filename}"


def extract_pdf_evidence(content: bytes, crop: str) -> Tuple[int, int, bool, str]:
    """Return page count, text length, crop-keyword result, and detected source periods."""
    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    periods = sorted({
        re.sub(r"\s+", "", period).replace("–", "-")
        for period in PERIOD_PATTERN.findall(text)
    })
    pattern = CROP_PATTERNS[crop.casefold()]
    return len(reader.pages), len(text), bool(pattern.search(text)), ";".join(periods) or "not_detected"


def fetch_document(url: str, crop: str) -> Dict[str, str]:
    result = {
        "url": url,
        "http_status": "",
        "sha256": "NONE",
        "page_count": "",
        "text_char_count": "",
        "crop_keyword_found": "",
        "source_period_tokens": "not_detected",
        "status": "",
        "error": "",
    }
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        result["http_status"] = str(response.status_code)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").casefold()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            raise ValueError("response is not a PDF")
        digest = sha256(response.content).hexdigest()
        pages, chars, keyword_found, periods = extract_pdf_evidence(response.content, crop)
        result.update({
            "sha256": digest,
            "page_count": str(pages),
            "text_char_count": str(chars),
            "crop_keyword_found": str(keyword_found).lower(),
            "source_period_tokens": periods,
            "status": (
                "public_pdf_crop_keyword_found"
                if keyword_found
                else "public_pdf_crop_keyword_not_found"
            ),
        })
    except (requests.RequestException, ValueError, OSError) as exc:
        result.update({
            "status": "document_unavailable_or_unreadable",
            "error": f"{type(exc).__name__}: {exc}",
        })
    return result


def build_coverage_row(site: Dict[str, str]) -> Dict[str, str]:
    state = normalise_location(site["state"])
    district = normalise_location(site["district"])
    state_code = STATE_CODES.get(state)
    row = {
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_id": "ICAR_CRIDA_CCP",
        "site_id": site["site_id"],
        "crop": site["crop"],
        "state": state,
        "district": district,
        "state_code": state_code or "UNMAPPED",
    }
    if not state_code:
        for name in DOCUMENTS:
            row.update({
                f"{name}_url": "NONE",
                f"{name}_http_status": "",
                f"{name}_sha256": "NONE",
                f"{name}_page_count": "",
                f"{name}_text_char_count": "",
                f"{name}_crop_keyword_found": "",
                f"{name}_source_period_tokens": "not_detected",
                f"{name}_status": "state_code_unmapped",
                f"{name}_error": f"No ICAR-CRIDA state code mapping for {state}",
            })
        row["crop_presence_status"] = "not_evaluated"
        row["sowing_window_status"] = "not_evaluated"
        row["pest_disease_contingency_status"] = "not_evaluated"
        row["admission_impact"] = "blocked_document_not_evaluated"
        return row

    evidence = {}
    for name, filename in DOCUMENTS.items():
        url = build_document_url(state_code, district, filename)
        evidence[name] = fetch_document(url, site["crop"])
        for key, value in evidence[name].items():
            row[f"{name}_{key}"] = value

    row["crop_presence_status"] = (
        "historical_official_crop_profile_keyword_found"
        if evidence["crop_profile"]["crop_keyword_found"] == "true"
        else "crop_profile_not_sufficient"
    )
    row["sowing_window_status"] = (
        "historical_official_sowing_window_keyword_found"
        if evidence["sowing_window"]["crop_keyword_found"] == "true"
        else "sowing_window_not_sufficient"
    )
    row["pest_disease_contingency_status"] = (
        "historical_crop_specific_contingency_keyword_found"
        if evidence["pest_disease_contingency"]["crop_keyword_found"] == "true"
        else "contingency_not_sufficient"
    )
    row["admission_impact"] = (
        "partial_historical_evidence_only_current_advisory_and_policy_still_required"
    )
    return row


OUTPUT_FIELDS = [
    "retrieved_at_utc",
    "source_id",
    "site_id",
    "crop",
    "state",
    "district",
    "state_code",
]
for _document_name in DOCUMENTS:
    OUTPUT_FIELDS.extend([
        f"{_document_name}_url",
        f"{_document_name}_http_status",
        f"{_document_name}_sha256",
        f"{_document_name}_page_count",
        f"{_document_name}_text_char_count",
        f"{_document_name}_crop_keyword_found",
        f"{_document_name}_source_period_tokens",
        f"{_document_name}_status",
        f"{_document_name}_error",
    ])
OUTPUT_FIELDS.extend([
    "crop_presence_status",
    "sowing_window_status",
    "pest_disease_contingency_status",
    "admission_impact",
])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public ICAR-CRIDA CCP evidence for every benchmark site."
    )
    parser.add_argument(
        "--sites",
        type=Path,
        default=PROJECT_ROOT / "data" / "registry" / "source_scoped_preflight_pool.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "data" / "registry" / "preflight_icar_crida_ccp_coverage.csv",
    )
    parser.add_argument(
        "--delay-s",
        type=float,
        default=0.3,
        help="Delay between site checks; use 0 only for a test double.",
    )
    parser.add_argument(
        "--crop",
        action="append",
        choices=sorted(CROP_PATTERNS),
        help="Collect one or more crops only; repeat this flag for multiple crops.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append selected-crop rows to an existing output instead of replacing it.",
    )
    args = parser.parse_args()
    if args.delay_s < 0:
        raise SystemExit("--delay-s must be non-negative.")

    with args.sites.open(newline="", encoding="utf-8") as source_file:
        sites = list(csv.DictReader(source_file))
    if args.crop:
        selected_crops = set(args.crop)
        sites = [site for site in sites if site["crop"] in selected_crops]
    if not sites:
        raise SystemExit(f"No site rows found in {args.sites}")

    rows: List[Dict[str, str]] = []
    for index, site in enumerate(sites, start=1):
        row = build_coverage_row(site)
        rows.append(row)
        print(
            f"[{index}/{len(sites)}] {site['site_id']}: "
            f"{row['crop_presence_status']}; {row['sowing_window_status']}; "
            f"{row['pest_disease_contingency_status']}"
        )
        if index != len(sites):
            time.sleep(args.delay_s)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    append_existing = args.append and args.out.exists() and args.out.stat().st_size > 0
    with args.out.open("a" if append_existing else "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        if not append_existing:
            writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
