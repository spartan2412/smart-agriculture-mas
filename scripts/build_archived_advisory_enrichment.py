"""Audit and bind dated advisory evidence without pretending that a state/zone
document is a district bulletin.

The public IMD GKMS portal is probed anonymously and its raw response is kept
as evidence of access status.  Existing hash-verified ICAR/IISR advisory
documents are then bound at their *actual* zone/state scope.  The resulting
table makes the shortfall explicit: no record becomes a district advisory
unless the document says it is one and its effective date covers the scenario.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMD_GKMS_URL = "https://agromet.imd.gov.in/"
REQUEST_HEADERS = {"User-Agent": "SmartAgricultureMAS/1.0 archived-advisory-discovery", "Accept": "text/html,*/*;q=0.8"}
SOURCE_FIELDS = [
    "advisory_source_id", "provider", "official_url", "advisory_issue_start", "advisory_issue_end", "scope_level",
    "state_scope", "crop_scope", "source_document_id", "source_raw_sha256", "retrieval_or_access_status", "raw_path",
    "raw_sha256", "retrieved_at_utc", "evidence_note",
]
BINDING_FIELDS = [
    "scenario_id", "advisory_source_id", "crop", "state", "district", "decision_date", "crop_scope_status",
    "geography_scope_status", "temporal_status", "scope_level", "binding_status", "binding_reason",
]
STATUS_FIELDS = [
    "scenario_id", "exact_district_advisory_status", "best_available_non_district_advisory_status",
    "best_available_non_district_source_id", "advisory_actionability", "restriction_reason",
]


ADVISORY_SPECS = [
    {
        "advisory_source_id": "ICAR_IISR_WEEKLY_SOYBEAN_2024", "provider": "ICAR–Indian Institute of Soybean Research",
        "official_url": "https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf", "advisory_issue_start": "2024-07-01",
        "advisory_issue_end": "2024-07-07", "scope_level": "central_soybean_zone_not_district",
        "state_scope": "Madhya Pradesh;Rajasthan", "crop_scope": "soybean", "source_document_id": "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024",
        "evidence_note": "Official weekly advisory; its stated Central soybean zone scope is not a district bulletin.",
    },
    {
        "advisory_source_id": "ICAR_KHARIF_STATE_2025", "provider": "Indian Council of Agricultural Research",
        "official_url": "https://icar.org.in/sites/default/files/Circulars/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf", "advisory_issue_start": "2025-05-31",
        "advisory_issue_end": "2025-12-31", "scope_level": "state_chapter_not_district",
        "state_scope": "Maharashtra;Rajasthan", "crop_scope": "rice;maize;soybean", "source_document_id": "ICAR_KHARIF_STATE_ADVISORIES_2025",
        "evidence_note": "Official named Kharif 2025 state-chapter publication; registry-defined study scope is state, not district.",
    },
    {
        "advisory_source_id": "ICAR_RABI_STATE_2021_22", "provider": "Indian Council of Agricultural Research",
        "official_url": "https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf", "advisory_issue_start": "2021-09-30",
        "advisory_issue_end": "2022-06-30", "scope_level": "state_chapter_not_district",
        "state_scope": "Madhya Pradesh;Maharashtra;Tamil Nadu", "crop_scope": "wheat;chickpea;maize;tomato", "source_document_id": "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "evidence_note": "Official named Rabi 2021–22 state-chapter publication; it expires before nearly all current study scenarios.",
    },
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_time_valid(decision_date: str, start: str, end: str) -> str:
    if decision_date < start:
        return "blocked_advisory_not_yet_issued"
    if decision_date > end:
        return "blocked_advisory_window_ended"
    return "pass_advisory_time_valid"


def main() -> None:
    scenario_root = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenario_root / "enriched"
    scenarios = read_csv(scenario_root / "manifests" / "scenario_manifest.csv")
    source_inventory = {row["source_document_id"]: row for row in read_csv(enriched / "official_rag_source_inventory.csv")}
    source_rows: List[Dict[str, str]] = []

    # The Portal's redirect to an explicit login page is persisted rather than
    # described from memory. It proves anonymous historical-district retrieval
    # was not available from this official entry point at collection time.
    portal_raw = Path("raw") / "archived_advisory_discovery" / "imd_gkms_portal.html"
    portal_row = {
        "advisory_source_id": "IMD_GKMS_ANONYMOUS_PORTAL", "provider": "India Meteorological Department GKMS",
        "official_url": IMD_GKMS_URL, "advisory_issue_start": "", "advisory_issue_end": "", "scope_level": "unknown_login_gated",
        "state_scope": "", "crop_scope": "", "source_document_id": "", "source_raw_sha256": "", "retrieval_or_access_status": "",
        "raw_path": str(portal_raw), "raw_sha256": "", "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "evidence_note": "",
    }
    try:
        response = requests.get(IMD_GKMS_URL, headers=REQUEST_HEADERS, timeout=45, allow_redirects=True)
        raw = response.content
        destination = enriched / portal_raw
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        text = raw.decode("utf-8", errors="replace").casefold()
        final_url = response.url.casefold()
        portal_row["raw_sha256"] = sha256(raw).hexdigest()
        if response.status_code == 200 and "login/login_form" in final_url and "sign in" in text:
            portal_row.update({
                "retrieval_or_access_status": "anonymous_historical_district_archive_not_accessible_login_form_returned",
                "evidence_note": "Official portal redirected to its sign-in form; no public anonymous historical district advisory endpoint was exposed by this request.",
            })
        else:
            portal_row.update({
                "retrieval_or_access_status": "portal_response_requires_manual_endpoint_review",
                "evidence_note": f"Unexpected portal response status={response.status_code}; final_url={response.url}",
            })
    except requests.RequestException as exc:
        portal_row.update({"retrieval_or_access_status": "portal_probe_failed", "evidence_note": f"{type(exc).__name__}: {exc}"})
    source_rows.append(portal_row)

    for spec in ADVISORY_SPECS:
        source = source_inventory.get(spec["source_document_id"])
        if source is None or not source["retrieval_status"].endswith("_admitted_to_rag"):
            raise SystemExit(f"Required official advisory source was not admitted: {spec['source_document_id']}")
        source_rows.append({
            **spec, "source_raw_sha256": source["raw_sha256"], "retrieval_or_access_status": "hash_verified_official_source_available",
            "raw_path": source["raw_path"], "raw_sha256": source["raw_sha256"],
            "retrieved_at_utc": source["retrieved_at_utc"],
        })

    bindings: List[Dict[str, str]] = []
    for scenario in scenarios:
        for spec in ADVISORY_SPECS:
            crop_status = "pass_crop_scope" if scenario["crop"] in spec["crop_scope"].split(";") else "blocked_crop_scope"
            geography_status = "pass_state_scope_not_district" if scenario["state"] in spec["state_scope"].split(";") else "blocked_geography_scope"
            temporal_status = is_time_valid(scenario["decision_date"], spec["advisory_issue_start"], spec["advisory_issue_end"])
            if all(item.startswith("pass_") for item in (crop_status, geography_status, temporal_status)):
                binding_status, reason = "available_non_district_advisory_only", "source scope is state/zone, not the scenario district"
            else:
                binding_status = next(item for item in (crop_status, geography_status, temporal_status) if item.startswith("blocked_"))
                reason = binding_status
            bindings.append({
                "scenario_id": scenario["scenario_id"], "advisory_source_id": spec["advisory_source_id"], "crop": scenario["crop"],
                "state": scenario["state"], "district": scenario["district"], "decision_date": scenario["decision_date"],
                "crop_scope_status": crop_status, "geography_scope_status": geography_status, "temporal_status": temporal_status,
                "scope_level": spec["scope_level"], "binding_status": binding_status, "binding_reason": reason,
            })
    by_scenario: Dict[str, List[Dict[str, str]]] = {}
    for binding in bindings:
        by_scenario.setdefault(binding["scenario_id"], []).append(binding)
    statuses: List[Dict[str, str]] = []
    for scenario in scenarios:
        available = [row for row in by_scenario[scenario["scenario_id"]] if row["binding_status"] == "available_non_district_advisory_only"]
        statuses.append({
            "scenario_id": scenario["scenario_id"],
            "exact_district_advisory_status": "unavailable_no_anonymous_public_historical_district_bulletin_verified",
            "best_available_non_district_advisory_status": "available_state_or_zone_scope" if available else "unavailable_for_exact_crop_state_date",
            "best_available_non_district_source_id": available[0]["advisory_source_id"] if available else "",
            "advisory_actionability": "non_district_context_only_not_a_district_specific_instruction",
            "restriction_reason": "The official IMD GKMS portal returned a sign-in form to anonymous access; state/zone sources are retained only at their stated scope.",
        })
    write_csv(enriched / "archived_advisory_source_discovery.csv", SOURCE_FIELDS, source_rows)
    write_csv(enriched / "scenario_archived_advisory_bindings.csv", BINDING_FIELDS, bindings)
    write_csv(enriched / "scenario_archived_advisory_status.csv", STATUS_FIELDS, statuses)
    print(f"Archived-advisory enrichment: {len(source_rows)} source-access records; {len(bindings)} source bindings; 0/{len(statuses)} exact district advisories claimed.")


if __name__ == "__main__":
    main()
