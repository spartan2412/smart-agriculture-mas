# Missing-Evidence Recovery Feasibility

This is an additive recovery layer. It does not alter the frozen 300-scenario
manifest, original selected Sentinel items, original Agmarknet reports, or
their hashes.

## Sentinel representative-cell context

The base layer had 14 satellite NDVI abstentions: four coordinates outside the
original selected asset and ten non-clear/non-land SCL pixels.

`recover_sentinel_ndvi_context.py` inspected only quality-gated candidates
already present in each scenario's original, frozen same-month STAC response.
It uses a deterministic order of scene cloud cover, nodata percentage, and
timestamp, admitting the first candidate that contains the exact coordinate
and has clear SCL 4 or 5. NDVI is calculated only after selection and is never
used to choose a candidate.

| Outcome | Count | Meaning |
| --- | ---: | --- |
| Recovered | 6 | A clear, contained alternate candidate existed in the original frozen source window. |
| Still abstained | 8 | No candidate in that exact source window was both contained and clear. |

The resulting MAS satellite context is 292/300: 286 from the original frozen
item and 6 from this recovery layer. The remaining eight records retain
`abstain_exact_frozen_scene_or_pixel_context_unavailable`.

## Strict Agmarknet market recovery

The seven market abstentions were retried against the three calendar months
strictly preceding each scenario, using the same official crop commodity,
state, and district query identity. All 21 returned reports were source-valid,
but none contained a reported price for its requested month.

| Outcome | Count | Meaning |
| --- | ---: | --- |
| Recoverable same-district historical trend | 0 | No scenario had two earlier reported-price months. |
| Confirmed no-price period | 7 | All three strict prior reports had an empty requested price column. |

No nearby mandi, state average, alternate crop commodity, future price, or
estimated value is used. These seven market contexts remain abstentions.

## Evidence artifacts

- `sentinel_ndvi_recovery_manifest.csv`, `sentinel_ndvi_recovery_features.csv`, and `sentinel_ndvi_recovery_status.csv`
- `market_recovery_feasibility.csv`
- Raw recovery responses under `raw/sentinel_ndvi_recovery/` and `raw/agmarknet_market_recovery/`
- `enrichment_audit.csv` and [ENRICHMENT_AUDIT.md](ENRICHMENT_AUDIT.md)
