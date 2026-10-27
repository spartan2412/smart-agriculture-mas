# Provenance and Alignment Fixture Audit

- Schema version: `1.0`
- Classification: `evaluation_only_counterfactual_not_real_farm_evidence`
- Frozen registry, scenarios, enrichments, source artifacts, and normal workflow: unchanged.
- Each stored fixture contains one controlled in-memory mutation only.
- No fixture can create a farm action, be loaded by the normal scenario loader, or enter a farmer-facing run.

## Coverage

| Fault class | Cases |
| --- | ---: |
| plan_item_crop_scope_mismatch | 10 |
| plan_item_decision_date_scope_mismatch | 10 |
| plan_item_district_scope_mismatch | 10 |
| plan_item_scenario_binding_mismatch | 10 |
| plan_item_season_scope_mismatch | 10 |
| weather_payload_hash_mismatch | 10 |

| Crop | Cases |
| --- | ---: |
| rice | 10 |
| wheat | 10 |
| maize | 10 |
| chickpea | 10 |
| soybean | 10 |
| tomato | 10 |

All **30** final crop--location sites are represented exactly twice.

## Required outcomes

- A0 blocks all 50 plan-item identity/binding mismatches at the real alignment validator.
- A5 exposes those same 50 invalid bundles past its intentionally omitted alignment validator, but the evaluation runner halts there; it never calls downstream agents or creates a farmer decision.
- Both A0 and A5 block all 10 payload-hash mismatches at the shared frozen loader verifier.
- No fixture creates a direct farm action or measures agricultural correctness.

## Persisted paired result

All **60/60** expected outcomes passed. A0 blocked **50/50** plan-item
identity/binding faults at the production alignment validator; A5 exposed the
same **50/50** faults only at its evaluation boundary; and both systems blocked
the **10/10** raw-payload hash faults at the shared loader. The comparison
report records this as a separate integrity protocol in
[`results/architecture-comparison`](../../results/architecture-comparison/),
not as agricultural accuracy or normal-scenario evidence.
