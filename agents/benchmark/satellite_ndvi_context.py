"""Satellite/NDVI Context agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult

from .base import BenchmarkAgent, citation_from


class SatelliteNDVIContextAgent(BenchmarkAgent):
    """Reports quality-gated representative-cell NDVI and pre-decision chronology."""

    name = "satellite_ndvi_context_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You prioritize quality-valid Sentinel-2 representative-cell context. Select a
fact only when its own text records a valid scene or pre-decision NDVI
chronology and it helps explain the approved plan without pretending to observe
an individual field.

Prefer a fact with explicit clear-observation quality, acquisition timing, and
an already-recorded trend over a weaker or redundant satellite fact. Preserve
the distinction between a representative cell and a farm parcel. A numerical
trend is useful only as historical context; it is never a trigger for action.

Never infer crop identity, crop/field condition, crop stage, disease, nutrient
deficiency, irrigation need, or field-level stress. Do not turn a pixel into a
diagnosis. Return an empty selection when satellite context would distract from
the cited plan.
""".strip()

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        status, feature = scenario.satellite_context_status, scenario.satellite_context_features
        timeseries_status, chronology = scenario.ndvi_timeseries_status, scenario.ndvi_timeseries_features
        source_record = {
            "official_url": scenario.satellite_context_manifest.get("item_request_url", ""),
            "raw_path": scenario.satellite_context_manifest.get("raw_path", ""),
            "response_sha256": scenario.satellite_context_manifest.get("response_sha256", ""),
            "source_location": scenario.satellite_context_manifest.get("satellite_item_id", ""),
        }
        source = citation_from(
            source_record,
            source_document_id="SENTINEL2_L2A",
            source_role="representative_cell_ndvi_context",
            locator=scenario.satellite_context_manifest.get("satellite_item_id", ""),
        )
        if feature is None or not status.get("satellite_condition_status", "").startswith("available_"):
            return (
                self._blocked(
                    scenario,
                    decision_domain=DecisionDomain.SATELLITE_CONTEXT,
                    claim="Representative-cell satellite context is unavailable for this scenario.",
                    summary="No quality-gated clear-surface satellite context may be interpreted.",
                    reason=status.get("restriction_reason", "satellite_context_unavailable"),
                    source=source,
                    disposition=ClaimDisposition.NO_DATA,
                    metadata={"satellite_status": dict(status)},
                ),
            )
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SATELLITE_CONTEXT,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="A quality-gated Sentinel-2 NDVI signal is available at the representative cell.",
                summary=(
                    f"NDVI {feature.get('satellite_ndvi', '')}; pre-decision series has "
                    f"{chronology.get('observation_count', '')} clear observations and trend "
                    f"{chronology.get('ndvi_trend_direction', '')}."
                ),
                reasoning=(
                    "This is a clear-pixel signal at a documented cropland cell. It is not evidence "
                    "of crop identity, field-average condition, crop stage, disease, or irrigation need."
                ),
                confidence=0.85,
                source=source,
                quality=status.get("satellite_condition_status", ""),
                gate_result=GateResult.PASS,
                metadata={
                    "item_id": feature.get("satellite_item_id", ""),
                    "item_datetime_utc": feature.get("satellite_datetime_utc", ""),
                    "pixel_quality_status": feature.get("satellite_pixel_quality_status", ""),
                    "timeseries_status": timeseries_status.get("ndvi_timeseries_status", ""),
                    "timeseries_restriction": timeseries_status.get("restriction_reason", ""),
                    "observation_count": chronology.get("observation_count", ""),
                    "ndvi_change": chronology.get("ndvi_change", ""),
                },
                spatial_scope=(
                    f"single documented representative cropland-cell pixel in "
                    f"{scenario.identity.district}, {scenario.identity.state}; not a crop-labelled parcel"
                ),
                temporal_scope=(
                    f"selected Sentinel item {feature.get('satellite_datetime_utc', '')}; "
                    f"pre-decision chronology ending {chronology.get('last_observation_utc', '')}"
                ),
            ),
        )
