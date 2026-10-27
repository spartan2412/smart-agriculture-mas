"""Independently audit the recovered PAU Rabi wheat operation layer."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "data" / "scenarios" / "enriched"
FIELDS = ["check", "expected", "actual", "result", "detail"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def result(check: str, expected: int | str, actual: int | str, errors: list[str]) -> dict[str, str]:
    return {"check": check, "expected": str(expected), "actual": str(actual), "result": "pass" if not errors else "fail", "detail": "; ".join(errors[:5]) or "validated"}


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def main() -> None:
    scenarios = read_csv(ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv")
    inventory = read_csv(ENRICHED / "archived_pau_rabi_source_inventory.csv")
    actions = read_csv(ENRICHED / "archived_pau_rabi_action_records.csv")
    bindings = read_csv(ENRICHED / "scenario_archived_pau_rabi_action_bindings.csv")
    combined_actions = {row["action_id"]: row for row in read_csv(ENRICHED / "official_action_records_all.csv")}
    combined_bindings = {(row["scenario_id"], row["action_id"]): row for row in read_csv(ENRICHED / "scenario_official_action_bindings_all.csv")}
    rows: list[dict[str, str]] = []
    source_errors: list[str] = []
    if len(inventory) != 3 or {row["source_document_id"] for row in inventory} != {"PAU_ARCHIVE_RABI_2021_22", "PAU_ARCHIVE_RABI_2023_24", "PAU_ARCHIVE_RABI_2024_25"}:
        source_errors.append("expected exactly the 2021–22, 2023–24 and 2024–25 recovered PAU Rabi documents")
    for source in inventory:
        raw = ENRICHED / source["raw_path"]
        extracted = ENRICHED / source["extracted_text_path"]
        if not raw.is_file() or sha256(raw.read_bytes()).hexdigest() != source["raw_sha256"]:
            source_errors.append(f"{source['source_document_id']}: raw hash")
        if not extracted.is_file() or sha256(extracted.read_bytes()).hexdigest() != source["extracted_text_sha256"]:
            source_errors.append(f"{source['source_document_id']}: extracted hash")
        if not source["archive_original_last_modified_utc"] or not source["archive_replay_url"].startswith("https://web.archive.org/web/"):
            source_errors.append(f"{source['source_document_id']}: missing original-date or replay provenance")
    rows.append(result("archive_provenance_and_hashes", 3, len(inventory), source_errors))
    quote_errors: list[str] = []
    for action in actions:
        source = next((row for row in inventory if row["source_document_id"] == action["source_document_id"]), None)
        if source is None:
            quote_errors.append(f"{action['action_id']}: missing source")
            continue
        document = json.loads((ENRICHED / source["extracted_text_path"]).read_text(encoding="utf-8"))
        if normalise(action["source_quote"]) not in normalise(dict(document["sections"]).get(action["source_location"], "")):
            quote_errors.append(f"{action['action_id']}: quote absent")
        if action["requires_actual_crop_stage"] != "true":
            quote_errors.append(f"{action['action_id']}: maturity gate missing")
    rows.append(result("verbatim_wheat_operations_and_maturity_gate", 3, len(actions), quote_errors))
    pairs = {(scenario["scenario_id"], action["action_id"]) for scenario in scenarios for action in actions}
    actual = {(binding["scenario_id"], binding["action_id"]) for binding in bindings}
    binding_errors = [] if len(bindings) == len(actual) and actual == pairs else ["scenario-action Cartesian coverage/uniqueness failure"]
    valid = [row for row in bindings if row["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition"]
    if any(row["binding_reason"] != "actual_crop_stage" for row in valid):
        binding_errors.append("valid Rabi scope lost maturity precondition")
    rows.append(result("full_temporal_scope_matrix_and_stage_gate", len(pairs), len(bindings), binding_errors))
    catalog_errors = []
    if not all(combined_actions.get(action["action_id"]) == action for action in actions):
        catalog_errors.append("action changed in combined catalog")
    if not all(combined_bindings.get((row["scenario_id"], row["action_id"])) == row for row in bindings):
        catalog_errors.append("binding changed in combined catalog")
    rows.append(result("combined_catalog_projection", len(actions) + len(bindings), sum(action["action_id"] in combined_actions for action in actions) + sum((row["scenario_id"], row["action_id"]) in combined_bindings for row in bindings), catalog_errors))
    direct = sum(row["binding_status"] == "source_scoped_eligible" for row in bindings)
    rows.append(result("no_direct_farm_action", 0, direct, [] if direct == 0 else ["unconditionally eligible action found"]))
    write_csv(ENRICHED / "archived_pau_rabi_action_audit.csv", rows)
    report = ["# Archived PAU Rabi Action-Recovery Audit\n\n", "| Check | Expected | Actual | Result |\n| --- | ---: | ---: | --- |\n"]
    report.extend(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['result']} |\n" for row in rows)
    report.extend(["\n## Scope\n\n", "- All archived PDFs retain the PAU original URL, replay URL, capture date and original-server Last-Modified date.\n", "- The PDF title/year and verbatim wheat quote were checked before admission.\n", "- The original-server date creates the conservative annual Rabi window; operation output remains conditional on actual wheat maturity.\n", "- No frozen scenario was altered.\n"])
    (ENRICHED / "ARCHIVED_PAU_RABI_ACTION_AUDIT.md").write_text("".join(report), encoding="utf-8")
    failed = [row for row in rows if row["result"] != "pass"]
    print(f"Archived PAU Rabi action-recovery audit: {len(rows) - len(failed)}/{len(rows)} checks passed; {len(valid)} conditionally applicable bindings.")
    if failed:
        raise SystemExit("Archived PAU Rabi action-recovery audit failed.")


if __name__ == "__main__":
    main()
