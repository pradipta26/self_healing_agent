from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def build_action_validation_event(state: AgentState) -> dict[str, Any]:
    """
    Build one of:
    - ACTION_VALIDATION_SUCCEEDED
    - ACTION_VALIDATION_FAILED
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    tool_call = state.get("tool_call", {})
    action_verification = state.get("action_verification_result", {})

    decision_id = decision.get("decision_id")
    if not decision_id:
        trace.append("build_action_validation_event:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for action validation lifecycle event.",
        }

    if not tool_call:
        trace.append("build_action_validation_event:missing_tool_call")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call is missing for action validation lifecycle event.",
        }

    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).upper()
    meta = tool_call.get("args", {}).get("_meta", {})
    attempt = meta.get("attempt")
    tool_step = meta.get("tool_step")

    validation_ok = bool(action_verification.get("ok", False))
    details = action_verification.get("details", {}) or {}
    reason_code = details.get("reason") or None

    if validation_ok:
        event_type = "ACTION_VALIDATION_SUCCEEDED"
        event_status = "SUCCEEDED"
    else:
        event_type = "ACTION_VALIDATION_FAILED"
        event_status = "FAILED"

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision_id,
        "event_type": event_type,
        "event_status": event_status,
        "stage_name": "ACTION_VALIDATION",
        "actor_type": "SYSTEM",
        "actor_id": "self_healing_agent",
        "request_id": state.get("approval_request", {}).get("request_id"),
        "related_entity_id": tool_call.get("idempotency_key"),
        "payload": {
            "tool_name": tool_name,
            "attempt": attempt,
            "tool_step": tool_step,
            "reason_code": reason_code,
        },
        "notes": [],
        "timestamp_utc": state.get("timestamp_utc"),
    }

    trace.append(f"build_action_validation_event:{event_status.lower()}")

    return {
        "lifecycle_event": event,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }