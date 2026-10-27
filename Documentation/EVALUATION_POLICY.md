# Evaluation Policy and Evidence Boundaries

- **Policy document revision:** 1.4
- **Runtime policy-record version:** 1.0 (`evaluation/benchmark_contract.py`)

**Scope:** the frozen 300-scenario, public-data-only benchmark MAS.

This is the evaluation boundary for the current research system. It prevents
the paper from presenting structural evidence checks as farm-outcome accuracy.
The contract is mirrored in
[`evaluation/benchmark_contract.py`](../evaluation/benchmark_contract.py).

## What the benchmark can measure

The benchmark evaluates whether the MAS uses aligned, source-scoped evidence
correctly:

- frozen-loader and integrity-gate pass rate;
- citation coverage and traceability;
- abstention-reason coverage;
- unsupported-direct-action rate;
- operation-binding compliance;
- eligible conflict detection;
- conflict-resolution trace completeness;
- provenance-precedence compliance;
- safe deferral of equal-precedence opposition; and
- exclusion of rejected or deferred claims from the decision path.

The separately frozen bounded-LLM relevance benchmark measures only the
selection quality of the eight optional LLM roles. Its 96 source-derived
questions expose immutable candidate fact/passage IDs, expected IDs, required
conditions, and same-scenario distractors. It supports fact/passage
precision/recall, plan/operation selection, safe-empty selection,
invalid-output, fallback, latency, and memory measures. It cannot change a
runtime decision and does not supply farm-outcome labels. See
[`BOUNDED_LLM_RELEVANCE_BENCHMARK.md`](BOUNDED_LLM_RELEVANCE_BENCHMARK.md).

### Final v5.1 bounded-LLM relevance evaluation

The observed E1-v4 benchmark and the v5.1 development set are retained as
historical evidence only. v5.1 prompt and candidate-packaging changes stopped
after development iteration 02. The final quality measurement is the separate
immutable 96-question set in
[`data/llm_relevance_heldout`](../data/llm_relevance_heldout/), documented in
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

It contains 12 date-specific scenario contexts at six verified study sites
that are unused by **both** earlier question sets: two contexts for each of
the six focus crops. Every bounded role receives 12 questions. Its 30
safe-empty questions test correct refusal to select evidence that cannot
authorize the requested decision; its 12 RAG questions name one actual,
source-scoped operation and its recorded required condition. All candidates
and distractors are already-admitted source-backed facts from the same
scenario. The manifest locks question, acceptance-policy, evidence, and v5
runtime hashes and rejects scenario or site overlap with the earlier sets.

The following thresholds were registered before any final held-out model call:

| Measure | Required result |
| --- | ---: |
| Fact-selection precision / recall | at least 80% each |
| Safe-empty accuracy | at least 80% |
| Exact RAG-passage precision / recall | at least 75% each |
| Invalid structured-output rate | at most 2% |
| Fallback rate | at most 2% |
| Subsequent E1-v5 30-site MAS pilot | 30 traces, 100% structural-oracle pass rate, 0 structural regressions |

These are bounded evidence-selection and runtime-safety acceptance gates, not
farm-outcome targets. A held-out result must never be used to tune the v5.1
prompt, instructions, candidate packaging, labels, or thresholds. If a gate
fails, report that outcome, diagnose it on a **new** development dataset, and
freeze a separately versioned future protocol before any new final evaluation.

### How percentages are calculated

All reported percentages are computed from persisted, source-derived records;
they are not subjective ratings or manually assigned “accuracy” values. For a
normal-scenario Oracle check, the rate is
`passing scenario results / 300`. The complete structural rate is
`scenarios passing all 20 independent checks / 300`. For the frozen 96-question
held-out selector test, precision is `TP / (TP + FP)`, recall is
`TP / (TP + FN)`, safe-empty accuracy is `correct empty selections / 30`, and
exact plan/operation accuracy is `exact ID-set matches / 30 eligible
questions`. Invalid-output and fallback rates each use all 96 model responses
as their denominator. The exact inputs, count numerators, denominators, and
final values are recorded in
[`RESULTS.md`](RESULTS.md#exact-metric-formulas-denominators-and-input-data).

For a conflict, a result is valid only when the trace records the comparable
claim IDs, the decision target, the applied deterministic rule path, accepted,
rejected, downgraded, and deferred claim IDs, citations, and whether a direct
farm action remains allowed.

## Interpretation of a 100% A0 structural rate

The A0 result of 300/300 is a **deterministic contract-conformance result**.
It is expected when the complete architecture is run over the deliberately
valid frozen population: every normal record has already passed source,
identity, geographic/temporal scope, and raw-hash admission checks; A0 retains
all required runtime gates; and E0 invokes no LLM.

`BenchmarkEvaluationOracle` is independent of the runtime graph in the
important implementation sense: it is a downstream read-only evaluator with a
separate result schema and cannot alter claims, coordinator resolution, or the
farmer message. It is not independent agricultural ground truth: the expected
facts and restrictions are derived from the same frozen public sources and
policy contract. A 100% A0 rate therefore supports a claim of implementation
conformance, not real-world agricultural correctness.

This interpretation is tested rather than assumed. Deliberately bad traces
fail the oracle, A3/A4/A6 lose declared contract properties when their
components are removed, and the separate malformed-bundle fixture protocol
shows A0 blocking 50/50 alignment mutations. A5's 300/300 normal-input rate
does not weaken that conclusion: valid frozen inputs do not exercise the gate
it omits, so A5's 50/50 fixture exposures are the relevant comparison.

Permitted paper wording is: **“A0 achieved 100% conformance with the frozen
structural evidence-and-safety contract.”** Prohibited wording includes
“100% agricultural accuracy,” “perfect recommendations,” or any implication
of farm-level outcome accuracy.

## Interpretation of every completed architecture result

The architecture results are controlled **component-removal tests** over the
same already-admitted 300 scenarios. A1–A6 are evaluation-only; their score is
the number of scenarios that still meet the full A0 contract after a declared
capability is removed. A lower score is evidence of a missing contract
property, not a direct estimate of agricultural harm or farmer impact.

| System | Result | Policy interpretation |
| --- | ---: | --- |
| A0 full deterministic MAS | 300/300 | Complete evidence, planning, provenance, safety, and coordination path retains every required invariant. |
| A1 regional-plan-only | 0/300 | It renders regional references but deliberately lacks source-scoped operations and coordinated claim/condition/citation handling. |
| A2 centralized source-filtered RAG | 0/300 | Scoped retrieval remains safe, but retrieval alone does not instantiate the required regional plan or MAS trace. |
| A3 without scoped RAG/recovery | 71/300 | Withholding retrieved operation passages removes required conditional-operation/citation coverage for 229 records. |
| A4 without regional plans | 0/300 | Withholding plan items, bindings, and dependent policy roles removes complete grounded-plan coverage. |
| A5 without provenance/alignment gates | 300/300 normal | Equality on already-valid inputs is expected and says nothing about protection; A0 blocks 50/50 malformed bindings while A5 exposes 50/50 at its omitted-gate boundary. |
| A6 without conflict coordination | 257/300 | The 43 natural NDVI--weather contextual divergences retain detection but lose the required coordinator-resolution trace. |

The 60 conflict fixtures complement these normal-input results. A0 follows
the stored resolver policy in 60/60 cases; A6 deliberately detects all 48
coordinator-required conflicts but resolves 0/48 because the experiment
withholds them from its coordinator. The paired 60 provenance fixtures show
50 A0 alignment blocks, 50 A5 expected exposures, 10 shared raw-hash blocks,
and zero direct actions. These are policy-boundary results, not farm labels.
The complete metric-level explanation, including crop/district strata, is in
[`RESULTS.md`](RESULTS.md#official-300-scenario-outcomes).
The reason each E0–E3 and A0–A6 configuration was run, its controlled
difference, and its valid comparison boundary are in
[EXPERIMENT_RUNS_GUIDE.md](EXPERIMENT_RUNS_GUIDE.md).

## Resolution policy

Only claims about the same decision domain and declared target are comparable.
The coordinator resolves them deterministically in this order:

1. A source-scoped opposing safety restriction blocks the contested action.
2. Blocked, unavailable, abstained, and out-of-gate claims cannot win.
3. Remaining claims are ranked by recorded gate result, geographic specificity,
   temporal specificity, source provenance, claim disposition, and recorded
   confidence.
4. Equal-precedence opposing claims are safely deferred. A bounded LLM is not
   allowed to break that tie.

The existing natural NDVI--weather divergence cases are retained as
non-action contextual divergences. They are traceable but cannot be converted
into an operation or direct farm action.

## What the benchmark must not claim

The frozen public evidence has no farm-level outcomes, soil test, field
moisture, observed crop stage, disease diagnosis, aligned leaf image, or
farmer adoption/outcome labels. Therefore the paper must not report field
action accuracy, irrigation accuracy, fertilizer-dose accuracy, pesticide
treatment accuracy, disease-diagnosis accuracy, Brier score, or calibration
as results from this benchmark.

The stored 60-case counterfactual provenance-conflict fixture registry, the
separate 60-case provenance/alignment integrity-fixture registry, and the
persisted E0 300-scenario oracle audit implement the current resolver-policy,
integrity-boundary, and structural-conformance portions of this policy.
Architecture ablation results are evaluation-only evidence; they never become
farmer-facing systems.

## Stored counterfactual conflict-fixture protocol

The resolver-policy suite is stored in
[`data/conflict_fixture_registry`](../data/conflict_fixture_registry/). It is
a controlled evaluation layer, not a fifth agricultural enrichment and not a
source of farmer-facing evidence. Each fixture starts from one immutable real
scenario, then applies a labelled in-memory provenance, scope, time, safety,
or integrity overlay. No frozen scenario, enrichment, source artifact, or
normal workflow run is modified.

| Fixture family | Cases | Required result |
| --- | ---: | --- |
| Scope, time-validity, and provenance precedence | 30 | Retain the higher-precedence conditional claim and reject the weaker claim. |
| Safety restriction precedence | 12 | Retain the restriction and keep direct farm action blocked. |
| Equal-precedence opposition | 6 | Defer safely; do not choose a winner through confidence or an LLM. |
| Identity/hash integrity mutation | 6 | Fail closed before conflict detection or coordination. |
| Unrelated-domain negative control | 6 | Do not manufacture a weather-versus-market conflict. |

The suite uses the production `ConflictDetectionAgent`,
`ProvenanceAwareCoordinatorAgent`, alignment validator, and raw-payload
verifier. The runner records an eligible real NDVI--weather divergence on a
base scenario as background context; it never counts that divergence as the
fixture's controlled conflict.

Run it independently of a farmer-facing scenario run:

```bash
.venv-macos/bin/python - <<'PY'
from evaluation.conflict_fixture_runner import ConflictFixtureRunner

runs = ConflictFixtureRunner().run_all()
assert len(runs) == 60
assert all(run.expected_match for run in runs)
PY
```

The resulting measures are policy-compliance measures: they support claims
about deterministic conflict detection, precedence, safe deferral, rejection,
and integrity blocking. They do not measure agronomic correctness or a
real-world farm outcome.

### A6 conflict-resolution ablation

The same 60 fixtures are also run through A6 in explicit evaluation-only
mode. A6 retains the production detector and the fixture claims, but passes an
empty conflict set into the coordinator. Therefore, the expected result is
not 60/60 A0-policy compliance: all 48 coordinator-required fixtures remain
detected but unresolved, while the six integrity blocks and six negative
controls behave as before. The persisted ablation summary reports
both A6 expected-behavior conformance and the corresponding A0-policy match
rate. This makes the coordinator contribution measurable without treating an
intentional component removal as an ordinary system failure.

## Stored provenance/alignment integrity-fixture protocol

[`data/provenance_fixture_registry`](../data/provenance_fixture_registry/)
stores a second, separate set of 60 controlled single-fault fixtures. They
test the integrity boundary rather than conflict resolution. Each begins with
one immutable real scenario and alters exactly one in-memory plan identity,
plan binding, or raw-payload hash. The 300 scenarios and all source files are
never edited.

| Fault class | Cases | Expected A0 result | Expected A5 result |
| --- | ---: | --- | --- |
| Plan-item crop, district, season, decision-date, or scenario-binding mismatch | 50 | Block at the production alignment validator | Pass the deliberately omitted validator; halt immediately in evaluation-only mode |
| Weather raw-payload SHA-256 mismatch | 10 | Block at the shared loader verifier | Block at the same shared loader verifier |

The paired runner is deliberately not a normal workflow runner: it never sends
an invalid bundle to context agents, the coordinator, or the farmer renderer.
It measures the protective value of the alignment validator under controlled
invalid input while documenting that raw-payload verification is a loader
boundary shared by A0 and A5. The `EvidenceProvenanceAgent` remains an
auditable provenance summary rather than a second payload-hash gate.

The executed fixture result is 60/60 expected outcomes: A0 blocked 50/50
plan identity/binding mutations, A5 exposed 50/50 at its deliberately omitted
validator boundary, and both systems blocked 10/10 payload-hash mutations.
No fixture produced a direct farm action.

```bash
.venv-macos/bin/python -m evaluation.provenance_fixture_runner \
  --output-dir results/local-provenance-gate-fixtures
```

## Executable evaluation oracle

The source-derived contract is implemented by
[`evaluation/benchmark_oracle.py`](../evaluation/benchmark_oracle.py). It is a
read-only external evaluator, not a LangGraph agent or a recommendation path.
It produces a per-run result schema and aggregate metrics for:

- input lineage, stable claim identity, claim-scope contract, and citation traceability;
- metadata-scoped RAG compliance;
- operation-binding, missing-condition, and conditional-operation completeness;
- source quote/URL/hash/locator fidelity and plan-source citation coverage;
- grounded plan coverage and farmer-message condition/citation fidelity;
- unsupported-action and agent-permission compliance;
- abstention-reason coverage;
- conflict trace completeness, conflict-citation fidelity, and rejected-evidence exclusion; and
- natural NDVI--weather divergence policy and the no-image vision boundary;
- bounded-LLM trace compliance where optional LLM mode is enabled.

It also requires disaggregated reporting by frozen crop, geography, season,
scenario partition, operation availability, and divergence-eligibility strata.

The evaluator currently implements 20 binary structural checks, an
all-checks-per-scenario result, deterministic repeatability fingerprints,
72 immutable stratum rows for the audited 300-scenario population, and a
separate 60-fixture conflict-policy aggregate. The provenance/alignment
fixture registry has its own external oracle so the frozen 20-check normal
scenario oracle remains unchanged. The exact check-to-evidence mapping and
reproduction commands are intentionally kept in the companion guide rather
than duplicated here.

Its current implementation and reproduction commands are documented in
[`ORACLE_EVALUATION_GUIDE.md`](ORACLE_EVALUATION_GUIDE.md). The oracle has passed an
in-memory 300/300 self-consistency audit of the deterministic full MAS and
60/60 controlled fixture-policy outcomes. The persisted A0–A6 comparison now
applies this unchanged oracle to the same 300-scenario population and reports
exact structural results: A0 300/300, A1 0/300, A2 0/300, A3 71/300, A4 0/300,
A5 300/300, and A6 257/300. The separate fixture protocols show A0's 60/60
conflict-policy matches and its 50/50 alignment blocks, while A6 intentionally
resolves 0/48 coordinator-required fixture conflicts and A5 exposes 50/50
omitted-gate mutations only in evaluation mode.

These results establish comparative conformance to this contract and the
effect of removing declared components. They are not field-outcome accuracy,
agronomic effectiveness, or evidence that one farmer plan would outperform
another. See the immutable result artifacts in
[`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).
The Phase 10 package at
[`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/) re-expresses these
same persisted results for publication; it adds no metric, evidence, scenario,
or evaluator input.

## Completed E1-v5 model-enabled comparison boundary

Phase 7 completed the separate E1-v5 evaluation without changing the 300
scenarios, source register, enrichments, RAG corpus, action bindings, agent
permissions, v5.1 prompts, candidate packaging, or oracle. E0 and E1 used the
same ordered scenario IDs, shared frozen data hashes, and the same 20-check
oracle schema.

The final 96-question held-out set is the sole reported measure of bounded-LLM
selection quality: 98.6% fact precision/recall, 100% safe-empty accuracy,
100% exact RAG passage precision/recall, and 0% invalid-output/fallback rate.
The full model-enabled run reports only runtime/safety behavior: 300/300
structural-oracle passes, 2,400 accepted bounded selections, zero fallbacks,
zero invalid/rejected outputs, and zero direct farm actions. It does not
recompute relevance accuracy or establish agricultural outcome accuracy.

The E0/E1 message appendix is an unscored qualitative inspection of six
paired outputs. It cannot be reported as a human preference study, usefulness
score, expert assessment, or baseline truth. The reproducible package is
[`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).

## Phase 9 reproducibility policy result

Phase 9 validates repeatability, not a new performance metric. The current
reproduction rule is exact equality of source/hash-checked, normalized
semantic evidence: scenario identity, oracle checks/fingerprint, claims,
citations, retrieved passages, decisions, conflicts, farmer message, and—for
E1—the eight bounded role selection records. Wall-clock time, RSS, timestamps,
run-directory names, and commit IDs remain recorded but are not semantic
equality fields.

The earlier clean-checkout E0/E1 semantic comparison passed: E0 300/300
traces plus the 60 conflict and 60 provenance fixtures; E1 300/300 traces and
2,400 selections. It is recoverable historical supporting evidence. The final
v2.2 release separately reverified E0, both fixture suites, 57/57 frozen
artifacts, and E1 Metal evidence. These facts support a reproducibility claim
only; it remains invalid to call them farm-action or agricultural outcome
accuracy.
