# Conflict Fixture Registry Audit

- Schema version: `1.0`
- Classification: `evaluation_only_counterfactual_not_real_farm_evidence`
- Frozen 300-scenario manifests and real-site registry: unchanged by this registry.
- Each fixture references a real base scenario and changes only evaluation provenance/gate metadata.
- No fixture contains synthetic weather, soil, disease, fertilizer, market, crop-stage, yield, or farm observation.
- No fixture is loaded by the normal farmer-facing benchmark workflow.

## Coverage

| Fixture family | Count |
| --- | ---: |
| coordinator_resolution | 48 |
| negative_control_no_comparable_conflict | 6 |
| pre_resolution_integrity_rejection | 6 |

| Crop | Stored fixtures |
| --- | ---: |
| rice | 10 |
| wheat | 10 |
| maize | 10 |
| chickpea | 10 |
| soybean | 10 |
| tomato | 10 |

The registry covers all **30 final crop--location sites**, with **two fixtures per site**.

## Expected resolver behaviour

- 30 source-scope, temporal-validity, or provenance cases must resolve by deterministic precedence.
- 12 safety cases must resolve by safety restriction and block a direct action.
- 6 equal-precedence cases must defer rather than choose an arbitrary winner.
- 6 integrity overlays must block before conflict detection/coordinator execution.
- 6 unrelated-domain negative controls must not be detected as conflicts.

The 43 natural NDVI--weather divergence cases remain separate real, non-action benchmark records; they are not copied or relabelled here.

## Oracle evaluation status

`BenchmarkEvaluationOracle.evaluate_fixture_runs()` requires both complete
fixture-family coverage and expected policy outcomes. The current registry
passes **60/60** outcomes with the required 48/6/6 family composition. This is
resolver-policy compliance only; it does not create a farm-outcome metric. See
[`Documentation/ORACLE_EVALUATION_GUIDE.md`](../../Documentation/ORACLE_EVALUATION_GUIDE.md).

The completed A6 evaluation-only ablation uses this unchanged registry. It
detects all 48 coordinator-resolution fixtures but resolves 0/48 by design,
because the coordinator receives an empty conflict set. The paired A0/A6
outcomes are preserved separately in
[`results/architecture-comparison`](../../results/architecture-comparison/);
they do not modify this registry or the 300 normal scenarios.
