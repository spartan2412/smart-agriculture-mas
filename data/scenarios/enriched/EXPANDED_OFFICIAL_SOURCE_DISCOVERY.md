# Expanded Official Source Discovery

This is the discovery ledger for the additional official RAG sources. It is
deliberately separate from the admitted corpus: finding an official web page
does not make it usable evidence. A source is added only after its exact scope,
date semantics, raw bytes, and reproducible hash meet the applicable gate.

The machine-readable ledger is
[`official_source_expansion_discovery.csv`](official_source_expansion_discovery.csv).

## Included official families

- [ICAR–Indian Institute of Soybean Research](https://icar-nsri.res.in/)
  archived weekly soybean advisory pages for 2021–2024 provided dated source
  candidates. The archive response is frozen in
  `raw/expanded_official_source_discovery/`. An individual PDF enters the
  corpus only if its own text verifies soybean and Central-Zone/Madhya
  Pradesh/Rajasthan scope.
- [ICAR–CRIDA Crop Contingency Plans](https://icar-crida.res.in/CCP/) already
  supplied exact, publicly retrievable, hash-verified documents for the final
  site registry. Their crop-profile, sowing-window, and contingency documents
  are included strictly as historical district context.
- Public Internet Archive preservation replays of the official PAU package
  URLs supplied six independently checked annual documents: Kharif 2023–2025
  for Punjab rice and Rabi 2021–22/2023–24/2024–25 for Punjab wheat. They are not
  inserted into the generic RAG corpus. Instead, page-quoted operations, raw
  hashes, original/replay URLs, publication evidence, and full 300-scenario
  scope matrices are retained in `archived_pau_*_source_inventory.csv` and
  their dedicated action-recovery audits.
- [Mahatma Phule Krishi Vidyapeeth, Rahuri](https://mpkv.ac.in/Extension/ExtensionPublication)
  publishes *Krishi Darshani* as an annual crop-production-technology guide
  for Maharashtra. The dated [2023 guide](https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf)
  is admitted only as state-level technical guidance from 7 June 2023 onward.
  Its source PDF, cited statewide-scope and chickpea-operation page rasters,
  visual transcription, full scope matrix, and independent audit are retained
  in the `mpkv_chickpea_*` artifacts. It is not inserted as a weekly or
  district advisory.

## Explicitly not added

- Direct historical [Punjab Agricultural University](https://www.pau.edu/)
  filenames may still return HTTP 404 because PAU overwrites annual package
  URLs. A current PAU document is never retroactively substituted. Only the
  separately audited public preservation replays above are admitted.
- A Wayback CDX query for the historical TNAU maize fall-armyworm and tomato
  fruit-borer extension-page URLs returned no preserved captures. No undated
  TNAU page is backdated to cover the pre-2023 maize scenarios.
- The IISR weekly PDFs aligned to remaining June/September 2022 and June 2023
  scenario dates remain excluded because their own text did not verify the
  Central-Zone/Madhya Pradesh/Rajasthan scope required by this benchmark.
- The [IMD GKMS portal](https://agromet.imd.gov.in/) returned an anonymous
  sign-in form. No dated district advisory was invented or inferred from a
  state/zone source.
- The [ICAR KVK portal](https://kvk.icar.gov.in/) was not publicly reachable
  from this collection environment. The resulting access outcome and the
  300-scenario no-claim status are in
  [PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md](PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md).
- Documents with ambiguous archive dates, duplicate archive URLs, unverified
  geographic scope, changed raw bytes, or failed retrieval remain excluded.
  Their reasons are preserved in
  `expanded_official_rag_source_rejections.csv` and
  `expanded_official_rag_source_inventory.csv`.

These exclusions are a research strength: they keep the final RAG layer
auditable and prevent a general online recommendation from being misrepresented
as a decision-time, district-specific agricultural instruction.
