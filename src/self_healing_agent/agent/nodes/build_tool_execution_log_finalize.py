from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState, ToolExecutionLogRecord



def build_tool_execution_log_finalize(state: AgentState) -> dict[str, Any]:
    """
    Build the finalize/update payload for the current tool_execution_log row.

    Expected to run after:
    - execute_tool
    - tool_retry_gate

    This node does not create a new row; it prepares the updated record values
    for the row inserted earlier by the start-log nodes.
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    tool_execution_log_id = state.get("tool_execution_log_id")
    if not tool_execution_log_id:
        trace.append("build_tool_execution_log_finalize:missing_log_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_execution_log_id is missing for finalize record.",
        }

    existing_record = state.get("tool_execution_log_record", {}) or {}
    tool_result = state.get("tool_result", {}) or {}
    failure_classification = state.get("tool_failure_classification", {}) or {}
    tool_trigger_codes = list(state.get("tool_trigger_codes", []))

    if not existing_record:
        trace.append("build_tool_execution_log_finalize:missing_existing_record")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_execution_log_record is missing for finalize record.",
        }

    tool_execution_log_record: ToolExecutionLogRecord = {
        **existing_record,
        "id": int(tool_execution_log_id),
        "raw_result_json": tool_result.get("raw", {}) or {},
        "ok": bool(tool_result.get("ok", False)),
        "error": tool_result.get("error", ""),
        "error_code": tool_result.get("error_code", ""),
        "failure_type": failure_classification.get("failure_type"),
        "retryable": failure_classification.get("retryable"),
        "tool_trigger_codes_json": tool_trigger_codes,
        "side_effect_committed": bool(tool_result.get("side_effect_committed", False)),
        "retry_decision": state.get("tool_retry_decision", "NO_RETRY"),
        "timestamp_utc": state.get("timestamp_utc"),
    }
    tool_name = str(tool_execution_log_record.get("tool_name", "UNKNOWN")).strip()

    trace.append(f"build_tool_execution_log_finalize:{tool_name}:ok")

    return {
        "tool_execution_log_record": tool_execution_log_record,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }