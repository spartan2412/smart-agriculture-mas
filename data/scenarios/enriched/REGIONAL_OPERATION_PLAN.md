# Regional Operation Plan Enrichment

This third additive enrichment turns the frozen benchmark's verified calendar,
regional-policy, and official-action artifacts into source-linked planning
items. It does not overwrite the registry, scenario manifest, first
enrichment, second enrichment, or MAS capability contract.

## Purpose

The farmer-facing layer needs useful regional planning content instead of a
bare list of unavailable farm-specific actions. The artifacts here provide a
traceable plan structure for every frozen scenario while retaining the
distinction between:

1. a declared regional crop-calendar position;
2. a verified regional nutrient or IPM policy reference; and
3. a time-valid, source-quoted operation whose unobserved field precondition
   prevents it from becoming a direct farm instruction.

## Artifacts

| Artifact | Rows | Purpose |
| --- | ---: | --- |
| `regional_operation_plan_summary.csv` | 300 | One source-linked planning summary for every frozen `scenario_id`. |
| `regional_operation_plan_items.csv` | 1,507 | Three planning references per scenario plus every existing conditionally applicable, source-quoted operation. |
| `regional_operation_plan_provenance.csv` | 5 | Input paths, SHA-256 fingerprints, row counts, and roles used by the deterministic builder. |
| `regional_operation_plan_audit.csv` | 5 checks | Machine-readable coverage, provenance, condition, hash, and direct-action guards. |
| `REGIONAL_OPERATION_PLAN_AUDIT.md` | 1 report | Human-readable version of the same audit. |

The current item count consists of 900 baseline references (calendar,
nutrient policy, and IPM policy for all 300 scenarios) plus 607 source-quoted
conditional operation items. The 607 items occur across 229 scenarios. The
other 71 scenarios retain only the fully aligned calendar and policy plan
references until more time-valid official operations are recovered.

## Safety and interpretation

The three baseline items are useful planning context, but they are not direct
farm instructions:

- The calendar item identifies only the early, middle, or late part of a
  declared district-scale season window. It does not observe sowing date or
  crop stage.
- The nutrient item retains the verified regional policy source. It does not
  produce a farm-specific fertilizer dose without a field soil test and actual
  stage.
- The IPM item retains the verified regional crop-protection source. It does
  not assert a disease, pest threshold, registration decision, or treatment
  need.

An item with `plan_item_type` equal to
`time_valid_source_quoted_conditional_operation` is stronger: its crop,
geography, season, and source-time gates already passed in
`scenario_official_action_bindings_all.csv`. Its `missing_evidence` field
contains the exact unobserved precondition that still prevents direct action.

Every summary records
`direct_farm_action_status=not_issued_no_farm_specific_observation_or_treatment_trigger`.
This is a guard, not a failed plan: the regional planning references and
conditional official operations remain available to the future planner and
coordinator.

## Rebuild and audit

Run from the repository root:

```bash
.venv-macos/bin/python scripts/build_regional_operation_plan.py
.venv-macos/bin/python scripts/audit_regional_operation_plan.py
```

The audit fails if an item is missing, duplicated, detached from its source
hash or binding, promoted to a direct action, or changed without updating its
canonical SHA-256.

## Next expansion

This layer deliberately does not use a future policy document as a historical
advisory. To raise the number of source-quoted operations beyond the current
229 scenarios, new records must come from public official documents whose
crop, regional scope, and publication/effective window are demonstrably
valid for the scenario date. Each new record must be quoted, hash-linked,
bound across all 300 scenarios, and admitted by the same audit.
