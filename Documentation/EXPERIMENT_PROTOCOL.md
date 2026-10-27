# Frozen Experiment Protocol

> **Phase 9 status:** complete. Clean E0/E1-v5 reproductions matched their
> frozen semantic trace and oracle boundaries. The final v2.2 release check
> additionally reproduced E0 and both fixture suites exactly, verified 57/57
> frozen artifacts, and refreshed exact E1 Metal evidence at
> [`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/).
> This note does not modify the hash-locked machine-readable protocol.
>
> **Phase 10 status:** complete. A read-only presentation generator produced
> paper tables, figures, source-traceable cases, and an explicit E2/E3
> negative-result table at
> [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/) without
> changing the protocol, inputs, runtime, or evaluation rules.

**Protocol version:** 1.1
**Status:** frozen normal-input protocol. The historical machine-readable
snapshot remains hash-locked; the official v2.2 release records the completed
E0, E1-v5, and A1–A6 runs with Oracle v1.4. The separate
provenance/alignment integrity-fixture protocol is evaluation-only and does
not alter the frozen 300-scenario population or the 20-check normal oracle.
**Machine-readable companion:** [`evaluation/experiment_protocol.json`](../evaluation/experiment_protocol.json)

## Purpose

This protocol fixes the research comparison rules before batch execution. It
prevents changing the population, evidence boundary, prompts, model settings,
baselines, oracle rules, or reported metrics after results are observed.

It applies only to the current provenance-constrained benchmark MAS. The
legacy prototype, caller-supplied demo data, proxy 22-crop data, and archived
vision experiment are outside this protocol and must not enter paper results.

## Frozen benchmark boundary

The machine-readable [`evaluation/experiment_protocol.json`](../evaluation/experiment_protocol.json)
is retained as the hash-locked pre-execution protocol snapshot consumed by
persisted runs. It is not rewritten to retrospectively label completed E1
experiments, because that would invalidate historical hash evidence. Current
completion status is recorded in this document and in the persisted Phase 7
comparison package. Its `1.1` version assertion is now aligned in
`tests/test_experiment_protocol.py`; the latest recorded complete suite passes
185/185 without modifying this hash-locked historical snapshot.

| Item | Fixed value |
| --- | --- |
| Normal evaluation population | 300 frozen, source-gated scenarios |
| Study sites | 30 verified crop × district × season sites |
| Crops | Rice, wheat, maize, chickpea, soybean, tomato |
| Runtime input | `FrozenBenchmarkLoader` only; no caller-supplied or live farm facts |
| Evidence layers | Registry, scenarios, and all four completed enrichments |
| Farm-specific direct action | Always forbidden in this public-data benchmark |
| Conflict evaluation | 60 stored, evaluation-only counterfactual fixtures |
| Integrity-boundary evaluation | 60 stored, evaluation-only provenance/alignment fixtures; separate from normal scenarios and conflict fixtures |
| Natural contextual divergence | 43 real NDVI–weather divergence records; never relabelled as farm-action conflicts |

The canonical hashes for the scenario identity, all four enrichment layers,
RAG/operation scope, oracle, workflow, and fixture manifest are in the
machine-readable protocol. The batch runner must recompute and match every
one before it runs a scenario. The existing loader additionally verifies
linked raw-source provenance and per-record hashes.

## Fixed oracle and safety policy

The independent `BenchmarkEvaluationOracle` remains downstream of the MAS.
The official v2.2 release uses Oracle v1.4 with the version 1.0 evaluation
contract. Every normal scenario run saves all 20 binary Oracle checks, an
aggregate result (which includes one derived all-check pass row), and the
72-row stratified result. The 60-fixture outcomes are reported separately.
The exact percentages use persisted count denominators—`passes / evaluated
records` for structural and fixture rates, and `TP/(TP+FP)` and `TP/(TP+FN)`
for held-out evidence-selection precision and recall. The final numerators,
denominators, and sources are in
[`RESULTS.md`](RESULTS.md#exact-metric-formulas-denominators-and-input-data).

These experiments may measure provenance, source scope, retrieval, condition
fidelity, action-binding compliance, safety, abstention, conflict-policy
handling, plan coverage, reproducibility, latency, memory, and bounded-LLM
selection quality. They must not claim field-action accuracy, irrigation
accuracy, fertilizer-dose accuracy, pesticide-treatment accuracy,
disease-diagnosis accuracy, yield impact, or calibration without outcome
labels.

## Fixed bounded-LLM boundary

The original 1.1 snapshot records the v4 bounded-LLM boundary. The completed
E1-v5 run uses its separately frozen v5.1 selection contract, prompt version,
and candidate packaging, documented in
[BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).
Both versions preserve the same authority restriction: only eight named roles
may call an LLM; temperature is `0.0`, output is bounded, and only
already-admitted fact IDs may be selected.

The LLM may rank or emphasize supplied fact IDs only. It cannot introduce a
fact, source, citation, condition, action, direct-action permission, gate
result, or conflict resolution. A model error or invalid structured response
must be retained as a visible fallback in the trace.

## Experiment configurations

| Run | Backend | Model | Purpose |
| --- | --- | --- | --- |
| E0 | None | Deterministic-only | Reference conformance and bounded-LLM control |
| E1 | Ollama with Metal | Installed Qwen 2.5 7B Instruct, Q4_K_M | Current local bounded-LLM baseline |
| E2 | Ollama with Metal | Qwen 2.5 14B Instruct | Model-capacity comparison |
| E3 | MLX-LM with Apple GPU | Qwen 2.5 14B Instruct | Deployment-runtime comparison with E2 |

E1 is bound to the installed Ollama model artifact recorded in the JSON
protocol. E0 and the deterministic architecture comparison are complete. The
versioned E1-v5 experiment subsequently completed its Apple-GPU preflight,
one-time held-out relevance evaluation, 30-site pilot, and full 300-scenario
MAS run. Those completion records are intentionally kept outside this
historical normal-input protocol snapshot; see
[EXPERIMENT_RUNS_GUIDE.md](EXPERIMENT_RUNS_GUIDE.md) and
[RESULTS.md](RESULTS.md).

E2 and E3 required a separate model-artifact binding before their transfer
evaluation. It records the base-model family, parameter count, quantization,
artifact hash, and generation settings. The completed binding has exactly E2
and E3 entries. Because its GGUF and MLX artifacts are not byte-identical,
the result is a **deployment-backend comparison**, not proof that runtime
alone caused a difference.

Both Apple-GPU preflights passed, but the frozen 96-question transfer gate
rejected E2 at 9.375% and E3 at 25.0% invalid structured output—above the
pre-registered 2% maximum. Neither configuration advanced to a 30-site pilot
or 300-scenario MAS run. See
[PHASE8_14B_EXPERIMENTS.md](PHASE8_14B_EXPERIMENTS.md) and
[EXPERIMENT_RUNS_GUIDE.md](EXPERIMENT_RUNS_GUIDE.md).

## Required architecture comparisons

Each comparison uses the same 300 scenarios, source boundary, loader, and
external oracle:

| ID | System | What it tests | Persisted normal result |
| --- | --- | --- | --- |
| A0 | Full deterministic MAS | Proposed farmer-facing reference architecture | 300/300 structural passes |
| A1 | Regional-operation-plan-only baseline | Value of coordinated multi-agent evidence handling | 0/300; evaluation-only |
| A2 | Centralized source-filtered RAG planner | Value of multi-agent decomposition | 0/300; evaluation-only |
| A3 | MAS without scoped RAG/operation retrieval | Value of official source-scoped retrieval | 71/300; evaluation-only |
| A4 | MAS without regional operation plans | Value of the third enrichment | 0/300; evaluation-only |
| A5 | MAS without provenance/alignment gates | Value of strict evidence boundaries | 300/300 valid inputs; controlled fixtures measure gate protection |
| A6 | MAS without conflict resolution | Value of deterministic conflict handling | 257/300; 43 natural divergence traces lose coordinator handling |

A1–A6 are implemented as offline research systems only. The runner requires
an explicit `--evaluation-only` flag for them, persists their oracle failures
for comparison, and never exposes them as a farmer-facing path.

The additional provenance/alignment fixture suite does not run through the
batch benchmark runner because it deliberately uses invalid in-memory bundles.
It records A0-versus-A5 gate behaviour in a separate harness, with 60/60
expected outcomes: 50 A0 alignment blocks, 50 A5 evaluation-boundary
exposures, and 10 shared loader hash blocks. It cannot affect E0 or any
normal-input architecture comparison.

The source-hash-validated comparison tables, crop/district strata, controlled
fixture summary, and 300-dpi figures are in
[`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/). They
are exact fixed-population structural results, not inferential tests or
agricultural outcome scores.

For the reader-facing explanation of why each E0–E3 and A0–A6 run was
necessary, exactly what changed, and what its result can establish, see
[EXPERIMENT_RUNS_GUIDE.md](EXPERIMENT_RUNS_GUIDE.md). This companion guide
does not alter the machine-readable historical protocol snapshot.

### Reference-rate interpretation

A0's 300/300 result is expected under this frozen protocol: all normal inputs
were admitted as valid before execution, the full architecture retains each
required gate, and E0 makes no LLM call. It means that all 20 trace invariants
held, not that agriculture is predictable with 100% accuracy. The independent
oracle is separate from the runtime graph and cannot modify its output, but it
derives expectations from the same frozen source/policy artifacts rather than
from field outcomes. Known-bad trace tests, component removals, and the
invalid-bundle A0/A5 fixtures demonstrate that the checks can fail and that
the result is not a hard-coded success path.

### Completed configuration-result interpretation

The completed A0–A6 results must be read as exact controlled architecture
comparisons, not as a leaderboard of agricultural effectiveness. A1's 0/300
means direct regional-plan rendering lacks the full coordinated
operation/condition/citation contract; A2's 0/300 means a source-filtered
central retriever lacks the regional-plan and typed multi-agent path; A3's
71/300 shows 229 traces lose required scoped-operation coverage when recovery
passages are withheld; and A4's 0/300 shows that removing regional plans
precludes complete grounded-plan coverage. A5's 300/300 normal rate is
expected because no normal row is malformed; only its 50/50 malformed-bundle
exposures measure the omitted gate. A6's 257/300 results solely from the 43
real contextual NDVI–weather divergences whose resolution trace is
deliberately withheld, while every retained safety property remains intact.

The controlled fixtures establish the matching causal boundaries: A0 resolves
60/60 stored policy cases; A6 detects 48/48 eligible coordinator cases but
resolves 0/48 by design; A0 blocks 50/50 identity/binding mutations; and the
shared loader blocks 10/10 raw-payload faults. See the complete explanation
in [`RESULTS.md`](RESULTS.md#why-each-configuration-obtained-its-result).

## Source-derived relevance benchmark

The source-derived relevance benchmark is now frozen at
[`data/llm_relevance_benchmark`](../data/llm_relevance_benchmark/): 96
questions, with 12 fixed questions for each of the eight bounded roles. It
uses two immutable anchor scenarios for each of the six focused crops. Every
record specifies its scenario ID, allowed source/document/passage/fact IDs,
expected plan or operation IDs where applicable, required conditions, and
same-scenario source-backed distractors. The manifest locks the question file,
input artifacts, and eight prompt-source hashes.

This benchmark measures selection precision/recall, top-k recall, plan-item
selection accuracy, invalid-output rate, fallback rate, latency, and memory.
It measures bounded evidence selection; it is not a farm-outcome benchmark.
The complete schema, integrity boundary, and future runner are documented in
[`BOUNDED_LLM_RELEVANCE_BENCHMARK.md`](BOUNDED_LLM_RELEVANCE_BENCHMARK.md).

### Final v5.1 held-out relevance protocol

The retained E1-v4 set is the original observed local-model baseline. It is
not the final quality estimate for v5.1. Development iterations 01 and 02 use
the separate observed 96-question development set and are permanently marked
development-only. No v5.1 prompt or candidate-packaging tuning is permitted
after iteration 02.

The final v5.1 relevance evaluation uses the immutable, hash-checked
[`data/llm_relevance_heldout`](../data/llm_relevance_heldout/) dataset:

| Boundary | Frozen value |
| --- | --- |
| Questions / roles | 96 total; 12 for each of the eight bounded roles |
| Evaluation contexts | 12 date-specific contexts at six study sites, two per crop |
| Earlier-set disjointness | No E1-v4 or v5-development scenario or study-site overlap |
| Candidate evidence | Only already-admitted, same-scenario, source-backed facts/passages |
| Safe-empty cases | 30, testing refusal to treat context as action authority |
| RAG cases | 12, each names one source-scoped operation and required condition |
| v5 binding | Runtime file hashes plus v5.1 selection-contract, prompt, and packaging versions |
| Final-use rule | One final model evaluation; no post-result v5.1 tuning |

Before that final run, acceptance requirements are fixed in
[`acceptance_criteria.json`](../data/llm_relevance_heldout/acceptance_criteria.json):
fact precision/recall and safe-empty accuracy each at least 80%; exact-passage
precision/recall each at least 75%; invalid structured-output and fallback
rates each at most 2%. A passing relevance run is followed—not replaced—by an
E1-v5 30-site MAS pilot that must retain 100% structural-oracle conformance
and zero structural regressions. These conditions measure selection quality
and bounded-runtime reliability, never agricultural outcome accuracy.

The final held-out runner must load the manifest and reject a changed
question file, criteria file, source artifact, v5 runtime artifact, or any
scenario/site overlap. Results must be persisted separately from all
development outputs and marked `final_heldout_evaluation`; a failure must be
reported rather than tuned against this set. The complete procedure is in
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

## Run order and acceptance gates

1. Confirm a clean committed protocol and verify all frozen hashes.
2. Build and validate the persistent batch runner. **Completed.**
3. Run E0 across 300 normal scenarios and save all oracle artifacts. **Completed at `e0c6d5a`: 300/300 full oracle passes.**
4. Run the 60 conflict fixtures once for that code commit. **Completed at `e0c6d5a`: 60/60 A0-policy passes.**
5. Before A6's 300-scenario ablation, run the same 60 fixtures with A6's coordinator-resolution input withheld. **Completed at `a1e6f21`:** 48/48 coordinator-required conflicts were detected, 0/48 resolved by design, and no direct action was issued.
6. Implement and run A0–A6 using the unchanged oracle. **Completed:** E0 passed 300/300; A1–A5 completed as explicit evaluation-only 300-scenario runs; A6 completed its normal and conflict-fixture ablation runs.
7. Freeze the source-derived relevance benchmark. **Completed:** 96
   source-derived questions (12 per bounded role) with manifest/source hashes;
   the earlier observed E1-v4 result remains historical only.
8. Freeze one anchor per 30 verified sites and verify Apple-GPU hardware
   preflight. **Completed for E1:** Ollama's configured Qwen2.5 7B Q4_K_M
   model was observed with non-zero GPU-resident memory; this is hardware
   proof only, not a 30-scenario result.
9. Preserve v5.1 development iteration 02, then run the immutable final
   v5.1 held-out relevance set exactly once with its pre-registered
   acceptance criteria. **Completed:** 96 questions passed all thresholds
   (98.6% fact precision/recall, 100% safe-empty and exact passage
   precision/recall, 0% invalid/fallback); no post-result v5.1 tuning is
   permitted.
10. Run the E1-v5 30-site Apple-GPU MAS pilot only after the held-out
    relevance result is persisted and reviewed. **Completed:** 30/30 external
    oracle passes; zero fallbacks, invalid outputs, safety regressions, or
    unsupported direct actions.
11. Bind E2/E3 model artifacts and apply the identical-artifact gate.
    **Completed:** backend-native artifacts were bound transparently. E2/E3
    cannot be called a runtime-only pair because the artifact bytes differ.
12. Run a configuration across all 300 scenarios only after its required
    relevance/pilot gates are satisfied. **E1-v5 completed:** 300/300 oracle
    passes, 2,400 accepted bounded selections, zero fallback/invalid events,
    and zero direct farm actions. **E2/E3 stopped correctly:** they failed the
    frozen structured-output transfer gate and are not eligible for pilots or
    full runs.
13. Produce comparative tables/figures and reproduce E0 from a clean checkout.
    **Comparison complete:** the read-only A0–A6 report validates the shared
    frozen population/hashes and writes six tables, crop/district supplements,
    three 300-dpi PNG/PDF figures, and a source-artifact manifest to
    [`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).
    **Phase 7 completed:** the final package also validates E0/E1 shared IDs,
    frozen data hashes, and oracle schema; reports held-out selection metrics
    and runtime behavior; and preserves six non-scored paired farmer-message
    examples. **Phase 9 completed:** clean-checkout E0/E1 reproductions and
    fixture checks are retained in the dated historical archive, with final
    v2.2 E0/fixture verification at
    [`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/).
    **Phase 10 completed:** a read-only generator now produces ten tables,
    four PNG/PDF figures, source-traceable cases, CSV summaries, an E2/E3
    transfer-negative-result table, and an input/output SHA-256 manifest at
    [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/). It creates no
    new experiment and does not modify this frozen protocol.

The pilot must confirm hardware acceleration, stable unified-memory use,
valid structured output, and recorded fallback behavior. A failed preflight
or hash mismatch invalidates that run rather than silently substituting data,
models, or settings.

## Required persisted artifacts

For every `scenario_id × configuration_id`, the runner must save the
`BenchmarkRun`, farmer message, trace, citations, retrieved-passage IDs,
operation bindings, conflict records, oracle result, and runtime measurements.
Each run manifest must include the clean Git commit, protocol hash, scenario
manifest hash, prompt hashes, backend, model artifact identity, quantization,
hardware details, Apple-GPU acceleration evidence, latency, peak memory,
invalid-output count, and fallback count.

## Interpretation rule

A high oracle pass rate means conformance with frozen evidence and safety
rules. It does not mean that a recommendation would succeed on an individual
farm. The paper must distinguish deterministic structural conformance,
controlled conflict-policy outcomes, and bounded-LLM relevance quality from
real-world agricultural outcome accuracy.
