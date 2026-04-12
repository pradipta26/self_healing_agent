from __future__ import annotations

from typing import Any

from self_healing_agent.agent.tools.mock_tools import mock_tool_execute
from self_healing_agent.agent.state import AgentState


def execute_action(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    action_policy = state.get("action_policy_decision", {})
    approval_response = state.get("approval_response", {})
    structured_input = state.get("structured_input", {})
    model_output = state.get("model_output", {})

    status = str(approval_response.get("status", "")).strip().upper()
    if status != "APPROVED":
        trace.append("execute_action:not_approved")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Execution attempted without APPROVED approval response.",
        }

    action_families = action_policy.get("action_families", [])
    if not action_families:
        trace.append("execute_action:no_action_family")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "No action families available for execution.",
        }

    primary_family = action_families[0]

    tool_call = {
        "tool_name": primary_family,
        "args": {
            "service": structured_input.get("service_domain"),
            "env": structured_input.get("env"),
            "hosts": structured_input.get("hosts", []),
            "instances": structured_input.get("instances", []),
            "proposed_actions": model_output.get("remediation", []),
        },
        "idempotency_key": (
            f"{state.get('decision', {}).get('decision_id', 'unknown')}:"
            f"{primary_family}:"
            f"{structured_input.get('service_domain', 'unknown')}:"
            f"{structured_input.get('env', 'unknown')}"
        ),
    }

    # Call dummy tool execution layer
    tool_result = mock_tool_execute(tool_call)

    trace.append("execute_action:ok")

    return {
        "tool_call": tool_call,
        "tool_result": tool_result,
        "error_flag": False,
        "error_message": None,
        "warnings": warnings,
        "trace": trace,
    }