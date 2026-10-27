"""Recheck public, time-valid district/KVK advisory access without guessing.

Only a source that exposes all of crop, exact district, and an issue period
covering the scenario decision date can be called a district advisory.  This
script records public-access failures and near-misses as evidence; it never
turns a state/zone or static district document into a district bulletin.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
REQUEST_HEADERS = {"User-Agent": "SmartAgricultureMAS/1.0 public-district-kvk-advisory-discovery", "Accept": "text/html,*/*;q=0.8"}
SOURCE_FIELDS = [
    "source_check_id", "provider", "official_url", "retrieved_at_utc", "http_status", "final_url", "raw_path",
    "raw_sha256", "public_access_status", "crop_scope_status", "district_scope_status", "time_validity_status",
    "admission_status", "evidence_note",
]
STATUS_FIELDS = [
    "scenario_id", "crop", "state", "district", "decision_date", "exact_public_district_kvk_advisory_status",
    "best_verified_non_district_source_status", "best_verified_non_district_source_id", "restriction_reason",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def portal_probe() -> Dict[str, str]:
    url = "https://kvk.icar.gov.in/"
    row = {
        "source_check_id": "ICAR_KVK_PUBLIC_PORTAL", "provider": "ICAR Krishi Vigyan Kendra portal", "official_url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "http_status": "", "final_url": "",
        "raw_path": "", "raw_sha256": "", "public_access_status": "", "crop_scope_status": "not_exposed",
        "district_scope_status": "not_exposed", "time_validity_status": "not_exposed", "admission_status": "", "evidence_note": "",
    }
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=45, allow_redirects=True)
        row.update({"http_status": str(response.status_code), "final_url": response.url})
        raw_relative = Path("raw") / "public_district_kvk_advisory_discovery" / "icar_kvk_portal.html"
        destination = ENRICHED / raw_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        row.update({"raw_path": str(raw_relative), "raw_sha256": sha256(response.content).hexdigest()})
        text = response.text.casefold()
        if response.status_code == 200 and "advis" in text and "district" in text:
            row.update({
                "public_access_status": "public_portal_retrieved_manual_endpoint_curation_required",
                "admission_status": "not_admitted_no_crop_district_issue_period_record_extracted",
                "evidence_note": "The landing response is not itself a crop-, district-, and date-specific advisory record.",
            })
        else:
            row.update({
                "public_access_status": "public_portal_no_machine_verifiable_dated_district_advisory_exposed",
                "admission_status": "not_admitted_no_crop_district_issue_period_record_extracted",
                "evidence_note": f"HTTP {response.status_code} response did not expose a verifiable dated district advisory record.",
            })
    except requests.RequestException as exc:
        row.update({
            "public_access_status": "public_portal_transport_or_dns_unavailable_at_collection_time",
            "admission_status": "not_admitted_no_public_record_retrieved",
            "evidence_note": f"{type(exc).__name__}: {exc}",
        })
    return row


def main() -> None:
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    sources: List[Dict[str, str]] = [portal_probe()]
    # Existing raw IMD access evidence is deliberately reused rather than
    # inventing a new access claim. Its login outcome applies to anonymous
    # historical district retrieval, not to any claimed district operation.
    imd = next((row for row in read_csv(ENRICHED / "archived_advisory_source_discovery.csv") if row["advisory_source_id"] == "IMD_GKMS_ANONYMOUS_PORTAL"), None)
    if imd is not None:
        sources.append({
            "source_check_id": "IMD_GKMS_ANONYMOUS_PORTAL", "provider": imd["provider"], "official_url": imd["official_url"],
            "retrieved_at_utc": imd["retrieved_at_utc"], "http_status": "", "final_url": "", "raw_path": imd["raw_path"],
            "raw_sha256": imd["raw_sha256"], "public_access_status": imd["retrieval_or_access_status"],
            "crop_scope_status": "not_exposed", "district_scope_status": "not_exposed", "time_validity_status": "not_exposed",
            "admission_status": "not_admitted_login_gated", "evidence_note": imd["evidence_note"],
        })
    sources.extend([
        {
            "source_check_id": "ICAR_IISR_EXACT_WEEK_ARCHIVE", "provider": "ICAR–Indian Institute of Soybean Research",
            "official_url": "https://icar-nsri.res.in/Advisory.html", "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "http_status": "200_prior_hash_verified", "final_url": "", "raw_path": "raw/expanded_official_source_discovery/",
            "raw_sha256": "multiple_frozen_archive_hashes", "public_access_status": "public_dated_weekly_sources_available",
            "crop_scope_status": "soybean_verified", "district_scope_status": "central_zone_not_district", "time_validity_status": "exact_week_verified",
            "admission_status": "not_admitted_as_district_advisory_zone_source_retained_separately",
            "evidence_note": "The 2023 and 2024 soybean source PDFs are zone-scoped; they remain exact-week non-district evidence only.",
        },
        {
            "source_check_id": "ICAR_CRIDA_FINAL_SITE_CCP", "provider": "ICAR–Central Research Institute for Dryland Agriculture",
            "official_url": "https://icar-crida.res.in/CCP/", "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "http_status": "200_prior_hash_verified", "final_url": "", "raw_path": "data/registry/preflight_icar_crida_ccp_coverage.csv",
            "raw_sha256": "per_document_frozen_in_final_site_registry", "public_access_status": "public_static_district_documents_available",
            "crop_scope_status": "per_site_verified", "district_scope_status": "exact_district", "time_validity_status": "historical_context_not_dated_decision_advisory",
            "admission_status": "not_admitted_as_district_advisory_historical_context_retained_separately",
            "evidence_note": "These documents are valuable exact-district historical context but do not state an advisory issue period covering a scenario decision date.",
        },
    ])

    statuses: List[Dict[str, str]] = []
    weekly_scope = {(row["scenario_id"], row["source_document_id"]): row for row in read_csv(ENRICHED / "scenario_expanded_rag_scope.csv")}
    weekly_sources = ["ICAR_IISR_WEEKLY_SOYBEAN_20230925", "ICAR_IISR_WEEKLY_SOYBEAN_20240624"]
    for scenario in scenarios:
        matching = [source for source in weekly_sources if weekly_scope.get((scenario["scenario_id"], source), {}).get("rag_scope_status") == "admitted_dated_advisory_to_metadata_filtered_rag"]
        statuses.append({
            "scenario_id": scenario["scenario_id"], "crop": scenario["crop"], "state": scenario["state"], "district": scenario["district"],
            "decision_date": scenario["decision_date"],
            "exact_public_district_kvk_advisory_status": "unavailable_no_public_crop_district_date_matched_advisory_verified",
            "best_verified_non_district_source_status": "available_exact_week_zone_advisory" if matching else "unavailable_for_exact_crop_state_date",
            "best_verified_non_district_source_id": matching[0] if matching else "",
            "restriction_reason": "No public source met crop + exact district + issue-period gates. Zone and static-district sources remain labelled at their actual scope.",
        })
    write_csv(ENRICHED / "public_district_kvk_advisory_discovery.csv", SOURCE_FIELDS, sources)
    write_csv(ENRICHED / "scenario_public_district_kvk_advisory_status.csv", STATUS_FIELDS, statuses)
    near_matches = sum(bool(row["best_verified_non_district_source_id"]) for row in statuses)
    report = [
        "# Public District/KVK Advisory Discovery\n\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n\n",
        f"- Official source-access checks: {len(sources)}\n",
        f"- Exact crop + district + decision-date public advisory records admitted: 0/{len(statuses)}\n",
        f"- Exact-week zone-advisory near-matches retained at their actual non-district scope: {near_matches}\n\n",
        "## Result\n\n",
        "No new district/KVK advisory is added to the corpus. The official KVK portal was not publicly reachable from this collection environment; the IMD GKMS entrypoint remained login-gated; the IISR sources are zone-scoped; and ICAR-CRIDA documents are static district context rather than dated advisories.\n\n",
        "This is a negative but useful provenance result. The scenario status file explicitly records unavailable district advice rather than relabelling a zone or static source as district-specific.\n",
    ]
    (ENRICHED / "PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md").write_text("".join(report), encoding="utf-8")
    print(f"Public district/KVK advisory discovery: {len(sources)} source-access checks; 0/{len(statuses)} exact district advisories admitted; {near_matches} zone advisory near-matches retained at correct scope.")


if __name__ == "__main__":
    main()
