# Project Updates: Verified India Agriculture Benchmark and MAS

This is the concise chronological record of completed project milestones. It
does not duplicate source inventories, agent contracts, detailed methodology,
or full result tables; those remain in their canonical documentation.

## Current release state

| Component | Completed state | Canonical detail |
| --- | --- | --- |
| Registry and scenarios | 30 admitted crop--district--season sites; 300 aligned, source-gated historical scenarios | [Approach.md](Approach.md) and [DATA_SOURCES.md](DATA_SOURCES.md) |
| Enrichment layers | Four source-linked enrichments, including scoped RAG/operations, regional plans, and post-harvest context | [Approach.md](Approach.md) |
| Runtime | 21-agent, frozen-input, provenance-constrained MAS | [AGENTS.md](AGENTS.md) |
| Structural evaluation | 20-check Oracle (plus one derived all-check aggregate row), A0--A6 architecture comparisons, conflict and provenance fixtures | [ORACLE_EVALUATION_GUIDE.md](ORACLE_EVALUATION_GUIDE.md) and [RESULTS.md](RESULTS.md) |
| Bounded LLM | Accepted E1-v5 7B Apple-Metal configuration; E2/E3 14B transfers preserved as non-admitted negative results | [EXPERIMENT_RUNS_GUIDE.md](EXPERIMENT_RUNS_GUIDE.md) |
| Reproduction | E0/E1-v5 clean-checkout reproduction, plus final v2.2 E0 and two-fixture verification | [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md) and [`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/) |
| Release hygiene | Historical test references migrated to official v2.2/recoverable paths; full suite passes 193/193 without changing frozen evidence or results | [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md) |
| Paper presentation | Ten regenerated tables, four PNG/PDF figures, case studies, a dedicated E2/E3 negative-result table, and a source-hash manifest | [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/) |

## Milestone timeline

### 1. Aligned public-data registry and scenario benchmark

The project first froze a realistic India benchmark before adding agents or
recommendation logic:

- selected six crops—rice, wheat, maize, chickpea, soybean, and tomato;
- admitted 30 crop--district--season sites after crop, district, representative
  cropland-cell, weather, soil, Sentinel, market, and management-evidence
  gates passed; and
- generated 300 retrospective scenarios: 30 anchors plus 270 independently
  source-gated supplementary contexts.

No scenario mixes weather, soil, market, crop, location, or season evidence
from unrelated contexts. No raw farmer data, synthetic disease event, weather,
market, fertilizer, or crop-protection combination was added.

Canonical evidence and exact provider links: [DATA_SOURCES.md](DATA_SOURCES.md).

### 2. First enrichment: MAS-ready context and capability restrictions

The first enrichment made the frozen scenarios usable by bounded agents:

- historical NASA POWER water/weather context;
- quality-gated representative-cell satellite context;
- source-backed historical Agmarknet market context;
- regional management-policy references; and
- a per-scenario capability contract that records required abstentions and
  allowed uses.

This established the key distinction between regional/context evidence and
farm-specific authorization.

### 3. Second enrichment: official RAG, action bindings, and NDVI chronology

The second enrichment added the controlled knowledge layer:

- 92 admitted official documents and 4,582 provenance-carrying chunks;
- 27,600 scenario-to-source metadata-scope decisions before retrieval;
- 41 source-quoted operation records and 12,300 action-binding decisions;
- archived PAU and MPKV recovery only where original identity, time, crop,
  geography, source, hash, quote, and condition gates passed; and
- pre-decision NDVI chronology and advisory-discovery records.

Recovered operation passages remain outside the generic corpus and become
retrievable only after their own scenario binding passes.

### 4. Third enrichment: regional operation plans

The third enrichment turned already-admitted calendar, nutrient, IPM, and
operation material into useful scenario-bound plans:

- 1,507 source-linked regional plan items across all 300 scenarios;
- 607 conditional source-quoted operation plan items across 229 scenarios;
- regional calendar, nutrient-policy, and IPM-policy references for every
  scenario; and
- zero fabricated field conditions or direct farm actions.

This gives each scenario a grounded regional plan without relabelling public
guidance as a farm observation.

### 5. Fourth enrichment: post-harvest, storage, and logistics context

The fourth enrichment added crop-scoped handling and local infrastructure
context:

- 300 source-linked post-harvest contexts;
- 700 conditional handling plan items;
- 14 exact-crop handling passages available only through their exact-crop RAG
  scope; and
- collection-date facility, warehouse, state-infrastructure, and static-route
  context without capacity, booking, transport, commodity acceptance, or
  sell/hold claims.

### 6. Frozen benchmark MAS implementation

The research runtime was intentionally separated from the legacy prototype.
It now uses:

- the fail-closed `FrozenBenchmarkLoader`;
- typed provenance-carrying claims;
- 21 reviewable agent roles;
- metadata-filtered generic, operation, and post-harvest RAG paths;
- deterministic uncertainty, action-feasibility, and conflict policy; and
- farmer-facing source-cited regional-plan rendering.

The normal benchmark cannot issue an irrigation-now order, field-specific
fertilizer dose, diagnosis, chemical treatment, leaf-vision result, live
storage booking, dispatch instruction, or sell/hold recommendation.

Agent contracts and execution order: [AGENTS.md](AGENTS.md).

### 7. Stored provenance-conflict and integrity fixtures

Two evaluation-only fixture registries were added without changing any normal
scenario:

- 60 conflict fixtures test scope, time, provenance, safety precedence, equal
  tie deferral, integrity rejection, and unrelated-domain non-conflicts; and
- 60 provenance/alignment fixtures test mutated crop/district/season/date/
  binding evidence and raw-payload hash enforcement.

They are labelled in-memory test overlays, never historical farm observations
or normal farmer-facing inputs.

### 8. External oracle and deterministic architecture comparison

An independent read-only oracle was added after the coordinator. It checks
lineage, citation, scope, retrieval, operation/condition fidelity, plan
coverage, safety, abstention, agent permissions, conflict closure, and
bounded-LLM trace properties.

The completed deterministic comparison uses the same frozen 300 scenarios:

| Configuration | Result | Meaning |
| --- | ---: | --- |
| A0 / E0 full deterministic MAS | 300/300 structural passes | Complete system conforms to the frozen structural contract. |
| A1 regional-plan-only | 0/300 | Plan references alone lack the complete coordinated trace. |
| A2 centralized scoped RAG | 0/300 | Retrieval alone lacks the planning and typed-claim path. |
| A3 without scoped RAG/operations | 71/300 | Removing scoped recovery reduces complete operation/citation coverage. |
| A4 without regional plans | 0/300 | The third enrichment is necessary for complete grounded-plan coverage. |
| A5 without later alignment gate | 300/300 normal | Valid inputs conceal gate value; paired fixtures reveal it. |
| A6 without conflict coordination | 257/300 | The 43 natural NDVI--weather divergence traces lack required coordination. |

These are structural-contract results, not farm-outcome or agricultural
accuracy. Complete figures, formulas, and interpretation are in
[RESULTS.md](RESULTS.md).

### 9. Bounded-LLM development and final E1-v5 evaluation

The system did not fine-tune model weights. It refined role-specific prompts
and candidate packaging using a separate development set, then froze v5.1
before final testing.

- E1-v4 remains a historical diagnostic baseline.
- V5/V5.1 development ended after iteration 02.
- A new 96-question source-derived held-out set was frozen with no scenario or
  study-site overlap with previous relevance datasets.
- The accepted Qwen2.5 7B Ollama/Metal configuration achieved 98.6% fact
  precision/recall, 100.0% safe-empty accuracy, 100.0% exact RAG
  precision/recall, and 0% invalid output/fallback.
- The accepted E1-v5 runtime completed both its 30-site pilot and 300-scenario
  full MAS run with 300/300 structural passes and 2,400 accepted bounded
  selections.

These results measure selection of already-admitted evidence, not agricultural
knowledge or farm-action correctness. The locked protocol is
[BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

### 10. Optional 14B transfer experiments

E2 (Ollama/Metal 14B) and E3 (MLX-LM 14B) both completed hardware preflights,
but did not pass the frozen structured-output gate:

| Configuration | Accepted selections | Invalid structured-output rate | Outcome |
| --- | ---: | ---: | --- |
| E2 Ollama 14B | 87/96 | 9.375% | Not admitted to pilot/full MAS. |
| E3 MLX 14B | 72/96 | 25.0% | Not admitted to pilot/full MAS. |

The negative result is retained transparently. The artifacts are not
byte-identical, so this is a deployment-backend transfer comparison rather
than a pure runtime-only claim. Details: [PHASE8_14B_EXPERIMENTS.md](PHASE8_14B_EXPERIMENTS.md).

### 11. Phase 9 clean-checkout reproducibility

The accepted E0 and E1-v5 configurations were rerun from a clean committed
checkout without replacing their original archives. The recorded frozen hashes,
300 semantic traces, oracle results, farmer-decision evidence, fixture traces,
and E1's 2,400 bounded selections reproduced exactly under their defined
comparison rules.

Method and limitations: [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md).

### 12. Phase 10 reproducible paper-artifact package

The project now has a presentation layer generated only from the frozen data,
persisted result archives, and agent contract. It adds no scenario, source,
LLM call, or manually entered result:

- ten paper tables for benchmark composition, agent responsibility,
  structural comparison, held-out bounded-LLM relevance, conflict fixtures,
  provenance fixtures, strata, case studies, and runtime/backend context;
- four 300-dpi PNG/PDF figures for the system architecture, ablations,
  controlled fixtures, and appropriately separated runtime measurements;
- six saved normal farmer-plan cases, one per crop, and one explicit
  evaluation-only conflict-resolution case; and
- a manifest with every input and generated-output SHA-256 fingerprint.

The runtime panel keeps full-MAS, relevance-only, and non-admitted E2/E3
transfer workloads separate. The presentation package repeats the structural
and evidence-selection boundaries: its percentages are not agricultural
outcome accuracy.

The official v2.2 rendering, including the E2/E3 negative-result table, is at
[`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/).

### 13. Official v2.2 release freeze and historical-result archive

The final paper boundary was frozen as 19 versioned `v2_2-*` result archives.
[`OFFICIAL_V2_2_RELEASE_MANIFEST.json`](../results/v2_2-paper-artifacts/OFFICIAL_V2_2_RELEASE_MANIFEST.json)
records their 3,054-file evidence tree and SHA-256 fingerprint. Earlier
benchmark runs, development iterations, and legacy vision/silver-label outputs
were moved without deletion to
[`results/archive/2026-10-12-pre-v2_2`](../results/archive/2026-10-12-pre-v2_2/).
The final results documentation now records every percentage’s numerator,
denominator, persisted input data, and interpretation boundary; therefore no
structural rate is presented as agricultural outcome accuracy.

## Current project statement

The project is ready for paper preparation. It supports the following narrow
claim:

> On a frozen, public-data-only India benchmark, the proposed MAS preserves
> source-scoped regional planning, provenance, safety boundaries, controlled
> conflict coordination, and bounded local evidence selection across 300
> aligned scenarios.

It does not support farm-specific prescription, field outcome, yield, profit,
or farmer-adoption claims.

## Navigation

- [Documentation map](README.md)
- [Active future work](To-Do.md)
- [Technical methodology](Approach.md)
- [Guide-facing project overview](<Documents/Current Project Idea.md>)
- [Architecture rationale](<Documents/New Architecture Justification.md>)
- [Results](RESULTS.md)
