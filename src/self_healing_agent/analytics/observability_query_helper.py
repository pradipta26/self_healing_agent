from typing import Any, Dict, List, Optional
from datetime import datetime
from psycopg2.extras import RealDictCursor
from self_healing_agent.utils.db_utils import get_db_connection


# ------------------------------------------------------------------
# NOTE:
# - These are thin helpers over SQL
# - No business logic here (important for maintainability)
# - Designed for future API wrapping
# ------------------------------------------------------------------


def _execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or {})
            return cur.fetchall()
    finally:
        conn.close()


# ============================================================
# TOOL EXECUTION
# ============================================================

def get_tool_execution_summary(
    start_time_utc: Optional[str] = None,
    end_time_utc: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = """
        SELECT
            tool_name,
            execution_phase,
            COUNT(*) AS total_attempts,
            COUNT(*) FILTER (WHERE ok = true) AS success_count,
            COUNT(*) FILTER (WHERE ok = false) AS failure_count,
            ROUND(
                COUNT(*) FILTER (WHERE ok = true)::numeric / NULLIF(COUNT(*), 0),
                4
            ) AS success_rate
        FROM tool_execution_log
        WHERE (%(start_time)s IS NULL OR timestamp_utc >= %(start_time)s)
          AND (%(end_time)s IS NULL OR timestamp_utc < %(end_time)s)
        GROUP BY tool_name, execution_phase
        ORDER BY total_attempts DESC
    """

    return _execute_query(
        query,
        {
            "start_time": start_time_utc,
            "end_time": end_time_utc,
        },
    )


# ============================================================
# RETRY SUMMARY
# ============================================================

def get_retry_summary(
    start_time_utc: Optional[str] = None,
    end_time_utc: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = """
        SELECT
            tool_name,
            execution_phase,
            COUNT(*) AS total_attempts,
            COUNT(*) FILTER (WHERE retry_decision = 'RETRY_TOOL') AS retry_count,
            ROUND(
                COUNT(*) FILTER (WHERE retry_decision = 'RETRY_TOOL')::numeric / NULLIF(COUNT(*), 0),
                4
            ) AS retry_rate
        FROM tool_execution_log
        WHERE (%(start_time)s IS NULL OR timestamp_utc >= %(start_time)s)
          AND (%(end_time)s IS NULL OR timestamp_utc < %(end_time)s)
        GROUP BY tool_name, execution_phase
        ORDER BY retry_rate DESC
    """

    return _execute_query(
        query,
        {
            "start_time": start_time_utc,
            "end_time": end_time_utc,
        },
    )


# ============================================================
# ROLLBACK SUMMARY
# ============================================================

def get_rollback_summary(
    start_time_utc: Optional[str] = None,
    end_time_utc: Optional[str] = None,
) -> Dict[str, Any]:
    query = """
        SELECT
            COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_SUCCEEDED') AS success_count,
            COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_FAILED') AS failure_count,
            COUNT(*) FILTER (
                WHERE event_type IN ('ROLLBACK_VERIFICATION_SUCCEEDED', 'ROLLBACK_VERIFICATION_FAILED')
            ) AS total,
            ROUND(
                COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_SUCCEEDED')::numeric /
                NULLIF(
                    COUNT(*) FILTER (
                        WHERE event_type IN ('ROLLBACK_VERIFICATION_SUCCEEDED', 'ROLLBACK_VERIFICATION_FAILED')
                    ),
                    0
                ),
                4
            ) AS success_rate
        FROM decision_lifecycle_event
        WHERE (%(start_time)s IS NULL OR timestamp_utc >= %(start_time)s)
          AND (%(end_time)s IS NULL OR timestamp_utc < %(end_time)s)
    """

    result = _execute_query(
        query,
        {
            "start_time": start_time_utc,
            "end_time": end_time_utc,
        },
    )

    return result[0] if result else {}


# ============================================================
# DECISION ROUTE SUMMARY
# ============================================================

def get_decision_route_summary(
    start_time_utc: Optional[str] = None,
    end_time_utc: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = """
        SELECT
            route,
            COUNT(*) AS count,
            ROUND(COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0), 4) AS ratio
        FROM decision_log
        WHERE (%(start_time)s IS NULL OR timestamp_utc >= %(start_time)s)
          AND (%(end_time)s IS NULL OR timestamp_utc < %(end_time)s)
        GROUP BY route
        ORDER BY count DESC
    """

    return _execute_query(
        query,
        {
            "start_time": start_time_utc,
            "end_time": end_time_utc,
        },
    )


# ============================================================
# RECENT FAILURES (OPERATOR VIEW)
# ============================================================

def get_recent_failures(
    limit: int = 50,
) -> List[Dict[str, Any]]:
    query = """
        SELECT
            incident_id,
            execution_phase,
            tool_name,
            error_code,
            failure_type,
            retry_decision,
            side_effect_committed,
            timestamp_utc
        FROM tool_execution_log
        WHERE ok = false
        ORDER BY timestamp_utc DESC
        LIMIT %(limit)s
    """

    return _execute_query(query, {"limit": limit})


# ============================================================
# INCIDENT EXECUTION SUMMARY (DRILLDOWN)
# ============================================================

def get_incident_execution_summary(
    incident_id: str,
) -> Dict[str, Any]:
    """
    Returns a full execution summary for a single incident:
    - decision metadata
    - tool execution summary
    - rollback info
    """

    # Decision summary
    decision_query = """
        SELECT
            decision_id,
            trace_id,
            incident_id,
            source_incident_id,
            route,
            escalation_type,
            confidence,
            actionability,
            summary,
            timestamp_utc
        FROM decision_log
        WHERE incident_id = %(incident_id)s
        ORDER BY timestamp_utc DESC
        LIMIT 1
    """

    decision_result = _execute_query(decision_query, {"incident_id": incident_id})
    decision = decision_result[0] if decision_result else {}

    # Tool execution summary
    tool_query = """
        SELECT
            id,
            execution_phase,
            tool_step,
            attempt,
            tool_name,
            action_family,
            executor,
            ok,
            error_code,
            failure_type,
            retry_decision,
            side_effect_committed,
            timestamp_utc
        FROM tool_execution_log
        WHERE incident_id = %(incident_id)s
        ORDER BY tool_step, attempt, id
    """

    tool_execution = _execute_query(tool_query, {"incident_id": incident_id})

    # Full lifecycle timeline
    lifecycle_query = """
        SELECT
            event_type,
            event_status,
            reason_code,
            payload,
            timestamp_utc
        FROM decision_lifecycle_event
        WHERE incident_id = %(incident_id)s
        ORDER BY timestamp_utc, id
    """

    lifecycle_timeline = _execute_query(lifecycle_query, {"incident_id": incident_id})

    # Rollback-focused subset for convenience
    rollback_events = [
        event
        for event in lifecycle_timeline
        if str(event.get("event_type", "")).startswith("ROLLBACK_")
    ]

    return {
        "incident_id": incident_id,
        "decision": decision,
        "tool_execution": tool_execution,
        "lifecycle_timeline": lifecycle_timeline,
        "rollback_events": rollback_events,
    }
