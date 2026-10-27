# Project Files Information and Version Classification

This document is the human-maintained map of the repository for the current
**Multi-Agent Smart Agriculture Decision System – A RAG-Grounded Multi-Agent
Framework for Multimodal Decision Support in Precision Agriculture**.

It intentionally uses two levels of detail:

- every **source-code, script, test, and documentation file** is named
  explicitly and described individually;
- frozen data and persisted experiment results are described at their
  **own folder/archive boundary**, because each such folder contains hundreds
  of immutable scenario payloads or traces with the same producer and purpose.

This is more useful than listing thousands of nearly identical JSON/CSV raw
records one by one. Their exact file identities, hashes, and row-level
provenance are already recorded in the registry/scenario/enrichment manifests,
audits, run manifests, and reproducibility archives.

## 1. Classification rule

| Classification | Meaning |
| --- | --- |
| **New benchmark system** | Required by, produced for, or retained as evidence for the frozen six-crop benchmark, its source-grounded MAS, evaluation, or paper reproduction. |
| **New supporting record** | Documents a historical bounded-LLM/research step or a non-admitted experiment. It is not a runtime input to farmer output, but is retained for transparent research reporting. |
| **Legacy / old project** | Belongs to the original caller-input prototype, proxy/silver-label experiment, unrestricted RAG, or PlantVillage vision work. It must not enter new benchmark results. |
| **Local-only / ignored** | `.venv-macos/`, `venv312/`, `.env`, `.pytest_cache/`, `__pycache__/`, `.DS_Store`, and similar local files. They are intentionally absent from Git and from the research evidence boundary. |

The practical boundary is `data/benchmark_loader.py`: only its verified frozen
bundle can enter the current MAS. A file being present in the repository does
not make it admissible agricultural evidence.

## 2. New-version root, data, and result folders

### 2.1 Root files and active package folders

| Path | Classification | Purpose and why it is needed |
| --- | --- | --- |
| `README.md` | New benchmark system | Repository entry point: setup, active benchmark boundary, execution commands, results, and limitations. |
| `config.py` | New benchmark system | Central runtime configuration retained for the supported macOS environment and benchmark settings. |
| `requirements.txt` | New benchmark system | Full dependency declaration for the active macOS benchmark environment. |
| `.env.example` | New benchmark system | Safe template for optional local settings; it never contains a secret. |
| `.gitignore` | New benchmark system | Prevents local environments, secrets, caches, and uncontrolled data from being committed. |
| `agents/benchmark/` | New benchmark system | One-module-per-role implementation of the 21-agent provenance-constrained MAS. Every active agent is listed in Section 3. |
| `data/` | New benchmark system | Holds the frozen registry, aligned scenarios, four enrichments, scope/binding evidence, fixtures, and relevance datasets. Its active folders are listed below. |
| `evaluation/` | New benchmark system | Holds the oracle, batch/relevance/fixture runners, comparison tools, and reproducibility verifier. Active files are listed in Section 4. |
| `graph/` | New benchmark system | Holds the deterministic E0/A0 and bounded E1-v5 workflow graphs. |
| `llm/` | New benchmark system | Holds the bounded selection clients and v5.1 selection contract implementation. |
| `scripts/` | New benchmark system | Reproducible collectors, builders, recovery tools, audits, scenario generators, and macOS setup script. Every script is listed in Section 5. |
| `tests/` | New benchmark system | Regression suite for data, loader, agents, workflow, evaluations, fixtures, and reproducibility. Every test is listed in Section 6. |
| `Documentation/` | New benchmark system | Research records, source register, protocol, methods, results, and project-facing material. Every active document is listed in Section 7. |
| `results/` | New benchmark system | Immutable experiment-result archives. Each current archive is listed in Section 2.3. |

### 2.2 Frozen new-version data folders

| Folder | Classification | Contents, producer, and use |
| --- | --- | --- |
| `data/registry/` | New benchmark system | Final 30/30 site registry, evidence status, source references, audit, and admission documentation. Built from source-gated crop × district × season sites before scenario generation. |
| `data/scenarios/manifests/` | New benchmark system | Canonical 300-scenario identity manifest. Produced by anchor and supplementary scenario generators; defines scenario IDs and aligned site/date context. |
| `data/scenarios/processed/` | New benchmark system | Derived scenario features joined by `FrozenBenchmarkLoader`; no caller-supplied facts may replace them. |
| `data/scenarios/evidence/` | New benchmark system | Per-scenario evidence-status and integrity records used to restrict capability and scope. |
| `data/scenarios/raw/agmarknet/` | New benchmark system | Frozen historical mandi source responses for scenario-linked market context. Hash-verified by the loader. |
| `data/scenarios/raw/nasa_power/` | New benchmark system | Frozen NASA POWER weather/water responses for scenario-linked historical context. Hash-verified by the loader. |
| `data/scenarios/raw/sentinel/` | New benchmark system | Frozen Sentinel scene/quality material used only as representative-cell context. |
| `data/scenarios/enriched/` | New benchmark system | Main enrichment output: capability contract, weather/soil/satellite/market context, source scope, RAG corpus metadata, operation bindings, regional plans, and post-harvest material. |
| `data/scenarios/enriched/raw/` | New benchmark system | Frozen public-source snapshots used by enrichments: official documents, recovered PAU/MPKV material, Agmarknet, NASA POWER, Sentinel, and logistics sources. |
| `data/scenarios/enriched/rag_sources/` | New benchmark system | Preserved extracted official-document text and source-quoted operation passages used after metadata/scope gates pass. |
| `data/scenarios/enriched/pilot/` | New supporting record | Earlier small evidence-collection pilot retained for provenance history; the final 300-scenario artifacts above are the runtime inputs. |
| `data/llm_relevance_benchmark/` | New supporting record | Original 96-question E1-v4 source-derived relevance benchmark; retained as a diagnostic baseline, not final v5.1 quality evidence. |
| `data/llm_relevance_development/` | New supporting record | Disjoint development-only relevance examples used before v5.1 freeze; never reported as held-out results. |
| `data/llm_relevance_heldout/` | New benchmark system | Immutable 96-question v5.1 held-out relevance set, expected IDs, conditions, distractors, hashes, and pre-registered acceptance criteria. |
| `data/pilot_sets/apple_gpu_30_anchor_scenarios/` | New benchmark system | Exact one-anchor-per-site E1-v5 Apple-GPU pilot population. Produced by `scripts/build_apple_gpu_pilot_set.py`. |
| `data/conflict_fixture_registry/` | New benchmark system | Stored 60-case evaluation-only provenance-conflict fixture registry. It tests resolver policy without altering the 300 normal historical scenarios. |
| `data/provenance_fixture_registry/` | New benchmark system | Stored 60-case malformed identity/scope/hash fixture registry. It tests fail-closed evidence gates without creating agricultural observations. |
| `data/external/models/mlx-community--Qwen2.5-14B-Instruct-4bit/` | New supporting record | Local MLX artifact/cache used to document the non-admitted E3 transfer experiment; not needed by the accepted E0/E1-v5 paper runtime. |

### 2.3 New-version result archives

The live [results index](../results/README.md) is the authoritative navigation
point. The versioned archives below are the only ones admitted to the v2.2
paper release; earlier generations were moved intact to the dated recoverable
archive documented after this table.

| Folder or file | Classification | What it contains and why it is retained |
| --- | --- | --- |
| `results/README.md` | New benchmark system — official index | The human-readable v2.2 result index. It identifies the 19 evidence archives, the three retained runtime-support inputs, and the dated historical archive; it was written when pre-v2.2 outputs were moved so readers do not mix result generations. |
| `results/v2_2-e0-full-mas/` | New benchmark system — official | Deterministic E0/A0 300-scenario traces, oracle aggregates, and 60 conflict fixtures. |
| `results/v2_2-e1-v5-30site-pilot/` | New benchmark system — official | Accepted 30-site model-enabled pilot with bounded selections, traces, citations, runtime, and oracle output. |
| `results/v2_2-e1-v5-apple-gpu-preflight/` | New benchmark system — official | Verified Qwen2.5 7B Apple-Metal residency evidence for the accepted E1 runtime. |
| `results/v2_2-e1-v5-full-mas/` | New benchmark system — official | Accepted E1-v5 300-scenario traces, selections, detailed farmer messages, oracle output, and runtime metadata. |
| `results/v2_2-a1-regional-plan-only/`, `results/v2_2-a2-centralized-rag/`, `results/v2_2-a3-no-scoped-rag/`, `results/v2_2-a4-no-regional-plans/`, `results/v2_2-a5-no-provenance-gates/`, `results/v2_2-a6-conflict-ablation/` | New benchmark system — official | The six separately named controlled 300-scenario ablation archives, each with manifests, traces, Oracle results, and strata. |
| `results/v2_2-provenance-gate-fixtures/` | New benchmark system — official | The 60-case malformed provenance/alignment fixture archive. |
| `results/v2_2-phase7-controlled-comparison/` | New benchmark system — official | E0/E1/A1–A6/fixture comparison package, including paired traces and qualitative cases. |
| `results/v2_2-e2-apple-gpu-preflight/`, `results/v2_2-e2-v5-relevance-14b/`, `results/v2_2-e3-apple-gpu-preflight/`, `results/v2_2-e3-v5-relevance-14b-mlx/`, and `results/v2_2-phase8-e2-e3-relevance-transfer/` | New supporting record — official release scope | Verified 14B acceleration evidence and transparently non-admitted relevance-transfer results; neither E2 nor E3 progressed to full MAS. |
| `results/v2_2-final-reproducibility-2026-10-12/` | New benchmark system — official | Clean-commit E0 and fixture reproduction, 57/57 frozen-artifact/hash verification, and refreshed E1 Metal evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e0-full-mas/` | Historical / recoverable | Superseded deterministic E0/A0 result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/a1-regional-plan-only/` | Historical / recoverable | Superseded A1 baseline result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/a2-centralized-rag/` | Historical / recoverable | Superseded A2 baseline result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/a3-no-scoped-rag/` | Historical / recoverable | Superseded A3 ablation result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/a4-no-regional-plans/` | Historical / recoverable | Superseded A4 ablation result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/a5-no-provenance-gates/` | Historical / recoverable | Superseded A5 ablation result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/a6-conflict-ablation/` | Historical / recoverable | Superseded A6 ablation result generation; not paper evidence. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/architecture-comparison/` | Historical / recoverable | Earlier A0–A6 aggregate tables, strata, and figures; superseded by `v2_2-phase7-controlled-comparison/` and `v2_2-paper-artifacts/`. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/paper-artifacts/` | Historical / recoverable | Earlier Phase 10 presentation package; superseded by the official v2.2 paper package. |
| `results/v2_2-paper-artifacts/` | New benchmark system — official paper package | Final v2.2 Phase 10 package rendered from versioned v2.2 archives by `evaluation/paper_artifacts.py`. It contains `TABLE_1_...` through `TABLE_10_...`, four PNG/PDF figures, case studies, runtime/backend CSVs, a dedicated E2/E3 transfer-negative-result table/CSV, and a clean-state SHA-256 input/output manifest. `OFFICIAL_V2_2_RELEASE_MANIFEST.json`, generated by `evaluation/paper_release_manifest.py`, separately hashes the 19 canonical `v2_2-*` result archives and explicitly excludes historical result generations. |
| `results/archive/2026-10-12-pre-v2_2/development-history/e1-relevance-7b/` | Historical / recoverable | E1-v4 local 7B relevance result retained to explain later v5/v5.1 refinement. |
| `results/archive/2026-10-12-pre-v2_2/development-history/e1-v5-development-iteration-01/` | Historical / recoverable | Development-only v5 selector iteration 01; never a final model-quality result. |
| `results/archive/2026-10-12-pre-v2_2/development-history/e1-v5-development-iteration-02/` | Historical / recoverable | Development-only v5 selector iteration 02; development stopped before held-out v5.1 evaluation. |
| `results/e1-v5-heldout-preflight/` | New benchmark system | Hash and runtime preflight for the final held-out relevance evaluator. |
| `results/e1-v5-heldout-final/` | New benchmark system | One-time final v5.1 held-out relevance result, metrics, acceptance report, and per-question selections. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e1-apple-gpu-preflight/` | Historical / recoverable | Earlier Apple-Metal runtime preflight. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e1-v5-apple-gpu-preflight/` | Historical / recoverable | Earlier E1-v5 Apple-Metal evidence superseded by the v2.2 preflight. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e1-30-site-pilot/` | Historical / recoverable | Earlier model-enabled pilot. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e1-v5-30-site-pilot/` | Historical / recoverable | Earlier E1-v5 pilot superseded by the v2.2 pilot. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e1-v5-full-mas/` | Historical / recoverable | Earlier E1-v5 full run superseded by v2.2. |
| `results/e2-e3-artifact-binding.json` | New supporting record | Exact artifact-binding record for the E2/E3 transfer comparison; documents why it is not a pure runtime-only comparison. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e2-apple-gpu-preflight/` and `e2-v5-relevance-14b/` | Historical / recoverable | Earlier E2 preflight and frozen transfer result, superseded by the v2.2 transparent negative-result record. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e3-apple-gpu-preflight/` and `e3-v5-relevance-14b-mlx/` | Historical / recoverable | Earlier E3 preflight and frozen transfer result, superseded by the v2.2 transparent negative-result record. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/provenance-gate-fixtures/` | Historical / recoverable | Earlier provenance/alignment fixture generation, superseded by v2.2. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/phase7-controlled-comparison/` | Historical / recoverable | Earlier E0/E1/A0–A6 comparison package, superseded by v2.2. |
| `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/phase9-reproducibility-2026-10-10/` | Historical / recoverable | Earlier clean-checkout reproducibility release, superseded by final v2.2 verification. |
| `results/archive/2026-10-12-pre-v2_2/README.md` | Historical / recoverable index | Explains the three dated archive classes, their producer/result-generation status, and the rule that none is current paper evidence. It was created with the archival move, not by a runtime experiment. |
| `results/v2_2-final-reproducibility-2026-10-12/` | New benchmark system — final release verification | Fresh clean-commit E0 reproduction, both 60-case fixture reproductions, exact 57-artifact/hash and 300-trace comparison, environment manifest, and refreshed E1 Apple-Metal evidence for the official v2.2 release. |
| `results/.gitkeep` | New benchmark system | Keeps the result directory represented in Git when local runs are absent. |

## 3. New-version runtime source files

### 3.1 Loader, schema, graphs, and bounded LLM files

| File | Purpose and why it is needed |
| --- | --- |
| `data/benchmark_loader.py` | Fail-closed `FrozenBenchmarkLoader`; joins registry, scenarios, enrichments, scope, bindings, and raw hashes into one immutable runtime bundle. |
| `data/evidence_schema.py` | Defines `TypedEvidenceClaim`, stable claim IDs, permitted use, scope, provenance, conditions, and block reasons. |
| `agents/__init__.py` | Python package marker needed to import `agents.benchmark`. |
| `graph/__init__.py` | Python package marker for benchmark workflow imports. |
| `graph/benchmark_workflow.py` | Deterministic 21-agent E0/A0 workflow and the base for A1–A6 ablations. |
| `graph/benchmark_workflow_v5.py` | E1-v5 workflow: retains deterministic authority while invoking only permitted bounded selectors. |
| `llm/__init__.py` | Python package marker for bounded-client imports. |
| `llm/benchmark_llm_client.py` | Local bounded selector client: immutable candidate IDs, structured-output parsing, fallback recording, and backend metadata. |
| `llm/bounded_selection_v5.py` | Frozen v5.1 role-aware prompt/candidate packaging and sufficiency-first selection contract. |
| `llm/mlx_lm_client.py` | MLX-LM adapter used only for the documented E3 transfer experiment; not the accepted E1 farmer-facing runtime. |

### 3.2 Each active benchmark-agent file

| File | Agent use in the new MAS |
| --- | --- |
| `agents/benchmark/__init__.py` | Exposes the benchmark-agent package. |
| `agents/benchmark/README.md` | Documents the benchmark-agent package boundary. |
| `agents/benchmark/base.py` | Shared agent base types and deterministic claim-emission helpers. |
| `agents/benchmark/scenario_evidence_router.py` | Starts only from a verified frozen scenario bundle and blocks caller-provided facts. |
| `agents/benchmark/crop_district_season_alignment_validator.py` | Validates crop, district, state, season, date, site, and linked-evidence alignment. |
| `agents/benchmark/metadata_gate.py` | Distributes source metadata, allowed use, and capability restrictions to later agents. |
| `agents/benchmark/evidence_provenance.py` | Preserves source identity, URL, hash, locator, and role in typed claims. |
| `agents/benchmark/weather_context.py` | Produces historical weather/water context only; never forecast or irrigation authority. |
| `agents/benchmark/soil_context.py` | Produces static SoilGrids context only; never field N/P/K or dose authority. |
| `agents/benchmark/satellite_ndvi_context.py` | Produces representative-cell NDVI/quality context and natural-divergence inputs only. |
| `agents/benchmark/market_evidence.py` | Produces source-backed historical nearest-mandi interpretation only. |
| `agents/benchmark/fertilizer_baseline.py` | Presents regional nutrient policy and the no-field-dose boundary together. |
| `agents/benchmark/crop_protection_safety.py` | Preserves IPM/regulatory guardrails while blocking diagnosis-less treatment. |
| `agents/benchmark/vision_availability.py` | Returns `no_data` because benchmark scenarios have no aligned field images. |
| `agents/benchmark/regional_calendar_operation_window.py` | Emits source-linked regional calendar and time-window plan evidence. |
| `agents/benchmark/official_operations_rag.py` | Retrieves only metadata-admitted generic or source-scoped official passages. |
| `agents/benchmark/postharvest_storage_logistics.py` | Emits conditional handling and static facility/route context without availability, booking, or sell/hold claims. |
| `agents/benchmark/regulatory_compliance.py` | Preserves PPQS/CIBRC regulatory evidence for traceability; never authorizes chemical use. |
| `agents/benchmark/action_feasibility.py` | Applies scope and condition gates to turn official operations into conditional, blocked, or unavailable claims. |
| `agents/benchmark/uncertainty_abstention.py` | Consolidates no-data, missing-condition, and safety restrictions. |
| `agents/benchmark/conflict_detection.py` | Detects only same-domain, same-target eligible evidence conflicts. |
| `agents/benchmark/conflict_resolution.py` | Implements deterministic source/scope/time/safety precedence primitives. |
| `agents/benchmark/provenance_aware_coordinator.py` | Accepts, rejects, downgrades, or defers eligible conflicting claims and produces the decision trace. |
| `agents/benchmark/farmer_explanation_citation.py` | Renders approved plan cards and concise citations without inventing facts or operations. |
| `agents/benchmark/benchmark_evaluator.py` | Exposes trace facts to the independent downstream oracle; it cannot change the decision. |

## 4. New-version evaluation source files

| File | Purpose and why it is needed |
| --- | --- |
| `evaluation/__init__.py` | Python package marker for evaluation modules. |
| `evaluation/benchmark_contract.py` | Declares immutable scenario, capability, and evaluation contract constraints. |
| `evaluation/benchmark_oracle.py` | Independent downstream 20-check structural evaluator; its aggregate output also records one derived all-check pass row. |
| `evaluation/benchmark_systems.py` | Creates declared A0–A6 architecture configurations without altering frozen inputs. |
| `evaluation/benchmark_batch_runner.py` | Hash-checked persistent runner for E0/E1 full-MAS and A0–A6 300-scenario runs. |
| `evaluation/apple_gpu_preflight.py` | Verifies Ollama Metal residency, model identity, and Apple-GPU evidence for E1. |
| `evaluation/bounded_llm_relevance.py` | Runs the historical E1-v4 96-question relevance benchmark. |
| `evaluation/bounded_llm_relevance_development.py` | Runs the original development relevance harness. |
| `evaluation/bounded_llm_relevance_heldout.py` | Runs the earlier held-out relevance interface retained for comparison history. |
| `evaluation/bounded_llm_relevance_v5_development.py` | Runs the explicitly development-only v5 relevance set. |
| `evaluation/bounded_llm_relevance_v5_heldout.py` | Hash-checks and runs the final v5.1 held-out relevance evaluation. |
| `evaluation/conflict_fixture_runner.py` | Runs the 60 stored conflict-policy fixtures against production detection/coordinator code. |
| `evaluation/provenance_fixture_oracle.py` | Independently checks expected blocking/exposure behavior for malformed-evidence fixtures. |
| `evaluation/provenance_fixture_runner.py` | Runs the 60 stored provenance/alignment fixtures. |
| `evaluation/frozen_benchmark_comparison.py` | Builds source-hash-validated A0–A6 aggregate, stratified, table, and figure comparisons. |
| `evaluation/paper_artifacts.py` | Read-only Phase 10 generator that combines frozen data, persisted results, and the agent contract into paper tables, static figures, case studies, and a SHA-256 artifact manifest. |
| `evaluation/final_phase7_comparison.py` | Builds the final E0/E1-v5 controlled comparison package. |
| `evaluation/phase8_preflight.py` | Validates E2/E3 artifact bindings and Apple-GPU preflight evidence. |
| `evaluation/phase8_relevance_runner.py` | Runs the frozen E2/E3 v5.1 relevance-transfer gate. |
| `evaluation/phase8_batch_runner.py` | Prevents E2/E3 batch scale-up unless their transfer gate passes. |
| `evaluation/reproducibility_verification.py` | Performs Phase 9 clean-checkout hash, semantic-trace, selection, and fixture comparison. |
| `evaluation/experiment_protocol.json` | Hash-locked machine-readable normal-input experiment protocol consumed by runners. |

## 5. New-version collection, build, audit, and setup scripts

| File | Purpose and why it is needed |
| --- | --- |
| `scripts/select_representative_cropland_cells.py` | Selects and records representative cropland cells for final registry locations. |
| `scripts/generate_anchor_scenarios.py` | Generates the 30 registered-site anchor scenarios. |
| `scripts/generate_supplementary_scenarios.py` | Generates source-gated supplementary scenarios to reach the frozen 300. |
| `scripts/collect_nasa_power_fixed_window_weather.py` | Collects fixed historical NASA POWER weather windows. |
| `scripts/collect_nasa_power_water_context.py` | Collects NASA POWER water-context evidence. |
| `scripts/collect_soilgrids_wcs_profiles.py` | Collects SoilGrids static soil property profiles. |
| `scripts/collect_sentinel_scene_coverage.py` | Collects Sentinel scene-quality/coverage metadata. |
| `scripts/collect_sentinel_ndvi_context.py` | Collects representative-cell Sentinel NDVI context. |
| `scripts/recover_sentinel_ndvi_context.py` | Recovers and validates missing Sentinel context where public evidence permits. |
| `scripts/collect_predecision_sentinel_ndvi_timeseries.py` | Collects pre-decision NDVI chronology for natural divergence analysis. |
| `scripts/collect_agmarknet_market_context.py` | Collects source-backed Agmarknet market context. |
| `scripts/collect_agmarknet_historical_market_evidence.py` | Collects historical Agmarknet evidence for market interpretation. |
| `scripts/collect_regional_management_evidence.py` | Collects official regional crop-management documents. |
| `scripts/collect_official_rag_sources.py` | Collects and registers official RAG-source documents. |
| `scripts/collect_crida_ccp_evidence.py` | Collects CRIDA crop-contingency-plan evidence. |
| `scripts/discover_public_district_kvk_advisories.py` | Records public KVK/district advisory-discovery attempts and evidence status. |
| `scripts/build_existing_policy_enrichment.py` | Builds first-enrichment policy/context records from frozen sources. |
| `scripts/build_archived_advisory_enrichment.py` | Builds archived dated-advisory enrichment records when valid evidence exists. |
| `scripts/build_exact_week_iisr_action_enrichment.py` | Builds source-quoted exact-week IISR operation records and bindings. |
| `scripts/build_official_action_enrichment.py` | Builds official source-scoped operation enrichment records. |
| `scripts/build_archived_pau_kharif_action_enrichment.py` | Builds recovered PAU Kharif operation records and time-valid bindings. |
| `scripts/build_archived_pau_rabi_action_enrichment.py` | Builds recovered PAU Rabi operation records and time-valid bindings. |
| `scripts/build_mpkv_chickpea_action_enrichment.py` | Builds MPKV chickpea operation records and scenario bindings. |
| `scripts/build_combined_official_action_catalog.py` | Combines validated official operations into one action catalog. |
| `scripts/build_combined_official_rag_catalog.py` | Combines metadata-admitted official RAG records. |
| `scripts/build_embedded_agmarknet_market_context.py` | Builds embedded historical market-context features. |
| `scripts/build_natural_signal_divergence_candidates.py` | Identifies natural NDVI–weather divergence candidates without fabricating conflicts. |
| `scripts/build_regional_operation_plan.py` | Builds the third-enrichment source-linked regional calendar/nutrient/IPM operation-plan library. |
| `scripts/build_postharvest_logistics_enrichment.py` | Builds fourth-enrichment crop-scoped handling and static logistics context. |
| `scripts/build_mas_enrichment_contract.py` | Produces the loader/agent contract joining all active enrichments. |
| `scripts/build_source_scoped_preflight_audit.py` | Preflights source-scoped final-site admission. |
| `scripts/build_source_scoped_final_admission.py` | Produces final 30/30 source-scoped site admission decision. |
| `scripts/build_conflict_fixture_registry.py` | Builds the stored 60-case conflict-policy fixture registry. |
| `scripts/build_provenance_fixture_registry.py` | Builds the stored 60-case provenance/alignment fixture registry. |
| `scripts/build_bounded_llm_relevance_benchmark.py` | Builds the historical v4 relevance benchmark. |
| `scripts/build_bounded_llm_relevance_development_set.py` | Builds the disjoint development-only relevance set. |
| `scripts/build_bounded_llm_relevance_heldout_set.py` | Builds the immutable final v5.1 held-out relevance set. |
| `scripts/build_apple_gpu_pilot_set.py` | Builds the exact 30-site Apple-GPU pilot subset. |
| `scripts/check_market_recovery_feasibility.py` | Checks whether public historical market recovery is feasible before claiming it. |
| `scripts/expand_official_rag_corpus.py` | Adds only metadata-validated public official RAG sources. |
| `scripts/audit_scenario_enrichment.py` | Fails closed if scenario enrichment identity/scope/source requirements fail. |
| `scripts/audit_advanced_enrichment.py` | Audits advanced enrichment records and their source integrity. |
| `scripts/audit_regional_operation_plan.py` | Audits the third-enrichment regional operation-plan dataset. |
| `scripts/audit_postharvest_logistics_enrichment.py` | Audits fourth-enrichment post-harvest/logistics source and scope boundaries. |
| `scripts/audit_expanded_official_rag_corpus.py` | Audits expanded official RAG document metadata and scopes. |
| `scripts/audit_archived_pau_kharif_action_enrichment.py` | Audits recovered PAU Kharif operation evidence. |
| `scripts/audit_archived_pau_rabi_action_enrichment.py` | Audits recovered PAU Rabi operation evidence. |
| `scripts/audit_mpkv_chickpea_action_enrichment.py` | Audits MPKV chickpea operation evidence. |
| `scripts/setup_macos.sh` | Creates the supported macOS virtual environment and installs dependencies. |

## 6. New-version test files

| File | What it validates |
| --- | --- |
| `tests/__init__.py` | Test package marker. |
| `tests/test_benchmark_loader.py` | Frozen loader joins, hashes, scope, and fail-closed behavior. |
| `tests/test_evidence_schema.py` | Typed claim fields, stable IDs, restrictions, and immutability. |
| `tests/test_benchmark_agents.py` | New benchmark-agent permissions and expected claim output. |
| `tests/test_benchmark_llm_boundary.py` | Bounded selector cannot modify sources, actions, gates, citations, or conditions. |
| `tests/test_benchmark_batch_runner.py` | Hash-checked persistent full-batch execution and stored run artifacts. |
| `tests/test_benchmark_oracle.py` | Independent 20-check Oracle pass/fail behavior. |
| `tests/test_benchmark_systems.py` | Declared A0–A6 component-removal configuration boundaries. |
| `tests/test_bounded_llm_relevance.py` | Historical v4 relevance dataset/runner integrity. |
| `tests/test_bounded_llm_relevance_development.py` | Development-set integrity and development-only labelling. |
| `tests/test_bounded_llm_relevance_heldout.py` | Earlier held-out relevance boundary compatibility. |
| `tests/test_bounded_llm_relevance_v5_development.py` | V5 development runner and no-final-result boundary. |
| `tests/test_bounded_llm_relevance_v5_heldout.py` | Final v5.1 hash, criteria, and held-out runner behavior. |
| `tests/test_bounded_llm_v5.py` | V5.1 prompts, candidate packaging, safe-empty, and structured-ID contract. |
| `tests/test_apple_gpu_preflight.py` | E1 Apple Metal artifact/residency proof requirements. |
| `tests/test_phase8_preflight.py` | E2/E3 artifact-binding and Apple-GPU preflight checks. |
| `tests/test_phase8_relevance_runner.py` | E2/E3 frozen relevance-transfer evaluation and admission decision. |
| `tests/test_phase8_batch_runner.py` | E2/E3 scale-up refusal after a failed transfer gate. |
| `tests/test_conflict_fixture_registry.py` | Stored conflict-fixture identity, policy family, and source constraints. |
| `tests/test_conflict_resolution.py` | Deterministic provenance/scope/time/safety conflict resolution and safe deferral. |
| `tests/test_provenance_fixture_registry.py` | Stored malformed-evidence fixture integrity and expected A0/A5 outcomes. |
| `tests/test_final_phase7_comparison.py` | Final E0/E1/A0–A6/fixture comparison package consistency. |
| `tests/test_frozen_benchmark_comparison.py` | Cross-run population/hash/oracle-schema equality before comparison. |
| `tests/test_paper_artifacts.py` | Phase 10 generation: required tables/figures, composition counts, manifest coverage, and structural-interpretation boundary. |
| `tests/test_reproducibility_verification.py` | Phase 9 semantic trace, selection, and fixture reproducibility comparison. |
| `tests/test_experiment_protocol.py` | Machine/human experiment-protocol version and frozen-contract consistency. |
| `tests/test_anchor_scenario_generator.py` | Anchor-scenario generation and registered-site alignment. |
| `tests/test_supplementary_scenario_generator.py` | Supplementary-scenario source/evidence alignment. |
| `tests/test_audit_scenario_enrichment.py` | Enrichment-audit rejection behavior. |
| `tests/test_mas_enrichment_contract.py` | Loader contract coverage across all active enrichments. |
| `tests/test_regional_operation_plan.py` | Third-enrichment plan items, bindings, and audit expectations. |
| `tests/test_postharvest_logistics_enrichment.py` | Fourth-enrichment scope, handling, facility, and safety boundaries. |
| `tests/test_official_action_enrichment.py` | Official source-quoted operation records and bindings. |
| `tests/test_exact_week_iisr_action_enrichment.py` | Exact-week IISR operation records and date/scope restrictions. |
| `tests/test_existing_policy_enrichment.py` | First-enrichment policy records and source constraints. |
| `tests/test_expanded_official_rag_corpus.py` | Expanded official RAG corpus metadata/scope admission. |
| `tests/test_source_scoped_preflight_audit.py` | Source-scoped site preflight audit. |
| `tests/test_source_scoped_final_admission.py` | Final source-scoped 30/30 site admission. |
| `tests/test_agmarknet_market_context.py` | Agmarknet market context collection and interpretation boundary. |
| `tests/test_agmarknet_historical_market_collector.py` | Historical Agmarknet collector persistence and integrity. |
| `tests/test_embedded_agmarknet_market_context.py` | Embedded historical market-context feature generation. |
| `tests/test_market_recovery_feasibility.py` | Historical market recovery feasibility classification. |
| `tests/test_nasa_power_fixed_window_weather.py` | NASA POWER fixed weather-window collection. |
| `tests/test_nasa_power_water_context.py` | NASA POWER water-context collection. |
| `tests/test_soilgrids_wcs_collector.py` | SoilGrids WCS profile collection and identity/scope checks. |
| `tests/test_sentinel_scene_collector.py` | Sentinel scene coverage/quality collection. |
| `tests/test_sentinel_ndvi_context.py` | Sentinel NDVI context collection/scope restrictions. |
| `tests/test_recover_sentinel_ndvi_context.py` | Sentinel recovery process and safe missing-data behavior. |
| `tests/test_representative_cropland_cells.py` | Representative-cell selection and registry alignment. |
| `tests/test_regional_management_collector.py` | Official regional-management source collection. |
| `tests/test_crida_ccp_collector.py` | CRIDA crop-contingency-plan source collection. |
| `tests/test_data_gov_market.py` | Retained data.gov market collector compatibility check. |
| `tests/test_agents.py` | Retained legacy-agent compatibility check; it is not a new benchmark paper metric. |
| `tests/test_vision_device.py` | Retained legacy device compatibility check; it is not a vision benchmark result. |

## 7. Current documentation files

| File | Purpose |
| --- | --- |
| `Documentation/AGENTS.md` | Inputs, outputs, ordering, handoffs, permissions, and boundaries for all 21 benchmark agents. |
| `Documentation/APPLE_GPU_PREFLIGHT.md` | Apple Metal proof method, artifact identity, and pilot-preflight boundary. |
| `Documentation/Approach.md` | Complete end-to-end methodology: data, enrichment, MAS, prompt refinement, metrics, and reproducibility. |
| `Documentation/README.md` | Canonical documentation map: identifies the source-of-truth document for each research, technical, evaluation, result, and historical topic to prevent duplicate records. |
| `Documentation/BOUNDED_LLM_RELEVANCE_BENCHMARK.md` | Historical E1-v4 relevance benchmark schema and limits. |
| `Documentation/BOUNDED_LLM_RELEVANCE_DEVELOPMENT_SET.md` | Development-only relevance dataset boundary. |
| `Documentation/BOUNDED_LLM_V5_SELECTION_CONTRACT.md` | V5.1 bounded-selection authority, prompt, and candidate-package contract. |
| `Documentation/BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md` | Final immutable held-out relevance protocol and acceptance criteria. |
| `Documentation/DATA_SOURCES.md` | Final source citations, links, restrictions, and provenance across registry, scenarios, enrichments, and RAG. |
| `Documentation/E1_RELEVANCE_ERROR_ANALYSIS.md` | Diagnostic analysis that motivated v5/v5.1 prompt/candidate refinement. |
| `Documentation/EVALUATION_POLICY.md` | Permitted claims, prohibited claims, metric boundaries, fixtures, and repeatability policy. |
| `Documentation/EXPERIMENT_CONFIGURATION_AND_ARCHIVE_GUIDE.md` | Canonical decoder for E0/A0–A6/E1–E3: system change, research question, official v2.2 archive location, result, permitted interpretation, and exact meaning of each run/fixture/preflight/release file. |
| `Documentation/EXPERIMENT_PROTOCOL.md` | Normal-input experiment configuration, frozen comparison boundary, and run sequence. |
| `Documentation/EXPERIMENT_RUNS_GUIDE.md` | Why E0–E3 and A0–A6 were run, their differences, results, and valid interpretations. |
| `Documentation/FILES_INFORMATION.md` | This file: human-maintained new-versus-legacy project map. |
| `Documentation/MAS_BASELINE_AUDIT.md` | Explicit old-prototype versus current-benchmark boundary. |
| `Documentation/ORACLE_EVALUATION_GUIDE.md` | Independent 20-check Oracle logic, formulas, aggregation, and failure interpretation. |
| `Documentation/PHASE8_14B_EXPERIMENTS.md` | Transparent E2/E3 transfer/preflight negative-result record. |
| `Documentation/REPRODUCIBILITY_VERIFICATION.md` | Phase 9 commands, semantic equality rules, and release archive boundary. |
| `Documentation/RESULTS.md` | Official v2.2 readable result record: exact formulas, source data, numerators/denominators, E0/E1, A0–A6, fixtures, held-out LLM, E2/E3, reproducibility, and the Phase 10 artifact map. |
| `Documentation/To-Do.md` | Active paper-writing and release checklist plus explicitly separated future extensions; it does not duplicate completed implementation history. |
| `Documentation/UPDATES.md` | Concise chronological project change record, with detailed sources, methods, contracts, and results linked to their canonical documents. |
| `Documentation/Documents/Current Project Idea.md` | Guide-facing current project proposal. |
| `Documentation/Documents/New Architecture Justification.md` | Guide-facing justification and use of the current architecture/agents. |
| `Documentation/Documents/New Architecture Diagram.png` | Diagram of the current benchmark architecture. |
| `Documentation/Documents/Evaluation 1.pptx` | Current project presentation material. |

## 8. Explicit legacy / old-project files and folders

None of the following is used by `FrozenBenchmarkLoader`, the 21-agent
benchmark graph, the current oracle, or the paper-result runs.

| Path | Why it belongs to the old project / why it is excluded now |
| --- | --- |
| `main.py` | Old CLI/demo entry point accepting non-frozen sample or live-style inputs. |
| `requirements-core.txt` | Earlier minimal prototype dependency subset; `requirements.txt` is the active environment file. |
| `agents/base_agent.py` | Old prototype evidence base class, superseded by `data/evidence_schema.py` for benchmark claims. |
| `agents/coordinator.py` | Old generic coordinator, superseded by `agents/benchmark/provenance_aware_coordinator.py`. |
| `agents/fertilizer_agent.py` | Old fertilizer agent relying on non-benchmark field-style inputs. |
| `agents/irrigation_agent.py` | Old irrigation agent requiring missing farm moisture/stage inputs. |
| `agents/market_agent.py` | Old market agent outside the frozen source-scoped market path. |
| `agents/soil_agent.py` | Old soil agent outside the static-SoilGrids benchmark boundary. |
| `agents/vision_agent.py` | Old vision agent; current benchmark returns `no_data` without aligned images. |
| `agents/weather_agent.py` | Old weather agent outside the frozen historical-weather boundary. |
| `baselines/__init__.py` | Old baseline package marker. |
| `baselines/single_llm.py` | Old centralized single-LLM example; not a formal current paper baseline. |
| `baselines/llm_rag.py` | Old LLM+RAG example; not the current scoped official RAG path. |
| `data/loaders.py` | Old proxy/Kaggle/sample loader, superseded by `data/benchmark_loader.py`. |
| `data/sample_market.json` | Old demo market sample. |
| `data/sample_soil.json` | Old demo soil sample. |
| `data/sample_weather.json` | Old demo weather sample. |
| `data/external/crop_recommendation/` | Old external crop-recommendation dataset; not part of the six-crop frozen registry. |
| `data/external/market_prices/` | Old external market-price data; not the source-hashed Agmarknet scenario evidence. |
| `data/external/plantvillage/` | Old reduced PlantVillage image dataset. |
| `data/external/plantvillage_full/` | Old full PlantVillage image dataset. |
| `data/knowledge_base/` | Old unrestricted/project-authored knowledge base; replaced by metadata-filtered official RAG. |
| `graph/workflow.py` | Old graph for caller-provided dictionaries; replaced by frozen `scenario_id` workflows. |
| `llm/llm_client.py` | Old generic LLM client; replaced by bounded benchmark selector client. |
| `rag/__init__.py` | Old unrestricted RAG package marker. |
| `rag/knowledge_base.py` | Old local RAG knowledge-base code. |
| `rag/retriever.py` | Old local RAG retriever code. |
| `rag/vector_store.py` | Old local vector-store code. |
| `evaluation/conflict_scenarios.py` | Old conflict-scenario helper, superseded by the stored provenance conflict-fixture registry. |
| `evaluation/diagnose_action_bias.py` | Old prototype diagnostic. |
| `evaluation/matched_multimodal_eval.py` | Old multimodal evaluation module. |
| `evaluation/metrics.py` | Old proxy/silver-label metric helpers, not current oracle metrics. |
| `evaluation/run_accuracy_eval.py` | Old silver-label accuracy runner. |
| `evaluation/run_comparison.py` | Old evaluation comparison runner. |
| `evaluation/run_eval.py` | Old generic evaluation runner. |
| `evaluation/silver_labels.py` | Old rule-derived silver labels; not paper ground truth. |
| `evaluation/vision_alignment.py` | Old vision alignment evaluation. |
| `vision/__init__.py` | Old PlantVillage vision package marker. |
| `vision/checkpoints/` | Old trained vision checkpoint artifacts. |
| `vision/device.py` | Old device-selection helper for vision work. |
| `vision/evaluate_checkpoint.py` | Old vision checkpoint evaluator. |
| `vision/gradcam.py` | Old Grad-CAM visualization helper. |
| `vision/inference.py` | Old image-inference path. |
| `vision/model.py` | Old vision-model definition. |
| `vision/train.py` | Old vision-training path. |
| `outputs/gradcam/` | Old Grad-CAM generated output archive. |
| `results/archive/2026-10-12-pre-v2_2/legacy-vision-and-silver-labels/accuracy_results.csv` | Old proxy/silver-label accuracy result. |
| `results/archive/2026-10-12-pre-v2_2/legacy-vision-and-silver-labels/accuracy_results_by_category.csv` | Old proxy/silver-label category result. |
| `results/archive/2026-10-12-pre-v2_2/legacy-vision-and-silver-labels/accuracy_results_summary.csv` | Old proxy/silver-label summary. |
| `results/archive/2026-10-12-pre-v2_2/legacy-vision-and-silver-labels/matched_multimodal.csv` | Old multimodal matching output. |
| `results/archive/2026-10-12-pre-v2_2/legacy-vision-and-silver-labels/vision_eval/` | Old vision evaluation archive. |
| `results/archive/2026-10-12-pre-v2_2/legacy-vision-and-silver-labels/vision_eval_full38/` | Old full-38-class vision evaluation archive. |
| `Documentation/Documents/Old Project Idea.docx` | Preserved old project proposal. |
| `Documentation/Documents/Old Architecture Justification.docx` | Preserved old architecture justification. |
| `Documentation/Documents/Old Architecture Diagram.png` | Preserved old architecture diagram. |
| `Documentation/Documents/Literature Survey/` | Preserved previous literature-reading documents/PDFs; background only, not benchmark evidence. |

## 9. Minimal current-paper reproduction boundary

To reproduce the current paper results, retain:

1. the new root configuration/dependency files and the active source files in
   Sections 3–5;
2. the frozen data folders in Section 2.2;
3. the 19 v2.2 archives named in
   `results/v2_2-paper-artifacts/OFFICIAL_V2_2_RELEASE_MANIFEST.json`, the
   two frozen held-out support directories, and the Phase 10
   `results/v2_2-paper-artifacts/` package in Section 2.3;
4. the test files, `evaluation/paper_artifacts.py`, and current documentation
   in Sections 4, 6, and 7.

Do **not** load the Section 8 legacy folders/files into the benchmark path.
They are preserved for historical transparency only and are not part of the
current paper’s frozen evidence, agent workflow, RAG corpus, oracle, or
result claims.
