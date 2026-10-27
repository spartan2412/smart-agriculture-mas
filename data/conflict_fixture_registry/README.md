# Evaluation-Only Conflict Fixture Registry

This registry stores **60 reproducible counterfactual provenance-conflict
fixtures** for evaluating the benchmark MAS conflict resolver. It is separate
from both the verified 30-site study registry and the frozen 300-scenario
benchmark.

Every fixture references one immutable real `base_scenario_id`, then applies a
small in-memory test overlay to competing typed claims. The overlay changes
only declared source scope, time validity, provenance completeness, safety
gate, or identity/hash metadata. It never adds agricultural observations.

## Classification and boundary

Every record is labelled:

```text
evaluation_only_counterfactual_not_real_farm_evidence
```

Therefore these fixtures:

- are not real historical farm situations;
- do not modify a real registry row, scenario, enrichment, source artifact, or
  normal MAS loader result;
- are not passed to the normal farmer-facing benchmark workflow;
- cannot issue a direct farm action; and
- must be described in the paper as controlled policy-evaluation cases, not
  real-world agricultural outcomes.

## Contents

| Artifact | Role |
| --- | --- |
| `conflict_fixture_manifest.csv` | One-row index for every stored fixture, expected policy status, base scenario, and checksum. |
| `fixtures/*.json` | Full two-claim counterfactual overlay or integrity/negative-control record. |
| `CONFLICT_FIXTURE_AUDIT.md` | Coverage and safety-boundary audit. |
| `DATA_SOURCES.md` | Exact frozen artifacts from which base identity and source references are derived. |

## Coverage

There are ten fixtures for each focused crop—rice, wheat, maize, chickpea,
soybean, and tomato—for **60 total**. They are distributed as two fixtures
across each of the 30 real final crop--location sites, rather than repeatedly
using one convenient district per crop:

| Fixture group | Count | Required outcome |
| --- | ---: | --- |
| Geographic scope, temporal validity, and provenance precedence | 30 | Retain the higher-precedence conditional claim and reject the weaker claim. |
| Safety restriction precedence | 12 | Retain the restriction; no direct action may be issued. |
| Equal-precedence opposition | 6 | Safely defer rather than choose an arbitrary claim. |
| Identity/hash integrity mutation | 6 | Block before conflict detection and coordination. |
| Unrelated-domain negative control | 6 | Do not manufacture a conflict from weather and market context. |

The separate frozen benchmark retains **43 real NDVI--weather contextual
divergences**. Those real records are not copied or relabelled as fixtures.

## Reproducibility

Build or revalidate the registry:

```bash
.venv-macos/bin/python scripts/build_conflict_fixture_registry.py
```

The builder derives the selected real base identities and real source
references from frozen inputs, writes content hashes, and fails closed when
the expected 60-row/ten-per-crop coverage is not present.

The evaluation runner loads a real base scenario and applies an overlay only
in memory:

```python
from evaluation.conflict_fixture_runner import ConflictFixtureRunner

runs = ConflictFixtureRunner().run_all()
assert all(run.expected_match for run in runs)
```

The runner separates a fixture's own conflict from any background natural
NDVI--weather divergence belonging to its real base scenario. This preserves
the distinction between real contextual evidence and controlled evaluation
evidence.

The current automated suite verifies all 60 expected fixture outcomes. Those
outcomes are policy checks only: 30 precedence selections, 12 safety
restrictions, 6 safe deferrals, 6 integrity blocks before coordination, and 6
unrelated-domain non-conflicts. They do not establish agricultural action
accuracy, farmer usefulness, or a real farm outcome.

The persisted architecture report records the complementary A6 ablation on
this same fixture set: all 48 coordinator-required conflicts remain detected,
but 0/48 are resolved because the coordinator input is intentionally withheld.
This is expected ablation behaviour, not a passing farmer-facing result. See
[`results/architecture-comparison`](../../results/architecture-comparison/) for
the separate A0/A6 fixture table and figure.

`BenchmarkEvaluationOracle.evaluate_fixture_runs()` independently aggregates
the same fixture-run outcomes. It requires the exact family composition
(48 coordinator-resolution, 6 pre-resolution integrity-rejection, and 6
unrelated-domain negative-control fixtures) as well as 60/60 expected matches.
This oracle result is separate from the 18-check normal-scenario oracle and
cannot enter a farmer-facing run. See the
[oracle evaluation guide](../../Documentation/ORACLE_EVALUATION_GUIDE.md).

See [`Documentation/EVALUATION_POLICY.md`](../../Documentation/EVALUATION_POLICY.md)
for the paper-facing measurement boundary,
[`Documentation/ORACLE_EVALUATION_GUIDE.md`](../../Documentation/ORACLE_EVALUATION_GUIDE.md)
for the executable evaluation procedure, and
[`Documentation/AGENTS.md`](../../Documentation/AGENTS.md) for the normal
workflow separation.
