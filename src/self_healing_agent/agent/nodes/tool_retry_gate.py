from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.tools.retry_classifier import classify_tool_failure
from self_healing_agent.observability.metrics import emit_counter
from self_healing_agent.observability.metrics_contract import (
    TOOL_RETRY_RATE,
    RETRY_ATTEMPT_COUNT,
    FAILURE_TYPE_DISTRIBUTION,
    SIDE_EFFECT_COMMITTED_RATE,
)

MAX_TOOL_RETRY = 2

def tool_retry_gate(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_result = state.get("tool_result", {})
    attempt = int(state.get("attempt", 1))
    tool_trigger_codes = list(state.get("tool_trigger_codes", []))

    tool_call = state.get("tool_call", {}) or {}
    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).strip()
    execution_phase = str(state.get("execution_phase", "FORWARD")).strip().upper()

    if tool_result.get("ok", False):
        emit_counter(
            FAILURE_TYPE_DISTRIBUTION,
            failure_type="NONE",
            tool_name=tool_name,
            execution_phase=execution_phase,
        )
        if bool(tool_result.get("side_effect_committed", False)):
            emit_counter(
                SIDE_EFFECT_COMMITTED_RATE,
                tool_name=tool_name,
                execution_phase=execution_phase,
                failure_type="NONE",
            )
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
    failure_type = classification.get("failure_type")
    retryable = classification.get("retryable", False)
    side_effect_committed = classification.get("side_effect_committed", False)
    reason_code = classification.get("reason_code")
    if reason_code:
        tool_trigger_codes.append(reason_code)

    emit_counter(
        FAILURE_TYPE_DISTRIBUTION,
        failure_type=str(failure_type or "UNKNOWN"),
        tool_name=tool_name,
        execution_phase=execution_phase,
    )

    if side_effect_committed:
        emit_counter(
            SIDE_EFFECT_COMMITTED_RATE,
            tool_name=tool_name,
            execution_phase=execution_phase,
            failure_type=str(failure_type or "UNKNOWN"),
        )

    # Do not retry if side effects already committed
    if side_effect_committed:
        trace.append("tool_retry_gate:no_retry_side_effect_committed")
        return {
            "tool_failure_classification": classification,
            "tool_retry_decision": "NO_RETRY",
            "tool_trigger_codes": tool_trigger_codes,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    if retryable and attempt < MAX_TOOL_RETRY:
        emit_counter(
            TOOL_RETRY_RATE,
            tool_name=tool_name,
            execution_phase=execution_phase,
            failure_type=str(failure_type or "UNKNOWN"),
        )
        emit_counter(
            RETRY_ATTEMPT_COUNT,
            tool_name=tool_name,
            execution_phase=execution_phase,
            failure_type=str(failure_type or "UNKNOWN"),
        )
        trace.append(f"tool_retry_gate:retry_tool:{failure_type}")
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

    trace.append(f"tool_retry_gate:no_retry:{failure_type}")
    return {
        "tool_failure_classification": classification,
        "tool_retry_decision": "NO_RETRY",
        "tool_trigger_codes": tool_trigger_codes,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }