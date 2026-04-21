from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def build_rollback_execution_event(state: AgentState) -> dict[str, Any]:
    """
    Build one of:
    - ROLLBACK_EXECUTION_STARTED
    - ROLLBACK_EXECUTION_SUCCEEDED
    - ROLLBACK_EXECUTION_FAILED

    Keep lifecycle payload slim.
    Detailed tool payloads belong in future tool_execution_log, not lifecycle_event.
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {}) or {}
    rollback_plan = state.get("rollback_plan", {}) or {}
    tool_call = state.get("tool_call", {}) or {}
    tool_result = state.get("tool_result", {}) or {}
    tool_retry_decision = str(state.get("tool_retry_decision", "NO_RETRY")).strip().upper()

    decision_id = decision.get("decision_id")
    if not decision_id:
        trace.append("build_rollback_execution_event:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for rollback execution lifecycle event.",
        }

    rollback_actions = rollback_plan.get("actions", []) or []
    rollback_status = str(rollback_plan.get("status", "SKIPPED")).strip().upper()

    # Determine event type/status
    if rollback_status == "PLANNED" and rollback_actions and not tool_call:
        event_type = "ROLLBACK_EXECUTION_STARTED"
        event_status = "STARTED"
        rollback_tool_name = rollback_actions[0].get("tool_name")
        idempotency_key = rollback_actions[0].get("idempotency_key")
    elif tool_retry_decision == "RETRY_TOOL":
        event_type = "ROLLBACK_EXECUTION_FAILED"
        event_status = "FAILED"
        rollback_tool_name = tool_call.get("tool_name")
        idempotency_key = tool_call.get("idempotency_key")
    elif tool_result.get("ok", False):
        event_type = "ROLLBACK_EXECUTION_SUCCEEDED"
        event_status = "SUCCEEDED"
        rollback_tool_name = tool_call.get("tool_name")
        idempotency_key = tool_call.get("idempotency_key")
    else:
        event_type = "ROLLBACK_EXECUTION_FAILED"
        event_status = "FAILED"
        rollback_tool_name = tool_call.get("tool_name") or (
            rollback_actions[0].get("tool_name") if rollback_actions else None
        )
        idempotency_key = tool_call.get("idempotency_key") or (
            rollback_actions[0].get("idempotency_key") if rollback_actions else None
        )

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision_id,
        "event_type": event_type,
        "event_status": event_status,
        "stage_name": "ROLLBACK_EXECUTION",
        "actor_type": "SYSTEM",
        "actor_id": "self_healing_agent",
        "request_id": state.get("approval_request", {}).get("request_id"),
        "related_entity_id": idempotency_key,
        "payload": {
            "tool_name": rollback_tool_name,
            "attempt": state.get("attempt"),
            "tool_step": state.get("tool_step"),
            "reason_code": tool_result.get("error") or rollback_plan.get("reason"),
        },
        "notes": [],
        "timestamp_utc": state.get("timestamp_utc"),
    }

    trace.append(f"build_rollback_execution_event:{event_status.lower()}")

    return {
        "lifecycle_event": event,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }