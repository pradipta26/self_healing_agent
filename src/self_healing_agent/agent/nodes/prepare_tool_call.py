from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def prepare_tool_call(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    structured_input = state.get("structured_input", {})
    action_policy = state.get("action_policy_decision", {})
    decision = state.get("decision", {})
    approval_response = state.get("approval_response", {})

    if str(approval_response.get("status", "")).strip().upper() != "APPROVED":
        trace.append("prepare_tool_call:not_approved")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Tool preparation attempted without APPROVED approval response.",
        }

    action_families = action_policy.get("action_families", [])
    if not action_families:
        trace.append("prepare_tool_call:missing_action_family")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "No action families available for tool preparation.",
        }

    decision_id = state.get("decision_id") or decision.get("decision_id")
    if not decision_id:
        trace.append("prepare_tool_call:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for tool preparation.",
        }

    trace_id = state.get("trace_id", "")
    incident_id = state.get("incident_id", "")
    tool_step = int(state.get("tool_step", 0)) + 1
    attempt = int(state.get("attempt", 0)) or 1

    primary_family = str(action_families[0]).upper()

    meta = {
        "trace_id": trace_id,
        "incident_id": incident_id,
        "decision_id": decision_id,
        "tool_step": tool_step,
        "attempt": attempt,
    }

    tool_args = {
        "service": structured_input.get("service_domain"),
        "env": structured_input.get("env"),
        "datacenter": structured_input.get("datacenter"),
        "app_name": structured_input.get("app_name"),
        "hosts": structured_input.get("hosts", []) or [],
        "instances": structured_input.get("instances", []) or [],
        "metric_names": structured_input.get("metric_names", []) or [],
        "reason": structured_input.get("reason", ""),
        "_meta": meta,
    }

    idempotency_key = (
        f"{decision_id}:"
        f"{incident_id or 'unknown_incident'}:"
        f"{primary_family}:"
        f"{structured_input.get('service_domain', 'unknown_service')}:"
        f"{structured_input.get('env', 'unknown_env')}"
    )

    tool_call = {
        "tool_name": primary_family,
        "args": tool_args,
        "idempotency_key": idempotency_key,
    }

    trace.append(f"prepare_tool_call:{primary_family}:ok")

    return {
        "tool_step": tool_step,
        "attempt": attempt,
        "tool_call": tool_call,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }