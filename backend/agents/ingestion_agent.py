"""
Ingestion agent for the PolicyPulse pipeline.

Converts unstructured incident logs, reports, or articles into structured
variables: event type, percentage magnitude, effective date, geographic scope,
and any raw numeric details. Acts as the quantitative parameter extractor for
downstream agents.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from agents.base_agent import AgentResponse, BaseAgent, IngestionOutput


logger = logging.getLogger(__name__)


INGESTION_SYSTEM_PROMPT = """You are the PolicyPulse Ingestion Agent. Your role is to convert unstructured incident logs, reports, or articles into structured variables. You must extract:
- The event type (e.g., fuel price changes, sales metrics shifts, CS ticket spikes).
- The percentage magnitude of change (as a float).
- The effective timeline/date.
- The geographic or regional scope (e.g., nationwide, Lahore, Karachi).
- Any specific raw numeric details (e.g., price values per unit, raw order volumes).

If a specific metric or date is missing, do your best to infer it or omit it from details. Assign a lower confidence score if key metrics are missing. Explain your extraction logic in 2-3 sentences.

Return ONLY a valid JSON object. Do not include markdown formatting or backticks."""


class IngestionAgent(BaseAgent):
    """Extracts structured event parameters from raw unstructured text."""

    def __init__(self) -> None:
        super().__init__(
            system_prompt=INGESTION_SYSTEM_PROMPT,
            agent_name="ingestion",
        )

    def run(
        self,
        input_data: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        text = input_data.get("text", "")

        try:
            raw = self._call_gemini(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ingestion Gemini call failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Failed to obtain a valid response from Gemini: {exc}",
            )

        if not isinstance(raw, dict):
            logger.warning(
                "Ingestion expected a JSON object, got %s", type(raw).__name__
            )
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini returned a non-object JSON payload; cannot extract "
                    "structured event data."
                ),
            )

        try:
            parsed = IngestionOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Ingestion output validation failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini response did not match the IngestionOutput schema "
                    f"(missing/invalid fields): {exc.error_count()} error(s)."
                ),
            )

        confidence = float(raw.get("confidence", 0.9))
        model_reason = raw.get("reasoning", "")

        magnitude = (
            f"{parsed.magnitude_pct}%" if parsed.magnitude_pct is not None else "n/a"
        )
        reasoning = (
            f"Extracted event_type='{parsed.event_type}', magnitude={magnitude}, "
            f"effective_date='{parsed.effective_date}', scope='{parsed.scope}'. "
            f"{model_reason}"
        ).strip()

        return self._make_response(
            output=parsed,
            confidence=confidence,
            reasoning=reasoning,
        )
