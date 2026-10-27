"""Farmer Explanation / Citation agent.

The renderer is deliberately deterministic.  It turns facts already admitted
by the frozen scenario loader into a self-contained farmer plan; it never asks
the farmer to consult a source in order to discover a detail that is already
stored in the benchmark bundle.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from data.benchmark_loader import FrozenBenchmarkScenario
from data.evidence_schema import AllowedUse, ClaimDisposition, DecisionDomain, GateResult, TypedEvidenceClaim

from .base import BenchmarkAgent, BenchmarkDecision, RetrievedPassage, internal_trace_citation


class FarmerExplanationCitationAgent(BenchmarkAgent):
    """Render a self-contained, citation-preserving plan without new facts."""

    name = "farmer_explanation_citation_agent"
    uses_llm = True
    llm_extension_point = True
    llm_selection_instruction = """
You select only optional historical-context cards that make the already
approved farmer plan clearer. Mandatory seasonal, nutrient, crop-protection,
post-harvest, safety, and citation content is rendered separately and must not
influence you to duplicate it.

Select weather only when the question or plan benefits from retrospective
weather context; select soil only for a requested static representative-cell
property context; select satellite only for a requested quality-valid
representative-cell trend; and select market only for a requested or clearly
useful historical published market comparison. Prefer the smallest useful set
of optional cards, in the order that best answers the question. Select no ID
when optional context would distract from the approved plan.

Never create advice, rewrite an operation, add an agricultural fact, convert
historical context into a forecast or farm observation, omit mandatory content,
or change a citation. The deterministic renderer retains all plan, safety, and
evidence-trace content regardless of your selection.
""".strip()

    @staticmethod
    def _selected_fact_ids(
        claims: Iterable[TypedEvidenceClaim],
        *,
        agent_name: str,
    ) -> tuple[str, ...]:
        """Return an accepted bounded selection, or no selection on fallback."""
        for claim in claims:
            if claim.agent_name != agent_name:
                continue
            bounded = claim.metadata.get("bounded_llm", {})
            if bounded.get("status") == "accepted":
                return tuple(str(item) for item in bounded.get("selected_fact_ids", ()))
        return ()

    @staticmethod
    def _order_sections(
        sections: Sequence[tuple[str, str]],
        selected_ids: Sequence[str],
    ) -> list[str]:
        """Move selected approved sections to the front while preserving all cards."""
        by_id = {section_id: text for section_id, text in sections}
        selected = [by_id[item] for item in selected_ids if item in by_id]
        selected_set = {item for item in selected_ids if item in by_id}
        return selected + [text for section_id, text in sections if section_id not in selected_set]

    @staticmethod
    def _value(row: Mapping[str, Any], field: str) -> str:
        """Return one normalized immutable source value, or an empty string."""
        return str(row.get(field, "") or "").strip()

    @classmethod
    def _source_lines(cls, row: Mapping[str, Any]) -> list[str]:
        """Render the captured provenance of a plan or facility record.

        A source link is supporting provenance, not an instruction for the
        farmer to look up missing details.  The card itself contains every
        source-backed detail the runtime is permitted to state.
        """
        source_id = cls._value(row, "source_document_id")
        title = cls._value(row, "source_title")
        provider = cls._value(row, "source_provider")
        url = cls._value(row, "source_url")
        locator = cls._value(row, "source_location")
        source_bits = [bit for bit in (title, source_id, provider) if bit]
        lines: list[str] = []
        if source_bits:
            lines.append(f"  - Source: {' — '.join(source_bits)}.")
        if locator:
            lines.append(f"  - Source location: {locator}.")
        if url:
            lines.append(f"  - Source URL: {url}")
        return lines

    @classmethod
    def _regional_plan_card(
        cls,
        item: Mapping[str, Any],
        policy_detail: Mapping[str, Any] | None = None,
    ) -> str:
        """Render one existing regional-plan item with all recorded details."""
        label = cls._value(item, "farmer_visible_label") or "Regional planning item"
        lane = cls._value(item, "plan_lane")
        status = cls._value(item, "item_status")
        actionability = cls._value(item, "actionability_status")
        heading = label
        if lane == "source_quoted_operation":
            heading = f"Conditional official operation — {label}"
        lines = [f"**{heading}**"]
        visible = cls._value(item, "farmer_visible_text")
        operation = cls._value(item, "operation_text")
        method = cls._value(item, "method_text")
        dose = cls._value(item, "dose_text")
        conditions = cls._value(item, "conditions_text")
        missing = cls._value(item, "missing_evidence")
        source_quote = cls._value(item, "source_quote")

        if visible:
            lines.append(f"  - Regional guidance: {visible}")
        if operation and operation != visible:
            lines.append(f"  - Operation: {operation}")
        if method:
            lines.append(f"  - Method: {method}")
        if dose:
            lines.append(f"  - Source-recorded schedule/dose: {dose}")
        if policy_detail is not None:
            detail = cls._value(policy_detail, "detail_text")
            detail_conditions = cls._value(policy_detail, "applicability_conditions")
            detail_boundary = cls._value(policy_detail, "non_action_boundary")
            detail_location = cls._value(policy_detail, "source_location")
            if detail:
                detail_label = (
                    "Source-recorded regional schedule"
                    if lane == "regional_nutrient_policy"
                    else "Source-recorded IPM method/options"
                )
                lines.append(f"  - {detail_label}: {detail}")
            if detail_conditions:
                lines.append(f"  - Source-recorded applicability: {detail_conditions}")
            if detail_boundary:
                lines.append(f"  - Safety boundary: {detail_boundary}")
            # A management bundle may cite one document for both nutrient and
            # IPM policy while the exact, source-recorded detail is on a
            # different page or section.  Preserve that narrower locator so
            # the displayed schedule/method remains auditable without making
            # the farmer infer which part of the source applies.
            if detail_location and detail_location != cls._value(item, "source_location"):
                lines.append(f"  - Source-recorded detail location: {detail_location}.")
        if conditions:
            lines.append(f"  - Required scope or condition: {conditions}")
        if missing:
            lines.append(f"  - Not established by this scenario: {missing}.")
        if lane == "source_quoted_operation":
            lines.append(
                "  - Current status: not issued as a farm action; it remains conditional until the required condition is observed."
            )
        elif lane == "regional_nutrient_policy":
            lines.append(
                "  - Safety boundary: This remains a regional policy reference; no field-specific dose is issued."
            )
        elif actionability:
            lines.append(f"  - Planning status: {actionability}.")
        elif status:
            lines.append(f"  - Planning status: {status}.")
        if source_quote:
            lines.append(f"  - Source wording: {source_quote}")
        lines.extend(cls._source_lines(item))
        return "\n".join(lines)

    @classmethod
    def _postharvest_plan_card(cls, item: Mapping[str, Any]) -> str:
        """Render one crop-scoped post-harvest item without activating it."""
        label = cls._value(item, "farmer_visible_label") or "Post-harvest handling"
        lines = [f"**Post-harvest plan — {label}**"]
        operation = cls._value(item, "operation_text")
        method = cls._value(item, "method_or_parameter")
        conditions = cls._value(item, "conditions_text")
        missing = cls._value(item, "missing_observation")
        source_quote = cls._value(item, "source_quote")
        if operation:
            lines.append(f"  - Operation: {operation}")
        if method:
            lines.append(f"  - Method or parameter: {method}")
        if conditions:
            lines.append(f"  - Required lot/harvest condition: {conditions}")
        if missing:
            lines.append(f"  - Not established by this scenario: {missing}.")
        lines.append(
            "  - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction."
        )
        if source_quote:
            lines.append(f"  - Source wording: {source_quote}")
        lines.extend(cls._source_lines(item))
        return "\n".join(lines)

    @classmethod
    def _facility_cards(cls, scenario: FrozenBenchmarkScenario) -> list[str]:
        """Render every captured facility candidate and its static route facts.

        Only fields actually retained by the fourth enrichment are shown.  In
        particular, a listed registry capacity is never described as vacant
        capacity, and route estimates are explicitly collection-time static
        geometry rather than a live dispatch instruction.
        """
        route_by_candidate = {
            cls._value(route, "candidate_id"): route
            for route in scenario.postharvest_static_route_context
            if cls._value(route, "candidate_id")
        }
        facility_rows = sorted(
            scenario.postharvest_site_facility_context,
            key=lambda row: (
                int(cls._value(row, "candidate_rank") or "0"),
                cls._value(row, "candidate_id"),
            ),
        )
        if not facility_rows:
            return []
        lines = [
            "**Storage/logistics context: source-linked facility and warehouse candidates**",
            "  - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.",
        ]
        for index, facility in enumerate(facility_rows, start=1):
            candidate_id = cls._value(facility, "candidate_id")
            name = cls._value(facility, "candidate_name") or "Unnamed source record"
            kind = cls._value(facility, "context_kind")
            district = cls._value(facility, "candidate_district")
            state = cls._value(facility, "candidate_state")
            lines.append(f"  {index}. **{name}**")
            if candidate_id:
                lines.append(f"     - Source record ID: {candidate_id}.")
            if kind:
                lines.append(f"     - Record type: {kind}.")
            if district or state:
                lines.append(f"     - Recorded location: {', '.join(bit for bit in (district, state) if bit)}.")
            registry_status = cls._value(facility, "candidate_registry_status")
            if registry_status:
                lines.append(f"     - Captured registry status: {registry_status}.")
            capacity = cls._value(facility, "candidate_capacity_mt")
            if capacity:
                lines.append(
                    f"     - Listed registry capacity: {capacity} MT; this is not current vacant capacity."
                )
            geodesic = cls._value(facility, "geodesic_km")
            if geodesic:
                lines.append(f"     - Captured straight-line distance: {geodesic} km.")
            route = route_by_candidate.get(candidate_id)
            if route:
                road_distance = cls._value(route, "road_distance_km")
                road_duration = cls._value(route, "road_duration_minutes")
                if road_distance or road_duration:
                    route_bits = []
                    if road_distance:
                        route_bits.append(f"{road_distance} km")
                    if road_duration:
                        route_bits.append(f"{road_duration} minutes")
                    lines.append(
                        "     - Captured static road-geometry estimate: "
                        + "; ".join(route_bits)
                        + ". It is not live traffic or a dispatch estimate."
                    )
                route_url = cls._value(route, "route_request_url")
                if route_url:
                    lines.append(f"     - Static-route source URL: {route_url}")
            temporal = cls._value(facility, "temporal_interpretation")
            if temporal:
                lines.append(f"     - Record scope: {temporal}")
            not_supported = cls._value(facility, "not_supported")
            if not_supported:
                lines.append(f"     - Not established: {not_supported}")
            lines.extend(f"     {line.strip()}" for line in cls._source_lines(facility))
        return ["\n".join(lines)]

    @classmethod
    def _claim_source_lines(
        cls,
        claim: TypedEvidenceClaim,
        *,
        title: str = "",
        fallback_url: str = "",
        fallback_locator: str = "",
    ) -> list[str]:
        """Render a claim citation without exposing internal trace-only fields."""
        return cls._source_lines({
            "source_document_id": claim.source.source_document_id or "",
            "source_title": title,
            # Context claims are constructed from a broad manifest.  Prefer a
            # source-specific frozen URL/locator supplied by the card so one
            # context domain can never inherit another domain's request URL.
            "source_url": fallback_url or claim.source.official_url,
            "source_location": fallback_locator or claim.source.locator,
        })

    @classmethod
    def _weather_context_card(
        cls,
        scenario: FrozenBenchmarkScenario,
        claim: TypedEvidenceClaim,
    ) -> str:
        """Render the complete frozen retrospective weather/water record."""
        values = scenario.water_context_features
        lines = ["**Historical weather and water context**"]
        lines.append(
            f"  - Historical decision window: {scenario.identity.decision_window_utc}; "
            f"source-observed days: {cls._value(values, 'weather_observed_days')}."
        )
        lines.append(
            "  - Air context: mean temperature "
            f"{cls._value(values, 'weather_t2m_mean_c')} °C; relative humidity "
            f"{cls._value(values, 'weather_rh2m_mean_percent')}%; wind speed "
            f"{cls._value(values, 'weather_ws2m_mean_m_s')} m/s; shortwave radiation "
            f"{cls._value(values, 'weather_shortwave_mean_mj_m2_day')} MJ/m²/day."
        )
        lines.append(
            "  - Water context: precipitation "
            f"{cls._value(values, 'weather_precipitation_total_mm')} mm; modelled root-zone wetness mean/min/max "
            f"{cls._value(values, 'water_gwetroot_mean_fraction')}/"
            f"{cls._value(values, 'water_gwetroot_min_fraction')}/"
            f"{cls._value(values, 'water_gwetroot_max_fraction')}; modelled top-layer wetness mean "
            f"{cls._value(values, 'water_gwettop_mean_fraction')}."
        )
        lines.append(
            "  - Water-balance context: land evaporation "
            f"{cls._value(values, 'water_land_evaporation_total_mm')} mm; precipitation minus land evaporation "
            f"{cls._value(values, 'water_precipitation_minus_land_evaporation_mm')} mm."
        )
        interpretation = cls._value(values, "water_context_interpretation")
        if interpretation:
            lines.append(f"  - Scope: {interpretation}")
        lines.append(
            "  - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast."
        )
        lines.extend(cls._claim_source_lines(
            claim,
            title="NASA POWER historical weather and modelled water context",
            fallback_url=cls._value(scenario.manifest, "weather_source_url"),
            fallback_locator=scenario.identity.decision_window_utc,
        ))
        return "\n".join(lines)

    @classmethod
    def _soil_context_card(
        cls,
        scenario: FrozenBenchmarkScenario,
        claim: TypedEvidenceClaim,
    ) -> str:
        """Render raw SoilGrids values with their recorded metadata semantics."""
        lines = ["**Static SoilGrids context (representative cell, 0–5 cm)**"]
        for row in sorted(scenario.registry_soil_profile, key=lambda item: cls._value(item, "property_id")):
            title = cls._value(row, "metadata_title") or cls._value(row, "property_id")
            raw_value = cls._value(row, "raw_value")
            conversion = cls._value(row, "conversion_note")
            line = f"  - {title}: source-reported raw value {raw_value}."
            if conversion:
                line += f" {conversion}"
            lines.append(line)
            request_url = cls._value(row, "metadata_request_url")
            if request_url:
                lines.append(f"    - Property source URL: {request_url}")
        lines.append(
            "  - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result."
        )
        first = scenario.registry_soil_profile[0] if scenario.registry_soil_profile else {}
        lines.extend(cls._claim_source_lines(
            claim,
            title="ISRIC SoilGrids static 0–5 cm profile",
            fallback_url=cls._value(first, "metadata_request_url"),
            fallback_locator=cls._value(first, "point_scope"),
        ))
        return "\n".join(lines)

    @classmethod
    def _satellite_context_card(
        cls,
        scenario: FrozenBenchmarkScenario,
        claim: TypedEvidenceClaim,
    ) -> str:
        """Render the admitted scene and chronology without crop-condition inference."""
        feature = scenario.satellite_context_features or {}
        chronology = scenario.ndvi_timeseries_features
        lines = ["**Historical Sentinel-2 / NDVI context (representative cell)**"]
        lines.append(
            f"  - Scene: {cls._value(feature, 'satellite_item_id')} acquired "
            f"{cls._value(feature, 'satellite_datetime_utc')}; pixel class "
            f"{cls._value(feature, 'satellite_scl_class')} ({cls._value(feature, 'satellite_scl_label')}); "
            f"quality {cls._value(feature, 'satellite_pixel_quality_status')}."
        )
        lines.append(
            "  - Scene values: red DN "
            f"{cls._value(feature, 'satellite_red_dn')}; NIR DN {cls._value(feature, 'satellite_nir_dn')}; "
            f"NDVI {cls._value(feature, 'satellite_ndvi')}."
        )
        lines.append(
            "  - Pre-decision chronology: "
            f"{cls._value(chronology, 'observation_count')} clear observations from "
            f"{cls._value(chronology, 'first_observation_utc')} to "
            f"{cls._value(chronology, 'last_observation_utc')} "
            f"({cls._value(chronology, 'time_span_days')} days); first/last NDVI "
            f"{cls._value(chronology, 'first_ndvi')}/{cls._value(chronology, 'last_ndvi')}; "
            f"change {cls._value(chronology, 'ndvi_change')}; slope "
            f"{cls._value(chronology, 'ndvi_linear_slope_per_day')} per day; recorded trend "
            f"{cls._value(chronology, 'ndvi_trend_direction')}."
        )
        catalog = cls._value(scenario.registry_sentinel, "catalog")
        collection = cls._value(scenario.registry_sentinel, "collection")
        if catalog or collection:
            lines.append(
                "  - Source record: "
                + "; ".join(bit for bit in (catalog, collection) if bit)
                + "."
            )
        interpretation = cls._value(feature, "satellite_condition_interpretation")
        if interpretation:
            lines.append(f"  - Scope: {interpretation}")
        lines.append(
            "  - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need."
        )
        lines.extend(cls._claim_source_lines(
            claim,
            title="Sentinel-2 L2A representative-cell context",
            fallback_locator=cls._value(feature, "satellite_item_id"),
        ))
        return "\n".join(lines)

    @classmethod
    def _satellite_unavailable_card(
        cls,
        scenario: FrozenBenchmarkScenario,
        claim: TypedEvidenceClaim,
    ) -> str:
        """Explain a quality-gated satellite absence without surfacing invalid NDVI."""
        feature = scenario.satellite_context_features or {}
        status = scenario.satellite_context_status
        lines = ["**Satellite / NDVI context status**"]
        item_id = cls._value(feature, "satellite_item_id")
        acquired = cls._value(feature, "satellite_datetime_utc")
        if item_id or acquired:
            lines.append(
                "  - Checked scene: "
                + "; ".join(bit for bit in (item_id, acquired) if bit)
                + "."
            )
        lines.append(
            "  - Quality status: "
            f"{cls._value(status, 'satellite_condition_status')}; pixel status "
            f"{cls._value(status, 'pixel_quality_status')}."
        )
        restriction = cls._value(status, "restriction_reason") or claim.block_reason or claim.summary
        if restriction:
            lines.append(f"  - No satellite/NDVI context is issued: {restriction}")
        lines.append(
            "  - Decision boundary: raw scene values and any limited chronology are withheld because the quality gate did not admit them as usable context."
        )
        lines.extend(cls._claim_source_lines(
            claim,
            title="Sentinel-2 L2A representative-cell quality-gate record",
            fallback_locator=item_id,
        ))
        return "\n".join(lines)

    @classmethod
    def _market_context_card(
        cls,
        scenario: FrozenBenchmarkScenario,
        claim: TypedEvidenceClaim,
    ) -> str:
        """Render all recorded historical market comparisons, not a sell/hold order."""
        values = scenario.market_context_features
        status = scenario.market_context_status
        registry = scenario.registry_market
        source_commodity = (
            cls._value(scenario.manifest, "market_source_commodity")
            or cls._value(registry, "source_commodity")
        )
        source_district = (
            cls._value(scenario.manifest, "market_source_district")
            or cls._value(registry, "source_district")
        )
        source_state = (
            cls._value(scenario.manifest, "market_source_state")
            or cls._value(registry, "source_state")
        )
        lines = ["**Historical nearest-mandi market context**"]
        lines.append(
            "  - Exact report values: decision-month mean "
            f"{cls._value(values, 'market_current_month_price_mean_as_reported')}; prior-month mean "
            f"{cls._value(values, 'market_previous_month_price_mean_as_reported')} "
            f"({cls._value(values, 'market_previous_month_change_percent')}% change); same-month prior-year mean "
            f"{cls._value(values, 'market_same_month_previous_year_price_mean_as_reported')} "
            f"({cls._value(values, 'market_same_month_year_over_year_percent')}% change)."
        )
        lines.append(
            "  - Report availability: "
            f"{cls._value(values, 'market_comparison_availability')}; price-unit status "
            f"{cls._value(scenario.features, 'market_price_unit_status')}; source commodity "
            f"{source_commodity} in {source_district}, {source_state}."
        )
        interpretation = cls._value(values, "market_context_interpretation")
        if interpretation:
            lines.append(f"  - Scope: {interpretation}")
        restriction = cls._value(status, "restriction_reason")
        if restriction:
            lines.append(f"  - Decision boundary: {restriction}")
        lines.extend(cls._claim_source_lines(
            claim,
            title="Agmarknet historical monthly report context",
            fallback_locator=f"decision date {scenario.identity.decision_date}",
        ))
        return "\n".join(lines)

    @classmethod
    def _market_unavailable_card(
        cls,
        scenario: FrozenBenchmarkScenario,
        claim: TypedEvidenceClaim,
    ) -> str:
        """Show the retained report value without inventing a missing comparison."""
        values = scenario.market_context_features
        status = scenario.market_context_status
        registry = scenario.registry_market
        source_commodity = (
            cls._value(scenario.manifest, "market_source_commodity")
            or cls._value(registry, "source_commodity")
        )
        source_district = (
            cls._value(scenario.manifest, "market_source_district")
            or cls._value(registry, "source_district")
        )
        source_state = (
            cls._value(scenario.manifest, "market_source_state")
            or cls._value(registry, "source_state")
        )
        lines = ["**Historical nearest-mandi market context**"]
        current_mean = cls._value(values, "market_current_month_price_mean_as_reported")
        if current_mean:
            lines.append(f"  - Source-recorded decision-month mean: {current_mean}.")
        lines.append(
            "  - Comparison status: "
            f"{cls._value(values, 'market_comparison_availability')}; "
            f"price-unit status {cls._value(scenario.features, 'market_price_unit_status')}; "
            f"source commodity {source_commodity} in {source_district}, {source_state}."
        )
        restriction = cls._value(status, "restriction_reason") or claim.block_reason or claim.summary
        if restriction:
            lines.append(f"  - No historical price comparison is issued: {restriction}")
        lines.append(
            "  - Decision boundary: the retained report does not support a current quotation, price forecast, sell/hold instruction, or farm-specific marketing decision."
        )
        lines.extend(cls._claim_source_lines(
            claim,
            title="Agmarknet historical monthly report context",
            fallback_locator=f"decision date {scenario.identity.decision_date}",
        ))
        return "\n".join(lines)

    @classmethod
    def _rag_excerpt_cards(
        cls,
        passages: Sequence[RetrievedPassage],
        *,
        question: str,
    ) -> list[str]:
        """Expose only a small, question-specific set of already-admitted passages."""
        if not question.strip():
            return []
        unique: list[RetrievedPassage] = []
        seen: set[tuple[str, str, str]] = set()
        for passage in passages:
            key = (passage.source_document_id, passage.locator, passage.text)
            if key not in seen:
                seen.add(key)
                unique.append(passage)
        if not unique:
            return []
        lines = ["**Question-specific official evidence excerpts**"]
        lines.append(f"  - Question: {question.strip()}")
        for index, passage in enumerate(unique[:2], start=1):
            lines.append(f"  {index}. **{passage.source_title or passage.source_document_id}**")
            lines.append(f"     - Official excerpt: {passage.text}")
            if passage.locator:
                lines.append(f"     - Source location: {passage.locator}.")
            lines.append(f"     - Source ID: {passage.source_document_id}.")
            if passage.official_url:
                lines.append(f"     - Source URL: {passage.official_url}")
        lines.append(
            "  - Scope: these passages are already metadata-admitted for this scenario and provide evidence context; retrieval does not authorize a farm action."
        )
        return ["\n".join(lines)]

    @staticmethod
    def _conflict_explanation_card(decision: BenchmarkDecision) -> list[str]:
        """Render a concise conclusion while retaining detailed records in the trace."""
        records = decision.conflict_resolution_records
        if not records:
            return []
        lines = ["**Evidence-resolution note**"]
        for record in records:
            if record.status == "handled_as_non_action_contextual_divergence":
                lines.append(
                    "  - Historical NDVI and weather context diverged. Both remain context only, so the regional plan and action boundary were unchanged."
                )
            else:
                lines.append(f"  - Resolution: {record.rationale}")
            if record.citations:
                lines.append(f"     - Supporting source IDs: {', '.join(record.citations)}.")
        lines.append(
            "  - The full accepted/rejected evidence path remains in the technical trace; this note reports only the farmer-relevant conclusion."
        )
        return ["\n".join(lines)]

    def render(
        self,
        scenario: FrozenBenchmarkScenario,
        decision: BenchmarkDecision,
        claims: Sequence[TypedEvidenceClaim],
        *,
        retrieved_passages: Sequence[RetrievedPassage] = (),
        question: str = "",
        coordinator_selected_fact_ids: Sequence[str] = (),
        presentation_selected_fact_ids: Sequence[str] = (),
        use_presentation_selection: bool = False,
    ) -> str:
        """Render only approved facts, using bounded selections for priority.

        The coordinator may reorder mandatory regional-plan cards. The farmer
        explanation role may prioritize context cards. It cannot suppress
        source-backed plan, context, citation, safety, or decision content.
        Neither selection can alter the deterministic decision status.
        """
        context_by_domain: dict[str, TypedEvidenceClaim] = {}
        for claim in claims:
            if claim.decision_domain in {
                DecisionDomain.WEATHER_CONTEXT,
                DecisionDomain.SOIL_CONTEXT,
                DecisionDomain.SATELLITE_CONTEXT,
                DecisionDomain.MARKET_CONTEXT,
            } and claim.disposition in {ClaimDisposition.CONTEXT, ClaimDisposition.NO_DATA}:
                context_by_domain.setdefault(claim.decision_domain.value, claim)
        weather = context_by_domain.get(DecisionDomain.WEATHER_CONTEXT.value)
        soil = context_by_domain.get(DecisionDomain.SOIL_CONTEXT.value)
        satellite = context_by_domain.get(DecisionDomain.SATELLITE_CONTEXT.value)
        market = context_by_domain.get(DecisionDomain.MARKET_CONTEXT.value)
        plan_items = sorted(
            scenario.regional_operation_plan_items,
            key=lambda item: (int(item.get("display_order", "0")), item.get("plan_item_id", "")),
        )
        policy_details_by_domain = {
            str(item.get("policy_domain", "")): item
            for item in scenario.regional_policy_detail_cards
        }
        lines = [
            f"Scenario: {scenario.identity.crop.title()} in {scenario.identity.district}, "
            f"{scenario.identity.state} ({scenario.identity.decision_date}).",
        ]
        core_sections: list[tuple[str, str]] = []
        selected_conditional = next(
            (
                claim
                for claim in claims
                if claim.disposition == ClaimDisposition.CONDITIONAL_OPERATION
                and claim.claim == decision.operation_text
            ),
            None,
        )
        if decision.direct_farm_action_issued:
            operation_text = f"Operation: {decision.operation_text}"
        elif decision.decision_status == "conditional_operation_pending_field_precondition":
            condition_text = (
                str(selected_conditional.metadata.get("conditions_text", "")).strip()
                if selected_conditional is not None
                else ""
            )
            if not condition_text and selected_conditional is not None:
                condition_text = selected_conditional.block_reason or ""
            source_text = (
                selected_conditional.source.source_document_id
                if selected_conditional is not None
                else ""
            )
            evidence_detail = " ".join(
                part
                for part in (
                    f"Required condition: {condition_text}" if condition_text else "",
                    f"Source: {source_text}." if source_text else "",
                )
                if part
            )
            operation_text = (
                f"Source-scoped regional operation: {decision.operation_text} "
                "It is not issued as a farm action; apply it only when its documented field condition is observed. "
                f"{evidence_detail}"
            )
        else:
            operation_text = (
                "Regional operation status: no time-valid source-quoted operation is available "
                "for this scenario date and scope."
            )
        core_sections.append(("decision:operation", operation_text))
        for item in plan_items:
            policy_domain = {
                "regional_nutrient_policy": "fertilizer",
                "regional_crop_protection_policy": "crop_protection",
            }.get(str(item.get("plan_lane", "")), "")
            core_sections.append((
                f"plan:{item.get('plan_item_id', '')}",
                self._regional_plan_card(item, policy_details_by_domain.get(policy_domain)),
            ))
        postharvest_items = sorted(
            scenario.postharvest_plan_items,
            key=lambda item: (int(item.get("display_order", "0")), item.get("plan_item_id", "")),
        )
        for item in postharvest_items:
            core_sections.append((
                f"postharvest:{item.get('plan_item_id', '')}",
                self._postharvest_plan_card(item),
            ))
        for facility_card in self._facility_cards(scenario):
            core_sections.append(("postharvest:infrastructure-context", facility_card))
        lines.extend(self._order_sections(core_sections, coordinator_selected_fact_ids))

        # These historical cards are complete representations of facts already
        # admitted by the frozen loader.  The bounded LLM may only move a card
        # forward; it cannot hide available source-backed context from farmers.
        context_sections: list[tuple[str, str]] = []
        if weather:
            context_sections.append(("context:weather", self._weather_context_card(scenario, weather)))
        if soil:
            context_sections.append(("context:soil", self._soil_context_card(scenario, soil)))
        if satellite:
            context_sections.append((
                "context:satellite",
                self._satellite_context_card(scenario, satellite)
                if satellite.disposition == ClaimDisposition.CONTEXT
                else self._satellite_unavailable_card(scenario, satellite),
            ))
        if market:
            context_sections.append((
                "context:market",
                self._market_context_card(scenario, market)
                if market.disposition == ClaimDisposition.CONTEXT
                else self._market_unavailable_card(scenario, market),
            ))
        lines.extend(
            self._order_sections(
                context_sections,
                presentation_selected_fact_ids if use_presentation_selection else (),
            )
        )

        lines.extend(self._rag_excerpt_cards(retrieved_passages, question=question))
        lines.extend(self._conflict_explanation_card(decision))
        if decision.uncertainty_reasons:
            lines.append("Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.")
        lines.append(f"Evidence trace: {', '.join(decision.citations[:8]) or 'no cited source identifier'}.")
        return "\n".join(lines)

    def run(
        self,
        scenario: FrozenBenchmarkScenario,
        *,
        decision: BenchmarkDecision,
        claims: Sequence[TypedEvidenceClaim] = (),
        message: str | None = None,
        retrieved_passages: Sequence[RetrievedPassage] = (),
        question: str = "",
        coordinator_selected_fact_ids: Sequence[str] = (),
        presentation_selected_fact_ids: Sequence[str] = (),
        use_presentation_selection: bool = False,
        **_: Any,
    ):
        message = message or self.render(
            scenario,
            decision,
            claims,
            retrieved_passages=retrieved_passages,
            question=question,
            coordinator_selected_fact_ids=coordinator_selected_fact_ids,
            presentation_selected_fact_ids=presentation_selected_fact_ids,
            use_presentation_selection=use_presentation_selection,
        )
        return (
            self._claim(
                scenario,
                decision_domain=DecisionDomain.SYSTEM_SAFETY,
                disposition=ClaimDisposition.CONTEXT,
                allowed_use=AllowedUse.CONTEXT_ONLY,
                claim="A farmer-facing explanation was rendered from the coordinator trace only.",
                summary=f"Rendered {decision.decision_status} with {len(decision.citations)} citation identifier(s).",
                reasoning=(
                    "The renderer preserves the coordinator's action status and does not introduce "
                    "a recommendation, diagnosis, dose, forecast, or uncited source."
                ),
                confidence=1.0,
                source=internal_trace_citation(
                    source_document_id="BENCHMARK_COORDINATOR_TRACE",
                    source_role="farmer_explanation_trace",
                ),
                quality="deterministic citation-preserving rendering",
                gate_result=GateResult.PASS,
                metadata={"farmer_message": message, "citations": decision.citations},
            ),
        )
