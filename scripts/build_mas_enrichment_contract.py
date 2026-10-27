"""Create the scenario-level contract that governs MAS use of enriched evidence.

The contract deliberately describes what an agent *may* say for each frozen
scenario.  It makes unobserved field signals machine-readable abstentions,
instead of letting an agent infer a field action from regional or
representative-cell context.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "scenario_id", "weather_water_context", "soil_context", "satellite_context", "satellite_feature_artifact", "market_context",
    "regional_calendar_context", "fertilizer_policy_context", "crop_protection_policy_context",
    "irrigation_action_agent", "fertilizer_prescription_agent", "pesticide_treatment_agent",
    "crop_stage_agent", "disease_diagnosis_agent", "leaf_vision_agent", "mas_output_rule",
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


def index_rows(rows: Sequence[Mapping[str, str]], name: str) -> Dict[str, Mapping[str, str]]:
    indexed = {row["scenario_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"{name} contains duplicate scenario IDs.")
    return indexed


def main() -> None:
    scenarios = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenarios / "enriched"
    manifest = read_csv(scenarios / "manifests" / "scenario_manifest.csv")
    expected = {row["scenario_id"] for row in manifest}
    sources = {
        "processed": index_rows(read_csv(scenarios / "processed" / "scenario_features.csv"), "processed features"),
        "evidence": index_rows(read_csv(scenarios / "evidence" / "scenario_evidence_status.csv"), "evidence status"),
        "water": index_rows(read_csv(enriched / "nasa_power_water_context_status.csv"), "NASA water status"),
        "satellite": index_rows(read_csv(enriched / "sentinel_ndvi_context_status.csv"), "Sentinel status"),
        "satellite_recovery": index_rows(read_csv(enriched / "sentinel_ndvi_recovery_status.csv"), "Sentinel recovery status"),
        "market": index_rows(read_csv(enriched / "agmarknet_embedded_market_context_status.csv"), "Agmarknet status"),
        "policy": index_rows(read_csv(enriched / "management_policy_features.csv"), "management policy"),
    }
    for name, indexed in sources.items():
        if name == "satellite_recovery":
            continue
        if set(indexed) != expected:
            raise ValueError(f"{name} does not have exact one-to-one frozen scenario coverage.")
    recovery_expected = {
        scenario_id for scenario_id, row in sources["satellite"].items()
        if not row["satellite_condition_status"].startswith("available")
    }
    if set(sources["satellite_recovery"]) != recovery_expected:
        raise ValueError("Sentinel recovery rows do not exactly cover base satellite abstentions.")

    records = []
    for row in manifest:
        scenario_id = row["scenario_id"]
        processed, evidence = sources["processed"][scenario_id], sources["evidence"][scenario_id]
        water, satellite = sources["water"][scenario_id], sources["satellite"][scenario_id]
        recovery = sources["satellite_recovery"].get(scenario_id)
        market, policy = sources["market"][scenario_id], sources["policy"][scenario_id]
        soil_available = all(processed.get(key, "") != "" for key in ("soil_phh2o_raw", "soil_clay_raw", "soil_sand_raw", "soil_silt_raw", "soil_ocd_raw"))
        records.append({
            "scenario_id": scenario_id,
            "weather_water_context": "",
            "soil_context": "available_static_soilgrids_context_no_field_npk_or_moisture" if soil_available else "unavailable_static_soil_context",
            "satellite_context": "",
            "satellite_feature_artifact": "",
            "market_context": (
                "available_historical_official_report_comparison_no_forecast"
                if market["market_context_status"].startswith("available") else "abstain_no_official_report_comparator"
            ),
            "regional_calendar_context": "available_declared_regional_season_window_not_observed_field_stage",
            "fertilizer_policy_context": "available_regional_baseline_policy_not_farm_specific_dose",
            "crop_protection_policy_context": "available_conditional_regional_ipm_policy_not_a_treatment_order",
            "irrigation_action_agent": "abstain_no_field_moisture_or_decision_time_forecast",
            "fertilizer_prescription_agent": "abstain_no_field_soil_test_or_actual_crop_stage",
            "pesticide_treatment_agent": "abstain_no_dated_diagnosis_or_threshold_event",
            "crop_stage_agent": evidence["crop_stage_status"],
            "disease_diagnosis_agent": evidence["disease_event_status"],
            "leaf_vision_agent": "abstain_no_aligned_field_leaf_image",
            "mas_output_rule": "context_explanation_and_evidence_trace_only_no_direct_farm_action",
        })
        if (
            policy["fertilizer_actionability"] != "regional_policy_reference_only_field_soil_test_and_actual_stage_required"
            or policy["protection_actionability"] != "conditional_IPM_policy_only_diagnosis_or_threshold_event_required"
        ):
            raise ValueError(f"{scenario_id} violates the frozen management policy actionability contract.")
        if water["water_context_status"] != "available_retrospective_context_only":
            raise ValueError(f"{scenario_id} lacks the expected NASA historical context status.")
    # The list comprehension above keeps the policy checks next to the source
    # data; assign weather context after verification so it cannot be inferred.
    for record in records:
        record["weather_water_context"] = "available_historical_observed_and_modelled_context_no_forecast"
        scenario_id = record["scenario_id"]
        base = sources["satellite"][scenario_id]
        recovery = sources["satellite_recovery"].get(scenario_id)
        if base["satellite_condition_status"].startswith("available"):
            record["satellite_context"] = "available_representative_cell_ndvi_context_not_crop_or_field_label"
            record["satellite_feature_artifact"] = "sentinel_ndvi_context_features.csv"
        elif recovery and recovery["satellite_recovery_status"] == "recovered_clear_point_ndvi_from_alternate_frozen_window_candidate":
            record["satellite_context"] = "available_recovered_representative_cell_ndvi_context_not_crop_or_field_label"
            record["satellite_feature_artifact"] = "sentinel_ndvi_recovery_features.csv"
        else:
            record["satellite_context"] = "abstain_exact_frozen_scene_or_pixel_context_unavailable"
            record["satellite_feature_artifact"] = "none"
    write_csv(enriched / "mas_enrichment_contract.csv", FIELDS, records)
    print(f"Wrote MAS enrichment contract for {len(records)}/{len(manifest)} frozen scenarios.")


if __name__ == "__main__":
    main()
