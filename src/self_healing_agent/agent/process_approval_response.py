from __future__ import annotations

from self_healing_agent.core.models import HitlResponsePayload
from self_healing_agent.utils.db_utils import get_db_connection
from langgraph.types import Command
from self_healing_agent.agent.service import get_graph


def validate_request_id_exists(request_id: str) -> bool:
    sql = """
    SELECT 1
    FROM approval_request
    WHERE request_id = %s
    LIMIT 1
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (request_id,))
        row = cursor.fetchone()
        return row is not None
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_thread_id_by_request_id(request_id: str) -> str:
    sql = """
    SELECT thread_id
    FROM approval_request
    WHERE request_id = %s
    LIMIT 1
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (request_id,))
        row = cursor.fetchone()

        if row is None:
            raise ValueError(f"No approval_request found for request_id={request_id}")

        thread_id = row[0]
        if not thread_id:
            raise ValueError(f"thread_id is missing for request_id={request_id}")

        return str(thread_id)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def resume_incident(payload: HitlResponsePayload) -> None:
    thread_id = get_thread_id_by_request_id(payload.request_id)

    graph = get_graph()

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    resume_payload = {
        "request_id": payload.request_id,
        "status": payload.status,
        "responder": payload.reviewer,
        "reason": payload.reason,
        "timestamp_utc": payload.timestamp_utc,
    }

    graph.invoke(Command(resume=resume_payload), config=config)