from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.observability.metrics import emit_counter
from self_healing_agent.observability.metrics_contract import (
    ROLLBACK_SUCCESS_RATE,
    ROLLBACK_FAILURE_RATE,
)


def verify_rollback(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_verification = state.get("tool_verification_result", {}) or {}
    rollback_plan = dict(state.get("rollback_plan", {}) or {})

    tool_call = state.get("tool_call", {}) or {}
    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).strip()
    execution_phase = str(state.get("execution_phase", "ROLLBACK")).strip().upper()

    if tool_verification.get("ok"):
        rollback_plan["status"] = "EXECUTED"
        rollback_plan["notes"] = list(rollback_plan.get("notes", [])) + [
            "Rollback completed through shared tool pipeline."
        ]
        emit_counter(
            ROLLBACK_SUCCESS_RATE,
            tool_name=tool_name,
            execution_phase=execution_phase,
        )
        trace.append("verify_rollback:ok")
        return {
            "rollback_plan": rollback_plan,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    rollback_plan["status"] = "FAILED"
    rollback_plan["reason"] = rollback_plan.get(
        "reason",
        "Rollback tool verification failed.",
    )
    emit_counter(
        ROLLBACK_FAILURE_RATE,
        tool_name=tool_name,
        execution_phase=execution_phase,
    )
    trace.append("verify_rollback:failed")
    return {
        "rollback_plan": rollback_plan,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }