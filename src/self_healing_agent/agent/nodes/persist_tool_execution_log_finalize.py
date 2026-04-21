

from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.utils.db_utils import get_db_connection



def _persist_tool_execution_log_finalize(record: dict[str, Any]) -> None:
    sql = """
    UPDATE tool_execution_log
    SET raw_result_json = %s,
        ok = %s,
        error = %s,
        error_code = %s,
        failure_type = %s,
        retryable = %s,
        retry_decision = %s,
        side_effect_committed = %s,
        tool_trigger_codes_json = %s,
        timestamp_utc = %s
    WHERE id = %s
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            sql,
            (
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
                record.get("id"),
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                f"Failed to update tool_execution_log finalize record for id={record.get('id')}"
            )

        conn.commit()

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()



def persist_tool_execution_log_finalize(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    record = state.get("tool_execution_log_record", {}) or {}
    if not record:
        trace.append("persist_tool_execution_log_finalize:missing_record")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_execution_log_record is missing from state for finalize persistence.",
        }

    record_id = record.get("id")
    if not record_id:
        trace.append("persist_tool_execution_log_finalize:missing_record_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "tool_execution_log_record.id is missing for finalize persistence.",
        }

    try:
        _persist_tool_execution_log_finalize(record)
        trace.append("persist_tool_execution_log_finalize:ok")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        trace.append("persist_tool_execution_log_finalize:error")
        warnings.append("TOOL_EXECUTION_LOG_FINALIZE_PERSIST_FAILED")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Failed to persist tool_execution_log finalize record: {exc}",
        }