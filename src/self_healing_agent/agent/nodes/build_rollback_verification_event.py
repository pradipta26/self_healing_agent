from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def build_rollback_verification_event(state: AgentState) -> dict[str, Any]:
    """
    Build one of:
    - ROLLBACK_VERIFICATION_SUCCEEDED
    - ROLLBACK_VERIFICATION_FAILED
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {}) or {}
    rollback_plan = state.get("rollback_plan", {}) or {}
    tool_call = state.get("tool_call", {}) or {}

    decision_id = decision.get("decision_id")
    if not decision_id:
        trace.append("build_rollback_verification_event:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for rollback verification lifecycle event.",
        }

    rollback_status = str(rollback_plan.get("status", "FAILED")).strip().upper()
    verification_ok = rollback_status == "EXECUTED"

    if verification_ok:
        event_type = "ROLLBACK_VERIFICATION_SUCCEEDED"
        event_status = "SUCCEEDED"
    else:
        event_type = "ROLLBACK_VERIFICATION_FAILED"
        event_status = "FAILED"

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision_id,
        "event_type": event_type,
        "event_status": event_status,
        "stage_name": "ROLLBACK_VERIFICATION",
        "actor_type": "SYSTEM",
        "actor_id": "self_healing_agent",
        "request_id": state.get("approval_request", {}).get("request_id"),
        "related_entity_id": tool_call.get("idempotency_key"),
        "payload": {
            "tool_name": tool_call.get("tool_name"),
            "attempt": state.get("attempt"),
            "tool_step": state.get("tool_step"),
            "reason_code": rollback_plan.get("reason"),
        },
        "notes": list(rollback_plan.get("notes", [])),
        "timestamp_utc": state.get("timestamp_utc"),
    }

    trace.append(f"build_rollback_verification_event:{event_status.lower()}")

    return {
        "lifecycle_event": event,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }