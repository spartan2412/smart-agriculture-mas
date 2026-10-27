# Table 6. Provenance and alignment gate evaluation

The fixture runner applies controlled single-fault mutations to otherwise valid frozen bundles. It demonstrates the gate boundary that normal 300-scenario records cannot exercise because those records are already aligned. This is software/provenance protection, not agricultural outcome validation.

| Measure | Observed | Meaning |
| --- | --- | --- |
| A0 alignment validator blocks | 50/50 | Malformed plan identity/binding rows stop before downstream agents. |
| A5 omitted-gate exposure | 50/50 | Expected evaluation-only exposure when the alignment boundary is removed. |
| Shared raw-payload hash blocks | 10/10 | The frozen loader rejects altered raw-source payloads before either workflow starts. |
| Invalid-fixture direct actions | 0 | No malformed bundle can produce a decision or direct farm action. |
