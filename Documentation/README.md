# Documentation Map

This directory records the current provenance-constrained Smart Agriculture
MAS. Each topic has one canonical home. Other documents may provide a short
contextual summary, but should link here rather than reproduce detailed tables
or implementation history.

## Canonical documents

| Need | Canonical document | Purpose |
| --- | --- | --- |
| Guide-facing research overview | [Documents/Current Project Idea.md](<Documents/Current Project Idea.md>) | Problem, scope, novelty, high-level method, current evidence, and bounded research claim. |
| End-to-end technical methodology | [Approach.md](Approach.md) | How the registry, scenarios, enrichments, MAS, prompts, conflicts, and evaluation were constructed. |
| Architecture rationale | [Documents/New Architecture Justification.md](<Documents/New Architecture Justification.md>) | Why the frozen loader, agents, RAG paths, safety policy, and coordinator are architected as they are. |
| Agent interface reference | [AGENTS.md](AGENTS.md) | All 21 roles, inputs, outputs, execution order, handoffs, and runtime contracts. |
| Data/source provenance | [DATA_SOURCES.md](DATA_SOURCES.md) | Public providers, exact URLs, evidence restrictions, source inventories, and canonical artifact locations. |
| Evaluation claim policy | [EVALUATION_POLICY.md](EVALUATION_POLICY.md) | What the benchmark measures, permitted claims, prohibited claims, and result interpretation rules. |
| Oracle implementation/audit | [ORACLE_EVALUATION_GUIDE.md](ORACLE_EVALUATION_GUIDE.md) | The 20 structural checks, schemas, aggregation, formulas, and fixture protocols. |
| Frozen experiment boundary | [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md) | Hash-locked inputs, runtime contracts, configurations, and persisted-run requirements. |
| Experiment rationale | [EXPERIMENT_RUNS_GUIDE.md](EXPERIMENT_RUNS_GUIDE.md) | Why E0--E3 and A0--A6 exist and which comparisons are valid. |
| Experiment/archive decoder | [EXPERIMENT_CONFIGURATION_AND_ARCHIVE_GUIDE.md](EXPERIMENT_CONFIGURATION_AND_ARCHIVE_GUIDE.md) | Exact E0/A0--A6/E1--E3 meanings, official archive contents, result-file roles, and permitted interpretations. |
| Numerical results and figures | [RESULTS.md](RESULTS.md), [results index](../results/README.md), and [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/) | Canonical v2.2 results, formulas/denominators, regenerated paper tables, static figures, case studies, the 14B negative-result table, the official evidence-release manifest, and clear separation from the dated historical archive. |
| Bounded-LLM experiment lifecycle | [BOUNDED_LLM_RELEVANCE_BENCHMARK.md](BOUNDED_LLM_RELEVANCE_BENCHMARK.md), [BOUNDED_LLM_RELEVANCE_DEVELOPMENT_SET.md](BOUNDED_LLM_RELEVANCE_DEVELOPMENT_SET.md), [BOUNDED_LLM_V5_SELECTION_CONTRACT.md](BOUNDED_LLM_V5_SELECTION_CONTRACT.md), [BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md), and [E1_RELEVANCE_ERROR_ANALYSIS.md](E1_RELEVANCE_ERROR_ANALYSIS.md) | Historical baseline, development-only work, frozen selector contract, final held-out protocol, and error analysis. |
| Runtime and reproducibility records | [APPLE_GPU_PREFLIGHT.md](APPLE_GPU_PREFLIGHT.md), [PHASE8_14B_EXPERIMENTS.md](PHASE8_14B_EXPERIMENTS.md), and [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md) | Apple-GPU evidence, transparent 14B transfer outcomes, and clean-checkout reproduction. |
| Historical changelog | [UPDATES.md](UPDATES.md) | Concise chronological record of completed project milestones. |
| Active work plan | [To-Do.md](To-Do.md) | Only unfinished work and future extensions; not a second implementation history. |
| File inventory | [FILES_INFORMATION.md](FILES_INFORMATION.md) | Current versus legacy project files and folders. |
| Legacy/current boundary | [MAS_BASELINE_AUDIT.md](MAS_BASELINE_AUDIT.md) | Separation of the original prototype from the frozen research benchmark. |

## Anti-duplication rule

When a fact, metric, source, contract, or result belongs to a canonical
document above, later documentation should state only the minimum contextual
summary and link to that source of truth. This preserves auditability without
creating multiple competing versions of the same information.
