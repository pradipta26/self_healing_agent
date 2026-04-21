

from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.utils.db_utils import get_db_connection



def _persist_tool_execution_log_start(record: dict[str, Any]) -> int:
    sql = """
    INSERT INTO tool_execution_log (
        decision_id,
        trace_id,
        incident_id,
        source_incident_id,
        thread_id,
        execution_phase,
        tool_step,
        attempt,
        tool_name,
        action_family,
        executor,
        idempotency_key,
        tool_args_json,
        raw_result_json,
        ok,
        error,
        error_code,
        failure_type,
        retryable,
        retry_decision,
        side_effect_committed,
        tool_trigger_codes_json,
        timestamp_utc
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s
    )
    RETURNING id
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            sql,
            (
                record.get("decision_id"),
                record.get("trace_id"),
                record.get("incident_id"),
                record.get("source_incident_id"),
                record.get("thread_id"),
                record.get("execution_phase"),
                record.get("tool_step"),
                record.get("attempt"),
                record.get("tool_name"),
                record.get("action_family"),
                record.get("executor"),
                record.get("idempotency_key"),
                record.get("tool_args_json", {}),
                record.get("raw_result_json", {}),
                record.get("ok", False),
                record.get("error", ""),
                record.get("error_code", ""),
                record.get("failure_type"),
                record.get("retryable"),
                record.get("retry_decision", "NO_RETRY"),
                record.get("side_effect_committed", False),
                record.get("tool_trigger_codes_json", []),
                record.get("timestamp_utc"),
            ),
        )
        row = cursor.fetchone()
        conn.commit()

        if not row:
            raise RuntimeError("Failed to insert tool_execution_log start record.")

        return int(row[0])

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()



def persist_tool_execution_log_start(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    record = state.get("tool_execution_log_record", {}) or {}
    if not record:
        trace.append("persist_tool_execution_log_start:missing_record")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_execution_log_record is missing from state.",
        }

    try:
        tool_execution_log_id = _persist_tool_execution_log_start(record)
        trace.append("persist_tool_execution_log_start:ok")
        return {
            "tool_execution_log_id": tool_execution_log_id,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        trace.append("persist_tool_execution_log_start:error")
        warnings.append("TOOL_EXECUTION_LOG_START_PERSIST_FAILED")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Failed to persist tool_execution_log start record: {exc}",
        }