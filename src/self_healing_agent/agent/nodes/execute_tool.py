from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.tools.resolver import resolve_executor


def execute_tool(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_call = state.get("tool_call", {}) or {}
    if not tool_call:
        trace.append("execute_tool:missing_tool_call")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call is missing from state.",
        }

    tool_definition = state.get("tool_definition", {}) or {}
    executor_name = str(tool_definition.get("executor", "")).strip()
    if not executor_name:
        trace.append("execute_tool:missing_executor")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_definition.executor is missing from state.",
        }

    try:
        executor = resolve_executor(executor_name)
        tool_result = executor(tool_call)
        trace.append(f"execute_tool:{executor_name}:ok")

        return {
            "tool_result": tool_result,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        trace.append(f"execute_tool:{executor_name}:error")
        warnings.append("TOOL_EXECUTION_EXCEPTION")

        return {
            "tool_result": {
                "ok": False,
                "raw": {},
                "error": str(exc),
                "error_code": "TOOL_EXECUTION_EXCEPTION",
                "transient": False,
                "side_effect_committed": False,
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }