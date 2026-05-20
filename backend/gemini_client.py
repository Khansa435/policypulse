"""
Gemini client wrapper for PolicyPulse.

Loads GEMINI_API_KEY from backend/.env at import time, configures the
google-generativeai SDK with a flash-tier model (preferring gemini-2.5-flash,
falling back to gemini-1.5-flash if the preferred name is rejected), and
exposes call_gemini() — a single entry point that returns a parsed JSON dict
from the model. Markdown fences and surrounding prose are stripped from the
response; transient API errors are retried with exponential backoff via
tenacity; JSON parsing failures surface as ValueError with the raw response
embedded for debugging (they are NOT retried, since they indicate a model
output problem rather than a network problem).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

_API_KEY: str = os.environ.get("GEMINI_API_KEY", "").strip()
if not _API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing or empty. "
        f"Set it in {_ENV_PATH} (see .env.example) or export it in the "
        "environment before importing this module."
    )

genai.configure(api_key=_API_KEY)


_PREFERRED_MODEL: str = "gemini-2.5-flash"
_FALLBACK_MODEL: str = "gemini-1.5-flash"
_active_model_name: str = _PREFERRED_MODEL


def _looks_like_model_not_found(err: Exception) -> bool:
    text = f"{type(err).__name__}: {err}".lower()
    return any(
        marker in text
        for marker in ("not found", "404", "invalid model", "unsupported model")
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _generate_raw(
    model_name: str,
    system_prompt: str,
    user_input: str,
    temperature: float,
) -> str:
    logger.info(
        "Gemini call: model=%s system_len=%d user_len=%d temp=%s",
        model_name,
        len(system_prompt),
        len(user_input),
        temperature,
    )
    config: dict[str, Any] = {"temperature": temperature}
    try:
        model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
        response = model.generate_content(user_input, generation_config=config)
    except TypeError:
        # SDK too old for system_instruction kwarg — fall back to prepending.
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            f"{system_prompt}\n\n{user_input}",
            generation_config=config,
        )
    return response.text


def _parse_json_response(raw: str) -> Any:
    text = raw.strip()
    text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    logger.warning("Direct JSON parse failed; attempting regex extraction")
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise ValueError(
                "Failed to parse Gemini response as JSON after fence-stripping "
                f"and regex extraction. Underlying error: {e}. "
                f"Raw response:\n{raw!r}"
            ) from e

    raise ValueError(
        "No JSON object or array could be extracted from Gemini response. "
        f"Raw response:\n{raw!r}"
    )


def call_gemini(
    system_prompt: str,
    user_input: str,
    temperature: float = 0.1,
) -> dict:
    """
    Send a structured request to Gemini and return the parsed JSON response.

    system_prompt is passed as the model's system_instruction when supported,
    otherwise prepended to user_input. temperature defaults to 0.1 to keep
    JSON output deterministic. The response text is stripped of markdown
    fences (```json … ```) and any leading/trailing prose before json.loads;
    if that fails, a regex pass extracts the first {…} or […] block and
    retries. Transient API errors are retried up to 3 times with exponential
    backoff (1–8s). On unrecoverable model rejection of gemini-2.5-flash, the
    client switches permanently to gemini-1.5-flash and retries the call.
    JSON parsing errors are NOT retried and surface as ValueError with the
    raw response embedded for debugging.
    """
    global _active_model_name

    try:
        raw = _generate_raw(
            _active_model_name, system_prompt, user_input, temperature
        )
    except Exception as e:
        if _active_model_name == _PREFERRED_MODEL and _looks_like_model_not_found(e):
            logger.warning(
                "Preferred model %s rejected (%s); falling back to %s",
                _PREFERRED_MODEL,
                e,
                _FALLBACK_MODEL,
            )
            _active_model_name = _FALLBACK_MODEL
            raw = _generate_raw(
                _active_model_name, system_prompt, user_input, temperature
            )
        else:
            logger.error("Gemini call failed after retries: %s", e)
            raise

    parsed = _parse_json_response(raw)
    logger.info(
        "Gemini call succeeded; parsed JSON of type=%s",
        type(parsed).__name__,
    )
    return parsed


if __name__ == "__main__":
    result = call_gemini(
        system_prompt=(
            "You are a JSON-returning assistant. Respond ONLY with valid JSON."
        ),
        user_input="Return a JSON object with key 'hello' and value 'world'.",
    )
    print(result)
