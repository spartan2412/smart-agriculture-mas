# Experiment Runs: Purpose, Comparisons, and Interpretation

This guide explains why each experiment was run, what it changes, what it
contributes to the research evidence, and how its result may be interpreted.
It is the companion to the numerical report in [RESULTS.md](RESULTS.md), the
hash-locked normal-input protocol in
[EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md), and the final model-quality
protocol in [BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).
For a filesystem-level decoder of every E0/A0--A6/E1--E3 archive and the exact
meaning of the files it contains, see
[EXPERIMENT_CONFIGURATION_AND_ARCHIVE_GUIDE.md](EXPERIMENT_CONFIGURATION_AND_ARCHIVE_GUIDE.md).

The project has two deliberately different experiment families:

- **E-runs** vary the bounded-LLM/model/runtime configuration while retaining
  the admitted MAS evidence and safety boundary.
- **A-runs** are controlled architecture baselines and ablations. They remove
  one declared component from the deterministic system to test why that
  component is needed.

Neither family measures farm yield, irrigation accuracy, fertilizer-dose
accuracy, disease-diagnosis accuracy, or profit. The public-data benchmark has
no field-level outcome labels. The reported scores measure source alignment,
scope, provenance, condition preservation, bounded evidence selection,
conflict-policy behavior, and reproducibility.

## 1. Controls shared by the valid comparisons

The comparisons are meaningful because their evidence boundary is fixed.

| Controlled item | Fixed boundary |
| --- | --- |
| Normal population | The same 300 frozen, source-gated scenarios covering six crops and 30 crop–district–season study sites. |
| Inputs | Registry, scenario records, all four enrichments, regional operation plans, operation bindings, RAG permissions, and post-harvest context. |
| Admission | `FrozenBenchmarkLoader` rejects identity, crop, district, season, date, scope, link, and raw-source-hash mismatches. |
| Safety | Farm-specific irrigation, exact field NPK dose, diagnosis/treatment, vision result, and live logistics instruction remain unavailable for every normal scenario. |
| Structural evaluation | The same external 20-check `BenchmarkEvaluationOracle` evaluates normal MAS traces; its aggregate includes one derived all-check row. |
| Conflict and integrity evidence | Separate 60-case conflict-policy and 60-case provenance/alignment fixture suites; neither changes the 300 historical scenarios. |
| Persisted trace | Each accepted run stores its scenario identity, evidence claims, citations, retrieved passages, plan items, decision trace, farmer message, oracle result, and run manifest. |

The normal A0–A6 comparisons therefore ask one causal question: **what
contract property is lost when this one architecture capability is removed?**
They do not ask which system is a better agricultural adviser in real fields.

## 2. Reading an experiment identifier

| Identifier | Meaning | Farmer-facing status |
| --- | --- | --- |
| **E0** | Deterministic full-MAS execution with no LLM call. | Accepted reference configuration. |
| **E1-v5** | Accepted Apple-Metal local bounded-LLM execution. The LLM may select only supplied, already-admitted IDs for eight narrow roles. | Accepted model-enabled configuration. |
| **E2 / E3** | Optional 14B transfer experiments. | Not admitted: the structured-output reliability gate failed before pilot/full-MAS use. |
| **A0** | The architecture label for the complete deterministic MAS under E0. | The deterministic farmer-facing reference. |
| **A1–A6** | Evaluation-only component-removal baselines/ablations. | Never farmer-facing. |

Thus **E0 and A0 are not competing systems**: E0 is the no-LLM execution
configuration, and A0 is the complete architecture it executes. Likewise,
E1-v5 uses the full A0 safety and evidence architecture, but adds bounded
selection calls. It does not give the LLM authority to create facts, issue
operations, bypass gates, alter citations, or resolve safety conflicts.

## 3. Why E0 was required

### E0 — deterministic full MAS reference

| Question | Answer |
| --- | --- |
| **Why run it?** | It establishes that the complete evidence, planning, provenance, conflict, and safety system works without nondeterministic model behavior. |
| **Why is it necessary?** | Without a deterministic reference, an E1 difference could be caused by a changed scenario, source, gate, or implementation rather than bounded-LLM selection. It is also the reproducibility control. |
| **What differs from E1?** | E0 makes zero LLM calls. E1-v5 uses the same frozen MAS boundary but invokes eight tightly bounded selectors (2,400 accepted calls across 300 scenarios). |
| **What did it give?** | 300/300 normal traces passed all 20 structural checks; 60/60 conflict-policy fixtures followed the coordinator policy; and the final v2.2 release reproduced E0 semantic traces and both fixture suites exactly. |
| **What may be claimed?** | The deterministic implementation conforms to the frozen source/provenance/safety contract on this benchmark. |
| **What may not be claimed?** | 100% agricultural, farmer-decision, yield, disease, irrigation, or fertilizer accuracy. |

The E0 result is intentionally high because every normal scenario was frozen
only after its source, identity, temporal/geographic scope, and hash checks
passed. Its 100.0% structural rate is a verification result, not an outcome
prediction result. The A-runs and malformed-input fixtures demonstrate that
the oracle detects missing components and invalid evidence rather than simply
returning success.

## 4. Why A0–A6 were required

The A-runs isolate the contribution of the proposed architecture. They all use
the same 300 normal scenario IDs, frozen evidence, and external oracle as A0.
Only the declared capability changes. A lower all-check score means the
reduced system no longer satisfies the **complete proposed-MAS contract**; it
does not mean it produced no information or caused measured field harm.

| Run | Deliberate comparison | Why it was needed | Difference from A0 | Observed result | What it gave the research |
| --- | --- | --- | --- | ---: | --- |
| **A0** | Complete deterministic MAS | Reference against which every removal is measured. | Nothing removed. | **300/300** | Shows the full evidence-to-plan trace satisfies all 20 structural checks on valid inputs. |
| **A1** | Regional-operation-plan-only baseline | Tests whether calendar/nutrient/IPM plan cards alone are enough. | Removes coordinated context, scoped operation recovery, feasibility, and coordinator trace. | **0/300** | Shows that useful regional plan references alone do not preserve the full source-scoped operation, condition, citation, and decision contract. |
| **A2** | Centralized source-filtered RAG baseline | Tests whether one scoped retriever can substitute for typed multi-agent decomposition. | Retains scoped retrieval but has no regional plan, source-scoped operation path, or coordinated typed-claim trace. | **0/300** | Shows that filtered retrieval alone does not create the complete grounded-plan and provenance workflow. |
| **A3** | MAS without scoped RAG and recovered operations | Tests the value of the official source-recovery and scenario-scoped operation path. | Withholds retrievable RAG chunks, source-quoted operation passages, and post-harvest RAG passages. | **71/300** | Shows 229 traces lose complete conditional-operation/citation coverage when that source-scoped path is removed. |
| **A4** | MAS without regional operation plans | Tests the value of the third enrichment. | Withholds plan summaries/items, operation records/bindings/passages, and dependent nutrient/IPM policy roles. | **0/300** | Shows the regional-operation-plan enrichment is needed for complete grounded plan coverage across the frozen population. |
| **A5** | MAS without provenance/alignment validation | Tests the protective value of identity, scope, and binding gates. | Omits the declared downstream provenance/alignment validator boundary. | **300/300 normal** | Valid normal records do not contain the malformed evidence required to expose the missing gate; the actual gate-value result comes from fixtures. |
| **A6** | MAS without conflict coordination | Tests whether the coordinator does more than merely detect a conflict. | Retains detection and safety, but withholds detected conflicts from the coordinator. | **257/300** | The 43 natural NDVI–weather divergence traces lose the required provenance-aware resolution record. |

### Why A5 needs a separate fixture result

A5 obtaining 300/300 on valid normal inputs is correct, not evidence that
provenance gates are unnecessary. The normal 300 were already admitted as
aligned. The deliberately malformed provenance/alignment fixture suite creates
the missing causal test:

| Controlled input | A0 full system | A5 omitted-gate system | What it demonstrates |
| --- | ---: | ---: | --- |
| 50 crop/district/season/date/plan-binding mutations | 50/50 blocked | 50/50 exposed at the documented evaluation boundary | The removed validator is the reason malformed linked evidence is blocked before later decisions. |
| 10 raw weather-payload hash mutations | 10/10 blocked | 10/10 blocked | Raw-payload verification is a shared loader boundary, so A5 cannot bypass it. |

### Why A6 needs conflict fixtures as well as natural divergences

The 43 natural NDVI–weather divergences are real contextual differences, not
farm-action disagreements. They prove that the normal trace includes
conflict-aware coordination where the policy requires it. The separate
60-fixture policy suite tests all deterministic resolver branches:

| Conflict result | Outcome | Meaning |
| --- | ---: | --- |
| A0 policy compliance | 60/60 | The full coordinator follows declared scope, time, provenance, safety, and safe-deferral precedence. |
| A6 eligible conflict detection | 48/48 | Detection remains present after the coordinator is removed. |
| A6 coordinator resolutions | 0/48 | Resolution is deliberately impossible in A6, identifying the coordinator’s causal role. |
| Direct-action safety | 60/60 for both fixture paths | A controlled conflict never turns into an unsupported farm-specific action. |

## 5. Why E1-v5 was required

### E1-v5 — accepted bounded-LLM configuration

| Question | Answer |
| --- | --- |
| **Why run it?** | To test whether a local LLM can reliably rank or omit already-admitted evidence while the MAS retains deterministic source, scope, safety, and conflict authority. |
| **Why is it necessary?** | Structural safety alone cannot measure selection quality. A separate relevance benchmark measures whether the LLM chooses the intended fact/passage/card rather than merely producing schema-valid text. |
| **What differs from E0?** | Same frozen sources, loader, agents, operation bindings, RAG scope, oracle, and action restrictions. E1 adds exactly eight bounded selection roles through Ollama/Metal; E0 has none. |
| **What did it give?** | A held-out selection-quality result, Apple-GPU pilot evidence, a 300-scenario model-enabled MAS run, runtime/fallback observations, and a clean-checkout reproduction. |
| **What cannot change?** | Actions, sources, citations, conditions, gate outcomes, conflict policy, or direct-action permissions remain deterministic. |

#### Why the v5.1 protocol is credible

The project did **not** fine-tune Qwen weights, use LoRA, or train a new
model. It refined prompts and candidate packaging only:

1. The historical E1-v4 96-question benchmark revealed safe-empty, broad-RAG,
   and fertilizer-boundary selection errors.
2. A separate source-derived 96-question development set—disjoint from the
   original v4 questions—was used for role-specific prompt and candidate
   contract refinement.
3. V5 introduced decision sufficiency before topical relevance, visible
   `allowed_use`/`does_not_establish` boundaries, exact source-scoped RAG
   selection, field-dose boundary ordering, and one primary coordinator card.
4. V5.1 added request-sufficiency and role-aware packaging. Development ended
   after iteration 02.
5. Only then was a new immutable, 96-question held-out set used once. It is
   disjoint from E1-v4 and development scenarios/sites and was never used for
   further tuning.

#### What E1-v5 gave

| Evaluation stage | Result | Why it matters |
| --- | ---: | --- |
| Final held-out relevance set | 96 questions | Measures source-derived selection quality separately from the structural oracle. |
| Fact precision / recall | 98.6% / 98.6% | The bounded model selected expected admitted evidence with high ID-level accuracy. |
| Safe-empty accuracy | 100.0% | Insufficient context was not silently treated as decision authorization. |
| Exact RAG passage precision / recall | 100.0% / 100.0% | Named source-scoped operation selection and required-condition retrieval were exact on the held-out cases. |
| Invalid structured output / fallback | 0.0% / 0.0% | No held-out response was schema-invalid or required a visible safe fallback. |
| Apple-GPU pilot | 30/30 oracle passes | The model-enabled full path was stable before scale-up. |
| Full MAS run | 300/300 structural passes; 2,400 accepted bounded selections | Adding bounded selection did not weaken the existing structural safety contract. |
| Phase 9 reproduction | 43/43 frozen hashes; 300/300 semantic traces; 2,400/2,400 selections | The recorded E1 behavior reproduced under the same bound artifact and settings. |

This supports a narrow claim: **the E1 model reliably selects from
already-admitted evidence under the frozen evaluation boundary.** It does not
claim that the model independently knows agriculture or makes field-level
recommendations correctly.

## 6. Why E2 and E3 were run, and why they stopped

E2 and E3 were optional Phase 8 transfer experiments. They were conducted to
avoid assuming that a larger Qwen model or another Apple-GPU runtime would
automatically be better than the accepted 7B configuration.

| Run | Why it was needed | What differs from E1-v5 | Frozen transfer result | Consequence |
| --- | --- | --- | ---: | --- |
| **E2** | Tests whether increased model capacity improves bounded evidence selection under the same v5.1 interface. | Ollama/Metal Qwen2.5 14B GGUF Q4_K_M rather than the E1 7B Q4_K_M artifact. | 87/96 accepted; **9.375%** invalid structured output. | Failed the `<=2%` invalid-output requirement; no pilot or 300-scenario MAS run. |
| **E3** | Tests a local MLX-LM Apple-GPU deployment of the 14B model family. | MLX-LM 14B 4-bit artifact rather than Ollama GGUF. | 72/96 accepted; **25.0%** invalid structured output. | Failed the same gate; no pilot or 300-scenario MAS run. |

Both preflights verified actual Apple-GPU execution. That is deployment
evidence, not selection-quality evidence. The parser rejected malformed
`selected_fact_ids` instead of accepting a schema-invalid response as an
empty choice; therefore the negative result is safety-preserving and
transparent.

E2 versus E3 is **not** a pure runtime-only comparison. Their 14B artifacts
are different formats and cannot be proved byte-equivalent (GGUF Q4_K_M versus
MLX 4-bit). The valid statement is that they are *deployment-backend transfer
experiments using the same Qwen2.5 14B model family*. It would be invalid to
claim that MLX itself caused the observed difference.

## 7. What comparisons are valid

| Comparison | Valid question | Boundary on the conclusion |
| --- | --- | --- |
| **E0 vs E1-v5** | Does bounded selection alter relevance/presentation while the same structural safety contract is retained? | It is not an agricultural outcome comparison; qualitative farmer-message differences are illustrative only. |
| **A0 vs A1–A6** | Which declared architecture capability is necessary for each complete-contract property? | Scores are fixed-population structural coverage, not yield or farmer-benefit effects. |
| **A0 vs A6 fixtures** | Does conflict coordination add resolution beyond conflict detection? | The fixtures test a declared policy, not every possible real agricultural conflict. |
| **A0 vs A5 fixtures** | Do provenance/alignment gates stop malformed linked evidence before decision-making? | These are controlled software/evidence-boundary faults, not observed farm records. |
| **E1 vs E2** | Does the 14B Ollama transfer meet the same pre-registered structured-output gate? | It failed; do not claim a capacity advantage. |
| **E2 vs E3** | How did two non-identical 14B deployments behave under the same frozen selection transfer? | Do not attribute a difference solely to runtime. |

## 8. Metric interpretation in one place

| Metric family | Formula or denominator | What it means | What it does not mean |
| --- | --- | --- | --- |
| Structural oracle pass rate | `all-20-check passes / normal scenarios` | Trace conformance to the frozen evidence-and-safety contract. | Agricultural outcome accuracy. |
| Fact/RAG precision | `TP / (TP + FP)` | Correctness of selected admitted fact or exact passage IDs. | Truth of an uncited free-form LLM statement. |
| Fact/RAG recall | `TP / (TP + FN)` | Coverage of expected source-derived IDs. | Completeness of real-world agricultural knowledge. |
| Safe-empty accuracy | `correct empty selections / safe-empty questions` | Correct refusal to treat insufficient context as action authority. | A farm-action refusal rate in deployment. |
| Invalid-output rate | `schema-invalid responses / all LLM responses` | Structured-output reliability of a bounded selector. | Generic language fluency. |
| Fixture-policy compliance | `fixtures matching the declared policy / all fixtures` | Deterministic conflict or integrity-policy behavior. | Farm conflict-resolution success. |
| Reproducibility match rate | `normalized semantic trace matches / 300` | Same frozen code/artifacts reproduce the recorded decision evidence. | Equal latency or memory across machines. |

## 9. Result and artifact locations

| Need | Primary artifact |
| --- | --- |
| Readable result numbers and detailed interpretation | [RESULTS.md](RESULTS.md) |
| Hash-locked normal-input configuration | [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md) and [`evaluation/experiment_protocol.json`](../evaluation/experiment_protocol.json) |
| Final v5.1 held-out protocol | [BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md) |
| E2/E3 negative transfer record | [PHASE8_14B_EXPERIMENTS.md](PHASE8_14B_EXPERIMENTS.md) |
| Machine-readable A0–A6 comparison tables and figures | [`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/) |
| Final E0/E1-v5 controlled package | [`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/) |
| Regenerated v2.2 paper tables, figures, case studies, and E2/E3 negative-result evidence | [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/) |
| Clean-checkout reproducibility release | [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md) and [`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/) |

## 10. Paper-ready summary

The experiments jointly support the following precise research statement:

> On the frozen public-data India benchmark, the proposed MAS preserves a
> source-scoped, provenance-constrained, conflict-aware regional planning
> contract across all 300 normal scenarios. Controlled component removals and
> fixture suites show why scoped operations, regional plans, alignment gates,
> and conflict coordination are required. A bounded local 7B LLM can select
> already-admitted evidence under a held-out source-derived protocol without
> weakening those deterministic safety boundaries; larger 14B transfer
> configurations were not admitted after failing the pre-registered
> structured-output gate.

The statement deliberately does not extend to farm-specific prescriptions,
field outcomes, yield, profit, or general agricultural accuracy.
