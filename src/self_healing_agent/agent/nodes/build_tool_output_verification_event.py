from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def build_tool_output_verification_event(state: AgentState) -> dict[str, Any]:
    """
    Build one of the following based on execution_phase:

    FORWARD:
    - TOOL_OUTPUT_VERIFICATION_SUCCEEDED
    - TOOL_OUTPUT_VERIFICATION_FAILED

    ROLLBACK:
    - ROLLBACK_OUTPUT_VERIFICATION_SUCCEEDED
    - ROLLBACK_OUTPUT_VERIFICATION_FAILED
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    tool_call = state.get("tool_call", {})
    tool_verification = state.get("tool_verification_result", {})
    tool_trigger_codes = list(state.get("tool_trigger_codes", []))
    execution_phase = str(state.get("execution_phase", "FORWARD")).strip().upper()

    decision_id = decision.get("decision_id")
    if not decision_id:
        trace.append("build_tool_output_verification_event:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for tool output verification lifecycle event.",
        }

    if not tool_call:
        trace.append("build_tool_output_verification_event:missing_tool_call")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call is missing for tool output verification lifecycle event.",
        }

    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).upper()
    meta = tool_call.get("args", {}).get("_meta", {})
    attempt = meta.get("attempt")
    tool_step = meta.get("tool_step")

    verification_ok = bool(tool_verification.get("ok", False))
    reason_code = None
    if tool_trigger_codes:
        reason_code = tool_trigger_codes[0]

    if execution_phase == "ROLLBACK":
        if verification_ok:
            event_type = "ROLLBACK_OUTPUT_VERIFICATION_SUCCEEDED"
            event_status = "SUCCEEDED"
        else:
            event_type = "ROLLBACK_OUTPUT_VERIFICATION_FAILED"
            event_status = "FAILED"
    else:
        if verification_ok:
            event_type = "TOOL_OUTPUT_VERIFICATION_SUCCEEDED"
            event_status = "SUCCEEDED"
        else:
            event_type = "TOOL_OUTPUT_VERIFICATION_FAILED"
            event_status = "FAILED"

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision_id,
        "event_type": event_type,
        "event_status": event_status,
        "stage_name": "TOOL_OUTPUT_VERIFICATION",
        "actor_type": "SYSTEM",
        "actor_id": "self_healing_agent",
        "request_id": state.get("approval_request", {}).get("request_id"),
        "related_entity_id": tool_call.get("idempotency_key"),
        "payload": {
            "execution_phase": execution_phase,
            "tool_name": tool_name,
            "attempt": attempt,
            "tool_step": tool_step,
            "reason_code": reason_code,
        },
        "notes": [],
        "timestamp_utc": state.get("timestamp_utc"),
    }

    trace.append(f"build_tool_output_verification_event:{event_status.lower()}")

    return {
        "lifecycle_event": event,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }