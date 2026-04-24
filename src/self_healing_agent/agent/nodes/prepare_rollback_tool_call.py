from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.tools.registry import AVAILABLE_TOOL_FAMILIES
from self_healing_agent.tools.resolver import resolve_precondition



def prepare_rollback_tool_call(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    rollback_plan = state.get("rollback_plan", {}) or {}
    rollback_actions = rollback_plan.get("actions", []) or []
    decision = state.get("decision", {}) or {}

    if not rollback_actions:
        trace.append("prepare_rollback_tool_call:no_actions")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Rollback requested but no rollback actions are present.",
        }

    rollback_action = rollback_actions[0]
    tool_name = str(rollback_action.get("tool_name", "")).strip()
    args = rollback_action.get("args", {}) or {}
    idempotency_key = rollback_action.get("idempotency_key")

    if not tool_name:
        trace.append("prepare_rollback_tool_call:missing_tool_name")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Rollback action is missing tool_name.",
        }

    rollback_tool_definition: dict[str, Any] | None = None
    for family_meta in AVAILABLE_TOOL_FAMILIES.values():
        rollback_meta = family_meta.get("rollback")
        if rollback_meta and rollback_meta.get("tool_name") == tool_name:
            rollback_tool_definition = rollback_meta
            break

    if not rollback_tool_definition:
        trace.append("prepare_rollback_tool_call:tool_definition_missing")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Rollback tool definition not found for tool_name={tool_name}.",
        }

    precondition_name = rollback_tool_definition.get("precondition")
    try:
        precondition_fn = resolve_precondition(precondition_name)
    except ValueError as exc:
        trace.append("prepare_rollback_tool_call:precondition_resolution_failed")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": str(exc),
        }

    if precondition_fn is not None:
        tool_precondition_result = precondition_fn(state)
    else:
        tool_precondition_result = {
            "ok": True,
            "reason": "NO_PRECONDITION_CONFIGURED",
            "facts": {},
        }

    if not tool_precondition_result.get("ok", False):
        trace.append("prepare_rollback_tool_call:precondition_failed")
        return {
            "tool_definition": rollback_tool_definition,
            "tool_precondition_result": tool_precondition_result,
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Rollback tool precondition failed: {tool_precondition_result.get('reason', 'UNKNOWN')}",
        }

    if not idempotency_key:
        decision_id = state.get("decision_id") or decision.get("decision_id") or "unknown_decision"
        idempotency_key = f"{decision_id}:rollback:{tool_name}"

    tool_step = int(state.get("tool_step", 0)) + 1
    attempt = 1

    tool_call = {
        "tool_name": tool_name,
        "args": args,
        "idempotency_key": idempotency_key,
    }

    trace.append(f"prepare_rollback_tool_call:{tool_name}:ok")

    return {
        "execution_phase": "ROLLBACK",
        "tool_step": tool_step,
        "attempt": attempt,
        "tool_definition": rollback_tool_definition,
        "tool_precondition_result": tool_precondition_result,
        "tool_call": tool_call,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }
