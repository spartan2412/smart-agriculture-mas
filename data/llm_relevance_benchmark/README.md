# Frozen Bounded-LLM Relevance Benchmark

This directory is an evaluation-only layer for the eight optional
bounded-LLM roles. It contains no new agricultural observations, no farmer
answers, and no farm-outcome labels.

## Contents

- `relevance_questions.jsonl` — 96 fixed question records: 12 for each
  bounded role.
- `manifest.json` — question-file hash, source-artifact hashes, selected
  scenario IDs, prompt-template version, and label-policy metadata.

The 12 canonical scenarios are two immutable anchor contexts for each focused
crop: rice, wheat, maize, chickpea, soybean, and tomato. Each question binds
one role to one of those scenarios and contains its own scenario identity,
farmer question, source-backed candidate facts/passages, expected IDs,
conditions, and distractors.

## Label boundary

Every candidate is derived from one of the same scenario's admitted typed
claims, regional plan cards, source-scoped official operation passages,
exact-crop post-harvest passages, or deterministic decision trace. Every
candidate retains source-document identities. Distractors are other admitted,
source-backed candidates from that same scenario; they are not fabricated
negative examples.

The expected IDs measure relevance under the role's already-frozen prompt and
scope restrictions. A small set of questions deliberately expects an empty
selection when the question requests an unsupported farm-level inference, such
as irrigation-now, a field NPK dose, a disease diagnosis, or a sell/hold
forecast.

This benchmark therefore measures bounded fact/passage selection quality. It
does not measure crop yield, irrigation accuracy, fertilizer-dose accuracy,
pesticide effectiveness, disease diagnosis, profit, or farmer outcomes.

## Rebuild and validate

Run from the project root only when intentionally creating a new version of
this frozen evaluation set:

```bash
.venv-macos/bin/python scripts/build_bounded_llm_relevance_benchmark.py
```

The builder refuses to overwrite an existing populated directory. It verifies
raw scenario evidence through the normal frozen loader and writes source hashes
into the manifest. `load_relevance_benchmark()` verifies both the question-file
hash and all source-artifact hashes before a relevance run starts.

## Historical model evaluation

The observed E1-v4 run of this set is retained as a historical baseline. It
must not be rerun or used to tune the improved v5.1 selector. The final v5.1
evaluation is the separately frozen, scenario/site-disjoint set in
`data/llm_relevance_heldout/`; see
[`Documentation/BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](../../Documentation/BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

The original execution shape was:

```bash
.venv-macos/bin/python -m evaluation.bounded_llm_relevance \
  --output-dir results/e1-relevance-pilot
```

That command saved one selection trace per question plus aggregate fact,
passage, plan/operation, empty-selection, invalid-output, fallback, latency,
and memory measures. It cannot change a MAS gate, evidence source, citation,
condition, conflict resolution, or direct-action permission.
