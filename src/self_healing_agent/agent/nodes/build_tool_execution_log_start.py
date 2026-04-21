from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState, ToolExecutionLogRecord
from self_healing_agent.observability.metrics import emit_counter
from self_healing_agent.observability.metrics_contract import TOOL_ATTEMPT_COUNT



def build_tool_execution_log_start(state: AgentState) -> dict[str, Any]:
    """
    Build the initial tool_execution_log record before tool execution begins.

    This guarantees that once a flow reaches tool preparation, a tool log row
    can be inserted even if execution or later lifecycle nodes fail.
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {}) or {}
    tool_definition = state.get("tool_definition", {}) or {}
    tool_call = state.get("tool_call", {}) or {}

    decision_id = str(decision.get("decision_id", "")).strip()
    trace_id = str(state.get("trace_id", "")).strip()
    incident_id = str(state.get("incident_id", "")).strip()
    thread_id = str(state.get("thread_id", "")).strip()
    execution_phase = str(state.get("execution_phase", "FORWARD")).strip().upper()
    source_incident_id = state.get("source_incident_id")

    if not decision_id:
        trace.append("build_tool_execution_log_start:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for tool_execution_log start record.",
        }

    if not trace_id:
        trace.append("build_tool_execution_log_start:missing_trace_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "trace_id is missing for tool_execution_log start record.",
        }

    if not incident_id:
        trace.append("build_tool_execution_log_start:missing_incident_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "incident_id is missing for tool_execution_log start record.",
        }

    if not thread_id:
        trace.append("build_tool_execution_log_start:missing_thread_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "thread_id is missing for tool_execution_log start record.",
        }

    tool_name = str(tool_call.get("tool_name", "")).strip()
    if not tool_name:
        trace.append("build_tool_execution_log_start:missing_tool_name")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call.tool_name is missing for tool_execution_log start record.",
        }

    idempotency_key = str(tool_call.get("idempotency_key", "")).strip()
    if not idempotency_key:
        trace.append("build_tool_execution_log_start:missing_idempotency_key")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_call.idempotency_key is missing for tool_execution_log start record.",
        }

    tool_execution_log_record: ToolExecutionLogRecord = {
        "decision_id": decision_id,
        "trace_id": trace_id,
        "incident_id": incident_id,
        "source_incident_id": source_incident_id,
        "thread_id": thread_id,
        "execution_phase": execution_phase,
        "tool_step": int(state.get("tool_step", 0)),
        "attempt": int(state.get("attempt", 1)),
        "tool_name": tool_name,
        "action_family": tool_definition.get("action_family"),
        "executor": tool_definition.get("executor"),
        "idempotency_key": idempotency_key,
        "tool_args_json": tool_call.get("args", {}) or {},
        "raw_result_json": {},
        "ok": False,
        "error": "",
        "error_code": "",
        "failure_type": None,
        "retryable": None,
        "retry_decision": "NO_RETRY",
        "side_effect_committed": False,
        "tool_trigger_codes_json": [],
        "timestamp_utc": state.get("timestamp_utc"),
    }

    emit_counter(
        TOOL_ATTEMPT_COUNT,
        tool_name=tool_name,
        execution_phase=execution_phase,
    )

    trace.append(f"build_tool_execution_log_start:{tool_name}:ok")

    return {
        "tool_execution_log_record": tool_execution_log_record,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }