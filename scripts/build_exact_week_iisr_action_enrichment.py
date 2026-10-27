"""Extract condition-gated operations from the nine exact-week IISR matches.

This builder is intentionally separate from the initial action layer.  It
accepts only the two ICAR-IISR weekly PDFs that passed the expanded source
hash, crop, Central-Zone state, and exact issue-week gates.  Every operation
keeps a verbatim source quote.  No operation is promoted to an automatic farmer
instruction when its real-world prerequisite is absent from a frozen scenario.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTION_FIELDS = [
    "action_id", "action_category", "crop", "state_scope", "season_scope", "source_document_id", "source_title",
    "provider", "official_url", "source_raw_sha256", "source_location", "source_issue_start", "source_issue_end",
    "source_quote", "operation_text", "method_text", "dose_text", "conditions_text", "operation_role",
    "requires_actual_crop_stage", "requires_field_observation", "requires_decision_time_forecast",
    "requires_soil_test_for_personalised_dose", "requires_diagnosis_or_threshold",
    "requires_documented_system_or_variety", "action_record_sha256",
]
BINDING_FIELDS = [
    "scenario_id", "action_id", "crop", "state", "district", "season", "decision_date", "source_document_id",
    "exact_week_source_scope_status", "crop_scope_status", "geography_scope_status", "season_scope_status",
    "temporal_status", "field_condition_status", "binding_status", "binding_reason", "action_record_sha256",
]
AUDIT_FIELDS = ["check", "expected", "actual", "result", "detail"]


# The quotes were read on the source PDFs and are rechecked against the
# hash-verified extraction below.  Pesticidal treatment passages are not added
# here: a dated diagnosis and an independently current label/use validation are
# absent, so recording a chemical dose would not create an executable action.
ACTION_SPECS = [
    {
        "action_id": "IISR_2023_SOYBEAN_HARVEST_90_PERCENT_YELLOW_PODS", "action_category": "harvest",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20230925", "source_location": "pdf_page_1",
        "source_quote": "Farmers are advised to harvest early maturing soybean varieties immediately after the 90% pods changes the color to yellow. This will not have adverse effect on the seed germination.",
        "operation_text": "Harvest early-maturing soybean immediately after 90% of pods turn yellow.",
        "method_text": "", "dose_text": "", "conditions_text": "Only for an observed early-maturing soybean variety with 90% yellow pods.",
        "operation_role": "source_quoted_regional_operation", "stage": True, "field": True,
    },
    {
        "action_id": "IISR_2023_SOYBEAN_HARVEST_ONLY_WITH_DRY_WINDOW", "action_category": "harvest",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20230925", "source_location": "pdf_page_1",
        "source_quote": "Farmers are advised to harvest their soybean crop while ensuring the possibility of no rains after the harvesting. Otherwise, the harvested crop gets affected due to fungal infection.",
        "operation_text": "Harvest only when a decision-time dry post-harvest weather window is supported.",
        "method_text": "", "dose_text": "", "conditions_text": "Requires observed harvest readiness and an archived decision-time forecast; historical observed weather is not a forecast.",
        "operation_role": "source_quoted_weather_guardrail", "stage": True, "forecast": True,
    },
    {
        "action_id": "IISR_2023_SOYBEAN_DRY_BEFORE_THRESHING_AND_PROTECT", "action_category": "post_harvest",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20230925", "source_location": "pdf_page_1",
        "source_quote": "The harvested crop must be threshed after sun drying. If the threshing is to be done later, it should be stored at safe place protecting from rains.",
        "operation_text": "Sun-dry harvested soybean before threshing; if delayed, store it in a place protected from rain.",
        "method_text": "", "dose_text": "", "conditions_text": "Only after actual harvest and with documented drying/storage conditions.",
        "operation_role": "source_quoted_regional_operation", "stage": True, "field": True,
    },
    {
        "action_id": "IISR_2023_SOYBEAN_DRAIN_EXCESS_WATER_AT_MATURITY", "action_category": "drainage",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20230925", "source_location": "pdf_page_1",
        "source_quote": "In event of continuous rains, farmers are advised to make necessary drainage arrangement in order to maintain the quality of the soybean produce as a result of logging situation",
        "operation_text": "Arrange drainage for a mature soybean field under continuous rain and waterlogging risk.",
        "method_text": "", "dose_text": "", "conditions_text": "Only when maturity and field-level continuous-rain/waterlogging conditions are observed.",
        "operation_role": "source_quoted_conditional_operation", "stage": True, "field": True,
    },
    {
        "action_id": "IISR_2023_SOYBEAN_VERIFY_STAGE_AND_INTENSITY_BEFORE_SPRAY", "action_category": "crop_protection_guardrail",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20230925", "source_location": "pdf_page_2",
        "source_quote": "Wherever the crop is of 80-90-day duration or at grain filling stage, the economic loss due to insect-pest-disease will be minimum. Therefore, farmers are advised to spray of insecticide/fungicides considering the crop stage and the intensity of the disease/insect.",
        "operation_text": "Do not make a routine spray decision; first verify actual crop stage and disease/insect intensity.",
        "method_text": "", "dose_text": "", "conditions_text": "Requires a dated diagnosis/threshold and observed crop stage. This row is a guardrail, not a treatment recommendation.",
        "operation_role": "source_quoted_treatment_guardrail", "stage": True, "diagnosis": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_SOW_AFTER_MONSOON_100MM", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_1",
        "source_quote": "Sowing may be done after the onset of monsoon and receipt of 100 mm rainfall.",
        "operation_text": "Sow soybean after monsoon onset and receipt of 100 mm rainfall.",
        "method_text": "", "dose_text": "100 mm rainfall threshold.", "conditions_text": "Only before actual sowing, after farm-relevant monsoon onset and cumulative rainfall are verified.",
        "operation_role": "source_quoted_conditional_operation", "stage": True, "field": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_DIVERSE_MATURITY_VARIETIES", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_1",
        "source_quote": "Grow more than 2-3 soybean varieties (having varied maturity duration) instead of one popular soybean variety.",
        "operation_text": "Use more than two to three locally recommended soybean varieties with varied maturity duration rather than one popular variety.",
        "method_text": "", "dose_text": "2-3 varieties.", "conditions_text": "Only before sowing with documented local variety suitability and seed availability.",
        "operation_role": "source_quoted_conditional_operation", "stage": True, "system": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_SPACING_DEPTH_AND_SEED_RATE", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_1",
        "source_quote": "Farmers are advised to use recommended row spacing of 45 cm and 5-10 cm plant to plant distance at 3-4 cm depth. The seed rate may be followed as 60-70 kg/ha.",
        "operation_text": "Use 45 cm rows, 5-10 cm plant spacing, 3-4 cm sowing depth, and 60-70 kg/ha seed rate.",
        "method_text": "", "dose_text": "45 cm rows; 5-10 cm plant spacing; 3-4 cm depth; 60-70 kg/ha seed rate.",
        "conditions_text": "Only during actual sowing with documented cultivar and field layout.",
        "operation_role": "source_quoted_regional_operation", "stage": True, "system": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_BBF_OR_RIDGE_FURROW", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_1",
        "source_quote": "As far as possible, try to sow soybean crop on Broad-Bed-Furrow/Ridge-Furrow planting system in order to avoid the risk of yield losses due aberrant weather conditions (drought or scanty/heavy/continued rains).",
        "operation_text": "Where feasible, sow soybean using a Broad-Bed-Furrow or Ridge-Furrow planting system.",
        "method_text": "Broad-Bed-Furrow/Ridge-Furrow planting system.", "dose_text": "", "conditions_text": "Only before sowing after field feasibility and planting-system availability are verified.",
        "operation_role": "source_quoted_conditional_operation", "stage": True, "system": True, "field": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_KEEP_SEED_AND_FERTILIZER_SEPARATE", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_2",
        "source_quote": "Farmers are advised not to mix seed along with fertilizers while sowing. Instead, they may use seed-cum-fertilizer seed drill for sowing OR broadcast the fertilizers just before the sowing.",
        "operation_text": "Do not mix seed with fertilizer while sowing; use a seed-cum-fertilizer drill or broadcast fertilizer just before sowing.",
        "method_text": "Seed-cum-fertilizer drill or fertilizer broadcast immediately before sowing.", "dose_text": "", "conditions_text": "Only during actual sowing and with documented equipment/method.",
        "operation_role": "source_quoted_regional_operation", "stage": True, "system": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_CENTRAL_ZONE_NUTRIENT_BASELINE", "action_category": "fertilizer",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_2",
        "source_quote": "Farmers are advised to apply the recommended quantity of all the nutrients (25:60:40:20 N:P2O5:K2O:S kg/ha) at the time of sowing only.",
        "operation_text": "Apply the Central Zone nutrient baseline at sowing only.",
        "method_text": "Broadcast fertilizer sources just before sowing or use a seed-cum-fertilizer drill during sowing.", "dose_text": "25:60:40:20 N:P2O5:K2O:S kg/ha.",
        "conditions_text": "Only at actual sowing. This is a regional baseline; a farm-specific adjustment requires a soil test.",
        "operation_role": "source_quoted_regional_baseline", "stage": True, "soil": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_ORGANIC_SEED_TREATMENT", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_2",
        "source_quote": "In case of organic soybean production, farmers are advised to use Trichoderma viride + Bradyrhizobium japonicum+PSB cultures/liquid biofertilizer/consortia during sowing operation (Table 1).",
        "operation_text": "For organic soybean production, use the listed Trichoderma, Bradyrhizobium japonicum, and PSB culture options during sowing.",
        "method_text": "Seed treatment during sowing.", "dose_text": "The quoted line refers to Table 1; no dose is emitted from this record.", "conditions_text": "Only for documented organic soybean production during actual sowing.",
        "operation_role": "source_quoted_conditional_operation", "stage": True, "system": True,
    },
    {
        "action_id": "IISR_2024_SOYBEAN_RAINFED_PIGEONPEA_INTERCROP", "action_category": "crop_establishment",
        "source_document_id": "ICAR_IISR_WEEKLY_SOYBEAN_20240624", "source_location": "pdf_page_2",
        "source_quote": "Growing of soybean with Pigeonpea in 4:2 is found most remunerative in case of rainfed farming systems.",
        "operation_text": "For a documented rainfed system, use soybean-pigeonpea intercropping at a 4:2 ratio.",
        "method_text": "Soybean-pigeonpea intercropping.", "dose_text": "4:2 ratio.", "conditions_text": "Only before sowing after the rainfed farming system and cropping plan are documented.",
        "operation_role": "source_quoted_conditional_operation", "stage": True, "system": True,
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


def normalise(value: str) -> str:
    """Normalize only known PDF line-wrap/extraction artifacts before quote check.

    The stored quote follows the visually reviewed source PDF.  These targeted
    repairs reconcile pypdf's spaces inserted inside words or around hyphens
    at a line break; they do not rewrite a recommendation's wording or dose.
    """
    value = re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()
    for extracted, printed in (
        ("m ake", "make"), ("m inimum", "minimum"), ("80 -90", "80-90"),
        ("insect - pest", "insect-pest"), ("Broad -Bed", "Broad-Bed"),
        ("Ridge- Furrow", "Ridge-Furrow"), ("seed- cum", "seed-cum"),
        ("japonicum +PSB", "japonicum+PSB"),
    ):
        value = value.replace(extracted, printed)
    return value


def canonical_hash(row: Mapping[str, str]) -> str:
    payload = {field: row.get(field, "") for field in ACTION_FIELDS if field != "action_record_sha256"}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def condition_reason(spec: Mapping[str, object]) -> str:
    required = []
    if spec.get("stage"):
        required.append("actual_crop_stage")
    if spec.get("field"):
        required.append("documented_field_condition")
    if spec.get("forecast"):
        required.append("decision_time_forecast")
    if spec.get("soil"):
        required.append("soil_test_for_personalised_dose")
    if spec.get("diagnosis"):
        required.append("dated_diagnosis_or_threshold")
    if spec.get("system"):
        required.append("documented_system_or_variety")
    return ";".join(required) or "no_additional_condition"


def audit_row(check: str, expected: int, actual: int, errors: List[str]) -> Dict[str, str]:
    return {"check": check, "expected": str(expected), "actual": str(actual), "result": "pass" if not errors else "fail", "detail": "; ".join(errors[:6]) if errors else "validated"}


def main() -> None:
    scenario_root = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenario_root / "enriched"
    scenarios = read_csv(scenario_root / "manifests" / "scenario_manifest.csv")
    inventory = {row["source_document_id"]: row for row in read_csv(enriched / "expanded_official_rag_source_inventory.csv")}
    scope = {(row["scenario_id"], row["source_document_id"]): row for row in read_csv(enriched / "scenario_expanded_rag_scope.csv")}
    source_text: Dict[str, Dict[str, str]] = {}
    for source_id in {str(spec["source_document_id"]) for spec in ACTION_SPECS}:
        source = inventory.get(source_id)
        if source is None or not source["admission_status"].startswith("admitted_"):
            raise SystemExit(f"Required exact-week source is not admitted: {source_id}")
        document = json.loads((enriched / source["extracted_text_path"]).read_text(encoding="utf-8"))
        source_text[source_id] = dict(document["sections"])

    actions: List[Dict[str, str]] = []
    quote_errors: List[str] = []
    for spec in ACTION_SPECS:
        source_id = str(spec["source_document_id"])
        source = inventory[source_id]
        quote = str(spec["source_quote"])
        location = str(spec["source_location"])
        if normalise(quote) not in normalise(source_text[source_id].get(location, "")):
            quote_errors.append(f"{spec['action_id']}: quote missing from {source_id}:{location}")
            continue
        row = {
            "action_id": str(spec["action_id"]), "action_category": str(spec["action_category"]), "crop": "soybean",
            "state_scope": "Madhya Pradesh;Rajasthan", "season_scope": "kharif", "source_document_id": source_id,
            "source_title": source["source_title"], "provider": source["provider"], "official_url": source["official_url"],
            "source_raw_sha256": source["raw_sha256"], "source_location": location, "source_issue_start": source["issue_start"],
            "source_issue_end": source["issue_end"], "source_quote": quote, "operation_text": str(spec["operation_text"]),
            "method_text": str(spec["method_text"]), "dose_text": str(spec["dose_text"]), "conditions_text": str(spec["conditions_text"]),
            "operation_role": str(spec["operation_role"]), "requires_actual_crop_stage": str(bool(spec.get("stage"))).lower(),
            "requires_field_observation": str(bool(spec.get("field"))).lower(),
            "requires_decision_time_forecast": str(bool(spec.get("forecast"))).lower(),
            "requires_soil_test_for_personalised_dose": str(bool(spec.get("soil"))).lower(),
            "requires_diagnosis_or_threshold": str(bool(spec.get("diagnosis"))).lower(),
            "requires_documented_system_or_variety": str(bool(spec.get("system"))).lower(), "action_record_sha256": "",
        }
        row["action_record_sha256"] = canonical_hash(row)
        actions.append(row)
    if quote_errors:
        raise SystemExit("; ".join(quote_errors))

    bindings: List[Dict[str, str]] = []
    for scenario in scenarios:
        for action in actions:
            source_scope = scope.get((scenario["scenario_id"], action["source_document_id"]), {})
            exact_scope = source_scope.get("rag_scope_status", "missing_expanded_source_scope")
            crop_status = "pass_crop_scope" if scenario["crop"] == "soybean" else "blocked_crop_scope"
            geography_status = "pass_central_zone_state_scope" if scenario["state"] in {"Madhya Pradesh", "Rajasthan"} else "blocked_central_zone_state_scope"
            season_status = "pass_season_scope" if scenario["season"] == "kharif" else "blocked_season_scope"
            temporal_status = "pass_exact_issue_week" if exact_scope == "admitted_dated_advisory_to_metadata_filtered_rag" else "blocked_exact_issue_week"
            applicable = all(value.startswith("pass_") for value in (crop_status, geography_status, season_status, temporal_status))
            spec = next(item for item in ACTION_SPECS if item["action_id"] == action["action_id"])
            pending = condition_reason(spec)
            if not applicable:
                binding_status = "blocked_exact_week_source_scope"
                reason = "The action's source did not pass crop, Central-Zone state, season, and exact-week metadata gates for this scenario."
                field_status = "not_evaluated_outside_exact_week_source_scope"
            else:
                binding_status = "conditionally_applicable_pending_unobserved_farm_condition"
                reason = pending
                field_status = "missing_in_frozen_scenario:" + pending
            bindings.append({
                "scenario_id": scenario["scenario_id"], "action_id": action["action_id"], "crop": scenario["crop"],
                "state": scenario["state"], "district": scenario["district"], "season": scenario["season"], "decision_date": scenario["decision_date"],
                "source_document_id": action["source_document_id"], "exact_week_source_scope_status": exact_scope,
                "crop_scope_status": crop_status, "geography_scope_status": geography_status, "season_scope_status": season_status,
                "temporal_status": temporal_status, "field_condition_status": field_status, "binding_status": binding_status,
                "binding_reason": reason, "action_record_sha256": action["action_record_sha256"],
            })

    audit: List[Dict[str, str]] = []
    source_errors = []
    for action in actions:
        source = inventory[action["source_document_id"]]
        raw = enriched / source["raw_path"]
        if not raw.is_file() or sha256(raw.read_bytes()).hexdigest() != action["source_raw_sha256"]:
            source_errors.append(f"{action['action_id']}: source raw hash mismatch")
    audit.append(audit_row("exact_week_source_quotes_and_hashes", len(actions), len(actions), source_errors))
    expected_pairs = {(scenario["scenario_id"], action["action_id"]) for scenario in scenarios for action in actions}
    actual_pairs = {(row["scenario_id"], row["action_id"]) for row in bindings}
    binding_errors = []
    if len(bindings) != len(actual_pairs) or actual_pairs != expected_pairs:
        binding_errors.append("scenario-action Cartesian coverage/uniqueness failure")
    unsafe = [row for row in bindings if row["binding_status"] == "source_scoped_eligible"]
    if unsafe:
        binding_errors.append("unexpected automatically executable action")
    audit.append(audit_row("exact_week_action_scope_and_conditions", len(expected_pairs), len(bindings), binding_errors))
    active = [row for row in bindings if row["binding_status"] == "conditionally_applicable_pending_unobserved_farm_condition"]
    if len(active) != 57:
        binding_errors = [f"expected 57 source-scoped conditional rows but found {len(active)}"]
    else:
        binding_errors = []
    audit.append(audit_row("exact_week_matching_scenario_operation_pairs", 57, len(active), binding_errors))

    write_csv(enriched / "exact_week_iisr_action_records.csv", ACTION_FIELDS, actions)
    write_csv(enriched / "scenario_exact_week_iisr_action_bindings.csv", BINDING_FIELDS, bindings)
    write_csv(enriched / "exact_week_iisr_action_audit.csv", AUDIT_FIELDS, audit)
    report = [
        "# Exact-Week ICAR-IISR Action Enrichment\n\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n\n",
        f"- Source-quoted, hash-checked action/guardrail records: {len(actions)}\n",
        f"- Complete scenario × action scope rows: {len(bindings)}\n",
        f"- Exact-week source-scoped conditional operation rows: {len(active)}\n",
        "- Automatically executable farm actions: 0\n\n",
        "## Rules\n\n",
        "- A source quote is checked against the extracted page of a hash-verified PDF.\n",
        "- A row must pass soybean, Central-Zone state, kharif, and exact advisory-week gates before its farm conditions are even considered.\n",
        "- Historical observed weather is not a decision-time forecast.\n",
        "- Regional nutrient baseline language is not a farm-specific fertilizer prescription.\n",
        "- The crop-protection row is a diagnosis/stage guardrail; no chemical treatment is emitted.\n",
    ]
    (enriched / "EXACT_WEEK_IISR_ACTION_ENRICHMENT.md").write_text("".join(report), encoding="utf-8")
    failures = [row for row in audit if row["result"] != "pass"]
    print(f"Exact-week IISR action enrichment: {len(actions)} records; {len(bindings)} bindings; {len(active)} conditional exact-week rows; {len(failures)} audit failures.")
    if failures:
        raise SystemExit("Exact-week IISR action enrichment audit failure.")


if __name__ == "__main__":
    main()
