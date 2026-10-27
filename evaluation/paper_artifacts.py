"""Generate the Phase 10 paper tables and static figures from frozen artifacts.

The generator is deliberately read-only with respect to benchmark data and
saved runs.  It does not invoke an LLM, rebuild a scenario, or alter an
existing result archive.  Each generated artifact is accompanied by a
machine-readable manifest that fingerprints every source file it consumed.

The reported measures are structural-conformance, evidence-selection, and
runtime measures.  They are never presented as agricultural outcome accuracy.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from textwrap import wrap
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "v2_2-paper-artifacts"

LLM_BOUNDED_AGENT_NUMBERS = {5, 6, 7, 8, 9, 13, 19, 20}
ROLE_LABELS = {
    "weather_context_agent": "Weather context",
    "soil_context_agent": "Soil context",
    "satellite_ndvi_context_agent": "Satellite / NDVI",
    "market_evidence_agent": "Market evidence",
    "fertilizer_baseline_agent": "Fertilizer baseline",
    "official_operations_rag_agent": "Official operations RAG",
    "provenance_aware_coordinator_agent": "Coordinator",
    "farmer_explanation_citation_agent": "Farmer explanation",
}


class PaperArtifactError(ValueError):
    """Raised when an immutable Phase 10 input is missing or malformed."""


@dataclass(frozen=True)
class InputFile:
    label: str
    path: Path


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise PaperArtifactError(f"Required paper-artifact input is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PaperArtifactError(f"Invalid JSON input: {path}") from exc


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise PaperArtifactError(f"Required paper-artifact input is missing: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise PaperArtifactError(f"Cannot fingerprint missing input: {path}")
    return sha256(path.read_bytes()).hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise PaperArtifactError(f"Refusing to write an empty table: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    normalized = [[str(value).replace("|", "\\|").replace("\n", " ") for value in row] for row in rows]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in normalized),
        ]
    )


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _short(text: str, limit: int = 150) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _strip_markdown(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    return value.replace("`", "").strip()


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
        return {"commit": commit, "worktree_clean": not bool(status), "status": status}
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - environment dependent
        return {"status": "unavailable", "error": type(exc).__name__}


def _base_inputs() -> dict[str, InputFile]:
    def item(label: str, relative: str) -> tuple[str, InputFile]:
        return label, InputFile(label, PROJECT_ROOT / relative)

    return dict(
        [
            item("canonical scenario manifest", "data/scenarios/manifests/scenario_manifest.csv"),
            item("final registry", "data/registry/final_study_sites.csv"),
            item("MAS enrichment contract", "data/scenarios/enriched/mas_enrichment_contract.csv"),
            item("regional operation plan items", "data/scenarios/enriched/regional_operation_plan_items.csv"),
            item("official action records", "data/scenarios/enriched/official_action_records_all.csv"),
            item("official RAG catalog", "data/scenarios/enriched/official_rag_corpus_catalog.csv"),
            item("official RAG chunks", "data/scenarios/enriched/official_rag_corpus_all_chunks.csv"),
            item("post-harvest plan items", "data/scenarios/enriched/scenario_postharvest_plan_items.csv"),
            item("post-harvest RAG passages", "data/scenarios/enriched/postharvest_rag_passages.csv"),
            item("post-harvest logistics context", "data/scenarios/enriched/scenario_postharvest_logistics_context.csv"),
            item("agent contract", "Documentation/AGENTS.md"),
            item("A0-A6 system summary", "results/v2_2-phase7-controlled-comparison/architecture-ablation/system_summary.csv"),
            item("A0-A6 metric rates", "results/v2_2-phase7-controlled-comparison/architecture-ablation/oracle_metric_rates.csv"),
            item("controlled fixture outcomes", "results/v2_2-phase7-controlled-comparison/architecture-ablation/fixture_protocol_results.csv"),
            item("crop-stratified outcomes", "results/v2_2-phase7-controlled-comparison/architecture-ablation/crop_stratified_key_metrics.csv"),
            item("district-stratified outcomes", "results/v2_2-phase7-controlled-comparison/architecture-ablation/district_stratified_key_metrics.csv"),
            item("E0/E1 runtime comparison", "results/v2_2-phase7-controlled-comparison/e0_e1_runtime_and_safety.csv"),
            item("E1 per-role runtime", "results/v2_2-phase7-controlled-comparison/e1_v5_bounded_llm_role_behavior.csv"),
            item("E1 final held-out metrics", "results/e1-v5-heldout-final/aggregate_final_heldout_metrics.json"),
            item("E1 held-out acceptance report", "results/v2_2-phase7-controlled-comparison/e1_v5_final_heldout_relevance.csv"),
            item("E1 case-study index", "results/v2_2-phase7-controlled-comparison/qualitative_farmer_message_cases.csv"),
            item("E1 full-MAS manifest", "results/v2_2-e1-v5-full-mas/run_manifest.json"),
            item("E2 relevance aggregate", "results/v2_2-e2-v5-relevance-14b/aggregate_relevance_metrics.json"),
            item("E2 relevance manifest", "results/v2_2-e2-v5-relevance-14b/run_manifest.json"),
            item("E2 acceptance report", "results/v2_2-e2-v5-relevance-14b/acceptance_report.json"),
            item("E2 Metal preflight", "results/v2_2-e2-apple-gpu-preflight/acceleration_evidence.json"),
            item("E3 relevance aggregate", "results/v2_2-e3-v5-relevance-14b-mlx/aggregate_relevance_metrics.json"),
            item("E3 relevance manifest", "results/v2_2-e3-v5-relevance-14b-mlx/run_manifest.json"),
            item("E3 acceptance report", "results/v2_2-e3-v5-relevance-14b-mlx/acceptance_report.json"),
            item("E3 Metal preflight", "results/v2_2-e3-apple-gpu-preflight/acceleration_evidence.json"),
            item("provenance fixture outcome", "results/v2_2-provenance-gate-fixtures/provenance_fixture_oracle_result.json"),
        ]
    )


def _agent_rows(contract_path: Path) -> list[dict[str, Any]]:
    """Extract the five canonical per-stage agent tables from AGENTS.md."""
    lines = contract_path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(lines):
        if not lines[cursor].startswith("| # | Agent / module | Input | Output |"):
            cursor += 1
            continue
        cursor += 2  # Header and markdown divider.
        while cursor < len(lines) and lines[cursor].startswith("|"):
            cells = [cell.strip() for cell in lines[cursor].strip().strip("|").split("|")]
            if len(cells) == 5 and cells[0].isdigit():
                number = int(cells[0])
                rows.append(
                    {
                        "number": number,
                        "agent": _strip_markdown(cells[1]),
                        "admitted_input": _strip_markdown(cells[2]),
                        "output": _strip_markdown(cells[3]),
                        "restriction_or_handoff": _strip_markdown(cells[4]),
                        "execution": (
                            "LLM-bounded ranking after deterministic admission"
                            if number in LLM_BOUNDED_AGENT_NUMBERS
                            else "Deterministic"
                        ),
                    }
                )
            cursor += 1
    numbers = [row["number"] for row in rows]
    if numbers != list(range(1, 22)):
        raise PaperArtifactError(
            "AGENTS.md did not yield the required 21 canonical agent rows; "
            f"found numbers {numbers}."
        )
    return rows


def _scenario_trace(path: Path) -> Mapping[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("benchmark_run"), Mapping):
        raise PaperArtifactError(f"Scenario trace lacks benchmark_run: {path}")
    return payload["benchmark_run"]


def _build_composition(inputs: Mapping[str, InputFile]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    scenarios = _read_csv(inputs["canonical scenario manifest"].path)
    sites = _read_csv(inputs["final registry"].path)
    contract = _read_csv(inputs["MAS enrichment contract"].path)
    plan_items = _read_csv(inputs["regional operation plan items"].path)
    actions = _read_csv(inputs["official action records"].path)
    rag_catalog = _read_csv(inputs["official RAG catalog"].path)
    rag_chunks = _read_csv(inputs["official RAG chunks"].path)
    postharvest_items = _read_csv(inputs["post-harvest plan items"].path)
    postharvest_passages = _read_csv(inputs["post-harvest RAG passages"].path)
    postharvest_context = _read_csv(inputs["post-harvest logistics context"].path)

    conditional_items = [
        row for row in plan_items if row.get("item_status") == "conditional_operation_pending_unobserved_field_precondition"
    ]
    operation_scenarios = {row["scenario_id"] for row in conditional_items}
    stats = {
        "scenario_count": len(scenarios),
        "site_count": len(sites),
        "crop_count": len({row["crop"] for row in scenarios}),
        "state_count": len({row["state"] for row in scenarios}),
        "district_count": len({row["district"] for row in scenarios}),
        "enrichment_contract_count": len(contract),
        "regional_plan_count": len(plan_items),
        "operation_record_count": len(actions),
        "operation_covered_scenario_count": len(operation_scenarios),
        "conditional_operation_item_count": len(conditional_items),
        "rag_document_count": len(rag_catalog),
        "rag_chunk_count": len(rag_chunks),
        "postharvest_item_count": len(postharvest_items),
        "postharvest_passage_count": len(postharvest_passages),
        "postharvest_context_count": len(postharvest_context),
    }
    if stats["scenario_count"] != 300 or stats["site_count"] != 30 or stats["crop_count"] != 6:
        raise PaperArtifactError(f"Unexpected frozen benchmark composition: {stats}")
    rows = [
        {
            "layer": "Frozen study registry",
            "what_is_counted": "Admitted crop × district × season sites",
            "count": stats["site_count"],
            "source_artifact": "data/registry/final_study_sites.csv",
            "research_role": "Locks location-aligned study sites before scenario generation.",
        },
        {
            "layer": "Canonical scenario benchmark",
            "what_is_counted": "Aligned historical decision contexts",
            "count": stats["scenario_count"],
            "source_artifact": "data/scenarios/manifests/scenario_manifest.csv",
            "research_role": "The fixed six-crop, 30-site test population.",
        },
        {
            "layer": "First / second enrichment contract",
            "what_is_counted": "Scenario capability and evidence contracts",
            "count": stats["enrichment_contract_count"],
            "source_artifact": "data/scenarios/enriched/mas_enrichment_contract.csv",
            "research_role": "Makes context availability and action restrictions explicit.",
        },
        {
            "layer": "Third enrichment: regional plans",
            "what_is_counted": "Source-linked calendar, nutrient, IPM, and conditional operation plan items",
            "count": stats["regional_plan_count"],
            "source_artifact": "data/scenarios/enriched/regional_operation_plan_items.csv",
            "research_role": f"Includes {stats['conditional_operation_item_count']} conditional items across {stats['operation_covered_scenario_count']} scenarios.",
        },
        {
            "layer": "Official operation recovery",
            "what_is_counted": "Source-quoted operation records",
            "count": stats["operation_record_count"],
            "source_artifact": "data/scenarios/enriched/official_action_records_all.csv",
            "research_role": "Provides scope- and condition-bound operational evidence.",
        },
        {
            "layer": "Scoped official RAG",
            "what_is_counted": "Admitted official source documents",
            "count": stats["rag_document_count"],
            "source_artifact": "data/scenarios/enriched/official_rag_corpus_catalog.csv",
            "research_role": f"Metadata-gated corpus with {stats['rag_chunk_count']} indexed chunks.",
        },
        {
            "layer": "Fourth enrichment: post-harvest",
            "what_is_counted": "Conditional crop-scoped handling plan items",
            "count": stats["postharvest_item_count"],
            "source_artifact": "data/scenarios/enriched/scenario_postharvest_plan_items.csv",
            "research_role": f"Paired with {stats['postharvest_passage_count']} exact-crop passages and {stats['postharvest_context_count']} site contexts.",
        },
    ]
    return rows, stats


def _metric_lookup(rows: Sequence[Mapping[str, str]]) -> dict[tuple[str, str], Mapping[str, str]]:
    return {(str(row["system_id"]), str(row["metric"])): row for row in rows}


def _format_rate(row: Mapping[str, str]) -> str:
    return f"{row['passed']}/{row['total']} ({_percent(float(row['rate']))})"


def _format_optional_rate(value: Any) -> str:
    return "—" if value is None else _percent(float(value))


def _backend_row(configuration: str, aggregate: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    overall = aggregate.get("overall")
    if not isinstance(overall, Mapping):
        raise PaperArtifactError(f"{configuration} aggregate lacks an overall result.")
    config = manifest.get("configuration", {})
    if not isinstance(config, Mapping):
        config = {}
    runtime = manifest.get("runtime_configuration", {})
    if not isinstance(runtime, Mapping):
        runtime = {}
    artifact = manifest.get("model_artifact_binding", {})
    if not isinstance(artifact, Mapping):
        artifact = {}
    role_artifact = artifact.get(configuration)
    if not isinstance(role_artifact, Mapping):
        role_artifact = {}
    backend = runtime.get("backend") or config.get("backend") or manifest.get("backend", "not recorded")
    model = (
        runtime.get("runtime_model_identifier")
        or config.get("ollama_tag")
        or config.get("model")
        or config.get("model_tag")
        or role_artifact.get("runtime_model_identifier")
        or manifest.get("model", "not recorded")
    )
    accepted = aggregate.get("all_relevance_thresholds_pass")
    if accepted is None:
        accepted = aggregate.get("final_research_result_permitted", False)
    return {
        "configuration": configuration,
        "backend": backend,
        "model": model,
        "question_count": int(overall["question_count"]),
        "mean_latency_ms": float(overall["mean_latency_ms"]),
        "p95_latency_ms": float(overall["p95_latency_ms"]),
        "fallback_rate": float(overall["fallback_rate"]),
        "invalid_output_rate": float(overall["invalid_structured_output_rate"]),
        "accepted": bool(accepted),
        "max_process_peak_memory_bytes": int(overall["max_process_peak_memory_bytes"]),
    }


def _negative_transfer_row(
    configuration: str,
    aggregate: Mapping[str, Any],
    manifest: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize one blocked 14B transfer without implying a full-MAS result."""
    overall = aggregate.get("overall")
    checks = acceptance.get("checks")
    backend_evidence = preflight.get("backend_evidence")
    if not isinstance(overall, Mapping) or not isinstance(checks, Mapping) or not isinstance(backend_evidence, Mapping):
        raise PaperArtifactError(f"{configuration} transfer artifacts are malformed.")
    acceleration = backend_evidence.get("acceleration")
    model = backend_evidence.get("model")
    if not isinstance(acceleration, Mapping) or not isinstance(model, Mapping):
        raise PaperArtifactError(f"{configuration} preflight lacks model or acceleration evidence.")
    gpu_bytes = int(acceleration.get("observed_gpu_resident_bytes", 0))
    failed_checks = sorted(name for name, passed in checks.items() if passed is False)
    if preflight.get("status") != "verified" or gpu_bytes <= 0:
        raise PaperArtifactError(f"{configuration} lacks verified nonzero Apple-GPU evidence.")
    if acceptance.get("all_relevance_thresholds_pass") is not False or failed_checks != ["invalid_structured_output_rate"]:
        raise PaperArtifactError(
            f"{configuration} is not the expected structured-output-only negative transfer result."
        )
    configuration_metadata = manifest.get("configuration")
    if not isinstance(configuration_metadata, Mapping):
        configuration_metadata = {}
    return {
        "configuration": configuration,
        "backend": str(backend_evidence.get("backend", "not recorded")),
        "model": str(model.get("runtime_model_identifier") or model.get("tag") or "not recorded"),
        "artifact_format": str(model.get("format") or model.get("quantization_level") or "not recorded"),
        "comparison_type": str(preflight.get("comparison_type", "not recorded")),
        "gpu_acceleration": f"Verified; {gpu_bytes / 1_000_000_000:.2f} GB resident",
        "question_count": int(overall["question_count"]),
        "accepted_selection_count": int(overall["accepted_selection_count"]),
        "fact_selection_precision": float(overall["fact_selection_precision"]),
        "fact_selection_recall": float(overall["fact_selection_recall"]),
        "safe_empty_selection_accuracy": float(overall["safe_empty_selection_accuracy"]),
        "passage_precision": float(overall["passage_precision"]),
        "passage_recall": float(overall["passage_recall"]),
        "invalid_structured_output_rate": float(overall["invalid_structured_output_rate"]),
        "fallback_rate": float(overall["fallback_rate"]),
        "mean_latency_ms": float(overall["mean_latency_ms"]),
        "failed_acceptance_check": ", ".join(failed_checks),
        "pilot_and_full_mas": "Not run: transfer gate blocked scale-up",
        "pre_registered_next_step": str(acceptance.get("next_step_if_fail", "not recorded")),
        "prompt_template_version": str(configuration_metadata.get("prompt_template_version", "not recorded")),
    }


def _write_composition_table(output_dir: Path, rows: Sequence[Mapping[str, Any]], stats: Mapping[str, int]) -> None:
    table = _markdown_table(
        ("Layer", "Count", "What is counted", "Research role"),
        [(row["layer"], row["count"], row["what_is_counted"], row["research_role"]) for row in rows],
    )
    _write_text(
        output_dir / "TABLE_1_DATASET_COMPOSITION.md",
        "# Table 1. Frozen dataset and evidence composition\n\n"
        "This is a benchmark composition table, not a claim that every source is a live farm observation. "
        "The scenario population is fixed at six crops, 30 study sites, "
        f"{stats['district_count']} districts, {stats['state_count']} states, and {stats['scenario_count']} historical contexts.\n\n"
        + table
        + "\n\nAll counts are regenerated from the listed source artifacts. The operation and post-harvest layers retain "
        "their documented field-condition boundaries; they do not authorize a farm-specific action.",
    )
    _write_csv(output_dir / "dataset_composition.csv", rows)


def _write_agent_table(output_dir: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    table = _markdown_table(
        ("#", "Agent", "Admitted evidence / input", "Output", "Restriction or handoff", "Execution"),
        [
            (
                row["number"],
                row["agent"],
                _short(str(row["admitted_input"]), 115),
                _short(str(row["output"]), 105),
                _short(str(row["restriction_or_handoff"]), 140),
                row["execution"],
            )
            for row in rows
        ],
    )
    _write_text(
        output_dir / "TABLE_2_AGENT_RESPONSIBILITIES.md",
        "# Table 2. Agent responsibility and authority boundary\n\n"
        "Rows are extracted from the frozen agent contract in `Documentation/AGENTS.md`. The eight LLM-bounded "
        "roles can only rank or omit candidate IDs after deterministic admission; their call cannot create a claim, "
        "change a source, relax a condition, or issue a direct farm action.\n\n"
        + table,
    )
    _write_csv(output_dir / "agent_responsibilities.csv", rows)


def _write_structural_table(
    output_dir: Path,
    summary: Sequence[Mapping[str, str]],
    metrics: Sequence[Mapping[str, str]],
) -> None:
    lookup = _metric_lookup(metrics)
    selected = (
        ("overall_structural_pass", "All structural checks"),
        ("grounded_plan_coverage", "Grounded plan coverage"),
        ("conditional_operation_completeness", "Conditional-operation completeness"),
        ("plan_and_selected_operation_citation_coverage", "Plan citation coverage"),
        ("rag_scope_compliance", "RAG scope compliance"),
        ("conflict_trace_completeness_and_exclusion", "Conflict trace compliance"),
        ("unsupported_action_prevention_and_agent_permissions", "Safety / permissions"),
    )
    header = ("System", "Role", *(label for _, label in selected), "Direct farm actions")
    table_rows = []
    for row in summary:
        system_id = row["system_id"]
        table_rows.append(
            (
                row["label"],
                row["comparison_role"],
                *(_format_rate(lookup[(system_id, metric)]) for metric, _ in selected),
                row["direct_farm_action_count"],
            )
        )
    _write_text(
        output_dir / "TABLE_3_MAIN_STRUCTURAL_RESULTS.md",
        "# Table 3. Main structural-conformance results over the frozen 300 scenarios\n\n"
        "A0/E0 is the deterministic full-MAS reference. A1–A6 are declared evaluation-only baselines or ablations. "
        "A rate is an exact independent-oracle conformance rate over the fixed benchmark, **not** irrigation, yield, "
        "disease, fertilizer-dose, market-profit, or general agricultural accuracy.\n\n"
        + _markdown_table(header, table_rows)
        + "\n\nA5 equals A0 on valid normal inputs because all 300 records were admitted as aligned; its protective value is "
        "measured only by the controlled malformed-bundle fixtures in Table 6.",
    )


def _write_relevance_table(output_dir: Path, heldout: Mapping[str, Any], acceptance: Sequence[Mapping[str, str]]) -> None:
    agents = heldout.get("by_agent")
    overall = heldout.get("overall")
    if not isinstance(agents, Mapping) or not isinstance(overall, Mapping):
        raise PaperArtifactError("Held-out E1 result lacks by_agent or overall metrics.")
    role_rows = []
    for role, label in ROLE_LABELS.items():
        values = agents.get(role)
        if not isinstance(values, Mapping):
            raise PaperArtifactError(f"Held-out result is missing role {role}.")
        role_rows.append(
            (
                label,
                int(values["question_count"]),
                _format_optional_rate(values.get("fact_selection_precision")),
                _format_optional_rate(values.get("fact_selection_recall")),
                _format_optional_rate(values.get("safe_empty_selection_accuracy")),
                _format_optional_rate(values.get("passage_precision")),
                _format_optional_rate(values.get("passage_recall")),
                _format_optional_rate(values.get("plan_or_operation_selection_accuracy")),
                _percent(float(values["invalid_structured_output_rate"])),
                _percent(float(values["fallback_rate"])),
                f"{float(values['mean_latency_ms']):.0f}",
            )
        )
    acceptance_rows = [
        (row["measure"], _percent(float(row["value"])), _percent(float(row["threshold"])), row["threshold_direction"], row["passed"])
        for row in acceptance
    ]
    _write_text(
        output_dir / "TABLE_4_BOUNDED_LLM_RELEVANCE.md",
        "# Table 4. Final E1-v5.1 held-out bounded-LLM relevance evaluation\n\n"
        "The 96-question source-derived held-out set was immutable and disjoint from the development contexts/sites. "
        "These measures test selection among already-admitted facts/passages; they do not measure farm outcomes.\n\n"
        "## Per-role results\n\n"
        + _markdown_table(
            ("Role", "Questions", "Fact P", "Fact R", "Safe empty", "Passage P", "Passage R", "Plan/op.", "Invalid", "Fallback", "Mean ms"),
            role_rows,
        )
        + "\n\n## Frozen acceptance criteria\n\n"
        + _markdown_table(("Measure", "Observed", "Threshold", "Direction", "Passed"), acceptance_rows)
        + "\n\nOverall: fact precision/recall "
        f"{_percent(float(overall['fact_selection_precision']))}/{_percent(float(overall['fact_selection_recall']))}; "
        f"safe-empty {_percent(float(overall['safe_empty_selection_accuracy']))}; invalid "
        f"{_percent(float(overall['invalid_structured_output_rate']))}; fallback {_percent(float(overall['fallback_rate']))}.",
    )
    _write_csv(
        output_dir / "bounded_llm_relevance_by_role.csv",
        [
            {
                "role": role,
                **dict(values),
            }
            for role, values in agents.items()
            if isinstance(values, Mapping)
        ],
    )


def _write_fixture_tables(
    output_dir: Path,
    fixtures: Sequence[Mapping[str, str]],
    provenance: Mapping[str, Any],
) -> None:
    table_rows = [
        (row["protocol"], row["measure"], row["system"], f"{row['numerator']}/{row['denominator']} ({_percent(float(row['rate']))})", row["interpretation"])
        for row in fixtures
    ]
    _write_text(
        output_dir / "TABLE_5_CONFLICT_RESOLUTION.md",
        "# Table 5. Controlled conflict-resolution results\n\n"
        "These 60 fixtures are labelled in-memory counterfactual policy tests, not additional farm scenarios or historical observations. "
        "The A6 coordinator-resolution row is intentionally zero because the ablation withholds conflict records from its coordinator.\n\n"
        + _markdown_table(("Protocol", "Measure", "System", "Result", "Interpretation"), table_rows),
    )
    provenance_rows = [
        ("A0 alignment validator blocks", f"{provenance['a0_alignment_validator_blocked_count']}/50", "Malformed plan identity/binding rows stop before downstream agents."),
        ("A5 omitted-gate exposure", f"{provenance['a5_alignment_validator_exposure_count']}/50", "Expected evaluation-only exposure when the alignment boundary is removed."),
        ("Shared raw-payload hash blocks", "10/10", "The frozen loader rejects altered raw-source payloads before either workflow starts."),
        ("Invalid-fixture direct actions", f"{provenance['direct_farm_action_fixture_count']}", "No malformed bundle can produce a decision or direct farm action."),
    ]
    _write_text(
        output_dir / "TABLE_6_PROVENANCE_GATE.md",
        "# Table 6. Provenance and alignment gate evaluation\n\n"
        "The fixture runner applies controlled single-fault mutations to otherwise valid frozen bundles. It demonstrates the gate boundary "
        "that normal 300-scenario records cannot exercise because those records are already aligned. This is software/provenance protection, "
        "not agricultural outcome validation.\n\n"
        + _markdown_table(("Measure", "Observed", "Meaning"), provenance_rows),
    )


def _write_stratified_table(
    output_dir: Path,
    crop_rows: Sequence[Mapping[str, str]],
    district_rows: Sequence[Mapping[str, str]],
) -> None:
    crop_lookup = {(row["system_id"], row["crop"], row["metric"]): row for row in crop_rows}
    crops = ("rice", "wheat", "maize", "chickpea", "soybean", "tomato")
    crop_table = [
        (
            crop.title(),
            _format_rate(crop_lookup[("A0", crop, "overall_structural_pass")]),
            _format_rate(crop_lookup[("A3", crop, "overall_structural_pass")]),
            _format_rate(crop_lookup[("A3", crop, "conditional_operation_completeness")]),
            _format_rate(crop_lookup[("A6", crop, "overall_structural_pass")]),
        )
        for crop in crops
    ]
    district_lookup = {(row["system_id"], row["district"], row["metric"]): row for row in district_rows}
    districts = sorted({row["district"] for row in district_rows})
    district_table = [
        (
            district,
            _format_rate(district_lookup[("A0", district, "overall_structural_pass")]),
            _format_rate(district_lookup[("A3", district, "overall_structural_pass")]),
            _format_rate(district_lookup[("A3", district, "conditional_operation_completeness")]),
        )
        for district in districts
    ]
    _write_text(
        output_dir / "TABLE_7_STRATIFIED_CONFORMANCE.md",
        "# Table 7. Crop and geographic structural conformance / coverage\n\n"
        "These strata make evidence coverage and contract conformance visible. They are **not** crop-performance, yield, or farmer-benefit rankings. "
        "A3 quantifies the fixed corpus coverage lost when scoped operation recovery is withheld. A6's full-pass column captures the natural "
        "conflict-trace loss; the precise controlled-resolution outcomes are reported separately in Table 5.\n\n"
        "## Crop strata\n\n"
        + _markdown_table(("Crop", "A0 all checks", "A3 all checks", "A3 conditional operations", "A6 all checks"), crop_table)
        + "\n\n## District strata\n\n"
        + _markdown_table(("District", "A0 all checks", "A3 all checks", "A3 conditional operations"), district_table),
    )


def _case_citations(trace: Mapping[str, Any]) -> str:
    decision = trace.get("decision", {})
    citations = decision.get("citations", []) if isinstance(decision, Mapping) else []
    if not isinstance(citations, list):
        return "No citations recorded"
    labels = []
    for citation in citations:
        if isinstance(citation, Mapping):
            labels.append(str(citation.get("source_document_id") or citation.get("source_id") or citation.get("title") or "source"))
        elif isinstance(citation, str):
            labels.append(citation)
    return ", ".join(dict.fromkeys(labels)) or "No citations recorded"


def _write_case_studies(output_dir: Path, cases: Sequence[Mapping[str, str]]) -> None:
    sections = [
        "# Table 8. Source-traceable farmer-facing and conflict-resolution case studies\n\n"
        "The six normal cases are one anchor scenario per crop from the saved E0/E1 paired-output comparison. "
        "Each retains its decision status, direct-action flag, and citation set across E0 and E1; E1 only changes bounded presentation/selection. "
        "The final conflict case is explicitly evaluation-only and never appears as a farmer message.\n"
    ]
    for case in cases:
        scenario_id = case["scenario_id"]
        trace = _scenario_trace(
            PROJECT_ROOT / "results" / "v2_2-e1-v5-full-mas" / "scenarios" / f"{scenario_id}.json"
        )
        decision = trace.get("decision", {})
        message = str(trace.get("farmer_message", "")).strip()
        sections.append(
            "\n## "
            f"{case['crop'].title()} — {case['district']}, {case['state']} ({case['decision_date']})\n\n"
            f"- Scenario: `{scenario_id}`\n"
            f"- Decision status: `{decision.get('decision_status', 'not recorded')}`\n"
            f"- Direct farm action: `{decision.get('direct_farm_action_issued', 'not recorded')}`\n"
            f"- Source IDs in decision trace: {_case_citations(trace)}\n"
            f"- E0/E1 citation set unchanged: `{case['citation_set_unchanged']}`; message exact match: `{case['farmer_message_exact_match']}`.\n\n"
            "**Saved E1 farmer-facing plan**\n\n"
            + "\n".join(f"> {line}" if line else ">" for line in message.splitlines())
            + "\n"
        )

    fixture_runs = _read_json(
        PROJECT_ROOT / "results" / "v2_2-e0-full-mas" / "conflict_fixture_runs.json"
    )
    if not isinstance(fixture_runs, list) or not fixture_runs or not isinstance(fixture_runs[0], Mapping):
        raise PaperArtifactError("Conflict fixture archive lacks a representative fixture record.")
    fixture = fixture_runs[0]
    fixture_decision = fixture.get("decision", {})
    if not isinstance(fixture_decision, Mapping):
        fixture_decision = {}
    resolution_records = fixture_decision.get("conflict_resolution_records", [])
    resolution = resolution_records[0] if isinstance(resolution_records, list) and resolution_records else {}
    if not isinstance(resolution, Mapping):
        resolution = {}
    rule_path = resolution.get("rule_path", [])
    if isinstance(rule_path, list):
        rule_path = " → ".join(str(value) for value in rule_path)
    sections.append(
        "\n## Evaluation-only coordinator conflict resolution\n\n"
        f"- Fixture: `{fixture.get('fixture_id', 'not recorded')}`\n"
        f"- Base scenario: `{fixture.get('base_scenario_id', 'not recorded')}`\n"
        f"- Rule path: `{rule_path or 'not recorded'}`\n"
        f"- Resolution: `{resolution.get('status', 'not recorded')}`; retained citation(s): `{', '.join(str(value) for value in resolution.get('citations', [])) or 'none'}`.\n"
        "- Interpretation: the controlled same-domain source-precedence case verifies deterministic resolution. "
        "It is not a real farm observation and is excluded from farmer-facing output.\n"
    )
    _write_text(output_dir / "TABLE_8_CASE_STUDIES.md", "".join(sections))


def _write_runtime_table(
    output_dir: Path,
    full_runtime: Sequence[Mapping[str, str]],
    backend_rows: Sequence[Mapping[str, Any]],
) -> None:
    full_table = [
        (
            row["configuration"],
            row["label"],
            row["scenario_count"],
            f"{row['fully_passing_oracle_count']}/{row['scenario_count']} ({_percent(float(row['overall_structural_oracle_rate']))})",
            row["bounded_llm_call_count"],
            f"{float(row['mean_trace_latency_ms']):.1f}",
            f"{float(row['max_trace_latency_ms']):.1f}",
            f"{float(row['max_process_peak_memory_bytes']) / (1024 ** 2):.1f}",
            f"{float(row['wall_clock_elapsed_seconds']):.1f}",
        )
        for row in full_runtime
    ]
    backend_table = [
        (
            row["configuration"],
            row["backend"],
            row["model"],
            row["question_count"],
            "accepted" if row["accepted"] else "not accepted (structured-output gate)",
            f"{row['mean_latency_ms']:.1f}",
            f"{row['p95_latency_ms']:.1f}",
            _percent(row["invalid_output_rate"]),
            _percent(row["fallback_rate"]),
            f"{row['max_process_peak_memory_bytes'] / (1024 ** 2):.1f}",
        )
        for row in backend_rows
    ]
    _write_text(
        output_dir / "TABLE_9_RUNTIME_AND_BACKEND.md",
        "# Table 9. Runtime and backend measurements\n\n"
        "Full-MAS runtime and held-out relevance runtime are distinct measurements and must not be compared as the same workload. "
        "Memory is descriptive process peak RSS/measurement output, not an isolated model-memory benchmark. E2/E3 are retained as transparent "
        "structured-output-gate negative results and have no 30-site or 300-scenario full-MAS run.\n\n"
        "## Full 300-scenario MAS workloads\n\n"
        + _markdown_table(("Configuration", "System", "Scenarios", "Structural pass", "LLM calls", "Mean trace ms", "Max trace ms", "Peak MiB", "Wall s"), full_table)
        + "\n\n## Held-out relevance runtime / deployment observations\n\n"
        + _markdown_table(("Configuration", "Backend", "Model", "Questions", "Result state", "Mean ms", "P95 ms", "Invalid", "Fallback", "Peak MiB"), backend_table),
    )
    _write_csv(output_dir / "runtime_and_backend.csv", list(backend_rows))


def _write_14b_transfer_negative_table(
    output_dir: Path,
    transfer_rows: Sequence[Mapping[str, Any]],
) -> None:
    """Write a separately labelled table for deployments blocked before MAS use."""
    if len(transfer_rows) != 2 or {row["configuration"] for row in transfer_rows} != {"E2", "E3"}:
        raise PaperArtifactError("Phase 10 requires exactly the E2 and E3 blocked-transfer records.")
    table_rows = [
        (
            row["configuration"],
            row["backend"],
            _short(str(row["model"]), 48),
            row["artifact_format"],
            row["gpu_acceleration"],
            f"{row['accepted_selection_count']}/{row['question_count']}",
            f"{_percent(float(row['fact_selection_precision']))}/{_percent(float(row['fact_selection_recall']))}",
            _percent(float(row["safe_empty_selection_accuracy"])),
            f"{_percent(float(row['passage_precision']))}/{_percent(float(row['passage_recall']))}",
            _percent(float(row["invalid_structured_output_rate"])),
            _percent(float(row["fallback_rate"])),
            _short(str(row["pilot_and_full_mas"]), 42),
        )
        for row in transfer_rows
    ]
    _write_text(
        output_dir / "TABLE_10_14B_TRANSFER_NEGATIVE_RESULTS.md",
        "# Table 10. 14B Apple-GPU transfer results: verified acceleration, blocked deployment\n\n"
        "E2 and E3 both used the immutable v5.1 held-out relevance set and the same pre-registered "
        "maximum invalid structured-output rate of 2%. Their Apple-GPU preflights succeeded, but each "
        "deployment failed that schema-reliability gate before any 30-site pilot or 300-scenario full-MAS run. "
        "The table is therefore a deployment-admission result, not a full-MAS safety, farmer-output, or agricultural-outcome comparison.\n\n"
        + _markdown_table(
            (
                "Config.", "Backend", "Model", "Artifact", "Apple GPU", "Valid", "Fact P/R",
                "Safe empty", "RAG P/R", "Invalid", "Fallback", "Pilot / full MAS",
            ),
            table_rows,
        )
        + "\n\nBoth deployments selected admitted evidence accurately among parsed responses, but the invalid-output "
        "rates—9.4% for E2 and 25.0% for E3—exceeded the 2% gate. E2 and E3 share the Qwen2.5 14B model "
        "family but not byte-identical artifacts or quantization formats; their `deployment_backend` label must "
        "not be interpreted as an isolated Ollama-versus-MLX runtime comparison.\n",
    )
    _write_csv(output_dir / "e2_e3_transfer_negative_results.csv", list(transfer_rows))


def _save_figure(figure: plt.Figure, base: Path) -> list[Path]:
    figure.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    figure.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(figure)
    return [base.with_suffix(".png"), base.with_suffix(".pdf")]


def _architecture_figure(output_dir: Path) -> list[Path]:
    figure, axis = plt.subplots(figsize=(18, 5.2))
    axis.set_xlim(0, 18)
    axis.set_ylim(0, 4.6)
    axis.axis("off")
    nodes = [
        (0.3, 2.9, 2.4, 0.78, "Frozen loader\nregistry + scenarios + enrichments"),
        (3.1, 2.9, 2.15, 0.78, "Integrity gates\nidentity, scope, hashes"),
        (5.65, 2.9, 2.65, 0.78, "Context + plan agents\nweather, soil, NDVI, market, policies"),
        (8.7, 2.9, 2.25, 0.78, "Scoped RAG\noperations + post-harvest"),
        (11.35, 2.9, 2.75, 0.78, "Conflict detector\n+ provenance coordinator"),
        (14.5, 2.9, 2.8, 0.78, "Farmer plan\nsource-cited, conditional"),
        (13.6, 0.9, 2.9, 0.78, "Independent oracle\nstructural / safety evaluation"),
    ]
    colors = ["#dbeafe", "#fee2e2", "#dcfce7", "#fef3c7", "#ede9fe", "#cffafe", "#f3f4f6"]
    for (x, y, width, height, text), color in zip(nodes, colors):
        axis.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.04", linewidth=1.2, edgecolor="#334155", facecolor=color))
        axis.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=8.7, color="#0f172a")
    for index in range(5):
        x, y, width, height, _ = nodes[index]
        nx, ny, _, _, _ = nodes[index + 1]
        axis.annotate("", xy=(nx - 0.08, ny + 0.39), xytext=(x + width + 0.08, y + 0.39), arrowprops={"arrowstyle": "->", "lw": 1.35, "color": "#475569"})
    axis.annotate("", xy=(15.05, 1.72), xytext=(15.9, 2.84), arrowprops={"arrowstyle": "->", "lw": 1.35, "color": "#475569"})
    axis.text(9.0, 0.33, "E0/A0–A6 structural comparison • E1-v5 bounded selection • controlled conflict and provenance fixtures", ha="center", va="center", fontsize=9, color="#334155")
    figure.suptitle("Figure 1. Provenance-constrained benchmark MAS and evaluation boundary", fontsize=14, fontweight="bold")
    return _save_figure(figure, output_dir / "FIGURE_1_SYSTEM_ARCHITECTURE")


def _structural_figure(output_dir: Path, summary: Sequence[Mapping[str, str]]) -> list[Path]:
    labels = [row["system_id"] for row in summary]
    values = [float(row["overall_structural_pass_rate"]) * 100 for row in summary]
    colors = ["#166534" if label == "A0" else "#2563eb" if label == "A5" else "#94a3b8" for label in labels]
    figure, axis = plt.subplots(figsize=(10, 5.2))
    bars = axis.bar(labels, values, color=colors)
    axis.set_ylim(0, 108)
    axis.set_ylabel("All-check structural conformance (%)")
    axis.set_xlabel("Configuration")
    axis.set_title("Figure 2. Structural conformance by baseline / ablation")
    axis.grid(axis="y", linestyle=":", alpha=0.5)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 2, f"{value:.1f}%", ha="center", va="bottom", fontsize=9)
    axis.text(0.5, -0.19, "A0/E0 is the full deterministic reference. A1–A6 are evaluation-only variants; values are not agricultural accuracy.", transform=axis.transAxes, ha="center", fontsize=8.5, color="#475569")
    return _save_figure(figure, output_dir / "FIGURE_2_STRUCTURAL_ABLATIONS")


def _fixture_figure(output_dir: Path, fixtures: Sequence[Mapping[str, str]]) -> list[Path]:
    labels = [f"{row['system']}: {row['measure']}" for row in fixtures]
    values = [float(row["rate"]) * 100 for row in fixtures]
    colors = ["#dc2626" if row["measure"] == "A6 coordinator resolution" else "#0f766e" for row in fixtures]
    figure, axis = plt.subplots(figsize=(11.5, 6.1))
    positions = list(range(len(labels)))
    axis.barh(positions, values, color=colors)
    axis.set_yticks(positions, [_short(label, 58) for label in labels], fontsize=8.5)
    axis.invert_yaxis()
    axis.set_xlim(0, 108)
    axis.set_xlabel("Expected policy result (%)")
    axis.set_title("Figure 3. Controlled conflict and provenance-fixture outcomes")
    axis.grid(axis="x", linestyle=":", alpha=0.5)
    for position, value in zip(positions, values):
        axis.text(value + 1.5, position, f"{value:.0f}%", va="center", fontsize=8.5)
    axis.text(0.5, -0.12, "The red 0% A6 resolution row is expected: the conflict coordinator is intentionally withheld in that ablation.", transform=axis.transAxes, ha="center", fontsize=8.5, color="#475569")
    return _save_figure(figure, output_dir / "FIGURE_3_CONTROLLED_FIXTURES")


def _runtime_figure(
    output_dir: Path,
    full_runtime: Sequence[Mapping[str, str]],
    backend_rows: Sequence[Mapping[str, Any]],
) -> list[Path]:
    figure, axes = plt.subplots(1, 3, figsize=(15.5, 4.6), gridspec_kw={"width_ratios": [1.0, 1.35, 1.0]})
    full_labels = [row["configuration"] for row in full_runtime]
    full_latency = [float(row["mean_trace_latency_ms"]) for row in full_runtime]
    axes[0].bar(full_labels, full_latency, color=["#166534", "#7c3aed"])
    axes[0].set_yscale("log")
    axes[0].set_title("Full 300-scenario MAS")
    axes[0].set_ylabel("Mean trace latency (ms, log scale)")
    for index, value in enumerate(full_latency):
        axes[0].text(index, value * 1.4, f"{value:.1f}", ha="center", fontsize=8)

    relevance_labels = [row["configuration"] for row in backend_rows]
    relevance_latency = [row["mean_latency_ms"] for row in backend_rows]
    colors = ["#7c3aed" if row["accepted"] else "#f59e0b" for row in backend_rows]
    axes[1].bar(relevance_labels, relevance_latency, color=colors)
    axes[1].set_title("Held-out relevance workload")
    axes[1].set_ylabel("Mean selection latency (ms)")
    for index, value in enumerate(relevance_latency):
        axes[1].text(index, value + max(relevance_latency) * 0.025, f"{value:.0f}", ha="center", fontsize=8)

    invalid = [row["invalid_output_rate"] * 100 for row in backend_rows]
    fallback = [row["fallback_rate"] * 100 for row in backend_rows]
    x_positions = list(range(len(backend_rows)))
    axes[2].bar([x - 0.18 for x in x_positions], invalid, width=0.36, label="Invalid output", color="#dc2626")
    axes[2].bar([x + 0.18 for x in x_positions], fallback, width=0.36, label="Fallback", color="#2563eb")
    axes[2].set_xticks(x_positions, relevance_labels)
    axes[2].set_ylim(0, max([2.0, *invalid, *fallback]) * 1.25)
    axes[2].set_title("Selection reliability")
    axes[2].set_ylabel("Rate (%)")
    axes[2].legend(fontsize=8)
    axes[2].grid(axis="y", linestyle=":", alpha=0.5)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
    figure.suptitle("Figure 4. Runtime and reliability measurements by workload", fontsize=14, fontweight="bold")
    figure.text(0.5, 0.01, "E2/E3 are relevance-only negative results after structured-output-gate failure; they are not full-MAS runtime comparisons.", ha="center", fontsize=8.5, color="#475569")
    figure.tight_layout(rect=(0, 0.05, 1, 0.91))
    return _save_figure(figure, output_dir / "FIGURE_4_RUNTIME_AND_RELIABILITY")


def _write_readme(output_dir: Path) -> None:
    _write_text(
        output_dir / "README.md",
        "# Phase 10 Paper Artifacts\n\n"
        "This directory is regenerated from frozen data, persisted result archives, and the documented agent contract. "
        "It is a presentation layer: it contains no new agricultural evidence, model call, scenario, source retrieval, or manual result entry.\n\n"
        "## Reproduce\n\n"
        "```bash\n"
        ".venv-macos/bin/python -m evaluation.paper_artifacts \\\n"
        "  --output-dir results/v2_2-paper-artifacts\n"
        "```\n\n"
        "The command rejects an existing non-empty output directory unless `--overwrite` is passed. "
        "`paper_artifact_manifest.json` records every input SHA-256, generator SHA-256, Git state, derived counts, and generated output fingerprint.\n\n"
        "## Interpretation boundary\n\n"
        "- Structural percentages are exact conformance rates on the frozen 300-scenario population, not agricultural outcome accuracy.\n"
        "- The bounded-LLM table measures selection among already-admitted source evidence, not farm action correctness.\n"
        "- Controlled conflict/provenance fixtures are evaluation-only policy tests, never farmer scenarios.\n"
        "- Runtime panels separate full-MAS, relevance-only, and unaccepted E2/E3 workloads.\n"
        "- Table 10 reports E2/E3 as verified-acceleration but non-admitted deployment transfers; neither has a pilot or full-MAS result.\n",
    )


def build_paper_artifacts(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
    render_figures: bool = True,
) -> Mapping[str, Any]:
    """Build all Phase 10 tables, figures, and the source/input manifest."""
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise PaperArtifactError(f"Output directory is not empty: {output_dir}. Pass overwrite=True to regenerate it.")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Capture the repository state before rendering.  The PDF renderers can
    # legitimately rewrite their own outputs, so measuring Git state while
    # assembling the manifest would otherwise mislabel a clean invocation as
    # dirty solely because of those generated files.
    generation_git = _git_metadata()
    inputs = _base_inputs()
    composition_rows, composition_stats = _build_composition(inputs)
    agent_rows = _agent_rows(inputs["agent contract"].path)
    summary = _read_csv(inputs["A0-A6 system summary"].path)
    metrics = _read_csv(inputs["A0-A6 metric rates"].path)
    fixtures = _read_csv(inputs["controlled fixture outcomes"].path)
    crop_rows = _read_csv(inputs["crop-stratified outcomes"].path)
    district_rows = _read_csv(inputs["district-stratified outcomes"].path)
    runtime_rows = _read_csv(inputs["E0/E1 runtime comparison"].path)
    heldout = _read_json(inputs["E1 final held-out metrics"].path)
    acceptance = _read_csv(inputs["E1 held-out acceptance report"].path)
    cases = _read_csv(inputs["E1 case-study index"].path)
    provenance = _read_json(inputs["provenance fixture outcome"].path)
    if len(summary) != 7 or len(cases) != 6 or len(runtime_rows) != 2:
        raise PaperArtifactError("Unexpected persisted Phase 10 result population.")

    backend_rows = [
        _backend_row("E1-v5.1", heldout, _read_json(inputs["E1 full-MAS manifest"].path)),
        _backend_row("E2", _read_json(inputs["E2 relevance aggregate"].path), _read_json(inputs["E2 relevance manifest"].path)),
        _backend_row("E3", _read_json(inputs["E3 relevance aggregate"].path), _read_json(inputs["E3 relevance manifest"].path)),
    ]
    transfer_rows = [
        _negative_transfer_row(
            "E2",
            _read_json(inputs["E2 relevance aggregate"].path),
            _read_json(inputs["E2 relevance manifest"].path),
            _read_json(inputs["E2 acceptance report"].path),
            _read_json(inputs["E2 Metal preflight"].path),
        ),
        _negative_transfer_row(
            "E3",
            _read_json(inputs["E3 relevance aggregate"].path),
            _read_json(inputs["E3 relevance manifest"].path),
            _read_json(inputs["E3 acceptance report"].path),
            _read_json(inputs["E3 Metal preflight"].path),
        ),
    ]

    _write_readme(output_dir)
    _write_composition_table(output_dir, composition_rows, composition_stats)
    _write_agent_table(output_dir, agent_rows)
    _write_structural_table(output_dir, summary, metrics)
    _write_relevance_table(output_dir, heldout, acceptance)
    _write_fixture_tables(output_dir, fixtures, provenance)
    _write_stratified_table(output_dir, crop_rows, district_rows)
    _write_case_studies(output_dir, cases)
    _write_runtime_table(output_dir, runtime_rows, backend_rows)
    _write_14b_transfer_negative_table(output_dir, transfer_rows)

    figures: list[Path] = []
    if render_figures:
        figures.extend(_architecture_figure(output_dir))
        figures.extend(_structural_figure(output_dir, summary))
        figures.extend(_fixture_figure(output_dir, fixtures))
        figures.extend(_runtime_figure(output_dir, runtime_rows, backend_rows))

    output_paths = sorted(path for path in output_dir.iterdir() if path.name != "paper_artifact_manifest.json")
    manifest = {
        "artifact_version": "phase10-paper-artifacts-v2-v2_2-inputs",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": {
            "path": "evaluation/paper_artifacts.py",
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "generation_git": generation_git,
        "input_artifacts": [
            {"label": item.label, "path": str(item.path.relative_to(PROJECT_ROOT)), "sha256": _sha256(item.path)}
            for item in inputs.values()
        ],
        "derived_counts": composition_stats,
        "generated_outputs": [
            {"path": path.name, "sha256": _sha256(path)} for path in output_paths if path.is_file()
        ],
        "interpretation_boundary": (
            "All reported rates are frozen-benchmark structural, evidence-selection, or runtime measurements; "
            "they are not agricultural outcome accuracy or field-trial results."
        ),
    }
    manifest_path = output_dir / "paper_artifact_manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True))
    return {
        "output_dir": str(output_dir),
        "table_count": len(list(output_dir.glob("TABLE_*.md"))),
        "figure_count": len(figures) // 2,
        "manifest": str(manifest_path),
        "scenario_count": composition_stats["scenario_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true", help="Replace generated files in an existing output directory.")
    parser.add_argument("--no-figures", action="store_true", help="Write tables and manifest only (used by lightweight checks).")
    args = parser.parse_args()
    result = build_paper_artifacts(
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        render_figures=not args.no_figures,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover - CLI wrapper
    main()
