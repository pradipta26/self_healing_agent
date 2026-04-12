from typing import Any
 
from self_healing_agent.agent.state import AgentState


def build_approval_response_event(state: AgentState) -> dict[str, Any]:
    decision = state.get("decision", {})
    approval_request = state.get("approval_request", {})
    approval_response = state.get("approval_response", {})
    approval_status = str(approval_response.get("status", "PENDING")).strip().upper()

    event_type = {
        "APPROVED": "APPROVAL_APPROVED",
        "REJECTED": "APPROVAL_REJECTED",
        "PENDING": "APPROVAL_PENDING",
    }.get(approval_status, "APPROVAL_PENDING")

    actor_type = "HUMAN" if approval_status in {"APPROVED", "REJECTED"} else "SYSTEM"
    actor_id = approval_response.get("responder", "unknown") if actor_type == "HUMAN" else "self_healing_agent"

    event = {
        "decision_log_id": state.get("decision_log_id"),
        "decision_id": decision.get("decision_id"),
        "event_type": event_type,
        "event_status": approval_status,
        "stage_name": "HITL_APPROVAL_RESPONSE",
        "actor_type": actor_type,
        "actor_id": actor_id,
        "request_id": approval_request.get("request_id"),
        "related_entity_id": approval_request.get("request_id"),
        "payload": {
            "required_human_role": approval_request.get("required_human_role"),
            "service": approval_request.get("service"),
            "env": approval_request.get("env"),
            "reason": approval_response.get("reason", ""),
        },
        "notes": [],
        "timestamp_utc": approval_response.get("timestamp_utc", state.get("timestamp_utc")),
    }

    trace = list(state.get("trace", []))
    trace.append("build_approval_response_event:ok")

    return {
        "lifecycle_event": event,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
        "warnings": list(state.get("warnings", [])),
    }