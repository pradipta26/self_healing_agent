from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.tools.retry_classifier import classify_tool_failure

MAX_TOOL_RETRY = 2

def tool_retry_gate(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_result = state.get("tool_result", {})
    attempt = int(state.get("attempt", 1))
    tool_trigger_codes = list(state.get("tool_trigger_codes", []))

    if tool_result.get("ok", False):
        trace.append("tool_retry_gate:no_retry_needed")
        return {
            "tool_failure_classification": {},
            "tool_retry_decision": "NO_RETRY",
            "tool_trigger_codes": tool_trigger_codes,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    classification = classify_tool_failure(tool_result)
    reason_code = classification.get("reason_code")
    if reason_code:
        tool_trigger_codes.append(reason_code)

    if classification.get("retryable", False) and attempt < MAX_TOOL_RETRY:
        trace.append("tool_retry_gate:retry_tool")
        return {
            "attempt": attempt + 1,
            "tool_failure_classification": classification,
            "tool_retry_decision": "RETRY_TOOL",
            "tool_trigger_codes": tool_trigger_codes,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    trace.append("tool_retry_gate:no_retry")
    return {
        "tool_failure_classification": classification,
        "tool_retry_decision": "NO_RETRY",
        "tool_trigger_codes": tool_trigger_codes,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }