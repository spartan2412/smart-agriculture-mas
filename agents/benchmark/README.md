# Benchmark MAS agents

This package is the provenance-constrained MAS path for the frozen six-crop
benchmark scenarios. It is separate from the legacy `agents/`
implementation and accepts only a validated `FrozenBenchmarkScenario`.

Every runtime role has its own module so that its evidence scope, safety rule,
and tests can be reviewed independently. Shared immutable contracts and helper
functions belong only in `base.py`.

| Layer | Agent modules |
|---|---|
| Integrity gates | `scenario_evidence_router.py`, `crop_district_season_alignment_validator.py`, `metadata_gate.py`, `evidence_provenance.py` |
| Restricted context | `weather_context.py`, `soil_context.py`, `satellite_ndvi_context.py`, `market_evidence.py`, `fertilizer_baseline.py`, `crop_protection_safety.py`, `vision_availability.py` |
| Official-operation path | `regional_calendar_operation_window.py`, `official_operations_rag.py`, `postharvest_storage_logistics.py`, `regulatory_compliance.py`, `action_feasibility.py` |
| Safety and coordination | `uncertainty_abstention.py`, `conflict_detection.py`, `provenance_aware_coordinator.py` |
| Output and evaluation | `farmer_explanation_citation.py`, `benchmark_evaluator.py` |

`graph/benchmark_workflow.py` composes these 21 agents. The gate agents run
first and fail closed. Context agents may run concurrently only after the gate
passes. The post-harvest role receives only crop-scoped conditional handling
records and collection-date infrastructure context; it cannot issue harvest,
storage, booking, dispatch, transport, or sell/hold instructions.

`conflict_resolution.py` is a deterministic coordinator policy component, not
a twenty-second agent. It resolves only same-domain/same-target claim records;
it is exercised by the separate 60-case
[`data/conflict_fixture_registry`](../../data/conflict_fixture_registry/)
through [`evaluation/conflict_fixture_runner.py`](../../evaluation/conflict_fixture_runner.py).
Those evaluation-only overlays are never loaded into a normal farmer-facing
workflow run.

The external `BenchmarkEvaluationOracle` is also outside the 21-agent graph.
After a normal run completes, it compares the resulting `BenchmarkRun` with
the same immutable `FrozenBenchmarkScenario` using 18 structural checks for
lineage, scope, retrieval, operation/condition fidelity, safety, conflict
handling, renderer fidelity, and bounded-LLM metadata. It cannot influence the
run. See [the evaluation policy](../../Documentation/EVALUATION_POLICY.md) and
[oracle evaluation guide](../../Documentation/ORACLE_EVALUATION_GUIDE.md).

The fixture runner also invokes the production alignment gate or raw-payload
hash verifier for its six integrity cases. It is therefore an evaluation
harness around production policy components, not a parallel recommendation
path. Its 30 provenance-precedence, 12 safety, 6 equal-tie, 6 integrity, and
6 unrelated-domain cases must remain separate from the 300 real benchmark
scenarios and from the 43 real NDVI--weather contextual divergences.

## Persisted architecture evaluation

The current A0–A6 comparison is outside this package's runtime path. It reads
saved batch/oracle artifacts and verifies common scenario IDs and frozen-input
hashes before computing exact structural rates: A0 300/300, A1 0/300, A2
0/300, A3 71/300, A4 0/300, A5 300/300, and A6 257/300. No module here was
changed or given extra authority for that report. A5's gate contribution is
assessed by the separate malformed-bundle fixture protocol rather than its
valid-input normal rate.

See [`results/architecture-comparison`](../../results/architecture-comparison/)
for the tables, figures, crop/district strata, fixture summaries, and source
artifact manifest. These outputs are structural-policy evidence only, not
farm-outcome accuracy.

### Why the A0 reference rate is 300/300

This rate is expected for the deterministic reference configuration, not a
claim that agriculture has been predicted perfectly. Before A0 runs, every
normal input has already passed the frozen scenario, enrichment, identity,
scope, and hash-admission checks. A0 then enables every production gate and
uses no LLM call. The separate downstream oracle verifies that the resulting
trace preserves all 18 source/provenance/safety/renderer invariants; it cannot
alter the workflow or make a passing trace pass. It is nevertheless not
independent farm-outcome ground truth, because its allowed facts and
restrictions are derived from the same frozen public-source contract.

The comparison is discriminative rather than hard-coded: known-bad traces
fail, removing scoped RAG/regional plans/conflict coordination changes normal
run outcomes, and malformed fixtures show A0 blocking 50/50 invalid bundles
while the intentionally gate-omitted A5 exposes all 50. Report the result as
**100% frozen structural evidence-and-safety conformance**, never as 100%
agricultural, crop, yield, irrigation, or farmer-outcome accuracy. See the
[full interpretation](../../Documentation/RESULTS.md#why-a0-obtains-300300-1000).

## Bounded LLM mode

When `BENCHMARK_LLM_ENABLED=true`, the workflow makes exactly eight bounded
LLM invocation attempts per scenario: Weather Context, Soil Context,
Satellite/NDVI Context, Market Evidence, Fertilizer Baseline, Official
Operations RAG, Provenance-Aware Coordinator, and Farmer
Explanation/Citation. The adapter is
[`llm/benchmark_llm_client.py`](../../llm/benchmark_llm_client.py).

The model receives only immutable, already-admitted fact IDs and may return a
validated subset of those IDs. Its accepted selection can prioritize
farmer-plan cards, re-rank already-admitted RAG passages, select optional
historical-context cards, and surface an approved fertilizer-policy boundary.
Each selection receives the frozen crop/location/season/date identity and the
farmer question for relevance only; both are untrusted data and cannot expand
the allowed facts or relax a gate. The post-harvest role is intentionally not a
ninth LLM call: it deterministically establishes the only admissible
post-harvest handling and infrastructure claims, while the bounded coordinator
may prioritize already-approved cards.
Each LLM-enabled agent owns its separate, versioned relevance prompt in its
own module through `llm_selection_instruction`; the full prompt objectives
and audit boundary are in
[`Documentation/AGENTS.md`](../../Documentation/AGENTS.md).
It cannot introduce prose, values, sources,
citations, action conditions, diagnoses, forecasts, doses, or recommendations.
The deterministic workflow retains sole authority over a claim's disposition,
allowed use, gate result, source citation, and action status. A failed optional
call is recorded as a safe fallback; set `BENCHMARK_LLM_REQUIRED=true` for an
experimental run that must stop when the selected backend is unavailable.

Offline/audit mode keeps `BENCHMARK_LLM_ENABLED=false`, so the same workflow
can run without a model during integrity tests.

## Completed bounded-LLM evidence

The final v5.1 selector was evaluated once on its disjoint 96-question
held-out set, then used unchanged in the 30-site pilot and full 300-scenario
E1-v5/A0 run. The held-out result was 98.6% fact precision/recall, 100%
safe-empty and exact RAG passage precision/recall, with zero invalid/fallback
events. The full runtime preserved 300/300 external-oracle passes, 2,400
accepted bounded selections, and zero direct farm actions. The Phase 7
comparison confirms that E0 and E1 share frozen inputs and that bounded
selection never alters decision status, operation text/status, citation set,
or direct-action flags. See
[`results/v2_2-phase7-controlled-comparison`](../../results/v2_2-phase7-controlled-comparison/).
