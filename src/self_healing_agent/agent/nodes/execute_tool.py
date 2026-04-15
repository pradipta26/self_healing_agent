from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.tools.mock_tools import mock_tool_execute


def execute_tool(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_call = state.get("tool_call", {})
    if not tool_call:
        trace.append("execute_tool:missing_tool_call")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call is missing from state.",
        }

    try:
        tool_result = mock_tool_execute(tool_call)
        trace.append("execute_tool:ok")

        return {
            "tool_result": tool_result,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        trace.append("execute_tool:error")
        warnings.append("TOOL_EXECUTION_EXCEPTION")

        return {
            "tool_result": {
                "ok": False,
                "raw": {},
                "error": str(exc),
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }