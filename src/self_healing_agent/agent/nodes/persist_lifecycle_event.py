from __future__ import annotations

from typing import Any

from psycopg2.extras import Json

from self_healing_agent.agent.state import AgentState
from self_healing_agent.utils.db_utils import get_db_connection


def _persist_lifecycle_event_record(event: dict[str, Any]) -> None:
    """
    Reusable low-level DB insert helper for decision_lifecycle_event.
    Shared by both FORWARD and ROLLBACK lifecycle event paths.
    Assumes the table has these columns:

        decision_log_id BIGINT NULL
        decision_id TEXT NOT NULL
        event_type TEXT NOT NULL
        event_status TEXT NULL
        stage_name TEXT NULL
        actor_type TEXT NULL
        actor_id TEXT NULL
        request_id TEXT NULL
        related_entity_id TEXT NULL
        payload JSONB NOT NULL DEFAULT '{}'::jsonb
        notes JSONB NOT NULL DEFAULT '[]'::jsonb
        timestamp_utc TIMESTAMPTZ NOT NULL
    """
    sql = """
    INSERT INTO decision_lifecycle_event (
        decision_log_id,
        decision_id,
        event_type,
        event_status,
        stage_name,
        actor_type,
        actor_id,
        request_id,
        related_entity_id,
        payload,
        notes,
        timestamp_utc
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            sql,
            (
                event.get("decision_log_id"),
                event.get("decision_id"),
                event.get("event_type"),
                event.get("event_status"),
                event.get("stage_name"),
                event.get("actor_type"),
                event.get("actor_id"),
                event.get("request_id"),
                event.get("related_entity_id"),
                Json(event.get("payload", {})),
                Json(event.get("notes", [])),
                event.get("timestamp_utc"),
            ),
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


def persist_lifecycle_event(state: AgentState) -> dict[str, Any]:
    """
    Generic shared graph node for lifecycle-event persistence.
    Used by both FORWARD and ROLLBACK event builders.

    Expects:
        state["lifecycle_event"] = {
            "decision_log_id": ...,
            "decision_id": ...,
            "event_type": ...,
            "event_status": ...,
            "stage_name": ...,
            "actor_type": ...,
            "actor_id": ...,
            "request_id": ...,
            "related_entity_id": ...,
            "payload": {...},
            "notes": [...],
            "timestamp_utc": ...
        }

    Examples of supported event families include:
    - approval events
    - tool execution / tool output verification events
    - action validation events
    - rollback execution / rollback verification events

    This node only persists one event at a time.
    """
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    event = state.get("lifecycle_event", {})
    if not event:
        trace.append("persist_lifecycle_event:missing_event")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "lifecycle_event is missing from state.",
        }

    if not event.get("decision_id"):
        trace.append("persist_lifecycle_event:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "lifecycle_event.decision_id is required.",
        }

    if not event.get("event_type"):
        trace.append("persist_lifecycle_event:missing_event_type")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "lifecycle_event.event_type is required.",
        }

    if not event.get("timestamp_utc"):
        trace.append("persist_lifecycle_event:missing_timestamp")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "lifecycle_event.timestamp_utc is required.",
        }

    try:
        _persist_lifecycle_event_record(event)
        trace.append(f"persist_lifecycle_event:{event.get('event_type')}")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        warnings.append("LIFECYCLE_EVENT_PERSIST_FAILED")
        trace.append("persist_lifecycle_event:error")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Failed to persist lifecycle event: {exc}",
        }