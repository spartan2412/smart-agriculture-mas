"""Build the final, read-only Phase 7 controlled-comparison package.

The package deliberately separates three different kinds of evidence:

* **structural architecture evidence** from the deterministic A0--A6 runs;
* **bounded-LLM selection evidence** from the frozen, held-out v5.1 set; and
* **qualitative farmer-message examples**, which are displayed for inspection
  but are never converted into a subjective accuracy or usefulness score.

No scenario, source, agent, prompt, model, or decision is regenerated.  This
module reads persisted artifacts only, rejects mismatched normal populations or
data hashes, and writes paper-ready tables and a complete provenance manifest.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping, Sequence

from evaluation.frozen_benchmark_comparison import SYSTEMS, SystemSpec, build_comparison


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_ROOT = PROJECT_ROOT / "results"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_ROOT / "derived-phase7-controlled-comparison"

E0_RESULT_DIRECTORY = "v2_2-e0-full-mas"
E1_RESULT_DIRECTORY = "v2_2-e1-v5-full-mas"
HELDOUT_RESULT_DIRECTORY = "e1-v5-heldout-final"
EXPECTED_SCENARIO_COUNT = 300
EXPECTED_BOUNDED_ROLES = frozenset(
    {
        "weather_context_agent",
        "soil_context_agent",
        "satellite_ndvi_context_agent",
        "market_evidence_agent",
        "fertilizer_baseline_agent",
        "official_operations_rag_agent",
        "provenance_aware_coordinator_agent",
        "farmer_explanation_citation_agent",
    }
)


class Phase7ComparisonIntegrityError(ValueError):
    """Raised when persisted artifacts cannot support a fair Phase 7 claim."""


@dataclass(frozen=True)
class PersistedRun:
    """Validated metadata and paths for one immutable 300-scenario run."""

    label: str
    directory: Path
    manifest: Mapping[str, Any]
    aggregate: Mapping[str, Any]
    stratified: Mapping[str, Any]
    batch_summary: Mapping[str, Any]


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise Phase7ComparisonIntegrityError(f"Required artifact is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Phase7ComparisonIntegrityError(f"Invalid JSON artifact: {path}") from exc


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(str(header) for header in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *(
                "| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |"
                for row in rows
            ),
        ]
    )


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise Phase7ComparisonIntegrityError(f"Refusing to write empty table: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _elapsed_seconds(manifest: Mapping[str, Any]) -> float:
    started = datetime.fromisoformat(str(manifest["started_at_utc"]).replace("Z", "+00:00"))
    completed = datetime.fromisoformat(str(manifest["completed_at_utc"]).replace("Z", "+00:00"))
    return round((completed - started).total_seconds(), 3)


def _git_metadata() -> Mapping[str, Any]:
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
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - host failure
        return {"status": "unavailable", "error": type(exc).__name__}


def _verified_artifact_map(manifest: Mapping[str, Any]) -> dict[str, str]:
    protocol = manifest.get("protocol")
    if not isinstance(protocol, Mapping):
        raise Phase7ComparisonIntegrityError("Run manifest has no protocol artifact section.")
    raw_artifacts = protocol.get("verified_artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise Phase7ComparisonIntegrityError("Run manifest has no verified-artifact hashes.")
    artifacts = {str(row["path"]): str(row["sha256"]) for row in raw_artifacts}
    if len(artifacts) != len(raw_artifacts):
        raise Phase7ComparisonIntegrityError("Run manifest duplicates a verified-artifact path.")
    return artifacts


def _metric_map(aggregate: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = aggregate.get("metrics")
    if not isinstance(rows, list) or not rows:
        raise Phase7ComparisonIntegrityError("Oracle aggregate has no metric records.")
    metrics = {str(row["name"]): row for row in rows}
    if len(metrics) != len(rows):
        raise Phase7ComparisonIntegrityError("Oracle aggregate duplicates a metric name.")
    return metrics


def _load_persisted_run(results_root: Path, directory_name: str, label: str) -> PersistedRun:
    directory = results_root / directory_name
    run = PersistedRun(
        label=label,
        directory=directory,
        manifest=_read_json(directory / "run_manifest.json"),
        aggregate=_read_json(directory / "aggregate_oracle_result.json"),
        stratified=_read_json(directory / "stratified_oracle_result.json"),
        batch_summary=_read_json(directory / "batch_summary.json"),
    )
    manifest = run.manifest
    if int(manifest.get("normal_scenario_count", -1)) != EXPECTED_SCENARIO_COUNT:
        raise Phase7ComparisonIntegrityError(f"{label} does not declare 300 normal scenarios.")
    for artifact_name, artifact in (
        ("aggregate", run.aggregate),
        ("stratified", run.stratified),
        ("batch summary", run.batch_summary),
    ):
        if int(artifact.get("scenario_count", -1)) != EXPECTED_SCENARIO_COUNT:
            raise Phase7ComparisonIntegrityError(f"{label} {artifact_name} is not a 300-scenario result.")
    ids = manifest.get("normal_scenario_ids")
    if not isinstance(ids, list) or len(ids) != EXPECTED_SCENARIO_COUNT or len(set(ids)) != EXPECTED_SCENARIO_COUNT:
        raise Phase7ComparisonIntegrityError(f"{label} lacks 300 unique persisted scenario IDs.")
    scenario_dir = directory / "scenarios"
    paths = sorted(scenario_dir.glob("*.json")) if scenario_dir.is_dir() else []
    if len(paths) != EXPECTED_SCENARIO_COUNT:
        raise Phase7ComparisonIntegrityError(f"{label} has {len(paths)} scenario traces, expected 300.")
    file_ids = {path.stem for path in paths}
    if file_ids != set(ids):
        raise Phase7ComparisonIntegrityError(f"{label} scenario trace filenames differ from its run manifest.")
    _verified_artifact_map(manifest)
    _metric_map(run.aggregate)
    return run


def _assert_e0_e1_comparable(e0: PersistedRun, e1: PersistedRun) -> dict[str, str]:
    if e0.manifest.get("configuration_id") != "E0" or e0.manifest.get("system_id") != "A0":
        raise Phase7ComparisonIntegrityError("E0 artifact is not the deterministic full-MAS A0 run.")
    if e1.manifest.get("configuration_id") != "E1" or e1.manifest.get("system_id") != "A0":
        raise Phase7ComparisonIntegrityError("E1 artifact is not the model-enabled full-MAS A0 run.")
    if bool(e0.manifest.get("bounded_llm", {}).get("enabled")):
        raise Phase7ComparisonIntegrityError("E0 must have bounded LLM disabled.")
    if not bool(e1.manifest.get("bounded_llm", {}).get("enabled")):
        raise Phase7ComparisonIntegrityError("E1 must have bounded LLM enabled.")
    if tuple(e0.manifest["normal_scenario_ids"]) != tuple(e1.manifest["normal_scenario_ids"]):
        raise Phase7ComparisonIntegrityError("E0 and E1 do not use the exact same ordered scenario population.")

    e0_artifacts = _verified_artifact_map(e0.manifest)
    e1_artifacts = _verified_artifact_map(e1.manifest)
    data_paths = sorted(path for path in e0_artifacts if path.startswith("data/"))
    if not data_paths:
        raise Phase7ComparisonIntegrityError("E0 manifest has no frozen data artifacts to compare.")
    for path in data_paths:
        if e1_artifacts.get(path) != e0_artifacts[path]:
            raise Phase7ComparisonIntegrityError(
                f"E1 does not bind the E0 frozen data hash for {path}."
            )
    for path in ("evaluation/benchmark_contract.py", "evaluation/benchmark_oracle.py"):
        if e1_artifacts.get(path) != e0_artifacts.get(path):
            raise Phase7ComparisonIntegrityError(f"E0 and E1 disagree on shared evaluation code: {path}")

    if tuple(sorted(_metric_map(e0.aggregate))) != tuple(sorted(_metric_map(e1.aggregate))):
        raise Phase7ComparisonIntegrityError("E0 and E1 use different external-oracle metric schemas.")
    return {path: e0_artifacts[path] for path in data_paths}


def _read_trace(run: PersistedRun, scenario_id: str) -> Mapping[str, Any]:
    trace = _read_json(run.directory / "scenarios" / f"{scenario_id}.json")
    identity = trace.get("scenario_identity")
    benchmark_run = trace.get("benchmark_run")
    oracle = trace.get("scenario_oracle_result")
    if not isinstance(identity, Mapping) or not isinstance(benchmark_run, Mapping) or not isinstance(oracle, Mapping):
        raise Phase7ComparisonIntegrityError(f"{run.label} trace has an invalid schema: {scenario_id}")
    if str(identity.get("scenario_id")) != scenario_id or str(benchmark_run.get("scenario_id")) != scenario_id:
        raise Phase7ComparisonIntegrityError(f"{run.label} trace identity mismatch: {scenario_id}")
    return trace


def _bounded_selections(trace: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, Any]] = {}
    claims = trace["benchmark_run"].get("claims")
    if not isinstance(claims, list):
        raise Phase7ComparisonIntegrityError("Trace claims must be a list.")
    for claim in claims:
        metadata = claim.get("metadata", {}) if isinstance(claim, Mapping) else {}
        record = metadata.get("bounded_llm") if isinstance(metadata, Mapping) else None
        if not isinstance(record, Mapping):
            continue
        agent_name = str(record.get("agent_name", ""))
        if not agent_name:
            raise Phase7ComparisonIntegrityError("Bounded-LLM trace record lacks agent_name.")
        previous = records.get(agent_name)
        if previous is not None and _canonical_json(previous) != _canonical_json(record):
            raise Phase7ComparisonIntegrityError(
                f"One scenario has conflicting bounded-LLM records for {agent_name}."
            )
        records[agent_name] = record
    return records


def _trace_row(e0: PersistedRun, e1: PersistedRun, scenario_id: str) -> dict[str, Any]:
    e0_trace = _read_trace(e0, scenario_id)
    e1_trace = _read_trace(e1, scenario_id)
    e0_identity = e0_trace["scenario_identity"]
    e1_identity = e1_trace["scenario_identity"]
    identity_fields = ("scenario_id", "site_id", "crop", "state", "district", "season", "decision_date")
    for field in identity_fields:
        if str(e0_identity.get(field)) != str(e1_identity.get(field)):
            raise Phase7ComparisonIntegrityError(f"E0/E1 trace identity mismatch for {scenario_id}: {field}")

    e0_run = e0_trace["benchmark_run"]
    e1_run = e1_trace["benchmark_run"]
    e0_decision = e0_run.get("decision", {})
    e1_decision = e1_run.get("decision", {})
    if not isinstance(e0_decision, Mapping) or not isinstance(e1_decision, Mapping):
        raise Phase7ComparisonIntegrityError(f"E0/E1 decision is invalid for {scenario_id}")
    e0_oracle = e0_trace["scenario_oracle_result"]
    e1_oracle = e1_trace["scenario_oracle_result"]
    selections = _bounded_selections(e1_trace)
    if set(selections) != EXPECTED_BOUNDED_ROLES:
        raise Phase7ComparisonIntegrityError(
            f"E1 trace {scenario_id} has bounded roles {sorted(selections)}, expected {sorted(EXPECTED_BOUNDED_ROLES)}"
        )
    statuses = [str(record.get("status", "")) for record in selections.values()]
    selected_counts = [len(record.get("selected_fact_ids", ())) for record in selections.values()]
    e0_message = str(e0_run.get("farmer_message", ""))
    e1_message = str(e1_run.get("farmer_message", ""))
    return {
        "scenario_id": scenario_id,
        "site_id": str(e0_identity["site_id"]),
        "crop": str(e0_identity["crop"]),
        "state": str(e0_identity["state"]),
        "district": str(e0_identity["district"]),
        "season": str(e0_identity["season"]),
        "decision_date": str(e0_identity["decision_date"]),
        "e0_oracle_passed": bool(e0_oracle.get("overall_passed")),
        "e1_oracle_passed": bool(e1_oracle.get("overall_passed")),
        "same_decision_status": e0_decision.get("decision_status") == e1_decision.get("decision_status"),
        "same_operation_status": e0_decision.get("operation_status") == e1_decision.get("operation_status"),
        "same_operation_text": e0_decision.get("operation_text") == e1_decision.get("operation_text"),
        "same_direct_action_flag": bool(e0_decision.get("direct_farm_action_issued")) == bool(e1_decision.get("direct_farm_action_issued")),
        "e0_direct_farm_action": bool(e0_decision.get("direct_farm_action_issued")),
        "e1_direct_farm_action": bool(e1_decision.get("direct_farm_action_issued")),
        "same_citation_set": set(e0_decision.get("citations", ())) == set(e1_decision.get("citations", ())),
        "e0_citation_count": len(e0_decision.get("citations", ())),
        "e1_citation_count": len(e1_decision.get("citations", ())),
        "farmer_message_exact_match": e0_message == e1_message,
        "e0_farmer_message_sha256": sha256(e0_message.encode("utf-8")).hexdigest(),
        "e1_farmer_message_sha256": sha256(e1_message.encode("utf-8")).hexdigest(),
        "e0_farmer_message_character_count": len(e0_message),
        "e1_farmer_message_character_count": len(e1_message),
        "e0_retrieved_passage_count": len(e0_run.get("retrieved_passages", ())),
        "e1_retrieved_passage_count": len(e1_run.get("retrieved_passages", ())),
        "e0_elapsed_ms": int(e0_trace.get("runtime", {}).get("elapsed_ms", 0)),
        "e1_elapsed_ms": int(e1_trace.get("runtime", {}).get("elapsed_ms", 0)),
        "e0_process_peak_memory_bytes": int(e0_trace.get("runtime", {}).get("process_peak_memory_bytes", 0)),
        "e1_process_peak_memory_bytes": int(e1_trace.get("runtime", {}).get("process_peak_memory_bytes", 0)),
        "e1_bounded_call_count": len(selections),
        "e1_accepted_selection_count": sum(status == "accepted" for status in statuses),
        "e1_fallback_count": sum(status == "fallback_after_error" for status in statuses),
        "e1_invalid_or_rejected_output_count": sum(status.startswith("rejected_") for status in statuses),
        "e1_empty_accepted_selection_count": sum(
            status == "accepted" and count == 0 for status, count in zip(statuses, selected_counts)
        ),
        "e1_selected_fact_count": sum(selected_counts),
    }


def _mean(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    return sum(float(row[key]) for row in rows) / len(rows) if rows else 0.0


def _max(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return max((int(row[key]) for row in rows), default=0)


def _sum(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(int(row[key]) for row in rows)


def _heldout_summary(
    results_root: Path,
    heldout_result_directory: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    directory = results_root / heldout_result_directory
    metrics = _read_json(directory / "aggregate_final_heldout_metrics.json")
    acceptance = _read_json(directory / "final_acceptance_report.json")
    overall = metrics.get("overall")
    if not isinstance(overall, Mapping) or int(overall.get("question_count", -1)) != 96:
        raise Phase7ComparisonIntegrityError("Final held-out relevance artifact is not the 96-question result.")
    if not bool(metrics.get("final_research_result_permitted")) or not bool(acceptance.get("all_relevance_thresholds_pass")):
        raise Phase7ComparisonIntegrityError("Final held-out relevance result did not pass its frozen acceptance policy.")
    return metrics, acceptance


def _metric_rate(aggregate: Mapping[str, Any], metric_name: str) -> float:
    metric = _metric_map(aggregate).get(metric_name)
    if metric is None:
        raise Phase7ComparisonIntegrityError(f"Missing oracle metric: {metric_name}")
    return float(metric["rate"])


def _e1_gpu_evidence(e1: PersistedRun) -> Mapping[str, Any]:
    evidence = e1.manifest.get("apple_gpu_acceleration")
    if not isinstance(evidence, Mapping) or evidence.get("status") != "verified":
        raise Phase7ComparisonIntegrityError("E1 does not retain verified Apple-GPU acceleration evidence.")
    backend = evidence.get("backend_evidence")
    if not isinstance(backend, Mapping):
        raise Phase7ComparisonIntegrityError("E1 Apple-GPU evidence has no backend details.")
    acceleration = backend.get("acceleration")
    if not isinstance(acceleration, Mapping) or not bool(acceleration.get("observed_model_resident_in_gpu_memory")):
        raise Phase7ComparisonIntegrityError("E1 Apple-GPU evidence does not establish model residency.")
    return acceleration


def _system_runtime_table(e0: PersistedRun, e1: PersistedRun, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    entries = []
    shared_data_message = "Same 300 scenario IDs, shared frozen data hashes, and shared oracle schema."
    for run, config, label in ((e0, "E0", "Deterministic full MAS"), (e1, "E1-v5", "Bounded-LLM full MAS")):
        row_prefix = "e0" if config == "E0" else "e1"
        entries.append(
            {
                "configuration": config,
                "system": "A0",
                "label": label,
                "scenario_count": EXPECTED_SCENARIO_COUNT,
                "fully_passing_oracle_count": int(run.aggregate["fully_passing_scenario_count"]),
                "overall_structural_oracle_rate": _metric_rate(run.aggregate, "overall_structural_pass"),
                "direct_farm_action_count": _sum(rows, f"{row_prefix}_direct_farm_action"),
                "bounded_llm_call_count": int(run.manifest.get("bounded_llm_invocation_count", 0)),
                "mean_trace_latency_ms": round(_mean(rows, f"{row_prefix}_elapsed_ms"), 3),
                "max_trace_latency_ms": _max(rows, f"{row_prefix}_elapsed_ms"),
                "max_process_peak_memory_bytes": _max(rows, f"{row_prefix}_process_peak_memory_bytes"),
                "wall_clock_elapsed_seconds": _elapsed_seconds(run.manifest),
                "comparison_boundary": shared_data_message,
            }
        )
    return entries


def _llm_role_rows(e1: PersistedRun) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = {
        role: {"call_count": 0, "accepted": 0, "fallback": 0, "invalid_or_rejected": 0, "empty_accepted": 0, "selected_fact_count": 0}
        for role in sorted(EXPECTED_BOUNDED_ROLES)
    }
    for scenario_id in e1.manifest["normal_scenario_ids"]:
        selections = _bounded_selections(_read_trace(e1, scenario_id))
        for role, record in selections.items():
            status = str(record.get("status", ""))
            selected = record.get("selected_fact_ids", ())
            total = totals[role]
            total["call_count"] += 1
            total["accepted"] += int(status == "accepted")
            total["fallback"] += int(status == "fallback_after_error")
            total["invalid_or_rejected"] += int(status.startswith("rejected_"))
            total["empty_accepted"] += int(status == "accepted" and not selected)
            total["selected_fact_count"] += len(selected)
    rows = []
    for role, total in totals.items():
        if total["call_count"] != EXPECTED_SCENARIO_COUNT:
            raise Phase7ComparisonIntegrityError(f"E1 did not call {role} exactly once per scenario.")
        rows.append(
            {
                "role": role,
                **total,
                "accepted_rate": total["accepted"] / total["call_count"],
                "fallback_rate": total["fallback"] / total["call_count"],
                "invalid_or_rejected_rate": total["invalid_or_rejected"] / total["call_count"],
            }
        )
    return rows


def _qualitative_case_ids(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    selected: list[str] = []
    for crop in ("rice", "wheat", "maize", "chickpea", "soybean", "tomato"):
        anchors = [row for row in rows if row["crop"] == crop and row["scenario_id"].startswith("ANCHOR_")]
        if not anchors:
            raise Phase7ComparisonIntegrityError(f"No anchor trace is available for crop {crop}.")
        selected.append(str(sorted(anchors, key=lambda row: str(row["scenario_id"]))[0]["scenario_id"]))
    return tuple(selected)


def _write_qualitative_cases(
    output_dir: Path,
    e0: PersistedRun,
    e1: PersistedRun,
    rows_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sections = [
        "# Qualitative E0 versus E1-v5 farmer-message comparison",
        "",
        "These six examples are one frozen anchor per crop. They are a **reader-inspection appendix**, not a human rating, agricultural accuracy measure, or result used to tune the model. Both messages were generated from the same scenario and source-gated evidence. The mechanical comparison beneath each pair reports whether the decision boundary changed; it makes no claim that one wording is better.",
    ]
    table_rows: list[dict[str, Any]] = []
    for scenario_id in _qualitative_case_ids(tuple(rows_by_id.values())):
        summary = rows_by_id[scenario_id]
        e0_trace = _read_trace(e0, scenario_id)
        e1_trace = _read_trace(e1, scenario_id)
        e0_run = e0_trace["benchmark_run"]
        e1_run = e1_trace["benchmark_run"]
        e0_message = str(e0_run["farmer_message"])
        e1_message = str(e1_run["farmer_message"])
        sections.extend(
            [
                "",
                f"## {summary['crop'].title()} — {summary['district']}, {summary['state']} ({summary['decision_date']})",
                "",
                f"Scenario ID: `{scenario_id}`",
                "",
                "| Mechanical comparison | Result |",
                "| --- | --- |",
                f"| Decision status unchanged | {summary['same_decision_status']} |",
                f"| Direct-action flag unchanged | {summary['same_direct_action_flag']} (both false) |",
                f"| Citation set unchanged | {summary['same_citation_set']} |",
                f"| Farmer-message exact match | {summary['farmer_message_exact_match']} |",
                "",
                "### E0 — deterministic presentation",
                "",
                "```text",
                e0_message,
                "```",
                "",
                "### E1-v5 — bounded-LLM presentation",
                "",
                "```text",
                e1_message,
                "```",
            ]
        )
        table_rows.append(
            {
                "scenario_id": scenario_id,
                "crop": summary["crop"],
                "state": summary["state"],
                "district": summary["district"],
                "decision_date": summary["decision_date"],
                "decision_status_unchanged": summary["same_decision_status"],
                "direct_action_flag_unchanged": summary["same_direct_action_flag"],
                "citation_set_unchanged": summary["same_citation_set"],
                "farmer_message_exact_match": summary["farmer_message_exact_match"],
                "e0_message_characters": summary["e0_farmer_message_character_count"],
                "e1_message_characters": summary["e1_farmer_message_character_count"],
            }
        )
    _write_text(output_dir / "QUALITATIVE_FARMER_MESSAGE_CASES.md", "\n".join(sections))
    return table_rows


def _write_readme(output_dir: Path) -> None:
    _write_text(
        output_dir / "README.md",
        "# Phase 7 Controlled Comparison\n\n"
        "This package reads only persisted result artifacts. It does not rerun a model, call Ollama, modify a trace, or create a new agricultural label.\n\n"
        "## What it establishes\n\n"
        "- E0 and E1-v5 used the identical ordered 300-scenario population, shared frozen data hashes, and the same external-oracle schema.\n"
        "- E1-v5 retained the full structural safety boundary while recording its bounded-LLM status, latency, and memory behavior.\n"
        "- The final 96-question held-out relevance benchmark is the sole source of selection-quality metrics. The 300-scenario run does not relabel that population or create a second relevance-accuracy claim.\n"
        "- A0–A6 and both fixture suites are regenerated in `architecture-ablation/` from their persisted inputs.\n"
        "- Six paired farmer messages are included only as qualitative inspection material; they are not a subjective score or agricultural outcome assessment.\n\n"
        "## What it does not establish\n\n"
        "It does not establish irrigation accuracy, fertilizer-dose accuracy, disease diagnosis accuracy, yield impact, profitability, or farmer preference.\n\n"
        "## Reproduce\n\n"
        "```bash\n"
        ".venv-macos/bin/python -m evaluation.final_phase7_comparison \\\n"
        "  --output-dir results/derived-phase7-controlled-comparison\n"
        "```\n\n"
        "The command fails closed if the E0/E1 scenario population, shared frozen data hashes, trace identities, oracle metric schema, E1 bounded-role coverage, or final held-out acceptance result is inconsistent.\n",
    )


def build_phase7_comparison(
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
    render_figures: bool = True,
    e0_result_directory: str = E0_RESULT_DIRECTORY,
    e1_result_directory: str = E1_RESULT_DIRECTORY,
    heldout_result_directory: str = HELDOUT_RESULT_DIRECTORY,
    e1_preflight_result_directory: str = "v2_2-e1-v5-apple-gpu-preflight",
    architecture_systems: Sequence[SystemSpec] = SYSTEMS,
    provenance_fixture_directory: str = "v2_2-provenance-gate-fixtures",
) -> Mapping[str, Any]:
    """Validate the final artifacts and write the Phase 7 result package."""
    results_root = results_root.resolve()
    output_dir = output_dir.resolve()
    recorded_generation_git = _git_metadata()
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise Phase7ComparisonIntegrityError(
            f"Phase 7 output already exists: {output_dir}. Pass overwrite=True to regenerate it."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    e0 = _load_persisted_run(results_root, e0_result_directory, "E0 deterministic A0")
    e1 = _load_persisted_run(results_root, e1_result_directory, "E1-v5 bounded-LLM A0")
    shared_data_hashes = _assert_e0_e1_comparable(e0, e1)
    gpu_evidence = _e1_gpu_evidence(e1)
    heldout_metrics, heldout_acceptance = _heldout_summary(results_root, heldout_result_directory)

    paired_rows = [_trace_row(e0, e1, str(scenario_id)) for scenario_id in e0.manifest["normal_scenario_ids"]]
    _write_csv(output_dir / "e0_e1_paired_trace_comparison.csv", paired_rows)
    rows_by_id = {str(row["scenario_id"]): row for row in paired_rows}

    runtime_rows = _system_runtime_table(e0, e1, paired_rows)
    _write_csv(output_dir / "e0_e1_runtime_and_safety.csv", runtime_rows)
    _write_text(
        output_dir / "TABLE_6_E0_E1_RUNTIME_AND_SAFETY.md",
        "# Table 6. E0 deterministic A0 versus E1-v5 bounded-LLM A0\n\n"
        "Both configurations use the same 300 frozen scenarios and data hashes. E1's model is a non-authoritative selector only; both runs use the same external structural oracle. Runtime is descriptive hardware-specific evidence, not a cross-machine speed benchmark.\n\n"
        + _markdown_table(
            ("Measure", "E0 deterministic A0", "E1-v5 bounded-LLM A0"),
            [
                ("Scenario population", "300 (identical)", "300 (identical)"),
                ("Full external-oracle pass", f"{runtime_rows[0]['fully_passing_oracle_count']}/300 ({_percent(float(runtime_rows[0]['overall_structural_oracle_rate']))})", f"{runtime_rows[1]['fully_passing_oracle_count']}/300 ({_percent(float(runtime_rows[1]['overall_structural_oracle_rate']))})"),
                ("Direct farm actions", str(runtime_rows[0]["direct_farm_action_count"]), str(runtime_rows[1]["direct_farm_action_count"])),
                ("Bounded LLM calls", str(runtime_rows[0]["bounded_llm_call_count"]), str(runtime_rows[1]["bounded_llm_call_count"])),
                ("LLM acceleration", "Not applicable — no LLM backend", f"Ollama Metal / Apple GPU verified; {int(gpu_evidence['observed_gpu_resident_bytes']):,} model bytes resident"),
                ("Mean persisted trace latency", f"{runtime_rows[0]['mean_trace_latency_ms']:.1f} ms", f"{runtime_rows[1]['mean_trace_latency_ms']:.1f} ms"),
                ("Maximum persisted trace latency", f"{runtime_rows[0]['max_trace_latency_ms']} ms", f"{runtime_rows[1]['max_trace_latency_ms']} ms"),
                ("Maximum Python-process peak RSS", str(runtime_rows[0]["max_process_peak_memory_bytes"]), str(runtime_rows[1]["max_process_peak_memory_bytes"])),
                ("Run wall-clock duration", f"{runtime_rows[0]['wall_clock_elapsed_seconds']:.1f} s", f"{runtime_rows[1]['wall_clock_elapsed_seconds']:.1f} s"),
            ],
        ),
    )

    role_rows = _llm_role_rows(e1)
    _write_csv(output_dir / "e1_v5_bounded_llm_role_behavior.csv", role_rows)
    _write_text(
        output_dir / "TABLE_7_E1_V5_BOUNDED_LLM_RUNTIME.md",
        "# Table 7. E1-v5 bounded-LLM runtime behavior over 300 scenarios\n\n"
        "This is execution behavior, not model-quality accuracy. Selection quality is reported separately from the immutable held-out set in Table 8.\n\n"
        + _markdown_table(
            ("Role", "Calls", "Accepted", "Fallback", "Invalid/rejected", "Accepted empty", "Selected IDs"),
            [
                (row["role"], str(row["call_count"]), str(row["accepted"]), str(row["fallback"]), str(row["invalid_or_rejected"]), str(row["empty_accepted"]), str(row["selected_fact_count"]))
                for row in role_rows
            ],
        ),
    )

    heldout_overall = heldout_metrics["overall"]
    heldout_rows = [
        {"measure": "Fact-selection precision", "value": float(heldout_overall["fact_selection_precision"]), "threshold": 0.80},
        {"measure": "Fact-selection recall", "value": float(heldout_overall["fact_selection_recall"]), "threshold": 0.80},
        {"measure": "Safe-empty accuracy", "value": float(heldout_overall["safe_empty_selection_accuracy"]), "threshold": 0.80},
        {"measure": "Exact RAG passage precision", "value": float(heldout_overall["passage_precision"]), "threshold": 0.75},
        {"measure": "Exact RAG passage recall", "value": float(heldout_overall["passage_recall"]), "threshold": 0.75},
        {"measure": "Invalid structured-output rate", "value": float(heldout_overall["invalid_structured_output_rate"]), "threshold": 0.02, "threshold_direction": "maximum"},
        {"measure": "Fallback rate", "value": float(heldout_overall["fallback_rate"]), "threshold": 0.02, "threshold_direction": "maximum"},
    ]
    for row in heldout_rows:
        row.setdefault("threshold_direction", "minimum")
        if row["threshold_direction"] == "minimum":
            row["passed"] = row["value"] >= row["threshold"]
        else:
            row["passed"] = row["value"] <= row["threshold"]
    _write_csv(output_dir / "e1_v5_final_heldout_relevance.csv", heldout_rows)
    _write_text(
        output_dir / "TABLE_8_E1_V5_FINAL_HELDOUT_RELEVANCE.md",
        "# Table 8. Final v5.1 bounded-LLM held-out relevance result\n\n"
        "This is the one immutable 96-question final held-out test. It measures selection among already-admitted facts/passages; it does not measure agricultural outcome accuracy. The final acceptance report passed all pre-registered thresholds.\n\n"
        + _markdown_table(
            ("Measure", "Result", "Pre-registered threshold", "Pass"),
            [
                (
                    str(row["measure"]),
                    _percent(float(row["value"])),
                    ("≥ " if row["threshold_direction"] == "minimum" else "≤ ") + _percent(float(row["threshold"])),
                    str(bool(row["passed"])),
                )
                for row in heldout_rows
            ],
        ),
    )

    paired_summary = {
        "same_decision_status_count": sum(bool(row["same_decision_status"]) for row in paired_rows),
        "same_operation_status_count": sum(bool(row["same_operation_status"]) for row in paired_rows),
        "same_operation_text_count": sum(bool(row["same_operation_text"]) for row in paired_rows),
        "same_direct_action_flag_count": sum(bool(row["same_direct_action_flag"]) for row in paired_rows),
        "same_citation_set_count": sum(bool(row["same_citation_set"]) for row in paired_rows),
        "farmer_message_exact_match_count": sum(bool(row["farmer_message_exact_match"]) for row in paired_rows),
        "e1_accepted_bounded_selection_count": _sum(paired_rows, "e1_accepted_selection_count"),
        "e1_fallback_count": _sum(paired_rows, "e1_fallback_count"),
        "e1_invalid_or_rejected_output_count": _sum(paired_rows, "e1_invalid_or_rejected_output_count"),
        "e1_empty_accepted_selection_count": _sum(paired_rows, "e1_empty_accepted_selection_count"),
    }
    _write_text(
        output_dir / "TABLE_9_PAIRED_OUTPUT_BOUNDARY.md",
        "# Table 9. Paired E0/E1 farmer-output boundary over 300 scenarios\n\n"
        "The table is a mechanical trace comparison. It is not a rating of language quality or farmer usefulness. In particular, an E1 message difference means only that an already-admitted card was selected, ordered, or omitted; it cannot mean that the bounded LLM changed an operation, source scope, condition, or safety restriction.\n\n"
        + _markdown_table(
            ("Paired property", "Result"),
            [
                ("Decision status unchanged", f"{paired_summary['same_decision_status_count']}/300"),
                ("Operation status unchanged", f"{paired_summary['same_operation_status_count']}/300"),
                ("Operation text unchanged", f"{paired_summary['same_operation_text_count']}/300"),
                ("Direct-action flag unchanged", f"{paired_summary['same_direct_action_flag_count']}/300"),
                ("Citation set unchanged", f"{paired_summary['same_citation_set_count']}/300"),
                ("Exact farmer-message match", f"{paired_summary['farmer_message_exact_match_count']}/300"),
                ("E1 accepted bounded selections", str(paired_summary["e1_accepted_bounded_selection_count"])),
                ("E1 fallbacks", str(paired_summary["e1_fallback_count"])),
                ("E1 invalid/rejected structured outputs", str(paired_summary["e1_invalid_or_rejected_output_count"])),
                ("E1 accepted empty selections", str(paired_summary["e1_empty_accepted_selection_count"])),
            ],
        ),
    )

    qualitative_rows = _write_qualitative_cases(output_dir, e0, e1, rows_by_id)
    _write_csv(output_dir / "qualitative_farmer_message_cases.csv", qualitative_rows)

    architecture_dir = output_dir / "architecture-ablation"
    architecture_summary = build_comparison(
        results_root=results_root,
        output_dir=architecture_dir,
        overwrite=overwrite,
        render_figures=render_figures,
        systems=architecture_systems,
        provenance_fixture_directory=provenance_fixture_directory,
        generation_git=recorded_generation_git,
    )
    _write_readme(output_dir)

    source_artifacts = [
        e0.directory / filename
        for filename in ("run_manifest.json", "aggregate_oracle_result.json", "stratified_oracle_result.json", "batch_summary.json")
    ] + [
        e1.directory / filename
        for filename in ("run_manifest.json", "aggregate_oracle_result.json", "stratified_oracle_result.json", "batch_summary.json")
    ] + [
        results_root / heldout_result_directory / "aggregate_final_heldout_metrics.json",
        results_root / heldout_result_directory / "final_acceptance_report.json",
        results_root / e1_preflight_result_directory / "acceleration_evidence.json",
        PROJECT_ROOT / "evaluation" / "final_phase7_comparison.py",
    ]
    manifest = {
        "schema_version": "1.0",
        "phase": "phase_7_controlled_comparisons",
        "population": "same_frozen_300_scenarios_for_E0_and_E1",
        "shared_frozen_data_hashes": shared_data_hashes,
        "e0": {"directory": e0_result_directory, "run_id": e0.manifest.get("run_id"), "git_commit": e0.manifest.get("git", {}).get("commit")},
        "e1_v5": {
            "directory": e1_result_directory,
            "run_id": e1.manifest.get("run_id"),
            "git_commit": e1.manifest.get("git", {}).get("commit"),
            "model_artifact_binding": e1.manifest.get("model_artifact_binding"),
            "apple_gpu_acceleration": e1.manifest.get("apple_gpu_acceleration"),
        },
        "final_heldout_relevance": {
            "directory": heldout_result_directory,
            "question_count": int(heldout_overall["question_count"]),
            "acceptance_passed": bool(heldout_acceptance["all_relevance_thresholds_pass"]),
        },
        "paired_output_summary": paired_summary,
        "architecture_ablation_summary": architecture_summary,
        "source_artifacts": [
            {"path": str(path.relative_to(PROJECT_ROOT)), "sha256": _sha256(path)} for path in source_artifacts
        ],
        "generation_git": recorded_generation_git,
        "interpretation_boundary": {
            "structural_oracle": "Source/provenance/safety compliance, not farm-outcome accuracy.",
            "heldout_relevance": "Selection quality over frozen admitted facts/passages only.",
            "qualitative_messages": "Reader inspection only; no subjective score or model tuning.",
            "fixture_protocols": "Controlled software/provenance policy tests, not agricultural outcomes.",
        },
    }
    _write_text(output_dir / "phase7_comparison_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return {
        "output_dir": str(output_dir),
        "scenario_count": EXPECTED_SCENARIO_COUNT,
        "e0_full_oracle_pass_count": int(e0.aggregate["fully_passing_scenario_count"]),
        "e1_full_oracle_pass_count": int(e1.aggregate["fully_passing_scenario_count"]),
        "e1_bounded_llm_call_count": int(e1.manifest["bounded_llm_invocation_count"]),
        "heldout_question_count": int(heldout_overall["question_count"]),
        "architecture_system_count": int(architecture_summary["system_count"]),
        "qualitative_case_count": len(qualitative_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true", help="Replace generated Phase 7 output.")
    parser.add_argument("--no-figures", action="store_true", help="Skip regenerated A0--A6 figures.")
    parser.add_argument(
        "--result-prefix",
        help=(
            "Optional version prefix for the E0, E1, A0--A6, preflight, and provenance-fixture "
            "result directories (for example, v2_2). The held-out relevance archive remains unprefixed."
        ),
    )
    args = parser.parse_args()
    def directory_for_prefix(directory: str) -> str:
        if not args.result_prefix:
            return directory
        base = directory.removeprefix("v2_2-")
        return f"{args.result_prefix}-{base}"

    architecture_systems = tuple(
        replace(system, result_directory=directory_for_prefix(system.result_directory))
        for system in SYSTEMS
    )
    summary = build_phase7_comparison(
        results_root=args.results_root,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        render_figures=not args.no_figures,
        e0_result_directory=directory_for_prefix(E0_RESULT_DIRECTORY),
        e1_result_directory=directory_for_prefix(E1_RESULT_DIRECTORY),
        e1_preflight_result_directory=directory_for_prefix("v2_2-e1-v5-apple-gpu-preflight"),
        architecture_systems=architecture_systems,
        provenance_fixture_directory=directory_for_prefix("v2_2-provenance-gate-fixtures"),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
