"""
Execution agent for the PolicyPulse pipeline.

This agent splits responsibility between Gemini and Python:
  1. Gemini PLANS the mutation — given the chosen Rank 1 action and the current
     database state, it returns a structured plan (action_taken + a list of
     mutations expressed as dot-path / operation / value).
  2. Python PERFORMS the mutation deterministically — each planned mutation is
     applied to a deep-copied snapshot of the state, and a leaf-level diff is
     computed by comparing the before and after snapshots.

The agent only produces the after_state and diff structure; the actual disk
write to mock_db.json / action_log.json is performed by the /analyze endpoint
in main.py, not here.
"""

from __future__ import annotations

import copy
import json
import logging
import uuid
from typing import Any, List

from pydantic import ValidationError

from agents.base_agent import (
    AgentResponse,
    BaseAgent,
    ExecutionDiffEntry,
    ExecutionOutput,
)


logger = logging.getLogger(__name__)


EXECUTION_SYSTEM_PROMPT = """You are the PolicyPulse Execution Agent. You are given the chosen Rank 1 action and the current business database state (mock_db.json). Your job is to produce a precise MUTATION PLAN that another system will apply to the database in Python — you do NOT write any files yourself.

Return a JSON object with this exact shape:
{
  "action_taken": "concise description of what is being done",
  "mutations": [
    {"path": "pricing_rules.delivery_surcharges", "operation": "append", "value": {"threshold_pkr": 800, "fee_pkr": 50}}
  ],
  "confidence": 1.0,
  "reasoning": "2-3 sentences explaining the mutation"
}

Rules for each mutation:
- "path" uses dot notation into the database object (e.g. "pricing_rules.delivery_surcharges", "campaigns", "pricing_rules.base_delivery_fee").
- "operation" is EXACTLY one of:
  - "append": append "value" to the list found at "path".
  - "set": overwrite the value at "path" with "value".
  - "increment": add the numeric "value" to the existing number at "path".
- Prefer paths that already exist in the provided state. To add a delivery surcharge, append to "pricing_rules.delivery_surcharges". To add a campaign, append to "campaigns".
- Make each "value" payload consistent in shape with the existing entries at that path.

Give an honest confidence (1.0 if the mapping is unambiguous, lower if the action is hard to translate into a concrete field change). Return ONLY a valid JSON object. Do not include markdown formatting or backticks."""


def _apply_mutation(state: dict, path: str, operation: str, value: Any) -> dict:
    """
    Apply a single mutation to a deep copy of `state` and return the result.

    `path` is dot-notation into nested dicts. `operation` is one of "append"
    (push `value` onto the list at path), "set" (overwrite), or "increment"
    (numeric add). Intermediate dict keys are created if missing.
    """
    mutated = copy.deepcopy(state)
    keys = path.split(".")
    target: Any = mutated
    for key in keys[:-1]:
        if not isinstance(target, dict):
            raise TypeError(f"Cannot navigate into non-dict at '{key}' for path '{path}'")
        if key not in target or not isinstance(target[key], dict):
            target[key] = {}
        target = target[key]

    last = keys[-1]
    if not isinstance(target, dict):
        raise TypeError(f"Cannot apply '{operation}' on non-dict parent for path '{path}'")

    if operation == "append":
        existing = target.get(last)
        if not isinstance(existing, list):
            existing = [] if existing is None else [existing]
        existing.append(value)
        target[last] = existing
    elif operation == "set":
        target[last] = value
    elif operation == "increment":
        current = target.get(last, 0)
        if not isinstance(current, (int, float)):
            raise TypeError(f"Cannot increment non-numeric value at path '{path}'")
        if not isinstance(value, (int, float)):
            raise TypeError(f"Increment value for path '{path}' must be numeric")
        target[last] = current + value
    else:
        raise ValueError(f"Unknown operation '{operation}' for path '{path}'")

    return mutated


def _compute_diff(
    before: Any,
    after: Any,
    path_prefix: str = "",
) -> List[ExecutionDiffEntry]:
    """
    Recursively compare `before` and `after`, returning one ExecutionDiffEntry
    per changed, added, or removed leaf path. Dicts recurse by key and lists by
    index; scalars (and mismatched types) are emitted as a single leaf change.
    """
    entries: List[ExecutionDiffEntry] = []

    if isinstance(before, dict) and isinstance(after, dict):
        for key in dict.fromkeys([*before.keys(), *after.keys()]):
            child = f"{path_prefix}.{key}" if path_prefix else str(key)
            if key not in before:
                entries.append(
                    ExecutionDiffEntry(path=child, old=None, new=after[key])
                )
            elif key not in after:
                entries.append(
                    ExecutionDiffEntry(path=child, old=before[key], new=None)
                )
            else:
                entries.extend(_compute_diff(before[key], after[key], child))
    elif isinstance(before, list) and isinstance(after, list):
        for idx in range(max(len(before), len(after))):
            child = f"{path_prefix}.{idx}" if path_prefix else str(idx)
            if idx >= len(before):
                entries.append(
                    ExecutionDiffEntry(path=child, old=None, new=after[idx])
                )
            elif idx >= len(after):
                entries.append(
                    ExecutionDiffEntry(path=child, old=before[idx], new=None)
                )
            else:
                entries.extend(_compute_diff(before[idx], after[idx], child))
    else:
        if before != after:
            entries.append(
                ExecutionDiffEntry(path=path_prefix, old=before, new=after)
            )

    return entries


class ExecutionAgent(BaseAgent):
    """Plans a DB mutation via Gemini, then applies it deterministically in Python."""

    def __init__(self) -> None:
        super().__init__(
            system_prompt=EXECUTION_SYSTEM_PROMPT,
            agent_name="execution",
        )

    def run(
        self,
        input_data: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        context = context or {}
        actions = context.get("actions", {})
        mock_db_state = context.get("mock_db_state", {})

        action_list = (
            actions.get("actions", []) if isinstance(actions, dict) else []
        )
        rank1 = (
            min(action_list, key=lambda a: a.get("rank", 999))
            if action_list
            else {}
        )

        user_input = (
            "RANK 1 ACTION (the chosen action to apply):\n"
            f"{json.dumps(rank1, indent=2, default=str)}\n\n"
            "CURRENT BUSINESS STATE (mock_db.json):\n"
            f"{json.dumps(mock_db_state, indent=2, default=str)}"
        )

        try:
            raw = self._call_gemini(user_input)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Execution Gemini call failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Failed to obtain a valid plan from Gemini: {exc}",
            )

        if not isinstance(raw, dict):
            logger.warning(
                "Execution expected a JSON object, got %s", type(raw).__name__
            )
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini returned a non-object JSON payload; cannot build a "
                    "mutation plan."
                ),
            )

        action_taken = raw.get("action_taken", "")
        mutations = raw.get("mutations", [])
        confidence = float(raw.get("confidence", 0.9))
        model_reason = raw.get("reasoning", "")

        if not isinstance(mutations, list) or not mutations:
            logger.warning("Execution plan contained no mutations")
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Gemini plan did not contain any mutations to apply; nothing "
                    "to execute."
                ),
            )

        before_state = copy.deepcopy(mock_db_state)
        after_state = copy.deepcopy(mock_db_state)
        try:
            for mutation in mutations:
                after_state = _apply_mutation(
                    after_state,
                    mutation["path"],
                    mutation["operation"],
                    mutation.get("value"),
                )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Failed to apply mutation: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=f"Mutation plan could not be applied to state: {exc}",
            )

        diff = _compute_diff(before_state, after_state)

        try:
            output = ExecutionOutput(
                action_taken=action_taken,
                before_state=before_state,
                after_state=after_state,
                diff=diff,
                log_entry_id=str(uuid.uuid4()),
            )
        except ValidationError as exc:
            logger.warning("ExecutionOutput validation failed: %s", exc)
            return self._make_response(
                output=None,
                confidence=0.3,
                reasoning=(
                    "Computed execution result did not match the ExecutionOutput "
                    f"schema: {exc.error_count()} error(s)."
                ),
            )

        reasoning = (
            f"Applied {len(mutations)} mutation(s) producing {len(diff)} diff "
            f"entr{'y' if len(diff) == 1 else 'ies'}. {model_reason}"
        ).strip()

        return self._make_response(
            output=output,
            confidence=confidence,
            reasoning=reasoning,
        )
