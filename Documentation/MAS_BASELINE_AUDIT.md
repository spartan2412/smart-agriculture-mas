# MAS Baseline Audit — Foundation Phase

This audit records the legacy MAS baseline and the completed separate,
provenance-constrained benchmark path. The legacy system remains preserved as a
pilot baseline; the benchmark path does not alter its agents or LangGraph
workflow.

## Preserved baseline

| Component | Current role | Treatment during benchmark integration |
|---|---|---|
| `graph/workflow.py` | Legacy LangGraph flow for caller-supplied weather, soil, vision, irrigation, fertilizer, and market dictionaries | Preserve unchanged as the Current MAS baseline. |
| `agents/` | Existing pilot agents and coordinator | Preserve unchanged; new benchmark-safe roles live separately in `agents/benchmark/`. |
| `agents/base_agent.py` | Legacy `AgentEvidence` schema | Preserve for pilot/evaluation compatibility; do not overload it with benchmark provenance. |
| `data/loaders.py` | 22-crop proxy/Kaggle and generic market-CSV loaders | Preserve for the supplementary proxy experiment only. |
| `main.py` | Sample JSON and optional live Open-Meteo/SoilGrids/USDA-NASS CLI demo | Preserve as a demo; do not use it for frozen benchmark results. |
| `evaluation/` and `vision/` | Pilot evaluations and separate PlantVillage vision experiment | Preserve as baselines/separate experiments. |

## Baseline gaps found

1. The legacy graph accepts arbitrary caller-supplied dictionaries and has no
   `scenario_id` or source-provenance gate.
2. Legacy `AgentEvidence` has recommendation/confidence fields but no typed
   decision domain, source scope, temporal scope, allowed use, or block reason.
3. The legacy irrigation/fertilizer path expects moisture, N/P/K, and growth
   stage inputs that the frozen benchmark deliberately does not contain.
4. The legacy vision path can accept a leaf image, but the 300 scenarios have
   no aligned field image; benchmark vision must return `no_data`.
5. The legacy RAG content is unrestricted project-authored material. Benchmark
   RAG must use the metadata-filtered official 92-source corpus only.

## Foundation additions completed

- `data/benchmark_loader.py` now builds one immutable
  `FrozenBenchmarkScenario` from every runtime evidence layer: the final
  registry, scenario manifest/features/evidence status, all four enrichments,
  regional and post-harvest plan summaries/items/provenance, relevant
  recovered PAU/MPKV source inventories, and post-harvest source inventories.
- It checks the frozen benchmark boundary end to end: exactly 30 admitted
  crop–site combinations and 300 scenarios; site/scenario identity;
  source/action scope; and consistent identifiers and hashes across joined
  evidence records.
- It verifies the scenario's retained raw weather, market, and supplementary
  Sentinel payload hashes. Anchor Sentinel evidence is checked against the
  registry preflight record because those 30 anchors intentionally do not
  duplicate a scenario-level Sentinel raw payload.
- It exposes metadata-admitted official RAG chunks and source-scoped regional
  operation passages to benchmark agents. It also exposes post-harvest RAG
  passages only through their exact-crop scope decisions. The complete
  per-scenario RAG scope decisions remain available for audit; a recovery
  passage is available only after its action binding has already passed crop,
  geography, season, and source-time scope.
- It validates the fourth-enrichment crop/profile/item relationships, exact-crop
  post-harvest RAG scope, collection-date facility/warehouse candidate records,
  static routes, and all raw source hashes before any agent receives them.
- `data/evidence_schema.py` defines immutable, provenance-carrying claims for
  the new MAS path. Every claim carries its decision domain, disposition,
  permitted use, source citation, spatial and temporal scope, gate result, and
    structured metadata. A blocked, abstained, or no-data claim requires a
    machine-readable reason.

## Benchmark MAS implementation completed

- `agents/benchmark/` implements 21 roles: four integrity gates, seven
  restricted context agents, five official-operation agents (including the
  deterministic Post-Harvest Storage & Logistics agent), three
  safety/coordinator agents, and two explanation/evaluation agents.
- `graph/benchmark_workflow.py` wires those roles into a new LangGraph path
  that accepts only a frozen `scenario_id`. The seven independent context roles
  run concurrently, while the resulting trace remains deterministically ordered.
- The workflow exposes metadata-admitted RAG chunks plus scope-passed
  source-quoted crop-operation and exact-crop post-harvest passages. It carries
  source, scope, allowed-use, and block-reason fields through every typed claim.
- It was exercised across all 300 frozen scenarios: all traces include a
  conditional operation or post-harvest handling plan; 700 conditional
  post-harvest plan items retain their unobserved lot/harvest condition; and no
  direct farm action is issued.
- Natural cross-source conflict handling admits only the 43 explicitly eligible
  NDVI divergence candidates; ineligible/stale/insufficient observations do
  not create a manufactured conflict.
- Same-domain conflicts now carry stable claim IDs and are resolved in the
  coordinator by deterministic safety, admissibility, and provenance rules.
  Equal-precedence opposition is safely deferred; rejected/deferred claims do
  not enter the final decision or citation set.

## Foundation verification

| Check | Result |
|---|---|
| Structural runtime-bundle validation | 300/300 scenarios passed |
| Raw source-payload hash verification | 300/300 scenarios passed |
| Fourth-enrichment audit | 8/8 source, profile, scope, and infrastructure checks passed |
| Stored conflict-policy fixture execution | 60/60 expected policy outcomes passed; six integrity cases block before detector/coordinator execution |
| Stored provenance/alignment integrity fixture execution | 60/60 expected outcomes passed: A0 blocks 50 plan identity/binding mutations, A5 exposes 50 at its omitted-validator boundary, and the shared loader blocks 10 payload-hash mutations; zero direct actions |
| Source-derived oracle self-consistency audit | 300/300 normal traces passed all 20 structural checks; 72 frozen stratum rows reported |
| Persisted A0–A6 architecture comparison | Input IDs, frozen artifact hashes, and oracle schema validated before exact structural aggregation: A0 300/300, A1 0/300, A2 0/300, A3 71/300, A4 0/300, A5 300/300, A6 257/300 |
| Automated test suite | 193/193 passed in post-archive release-hygiene validation (42.04 seconds), including the read-only Phase 10 paper-artifact generator; historical comparison/held-out tests now resolve only official v2.2 or recoverable-archive paths, without changing frozen evidence |

The A0 300/300 result is expected for a valid, deterministic reference path:
normal bundles passed admission before being frozen and A0 retains every
runtime gate. It is not a field-accuracy score. The downstream oracle is
separate from the graph and cannot change its output, but its expectations are
source-contract invariants, not independent farm labels. Known-bad trace tests,
ablations, and controlled malformed-input fixtures establish that violations
are observable; notably, A0 blocks 50/50 alignment mutations whereas A5
exposes them only after its validator is intentionally omitted.

The remaining architecture results isolate equally specific contracts: A1's
0/300 retains regional references but removes coordinated operation handling;
A2's 0/300 retains scoped retrieval but removes the regional-plan/multi-agent
path; A3's 71/300 loses scoped-operation completeness for 229 records; A4's
0/300 removes complete regional-plan coverage; and A6's 257/300 withholds
resolution from 43 natural NDVI–weather contextual divergences while retaining
detection and safety. The 60 conflict fixtures and 60 provenance fixtures
establish the corresponding policy/gate causal boundaries. These figures are
not agricultural outcomes; see
[`RESULTS.md`](RESULTS.md#official-300-scenario-outcomes) for the
complete metric and fixture interpretation.
The experiment-purpose and comparison-boundary companion is
[`EXPERIMENT_RUNS_GUIDE.md`](EXPERIMENT_RUNS_GUIDE.md).

## Status boundary

The legacy graph and agents remain untouched, and no legacy recommendation
code is connected to the benchmark path. The new benchmark path retains
deterministic authority over all integrity, source-scope, feasibility, and
action decisions. When `BENCHMARK_LLM_ENABLED=true`, eight selected roles make
schema-constrained calls that may select only immutable approved fact IDs; they
can prioritize approved presentation/retrieval order, but cannot alter a gate,
source, citation, condition, or action status. The automated A0–A6
comparisons and controlled provenance fixtures are complete. E1's exact
Ollama E1-v5 has passed its Apple-GPU preflight, final v5.1 held-out relevance
evaluation, 30-scenario bounded-LLM pilot, and 300-scenario MAS run. Optional
E2/E3 14B deployments also passed runtime preflight but failed the frozen
relevance-transfer invalid-output gate; they did not advance to pilots. The
source-traceable case studies and paper-result presentation package are
complete at [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/).
The final v2.2 clean-commit verification is complete at
[`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/);
the earlier Phase 9 outputs are recoverable historical records.
The observed E1-v4 relevance fixture remains frozen at
[`data/llm_relevance_benchmark`](../data/llm_relevance_benchmark/), but it is
not the final v5.1 quality estimate. Development ended at v5.1 iteration 02,
and the separate final set at
[`data/llm_relevance_heldout`](../data/llm_relevance_heldout/) contains 96
source-derived questions, 12 per role, pre-registered thresholds, and no
scenario or study-site overlap with v4/development. Expert labels and vision
remain outside the active benchmark scope.

The eight bounded roles own their detailed relevance prompts in their
respective agent modules. The shared client supplies only universal constraints,
JSON validation, immutable-ID checking, frozen scenario/question relevance
context, and visible fallback. E1-v4 retains its own frozen prompt hash; the
current final path uses the separate v5.1 selection-contract, prompt, and
candidate-packaging hashes. The new post-harvest role remains deterministic:
it is the only authority that turns admissible post-harvest records into
conditional handling and collection-date infrastructure claims. The configured
benchmark backend is local Ollama with `qwen2.5:7b-instruct`; the completed
full model-enabled E1-v5 run made 2,400 local bounded calls rather than consuming a
cloud provider token quota. The separate 60-case conflict-fixture registry has
already validated deterministic conflict-policy outcomes through the
production detector/coordinator and integrity components. It is not loaded by
the legacy or benchmark workflow and is not a fifth enrichment. No further
model comparison or clean reproduction is pending within the current paper
boundary. The remaining work is paper writing and release audit, rather than
new scenario fabrication or post-held-out tuning.

The new external oracle in
[`evaluation/benchmark_oracle.py`](../evaluation/benchmark_oracle.py) evaluates
the completed benchmark trace against the frozen scenario bundle; it does not
alter the legacy baseline, the benchmark workflow, or a farmer-facing result.
Its contract-level checks and result schema are documented in
[`EVALUATION_POLICY.md`](EVALUATION_POLICY.md) and
[`ORACLE_EVALUATION_GUIDE.md`](ORACLE_EVALUATION_GUIDE.md). The current
in-memory audit verifies all 20 structural checks across 300/300 normal runs,
reports 72 immutable stratum rows, and separately verifies 60/60 controlled
conflict-fixture outcomes. The protocol-bound batch runner persisted E0 at
`e0c6d5a`: 300/300 normal traces and 60/60 fixture outcomes passed. A6 then
ran the same 60 fixtures at `a1e6f21`, detecting all 48
coordinator-required conflicts, resolving none by design, and issuing no
direct action. A1–A5 have also completed their 300-scenario evaluation-only
comparisons. The read-only
[`architecture comparison`](../results/v2_2-phase7-controlled-comparison/README.md)
validates their shared frozen population/hashes and generates paper tables,
figures, crop/district strata, and fixture summaries. The separate
provenance/alignment fixture runner supplies the
controlled evidence that A0 blocks malformed bundles while A5's omitted
validator exposes them; it never alters a normal scenario or batch result.

The final held-out runner and its mocked-response safety tests preceded the
one-time hash-checked v5.1 evaluation. The held-out result measures selection
quality only; the subsequently completed pilot and 300-scenario run verify
that bounded selection did not weaken the deterministic evidence-and-safety
boundary. No post-held-out prompt or candidate-package tuning occurred.

## Phase 7 completion status

The previously planned model-enabled evaluation is complete. The one-time
v5.1 held-out run passed its frozen acceptance thresholds (98.6% fact
precision/recall; 100% safe-empty and exact passage precision/recall; zero
fallback/invalid outputs). The accepted E1-v5 selector passed the 30-site
pilot and the full 300-scenario A0 run: 300/300 external-oracle passes, 2,400
accepted bounded selections, and zero unsupported direct farm actions.

The result does not change the legacy/current boundary in this audit. E0 and
E1 are both current benchmark workflows; the earlier `main.py` and legacy
agent graph remain excluded from paper comparisons. The read-only final
comparison package preserves this distinction, validates E0/E1 input parity,
and keeps six paired farmer-message examples explicitly non-scored:
[`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).

## Phase 9 completion status

The accepted benchmark is now also clean-checkout reproducible. Phase 9 did
not reconnect legacy code, change the benchmark graph, add an agent, or modify
the frozen E1-v5 prompt/candidate/source boundary. The new verifier compared
accepted and fresh semantic traces rather than raw telemetry: E0 matched all
300 scenario traces and both fixture suites; E1 matched all 300 scenario
traces and all 2,400 bounded selector records. Those earlier semantic results
are retained in the dated archive; the official v2.2 verification record is
[`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/).

## Phase 10 presentation status

Phase 10 added no runtime agent, evidence source, scenario, prompt, model
call, or legacy dependency. It reads the frozen benchmark inputs, saved result
archives, and the 21-agent contract to regenerate publication materials. The
ten tables, four PNG/PDF figures, six normal cases, one explicitly labelled
evaluation-only fixture case, and SHA-256 artifact manifest are in
[`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/). This improves result
traceability and presentation only; it does not change the legacy/current
boundary or establish agricultural outcome accuracy.
