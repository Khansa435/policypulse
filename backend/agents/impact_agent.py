"""
Impact agent for the PolicyPulse pipeline.

Performs quantitative financial and operational impact calculations by
combining the upstream Ingestion and Insight outputs with the CURRENT business
state from mock_db.json. It is required to ground its numbers (affected SKUs,
daily orders, projected loss, margin compression) in the real database state
rather than hallucinating figures.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from agents.base_agent import AgentResponse, BaseAgent, ImpactOutput


logger = logging.getLogger(__name__)


IMPACT_SYSTEM_PROMPT = """You are the PolicyPulse Impact Agent. Your role is to perform quantitative calculations by combining the Ingestion and Insight outputs with the current business state (`mock_db.json`).

Analyze the database metrics:
- Active SKUs, daily order counts, average ticket size, and customer regions.
Calculate:
1. "affected_skus": Number of products affected (e.g. if the incident is regional, select SKUs or set to 0 if overall catalog is unaffected. For logistics/shipping changes, calculate SKUs exposed to courier fees).
2. "affected_daily_orders": Number of daily orders in the scope region or categories.
3. "projected_daily_loss_pkr": Estimate the daily financial cost increase or revenue loss based on the magnitude of the incident.
4. "margin_compression_pct": The percentage reduction in operating margins (e.g., if delivery cost increases by Rs. 37.5 per order on Rs. 1100 average ticket, that is roughly 3.4% margin compression. Adjust based on severity).

Clearly explain your math in the reasoning field. Return ONLY a valid JSON object. Do not include markdown formatting or backticks."""


class ImpactAgent(BaseAgent):
    """Computes grounded financial/operational impact against real DB state."""

    def __init__(self) -> None:
        super().__init__(
            system_prompt=IMPACT_SYSTEM_PROMPT,
            agent_name="impact",
        )

    def run(
        self,
        input_data: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        text = input_data.get("text", "")
        context = context or {}
        ingestion = context.get("ingestion", {})
        insight = context.get("insight", {})
        mock_db_state = context.get("mock_db_state", {})

        user_input = (
            "ORIGINAL TEXT:\n"
            f"{text}\n\n"
            "INGESTION AGENT OUTPUT:\n"
            f"{json.dumps(ingestion, indent=2, default=str)}\n\n"
            "INSIGHT AGENT OUTPUT:\n"
            f"{json.dumps(insight, indent=2, default=str)}\n\n"
            "CURRENT BUSINESS STATE (mock_db.json) — use these REAL numbers, "
            "do not invent figures:\n"
            f"{json.dumps(mock_db_state, indent=2, default=str)}"
        )

        try:
            raw = self._call_gemini(user_input)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Impact Gemini call failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Failed to obtain a valid response from Gemini: {exc}",
            )

        if not isinstance(raw, dict):
            logger.warning(
                "Impact expected a JSON object, got %s", type(raw).__name__
            )
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini returned a non-object JSON payload; cannot compute "
                    "impact figures."
                ),
            )

        try:
            parsed = ImpactOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Impact output validation failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini response did not match the ImpactOutput schema "
                    f"(missing/invalid fields): {exc.error_count()} error(s)."
                ),
            )

        confidence = float(raw.get("confidence", 0.9))
        model_reason = raw.get("reasoning", "")

        reasoning = (
            f"Impact computed against current state: affected_skus="
            f"{parsed.affected_skus}, affected_daily_orders="
            f"{parsed.affected_daily_orders}, projected_daily_loss_pkr="
            f"{parsed.projected_daily_loss_pkr}, margin_compression_pct="
            f"{parsed.margin_compression_pct}. {model_reason}"
        ).strip()

        return self._make_response(
            output=parsed,
            confidence=confidence,
            reasoning=reasoning,
        )
