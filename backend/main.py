"""
PolicyPulse FastAPI backend.

Exposes health, state inspection, and reset endpoints over the local JSON mock
database. The /analyze endpoint is intentionally not wired up yet — it will be
added once the agent pipeline is in place.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
