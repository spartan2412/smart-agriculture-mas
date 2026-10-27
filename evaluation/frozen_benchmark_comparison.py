"""Create reproducible paper tables and figures from persisted A0--A6 runs.

This module reads only committed benchmark-result artifacts.  It never calls
the legacy prototype, regenerates scenarios, invokes an LLM, or changes a
normal trace.  The comparison is exhaustive over the fixed 300-scenario
population, so it reports paired structural rates and count differences rather
than pretending that the oracle supplies farm-outcome accuracy labels.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_ROOT = PROJECT_ROOT / "results"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_ROOT / "derived-architecture-comparison"


@dataclass(frozen=True)
class SystemSpec:
    system_id: str
    result_directory: str
    label: str
    comparison_role: str


SYSTEMS: tuple[SystemSpec, ...] = (
    SystemSpec("A0", "v2_2-e0-full-mas", "A0 Full MAS", "Proposed farmer-facing reference"),
    SystemSpec("A1", "v2_2-a1-regional-plan-only", "A1 Regional plan only", "Coordinated-MAS baseline"),
    SystemSpec("A2", "v2_2-a2-centralized-rag", "A2 Centralized RAG", "Multi-agent decomposition baseline"),
    SystemSpec("A3", "v2_2-a3-no-scoped-rag", "A3 No scoped RAG", "Scoped retrieval / operation recovery ablation"),
    SystemSpec("A4", "v2_2-a4-no-regional-plans", "A4 No regional plans", "Third-enrichment ablation"),
    SystemSpec("A5", "v2_2-a5-no-provenance-gates", "A5 No alignment gates", "Integrity-gate ablation; evaluation only"),
    SystemSpec("A6", "v2_2-a6-conflict-ablation", "A6 No conflict coordinator", "Conflict-resolution ablation"),
)

KEY_METRICS: tuple[str, ...] = (
    "overall_structural_pass",
    "grounded_plan_coverage",
    "conditional_operation_completeness",
    "operation_binding_and_condition_compliance",
    "plan_and_selected_operation_citation_coverage",
    "rag_scope_compliance",
    "conflict_trace_completeness_and_exclusion",
    "unsupported_action_prevention_and_agent_permissions",
)

HEATMAP_METRICS: tuple[str, ...] = (
    "overall_structural_pass",
    "abstention_reason_coverage",
    "citation_traceability",
    "conditional_operation_completeness",
    "grounded_plan_coverage",
    "operation_binding_and_condition_compliance",
    "plan_and_selected_operation_citation_coverage",
    "rag_scope_compliance",
    "conflict_trace_completeness_and_exclusion",
    "unsupported_action_prevention_and_agent_permissions",
    "vision_no_data_boundary",
)

METRIC_LABELS = {
    "overall_structural_pass": "All structural checks",
    "abstention_reason_coverage": "Abstention reason",
    "citation_traceability": "Citation traceability",
    "conditional_operation_completeness": "Conditional operations",
    "grounded_plan_coverage": "Grounded plan coverage",
    "operation_binding_and_condition_compliance": "Operation binding + condition",
    "plan_and_selected_operation_citation_coverage": "Plan citation coverage",
    "rag_scope_compliance": "RAG scope",
    "conflict_trace_completeness_and_exclusion": "Conflict trace",
    "unsupported_action_prevention_and_agent_permissions": "Safety / permissions",
    "vision_no_data_boundary": "Vision no-data boundary",
}


class ComparisonIntegrityError(ValueError):
    """Raised when persisted run artifacts cannot support a fair comparison."""


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ComparisonIntegrityError(f"Required comparison artifact is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComparisonIntegrityError(f"Invalid JSON artifact: {path}") from exc


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_metadata() -> dict[str, Any]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.STDOUT
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        return {"commit": commit, "clean": not bool(status), "status": status}
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - environment failure
        return {"status": "unavailable", "error": type(exc).__name__}


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _rate_map(aggregate: Mapping[str, Any]) -> dict[str, float]:
    metrics = aggregate.get("metrics")
    if not isinstance(metrics, list):
        raise ComparisonIntegrityError("Aggregate oracle report has no metrics list.")
    parsed: dict[str, float] = {}
    for row in metrics:
        name = str(row.get("name", ""))
        if not name:
            raise ComparisonIntegrityError("Aggregate oracle report has an unnamed metric.")
        parsed[name] = float(row["rate"])
    return parsed


def _metric_count_map(aggregate: Mapping[str, Any]) -> dict[str, tuple[int, int, float]]:
    return {
        str(row["name"]): (int(row["passed"]), int(row["total"]), float(row["rate"]))
        for row in aggregate["metrics"]
    }


def _verified_artifact_map(manifest: Mapping[str, Any]) -> dict[str, str]:
    protocol = manifest.get("protocol", {})
    verified = protocol.get("verified_artifacts", []) if isinstance(protocol, Mapping) else []
    if not isinstance(verified, list) or not verified:
        raise ComparisonIntegrityError("Run manifest lacks protocol verified-artifact hashes.")
    mapping = {str(row["path"]): str(row["sha256"]) for row in verified}
    if len(mapping) != len(verified):
        raise ComparisonIntegrityError("Run manifest has duplicated verified-artifact paths.")
    return mapping


def _csv_write(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    escaped_headers = [str(header) for header in headers]
    body = [[str(value).replace("|", "\\|") for value in row] for row in rows]
    return "\n".join([
        "| " + " | ".join(escaped_headers) + " |",
        "| " + " | ".join("---" for _ in escaped_headers) + " |",
        *("| " + " | ".join(row) + " |" for row in body),
    ])


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _short_metric(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " "))


@dataclass(frozen=True)
class LoadedSystem:
    spec: SystemSpec
    manifest: Mapping[str, Any]
    aggregate: Mapping[str, Any]
    stratified: Mapping[str, Any]
    batch_summary: Mapping[str, Any]

    @property
    def rates(self) -> dict[str, float]:
        return _rate_map(self.aggregate)

    @property
    def counts(self) -> dict[str, tuple[int, int, float]]:
        return _metric_count_map(self.aggregate)


def _load_system(results_root: Path, spec: SystemSpec) -> LoadedSystem:
    directory = results_root / spec.result_directory
    manifest = _read_json(directory / "run_manifest.json")
    aggregate = _read_json(directory / "aggregate_oracle_result.json")
    stratified = _read_json(directory / "stratified_oracle_result.json")
    batch_summary = _read_json(directory / "batch_summary.json")
    if manifest.get("system_id") != spec.system_id:
        raise ComparisonIntegrityError(
            f"{spec.result_directory} declares {manifest.get('system_id')}, expected {spec.system_id}."
        )
    if int(manifest.get("normal_scenario_count", -1)) != 300:
        raise ComparisonIntegrityError(f"{spec.system_id} is not a 300-scenario run.")
    if int(aggregate.get("scenario_count", -1)) != 300:
        raise ComparisonIntegrityError(f"{spec.system_id} aggregate does not cover 300 scenarios.")
    if int(batch_summary.get("scenario_count", -1)) != 300:
        raise ComparisonIntegrityError(f"{spec.system_id} batch summary does not cover 300 scenarios.")
    if int(stratified.get("scenario_count", -1)) != 300:
        raise ComparisonIntegrityError(f"{spec.system_id} stratified report does not cover 300 scenarios.")
    return LoadedSystem(spec, manifest, aggregate, stratified, batch_summary)


def load_comparison_inputs(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    *,
    systems: Sequence[SystemSpec] = SYSTEMS,
) -> tuple[LoadedSystem, ...]:
    """Load and validate all persisted architecture artifacts fairly."""
    loaded = tuple(_load_system(results_root, spec) for spec in systems)
    if tuple(system.spec.system_id for system in loaded) != tuple(system.system_id for system in SYSTEMS):
        raise ComparisonIntegrityError("Architecture comparison requires the canonical A0--A6 system order.")
    reference = loaded[0]
    reference_ids = tuple(reference.manifest.get("normal_scenario_ids", ()))
    reference_hashes = _verified_artifact_map(reference.manifest)
    reference_metrics = tuple(sorted(reference.rates))
    for current in loaded[1:]:
        if tuple(current.manifest.get("normal_scenario_ids", ())) != reference_ids:
            raise ComparisonIntegrityError(f"{current.spec.system_id} did not use E0's exact scenario population.")
        if _verified_artifact_map(current.manifest) != reference_hashes:
            raise ComparisonIntegrityError(
                f"{current.spec.system_id} did not verify E0's exact frozen artifact hashes."
            )
        if tuple(sorted(current.rates)) != reference_metrics:
            raise ComparisonIntegrityError(
                f"{current.spec.system_id} aggregate metric schema differs from E0."
            )
    return loaded


def _system_summary(loaded: Sequence[LoadedSystem]) -> list[dict[str, Any]]:
    rows = []
    for system in loaded:
        start = _parse_utc(str(system.manifest["started_at_utc"]))
        end = _parse_utc(str(system.manifest["completed_at_utc"]))
        counts = system.counts
        full_passed, total, rate = counts["overall_structural_pass"]
        rows.append({
            "system_id": system.spec.system_id,
            "label": system.spec.label,
            "comparison_role": system.spec.comparison_role,
            "evaluation_only": bool(system.manifest["evaluation_only"]),
            "run_status": system.manifest["status"],
            "scenario_count": total,
            "fully_passing_scenario_count": full_passed,
            "overall_structural_pass_rate": rate,
            "elapsed_seconds": round((end - start).total_seconds(), 3),
            "bounded_llm_invocation_count": int(system.manifest.get("bounded_llm_invocation_count", 0)),
            "direct_farm_action_count": 0,
            "run_commit": str(system.manifest.get("git", {}).get("commit", "")),
        })
    return rows


def _metric_rows(loaded: Sequence[LoadedSystem]) -> list[dict[str, Any]]:
    rows = []
    for system in loaded:
        for metric, (passed, total, rate) in system.counts.items():
            rows.append({
                "system_id": system.spec.system_id,
                "label": system.spec.label,
                "metric": metric,
                "metric_label": _short_metric(metric),
                "passed": passed,
                "total": total,
                "rate": rate,
                "percentage": rate * 100,
                "delta_vs_a0_percentage_points": (rate - loaded[0].rates[metric]) * 100,
            })
    return rows


def _stratum_rows(
    loaded: Sequence[LoadedSystem],
    *,
    stratum_name: str,
    stratum_field: str,
    expected_value_count: int,
) -> list[dict[str, Any]]:
    selected = (
        "overall_structural_pass",
        "grounded_plan_coverage",
        "conditional_operation_completeness",
        "operation_binding_and_condition_compliance",
    )
    rows = []
    for system in loaded:
        for stratum in system.stratified["strata"]:
            if stratum["stratum_name"] != stratum_name:
                continue
            metric_map = {
                metric["name"]: metric
                for metric in stratum["metrics"]
            }
            for metric in selected:
                detail = metric_map[metric]
                rows.append({
                    "system_id": system.spec.system_id,
                    stratum_field: stratum["stratum_value"],
                    "metric": metric,
                    "metric_label": _short_metric(metric),
                    "passed": int(detail["passed"]),
                    "total": int(detail["total"]),
                    "rate": float(detail["rate"]),
                })
    expected = len(loaded) * expected_value_count * len(selected)
    if len(rows) != expected:
        raise ComparisonIntegrityError(
            f"{stratum_name} stratification is incomplete: {len(rows)}/{expected} rows."
        )
    return rows


def _crop_rows(loaded: Sequence[LoadedSystem]) -> list[dict[str, Any]]:
    return _stratum_rows(
        loaded,
        stratum_name="crop",
        stratum_field="crop",
        expected_value_count=6,
    )


def _district_rows(loaded: Sequence[LoadedSystem]) -> list[dict[str, Any]]:
    return _stratum_rows(
        loaded,
        stratum_name="district",
        stratum_field="district",
        expected_value_count=23,
    )


def _benchmark_composition() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Summarize the immutable benchmark population from its canonical manifest."""
    manifest_path = PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv"
    if not manifest_path.is_file():
        raise ComparisonIntegrityError(f"Canonical scenario manifest is missing: {manifest_path}")
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    if len(records) != 300:
        raise ComparisonIntegrityError(f"Canonical scenario manifest has {len(records)}, expected 300 records.")
    required = {"scenario_id", "scenario_type", "site_id", "crop", "state", "district", "season"}
    if not records or not required.issubset(records[0]):
        raise ComparisonIntegrityError("Canonical scenario manifest lacks required composition fields.")

    anchor_type = "verified_anchor_context"
    supplementary_type = "verified_supplementary_historical_context"
    rows = []
    for crop in sorted({str(record["crop"]) for record in records}):
        subset = [record for record in records if record["crop"] == crop]
        rows.append({
            "crop": crop,
            "scenario_count": len(subset),
            "site_count": len({record["site_id"] for record in subset}),
            "district_count": len({record["district"] for record in subset}),
            "state_count": len({record["state"] for record in subset}),
            "season": ", ".join(sorted({record["season"] for record in subset})),
            "anchor_count": sum(record["scenario_type"] == anchor_type for record in subset),
            "supplementary_count": sum(record["scenario_type"] == supplementary_type for record in subset),
        })
    if len(rows) != 6 or any(row["scenario_count"] != 50 for row in rows):
        raise ComparisonIntegrityError("Canonical composition is not the declared six-crop, 50-scenarios-per-crop design.")
    totals = {
        "scenario_count": len(records),
        "site_count": len({record["site_id"] for record in records}),
        "district_count": len({record["district"] for record in records}),
        "state_count": len({record["state"] for record in records}),
        "crop_count": len(rows),
        "anchor_count": sum(record["scenario_type"] == anchor_type for record in records),
        "supplementary_count": sum(record["scenario_type"] == supplementary_type for record in records),
        "manifest_path": manifest_path,
    }
    if totals["anchor_count"] != 30 or totals["supplementary_count"] != 270 or totals["site_count"] != 30:
        raise ComparisonIntegrityError("Canonical composition does not match the frozen 30-anchor / 270-supplementary design.")
    return rows, totals


def _fixture_rows(
    results_root: Path,
    *,
    a0_result_directory: str,
    a6_result_directory: str,
    provenance_fixture_directory: str,
) -> list[dict[str, Any]]:
    e0_fixture = _read_json(results_root / a0_result_directory / "fixture_oracle_result.json")
    a6_runs = _read_json(results_root / a6_result_directory / "conflict_fixture_runs.json")
    gate_fixture = _read_json(
        results_root / provenance_fixture_directory / "provenance_fixture_oracle_result.json"
    )
    if not isinstance(a6_runs, list) or len(a6_runs) != 60:
        raise ComparisonIntegrityError("A6 conflict fixture artifact must contain exactly 60 records.")
    coordinator_runs = [row for row in a6_runs if row.get("fixture_family") == "coordinator_resolution"]
    if len(coordinator_runs) != 48:
        raise ComparisonIntegrityError("A6 fixture artifact must contain 48 coordinator-resolution records.")
    a6_expected = sum(bool(row.get("expected_match")) for row in a6_runs)
    a6_detected = sum(bool(row.get("fixture_conflicts")) for row in coordinator_runs)
    a6_resolved = sum(int(row.get("fixture_resolution_record_count", 0)) > 0 for row in coordinator_runs)
    a6_actions = sum(
        bool((row.get("decision") or {}).get("direct_farm_action_issued")) for row in a6_runs
    )
    rows = [
        {
            "protocol": "Conflict policy fixtures",
            "measure": "A0 reference-policy matches",
            "system": "A0",
            "numerator": int(e0_fixture["passed_fixture_count"]),
            "denominator": int(e0_fixture["fixture_count"]),
            "rate": float(e0_fixture["compliance_rate"]),
            "interpretation": "Full resolver follows all stored conflict-policy cases.",
        },
        {
            "protocol": "Conflict policy fixtures",
            "measure": "A6 expected ablation behaviour",
            "system": "A6",
            "numerator": a6_expected,
            "denominator": len(a6_runs),
            "rate": a6_expected / len(a6_runs),
            "interpretation": "Detector/safety remain intact while coordination is intentionally withheld.",
        },
        {
            "protocol": "Conflict policy fixtures",
            "measure": "A6 eligible conflict detection",
            "system": "A6",
            "numerator": a6_detected,
            "denominator": len(coordinator_runs),
            "rate": a6_detected / len(coordinator_runs),
            "interpretation": "All coordinator-required same-domain conflicts remain visible to the detector.",
        },
        {
            "protocol": "Conflict policy fixtures",
            "measure": "A6 coordinator resolution",
            "system": "A6",
            "numerator": a6_resolved,
            "denominator": len(coordinator_runs),
            "rate": a6_resolved / len(coordinator_runs),
            "interpretation": "Zero by design: the A6 coordinator receives no conflicts.",
        },
        {
            "protocol": "Conflict policy fixtures",
            "measure": "A6 direct-action safety",
            "system": "A6",
            "numerator": len(a6_runs) - a6_actions,
            "denominator": len(a6_runs),
            "rate": (len(a6_runs) - a6_actions) / len(a6_runs),
            "interpretation": "No controlled conflict fixture issues a direct farm action.",
        },
        {
            "protocol": "Provenance/alignment integrity fixtures",
            "measure": "A0 alignment blocks",
            "system": "A0",
            "numerator": int(gate_fixture["a0_alignment_validator_blocked_count"]),
            "denominator": 50,
            "rate": int(gate_fixture["a0_alignment_validator_blocked_count"]) / 50,
            "interpretation": "A0 blocks controlled plan identity/binding mismatches before downstream agents.",
        },
        {
            "protocol": "Provenance/alignment integrity fixtures",
            "measure": "A5 omitted-gate exposure observed",
            "system": "A5",
            "numerator": int(gate_fixture["a5_alignment_validator_exposure_count"]),
            "denominator": 50,
            "rate": int(gate_fixture["a5_alignment_validator_exposure_count"]) / 50,
            "interpretation": "Expected evaluation-only exposure after removing the alignment validator; runner halts there.",
        },
        {
            "protocol": "Provenance/alignment integrity fixtures",
            "measure": "Shared loader payload-hash blocks",
            "system": "A0 and A5",
            "numerator": int(gate_fixture["shared_loader_payload_hash_blocked_count"]),
            "denominator": 10,
            "rate": int(gate_fixture["shared_loader_payload_hash_blocked_count"]) / 10,
            "interpretation": "Immutable raw-payload hash verification is a shared loader boundary.",
        },
        {
            "protocol": "Provenance/alignment integrity fixtures",
            "measure": "Direct-action safety",
            "system": "A0 and A5",
            "numerator": int(gate_fixture["fixture_count"]) - int(gate_fixture["direct_farm_action_fixture_count"]),
            "denominator": int(gate_fixture["fixture_count"]),
            "rate": 1.0 - int(gate_fixture["direct_farm_action_fixture_count"]) / int(gate_fixture["fixture_count"]),
            "interpretation": "The invalid-bundle runner creates no decision or direct action.",
        },
    ]
    return rows


def _figure_metric_heatmap(loaded: Sequence[LoadedSystem], output_dir: Path) -> list[Path]:
    matrix = [[system.rates[metric] * 100 for metric in HEATMAP_METRICS] for system in loaded]
    figure, axis = plt.subplots(figsize=(15.5, 5.2), constrained_layout=True)
    cmap = LinearSegmentedColormap.from_list("safety_rates", ["#f3f4f6", "#9ecae1", "#08519c"])
    image = axis.imshow(matrix, vmin=0, vmax=100, cmap=cmap, aspect="auto")
    axis.set_title("Structural-oracle compliance across the frozen 300-scenario benchmark")
    axis.set_yticks(range(len(loaded)), [system.spec.label for system in loaded])
    axis.set_xticks(range(len(HEATMAP_METRICS)), [_short_metric(metric) for metric in HEATMAP_METRICS])
    axis.tick_params(axis="x", labelrotation=42, labelsize=8)
    axis.tick_params(axis="y", labelsize=9)
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            text_color = "white" if value >= 62 else "black"
            axis.text(column_index, row_index, f"{value:.0f}", ha="center", va="center", color=text_color, fontsize=8)
    colorbar = figure.colorbar(image, ax=axis, shrink=0.9, pad=0.015)
    colorbar.set_label("Oracle pass rate (%)")
    axis.set_xlabel("Independent structural oracle check")
    axis.set_ylabel("Architecture system")
    return _save_figure(figure, output_dir / "FIGURE_1_ORACLE_METRIC_HEATMAP")


def _figure_key_metrics(loaded: Sequence[LoadedSystem], output_dir: Path) -> list[Path]:
    metrics = KEY_METRICS
    colors = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#666666", "#1f78b4"]
    figure = plt.figure(figsize=(13.5, 7.2), constrained_layout=True)
    grid = figure.add_gridspec(2, 1, height_ratios=(0.16, 1))
    header = figure.add_subplot(grid[0])
    axis = figure.add_subplot(grid[1])
    header.axis("off")
    header.text(
        0.5,
        0.96,
        "A0 versus architecture baselines and ablations",
        ha="center",
        va="top",
        fontsize=15,
    )
    width = 0.11
    x_positions = list(range(len(metrics)))
    legend_handles = []
    for index, system in enumerate(loaded):
        offsets = [x + (index - (len(loaded) - 1) / 2) * width for x in x_positions]
        hatch = "//" if system.spec.system_id == "A5" else None
        axis.bar(
            offsets,
            [system.rates[metric] * 100 for metric in metrics],
            width=width,
            color=colors[index],
            edgecolor="black",
            linewidth=0.25,
            hatch=hatch,
            label=system.spec.system_id,
        )
        legend_handles.append(Patch(facecolor=colors[index], edgecolor="black", hatch=hatch, label=system.spec.system_id))
    axis.set_ylim(0, 105)
    axis.set_ylabel("Oracle pass rate (%)")
    axis.set_xlabel("Key structural metric")
    axis.set_xticks(x_positions, [_short_metric(metric) for metric in metrics], rotation=30, ha="right")
    axis.grid(axis="y", linewidth=0.4, alpha=0.35)
    header.legend(handles=legend_handles, title="System", ncols=7, loc="lower center", bbox_to_anchor=(0.5, -0.15))
    return _save_figure(figure, output_dir / "FIGURE_2_KEY_ABLATION_METRICS")


def _figure_fixture_protocols(fixture_rows: Sequence[Mapping[str, Any]], output_dir: Path) -> list[Path]:
    conflict = [row for row in fixture_rows if row["protocol"] == "Conflict policy fixtures"]
    integrity = [row for row in fixture_rows if row["protocol"] == "Provenance/alignment integrity fixtures"]
    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), constrained_layout=True)
    panels = (
        (axes[0], conflict, "Controlled conflict-policy fixtures"),
        (axes[1], integrity, "Controlled provenance/alignment fixtures"),
    )
    colors = ["#1b9e77", "#7570b3", "#1f78b4", "#d95f02", "#66a61e"]
    for axis, rows, title in panels:
        labels = [str(row["measure"]) for row in rows]
        values = [float(row["rate"]) * 100 for row in rows]
        bars = axis.barh(range(len(rows)), values, color=colors[:len(rows)])
        for bar, row, value in zip(bars, rows, values):
            if "exposure" in str(row["measure"]).lower():
                bar.set_hatch("//")
            axis.text(min(value + 1.2, 96), bar.get_y() + bar.get_height() / 2, f"{int(row['numerator'])}/{int(row['denominator'])}", va="center", fontsize=9)
        axis.set_xlim(0, 112)
        axis.set_yticks(range(len(rows)))
        axis.set_yticklabels(labels, fontsize=8)
        axis.invert_yaxis()
        axis.set_xlabel("Expected protocol outcome rate (%)")
        axis.set_title(title)
        axis.grid(axis="x", linewidth=0.4, alpha=0.35)
    figure.legend(
        handles=[
            Patch(facecolor="#1b9e77", label="Required protective / policy outcome"),
            Patch(facecolor="#7570b3", hatch="//", label="Expected A5 exposure (evaluation-only)"),
        ],
        loc="lower center",
        ncols=2,
        bbox_to_anchor=(0.5, -0.06),
    )
    return _save_figure(figure, output_dir / "FIGURE_3_CONTROLLED_FIXTURE_PROTOCOLS")


def _save_figure(figure: Any, base: Path) -> list[Path]:
    paths = [base.with_suffix(".png"), base.with_suffix(".pdf")]
    figure.savefig(paths[0], dpi=300, bbox_inches="tight")
    figure.savefig(paths[1], bbox_inches="tight")
    plt.close(figure)
    return paths


def _write_tables(
    output_dir: Path,
    summary_rows: Sequence[Mapping[str, Any]],
    metric_rows: Sequence[Mapping[str, Any]],
    fixture_rows: Sequence[Mapping[str, Any]],
    crop_rows: Sequence[Mapping[str, Any]],
    district_rows: Sequence[Mapping[str, Any]],
    composition_rows: Sequence[Mapping[str, Any]],
    composition_totals: Mapping[str, Any],
) -> None:
    _csv_write(output_dir / "system_summary.csv", tuple(summary_rows[0]), summary_rows)
    _csv_write(output_dir / "oracle_metric_rates.csv", tuple(metric_rows[0]), metric_rows)
    _csv_write(output_dir / "fixture_protocol_results.csv", tuple(fixture_rows[0]), fixture_rows)
    _csv_write(output_dir / "crop_stratified_key_metrics.csv", tuple(crop_rows[0]), crop_rows)
    _csv_write(output_dir / "district_stratified_key_metrics.csv", tuple(district_rows[0]), district_rows)
    _csv_write(output_dir / "benchmark_composition.csv", tuple(composition_rows[0]), composition_rows)

    composition_md = _markdown_table(
        ("Crop", "Scenarios", "Sites", "Districts", "States", "Season", "Anchors", "Supplementary"),
        [
            (
                str(row["crop"]),
                str(row["scenario_count"]),
                str(row["site_count"]),
                str(row["district_count"]),
                str(row["state_count"]),
                str(row["season"]),
                str(row["anchor_count"]),
                str(row["supplementary_count"]),
            )
            for row in composition_rows
        ]
        + [
            (
                "Total",
                str(composition_totals["scenario_count"]),
                str(composition_totals["site_count"]),
                str(composition_totals["district_count"]),
                str(composition_totals["state_count"]),
                "Six crop-season strata",
                str(composition_totals["anchor_count"]),
                str(composition_totals["supplementary_count"]),
            )
        ],
    )
    _write_text(
        output_dir / "TABLE_0_BENCHMARK_COMPOSITION.md",
        "# Table 0. Frozen benchmark composition\n\n"
        "Counts are read from the canonical scenario manifest. The normal benchmark is six crops across "
        "30 crop–site combinations in five states; it contains 30 verified anchors and 270 verified "
        "supplementary historical contexts.\n\n"
        + composition_md,
    )

    summary_md = _markdown_table(
        ("System", "Role", "Full structural pass", "Direct actions", "Run status"),
        [
            (
                row["label"],
                row["comparison_role"],
                f"{row['fully_passing_scenario_count']}/{row['scenario_count']} ({_percent(float(row['overall_structural_pass_rate']))})",
                str(row["direct_farm_action_count"]),
                str(row["run_status"]),
            )
            for row in summary_rows
        ],
    )
    _write_text(
        output_dir / "TABLE_1_SYSTEM_COMPARISON.md",
        "# Table 1. Architecture comparison over the frozen 300-scenario benchmark\n\n"
        "All A1–A6 rows are evaluation-only systems. A0 is the sole farmer-facing architecture. "
        "A lower full-pass rate identifies structural requirements intentionally lost by a baseline or ablation; it is not farm-outcome accuracy.\n\n"
        + summary_md,
    )

    by_system_metric = {
        (str(row["system_id"]), str(row["metric"])): row
        for row in metric_rows
    }
    key_md = _markdown_table(
        ("System", *(_short_metric(metric) for metric in KEY_METRICS)),
        [
            (
                system_id,
                *(
                    f"{by_system_metric[(system_id, metric)]['passed']}/300 "
                    f"({_percent(float(by_system_metric[(system_id, metric)]['rate']))})"
                    for metric in KEY_METRICS
                ),
            )
            for system_id in ("A0", "A1", "A2", "A3", "A4", "A5", "A6")
        ],
    )
    _write_text(
        output_dir / "TABLE_2_KEY_ORACLE_ABLATIONS.md",
        "# Table 2. Key independent-oracle rates by system\n\n"
        "The complete 19-metric long-form table is `oracle_metric_rates.csv`. This selected table highlights "
        "the structural requirements directly affected by the declared architecture variants.\n\n"
        + key_md,
    )

    fixture_md = _markdown_table(
        ("Protocol", "Measure", "System", "Result", "Interpretation"),
        [
            (
                str(row["protocol"]),
                str(row["measure"]),
                str(row["system"]),
                f"{row['numerator']}/{row['denominator']} ({_percent(float(row['rate']))})",
                str(row["interpretation"]),
            )
            for row in fixture_rows
        ],
    )
    _write_text(
        output_dir / "TABLE_3_CONTROLLED_FIXTURE_PROTOCOLS.md",
        "# Table 3. Controlled conflict and integrity fixture outcomes\n\n"
        "These are controlled software/provenance policy evaluations, not historical farm outcomes. "
        "The A5 exposure row is an expected ablation observation, not a successful protective behavior.\n\n"
        + fixture_md,
    )

    crop_order = ("rice", "wheat", "maize", "chickpea", "soybean", "tomato")
    crop_lookup = {(row["system_id"], row["crop"], row["metric"]): row for row in crop_rows}
    crop_md = _markdown_table(
        ("Crop", "A0 full structural", "A3 full structural", "A3 conditional operations", "A5 full structural"),
        [
            (
                crop,
                _percent(float(crop_lookup[("A0", crop, "overall_structural_pass")]["rate"])),
                _percent(float(crop_lookup[("A3", crop, "overall_structural_pass")]["rate"])),
                _percent(float(crop_lookup[("A3", crop, "conditional_operation_completeness")]["rate"])),
                _percent(float(crop_lookup[("A5", crop, "overall_structural_pass")]["rate"])),
            )
            for crop in crop_order
        ],
    )
    _write_text(
        output_dir / "TABLE_4_CROP_STRATIFICATION.md",
        "# Table 4. Crop-stratified structural comparison\n\n"
        "A3 quantifies the loss of source-scoped operation recovery. A5 matches A0 on valid frozen inputs because "
        "the population is already aligned; Table 3's controlled integrity fixtures measure the protective gate difference.\n\n"
        + crop_md,
    )

    district_lookup = {
        (row["system_id"], row["district"], row["metric"]): row
        for row in district_rows
    }
    district_names = sorted({str(row["district"]) for row in district_rows})
    district_md = _markdown_table(
        ("District", "A0 full structural", "A3 full structural", "A3 conditional operations"),
        [
            (
                district,
                _percent(float(district_lookup[("A0", district, "overall_structural_pass")]["rate"])),
                _percent(float(district_lookup[("A3", district, "overall_structural_pass")]["rate"])),
                _percent(float(district_lookup[("A3", district, "conditional_operation_completeness")]["rate"])),
            )
            for district in district_names
        ],
    )
    _write_text(
        output_dir / "TABLE_5_DISTRICT_STRATIFICATION.md",
        "# Table 5. District-stratified structural comparison\n\n"
        "This supplementary table makes the geographic distribution visible. Districts shared by two crops "
        "aggregate the corresponding frozen scenarios. The complete long-form district × system × metric "
        "values are in `district_stratified_key_metrics.csv`.\n\n"
        + district_md,
    )


def _write_readme(output_dir: Path) -> None:
    _write_text(
        output_dir / "README.md",
        "# Frozen Architecture Comparison\n\n"
        "This directory is generated only from the persisted E0 and A1–A6 result artifacts plus the two stored fixture suites. "
        "It contains no new scenario, source, agricultural label, or model output.\n\n"
        "## Interpretation boundary\n\n"
        "- The 300 normal scenarios are an exhaustive fixed benchmark population, so tables report exact count/rate differences rather than farm-outcome accuracy or inferential significance tests.\n"
        "- A1–A6 are declared evaluation-only systems. Their expected oracle failures identify the contract properties contributed by removed components.\n"
        "- The conflict and provenance/alignment fixtures are controlled policy tests. They do not establish agricultural correctness or farmer impact.\n"
        "- A5's normal 300-scenario equality with A0 is expected because the frozen records are valid. Its controlled fixture result, not the normal rate, demonstrates why the alignment validator remains necessary.\n\n"
        "## Reproduce\n\n"
        "```bash\n"
        ".venv-macos/bin/python -m evaluation.frozen_benchmark_comparison \\\n"
        "  --output-dir results/derived-architecture-comparison\n"
        "```\n\n"
        "The command refuses a non-empty output directory unless `--overwrite` is supplied. Before writing any result, it rejects a run whose normal-scenario IDs, 300-scenario count, frozen-input hashes, or oracle-metric schema differs from A0.\n\n"
        "## Generated artifacts\n\n"
        "| Artifact | Use |\n| --- | --- |\n"
        "| `TABLE_0_BENCHMARK_COMPOSITION.md` | Frozen scenario population composition. |\n"
        "| `TABLE_1_SYSTEM_COMPARISON.md` | Overall architecture comparison. |\n"
        "| `TABLE_2_KEY_ORACLE_ABLATIONS.md` | Selected independent-oracle rates. |\n"
        "| `TABLE_3_CONTROLLED_FIXTURE_PROTOCOLS.md` | Conflict and integrity-fixture results. |\n"
        "| `TABLE_4_CROP_STRATIFICATION.md` | Crop-level A0/A3/A5 comparison. |\n"
        "| `TABLE_5_DISTRICT_STRATIFICATION.md` | Geographic supplementary comparison. |\n"
        "| `oracle_metric_rates.csv` | All 19 normal-scenario oracle metrics, long form. |\n"
        "| `crop_stratified_key_metrics.csv` | Complete crop × system × key-metric values. |\n"
        "| `district_stratified_key_metrics.csv` | Complete district × system × key-metric values. |\n"
        "| `benchmark_composition.csv` | Machine-readable frozen-population composition. |\n"
        "| `FIGURE_*.png` / `FIGURE_*.pdf` | 300 dpi raster and vector paper figures. |\n"
        "| `comparison_manifest.json` | Source artifact fingerprints, validation status, and generation Git state. |\n",
    )


def build_comparison(
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
    render_figures: bool = True,
    systems: Sequence[SystemSpec] = SYSTEMS,
    provenance_fixture_directory: str = "v2_2-provenance-gate-fixtures",
    generation_git: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Validate all runs and write comparison tables, figures, and manifest."""
    results_root = results_root.resolve()
    output_dir = output_dir.resolve()
    recorded_generation_git = dict(generation_git) if generation_git is not None else _git_metadata()
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise ComparisonIntegrityError(
            f"Comparison output already exists: {output_dir}. Pass overwrite=True only to regenerate it."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    loaded = load_comparison_inputs(results_root, systems=systems)
    summary_rows = _system_summary(loaded)
    metric_rows = _metric_rows(loaded)
    crop_rows = _crop_rows(loaded)
    district_rows = _district_rows(loaded)
    composition_rows, composition_totals = _benchmark_composition()
    loaded_by_id = {system.spec.system_id: system for system in loaded}
    fixture_rows = _fixture_rows(
        results_root,
        a0_result_directory=loaded_by_id["A0"].spec.result_directory,
        a6_result_directory=loaded_by_id["A6"].spec.result_directory,
        provenance_fixture_directory=provenance_fixture_directory,
    )
    _write_tables(
        output_dir,
        summary_rows,
        metric_rows,
        fixture_rows,
        crop_rows,
        district_rows,
        composition_rows,
        composition_totals,
    )
    figure_paths: list[Path] = []
    if render_figures:
        figure_paths.extend(_figure_metric_heatmap(loaded, output_dir))
        figure_paths.extend(_figure_key_metrics(loaded, output_dir))
        figure_paths.extend(_figure_fixture_protocols(fixture_rows, output_dir))
    _write_readme(output_dir)
    source_files = [
        *(results_root / system.spec.result_directory / filename
          for system in loaded
          for filename in ("run_manifest.json", "aggregate_oracle_result.json", "stratified_oracle_result.json", "batch_summary.json")),
        results_root / loaded_by_id["A0"].spec.result_directory / "fixture_oracle_result.json",
        results_root / loaded_by_id["A6"].spec.result_directory / "conflict_fixture_runs.json",
        results_root / provenance_fixture_directory / "provenance_fixture_oracle_result.json",
        composition_totals["manifest_path"],
    ]
    manifest = {
        "schema_version": "1.0",
        "comparison_population": "fixed_300_source_gated_scenarios",
        "systems": [system.spec.system_id for system in loaded],
        "normal_scenario_count": 300,
        "shared_frozen_artifact_hashes": _verified_artifact_map(loaded[0].manifest),
        "source_artifacts": [
            {"path": str(path.relative_to(PROJECT_ROOT)), "sha256": _sha256(path)}
            for path in source_files
        ],
        "generation_git": recorded_generation_git,
        "generated_outputs": [
            *[path.name for path in sorted(output_dir.iterdir()) if path.is_file()],
            "comparison_manifest.json",
        ],
        "fixture_protocol_summary": fixture_rows,
        "interpretation": {
            "normal_oracle": "Structural source/provenance/safety conformance; not agricultural outcome accuracy.",
            "conflict_fixtures": "Controlled conflict-policy evaluation; not farm outcomes.",
            "integrity_fixtures": "Controlled A0/A5 gate-boundary evaluation; invalid bundles stop before farmer output.",
        },
    }
    _write_text(output_dir / "comparison_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return {
        "output_dir": str(output_dir),
        "system_count": len(loaded),
        "scenario_count": 300,
        "table_count": 6,
        "figure_count": len(figure_paths) // 2,
        "figure_files": [path.name for path in figure_paths],
        "a0_full_pass_count": int(loaded[0].aggregate["fully_passing_scenario_count"]),
        "a3_full_pass_count": int(loaded[3].aggregate["fully_passing_scenario_count"]),
        "a5_full_pass_count": int(loaded[5].aggregate["fully_passing_scenario_count"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true", help="Replace generated comparison files in output-dir.")
    parser.add_argument("--no-figures", action="store_true", help="Write validated tables and manifest without figures.")
    args = parser.parse_args()
    summary = build_comparison(
        results_root=args.results_root,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        render_figures=not args.no_figures,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
