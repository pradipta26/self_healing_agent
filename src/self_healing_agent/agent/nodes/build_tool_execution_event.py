from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def build_tool_execution_event(state: AgentState) -> dict[str, Any]:
    """
    Build one of the following based on execution_phase:

    FORWARD:
    - TOOL_EXECUTION_STARTED
    - TOOL_EXECUTION_RETRY_SCHEDULED
    - TOOL_EXECUTION_SUCCEEDED
    - TOOL_EXECUTION_FAILED

    ROLLBACK:
    - ROLLBACK_EXECUTION_STARTED
    - ROLLBACK_EXECUTION_RETRY_SCHEDULED
    - ROLLBACK_EXECUTION_SUCCEEDED
    - ROLLBACK_EXECUTION_FAILED

    Keep lifecycle payload slim.
    Detailed tool payloads should go to future tool_execution_log, not lifecycle_event.
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    tool_call = state.get("tool_call", {})
    tool_result = state.get("tool_result", {})
    retry_decision = str(state.get("tool_retry_decision", "NO_RETRY")).strip().upper()
    execution_phase = str(state.get("execution_phase", "FORWARD")).strip().upper()

    decision_id = decision.get("decision_id")
    if not decision_id:
        trace.append("build_tool_execution_event:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for tool execution lifecycle event.",
        }

    if not tool_call:
        trace.append("build_tool_execution_event:missing_tool_call")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call is missing for tool execution lifecycle event.",
        }

    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).upper()
    meta = tool_call.get("args", {}).get("_meta", {})
    attempt = meta.get("attempt")
    tool_step = meta.get("tool_step")

    tool_ok = bool(tool_result.get("ok", False))
    tool_error = str(tool_result.get("error", "")).strip()

    if execution_phase == "ROLLBACK":
        if retry_decision == "RETRY_TOOL":
            event_type = "ROLLBACK_EXECUTION_RETRY_SCHEDULED"
            event_status = "RETRY_SCHEDULED"
        elif tool_ok:
            event_type = "ROLLBACK_EXECUTION_SUCCEEDED"
            event_status = "SUCCEEDED"
        elif tool_call and not tool_result:
            event_type = "ROLLBACK_EXECUTION_STARTED"
            event_status = "STARTED"
        else:
            event_type = "ROLLBACK_EXECUTION_FAILED"
            event_status = "FAILED"
    else:
        if retry_decision == "RETRY_TOOL":
            event_type = "TOOL_EXECUTION_RETRY_SCHEDULED"
            event_status = "RETRY_SCHEDULED"
        elif tool_ok:
            event_type = "TOOL_EXECUTION_SUCCEEDED"
            event_status = "SUCCEEDED"
        elif tool_call and not tool_result:
            event_type = "TOOL_EXECUTION_STARTED"
            event_status = "STARTED"
        else:
            event_type = "TOOL_EXECUTION_FAILED"
            event_status = "FAILED"

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision_id,
        "event_type": event_type,
        "event_status": event_status,
        "stage_name": "TOOL_EXECUTION",
        "actor_type": "SYSTEM",
        "actor_id": "self_healing_agent",
        "request_id": state.get("approval_request", {}).get("request_id"),
        "related_entity_id": tool_call.get("idempotency_key"),
        "payload": {
            "execution_phase": execution_phase,
            "tool_name": tool_name,
            "attempt": attempt,
            "tool_step": tool_step,
            "reason_code": tool_error or None,
        },
        "notes": [],
        "timestamp_utc": state.get("timestamp_utc"),
    }

    trace.append(f"build_tool_execution_event:{event_status.lower()}")

    return {
        "lifecycle_event": event,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }
