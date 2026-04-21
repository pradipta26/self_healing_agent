from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.observability.metrics import emit_counter
from self_healing_agent.observability.metrics_contract import ROLLBACK_INVOCATION_RATE


def rollback_or_investigation(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    rollback_plan = state.get("rollback_plan", {}) or {}
    rollback_status = str(rollback_plan.get("status", "SKIPPED")).strip().upper()
    rollback_actions = rollback_plan.get("actions", []) or []

    if rollback_status == "PLANNED" and rollback_actions:
        tool_call = state.get("tool_call", {}) or {}
        tool_name = str(tool_call.get("tool_name", "UNKNOWN")).strip()
        execution_phase = str(state.get("execution_phase", "ROLLBACK")).strip().upper()

        emit_counter(
            ROLLBACK_INVOCATION_RATE,
            tool_name=tool_name,
            execution_phase=execution_phase,
        )

        trace.append("rollback_or_investigation:execute_rollback")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    trace.append("rollback_or_investigation:build_investigation_request")
    return {
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }