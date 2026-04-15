from __future__ import annotations

from typing import Any

from self_healing_agent.utils.db_utils import get_db_connection


ACTIVE_STATUSES = {"ACTIVE"}
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


def try_acquire_incident_workflow_lock(
    hawkeye_incident_id: str,
    incident_id: str,
    thread_id: str,
) -> dict[str, Any]:
    """
    Try to register an ACTIVE workflow for a Hawkeye incident.

    Uses INSERT ... ON CONFLICT DO NOTHING for deterministic idempotency.

    Returns:
        {
            "acquired": bool,
            "reopened": bool,
            "existing_incident_id": str | None,
            "existing_thread_id": str | None,
            "workflow_status": str | None,
            "decision_id": str | None,
        }
    """

    insert_sql = """
    INSERT INTO incident_workflow_lock (
        hawkeye_incident_id,
        incident_id,
        workflow_status,
        thread_id,
        decision_id,
        created_at,
        updated_at
    )
    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (hawkeye_incident_id) DO NOTHING
    """

    select_sql = """
    SELECT hawkeye_incident_id, incident_id, workflow_status, thread_id, decision_id
    FROM incident_workflow_lock
    WHERE hawkeye_incident_id = %s
    LIMIT 1
    """

    reopen_sql = """
    UPDATE incident_workflow_lock
    SET incident_id = %s,
        workflow_status = %s,
        thread_id = %s,
        decision_id = %s,
        updated_at = NOW()
    WHERE hawkeye_incident_id = %s
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(insert_sql, ( hawkeye_incident_id, incident_id, "ACTIVE", thread_id, None, ))

        if cursor.rowcount == 1:
            conn.commit()
            return {
                "acquired": True,
                "reopened": False,
                "existing_incident_id": None,
                "existing_thread_id": None,
                "workflow_status": "ACTIVE",
                "decision_id": None,
            }

        # Conflict occurred → row already exists
        conn.commit()  # safe, no-op but consistent

        cursor.execute(select_sql, (hawkeye_incident_id,))
        row = cursor.fetchone()

        if row is None:
            # extremely rare race fallback
            return {
                "acquired": False,
                "reopened": False,
                "existing_incident_id": None,
                "existing_thread_id": None,
                "workflow_status": None,
                "decision_id": None,
            }

        existing_incident_id = row[1]
        existing_status = row[2]
        existing_thread_id = row[3]
        existing_decision_id = row[4]

        if existing_status in TERMINAL_STATUSES:
            cursor.execute(
                reopen_sql,
                (
                    incident_id,
                    "ACTIVE",
                    thread_id,
                    None,
                    hawkeye_incident_id,
                ),
            )
            conn.commit()
            return {
                "acquired": True,
                "reopened": True,
                "existing_incident_id": existing_incident_id,
                "existing_thread_id": existing_thread_id,
                "workflow_status": "ACTIVE",
                "decision_id": None,
            }

        return {
            "acquired": False,
            "reopened": False,
            "existing_incident_id": existing_incident_id,
            "workflow_status": existing_status,
            "existing_thread_id": existing_thread_id,
            "decision_id": existing_decision_id,
        }

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_incident_workflow_lock(
    hawkeye_incident_id: str,
) -> dict[str, Any] | None:
    """
    Read existing workflow lock row for a Hawkeye incident.
    """
    sql = """
    SELECT hawkeye_incident_id, incident_id, workflow_status, thread_id, decision_id
    FROM incident_workflow_lock
    WHERE hawkeye_incident_id = %s
    LIMIT 1
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (hawkeye_incident_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "hawkeye_incident_id": row[0],
            "incident_id": row[1],
            "workflow_status": row[2],
            "thread_id": row[3],
            "decision_id": row[4],
        }

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def mark_incident_workflow_completed(
    hawkeye_incident_id: str,
    decision_id: str | None,
) -> None:
    sql = """
    UPDATE incident_workflow_lock
    SET workflow_status = %s,
        decision_id = %s,
        updated_at = NOW()
    WHERE hawkeye_incident_id = %s
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, ("COMPLETED", decision_id, hawkeye_incident_id))
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


def mark_incident_workflow_failed(
    hawkeye_incident_id: str,
    decision_id: str | None,
) -> None:
    sql = """
    UPDATE incident_workflow_lock
    SET workflow_status = %s,
        decision_id = %s,
        updated_at = NOW()
    WHERE hawkeye_incident_id = %s
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, ("FAILED", decision_id, hawkeye_incident_id))
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


def mark_incident_workflow_cancelled(
    hawkeye_incident_id: str,
    decision_id: str | None,
) -> None:
    sql = """
    UPDATE incident_workflow_lock
    SET workflow_status = %s,
        decision_id = %s,
        updated_at = NOW()
    WHERE hawkeye_incident_id = %s
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, ("CANCELLED", decision_id, hawkeye_incident_id))
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