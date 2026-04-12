from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from self_healing_agent.agent.state import AgentState


def hitl_approval(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    approval_request = state.get("approval_request", {})
    if not approval_request:
        trace.append("hitl_approval:missing_approval_request")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Approval request is missing from state.",
        }

    # Pause here. On resume, interrupt(...) returns the payload passed by
    # Command(resume=...) from the API layer.
    resume_payload = interrupt(
        {
            "request_id": approval_request.get("request_id"),
        }
    )

    if not isinstance(resume_payload, dict):
        trace.append("hitl_approval:invalid_resume_payload")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Resume payload from HITL approval must be a JSON object.",
        }

    status = str(resume_payload.get("status", "")).strip().upper()
    if status not in {"APPROVED", "REJECTED", "PENDING"}:
        trace.append("hitl_approval:invalid_status")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Resume payload from HITL approval must include a valid status.",
        }

    response = {
        "request_id": resume_payload.get(
            "request_id", approval_request.get("request_id")
        ),
        "status": status,
        "responder": resume_payload.get("responder", ""),
        "reason": resume_payload.get("reason", ""),
        "timestamp_utc": resume_payload.get(
            "timestamp_utc", state.get("timestamp_utc", "")
        ),
    }

    trace.append(f"hitl_approval:{status.lower()}")

    return {
        "approval_response": response,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }