from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def validate_action_result(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_result = state.get("tool_result", {})
    ok = bool(tool_result.get("ok"))

    verification_result = {
        "ok": ok,
        "details": {
            "verification_mode": "MOCK",
            "message": "Post-action verification placeholder executed.",
        },
    }

    trace.append("verify_action_result:ok")

    return {
        "verification_result": verification_result,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }