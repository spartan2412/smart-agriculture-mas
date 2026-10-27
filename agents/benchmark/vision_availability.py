"""Vision Availability agent."""
from __future__ import annotations

from typing import Any

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import ClaimDisposition, DecisionDomain

from .base import BenchmarkAgent


class VisionAvailabilityAgent(BenchmarkAgent):
    """Returns no data because no scenario contains an aligned leaf image."""

    name = "vision_availability_agent"

    def run(self, scenario: FrozenBenchmarkScenario, **_: Any):
        return (
            self._blocked(
                scenario,
                decision_domain=DecisionDomain.CROP_PROTECTION_SAFETY,
                claim="No aligned field leaf image is available for vision inference.",
                summary="Leaf vision returns no_data for this frozen public-data scenario.",
                reason=scenario.agent_permission("leaf_vision_agent"),
                disposition=ClaimDisposition.NO_DATA,
                quality="no aligned field image in benchmark",
                metadata={"legacy_vision_model_usage": "separate PlantVillage experiment only"},
            ),
        )
