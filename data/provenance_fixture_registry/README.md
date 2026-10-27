# Evaluation-Only Provenance and Alignment Fixture Registry

This registry stores **60 reproducible, single-fault counterfactual fixtures** for testing the frozen benchmark's integrity boundary. It is separate from the 30-site registry, four agricultural enrichments, 300 frozen scenarios, and the 60 conflict-resolution fixtures.

Every fixture starts from one immutable real scenario, then applies one in-memory identity/binding or payload-hash mutation. It contains no weather, soil, disease, market, fertilizer, crop-stage, yield, or farm observation and is never supplied to the farmer-facing MAS workflow.

## What this evaluates

| Fault class | Cases | Production boundary under test | Expected A0 result | Expected A5 result |
| --- | ---: | --- | --- | --- |
| Plan item crop scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |
| Plan item district scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |
| Plan item season scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |
| Plan item decision-date scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |
| Plan-item scenario binding mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |
| Weather payload SHA-256 mismatch | 10 | Frozen loader raw-payload verifier | Block | Block |

A5 omits the alignment validator and the provenance-trace agent by design. It does **not** bypass the loader: payload hash verification remains a shared immutable-input boundary for A0 and A5. The `EvidenceProvenanceAgent` is an auditable provenance summary, not a second hash validator; this registry records that architectural distinction rather than claiming a nonexistent check.

## Coverage and safety boundary

- 60 fixtures total: 10 per fault class, 10 per focused crop, and two per each of the 30 final crop--location sites.
- A fixture is a test of rejection/exposure behaviour, not a real farm event or agricultural outcome.
- A5 exposure stops at its evaluation-only gate boundary. The runner never executes downstream agents, coordinator, or farmer message on an invalid bundle.
- All expected direct-farm-action values are `false` and no decision object is constructed for a fixture.

## Contents

| Artifact | Purpose |
| --- | --- |
| `provenance_fixture_manifest.csv` | One-row index with expected A0/A5 outcomes and checksum. |
| `fixtures/*.json` | Full labelled in-memory overlay for each controlled fault. |
| `PROVENANCE_FIXTURE_AUDIT.md` | Coverage and expected-result audit. |
| `DATA_SOURCES.md` | Exact frozen project artifacts from which identities and plan rows are derived. |

## Rebuild and evaluate

```bash
.venv-macos/bin/python scripts/build_provenance_fixture_registry.py
.venv-macos/bin/python -m evaluation.provenance_fixture_runner --output-dir results/provenance-gate-fixtures
```

The normal benchmark path never imports these fixtures. See [the evaluation policy](../../Documentation/EVALUATION_POLICY.md) and [oracle guide](../../Documentation/ORACLE_EVALUATION_GUIDE.md) for paper-facing interpretation.

The persisted paired execution passed all 60 expected outcomes: A0 blocked all
50 plan identity/binding mutations, A5 exposed all 50 only at its intentional
evaluation boundary, and the shared loader blocked all 10 payload-hash
mutations for both systems. No fixture created a decision or direct farm
action. The cross-run report preserves these as a separate protocol in
[`results/architecture-comparison`](../../results/architecture-comparison/).
