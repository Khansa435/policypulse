"""
Orchestrator agent for the PolicyPulse pipeline.

Examines raw unstructured text and decides whether it is operationally relevant
to the business. If relevant, it signals the pipeline to proceed and names the
specialist agents to invoke; otherwise it halts the pipeline early.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from agents.base_agent import AgentResponse, BaseAgent, OrchestratorOutput


logger = logging.getLogger(__name__)


ORCHESTRATOR_SYSTEM_PROMPT = """You are the PolicyPulse Orchestrator Agent. Your role is to examine incoming unstructured text (which may be news articles, regulatory filings, internal operations memos, or spam/irrelevant reports) and determine if it has operational or financial relevance to our business (which deals with e-commerce, sales, catalog SKUs, delivery logistics, and customer service).

If the text contains actionable information regarding pricing, sales trends, regional logistics, courier fuel adjustments, or customer tickets, set "should_halt" to false and list all 5 specialist agents: ["ingestion", "insight", "impact", "actions", "execution"] in "agents_invoked".
If the text is irrelevant spam, gossip, or general interest news that does not affect business operations, set "should_halt" to true and leave "agents_invoked" empty.

Provide an honest confidence score between 0.0 and 1.0 reflecting how clear the decision is. Explain your reasoning in exactly 2-3 sentences in the "reason" field.

Return ONLY a valid JSON object. Do not include markdown formatting or backticks around the JSON."""


class OrchestratorAgent(BaseAgent):
    """Routes the pipeline: decides whether to halt or invoke the specialists."""

    def __init__(self) -> None:
        super().__init__(
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            agent_name="orchestrator",
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
            logger.warning("Orchestrator Gemini call failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Failed to obtain a valid response from Gemini: {exc}",
            )

        if not isinstance(raw, dict):
            logger.warning(
                "Orchestrator expected a JSON object, got %s", type(raw).__name__
            )
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini returned a non-object JSON payload; cannot route the "
                    "pipeline."
                ),
            )

        try:
            parsed = OrchestratorOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Orchestrator output validation failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini response did not match the OrchestratorOutput schema "
                    f"(missing/invalid fields): {exc.error_count()} error(s)."
                ),
            )

        confidence = float(raw.get("confidence", 0.9))
        model_reason = raw.get("reason") or parsed.reason

        if parsed.should_halt:
            reasoning = (
                f"Document is not business-relevant, halting pipeline. {model_reason}"
            ).strip()
        else:
            reasoning = (
                "Document classified as business-relevant; pipeline proceeding. "
                f"{model_reason}"
            ).strip()

        return self._make_response(
            output=parsed,
            confidence=confidence,
            reasoning=reasoning,
        )
