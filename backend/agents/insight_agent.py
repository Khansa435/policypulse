"""
Insight agent for the PolicyPulse pipeline.

Interprets the structured Ingestion output qualitatively: it identifies the
primary operational driver, the bottleneck, a severity level, and a qualitative
assessment of how the incident affects day-to-day operations. Receives both the
original text and the upstream ingestion output as context.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from agents.base_agent import AgentResponse, BaseAgent, InsightOutput


logger = logging.getLogger(__name__)


INSIGHT_SYSTEM_PROMPT = """You are the PolicyPulse Insight Agent. Your role is to translate structured business event data into qualitative operational takeaways — the "so what" behind the numbers.

Given the original document text and the upstream Ingestion output (event_type, magnitude_pct, scope, etc.), produce:
- `insight`: a single 1-2 sentence statement capturing the core operational implication. Focus on the bottleneck, the at-risk segment, or the primary driver. Be specific, not generic. Example: "Delivery cost per order rises ~12%, making sub-Rs.800 orders structurally unprofitable at current pricing."
- `implications`: a list of 2-4 short bullet-style strings, each naming a downstream operational consequence the business will face (e.g., "Margin compression on small-ticket orders", "Customer trust risk if delivery fees rise without notice", "Supplier renegotiation likely needed within 7 days").
- `confidence`: a float 0.0-1.0 reflecting how confident you are in the insight given the input quality.
- `reasoning`: 2-3 sentences explaining how you arrived at this insight from the upstream data.

If the upstream ingestion data is sparse or ambiguous, return a lower confidence (0.5-0.7) and acknowledge the gap in `reasoning`.

Return ONLY a valid JSON object with keys: insight, implications, confidence, reasoning. Do not include markdown formatting or backticks."""


class InsightAgent(BaseAgent):
    """Translates quantitative ingestion facts into a qualitative diagnosis."""

    def __init__(self) -> None:
        super().__init__(
            system_prompt=INSIGHT_SYSTEM_PROMPT,
            agent_name="insight",
        )

    def run(
        self,
        input_data: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        text = input_data.get("text", "")
        context = context or {}
        ingestion = context.get("ingestion", {})

        user_input = (
            "ORIGINAL TEXT:\n"
            f"{text}\n\n"
            "INGESTION AGENT OUTPUT (structured facts):\n"
            f"{json.dumps(ingestion, indent=2, default=str)}"
        )

        try:
            raw = self._call_gemini(user_input)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Insight Gemini call failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Failed to obtain a valid response from Gemini: {exc}",
            )

        if not isinstance(raw, dict):
            logger.warning(
                "Insight expected a JSON object, got %s", type(raw).__name__
            )
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini returned a non-object JSON payload; cannot produce a "
                    "qualitative assessment."
                ),
            )

        try:
            parsed = InsightOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Insight output validation failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini response did not match the InsightOutput schema "
                    f"(missing/invalid fields): {exc.error_count()} error(s)."
                ),
            )

        confidence = float(raw.get("confidence", 0.9))
        model_reason = raw.get("reasoning", "")

        reasoning = (
            f"Qualitative takeaway: {parsed.insight} "
            f"({len(parsed.implications)} implication(s) identified). "
            f"{model_reason}"
        ).strip()

        return self._make_response(
            output=parsed,
            confidence=confidence,
            reasoning=reasoning,
        )
