# Smart Agriculture MAS — Active Research Work Plan

This is the **current and future-only** work plan for the research version of
the project. It intentionally does not repeat implementation history,
source inventories, agent contracts, or completed result tables.

The project is currently at the paper-writing and release stage. The frozen registry,
300 scenarios, four enrichments, provenance-constrained MAS, bounded-LLM
evaluation, architecture comparisons, fixture suites, and clean-checkout
reproduction are complete. Phase 10 also produced a source-traceable paper
artifact set: ten tables, four PNG/PDF figures, six normal farmer-plan cases,
one labelled fixture case, and a SHA-256 input/output manifest.

For the full history, see [UPDATES.md](UPDATES.md). For the implemented method,
see [Approach.md](Approach.md); for current results, see [RESULTS.md](RESULTS.md).

## Current frozen research boundary

| Item | Current status | Canonical record |
| --- | --- | --- |
| Benchmark population | Frozen: 300 source-gated retrospective scenarios across six crops and 30 study sites | [Approach.md](Approach.md) |
| Evidence layers | Frozen: registry, scenarios, four enrichments, scoped RAG, operation bindings, and post-harvest context | [DATA_SOURCES.md](DATA_SOURCES.md) |
| Proposed MAS | Complete: 21-agent provenance-constrained workflow with deterministic safety and conflict authority | [AGENTS.md](AGENTS.md) |
| Evaluation | Complete: external 20-check Oracle, A0--A6 comparisons, conflict fixtures, provenance fixtures, and stratified reports | [ORACLE_EVALUATION_GUIDE.md](ORACLE_EVALUATION_GUIDE.md) |
| Model-enabled configuration | Accepted E1-v5: bounded Qwen2.5 7B evidence selection on Apple Metal | [BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md) |
| Reproducibility | Complete: historical E0/E1 semantic reproduction plus final v2.2 clean-commit E0/fixture verification, 57/57 artifact hashes, and refreshed Metal evidence | [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md) |

## Active work: paper writing and release

The reproducible Phase 10 package is in
[`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/). It is the source for
the dataset, agent, structural, bounded-LLM, fixture, stratification, case,
and runtime presentation material. Its manifest records every consumed input
hash; use it rather than manually copying a result number.
The official-release boundary is fixed by
[`OFFICIAL_V2_2_RELEASE_MANIFEST.json`](../results/v2_2-paper-artifacts/OFFICIAL_V2_2_RELEASE_MANIFEST.json);
the [results index](../results/README.md) and dated
[archive](../results/archive/2026-10-12-pre-v2_2/) keep earlier generations
recoverable but out of the paper evidence set.

### 1. Write the paper with the correct research claim

- [ ] State the problem as provenance-safe, source-scoped regional decision
  support from aligned public evidence.
- [ ] Describe the novelty as the combined aligned benchmark, metadata-filtered
  RAG, operation bindings, typed claims, deterministic conflict coordination,
  and external structural oracle.
- [ ] Report exactly what each metric measures and the denominator/formula.
- [ ] State that E0/A0 300/300 is structural-contract conformance, **not**
  agricultural, irrigation, fertilizer, diagnosis, yield, profit, or farmer
  outcome accuracy.
- [ ] Report E2/E3 as transparent non-admitted transfer results; do not claim
  a larger-model or runtime advantage.

Permitted and prohibited claims: [EVALUATION_POLICY.md](EVALUATION_POLICY.md).

### 2. Package the reproducibility appendix

- [ ] Link the committed result archives, source registry, scenario manifests,
  enrichments, prompt/contract hashes, and environment records.
- [ ] Include the clean-checkout reproduction commands and equality criteria.
- [ ] State that timing and peak-RSS values are operational telemetry, not
  cross-machine equality criteria.
- [ ] Exclude credentials, `.env` values, and any local-only data.

Canonical reproducibility record: [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md).

### 3. Final audit before submission

- [ ] Verify that every paper number appears in a committed result artifact.
- [ ] Verify every public source citation against [DATA_SOURCES.md](DATA_SOURCES.md).
- [ ] Verify every architecture/agent statement against [AGENTS.md](AGENTS.md)
  or [Documents/New Architecture Justification.md](<Documents/New Architecture Justification.md>).
- [ ] Verify that all stated limitations are retained in the abstract,
  methodology, results, and conclusion.
- [ ] Run the project test suite and preserve the exact commit identifier used
  for the paper release.

## Future extensions — outside the current paper result

These are legitimate future projects, not missing benchmark requirements.

1. **Prospective shadow deployment.** Define a new decision-time protocol and
   collect time-valid forecast, farm-observation, and advisory evidence before
   making live claims.
2. **Farm-specific evidence integration.** Add measured soil moisture, soil
   tests, sowing/stage observations, diagnosed threshold events, and aligned
   leaf imagery through the same provenance and capability gates.
3. **Independent expert review.** Add agricultural-expert appropriateness
   labels under a separately frozen protocol.
4. **New model versions.** Any new LLM, prompt design, parser, or candidate
   packaging requires a separate development set, held-out protocol, pilot,
   and reproducibility record.

## Completed work reference

The following are complete and intentionally tracked elsewhere rather than as
tasks here:

- the 30/30 site registry and 300/300 aligned scenario benchmark;
- all four source-linked enrichments and recovered operation evidence;
- the 21-agent benchmark MAS and source-scoped RAG paths;
- conflict and provenance fixture registries;
- the external oracle, deterministic E0/A0--A6 comparisons, and E1-v5 runs;
- E2/E3 negative-result recording; and
- Phase 9 clean-checkout reproducibility verification.

See [UPDATES.md](UPDATES.md) for the chronological history and
[Approach.md](Approach.md) for the complete implementation pathway. The
earlier 22-crop proxy/silver-label and legacy-MAS context remains preserved in
[MAS_BASELINE_AUDIT.md](MAS_BASELINE_AUDIT.md); it is not part of the current
paper benchmark.
