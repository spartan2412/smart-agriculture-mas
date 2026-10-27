# Bounded-LLM Relevance Development Set

## Purpose

This is a source-derived **development-only** question set for improving the
bounded LLM evidence selector after the E1-v4 error audit. It is separate from
the original 96-question E1-v4 relevance benchmark and must never be reported
as a held-out model-quality result.

The set helps improve selector behavior while preserving the system's existing
evidence boundaries: the LLM can only select already-admitted source-backed
candidate IDs. It cannot add facts, citations, conditions, operations, or
farm-specific actions.

## Composition

| Item | Value |
| --- | ---: |
| Questions | 96 |
| Bounded roles | 8 |
| Questions per role | 12 |
| Development anchors | 12, two per focused crop |
| Focused crops | 6 |
| Controlled safe-empty questions | 30 |
| Candidate limit | 3 IDs |
| E1-v4 scenario overlap | 0 |

The 12 anchors are different from every scenario used by the E1-v4 relevance
benchmark. They retain real crop, state, district, season, date, source, RAG,
and operation alignment from the frozen 300-scenario study population.

## Targeted challenge families

| Role group | Development challenge |
| --- | --- |
| Weather, soil, satellite, market | Six safe-empty cases per role: topical context must not be selected when the requested irrigation, field-NPK, diagnosis, or sell/hold decision is unsupported. |
| Fertilizer baseline | The field-dose boundary is mandatory; calendar and crop-protection cards are source-backed distractors, not substitutes. |
| Official operations RAG | Select exactly one matching source-scoped/exact-crop passage and preserve its recorded condition; do not select a generic or neighbouring operation. |
| Provenance-aware coordinator | Select one specified primary regional plan card only. |
| Farmer explanation/citation | Optional context must not be used to authorize a farm-specific action. |

## Integrity boundary

The builder and loader reject the set if:

1. a question reuses an E1-v4 evaluation scenario;
2. any expected identifier is outside the question's source-backed candidates;
3. a candidate lacks source identity or a question lacks a required condition;
4. role coverage, question count, challenge coverage, or safe-empty count differs;
5. the question file or immutable evidence artifact hashes change.

Prompt and candidate-packaging code are intentionally recorded as builder
provenance rather than as immutable input hashes. They are the objects that
this development set is meant to improve. Frozen source evidence, labels, and
candidate IDs remain hash-checked.

## Usage sequence

1. Run prompt/candidate-packaging iterations only on this development set.
2. Preserve every prompt version, candidate-contract version, model artifact
   hash, and development result.
3. Do not claim these results as the final E1 result.
4. After selecting a final prompt version, create and freeze a separate,
   untouched held-out relevance test set.
5. Evaluate the final selector once on that held-out set, then rerun the
   30-site Apple-GPU pilot before any 300-scenario E1 run.

## Artifacts

- Question set: `data/llm_relevance_development/development_questions.jsonl`
- Manifest: `data/llm_relevance_development/manifest.json`
- Builder: `scripts/build_bounded_llm_relevance_development_set.py`
- V5 development runner: `evaluation/bounded_llm_relevance_v5_development.py`

## V5 development execution

### Freeze status

V5.1 development stopped after persisted iteration 02. Both development
outputs remain useful for diagnosing selector behavior, but neither is a
final research result and neither may be used for additional v5.1 tuning.
The final set is already built at
[`data/llm_relevance_heldout`](../data/llm_relevance_heldout/); it is
scenario/site-disjoint from this set and must be evaluated without further
prompt or candidate-packaging changes. See
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

The v5 runner uses the separate sufficiency-first v5 prompt and role-aware
candidate packaging contract. It reads the 96 immutable development questions,
keeps their original source-backed IDs and labels, and writes a new,
non-overwritable iteration directory. Every per-question record, aggregate,
and run manifest is marked:

```text
usage = development_only_not_heldout_evaluation
not_heldout_evaluation = true
final_research_result_permitted = false
```

Consequently, these outputs are useful for diagnosing prompt/candidate
packaging behavior, but must never appear as the final model-quality results
in the paper. The runner refuses any dataset whose manifest is not explicitly
development-only, and it refuses to overwrite a prior iteration.

After committing the runner, an Apple-Metal/Ollama development iteration can
be run as follows:

```bash
BENCHMARK_LLM_ENABLED=true \
LLM_BACKEND=ollama \
OLLAMA_MODEL=qwen2.5:7b-instruct \
.venv-macos/bin/python -m evaluation.bounded_llm_relevance_v5_development \
  --output-dir results/local-e1-v5-development-iteration-01 \
  --required
```

The command records selection precision/recall, safe-empty accuracy,
passage/operation-selection accuracy, invalid structured-output rate,
fallback rate, role-wise metrics, latency, prompt hashes, model configuration,
and the v5 contract identifiers. A clean Git worktree is required for a
persisted run.

### Plan/operation metric semantics

From v5 onward, plan/operation accuracy is projected from the expected and
selected **source-backed fact IDs**. A fertilizer field-dose boundary may be
the only correct answer to a safety question and deliberately contains no
regional-plan identifier; it is therefore excluded from plan/operation
accuracy rather than misgraded as a missing policy selection. The original
declared plan-ID field remains in each trace as legacy metadata.

For a previously persisted v5 development run, write a non-destructive metric
sidecar without making an LLM call:

```bash
.venv-macos/bin/python -m evaluation.bounded_llm_relevance_v5_development \
  --reanalyze-run results/archive/2026-10-12-pre-v2_2/development-history/e1-v5-development-iteration-02
```

To reproduce the creation into a new empty directory:

```bash
.venv-macos/bin/python scripts/build_bounded_llm_relevance_development_set.py \
  --output-dir /absolute/path/to/new-development-set
```

## Final-evaluation status

Iteration 02 remains development-only. After development froze, the separate
v5.1 held-out protocol was executed once and passed all registered thresholds;
the accepted selector then completed the 30-site pilot and full 300-scenario
E1-v5/A0 run. These final results are recorded in
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md) and
[`results/archive/2026-10-12-pre-v2_2/development-history`](../results/archive/2026-10-12-pre-v2_2/development-history/). The
official final comparison is separately recorded in
[`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).
Neither result authorizes further development-set tuning against the held-out
questions.
