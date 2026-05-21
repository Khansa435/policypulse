"""
PolicyPulse FastAPI backend.

Exposes health, state inspection, reset, and the full six-agent /analyze
pipeline over the local JSON mock database.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.action_agent import ActionAgent
from agents.base_agent import AgentResponse, AnalyzeRequest, PipelineResponse
from agents.execution_agent import ExecutionAgent
from agents.impact_agent import ImpactAgent
from agents.ingestion_agent import IngestionAgent
from agents.insight_agent import InsightAgent
from agents.orchestrator_agent import OrchestratorAgent


BASE_DIR = Path(__file__).resolve().parent
MOCK_DB_PATH = BASE_DIR / "mock_db.json"
MOCK_DB_BAK_PATH = BASE_DIR / "mock_db.bak.json"
ACTION_LOG_PATH = BASE_DIR / "action_log.json"

load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PolicyPulse Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

db_lock = asyncio.Lock()

orchestrator = OrchestratorAgent()
ingestion = IngestionAgent()
insight = InsightAgent()
impact = ImpactAgent()
action = ActionAgent()
execution = ExecutionAgent()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_to_dict(response: AgentResponse | None) -> dict:
    """Normalize an agent response's output into a plain dict for downstream context."""
    if response is None or response.output is None:
        return {}
    output = response.output
    if isinstance(output, BaseModel):
        return output.model_dump()
    if isinstance(output, dict):
        return output
    return {}


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _error_response(message: str, status: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": _now_iso()}


@app.get("/state")
async def get_state() -> Any:
    try:
        return _read_json(MOCK_DB_PATH)
    except FileNotFoundError:
        logger.exception("mock_db.json not found at %s", MOCK_DB_PATH)
        return _error_response(f"mock_db.json not found at {MOCK_DB_PATH}")
    except json.JSONDecodeError as e:
        logger.exception("mock_db.json is not valid JSON")
        return _error_response(f"mock_db.json is not valid JSON: {e}")


@app.get("/log")
async def get_log() -> Any:
    try:
        return _read_json(ACTION_LOG_PATH)
    except FileNotFoundError:
        logger.exception("action_log.json not found at %s", ACTION_LOG_PATH)
        return _error_response(
            f"action_log.json not found at {ACTION_LOG_PATH}"
        )
    except json.JSONDecodeError as e:
        logger.exception("action_log.json is not valid JSON")
        return _error_response(f"action_log.json is not valid JSON: {e}")


@app.post("/reset")
async def reset() -> Any:
    async with db_lock:
        try:
            backup = _read_json(MOCK_DB_BAK_PATH)
        except FileNotFoundError:
            logger.exception("mock_db.bak.json missing — cannot reset")
            return _error_response(
                f"mock_db.bak.json not found at {MOCK_DB_BAK_PATH}; "
                "cannot reset"
            )
        except json.JSONDecodeError as e:
            logger.exception("mock_db.bak.json is not valid JSON")
            return _error_response(
                f"mock_db.bak.json is not valid JSON: {e}; cannot reset"
            )

        try:
            _write_json(MOCK_DB_PATH, backup)
            _write_json(ACTION_LOG_PATH, [])
        except OSError as e:
            logger.exception("Failed to write reset state")
            return _error_response(f"Failed to write reset state: {e}")

        logger.info(
            "Mock DB reset from %s; action log cleared",
            MOCK_DB_BAK_PATH.name,
        )
        return {"status": "reset_complete", "timestamp": _now_iso()}


@app.post("/analyze", response_model=PipelineResponse)
async def analyze(request: AnalyzeRequest) -> Any:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    text = request.text
    agent_trace: list[AgentResponse] = []

    def _elapsed_ms() -> int:
        return int((time.perf_counter() - start) * 1000)

    try:
        # STEP A — orchestrator: decide relevance / whether to halt.
        logger.info("[%s] orchestrator start", request_id)
        orchestrator_response = await asyncio.to_thread(
            orchestrator.run, {"text": text}, None
        )
        agent_trace.append(orchestrator_response)
        logger.info(
            "[%s] orchestrator end confidence=%s",
            request_id,
            orchestrator_response.confidence,
        )

        should_halt = bool(
            getattr(orchestrator_response.output, "should_halt", False)
        )
        if should_halt:
            logger.info("[%s] orchestrator halted pipeline", request_id)
            return PipelineResponse(
                request_id=request_id,
                input_text=text,
                orchestrator=orchestrator_response,
                agent_trace=agent_trace,
                total_duration_ms=_elapsed_ms(),
            )

        # STEP B — ingestion: extract structured event facts.
        logger.info("[%s] ingestion start", request_id)
        ingestion_response = await asyncio.to_thread(
            ingestion.run, {"text": text}, None
        )
        agent_trace.append(ingestion_response)
        logger.info(
            "[%s] ingestion end confidence=%s",
            request_id,
            ingestion_response.confidence,
        )
        ingestion_dict = _output_to_dict(ingestion_response)

        # STEP C — snapshot the current DB state under the lock, then release.
        async with db_lock:
            try:
                mock_db_state = _read_json(MOCK_DB_PATH)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.exception(
                    "[%s] could not read mock_db.json snapshot", request_id
                )
                mock_db_state = {}

        # STEP D — insight: qualitative takeaways from ingestion.
        logger.info("[%s] insight start", request_id)
        insight_response = await asyncio.to_thread(
            insight.run,
            {"text": text},
            {"ingestion": ingestion_dict},
        )
        agent_trace.append(insight_response)
        logger.info(
            "[%s] insight end confidence=%s",
            request_id,
            insight_response.confidence,
        )
        insight_dict = _output_to_dict(insight_response)

        # STEP E — impact: quantitative impact against real DB state.
        logger.info("[%s] impact start", request_id)
        impact_response = await asyncio.to_thread(
            impact.run,
            {"text": text},
            {
                "ingestion": ingestion_dict,
                "insight": insight_dict,
                "mock_db_state": mock_db_state,
            },
        )
        agent_trace.append(impact_response)
        logger.info(
            "[%s] impact end confidence=%s",
            request_id,
            impact_response.confidence,
        )
        impact_dict = _output_to_dict(impact_response)

        # STEP F — action: three ranked mitigation actions.
        logger.info("[%s] action start", request_id)
        action_response = await asyncio.to_thread(
            action.run,
            {"text": text},
            {
                "ingestion": ingestion_dict,
                "insight": insight_dict,
                "impact": impact_dict,
                "mock_db_state": mock_db_state,
            },
        )
        agent_trace.append(action_response)
        logger.info(
            "[%s] action end confidence=%s",
            request_id,
            action_response.confidence,
        )
        action_dict = _output_to_dict(action_response)

        # STEP G — execution: plan + simulate the Rank 1 mutation.
        logger.info("[%s] execution start", request_id)
        execution_response = await asyncio.to_thread(
            execution.run,
            {"text": text},
            {"actions": action_dict, "mock_db_state": mock_db_state},
        )
        agent_trace.append(execution_response)
        logger.info(
            "[%s] execution end confidence=%s",
            request_id,
            execution_response.confidence,
        )

        # STEP H — persist the mutated state and append an audit log entry.
        execution_output = execution_response.output
        if execution_output is not None:
            async with db_lock:
                try:
                    _write_json(MOCK_DB_PATH, execution_output.after_state)

                    try:
                        log = _read_json(ACTION_LOG_PATH)
                        if not isinstance(log, list):
                            log = []
                    except (FileNotFoundError, json.JSONDecodeError):
                        log = []

                    log.append(
                        {
                            "log_entry_id": execution_output.log_entry_id,
                            "request_id": request_id,
                            "timestamp": _now_iso(),
                            "action_taken": execution_output.action_taken,
                            "agent_trace_summary": [
                                {
                                    "agent_name": r.agent_name,
                                    "confidence": r.confidence,
                                }
                                for r in agent_trace
                            ],
                        }
                    )
                    _write_json(ACTION_LOG_PATH, log)
                    logger.info(
                        "[%s] persisted after_state; logged entry %s",
                        request_id,
                        execution_output.log_entry_id,
                    )
                except OSError:
                    logger.exception(
                        "[%s] failed to persist execution result", request_id
                    )
        else:
            logger.warning(
                "[%s] execution produced no output; skipping persistence",
                request_id,
            )

        # STEP I — assemble the full pipeline response.
        return PipelineResponse(
            request_id=request_id,
            input_text=text,
            orchestrator=orchestrator_response,
            ingestion=ingestion_response,
            insight=insight_response,
            impact=impact_response,
            actions=action_response,
            execution=execution_response,
            agent_trace=agent_trace,
            total_duration_ms=_elapsed_ms(),
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("[%s] /analyze pipeline failed", request_id)
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "request_id": request_id},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
