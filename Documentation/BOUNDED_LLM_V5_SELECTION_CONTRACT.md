# Bounded-LLM v5 Selection Contract

## Status and boundary

This is the frozen design contract for the v5 bounded selector. It is a new,
separate path from the hash-locked E1-v4 selector and does not alter the
existing E1-v4 benchmark, pilot, model result, or deterministic MAS workflow.

| Field | Value |
| --- | --- |
| Contract version | `v5.1-sufficiency-primary-selection-contract-2` |
| Prompt version | `bounded-selection-v5.1-sufficiency-primary-candidate-contract` |
| Candidate-packaging version | `v5.1-role-aware-candidate-packaging-2` |
| LLM authority | Rank or omit supplied IDs only |
| LLM authority over actions, gates, sources, conditions, citations | None |

The contract is based on the recorded E1-v4 error analysis. It is designed to
improve relevance selection, not to make a farm-specific action possible from
the frozen public evidence.

## Universal selection contract

Every v5 invocation applies these rules before ranking:

1. Assess **sufficiency for the exact requested decision** before topical
   relevance.
2. Respect each candidate's visible `allowed_use` and `does_not_establish`
   fields as hard limits.
3. Return `[]` if no candidate is sufficient; a source-backed contextual fact
   is not automatically an action authorization.
4. Return only listed, unique IDs within the deterministic policy limit.
5. Never create, combine, paraphrase, or relax a fact, source, condition,
   operation, field observation, action, dose, diagnosis, forecast, or gate.

When an exact question asks a candidate to authorize a farm action, the
candidate package carries an explicit deterministic request-sufficiency state.
If all supplied candidates are context-only, regional policy, or restrictions,
the state is `no_candidate_authorizes_requested_farm_action` and the model must
return `[]`. This does not inject a new fact or decide an action; it makes the
existing `allowed_use` boundary visible at the question level.

## Role-specific policy

| Role | V5 policy | Maximum selections |
| --- | --- | ---: |
| Weather, Soil, Satellite, Market | Sufficiency before context | 1 |
| Fertilizer Baseline | Mandatory field-dose boundary before regional policy | 2 |
| Official Operations RAG | One exact source-scoped or exact-crop passage | 1 |
| Provenance-Aware Coordinator | One primary approved plan card | 1 |
| Farmer Explanation/Citation | Optional context without action authority | 1 |

### Context roles

Historical weather, static SoilGrids, representative-cell NDVI, and historical
market information may be selected only as context. They must return `[]` when
the request asks them to authorize irrigation now, a field NPK dose, disease
diagnosis, a sell/hold forecast, or another farm-specific action.

### Fertilizer role

When nutrient scope or dosage is discussed, the documented field-dose boundary
has priority over the regional nutrient-policy reference. Calendar and crop
protection cards are omitted from the fertilizer candidate package unless the
request explicitly concerns those domains. If the exact request asks for both
the regional policy and field-dose restriction, both exact candidates must be
retained, with the boundary first.

### RAG role

Candidates show their admitted corpus layer. A matching
`source_scoped_operation` outranks generic related official text and the model
may choose only one operation/handling passage. Its recorded scope and
condition remain deterministic evidence; selection cannot remove them.

### Coordinator role

The package omits the decision trace. For ordinary planning questions it also
omits post-harvest cards. The LLM may prioritize one approved card; it cannot
choose a second lane, promote a conditional operation, or alter conflict
resolution.

### Farmer explanation role

Only optional approved context cards are eligible. They can change display
order, never the operation, citations, restriction, or direct-action status.

## Deterministic candidate packaging

The packager derives its fields only from the existing claim/passage/card:

- `candidate_kind` identifies an existing claim, plan, or admitted passage
  class;
- `selection_priority` expresses the contract's deterministic ordering;
- `allowed_use` mirrors the typed evidence scope; and
- `does_not_establish` carries the existing claim restriction or the fixed
  system boundary for an already-admitted plan/passage.

It may remove role-irrelevant candidate IDs from an LLM prompt, but it cannot
add an ID, source, or evidence record to the trace.

## Acceptance requirements before evaluation

V5 must pass regression tests proving that it returns safe empty selections,
keeps the fertilizer boundary, limits RAG/coordinator selection to one primary
candidate, rejects unknown IDs, and leaves all deterministic decisions and
sources unchanged. Its development results are not held-out findings. The
separate final 96-question held-out set is frozen with pre-registered
thresholds and runtime hashes. See
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

## Completed evaluation status

The held-out runner was first validated with deterministic mock outputs and
then used for its single permitted E1-v5 Ollama/Metal evaluation. It recorded
98.6% fact-selection precision and recall, 100.0% safe-empty accuracy, 100.0%
exact RAG-passage precision and recall, and 0.0% invalid structured outputs or
fallbacks. No v5.1 prompt, candidate packaging, source artifact, or agent
permission changed afterward.

The identical accepted runtime then completed a 30-site pilot and the full
300-scenario E1-v5/A0 run. The full run retained 300/300 structural-oracle
passes, made 2,400 accepted bounded selections, and issued no unsupported
direct farm action. These are bounded-evidence-selection and runtime results,
not agricultural outcome accuracy. The final comparison is in
[`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).
