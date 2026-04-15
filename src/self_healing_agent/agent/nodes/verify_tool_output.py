from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def verify_tool_output(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_result = state.get("tool_result", {})
    tool_trigger_codes = list(state.get("tool_trigger_codes", []))

    if not tool_result.get("ok", False):
        tool_trigger_codes.append("TOOL_EXECUTION_FAILED")
        trace.append("verify_tool_output:tool_not_ok")
        return {
            "verification_result": {
                "ok": False,
                "details": {
                    "reason": "tool_not_ok",
                    "error": tool_result.get("error", ""),
                },
            },
            "tool_trigger_codes": tool_trigger_codes,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    raw = tool_result.get("raw")
    if not isinstance(raw, dict):
        tool_trigger_codes.append("TOOL_OUTPUT_MALFORMED")
        trace.append("verify_tool_output:raw_missing_or_invalid")
        return {
            "verification_result": {
                "ok": False,
                "details": {
                    "reason": "raw_missing_or_invalid",
                },
            },
            "tool_trigger_codes": tool_trigger_codes,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    message = raw.get("message")
    if not isinstance(message, str) or not message.strip():
        tool_trigger_codes.append("TOOL_OUTPUT_MALFORMED")
        trace.append("verify_tool_output:message_missing")
        return {
            "verification_result": {
                "ok": False,
                "details": {
                    "reason": "message_missing",
                },
            },
            "tool_trigger_codes": tool_trigger_codes,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    trace.append("verify_tool_output:ok")
    return {
        "tool_verification_result": {
            "ok": True,
            "details": {
                "verification_mode": "MOCK",
                "message": message,
            },
        },
        "tool_trigger_codes": [],
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }