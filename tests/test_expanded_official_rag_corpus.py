from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.expand_official_rag_corpus import is_admitted, parse_week_range


def test_weekly_archive_dates_require_an_explicit_range_without_guessing():
    assert parse_week_range("27 Sept- 3 Oct", 2023) == ("2023-09-27", "2023-10-03")
    assert parse_week_range("04-10 Oct", 2021) == ("2021-10-04", "2021-10-10")
    assert parse_week_range("MAY 2024", 2024) is None


def test_only_explicit_allow_list_statuses_enter_expanded_corpus():
    assert is_admitted("admitted_initial_hash_frozen")
    assert is_admitted("admitted_exact_final_site_hash_verified")
    assert not is_admitted("rejected_content_scope_verification_failed")
    assert not is_admitted("rejected_source_retrieval_or_extraction_failure")
