"""Collect auditable regional nutrient and crop-protection evidence.

This registry layer deliberately records a *regional baseline*, never a
field-specific prescription.  Every numeric management record is linked to a
dated, public, first-party source.  A crop-protection action is retained only
when the regional source and a current PPQS/CIBRC Major Uses record agree on
the crop, diagnosed problem, active ingredient, and formulation.  When their
rates use comparable units, the curated row also records the rate-alignment
check; an incomparable rate is never labelled exact.

The script does not scrape a portal for a generic answer and apply it to every
district.  Its coverage table makes geography mismatches and source gaps
explicit.  In particular, an official document that is not machine-readable,
undated, or outside a location's scope remains blocked.

Run from the repository root:

    python scripts/collect_regional_management_evidence.py
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import requests
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUEST_HEADERS = {
    "User-Agent": "SmartAgricultureMAS/1.0 regional-management-evidence",
    "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.1",
}


class TextExtractor(HTMLParser):
    """Small dependency-free HTML-to-text extractor for source checks."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return " ".join(self.parts)


@dataclass(frozen=True)
class SourceSpec:
    source_document_id: str
    source_title: str
    provider: str
    geography_scope: str
    crop_scope: str
    management_scope: str
    official_url: str
    expected_issue_date: str
    required_terms: Sequence[str]
    issue_date_terms: Sequence[str] = ()
    # Some official legacy PDFs record their version date only in the PDF
    # document metadata.  This is accepted only when the exact expected
    # YYYYMMDD token is declared here and is written explicitly to the source
    # snapshot; it is never inferred from an HTTP retrieval timestamp.
    metadata_date_expected: str = ""
    title_conflict_term: str = ""
    source_class: str = "regional_policy"
    extract_page_numbers: Sequence[int] = ()


@dataclass(frozen=True)
class PolicySpec:
    policy_id: str
    site_id: str
    crop: str
    season: str
    policy_domain: str
    policy_kind: str
    trigger_or_scope: str
    regional_management_record: str
    source_document_id: str
    source_locator: str
    ppqs_source_document_id: str = ""
    ppqs_locator: str = ""
    ppqs_required_terms: Sequence[str] = ()
    ppqs_rate_record: str = ""
    dose_alignment_status: str = "not_applicable"
    safety_note: str = (
        "Research registry evidence only; not a farm-specific recommendation. "
        "A field deployment needs current local diagnosis, label compliance, and "
        "qualified extension review."
    )


# These are deliberately few and tightly scoped.  A source must be official,
# crop-specific, readable, dated, and geographically compatible before it can
# move a site out of a management-evidence gap.
SOURCES: Sequence[SourceSpec] = (
    SourceSpec(
        "PAU_KHARIF_2026",
        "Package of Practices for Crops of Punjab — Kharif 2026",
        "Punjab Agricultural University",
        "Punjab state",
        "rice",
        "fertilizer;crop_protection",
        "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf",
        "March 2026",
        ("Kharif 2026", "RICE"),
    ),
    SourceSpec(
        "PAU_RABI_2025_26",
        "Package of Practices for Crops of Punjab — Rabi 2025–26",
        "Punjab Agricultural University",
        "Punjab state",
        "wheat",
        "fertilizer;crop_protection",
        "https://pau.edu/content/ccil/pf/pp_rabi.pdf",
        "August 2025",
        ("PACKAGE OF PRACTICES FOR CROPS OF PUNJAB", "Rabi 2025-26", "WHEAT"),
    ),
    SourceSpec(
        "TNAU_RICE_NUTRIENT_2023",
        "TNAU Agritech rice nutrient management — inorganic fertilizers",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu; includes a Cauvery delta tract distinction",
        "rice",
        "fertilizer",
        "https://agritech.tnau.ac.in/agriculture/agri_main_feild_%20InOrganic_biofertilizers_Rice.html",
        "January 2023",
        ("Nutrient Management :: Rice", "Cauvery delta", "Updated on Jan 2023"),
        ("Updated on Jan 2023",),
    ),
    SourceSpec(
        "TNAU_RICE_PROTECTION_INDEX_2023",
        "TNAU Agritech rice crop-protection index",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu",
        "rice",
        "crop_protection",
        "https://agritech.tnau.ac.in/agriculture/crop_prot_rice%20crop.html",
        "January 2023",
        ("Crop Protection", "Pests of Rice", "Diseases of Rice", "Updated on Jan 2023"),
        ("Updated on Jan 2023",),
    ),
    SourceSpec(
        "TNAU_TOMATO_NUTRIENT_2023",
        "TNAU Agritech tomato irrigation and manuring page",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu",
        "tomato",
        "fertilizer",
        "https://agritech.tnau.ac.in/horticulture/horti_vegetables_tomato_irrigation.html",
        "June 2023",
        ("Tomato field", "STCR-IPNS", "Updated on Jun, 2023"),
        ("Updated on Jun, 2023",),
        # The page is linked from the Tomato index and says "tomato field",
        # but its visible heading says Chilli.  Do not promote its numbers to
        # a verified tomato baseline without a manual first-party correction.
        title_conflict_term="Chilli",
    ),
    SourceSpec(
        "TNAU_TOMATO_FERTIGATION_2014",
        "TNAU tomato fertigation schedule for hybrids",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu; hybrid tomato under the documented drip-fertigation system",
        "tomato",
        "fertilizer;fertigation",
        "https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf",
        "29.10.2014",
        ("Tomato - Fertigation", "nutrient requirement for hybrids is 200:250:250 kg of NPK per ha"),
        metadata_date_expected="20141029",
    ),
    SourceSpec(
        "TNAU_TOMATO_FRUIT_BORER_2023",
        "TNAU Agritech tomato fruit-borer integrated management",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu",
        "tomato",
        "crop_protection",
        "https://agritech.tnau.ac.in/crop_protection/tomato/tomato_1.html",
        "June 2023",
        ("Fruit Borer", "Helicoverpa armigera", "Chlorantraniliprole 18.5 SC", "Updated on Jun, 2023"),
        ("Updated on Jun, 2023",),
    ),
    SourceSpec(
        "TNAU_TOMATO_EARLY_BLIGHT_2023",
        "TNAU Agritech tomato early-blight integrated disease management",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu",
        "tomato",
        "crop_protection",
        "https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html",
        "June 2023",
        ("Early Blight", "Alternaria solani", "Azoxystrobin 18.2%+Difenoconazole 11.4% SC", "Updated on Jun 2023"),
        ("Updated on Jun 2023",),
    ),
    SourceSpec(
        "TNAU_MAIZE_FAW_2023",
        "TNAU fall-armyworm management in maize",
        "Tamil Nadu Agricultural University",
        "Tamil Nadu",
        "maize",
        "crop_protection;IPM",
        "https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html",
        "May 2023",
        ("Fall armyworm", "Chlorantraniliprole 18.5 SC", "200ml/ha", "Updated on May 2023"),
        ("Updated on May 2023",),
    ),
    SourceSpec(
        "UASD_NORTH_KARNATAKA_POP_2023",
        "UAS Dharwad Package of Practices Agriculture 2023 landing page",
        "University of Agricultural Sciences Dharwad",
        "North Karnataka agricultural zones only",
        "cereals;pulses;oilseeds",
        "fertilizer;crop_protection",
        "https://sites.google.com/a/uasd.in/pop/pop-agriculture",
        "2023",
        ("Package of Practices", "PoP Agriculture", "2023"),
        source_class="official_source_locator",
    ),
    SourceSpec(
        "ODISHA_EXPERT_COMMITTEE_2021_22",
        "Odisha Expert Committee Recommendations 2021–22",
        "Department of Agriculture & Farmers' Empowerment, Government of Odisha",
        "Odisha state; prepared with OUAT, NRRI, CHES and Central IPM Centre contributors",
        "rice;maize;other Odisha crops",
        "crop_protection;micronutrients;biofertilizers",
        "https://agri.odisha.gov.in/sites/default/files/2022-04/EXPERT%20COMMITTEE%20RECOMMENDATIONS_2021-22.pdf",
        "2021–22",
        ("Expert Committee Recommendations 2021-22", "PADDY", "FLONICAMID 50% WG"),
        ("Expert Committee Recommendations 2021-22",),
    ),
    SourceSpec(
        "ICAR_IISR_SOYBEAN_BULLETIN_2023",
        "Improved Technologies and Recommendations for Maximizing Soybean Productivity",
        "ICAR–Indian Institute of Soybean Research",
        "AICRP soybean Central Zone: Madhya Pradesh, Bundelkhand Uttar Pradesh, Rajasthan, Gujarat and north-west Maharashtra",
        "soybean",
        "fertilizer;crop_protection;IPM",
        "https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf",
        "2023",
        ("Extension Bulletin 18(2023) English Edition", "Central Zone: Madhya Pradesh", "Chlorantraniliprole 18.5 SC"),
        ("Extension Bulletin 18(2023) English Edition",),
    ),
    SourceSpec(
        "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024",
        "ICAR-IISR weekly advisory for soybean farmers, 1–7 July 2024",
        "ICAR–Indian Institute of Soybean Research",
        "Central soybean zone; applied only to registered Madhya Pradesh and Rajasthan sites",
        "soybean",
        "fertilizer;crop_establishment",
        "https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf",
        "01.07.2024",
        ("Weekly Advisory for Soybean Farmers", "central zone", "25:60:40:20"),
        ("Date: 01.07.2024",),
    ),
    SourceSpec(
        "ICAR_KHARIF_STATE_ADVISORIES_2025",
        "ICAR Kharif Agro-Advisories for Farmers 2025",
        "Indian Council of Agricultural Research",
        "State-specific chapters; this registry uses only the Haryana & Delhi, Karnataka, Maharashtra and Rajasthan chapters for compatible kharif sites",
        "rice;maize;soybean;other kharif crops",
        "fertilizer;crop_protection;crop_establishment",
        "https://icar.org.in/sites/default/files/Circulars/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf",
        "May 2025",
        ("ICAR Kharif Agro-Advisory 2025", "May 2025", "Haryana & Delhi", "Karnataka", "Maharashtra", "Rajasthan"),
        ("May 2025",),
        extract_page_numbers=(4, 78, 126, 128, 158, 228),
    ),
    SourceSpec(
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "ICAR Rabi Agro-Advisory for Farmers 2021–22",
        "Indian Council of Agricultural Research",
        "State-specific chapters; this registry uses only the Haryana & Delhi, Uttar Pradesh, Madhya Pradesh, Maharashtra, Karnataka and Tamil Nadu & Puducherry chapters for compatible rabi sites",
        "wheat;chickpea;maize;tomato;other rabi crops",
        "fertilizer;crop_protection;crop_establishment",
        "https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf",
        "September 2021",
        ("ICAR Rabi Agro Advisory for Farmers", "September 2021", "HARYANA", "UTTAR PRADESH", "MAHARASHTRA", "MADHYA PRADESH", "KARNATAKA", "TAMIL NADU", "Maize", "Tomato"),
        ("September 2021",),
        extract_page_numbers=(3, 126, 129, 131, 134, 139, 148, 315, 331, 332, 388, 390, 394, 395, 404, 415),
    ),
    SourceSpec(
        "CIBRC_INSECTICIDE_2026",
        "CIBRC Major Uses of Pesticides — chemical insecticides",
        "PPQS / Central Insecticides Board and Registration Committee",
        "India national regulatory record",
        "registered crops",
        "crop_protection_registration",
        "https://ppqs.gov.in/sites/default/files/updated_mup_insecticide_as_on_31.03.2026_c.pdf",
        "31.03.2026",
        ("Thiamethoxam", "Chlorantraniliprole", "Rice"),
        source_class="national_regulatory_record",
    ),
    SourceSpec(
        "CIBRC_FUNGICIDE_2026",
        "CIBRC Major Uses of Pesticides — chemical fungicides",
        "PPQS / Central Insecticides Board and Registration Committee",
        "India national regulatory record",
        "registered crops",
        "crop_protection_registration",
        "https://ppqs.gov.in/sites/default/files/2._chemical_mup_fungicide_as_on_31.03.2026_0.pdf",
        "31.03.2026",
        ("Propiconazole", "Wheat", "Rice"),
        ("31/03/2026",),
        source_class="national_regulatory_record",
    ),
)


POLICIES: Sequence[PolicySpec] = (
    PolicySpec(
        "PAU_RICE_2026_BLANKET_NPK",
        "IN_PB_LUDHIANA_RICE_KHARIF",
        "rice",
        "kharif",
        "fertilizer",
        "regional_blanket_baseline",
        "Punjab PAU rice; only when a field soil-test result is unavailable. PAU further restricts P and K to documented soil-test deficiency and says to skip P after recommended P to preceding wheat.",
        "For PAU rice varieties other than PR 132: N 42, P2O5 12, K2O 12 kg/acre; cited fertilizer equivalents are neem-coated urea 90 kg, DAP 27 kg or single superphosphate 75 kg, and MOP 20 kg/acre. Apply N in three equal splits: within 7 days of transplanting, 21 DAT, then 35 DAT for PR 126 or 42 DAT for other varieties.",
        "PAU_KHARIF_2026",
        "PDF p. 10 (printed page 10)",
    ),
    PolicySpec(
        "PAU_RICE_2026_STEM_BORER_ETL",
        "IN_PB_LUDHIANA_RICE_KHARIF",
        "rice",
        "kharif",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Rice stem borer; apply only when PAU's economic threshold of more than 5% dead hearts is reached. PAU lists a neem-based option and chemical alternatives; this row records one regulatory cross-checked option, not a default spray.",
        "Chlorantraniliprole 18.5% SC: PAU lists 60 mL/acre in 100 L water, with repeat only when damage again reaches the threshold. PPQS current Major Uses record lists rice stem borer and leaf folder for chlorantraniliprole 18.5% SC.",
        "PAU_KHARIF_2026",
        "PDF pp. 14–15 (printed pp. 14–15)",
        "CIBRC_INSECTICIDE_2026",
        "PDF p. 12: Rice—stem borer/leaf folder—chlorantraniliprole 18.5% SC",
        ("Chlorantraniliprole 18.50% SC", "Rice", "Stem borer"),
        "PPQS: 150 mL/ha in 500 L water; PAU: 60 mL/acre (approximately 148 mL/ha).",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "PAU_RICE_2026_SHEATH_BLIGHT",
        "IN_PB_LUDHIANA_RICE_KHARIF",
        "rice",
        "kharif",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Rice sheath blight at maximum tillering to boot stage, as soon as disease appears. PAU first specifies residue/bund management and avoiding excessive N; this row records one PPQS-cross-checked chemical option.",
        "Propiconazole 25% EC: PAU lists 200 mL/acre in 200 L water and a second spray 15 days later when required. PPQS current Major Uses record lists rice sheath blight for propiconazole 25% EC.",
        "PAU_KHARIF_2026",
        "PDF p. 17 (printed page 17)",
        "CIBRC_FUNGICIDE_2026",
        "PDF p. 24: Rice—sheath blight—propiconazole 25% EC",
        ("Propiconazole 25% EC", "Rice (Paddy)", "Sheath blight"),
        "PPQS: 500 mL/ha in 750 L water; PAU: 200 mL/acre (approximately 494 mL/ha).",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "PAU_WHEAT_2025_26_BLANKET_NPK",
        "IN_PB_LUDHIANA_WHEAT_RABI",
        "wheat",
        "rabi",
        "fertilizer",
        "regional_blanket_baseline",
        "Punjab medium-fertility wheat soil; only when a field soil-test result is unavailable. Potassium remains conditional on a documented low-K soil test.",
        "N 50 and P2O5 25 kg/acre; cited equivalents are neem-coated urea 110 kg and DAP 55 kg or single superphosphate 155 kg/acre. K2O is only for low-K soil: 12 kg/acre (20 kg MOP); PAU specifies 24 kg K2O/acre in Gurdaspur, Hoshiarpur, Rupnagar and SBS Nagar. Drill P and any K at sowing; apply urea at first and second irrigation as stated in the source.",
        "PAU_RABI_2025_26",
        "PDF pp. 9–10 (printed pp. 9–10)",
    ),
    PolicySpec(
        "PAU_WHEAT_2025_26_YELLOW_RUST",
        "IN_PB_LUDHIANA_WHEAT_RABI",
        "wheat",
        "rabi",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Confirmed yellow/stripe rust. PAU requires resistant varieties, monitoring from the second week of December, and initial spot treatment surrounding the infection; this row records one PPQS-cross-checked option.",
        "Propiconazole 25% EC: PAU lists 200 mL/acre in 200 L water as soon as disease is noticed, initially around infected patches; repeat only as needed. PPQS current Major Uses record lists wheat stripe/yellow rust for propiconazole 25% EC.",
        "PAU_RABI_2025_26",
        "PDF pp. 19–20 (printed pp. 19–20)",
        "CIBRC_FUNGICIDE_2026",
        "PDF p. 24: Wheat—stripe/yellow rust—propiconazole 25% EC",
        ("Propiconazole 25% EC", "Wheat", "Stripe rust"),
        "PPQS: 500 mL/ha in 750 L water; PAU: 200 mL/acre (approximately 494 mL/ha).",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "TNAU_RICE_2023_WET_SEASON_NPK",
        "IN_TN_THANJAVUR_RICE_SAMBA",
        "rice",
        "samba",
        "fertilizer",
        "regional_blanket_baseline",
        "TNAU wet-season medium- and long-duration rice baseline. The site is in Tamil Nadu; the source explicitly distinguishes the Cauvery delta tract for short-duration dry-season rice. This must not be converted into a farm dose without crop duration, soil test, and water-management context.",
        "For medium- and long-duration wet-season rice: N:P2O5:K2O = 150:50:50 kg/ha. Apply N and K in four equal splits (basal, tillering, panicle initiation, heading); apply P as basal. The source prioritises STCR-IPNS, LCC, and SSNM over blanket values where available.",
        "TNAU_RICE_NUTRIENT_2023",
        "HTML page, section ‘Main Field Application of Inorganic Fertilizers’",
    ),
    PolicySpec(
        "TNAU_TOMATO_2014_HYBRID_FERTIGATION",
        "IN_TN_KRISHNAGIRI_TOMATO_RABI",
        "tomato",
        "rabi",
        "fertilizer",
        "regional_conditional_baseline",
        "Tamil Nadu tomato hybrid only, under the source's drip-fertigation system. Record hybrid status and irrigation method before use; this dated regional schedule is not a field soil-test substitute or a current-season advisory.",
        "For hybrid tomato, total N:P2O5:K2O = 200:250:250 kg/ha. Apply 75% P2O5 (187.5 kg/ha, stated as 1,172 kg superphosphate) as basal. Fertigate the remaining N:P2O5:K2O = 200:62.5:250 kg/ha once every three days across four source stages: transplanting–establishment (10 days), flower initiation–flowering (30), flowering–fruit set (30), and alternate days from picking (80).",
        "TNAU_TOMATO_FERTIGATION_2014",
        "PDF p. 1, ‘Tomato - Fertigation’ schedule; official PDF metadata creation/modification date 2014-10-29",
    ),
    PolicySpec(
        "TNAU_TOMATO_2023_FRUIT_BORER",
        "IN_TN_KRISHNAGIRI_TOMATO_RABI",
        "tomato",
        "rabi",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Confirmed tomato fruit borer (Helicoverpa armigera). TNAU requires fruit/larva removal, trap and biological-control measures before listing chemical alternatives; this row records one PPQS-cross-checked option.",
        "Chlorantraniliprole 18.5% SC: TNAU lists 3 mL/10 L. PPQS current Major Uses record lists tomato fruit borer for chlorantraniliprole 18.5% SC. Retain the complete TNAU IPM bundle in any experimental comparison.",
        "TNAU_TOMATO_FRUIT_BORER_2023",
        "HTML page, Fruit Borer—Management table",
        "CIBRC_INSECTICIDE_2026",
        "PDF p. 12: Tomato—fruit borer—chlorantraniliprole 18.5% SC",
        ("Chlorantraniliprole 18.50% SC", "Tomato", "Fruit borer"),
        "PPQS: 150 mL/ha in 500 L water; TNAU gives 3 mL/10 L but does not state treated area/water volume per hectare.",
        "source_rate_not_comparable_to_PPQS_area_rate",
    ),
    PolicySpec(
        "TNAU_TOMATO_2023_EARLY_BLIGHT",
        "IN_TN_KRISHNAGIRI_TOMATO_RABI",
        "tomato",
        "rabi",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Confirmed tomato early blight (Alternaria solani). TNAU requires crop-debris removal, rotation, and seed treatment; this row records one PPQS-cross-checked chemical option.",
        "Azoxystrobin 18.2% + difenoconazole 11.4% SC: TNAU lists 200 mL/acre. PPQS current Major Uses record lists tomato early and late blight for the same formulation.",
        "TNAU_TOMATO_EARLY_BLIGHT_2023",
        "HTML page, Early Blight—Integrated Disease Management",
        "CIBRC_FUNGICIDE_2026",
        "PDF p. 45: Tomato—early/late blight—azoxystrobin 18.2% + difenoconazole 11.4% SC",
        ("Azoxystrobin 18.2% + Difenoconazole 11.4%", "Tomato", "Early blight"),
        "PPQS: 1 mL/L in 500 L water/ha (500 mL/ha); TNAU: 200 mL/acre (approximately 494 mL/ha).",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "ODISHA_RICE_2021_22_BPH_FLONICAMID",
        "IN_OD_CUTTACK_RICE_KHARIF",
        "rice",
        "kharif",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Confirmed brown plant hopper (BPH), white-backed plant hopper (WBPH), or green leaf hopper (GLH) in the Odisha rice crop. The Odisha state expert document is a crop–pest table, so it is not a calendar spray instruction.",
        "Flonicamid 50% WG: 150 g formulation/ha in 500 L water as a foliar spray. The state document identifies this option for paddy BPH/WBPH/GLH; the current PPQS Major Uses record lists the same formulation for rice BPH, at the same dose and water volume.",
        "ODISHA_EXPERT_COMMITTEE_2021_22",
        "PDF p. 20 (printed p. 13), PADDY—BPH/WBPH/GLH row",
        "CIBRC_INSECTICIDE_2026",
        "PDF p. 32: Rice—brown/white-backed/green leaf hopper—flonicamid 50% WG",
        ("Flonicamid 50%WG", "Rice", "Brown plant hopper"),
        "PPQS: 150 g/ha in 500 L water; Odisha: 150 g/ha in 500 L water.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    *(
        PolicySpec(
            f"ICAR_IISR_SOYBEAN_2024_CENTRAL_NPK_{site_id.rsplit('_', 3)[1]}",
            site_id,
            "soybean",
            "kharif",
            "fertilizer",
            "regional_blanket_baseline",
            "ICAR-IISR Central Zone soybean baseline for the registered Madhya Pradesh or Rajasthan location; apply only at sowing, not as a replacement for a field soil test or a nutrient plan for another soybean zone.",
            "N:P2O5:K2O:S = 25:60:40:20 kg/ha, all at sowing. The dated advisory gives central-zone source combinations: 56 kg urea + 375–400 kg SSP + 67 kg MOP; or 140 kg DAP + 67 kg MOP + 25 kg bentonite sulphur; or 200 kg 12:32:16 + 25 kg bentonite sulphur per hectare. Use a seed-cum-fertilizer drill or broadcast before sowing; do not mix fertilizer with seed.",
            "ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024",
            "PDF p. 2, item 7",
        )
        for site_id in (
            "IN_MP_INDORE_SOYBEAN_KHARIF",
            "IN_MP_UJJAIN_SOYBEAN_KHARIF",
            "IN_RJ_JHALAWAR_SOYBEAN_KHARIF",
        )
    ),
    *(
        PolicySpec(
            f"ICAR_IISR_SOYBEAN_2023_DEFOLIATOR_ETL_{site_id.rsplit('_', 3)[1]}",
            site_id,
            "soybean",
            "kharif",
            "crop_protection",
            "diagnosis_triggered_IPM_chemical_option",
            "Soybean defoliators at ICAR-IISR's economic threshold: green semilooper at 4 larvae/m row at flowering or 3 larvae/m at podding; tobacco caterpillar at 10 larvae/m before flowering. The source requires IPM and warns against chemical use below the threshold.",
            "Chlorantraniliprole 18.5% SC: 150 mL/ha. ICAR-IISR lists it for soybean defoliators; the current PPQS Major Uses record lists the same formulation for soybean green semilooper and tobacco caterpillar at 150 mL/ha.",
            "ICAR_IISR_SOYBEAN_BULLETIN_2023",
            "PDF pp. 47 and 49 (printed pp. 44 and 46), Tables 6 and 8",
            "CIBRC_INSECTICIDE_2026",
            "PDF p. 12: Soybean—green semilooper/stem fly/girdle beetle/tobacco caterpillar—chlorantraniliprole 18.5% SC",
            ("Chlorantraniliprole 18.50% SC", "Soybean", "Green Semi looper"),
            "PPQS: 150 mL/ha in 500–750 L water; ICAR-IISR: 150 mL/ha.",
            "regional_and_PPQS_rates_align_after_unit_conversion",
        )
        for site_id in (
            "IN_MP_INDORE_SOYBEAN_KHARIF",
            "IN_MP_UJJAIN_SOYBEAN_KHARIF",
            "IN_RJ_JHALAWAR_SOYBEAN_KHARIF",
        )
    ),
    PolicySpec(
        "ICAR_HARYANA_RICE_2025_CONDITIONAL_NPK",
        "IN_HR_KARNAL_RICE_KHARIF",
        "rice",
        "kharif",
        "fertilizer",
        "regional_blanket_baseline",
        "Haryana state rice baseline, conditional on crop duration and variety group; use the declared branch only after the experiment records the cultivar/duration. It is not a field-specific substitute for a soil test.",
        "Apply 15 t FYM/ha before transplanting. For medium-, mid-early and hybrid rice: N 150, P2O5 60, K2O 60 kg/ha plus ZnSO4 25 kg/ha. For early-duration varieties: N 120, P2O5 60, K2O 60 kg/ha plus ZnSO4 25 kg/ha. Apply one-third N and all P, K and zinc at puddling; apply remaining N in equal splits at 3 and 6 weeks after transplanting.",
        "ICAR_KHARIF_STATE_ADVISORIES_2025",
        "PDF p. 78 (printed p. 63), Haryana & Delhi—rice manure and fertilizer management",
    ),
    PolicySpec(
        "ICAR_HARYANA_RICE_2025_STEM_BORER",
        "IN_HR_KARNAL_RICE_KHARIF",
        "rice",
        "kharif",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Confirmed rice stem borer or leaf folder in the Haryana rice crop. The source lists crop protection options; this registry records one current PPQS-cross-checked option rather than a routine calendar spray.",
        "Chlorantraniliprole 18.5% SC: 150 mL/ha for rice stem borer and leaf folder. The current PPQS Major Uses record lists the same crop, problems, formulation and dose.",
        "ICAR_KHARIF_STATE_ADVISORIES_2025",
        "PDF p. 78 (printed p. 63), Haryana & Delhi—rice plant protection",
        "CIBRC_INSECTICIDE_2026",
        "PDF p. 12: Rice—stem borer/leaf folder—chlorantraniliprole 18.5% SC",
        ("Chlorantraniliprole 18.50% SC", "Rice", "Stem borer"),
        "PPQS: 150 mL/ha in 500 L water; ICAR Haryana chapter: 150 mL/ha.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    *(
        PolicySpec(
            f"ICAR_MAHARASHTRA_SOYBEAN_2025_NPK_{label}",
            site_id,
            "soybean",
            "kharif",
            "fertilizer",
            "regional_blanket_baseline",
            "Maharashtra soybean nutrient baseline at sowing. It is regional guidance only; retain the site soil-test status and do not promote it as a farm-specific dose.",
            "N:P2O5:K2O:S = 25:60:40:20 kg/ha, using the cited state-source combination of 56 kg urea + 375 kg SSP + 67 kg MOP per hectare. The same section specifies sowing from 20 June to 5 July, 65 kg seed/ha and 45 cm row spacing.",
            "ICAR_KHARIF_STATE_ADVISORIES_2025",
            "PDF p. 158 (printed pp. 142–143), Maharashtra—soybean",
        )
        for site_id, label in (
            ("IN_MH_AKOLA_SOYBEAN_KHARIF", "AKOLA"),
            ("IN_MH_NANDED_SOYBEAN_KHARIF", "NANDED"),
        )
    ),
    *(
        PolicySpec(
            f"ICAR_KARNATAKA_MAIZE_2025_CONDITIONAL_NPK_{label}",
            site_id,
            "maize",
            "kharif",
            "fertilizer",
            "regional_blanket_baseline",
            "Karnataka maize baseline with an explicit water-regime branch. An experiment must record whether the registered scenario is irrigated or dryland before selecting a branch; no branch may be inferred from the district name alone.",
            "For irrigated maize: N:P2O5:K2O = 150:65:65 kg/ha plus ZnSO4 25 kg/ha. For dryland maize: 100:50:25 kg/ha plus ZnSO4 10 kg/ha. Apply the documented N splits at sowing, knee-high stage, tasseling and grain filling; use the source's water-regime branch without interpolation.",
            "ICAR_KHARIF_STATE_ADVISORIES_2025",
            "PDF p. 128 (printed pp. 112–113), Karnataka—maize nutrient management",
        )
        for site_id, label in (
            ("IN_KA_DAVANAGERE_MAIZE_KHARIF", "DAVANAGERE"),
            ("IN_KA_CHIKKABALLAPUR_MAIZE_KHARIF", "CHIKKABALLAPUR"),
        )
    ),
    PolicySpec(
        "ICAR_RAJASTHAN_MAIZE_2025_FAW",
        "IN_RJ_UDAIPUR_MAIZE_KHARIF",
        "maize",
        "kharif",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Confirmed fall armyworm in maize up to 20 days old. The Rajasthan chapter gives a stage-specific option; this record is not a preventive spray schedule.",
        "Chlorantraniliprole 18.5% SC: 200 mL/ha in 500 L water for maize fall armyworm up to 20 days old. The current PPQS Major Uses record has the same crop, problem, formulation, dose and water volume.",
        "ICAR_KHARIF_STATE_ADVISORIES_2025",
        "PDF p. 228 (printed pp. 212–213), Rajasthan—maize fall armyworm",
        "CIBRC_INSECTICIDE_2026",
        "PDF p. 12: Maize—fall armyworm—chlorantraniliprole 18.5% SC",
        ("Chlorantraniliprole 18.50% SC", "Maize", "Fall army worm"),
        "PPQS: 200 mL/ha in 500 L water; ICAR Rajasthan chapter: 200 mL/ha in 500 L water.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "ICAR_RABI_HARYANA_WHEAT_2021_NPK",
        "IN_HR_KARNAL_WHEAT_RABI",
        "wheat",
        "rabi",
        "fertilizer",
        "regional_blanket_baseline",
        "Haryana irrigated wheat baseline when a field soil test is unavailable. The source explicitly prefers soil-test-based nutrient application; the experiment must record the irrigated branch before using this regional fallback.",
        "For irrigated wheat: N 150, P2O5 60, K2O 30 kg/ha plus ZnSO4 (21%) 25 kg/ha. Apply half the N plus all P, K and zinc at sowing; broadcast the remaining 75 kg N/ha with the first irrigation at 21–22 DAS.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF pp. 130–131 (printed pp. 120–121), Haryana & Delhi—wheat nutrient management",
    ),
    PolicySpec(
        "ICAR_RABI_HARYANA_WHEAT_2021_YELLOW_RUST",
        "IN_HR_KARNAL_WHEAT_RABI",
        "wheat",
        "rabi",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Visible wheat yellow-rust symptoms. The state chapter says to spray as soon as symptoms appear and repeat only when required after 10–15 days; this is not a calendar spray.",
        "Propiconazole 25% EC: ICAR lists 500 mL/ha in 625 L water for yellow rust. Current PPQS Major Uses lists wheat stripe/yellow rust for propiconazole 25% EC at 500 mL/ha in 750 L water. The active-formulation area dose aligns; the different carrier-water volume remains explicit.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 134 (printed p. 124), Haryana & Delhi—yellow rust",
        "CIBRC_FUNGICIDE_2026",
        "PDF p. 24: Wheat—stripe/yellow rust—propiconazole 25% EC",
        ("Propiconazole 25% EC", "Wheat", "Stripe rust"),
        "PPQS: 500 mL/ha in 750 L water; ICAR Haryana: 500 mL/ha in 625 L water.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "ICAR_RABI_UP_WHEAT_2021_NPK",
        "IN_UP_MEERUT_WHEAT_RABI",
        "wheat",
        "rabi",
        "fertilizer",
        "regional_blanket_baseline",
        "Uttar Pradesh irrigated timely-sown wheat baseline; keep it as a regional fallback rather than a substitute for a soil test.",
        "Apply 10 t FYM/ha and N:P2O5:K2O = 120:60:40 kg/ha before/at sowing as stated in the state chapter. The source describes 22.5 cm row spacing for irrigated timely-sown wheat.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 148 (printed p. 138), Uttar Pradesh—wheat",
    ),
    PolicySpec(
        "ICAR_RABI_UP_WHEAT_2021_CARBOXIN",
        "IN_UP_MEERUT_WHEAT_RABI",
        "wheat",
        "rabi",
        "crop_protection",
        "diagnosis_triggered_seed_treatment_option",
        "Before sowing where seed-borne loose smut, flag smut or bunt is a documented risk. This is a seed-treatment option, not a post-emergence foliar spray or a response to an unconfirmed field diagnosis.",
        "Carboxin 75% WP: the Uttar Pradesh chapter lists 2.5 g/kg seed. Current PPQS Major Uses lists the same formulation for wheat loose smut, flag smut and bunt at 2–2.5 g/kg seed.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 148 (printed p. 138), Uttar Pradesh—wheat seed treatment",
        "CIBRC_FUNGICIDE_2026",
        "PDF p. 6: Wheat—flag smut/loose smut/bunt—carboxin 75% WP",
        ("Carboxin 75% WP", "Wheat", "Loose smut"),
        "PPQS: 2–2.5 g/kg seed; ICAR Uttar Pradesh: 2.5 g/kg seed.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "ICAR_RABI_MP_WHEAT_2021_NPK",
        "IN_MP_SEHORE_WHEAT_RABI",
        "wheat",
        "rabi",
        "fertilizer",
        "regional_conditional_baseline",
        "Madhya Pradesh wheat baseline with irrigation branches. The experimental record must name the selected water-availability branch; no branch may be inferred from the district alone.",
        "N:P2O5:K2O kg/ha: rainfed 40:20:10; limited/partial irrigation 60:40:30; irrigated 120:60:40. The source further lists micronutrients only according to soil-test values.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 332 (printed p. 322), Madhya Pradesh—wheat",
    ),
    PolicySpec(
        "ICAR_RABI_MH_CHICKPEA_2021_NPK",
        "IN_MH_JALNA_CHICKPEA_RABI",
        "chickpea",
        "rabi",
        "fertilizer",
        "regional_blanket_baseline",
        "Maharashtra chickpea baseline at sowing. The source recommends soil testing for secondary and micronutrients; do not convert this baseline into a farm-specific prescription.",
        "Apply N:P2O5:K2O = 25:50:25 kg/ha as basal at sowing. The source differentiates rainfed and irrigated sowing windows and specifies seed-rate branches by desi or Kabuli type.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 315 (printed p. 305), Maharashtra—chickpea",
    ),
    PolicySpec(
        "ICAR_RABI_MH_CHICKPEA_2021_POD_BORER",
        "IN_MH_JALNA_CHICKPEA_RABI",
        "chickpea",
        "rabi",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "Helicoverpa/pod-borer pressure at the economic threshold. The Maharashtra chapter requires pheromone traps and an NSKE spray before recording a chemical option; this row is not a routine calendar spray.",
        "Quinalphos 25% EC: ICAR lists 20 mL/10 L water as an ETL-based option. Current PPQS Major Uses lists Bengal gram pod borer for quinalphos 25% EC at 1,000 mL/ha in 500–1,000 L water; 20 mL/10 L corresponds to the 500 L/ha label branch.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 315 (printed p. 305), Maharashtra—chickpea IPM",
        "CIBRC_INSECTICIDE_2026",
        "PDF p. 47: Bengal gram—pod borer—quinalphos 25% EC",
        ("Quinalphos 25 %EC", "Bengal gram", "Pod borer"),
        "PPQS: 1,000 mL/ha in 500–1,000 L water; ICAR Maharashtra: 20 mL/10 L water.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    ),
    PolicySpec(
        "ICAR_RABI_KARNATAKA_TOMATO_2021_NPK",
        "IN_KA_KOLAR_TOMATO_RABI",
        "tomato",
        "rabi",
        "fertilizer",
        "regional_conditional_baseline",
        "Karnataka tomato baseline with distinct hybrid and non-hybrid branches. The scenario record must state cultivar class before choosing a branch.",
        "For tomato hybrids apply N:P2O5:K2O = 250:250:250 kg/ha; for other tomatoes apply 115:100:60 kg/ha. The source also specifies disease-resistant hybrids, rotation and nursery measures.",
        "ICAR_RABI_STATE_ADVISORIES_2021_22",
        "PDF p. 415 (printed p. 405), Karnataka—tomato",
    ),
)


SOURCE_FIELDS = [
    "retrieved_at_utc", "source_document_id", "source_title", "provider", "source_class",
    "geography_scope", "crop_scope", "management_scope", "official_url", "expected_issue_date",
    "http_status", "content_type", "byte_count", "sha256", "text_char_count", "required_terms_status",
    "source_date_status", "source_metadata_date", "title_consistency_status", "source_status", "error",
]
POLICY_FIELDS = [
    "policy_id", "site_id", "crop", "season", "policy_domain", "policy_kind", "trigger_or_scope",
    "regional_management_record", "source_document_id", "source_locator", "source_issue_date",
    "source_evidence_status", "ppqs_source_document_id", "ppqs_locator", "ppqs_match_status",
    "ppqs_rate_record", "dose_alignment_status", "policy_verification_status", "safety_note",
]
COVERAGE_FIELDS = [
    "site_id", "crop", "state", "district", "fertilizer_source_document_ids", "fertilizer_status",
    "crop_protection_source_document_ids", "crop_protection_status", "verified_policy_ids",
    "management_bundle_status", "coverage_note",
]


def extract_text_and_metadata_date(
    content: bytes, content_type: str, page_numbers: Sequence[int] = ()
) -> tuple[str, str]:
    """Extract source text and, for PDFs, the declared document metadata date."""
    if "pdf" in content_type.casefold() or content.startswith(b"%PDF"):
        reader = PdfReader(BytesIO(content))
        pages = (
            (reader.pages[number - 1] for number in page_numbers)
            if page_numbers
            else reader.pages
        )
        metadata = reader.metadata or {}
        metadata_date = str(metadata.get("/ModDate") or metadata.get("/CreationDate") or "")
        return "\n".join(page.extract_text() or "" for page in pages), metadata_date
    parser = TextExtractor()
    parser.feed(content.decode("utf-8", "replace"))
    return parser.text(), ""


def casefold_contains_all(text: str, terms: Sequence[str]) -> bool:
    haystack = text.casefold()
    return all(term.casefold() in haystack for term in terms)


def source_status(
    spec: SourceSpec, text: str, fetched: bool, metadata_date: str = ""
) -> tuple[str, str, str]:
    """Return required-term, date, and conservative source status."""
    if not fetched:
        return "not_checked", "not_checked", "source_unavailable_or_unreadable"
    terms_ok = casefold_contains_all(text, spec.required_terms)
    date_terms = spec.issue_date_terms or (spec.expected_issue_date,)
    date_ok = casefold_contains_all(text, date_terms)
    metadata_date_ok = bool(
        spec.metadata_date_expected and spec.metadata_date_expected in metadata_date
    )
    title_conflict = bool(spec.title_conflict_term and spec.title_conflict_term.casefold() in text.casefold())
    required = "required_terms_found" if terms_ok else "required_terms_missing"
    date = (
        "expected_issue_date_found"
        if date_ok
        else "official_pdf_metadata_date_verified"
        if metadata_date_ok
        else "expected_issue_date_missing"
    )
    if title_conflict:
        return required, date, "content_title_conflict_manual_signoff_required"
    if terms_ok and (date_ok or metadata_date_ok):
        return required, date, "dated_source_semantics_verified"
    return required, date, "source_semantics_or_date_not_verified"


def collect_source(spec: SourceSpec, timeout_s: float) -> tuple[Dict[str, str], str]:
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    row = {
        "retrieved_at_utc": retrieved_at,
        "source_document_id": spec.source_document_id,
        "source_title": spec.source_title,
        "provider": spec.provider,
        "source_class": spec.source_class,
        "geography_scope": spec.geography_scope,
        "crop_scope": spec.crop_scope,
        "management_scope": spec.management_scope,
        "official_url": spec.official_url,
        "expected_issue_date": spec.expected_issue_date,
        "http_status": "",
        "content_type": "",
        "byte_count": "",
        "sha256": "NONE",
        "text_char_count": "",
        "required_terms_status": "not_checked",
        "source_date_status": "not_checked",
        "source_metadata_date": "NONE",
        "title_consistency_status": "consistent",
        "source_status": "source_unavailable_or_unreadable",
        "error": "",
    }
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            response = requests.get(spec.official_url, headers=REQUEST_HEADERS, timeout=timeout_s)
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            last_error = exc
    else:
        row["error"] = f"{type(last_error).__name__}: {last_error}"
        return row, ""
    try:
        row["http_status"] = str(response.status_code)
        content_type = response.headers.get("Content-Type", "")
        text, metadata_date = extract_text_and_metadata_date(
            response.content, content_type, spec.extract_page_numbers
        )
        required_status, date_status, status = source_status(spec, text, True, metadata_date)
        row.update({
            "content_type": content_type,
            "byte_count": str(len(response.content)),
            "sha256": sha256(response.content).hexdigest(),
            "text_char_count": str(len(text)),
            "required_terms_status": required_status,
            "source_date_status": date_status,
            "source_metadata_date": metadata_date or "NONE",
            "title_consistency_status": (
                "title_conflict_detected" if status == "content_title_conflict_manual_signoff_required" else "consistent"
            ),
            "source_status": status,
        })
        return row, text
    except (requests.RequestException, ValueError, OSError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row, ""


def policy_status(policy: PolicySpec, source_rows: Dict[str, Dict[str, str]], source_text: Dict[str, str]) -> tuple[str, str]:
    source_row = source_rows[policy.source_document_id]
    if source_row["source_status"] != "dated_source_semantics_verified":
        return "not_checked", "regional_source_not_verified"
    if not policy.ppqs_source_document_id:
        return "not_applicable", "regional_baseline_source_verified"
    ppqs_row = source_rows[policy.ppqs_source_document_id]
    matches = casefold_contains_all(source_text.get(policy.ppqs_source_document_id, ""), policy.ppqs_required_terms)
    if (
        ppqs_row["source_status"] == "dated_source_semantics_verified"
        and matches
        and policy.dose_alignment_status == "regional_and_PPQS_rates_align_after_unit_conversion"
    ):
        return "current_PPQS_crop_problem_formulation_terms_found", "regional_trigger_and_PPQS_match_verified"
    if ppqs_row["source_status"] == "dated_source_semantics_verified" and matches:
        return "current_PPQS_crop_problem_formulation_terms_found", "regional_trigger_source_verified_PPQS_rate_alignment_pending"
    return "current_PPQS_exact_terms_not_verified", "regional_trigger_source_verified_PPQS_match_pending"


def policy_rows(source_rows: Dict[str, Dict[str, str]], source_text: Dict[str, str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for policy in POLICIES:
        ppqs_status, verification = policy_status(policy, source_rows, source_text)
        source_row = source_rows[policy.source_document_id]
        rows.append({
            "policy_id": policy.policy_id,
            "site_id": policy.site_id,
            "crop": policy.crop,
            "season": policy.season,
            "policy_domain": policy.policy_domain,
            "policy_kind": policy.policy_kind,
            "trigger_or_scope": policy.trigger_or_scope,
            "regional_management_record": policy.regional_management_record,
            "source_document_id": policy.source_document_id,
            "source_locator": policy.source_locator,
            "source_issue_date": source_row["expected_issue_date"],
            "source_evidence_status": source_row["source_status"],
            "ppqs_source_document_id": policy.ppqs_source_document_id or "NONE",
            "ppqs_locator": policy.ppqs_locator or "NONE",
            "ppqs_match_status": ppqs_status,
            "ppqs_rate_record": policy.ppqs_rate_record or "NONE",
            "dose_alignment_status": policy.dose_alignment_status,
            "policy_verification_status": verification,
            "safety_note": policy.safety_note,
        })
    return rows


def joined(values: Iterable[str]) -> str:
    material = sorted(set(value for value in values if value))
    return ";".join(material) if material else "NONE"


def build_coverage_rows(sites: List[Dict[str, str]], policies: List[Dict[str, str]], source_rows: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    by_site: Dict[str, List[Dict[str, str]]] = {}
    for policy in policies:
        by_site.setdefault(policy["site_id"], []).append(policy)
    rows: List[Dict[str, str]] = []
    for site in sites:
        policies_for_site = by_site.get(site["site_id"], [])
        fertilizer = [policy for policy in policies_for_site if policy["policy_domain"] == "fertilizer"]
        protection = [policy for policy in policies_for_site if policy["policy_domain"] == "crop_protection"]
        fertilizer_verified = any(policy["policy_verification_status"] == "regional_baseline_source_verified" for policy in fertilizer)
        protection_verified = any(policy["policy_verification_status"] == "regional_trigger_and_PPQS_match_verified" for policy in protection)
        located_uasd = site["site_id"] == "IN_KA_DHARWAD_CHICKPEA_RABI" and source_rows["UASD_NORTH_KARNATAKA_POP_2023"]["source_status"] == "dated_source_semantics_verified"
        fertilizer_status = (
            "regional_baseline_schedule_evidence_verified"
            if fertilizer_verified
            else "official_regional_source_located_but_structured_schedule_not_verified"
            if located_uasd
            else "no_verified_regional_fertilizer_baseline"
        )
        protection_status = (
            "regional_trigger_and_PPQS_match_verified"
            if protection_verified
            else "official_regional_source_located_but_structured_schedule_not_verified"
            if located_uasd
            else "no_verified_regional_trigger_and_PPQS_match"
        )
        if fertilizer_verified and protection_verified:
            bundle_status = "regional_fertilizer_and_crop_protection_evidence_verified_not_farm_specific"
            note = "A dated regional source and at least one exact current PPQS-linked trigger are archived. This does not replace a dated district outbreak advisory or a field soil test."
        elif site["site_id"] == "IN_TN_THANJAVUR_RICE_SAMBA" and fertilizer_verified:
            bundle_status = "fertilizer_verified_crop_protection_date_gate_pending"
            note = "TNAU’s dated rice nutrient page is verified. Its detailed rice crop-protection page is publicly reachable but lacks a content update date, so no action is promoted."
        elif site["site_id"] == "IN_TN_KRISHNAGIRI_TOMATO_RABI" and protection_verified:
            bundle_status = "crop_protection_verified_fertilizer_title_conflict_pending"
            note = "TNAU tomato IPM entries and PPQS matches are verified. The linked nutrient page contains a visible Chilli title conflict, so its numbers are held out pending manual first-party confirmation."
        elif fertilizer_verified:
            bundle_status = "fertilizer_verified_crop_protection_pending"
            note = "A dated geographically compatible regional fertilizer baseline is archived. A matching diagnosis-triggered regional crop-protection action has not yet passed the exact current PPQS gate."
        elif protection_verified:
            bundle_status = "crop_protection_verified_fertilizer_pending"
            note = "A dated geographically compatible diagnosis-triggered crop-protection action and current PPQS match are archived. A regional fertilizer baseline has not yet passed the evidence gate."
        elif located_uasd:
            bundle_status = "official_north_karnataka_source_located_structuring_pending"
            note = "UAS Dharwad’s official 2023 North Karnataka PoP is recorded, but the linked crop PDFs require language-aware/manual extraction before values or actions can be used."
        else:
            bundle_status = "regional_management_evidence_missing"
            note = "No geographically compatible dated fertilizer baseline and exact local-trigger/PPQS crop-protection pair has been verified yet."
        rows.append({
            "site_id": site["site_id"],
            "crop": site["crop"],
            "state": site["state"].replace("_", " "),
            "district": site["district"].replace("_", " "),
            "fertilizer_source_document_ids": joined(policy["source_document_id"] for policy in fertilizer),
            "fertilizer_status": fertilizer_status,
            "crop_protection_source_document_ids": joined(policy["source_document_id"] for policy in protection),
            "crop_protection_status": protection_status,
            "verified_policy_ids": joined(
                policy["policy_id"] for policy in policies_for_site
                if policy["policy_verification_status"] in {
                    "regional_baseline_source_verified", "regional_trigger_and_PPQS_match_verified"
                }
            ),
            "management_bundle_status": bundle_status,
            "coverage_note": note,
        })
    return rows


def write_csv(path: Path, fields: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect dated regional fertilizer and crop-protection evidence.")
    parser.add_argument(
        "--sites",
        type=Path,
        help="Optional site manifest. Supply --coverage-out with this option to build a coverage table.",
    )
    parser.add_argument("--source-out", type=Path, default=PROJECT_ROOT / "data" / "registry" / "regional_management_source_snapshot.csv")
    parser.add_argument("--policy-out", type=Path, default=PROJECT_ROOT / "data" / "registry" / "regional_management_policy.csv")
    parser.add_argument(
        "--coverage-out",
        type=Path,
        help="Optional coverage-table output. Requires --sites.",
    )
    parser.add_argument("--timeout-s", type=float, default=45.0)
    args = parser.parse_args()
    if args.timeout_s <= 0:
        raise SystemExit("--timeout-s must be positive.")

    if (args.sites is None) != (args.coverage_out is None):
        raise SystemExit("--sites and --coverage-out must be supplied together.")
    source_rows: Dict[str, Dict[str, str]] = {}
    source_text: Dict[str, str] = {}
    for source in SOURCES:
        row, text = collect_source(source, args.timeout_s)
        source_rows[source.source_document_id] = row
        source_text[source.source_document_id] = text
        print(f"{source.source_document_id}: {row['source_status']}")
    rows = policy_rows(source_rows, source_text)
    write_csv(args.source_out, SOURCE_FIELDS, list(source_rows.values()))
    write_csv(args.policy_out, POLICY_FIELDS, rows)
    print(f"Wrote {len(source_rows)} source rows to {args.source_out}")
    print(f"Wrote {len(rows)} policy rows to {args.policy_out}")
    if args.sites is not None and args.coverage_out is not None:
        with args.sites.open(newline="", encoding="utf-8") as source_file:
            sites = list(csv.DictReader(source_file))
        coverage = build_coverage_rows(sites, rows, source_rows)
        write_csv(args.coverage_out, COVERAGE_FIELDS, coverage)
        print(f"Wrote {len(coverage)} coverage rows to {args.coverage_out}")


if __name__ == "__main__":
    main()
