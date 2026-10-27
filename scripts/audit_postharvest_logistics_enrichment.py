"""Fail-closed audit for the fourth post-harvest logistics enrichment."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
AUDIT_FIELDS = ["check", "expected", "actual", "result", "detail"]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def row_hash(row: Mapping[str, str], field: str) -> str:
    payload = {key: value for key, value in row.items() if key != field}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def check(name: str, expected: int | str, actual: int | str, errors: List[str]) -> Dict[str, str]:
    return {"check": name, "expected": str(expected), "actual": str(actual), "result": "pass" if not errors else "fail", "detail": "; ".join(errors[:5]) if errors else "validated"}


def main() -> None:
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    sites = read_csv(PROJECT_ROOT / "data" / "registry" / "final_study_sites.csv")
    sources = read_csv(ENRICHED / "postharvest_source_inventory.csv")
    profiles = read_csv(ENRICHED / "postharvest_handling_profiles.csv")
    operations = read_csv(ENRICHED / "postharvest_operation_library.csv")
    facilities = read_csv(ENRICHED / "postharvest_nhb_facility_records.csv")
    warehouses = read_csv(ENRICHED / "postharvest_wdra_warehouse_records.csv")
    infrastructure = read_csv(ENRICHED / "postharvest_nhb_state_infrastructure.csv")
    site_context = read_csv(ENRICHED / "postharvest_site_facility_context.csv")
    routes = read_csv(ENRICHED / "postharvest_static_route_context.csv")
    site_summaries = read_csv(ENRICHED / "postharvest_site_summary.csv")
    items = read_csv(ENRICHED / "scenario_postharvest_plan_items.csv")
    contexts = read_csv(ENRICHED / "scenario_postharvest_logistics_context.csv")
    passages = read_csv(ENRICHED / "postharvest_rag_passages.csv")
    rag_scope = read_csv(ENRICHED / "scenario_postharvest_rag_scope.csv")
    audit: List[Dict[str, str]] = []

    scenario_ids = {row["scenario_id"] for row in scenarios}
    site_ids = {row["site_id"] for row in sites}
    crops = {row["crop"] for row in scenarios}
    identity = {row["scenario_id"]: row for row in scenarios}

    source_errors = []
    if len({row["source_document_id"] for row in sources}) != len(sources):
        source_errors.append("source IDs are not unique")
    for row in sources:
        raw = ENRICHED / row["raw_path"]
        if not raw.is_file() or digest(raw) != row["raw_sha256"]:
            source_errors.append(f"{row['source_document_id']}: raw snapshot is missing or hash mismatched")
            break
    audit.append(check("source_snapshot_integrity", len(sources), len(sources), source_errors))

    profile_errors = []
    if len(profiles) != 6 or {row["crop"] for row in profiles} != crops:
        profile_errors.append("profiles do not cover exactly the six benchmark crops")
    if any(row_hash(row, "profile_sha256") != row["profile_sha256"] for row in profiles):
        profile_errors.append("profile hash mismatch")
    if any(row["farmer_output_status"] != "conditional_plan_items_available_no_direct_farm_action" for row in profiles):
        profile_errors.append("profile was promoted to a direct farm action")
    audit.append(check("six_crop_profiles_and_direct_action_guard", 6, len(profiles), profile_errors))

    operation_errors = []
    profile_by_id = {row["profile_id"]: row for row in profiles}
    source_by_id = {row["source_document_id"]: row for row in sources}
    if len({row["operation_id"] for row in operations}) != len(operations):
        operation_errors.append("operation IDs are not unique")
    if any(row["profile_id"] not in profile_by_id or row["source_document_id"] not in source_by_id for row in operations):
        operation_errors.append("operation refers to unknown profile or source")
    for row in operations:
        source = source_by_id.get(row["source_document_id"])
        if source and row["source_raw_sha256"] != source["raw_sha256"]:
            operation_errors.append(f"{row['operation_id']}: source hash mismatch")
            break
        if row["actionability_status"] != "conditional_postharvest_planning_reference_not_direct_farm_action":
            operation_errors.append(f"{row['operation_id']}: actionability is unsafe")
            break
        if not row["source_quote"] or not row["missing_observation"]:
            operation_errors.append(f"{row['operation_id']}: source quote or condition missing")
            break
        if row_hash(row, "operation_sha256") != row["operation_sha256"]:
            operation_errors.append(f"{row['operation_id']}: hash mismatch")
            break
    audit.append(check("source_quoted_operations", len(operations), len(operations), operation_errors))

    infrastructure_errors = []
    required_states = {row["state"] for row in sites}
    if not facilities or not warehouses or not infrastructure:
        infrastructure_errors.append("at least one infrastructure table is empty")
    if {row["state"] for row in infrastructure} != required_states:
        infrastructure_errors.append("NHB state aggregate does not cover benchmark states")
    for table, hash_field in ((facilities, "facility_sha256"), (warehouses, "warehouse_sha256"), (infrastructure, "infrastructure_sha256")):
        if len({tuple(row.items()) for row in table}) != len(table):
            infrastructure_errors.append("duplicate fully-identical infrastructure record")
            break
        if any(row_hash(row, hash_field) != row[hash_field] for row in table):
            infrastructure_errors.append(f"{hash_field} mismatch")
            break
        if any("historical" not in row["not_supported"].lower() or "availab" not in row["not_supported"].lower() for row in table):
            infrastructure_errors.append("infrastructure record lacks historical-availability boundary")
            break
    audit.append(check("collection_date_infrastructure_integrity", len(facilities) + len(warehouses) + len(infrastructure), len(facilities) + len(warehouses) + len(infrastructure), infrastructure_errors))

    site_errors = []
    summaries_by_site = {row["site_id"]: row for row in site_summaries}
    if len(summaries_by_site) != len(site_summaries) or set(summaries_by_site) != site_ids:
        site_errors.append("site summaries must cover every frozen site exactly once")
    for row in site_context:
        if row["site_id"] not in site_ids or row_hash(row, "site_context_sha256") != row["site_context_sha256"]:
            site_errors.append("site context identity or hash mismatch")
            break
        if row["context_kind"] not in {"nhb_mapped_project_proximity", "wdra_registered_warehouse_district_match"}:
            site_errors.append("unsupported candidate context kind")
            break
        if "No claim" not in row["not_supported"]:
            site_errors.append("candidate context lacks availability boundary")
            break
    for row in site_summaries:
        if row_hash(row, "site_summary_sha256") != row["site_summary_sha256"]:
            site_errors.append("site summary hash mismatch")
            break
        observed_routes = len([route for route in routes if route["site_id"] == row["site_id"]])
        if int(row["static_road_route_count"]) != observed_routes:
            site_errors.append("site summary static-route count mismatch")
            break
    audit.append(check("site_context_identity_and_safety", len(sites), len(site_summaries), site_errors))

    route_errors = []
    expected_route_pairs = {(row["site_id"], row["candidate_id"]) for row in site_context if row["context_kind"] == "nhb_mapped_project_proximity"}
    actual_route_pairs = {(row["site_id"], row["candidate_id"]) for row in routes}
    if actual_route_pairs != expected_route_pairs or len(actual_route_pairs) != len(routes):
        route_errors.append("static route records must cover each NHB candidate exactly once")
    for row in routes:
        raw = ENRICHED / row["raw_path"]
        if not raw.is_file() or digest(raw) != row["raw_sha256"] or row_hash(row, "route_sha256") != row["route_sha256"]:
            route_errors.append("static route source/hash mismatch")
            break
        boundary = row["not_supported"].lower()
        if not all(term in boundary for term in ("traffic", "availability", "booking", "historical")):
            route_errors.append("static route lacks live-routing safety boundary")
            break
    audit.append(check("static_route_context_integrity", len(expected_route_pairs), len(routes), route_errors))

    scenario_errors = []
    context_by_id = {row["scenario_id"]: row for row in contexts}
    if len(context_by_id) != len(contexts) or set(context_by_id) != scenario_ids:
        scenario_errors.append("scenario context must cover every frozen scenario exactly once")
    expected_items = 0
    expected_pairs = set()
    for scenario in scenarios:
        selected = [row for row in operations if row["crop"] == scenario["crop"]]
        expected_items += len(selected)
        expected_pairs.update((scenario["scenario_id"], row["operation_id"]) for row in selected)
    actual_pairs = {(row["scenario_id"], row["operation_id"]) for row in items}
    if len(items) != expected_items or actual_pairs != expected_pairs:
        scenario_errors.append("scenario operation bindings do not equal crop-scoped profile operations")
    for row in items:
        expected = identity.get(row["scenario_id"])
        if expected is None or any(row[field] != expected[field] for field in ("site_id", "crop", "state", "district", "season", "decision_date")):
            scenario_errors.append("scenario plan identity mismatch")
            break
        if row["item_status"] != "conditional_postharvest_operation_pending_lot_observation" or row["actionability_status"] != "conditional_postharvest_planning_reference_not_direct_farm_action":
            scenario_errors.append("scenario operation was promoted to an unsafe action")
            break
        if row_hash(row, "plan_item_sha256") != row["plan_item_sha256"]:
            scenario_errors.append("scenario plan hash mismatch")
            break
    for row in contexts:
        if row_hash(row, "context_sha256") != row["context_sha256"] or row["context_status"] != "available_source_linked_postharvest_context":
            scenario_errors.append("scenario context hash or status mismatch")
            break
    audit.append(check("all_300_scenario_bindings", expected_items, len(items), scenario_errors))

    rag_errors = []
    passage_by_id = {row["passage_id"]: row for row in passages}
    if len(passage_by_id) != len(passages):
        rag_errors.append("RAG passage IDs are not unique")
    if {(row["scenario_id"], row["passage_id"]) for row in rag_scope} != {
        (row["scenario_id"], f"POSTHARVEST_PASSAGE__{row['operation_id']}") for row in items
    }:
        rag_errors.append("RAG scope does not exactly equal scenario post-harvest operation scope")
    for row in passages:
        if row_hash(row, "passage_sha256") != row["passage_sha256"] or not row["text"]:
            rag_errors.append("RAG passage hash or source text mismatch")
            break
    for row in rag_scope:
        passage = passage_by_id.get(row["passage_id"])
        scenario = identity.get(row["scenario_id"])
        if not passage or not scenario or passage["crop"] != scenario["crop"] or row["crop_scope_status"] != "pass_exact_crop":
            rag_errors.append("RAG scope leaked a passage beyond exact crop scope")
            break
        if row_hash(row, "scope_sha256") != row["scope_sha256"]:
            rag_errors.append("RAG scope hash mismatch")
            break
    audit.append(check("crop_filtered_postharvest_rag_scope", len(items), len(rag_scope), rag_errors))

    write_csv(ENRICHED / "postharvest_logistics_audit.csv", AUDIT_FIELDS, audit)
    report = [
        "# Post-Harvest Storage and Logistics Enrichment Audit\n\n",
        "This audit validates only the fourth enrichment. It does not reclassify infrastructure directories as historical operational evidence.\n\n",
        "| Check | Expected | Actual | Result |\n| --- | ---: | ---: | --- |\n",
    ]
    report.extend(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['result']} |\n" for row in audit)
    report.extend([
        "\n## Safety interpretation\n\n",
        "- Every post-harvest operation remains conditional on an unobserved lot condition; none is a direct farm action.\n",
        "- NHB and WDRA records are collection-date infrastructure/registration context. They cannot establish capacity, vacancy, commodity acceptance, booking, transport, or historical availability.\n",
        "- Static OSRM routes are collection-date road-geometry estimates only. They cannot establish traffic, vehicle availability, freight, cold-chain fit, booking, dispatch, or historical access.\n",
        "- Post-harvest RAG passages are scoped to the exact crop and cannot be retrieved for another crop.\n",
    ])
    (ENRICHED / "POSTHARVEST_LOGISTICS_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failed = [row for row in audit if row["result"] != "pass"]
    print(f"Post-harvest logistics audit: {len(audit) - len(failed)}/{len(audit)} checks passed.")
    if failed:
        raise SystemExit("Post-harvest logistics audit failed; inspect postharvest_logistics_audit.csv.")


if __name__ == "__main__":
    main()
