"""
Base agent abstractions and Pydantic schemas for the PolicyPulse pipeline.

Defines the shared data contracts exchanged between the six agents
(orchestrator, ingestion, insight, impact, actions, execution) and the
abstract BaseAgent each concrete agent extends. Concrete agents call Gemini
through the shared gemini_client.call_gemini helper, wrapped here as
_call_gemini, and emit a uniformly timestamped AgentResponse via _make_response.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from gemini_client import call_gemini


class AgentResponse(BaseModel):
    agent_name: str
    output: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    timestamp: str


class AnalyzeRequest(BaseModel):
    text: str
    scenario_hint: Optional[str] = "auto"


class OrchestratorOutput(BaseModel):
    should_halt: bool
    reason: str
    agents_invoked: List[str]


class IngestionOutput(BaseModel):
    event_type: str
    magnitude_pct: Optional[float] = None
    effective_date: Optional[str] = None
    scope: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class InsightOutput(BaseModel):
    insight: str
    implications: List[str]


class ImpactOutput(BaseModel):
    affected_skus: Optional[int] = None
    affected_daily_orders: Optional[int] = None
    projected_daily_loss_pkr: Optional[float] = None
    margin_compression_pct: Optional[float] = None
    revenue_loss_weekly_pkr: Optional[float] = None
    churn_risk: Optional[str] = None
    customer_count_affected: Optional[int] = None
    notes: str = ""


class ActionItem(BaseModel):
    rank: int
    action: str
    expected_impact: str
    rationale: str


class ActionOutput(BaseModel):
    actions: List[ActionItem]


class ExecutionDiffEntry(BaseModel):
    path: str
    old: Any = None
    new: Any = None


class ExecutionOutput(BaseModel):
    action_taken: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    diff: List[ExecutionDiffEntry]
    log_entry_id: str


class PipelineResponse(BaseModel):
    request_id: str
    input_text: str
    orchestrator: AgentResponse
    ingestion: Optional[AgentResponse] = None
    insight: Optional[AgentResponse] = None
    impact: Optional[AgentResponse] = None
    actions: Optional[AgentResponse] = None
    execution: Optional[AgentResponse] = None
    agent_trace: List[AgentResponse]
    total_duration_ms: int


class BaseAgent(ABC):
    """
    Abstract base for every agent in the pipeline.

    Subclasses receive a fixed system_prompt and a human-readable agent_name,
    then implement run() to transform input_data (and optional shared context)
    into an AgentResponse. The _call_gemini and _make_response helpers keep the
    Gemini call site and response shape consistent across all agents.
    """

    def __init__(self, system_prompt: str, agent_name: str) -> None:
        self.system_prompt = system_prompt
        self.agent_name = agent_name

    @abstractmethod
    def run(
        self,
        input_data: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        """Execute the agent and return its structured response."""
        raise NotImplementedError

    def _call_gemini(self, user_input: str) -> dict | list:
        """Send user_input to Gemini under this agent's system prompt."""
        return call_gemini(self.system_prompt, user_input)

    def _make_response(
        self,
        output: Any,
        confidence: float,
        reasoning: str,
    ) -> AgentResponse:
        """Wrap an agent's output in a timestamped AgentResponse."""
        return AgentResponse(
            agent_name=self.agent_name,
            output=output,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
