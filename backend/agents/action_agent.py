"""
Action agent for the PolicyPulse pipeline.

Proposes three ranked, concrete mitigation actions in response to an incident,
grounded in the upstream Ingestion, Insight, and Impact outputs plus the current
business state. Each action carries a quantified expected impact and a rationale
for its ranking.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from agents.base_agent import AgentResponse, ActionOutput, BaseAgent


logger = logging.getLogger(__name__)


ACTION_SYSTEM_PROMPT = """You are the PolicyPulse Action Agent. Your job is to propose exactly 3 alternative mitigation actions for the business, ranked 1 (best) to 3 (least preferred).

You are given the original document text plus the upstream Ingestion, Insight, and Impact outputs and the current business state (mock_db.json). Use the real impact figures to size your recommendations.

Return a JSON object with this exact shape:
{
  "actions": [
    {
      "rank": 1,
      "action": "concrete operational action to take",
      "expected_impact": "quantified benefit, e.g. 'Recovers ~Rs.45,000/day in margin'",
      "rationale": "why this action ranks where it does relative to the others"
    }
  ],
  "confidence": 0.0,
  "reasoning": "2-3 sentences explaining why Rank 1 was preferred"
}

Provide EXACTLY 3 actions with ranks 1, 2, and 3 (no duplicates). Rank the action with the highest recovery potential and lowest customer friction as Rank 1. Each "expected_impact" must include a concrete number where possible. Provide an honest confidence between 0.0 and 1.0.

Return ONLY a valid JSON object. Do not include markdown formatting or backticks."""


class ActionAgent(BaseAgent):
    """Proposes three ranked mitigation actions grounded in upstream analysis."""

    def __init__(self) -> None:
        super().__init__(
            system_prompt=ACTION_SYSTEM_PROMPT,
            agent_name="actions",
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
        impact = context.get("impact", {})
        mock_db_state = context.get("mock_db_state", {})

        user_input = (
            "ORIGINAL TEXT:\n"
            f"{text}\n\n"
            "INGESTION AGENT OUTPUT:\n"
            f"{json.dumps(ingestion, indent=2, default=str)}\n\n"
            "INSIGHT AGENT OUTPUT:\n"
            f"{json.dumps(insight, indent=2, default=str)}\n\n"
            "IMPACT AGENT OUTPUT:\n"
            f"{json.dumps(impact, indent=2, default=str)}\n\n"
            "CURRENT BUSINESS STATE (mock_db.json):\n"
            f"{json.dumps(mock_db_state, indent=2, default=str)}"
        )

        try:
            raw = self._call_gemini(user_input)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Action Gemini call failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Failed to obtain a valid response from Gemini: {exc}",
            )

        if not isinstance(raw, dict):
            logger.warning(
                "Action expected a JSON object, got %s", type(raw).__name__
            )
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini returned a non-object JSON payload; cannot produce "
                    "ranked actions."
                ),
            )

        try:
            parsed = ActionOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Action output validation failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini response did not match the ActionOutput schema "
                    f"(missing/invalid fields): {exc.error_count()} error(s)."
                ),
            )

        confidence = float(raw.get("confidence", 0.9))
        model_reason = raw.get("reasoning", "")

        ranked = sorted(parsed.actions, key=lambda a: a.rank)
        top = ranked[0].action if ranked else "n/a"
        reasoning = (
            f"Proposed {len(parsed.actions)} ranked action(s); Rank 1: {top}. "
            f"{model_reason}"
        ).strip()

        return self._make_response(
            output=parsed,
            confidence=confidence,
            reasoning=reasoning,
        )
