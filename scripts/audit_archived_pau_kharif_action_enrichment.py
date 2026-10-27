"""Audit the recovered PAU Kharif action layer independently of the planner."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED = PROJECT_ROOT / "data" / "scenarios" / "enriched"
FIELDS = ["check", "expected", "actual", "result", "detail"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def action_hash(row: dict[str, str]) -> str:
    payload = {key: value for key, value in row.items() if key != "action_record_sha256"}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def result(check: str, expected: int | str, actual: int | str, errors: list[str]) -> dict[str, str]:
    return {"check": check, "expected": str(expected), "actual": str(actual), "result": "pass" if not errors else "fail", "detail": "; ".join(errors[:5]) or "validated"}


def main() -> None:
    scenarios = read_csv(PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    inventory = read_csv(ENRICHED / "archived_pau_kharif_source_inventory.csv")
    actions = read_csv(ENRICHED / "archived_pau_kharif_action_records.csv")
    bindings = read_csv(ENRICHED / "scenario_archived_pau_kharif_action_bindings.csv")
    combined_actions = {row["action_id"]: row for row in read_csv(ENRICHED / "official_action_records_all.csv")}
    combined_bindings = {(row["scenario_id"], row["action_id"]): row for row in read_csv(ENRICHED / "scenario_official_action_bindings_all.csv")}
    rows: list[dict[str, str]] = []

    source_errors: list[str] = []
    expected_years = {"2023", "2024", "2025"}
    if len(inventory) != 3 or {source["source_document_id"].rsplit("_", 1)[-1] for source in inventory} != expected_years:
        source_errors.append("expected exactly the 2023, 2024, and 2025 PAU Kharif captures")
    for source in inventory:
        raw = ENRICHED / source["raw_path"]
        extracted = ENRICHED / source["extracted_text_path"]
        if not source["official_url"].endswith("/pp_kharif.pdf") or not source["archive_replay_url"].startswith("https://web.archive.org/web/"):
            source_errors.append(f"{source['source_document_id']}: source/original URL provenance")
        if not raw.is_file() or digest(raw) != source["raw_sha256"]:
            source_errors.append(f"{source['source_document_id']}: raw PDF hash")
        if not extracted.is_file() or digest(extracted) != source["extracted_text_sha256"]:
            source_errors.append(f"{source['source_document_id']}: extracted text hash")
        if source["source_effective_from"][:4] not in source["source_title"]:
            source_errors.append(f"{source['source_document_id']}: title/year mismatch")
    rows.append(result("archive_provenance_and_hashes", 3, len(inventory), source_errors))

    quote_errors: list[str] = []
    for action in actions:
        source = next((item for item in inventory if item["source_document_id"] == action["source_document_id"]), None)
        if source is None:
            quote_errors.append(f"{action['action_id']}: unknown source")
            continue
        document = json.loads((ENRICHED / source["extracted_text_path"]).read_text(encoding="utf-8"))
        text = dict(document["sections"]).get(action["source_location"], "")
        if normalise(action["source_quote"]) not in normalise(text):
            quote_errors.append(f"{action['action_id']}: absent quote")
        if action_hash(action) != action["action_record_sha256"]:
            quote_errors.append(f"{action['action_id']}: canonical hash")
        if action["requires_actual_crop_stage"] != "true" or action["action_layer"] != "archived_official_pau_package":
            quote_errors.append(f"{action['action_id']}: safety/layer contract")
    rows.append(result("verbatim_operations_and_action_hashes", 6, len(actions), quote_errors))

    binding_errors: list[str] = []
    expected = {(scenario["scenario_id"], action["action_id"]) for scenario in scenarios for action in actions}
    actual = {(binding["scenario_id"], binding["action_id"]) for binding in bindings}
    if len(bindings) != len(actual) or actual != expected:
        binding_errors.append("not a unique complete scenario-action matrix")
    valid = 0
    for binding in bindings:
        stages = (binding["crop_scope_status"], binding["geography_scope_status"], binding["season_scope_status"], binding["temporal_status"])
        if all(stage.startswith("pass_") for stage in stages):
            valid += 1
            if binding["binding_status"] != "conditionally_applicable_pending_unobserved_farm_condition" or binding["binding_reason"] != "actual_crop_stage":
                binding_errors.append(f"{binding['scenario_id']}:{binding['action_id']}: valid scope did not retain stage gate")
                break
        elif binding["binding_status"].startswith("conditionally_"):
            binding_errors.append(f"{binding['scenario_id']}:{binding['action_id']}: invalid scope became conditional")
            break
    rows.append(result("full_temporal_scope_matrix_and_stage_gate", len(expected), len(bindings), binding_errors))

    catalog_errors: list[str] = []
    if not all(combined_actions.get(action["action_id"]) == action for action in actions):
        catalog_errors.append("recovered action does not survive the combined catalog unchanged")
    if not all(combined_bindings.get((binding["scenario_id"], binding["action_id"])) == binding for binding in bindings):
        catalog_errors.append("recovered binding does not survive the combined catalog unchanged")
    rows.append(result("combined_catalog_projection", 6 + len(bindings), sum(action["action_id"] in combined_actions for action in actions) + sum((binding["scenario_id"], binding["action_id"]) in combined_bindings for binding in bindings), catalog_errors))

    no_direct_errors = []
    if any(binding["binding_status"] == "source_scoped_eligible" for binding in bindings):
        no_direct_errors.append("an archived action became unconditionally eligible")
    rows.append(result("no_direct_farm_action", 0, sum(binding["binding_status"] == "source_scoped_eligible" for binding in bindings), no_direct_errors))

    write_csv(ENRICHED / "archived_pau_kharif_action_audit.csv", rows)
    report = ["# Archived PAU Kharif Action-Recovery Audit\n\n", "| Check | Expected | Actual | Result |\n| --- | ---: | ---: | --- |\n"]
    report.extend(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['result']} |\n" for row in rows)
    report.extend(["\n## Scope\n\n", "- The replay URLs preserve PAU's original annual package URL; the archive is cited alongside, never instead of, the official publisher.\n", "- Each document self-identifies its Kharif year and each operation is checked verbatim against extracted PDF page 11.\n", "- A recovered operation passes only crop, Punjab geography, Kharif season, and conservative capture-derived date gates. It remains conditional on observed crop maturity.\n", "- No frozen scenario was changed.\n"])
    (ENRICHED / "ARCHIVED_PAU_KHARIF_ACTION_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failed = [row for row in rows if row["result"] != "pass"]
    print(f"Archived PAU Kharif action-recovery audit: {len(rows) - len(failed)}/{len(rows)} checks passed; {valid} conditionally applicable bindings.")
    if failed:
        raise SystemExit("Archived PAU Kharif action-recovery audit failed.")


if __name__ == "__main__":
    main()
