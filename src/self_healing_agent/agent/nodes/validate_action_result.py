from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def validate_action_result(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_verification = state.get("tool_verification_result", {})
    tool_result = state.get("tool_result", {})

    # Defensive guard:
    # action-level validation should only happen after tool-output verification passed.
    if not tool_verification.get("ok", False):
        trace.append("validate_action_result:tool_verification_not_ok")
        return {
            "action_verification_result": {
                "ok": False,
                "details": {
                    "validation_mode": "MOCK",
                    "reason": "tool_verification_not_ok",
                    "message": "Action validation skipped because tool verification did not pass.",
                },
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    # V1 placeholder:
    # Later this should check real post-action operational outcome, such as:
    # - JVM healthy after restart
    # - traffic shifted after failover
    # - disk usage reduced after cleanup
    ok = bool(tool_result.get("ok"))

    action_verification_result = {
        "ok": ok,
        "details": {
            "validation_mode": "MOCK",
            "message": "Post-action outcome validation placeholder executed.",
        },
    }

    trace.append("validate_action_result:ok")

    return {
        "action_verification_result": action_verification_result,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }