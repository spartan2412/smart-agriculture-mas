from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_regional_management_evidence import (
    PolicySpec,
    SourceSpec,
    casefold_contains_all,
    policy_status,
    source_status,
)


def test_source_status_accepts_a_display_date_variant_and_rejects_title_conflict():
    source = SourceSpec(
        "TEST_TOMATO",
        "Test tomato source",
        "Test provider",
        "Test state",
        "tomato",
        "fertilizer",
        "https://example.invalid/test",
        "June 2023",
        ("Tomato", "Updated on Jun, 2023"),
        ("Updated on Jun, 2023",),
    )
    required, date, status = source_status(source, "Tomato guidance. Updated on Jun, 2023", True)

    assert required == "required_terms_found"
    assert date == "expected_issue_date_found"
    assert status == "dated_source_semantics_verified"

    conflicting = SourceSpec(
        "TEST_CONFLICT",
        "Test source",
        "Test provider",
        "Test state",
        "tomato",
        "fertilizer",
        "https://example.invalid/conflict",
        "June 2023",
        ("Tomato",),
        ("June 2023",),
        title_conflict_term="Chilli",
    )
    assert source_status(conflicting, "Tomato field. Chilli heading. June 2023", True)[2] == (
        "content_title_conflict_manual_signoff_required"
    )


def test_policy_requires_both_a_dated_regional_source_and_exact_ppqs_terms():
    policy = PolicySpec(
        "TEST_POLICY",
        "TEST_SITE",
        "rice",
        "kharif",
        "crop_protection",
        "diagnosis_triggered_IPM_chemical_option",
        "diagnosed rice stem borer",
        "one documented action",
        "REGIONAL",
        "source p. 1",
        "PPQS",
        "registration p. 1",
        ("Rice", "Stem borer", "Example 18.5% SC"),
        "Comparable source and PPQS rates recorded.",
        "regional_and_PPQS_rates_align_after_unit_conversion",
    )
    rows = {
        "REGIONAL": {"source_status": "dated_source_semantics_verified"},
        "PPQS": {"source_status": "dated_source_semantics_verified"},
    }
    texts = {"PPQS": "Rice Stem borer Example 18.5% SC"}

    assert policy_status(policy, rows, texts) == (
        "current_PPQS_crop_problem_formulation_terms_found",
        "regional_trigger_and_PPQS_match_verified",
    )
    assert casefold_contains_all(texts["PPQS"], ("rice", "STEM BORER"))
