from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.evidence_schema import (
    AllowedUse,
    ClaimDisposition,
    DecisionDomain,
    GateResult,
    SourceCitation,
    TypedEvidenceClaim,
)


def _claim(**overrides):
    values = {
        "scenario_id": "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130",
        "agent_name": "weather_context_agent",
        "decision_domain": DecisionDomain.WEATHER_CONTEXT,
        "disposition": ClaimDisposition.CONTEXT,
        "allowed_use": AllowedUse.CONTEXT_ONLY,
        "claim": "Historical weather context is available.",
        "summary": "Historical observed context only.",
        "reasoning": "The frozen contract excludes a decision-time forecast.",
        "confidence": 0.8,
        "source": SourceCitation(source_document_id="NASA_POWER"),
        "spatial_scope": "documented representative cell",
        "temporal_scope": "historical decision window",
        "quality": "source-hashed",
        "gate_result": GateResult.PASS,
    }
    values.update(overrides)
    return TypedEvidenceClaim(**values)


def test_typed_claim_carries_domain_scope_and_source():
    claim = _claim()

    assert claim.decision_domain == DecisionDomain.WEATHER_CONTEXT
    assert claim.source.source_document_id == "NASA_POWER"
    assert claim.allowed_use == AllowedUse.CONTEXT_ONLY


def test_abstention_requires_a_machine_readable_reason():
    with pytest.raises(ValidationError, match="block_reason"):
        _claim(
            disposition=ClaimDisposition.ABSTAIN,
            allowed_use=AllowedUse.UNAVAILABLE,
            gate_result=GateResult.ABSTAIN,
        )


def test_unavailable_source_cannot_be_emitted_as_context():
    with pytest.raises(ValidationError, match="unavailable evidence"):
        _claim(allowed_use=AllowedUse.UNAVAILABLE)


def test_safe_abstention_is_valid_when_reason_is_preserved():
    claim = _claim(
        decision_domain=DecisionDomain.CROP_PROTECTION_SAFETY,
        disposition=ClaimDisposition.ABSTAIN,
        allowed_use=AllowedUse.UNAVAILABLE,
        gate_result=GateResult.ABSTAIN,
        claim="No treatment can be issued.",
        summary="No dated diagnosis or threshold event is available.",
        reasoning="The capability contract requires treatment abstention.",
        confidence=1.0,
        block_reason="abstain_no_dated_diagnosis_or_threshold_event",
    )

    assert claim.block_reason == "abstain_no_dated_diagnosis_or_threshold_event"
