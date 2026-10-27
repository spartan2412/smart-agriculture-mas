from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_source_scoped_preflight_audit import find_bundle, source_verified


def test_bundle_selection_requires_crop_state_and_season_not_only_crop():
    bundles = [
        {"management_bundle_id": "PB", "crop": "rice", "states": "Punjab", "season": "kharif"},
        {"management_bundle_id": "TN", "crop": "rice", "states": "Tamil Nadu", "season": "samba"},
    ]
    assert find_bundle({"crop": "rice", "state": "Punjab", "proposed_season": "kharif"}, bundles)["management_bundle_id"] == "PB"
    assert find_bundle({"crop": "rice", "state": "Punjab", "proposed_season": "samba"}, bundles) is None


def test_source_status_requires_every_documented_source_to_be_dated_and_verified():
    source_snapshot = {
        "A": {"source_status": "dated_source_semantics_verified"},
        "B": {"source_status": "content_title_conflict_manual_signoff_required"},
    }
    assert source_verified(["A"], source_snapshot) is True
    assert source_verified(["A", "B"], source_snapshot) is False
    assert source_verified(["MISSING"], source_snapshot) is False
