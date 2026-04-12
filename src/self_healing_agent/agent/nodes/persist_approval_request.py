from __future__ import annotations

from typing import Any

from psycopg2.extras import Json

from self_healing_agent.agent.state import AgentState
from self_healing_agent.utils.db_utils import get_db_connection


def persist_approval_request(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    approval_request = state.get("approval_request", {})
    decision_log = state.get("decision_log", {})
    thread_id = state.get("thread_id")

    if not approval_request:
        trace.append("persist_approval_request:missing_approval_request")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Approval request is missing from state.",
        }

    if not decision_log:
        trace.append("persist_approval_request:missing_decision_log")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Decision log is missing from state.",
        }

    decision_id = decision_log.get("decision_id")
    if not decision_id:
        trace.append("persist_approval_request:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Decision ID is missing from decision_log.",
        }

    if not thread_id:
        trace.append("persist_approval_request:missing_thread_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "thread_id is missing from state.",
        }

    sql = """
    INSERT INTO approval_request (
        request_id,
        decision_id,
        thread_id,
        status,
        required_human_role,
        approval_request_payload,
        workflow_state_snapshot,
        reviewer,
        review_reason,
        created_at,
        updated_at,
        responded_at
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s
    )
    """

    values = (
        approval_request.get("request_id"),
        decision_id,
        thread_id,
        "PENDING",
        approval_request.get("required_human_role", "APPROVER"),
        Json(approval_request),
        Json(state),   # keep as backup only
        None,          # reviewer
        None,          # review_reason
        None,          # responded_at
    )

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()

        trace.append("persist_approval_request:ok")

        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        if conn is not None:
            conn.rollback()

        trace.append("persist_approval_request:error")
        warnings.append("APPROVAL_REQUEST_PERSIST_FAILED")

        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Failed to persist approval request: {exc}",
        }

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()