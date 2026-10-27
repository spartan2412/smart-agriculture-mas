# Table 4. Final E1-v5.1 held-out bounded-LLM relevance evaluation

The 96-question source-derived held-out set was immutable and disjoint from the development contexts/sites. These measures test selection among already-admitted facts/passages; they do not measure farm outcomes.

## Per-role results

| Role | Questions | Fact P | Fact R | Safe empty | Passage P | Passage R | Plan/op. | Invalid | Fallback | Mean ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Weather context | 12 | 100.0% | 100.0% | 100.0% | — | — | — | 0.0% | 0.0% | 2146 |
| Soil context | 12 | 100.0% | 100.0% | 100.0% | — | — | — | 0.0% | 0.0% | 2136 |
| Satellite / NDVI | 12 | 100.0% | 100.0% | 100.0% | — | — | — | 0.0% | 0.0% | 2281 |
| Market evidence | 12 | 100.0% | 100.0% | 100.0% | — | — | — | 0.0% | 0.0% | 2310 |
| Fertilizer baseline | 12 | 100.0% | 100.0% | — | — | — | 100.0% | 0.0% | 0.0% | 1989 |
| Official operations RAG | 12 | 100.0% | 100.0% | — | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 2024 |
| Coordinator | 12 | 100.0% | 100.0% | — | — | — | 100.0% | 0.0% | 0.0% | 4394 |
| Farmer explanation | 12 | 83.3% | 83.3% | 100.0% | — | — | — | 0.0% | 0.0% | 2484 |

## Frozen acceptance criteria

| Measure | Observed | Threshold | Direction | Passed |
| --- | --- | --- | --- | --- |
| Fact-selection precision | 98.6% | 80.0% | minimum | True |
| Fact-selection recall | 98.6% | 80.0% | minimum | True |
| Safe-empty accuracy | 100.0% | 80.0% | minimum | True |
| Exact RAG passage precision | 100.0% | 75.0% | minimum | True |
| Exact RAG passage recall | 100.0% | 75.0% | minimum | True |
| Invalid structured-output rate | 0.0% | 2.0% | maximum | True |
| Fallback rate | 0.0% | 2.0% | maximum | True |

Overall: fact precision/recall 98.6%/98.6%; safe-empty 100.0%; invalid 0.0%; fallback 0.0%.
