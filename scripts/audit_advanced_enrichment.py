"""Verify the six-layer official-action and pre-decision-satellite enrichment."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["layer", "expected_rows", "actual_rows", "passing_rows", "unavailable_rows", "result", "detail"]


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


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def audit_row(layer: str, expected: int, actual: int, passing: int, unavailable: int, errors: List[str]) -> Dict[str, str]:
    return {
        "layer": layer, "expected_rows": str(expected), "actual_rows": str(actual), "passing_rows": str(passing),
        "unavailable_rows": str(unavailable), "result": "pass" if not errors else "fail",
        "detail": "; ".join(errors[:6]) if errors else "validated",
    }


def main() -> None:
    scenario_root = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenario_root / "enriched"
    scenarios = read_csv(scenario_root / "manifests" / "scenario_manifest.csv")
    scenario_ids = {row["scenario_id"] for row in scenarios}
    audit: List[Dict[str, str]] = []

    sources = read_csv(enriched / "official_rag_source_inventory.csv")
    chunks = read_csv(enriched / "official_rag_chunks.csv")
    selection = read_csv(enriched / "official_rag_source_selection_audit.csv")
    registry_sources = read_csv(PROJECT_ROOT / "data" / "registry" / "regional_management_source_snapshot.csv")
    selection_errors: List[str] = []
    if len(selection) != len(registry_sources) or len({row["source_document_id"] for row in selection}) != len(selection):
        selection_errors.append("source-snapshot selection audit does not cover each registry source once")
    selected_ids = {row["source_document_id"] for row in selection if row["selection_status"] == "selected_for_hash_verified_retrieval"}
    if selected_ids != {row["source_document_id"] for row in sources}:
        selection_errors.append("selected source IDs differ from retrieval inventory")
    audit.append(audit_row("official_source_selection_scope", len(selection), len(selection), len(selected_ids), len(selection) - len(selected_ids), selection_errors))
    source_errors: List[str] = []
    admitted = [row for row in sources if row["retrieval_status"].endswith("_admitted_to_rag")]
    for source in admitted:
        raw = enriched / source["raw_path"]
        extracted = enriched / source["extracted_text_path"]
        if not raw.is_file() or digest(raw) != source["raw_sha256"] or source["raw_sha256"] != source["expected_sha256"]:
            source_errors.append(f"{source['source_document_id']}: raw hash")
        if not extracted.is_file() or digest(extracted) != source["extracted_text_sha256"]:
            source_errors.append(f"{source['source_document_id']}: extracted text hash")
    chunk_ids = {row["source_document_id"] for row in chunks}
    if chunk_ids != {row["source_document_id"] for row in admitted}:
        source_errors.append("chunk document set differs from admitted source set")
    audit.append(audit_row("official_source_retrieval_and_hashes", len(sources), len(sources), len(admitted), len(sources) - len(admitted), source_errors))

    actions = read_csv(enriched / "official_action_records.csv")
    action_errors: List[str] = []
    for action in actions:
        source = next((row for row in admitted if row["source_document_id"] == action["source_document_id"]), None)
        if source is None:
            action_errors.append(f"{action['action_id']}: source not admitted")
            continue
        document = json.loads((enriched / source["extracted_text_path"]).read_text(encoding="utf-8"))
        sections = dict(document["sections"])
        if normalise(action["source_quote"]) not in normalise(sections.get(action["source_location"], "")):
            action_errors.append(f"{action['action_id']}: quote missing")
        if action["source_raw_sha256"] != source["raw_sha256"]:
            action_errors.append(f"{action['action_id']}: source hash mismatch")
    audit.append(audit_row("structured_official_action_records", len(actions), len(actions), len(actions) - len(action_errors), 0, action_errors))

    bindings = read_csv(enriched / "scenario_official_action_bindings.csv")
    binding_errors: List[str] = []
    expected_pairs = {(scenario["scenario_id"], action["action_id"]) for scenario in scenarios for action in actions}
    actual_pairs = {(row["scenario_id"], row["action_id"]) for row in bindings}
    if len(bindings) != len(actual_pairs) or actual_pairs != expected_pairs:
        binding_errors.append("scenario-action Cartesian coverage/uniqueness failure")
    prohibited = [row for row in bindings if row["binding_status"] == "source_scoped_eligible"]
    if prohibited:
        binding_errors.append(f"{len(prohibited)} unconditioned action rows unexpectedly eligible")
    audit.append(audit_row("scenario_operation_bindings", len(expected_pairs), len(bindings), len(bindings) - len(prohibited), 0, binding_errors))

    rag_scope = read_csv(enriched / "scenario_rag_scope.csv")
    rag_errors: List[str] = []
    expected_rag_pairs = {(scenario["scenario_id"], source["source_document_id"]) for scenario in scenarios for source in admitted}
    actual_rag_pairs = {(row["scenario_id"], row["source_document_id"]) for row in rag_scope}
    if len(rag_scope) != len(actual_rag_pairs) or actual_rag_pairs != expected_rag_pairs:
        rag_errors.append("scenario-document Cartesian coverage/uniqueness failure")
    invalid_admitted = [row for row in rag_scope if row["rag_scope_status"] == "admitted_to_metadata_filtered_rag" and not (
        row["crop_scope_status"].startswith("pass_") and row["geography_scope_status"].startswith("pass_") and row["source_temporal_status"].startswith("pass_")
    )]
    if invalid_admitted:
        rag_errors.append(f"{len(invalid_admitted)} metadata-invalid documents admitted")
    audit.append(audit_row("metadata_filtered_rag_scope", len(expected_rag_pairs), len(rag_scope), sum(row["rag_scope_status"] == "admitted_to_metadata_filtered_rag" for row in rag_scope), sum(row["rag_scope_status"] != "admitted_to_metadata_filtered_rag" for row in rag_scope), rag_errors))

    advisory_sources = read_csv(enriched / "archived_advisory_source_discovery.csv")
    advisory_bindings = read_csv(enriched / "scenario_archived_advisory_bindings.csv")
    advisory_statuses = read_csv(enriched / "scenario_archived_advisory_status.csv")
    advisory_errors: List[str] = []
    if {row["scenario_id"] for row in advisory_statuses} != scenario_ids or len(advisory_statuses) != len(scenarios):
        advisory_errors.append("district advisory status does not cover all scenarios exactly once")
    if any(row["exact_district_advisory_status"].startswith("available") for row in advisory_statuses):
        advisory_errors.append("a non-verified district advisory was claimed available")
    imd = next((row for row in advisory_sources if row["advisory_source_id"] == "IMD_GKMS_ANONYMOUS_PORTAL"), None)
    if imd is None or not imd["retrieval_or_access_status"].startswith("anonymous_historical_district_archive_not_accessible"):
        advisory_errors.append("IMD anonymous access evidence not recorded")
    if imd and imd["raw_path"]:
        raw = enriched / imd["raw_path"]
        if not raw.is_file() or digest(raw) != imd["raw_sha256"]:
            advisory_errors.append("IMD access-evidence raw hash")
    audit.append(audit_row("archived_district_advisory_access_and_scope", len(scenarios), len(advisory_statuses), 0, len(scenarios), advisory_errors))

    timeseries_manifest = read_csv(enriched / "sentinel_ndvi_timeseries_manifest.csv")
    observations = read_csv(enriched / "sentinel_ndvi_timeseries_observations.csv")
    features = read_csv(enriched / "sentinel_ndvi_timeseries_features.csv")
    statuses = read_csv(enriched / "sentinel_ndvi_timeseries_status.csv")
    ndvi_errors: List[str] = []
    if {row["scenario_id"] for row in timeseries_manifest} != scenario_ids or len(timeseries_manifest) != len(scenarios):
        ndvi_errors.append("timeseries manifest does not cover all scenarios exactly once")
    if {row["scenario_id"] for row in features} != scenario_ids or len(features) != len(scenarios):
        ndvi_errors.append("timeseries features does not cover all scenarios exactly once")
    if {row["scenario_id"] for row in statuses} != scenario_ids or len(statuses) != len(scenarios):
        ndvi_errors.append("timeseries status does not cover all scenarios exactly once")
    dates = {row["scenario_id"]: row["decision_date"] for row in scenarios}
    base_context = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_context_manifest.csv")}
    recovery_context = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_recovery_manifest.csv")}
    timeseries_by_id = {row["scenario_id"]: row for row in timeseries_manifest}
    pair_set = set()
    for observation in observations:
        key = (observation["scenario_id"], observation["satellite_item_id"])
        if key in pair_set:
            ndvi_errors.append("duplicate scenario-item NDVI observation")
            break
        pair_set.add(key)
        if observation["satellite_datetime_utc"][:10] > dates[observation["scenario_id"]]:
            ndvi_errors.append("post-decision NDVI observation")
            break
        if observation["satellite_pixel_quality_status"] != "clear_surface_pixel":
            ndvi_errors.append("non-clear NDVI observation emitted")
            break
        red, nir = int(observation["satellite_red_dn"]), int(observation["satellite_nir_dn"])
        expected_ndvi = (nir - red) / (nir + red)
        if abs(expected_ndvi - float(observation["satellite_ndvi"])) > 0.000001:
            ndvi_errors.append("NDVI arithmetic mismatch")
            break
        provenance = observation["observation_provenance"]
        if provenance == "frozen_exact_context":
            source = base_context.get(observation["scenario_id"])
            expected_hash = source.get("response_sha256", "") if source else ""
        elif provenance == "frozen_same_window_recovery_context":
            source = recovery_context.get(observation["scenario_id"])
            expected_hash = source.get("item_response_sha256", "") if source else ""
        elif provenance == "new_predecision_stac_search":
            expected_hash = timeseries_by_id[observation["scenario_id"]]["response_sha256"]
        else:
            ndvi_errors.append("unknown NDVI observation provenance")
            break
        if observation["evidence_response_sha256"] != expected_hash:
            ndvi_errors.append("NDVI observation evidence hash does not match its declared provenance")
            break
    for manifest in timeseries_manifest:
        if manifest["source_status"] != "predecision_stac_search_retrieved_and_metadata_filtered":
            continue
        raw = enriched / manifest["raw_path"]
        if not raw.is_file() or digest(raw) != manifest["response_sha256"]:
            ndvi_errors.append(f"{manifest['scenario_id']}: raw STAC hash")
            break
    available = sum(row["ndvi_timeseries_status"].startswith("available_") for row in statuses)
    unavailable = len(statuses) - available
    audit.append(audit_row("predecision_sentinel_ndvi_timeseries", len(scenarios), len(timeseries_manifest), available, unavailable, ndvi_errors))

    divergence = read_csv(enriched / "natural_signal_divergence_candidates.csv")
    divergence_errors: List[str] = []
    if {row["scenario_id"] for row in divergence} != scenario_ids or len(divergence) != len(scenarios):
        divergence_errors.append("signal-divergence table does not cover all scenarios exactly once")
    unsafe = [row for row in divergence if "action" in row["coordinator_handling_rule"] and "non_action" not in row["coordinator_handling_rule"] and "without_forcing" not in row["coordinator_handling_rule"]]
    if unsafe:
        divergence_errors.append("signal-divergence row has an action-oriented coordinator rule")
    candidates = sum(row["candidate_status"] == "eligible_natural_signal_divergence_candidate" for row in divergence)
    audit.append(audit_row("natural_cross_source_signal_divergence", len(scenarios), len(divergence), candidates, len(divergence) - candidates, divergence_errors))

    write_csv(enriched / "advanced_enrichment_audit.csv", FIELDS, audit)
    report = [
        "# Advanced Enrichment Audit\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n",
        "| Layer | Passing | Unavailable | Result |\n| --- | ---: | ---: | --- |\n",
    ]
    report.extend(f"| {row['layer']} | {row['passing_rows']} | {row['unavailable_rows']} | {row['result']} |\n" for row in audit)
    report.extend([
        "\n## Interpretation\n",
        "- Official documents must reproduce their frozen registry SHA-256 before entering the corpus.\n",
        "- Every action quote is checked against its recorded source page.\n",
        "- Metadata filtering happens before retrieval ranking: document crop, registry geography, and effective date must all pass.\n",
        "- A login-gated public portal is evidence of unavailable anonymous district archive access, not a justification to create a district advisory.\n",
        "- Sentinel time series contain only pre-decision, clear representative-cell observations. They are not crop, disease, stage, or action labels.\n",
    ])
    (enriched / "ADVANCED_ENRICHMENT_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failed = [row for row in audit if row["result"] != "pass"]
    print(f"Advanced enrichment audit: {len(audit) - len(failed)}/{len(audit)} layers passed.")
    if failed:
        raise SystemExit("Advanced enrichment audit failure; inspect advanced_enrichment_audit.csv.")


if __name__ == "__main__":
    main()
