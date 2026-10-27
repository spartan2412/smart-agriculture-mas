"""Unit and integration checks for deterministic provenance conflict resolution."""
from __future__ import annotations

from agents.benchmark.conflict_detection import ConflictDetectionAgent
from agents.benchmark.conflict_resolution import ConflictResolutionPolicy
from agents.benchmark.provenance_aware_coordinator import ProvenanceAwareCoordinatorAgent
from data.benchmark_loader import FrozenBenchmarkLoader
from data.evidence_schema import (
    AllowedUse,
    ClaimDisposition,
    DecisionDomain,
    GateResult,
    SourceCitation,
    TypedEvidenceClaim,
)


RICE_ANCHOR = "ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130"
ELIGIBLE_DIVERGENCE = "ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331"


def _scenario():
    return FrozenBenchmarkLoader().load(RICE_ANCHOR, verify_raw_hashes=False)


def _claim(
    scenario,
    *,
    agent_name: str,
    polarity: str,
    disposition: ClaimDisposition = ClaimDisposition.SUPPORTED_OPERATION,
    allowed_use: AllowedUse = AllowedUse.CONDITIONAL_OPERATION_ONLY,
    gate_result: GateResult = GateResult.PASS,
    source_id: str = "OFFICIAL_TEST_SOURCE",
    scope: str = "state-level source scope",
    temporal_scope: str = "seasonal source scope",
    confidence: float = 0.8,
    safety: bool = False,
) -> TypedEvidenceClaim:
    return TypedEvidenceClaim(
        scenario_id=scenario.identity.scenario_id,
        agent_name=agent_name,
        decision_domain=DecisionDomain.OFFICIAL_OPERATION,
        disposition=disposition,
        allowed_use=allowed_use,
        claim=f"{polarity} source-scoped operation from {source_id}",
        summary="Comparable test claim.",
        reasoning="A test-only trace checks deterministic conflict policy.",
        confidence=confidence,
        source=SourceCitation(
            source_document_id=source_id,
            official_url="https://example.org/official-source",
            raw_sha256="a" * 64,
            locator="page 1",
            source_role="test_official_source",
        ),
        spatial_scope=scope,
        temporal_scope=temporal_scope,
        quality="test-quality",
        gate_result=gate_result,
        block_reason="documented safety restriction" if disposition == ClaimDisposition.BLOCKED else None,
        metadata={
            "decision_target": "test:official_operation",
            "assertion_polarity": polarity,
            "safety_restriction": safety,
        },
    )


def test_claim_id_is_stable_and_ignores_presentation_only_llm_metadata():
    scenario = _scenario()
    claim = _claim(scenario, agent_name="source_agent", polarity="supports")
    annotated = claim.model_copy(update={
        "metadata": {**claim.metadata, "bounded_llm": {"status": "accepted", "selected_fact_ids": ["claim_1"]}}
    })

    assert claim.claim_id == annotated.claim_id
    assert len(claim.claim_id) == 64
    changed = claim.model_copy(update={"claim": "different immutable evidence"})
    assert changed.claim_id != claim.claim_id


def test_detector_references_stable_claim_ids_for_same_target_conflict():
    scenario = _scenario()
    support = _claim(scenario, agent_name="support_agent", polarity="supports")
    oppose = _claim(scenario, agent_name="oppose_agent", polarity="opposes")

    conflicts = ConflictDetectionAgent().detect(scenario, (support, oppose))

    assert len(conflicts) == 1
    assert conflicts[0].conflict_id
    assert conflicts[0].claim_ids == tuple(sorted((support.claim_id, oppose.claim_id)))


def test_safety_restriction_wins_and_coordinator_excludes_rejected_action():
    scenario = _scenario()
    support = _claim(scenario, agent_name="operation_agent", polarity="supports", source_id="ACTION_SOURCE")
    safety = _claim(
        scenario,
        agent_name="safety_agent",
        polarity="opposes",
        disposition=ClaimDisposition.BLOCKED,
        allowed_use=AllowedUse.UNAVAILABLE,
        gate_result=GateResult.BLOCKED,
        source_id="SAFETY_SOURCE",
        safety=True,
    )
    conflicts = ConflictDetectionAgent().detect(scenario, (support, safety))
    decision = ProvenanceAwareCoordinatorAgent().coordinate(
        scenario, (support, safety), (), conflicts
    )
    record = decision.conflict_resolution_records[0]

    assert record.status == "resolved_by_safety_restriction"
    assert record.accepted_claim_ids == (safety.claim_id,)
    assert record.rejected_claim_ids == (support.claim_id,)
    assert not decision.direct_farm_action_issued
    assert decision.decision_status == "context_only_no_direct_farm_action"
    assert "SAFETY_SOURCE" in decision.citations
    assert "ACTION_SOURCE" not in decision.citations


def test_equal_precedence_opposition_is_deferred_not_arbitrarily_selected():
    scenario = _scenario()
    support = _claim(scenario, agent_name="support_agent", polarity="supports", source_id="SOURCE_A")
    oppose = _claim(scenario, agent_name="oppose_agent", polarity="opposes", source_id="SOURCE_B")
    conflicts = ConflictDetectionAgent().detect(scenario, (support, oppose))

    result = ConflictResolutionPolicy().resolve(scenario, (support, oppose), conflicts)
    record = result.records[0]

    assert record.status == "deferred_equal_precedence"
    assert set(record.deferred_claim_ids) == {support.claim_id, oppose.claim_id}
    assert set(result.excluded_claim_ids) == {support.claim_id, oppose.claim_id}
    assert not record.direct_farm_action_allowed


def test_eligible_natural_divergence_is_traceable_but_remains_non_action_context():
    scenario = FrozenBenchmarkLoader().load(ELIGIBLE_DIVERGENCE, verify_raw_hashes=False)
    from agents.benchmark.satellite_ndvi_context import SatelliteNDVIContextAgent
    from agents.benchmark.weather_context import WeatherContextAgent

    claims = (WeatherContextAgent().run(scenario)[0], SatelliteNDVIContextAgent().run(scenario)[0])
    conflicts = ConflictDetectionAgent().detect(scenario, claims)
    result = ConflictResolutionPolicy().resolve(scenario, claims, conflicts)

    assert len(result.records) == 1
    assert result.records[0].status == "handled_as_non_action_contextual_divergence"
    assert not result.records[0].direct_farm_action_allowed
    assert not result.excluded_claim_ids
