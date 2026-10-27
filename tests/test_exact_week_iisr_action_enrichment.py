from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_exact_week_iisr_action_enrichment import condition_reason, normalise


def test_pdf_line_wrap_artifacts_normalise_without_changing_advisory_meaning():
    extracted = "Broad -Bed-Furrow/Ridge- Furrow planting system"
    printed = "Broad-Bed-Furrow/Ridge-Furrow planting system"
    assert normalise(extracted) == normalise(printed)
    assert normalise("m ake necessary drainage") == "make necessary drainage"


def test_exact_week_actions_keep_missing_field_evidence_explicit():
    assert condition_reason({"stage": True, "field": True}) == "actual_crop_stage;documented_field_condition"
    assert condition_reason({"stage": True, "forecast": True}) == "actual_crop_stage;decision_time_forecast"
    assert condition_reason({"stage": True, "soil": True}) == "actual_crop_stage;soil_test_for_personalised_dose"
