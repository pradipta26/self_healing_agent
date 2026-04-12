from typing import Any

from self_healing_agent.agent.state import AgentState

def build_approval_requested_event(state: AgentState) -> dict[str, Any]:
    decision = state.get("decision", {})
    approval_request = state.get("approval_request", {})

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision.get("decision_id"),
        "event_type": "APPROVAL_REQUEST_CREATED",
        "event_status": "PENDING",
        "stage_name": "HITL_APPROVAL",
        "actor_type": "SYSTEM",
        "actor_id": "self_healing_agent",
        "request_id": approval_request.get("request_id"),
        "related_entity_id": approval_request.get("request_id"),
        "payload": {
            "required_human_role": approval_request.get("required_human_role"),
            "service": approval_request.get("service"),
            "env": approval_request.get("env"),
        },
        "notes": [],
        "timestamp_utc": state.get("timestamp_utc"),
    }

    trace = list(state.get("trace", []))
    trace.append("build_approval_requested_event:ok")

    return {
        "lifecycle_event": event,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
        "warnings": list(state.get("warnings", [])),
    }