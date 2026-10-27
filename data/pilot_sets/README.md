# Frozen Local-Model Pilot Sets

`apple_gpu_30_anchor_scenarios` is the current local-model pilot population.
It has one already-admitted anchor scenario for each of the 30 final study
sites: five sites for each of the six focused crops.

It is a reproducibility selection from the frozen 300-scenario benchmark. It
does not add observations, modify any scenario, or constitute a new data
enrichment. Its manifest verifies the source anchor-manifest hash, row file
hash, and canonical scenario/site identity hash.

For the final v5.1 path, this pilot may be used only after the separate
immutable held-out relevance evaluation is executed and accepted. It is not a
replacement for that held-out evaluation and must use the exact locked 30-row
CSV; see
[`Documentation/BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](../../Documentation/BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).
