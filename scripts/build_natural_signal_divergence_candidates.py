"""Identify auditable, non-action cross-source signal-divergence candidates.

These rows are deliberately not labelled crop stress, disease, or irrigation
conflicts. They merely flag an observed numerical NDVI trajectory whose
direction differs from a separately scoped, retrospective NASA POWER water
context. A future coordinator can use them to evaluate whether it properly
detects and explains evidence-scope differences without manufacturing a farm
operation.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "scenario_id", "crop", "state", "district", "decision_date", "ndvi_observation_count", "ndvi_last_observation_utc",
    "ndvi_last_observation_lag_days", "ndvi_change", "ndvi_trend_direction", "nasa_weather_source_status",
    "nasa_water_context_status", "nasa_precipitation_total_mm", "nasa_precipitation_minus_land_evaporation_mm",
    "nasa_gwetroot_mean_fraction", "candidate_status", "cross_source_relation", "coordinator_handling_rule", "restriction_reason",
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


def main() -> None:
    scenario_root = PROJECT_ROOT / "data" / "scenarios"
    enriched = scenario_root / "enriched"
    scenarios = read_csv(scenario_root / "manifests" / "scenario_manifest.csv")
    features = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_timeseries_features.csv")}
    statuses = {row["scenario_id"]: row for row in read_csv(enriched / "sentinel_ndvi_timeseries_status.csv")}
    nasa_features = {row["scenario_id"]: row for row in read_csv(enriched / "nasa_power_water_context_features.csv")}
    nasa_status = {row["scenario_id"]: row for row in read_csv(enriched / "nasa_power_water_context_status.csv")}
    rows: List[Dict[str, str]] = []
    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        feature, status = features[scenario_id], statuses[scenario_id]
        water, water_status = nasa_features[scenario_id], nasa_status[scenario_id]
        row = {
            "scenario_id": scenario_id, "crop": scenario["crop"], "state": scenario["state"], "district": scenario["district"],
            "decision_date": scenario["decision_date"], "ndvi_observation_count": feature["observation_count"],
            "ndvi_last_observation_utc": feature["last_observation_utc"], "ndvi_last_observation_lag_days": "",
            "ndvi_change": feature["ndvi_change"], "ndvi_trend_direction": feature["ndvi_trend_direction"],
            "nasa_weather_source_status": water_status["weather_source_status"], "nasa_water_context_status": water_status["water_context_status"],
            "nasa_precipitation_total_mm": water["weather_precipitation_total_mm"],
            "nasa_precipitation_minus_land_evaporation_mm": water["water_precipitation_minus_land_evaporation_mm"],
            "nasa_gwetroot_mean_fraction": water["water_gwetroot_mean_fraction"], "candidate_status": "", "cross_source_relation": "",
            "coordinator_handling_rule": "", "restriction_reason": "",
        }
        if not status["ndvi_timeseries_status"].startswith("available_"):
            row.update({
                "candidate_status": "not_eligible_insufficient_clear_predecision_ndvi_series",
                "cross_source_relation": "not_evaluated", "coordinator_handling_rule": "do_not_construct_conflict_from_missing_satellite_series",
                "restriction_reason": "No three-point clear representative-cell NDVI chronology is available.",
            })
        else:
            lag = (date.fromisoformat(scenario["decision_date"]) - date.fromisoformat(feature["last_observation_utc"][:10])).days
            row["ndvi_last_observation_lag_days"] = str(lag)
            if lag > 15:
                row.update({
                    "candidate_status": "not_eligible_last_ndvi_too_distant_from_decision", "cross_source_relation": "not_evaluated",
                    "coordinator_handling_rule": "do_not_compare_distant_satellite_endpoint_to_decision_window_context",
                    "restriction_reason": "The final clear NDVI point is more than 15 days before the decision date.",
                })
            else:
                change = float(feature["ndvi_change"])
                water_balance = float(water["water_precipitation_minus_land_evaporation_mm"])
                if change <= -0.05 and water_balance >= 0:
                    relation = "ndvi_decrease_at_least_0_05_with_nonnegative_nasa_precipitation_minus_evaporation"
                elif change >= 0.05 and water_balance < 0:
                    relation = "ndvi_increase_at_least_0_05_with_negative_nasa_precipitation_minus_evaporation"
                else:
                    relation = "no_predefined_cross_source_numerical_divergence"
                if relation.startswith("no_"):
                    row.update({
                        "candidate_status": "eligible_but_no_predefined_numerical_divergence", "cross_source_relation": relation,
                        "coordinator_handling_rule": "retain_as_context_without_forcing_a_conflict", "restriction_reason": "No divergence rule matched; no conflict should be manufactured.",
                    })
                else:
                    row.update({
                        "candidate_status": "eligible_natural_signal_divergence_candidate", "cross_source_relation": relation,
                        "coordinator_handling_rule": "surface_scope_and_time_window_difference_then_keep_non_action_context_only",
                        "restriction_reason": "NDVI covers a representative cell over a 90-day chronology; NASA water values are retrospective modelled decision-window context. This is not a crop diagnosis or action trigger.",
                    })
        rows.append(row)
    write_csv(enriched / "natural_signal_divergence_candidates.csv", FIELDS, rows)
    candidates = sum(row["candidate_status"] == "eligible_natural_signal_divergence_candidate" for row in rows)
    print(f"Natural cross-source signal-divergence candidates: {candidates}/{len(rows)}; no row is a farm-action instruction.")


if __name__ == "__main__":
    main()
