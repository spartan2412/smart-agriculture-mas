# Official Action and RAG Enrichment
Generated: 2026-09-26T16:29:12+00:00
- Hash-verified official source documents in chunk corpus: 14
- Verbatim, source-checked operation records: 18
- Scenario × operation applicability rows: 5400
- Scenario × document metadata-scope rows: 4200

## Expanded official source layer

The canonical integration view is now `official_rag_corpus_catalog.csv`,
`official_rag_corpus_all_chunks.csv`, and
`scenario_official_rag_scope_all.csv`. It combines the original 14
hash-verified action-RAG documents with 78 additional public official
documents: 27 dated ICAR–Indian Institute of Soybean Research weekly advisory
documents and 51 ICAR–CRIDA final-site district documents. The combined corpus
therefore contains 92 sources, 4,582 chunks, and 27,600 scenario × source
metadata-scope rows.

The two added source families have deliberately different permissions:

- ICAR–IISR weekly soybean advisory PDFs may be retrieved only when crop,
  Central-Zone state, and exact dated issue week all match. This produced 9
  valid dated-advisory scenario bindings.
- ICAR–CRIDA crop-profile, sowing-window, and contingency PDFs are old,
  district-specific background context. They may be retrieved only for their
  exact crop and district (670 valid bindings), but are never current advice,
  farm-specific instructions, or structured operations.

The expanded collector started from 120 candidates. It admitted 78 only after
their raw source bytes and extracted text were hashed and checked. Forty-one
weekly PDFs whose extracted text did not state the required Central-Zone or
Madhya Pradesh/Rajasthan scope, and one unavailable source URL, were excluded
rather than being inferred into the corpus. Four malformed or ambiguous archive
links are recorded separately in
`expanded_official_rag_source_rejections.csv`.

Exact source URLs, raw paths, hashes, periods, restrictions, and admission
statuses are in `official_rag_corpus_catalog.csv`; the two underlying
inventories remain available as `official_rag_source_inventory.csv` and
`expanded_official_rag_source_inventory.csv`. The integrity report is
[EXPANDED_OFFICIAL_RAG_AUDIT.md](EXPANDED_OFFICIAL_RAG_AUDIT.md).

## Relationship to the fourth enrichment

This document describes the generic official corpus and the source-scoped
crop-operation path only. The fourth enrichment is intentionally not appended
to the 92-document generic corpus. Its 14 source-quoted post-harvest passages
are admitted through a separate exact-crop allow-list in
`scenario_postharvest_rag_scope.csv`; the active RAG agent labels them as the
`postharvest_exact_crop` corpus layer. This prevents a handling passage for one
crop from being retrieved for another crop and prevents facility, warehouse,
or static-route context from being presented as an operational instruction.

See [POSTHARVEST_LOGISTICS_ENRICHMENT.md](POSTHARVEST_LOGISTICS_ENRICHMENT.md)
and [POSTHARVEST_LOGISTICS_AUDIT.md](POSTHARVEST_LOGISTICS_AUDIT.md) for the
source and scope contract.

## Exact-week action extraction

Two of the admitted IISR weekly PDFs match nine scenario decision dates
exactly: 25 September-1 October 2023 and 24-30 June 2024. Their visually
reviewed, source-quoted operations are stored in
`exact_week_iisr_action_records.csv`. The rows include harvest, post-harvest,
drainage, sowing, spacing, planting-system, nutrient-timing, organic seed
treatment, and intercrop operations, plus a crop-protection guardrail.

Every operation is bound against all 300 scenarios in
`scenario_exact_week_iisr_action_bindings.csv`. Only 57 pairs pass the
source's crop, Central-Zone state, season, and exact-week gates. All 57 remain
conditional because the frozen scenario does not contain its required field
facts; zero rows become automatic farm actions. The normalized MAS-ready action
view is `official_action_records_all.csv` with
`scenario_official_action_bindings_all.csv`.

## Safety and temporal rules
- A source quote must be found in its recorded official page before an action record is written.
- Named weekly, seasonal, and package-of-practice documents have explicit effective end dates. A later scenario cannot retrieve them as a current source.
- `conditionally_applicable_pending_unobserved_farm_condition` is not an instruction. It records a relevant official operation whose real farm precondition is absent from the frozen benchmark.
- CIBRC/PPQS documents are retained as regulatory context and are never used as treatment recommendations.
- The added ICAR–CRIDA documents are historical district context, not current
  advisory evidence. The added IISR documents do not bypass their exact-week
  time gate.
