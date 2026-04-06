from __future__ import annotations

from typing import Any

from self_healing_agent.utils.db_utils import get_db_connection


def _fetch_one_dict(cursor, query: str) -> dict[str, Any]:
    cursor.execute(query)
    row = cursor.fetchone()
    if not row:
        return {}

    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def _fetch_many_dicts(cursor, query: str) -> list[dict[str, Any]]:
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def _to_kv_map(
    rows: list[dict[str, Any]],
    key_field: str,
    value_field: str = "count",
    empty_key: str = "UNKNOWN",
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for row in rows:
        key = row.get(key_field)
        if key in (None, ""):
            key = empty_key

        result[str(key)] = row.get(value_field, 0)

    return result


def get_decision_summary_metrics() -> dict[str, Any]:
    query = """
    SELECT
        COUNT(*) AS total_decisions,
        COUNT(*) FILTER (WHERE route = 'PROPOSE') AS propose_count,
        ROUND(
            COUNT(*) FILTER (WHERE route = 'PROPOSE')::numeric / NULLIF(COUNT(*), 0),
            4
        ) AS proposal_rate,
        COUNT(*) FILTER (WHERE route <> 'PROPOSE') AS escalation_count,
        ROUND(
            COUNT(*) FILTER (WHERE route <> 'PROPOSE')::numeric / NULLIF(COUNT(*), 0),
            4
        ) AS escalation_rate,
        ROUND(AVG(retrieval_score_avg)::numeric, 6) AS avg_retrieval_score,
        ROUND(AVG(decision_latency_ms)::numeric, 2) AS avg_decision_latency_ms
    FROM decision_log;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        return _fetch_one_dict(cursor, query)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_escalation_breakdown() -> dict[str, int]:
    query = """
    SELECT
        escalation_type,
        COUNT(*) AS count
    FROM decision_log
    GROUP BY escalation_type
    ORDER BY count DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = _fetch_many_dicts(cursor, query)
        return _to_kv_map(rows, key_field="escalation_type")

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_warning_breakdown() -> dict[str, int]:
    query = """
    SELECT
        unnest(warnings) AS warning,
        COUNT(*) AS count
    FROM decision_log
    GROUP BY warning
    ORDER BY count DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = _fetch_many_dicts(cursor, query)
        return _to_kv_map(rows, key_field="warning")

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_latency_metrics() -> dict[str, Any]:
    overall_query = """
    SELECT
        ROUND(AVG(decision_latency_ms)::numeric, 2) AS avg_latency_ms,
        MIN(decision_latency_ms) AS min_latency_ms,
        MAX(decision_latency_ms) AS max_latency_ms
    FROM decision_log
    WHERE decision_latency_ms IS NOT NULL;
    """

    by_route_query = """
    SELECT
        route,
        ROUND(AVG(decision_latency_ms)::numeric, 2) AS avg_latency_ms,
        COUNT(*) AS count
    FROM decision_log
    WHERE decision_latency_ms IS NOT NULL
    GROUP BY route
    ORDER BY avg_latency_ms DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        overall = _fetch_one_dict(cursor, overall_query)
        by_route_rows = _fetch_many_dicts(cursor, by_route_query)

        return {
            "overall": overall,
            "by_route": by_route_rows,
        }

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_retrieval_confidence_breakdown() -> dict[str, int]:
    query = """
    SELECT
        policy_checks -> 'retrieval' ->> 'confidence' AS retrieval_confidence,
        COUNT(*) AS count
    FROM decision_log
    GROUP BY retrieval_confidence
    ORDER BY count DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = _fetch_many_dicts(cursor, query)
        return _to_kv_map(rows, key_field="retrieval_confidence")

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_grounding_verdict_breakdown() -> dict[str, int]:
    query = """
    SELECT
        policy_checks -> 'grounding' ->> 'verdict' AS grounding_verdict,
        COUNT(*) AS count
    FROM decision_log
    GROUP BY grounding_verdict
    ORDER BY count DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = _fetch_many_dicts(cursor, query)
        return _to_kv_map(rows, key_field="grounding_verdict")

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_safe_proposal_metrics() -> dict[str, Any]:
    query = """
    SELECT
        COUNT(*) FILTER (
            WHERE route = 'PROPOSE'
              AND (facts ->> 'context_validity') = 'VALID'
              AND (facts ->> 'grounding_verdict') = 'GROUNDED'
        ) AS safe_proposals,
        COUNT(*) AS total_decisions,
        ROUND(
            COUNT(*) FILTER (
                WHERE route = 'PROPOSE'
                  AND (facts ->> 'context_validity') = 'VALID'
                  AND (facts ->> 'grounding_verdict') = 'GROUNDED'
            )::numeric / NULLIF(COUNT(*), 0),
            4
        ) AS safe_proposal_rate
    FROM decision_log;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        return _fetch_one_dict(cursor, query)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_retrieval_weakness_metrics() -> dict[str, Any]:
    query = """
    SELECT
        COUNT(*) FILTER (
            WHERE retrieval_empty = true
               OR conflicting_signals = true
               OR (facts ->> 'context_validity') IN ('LOW_QUALITY', 'CONFLICTING', 'EMPTY')
        ) AS weak_retrieval_cases,
        COUNT(*) AS total_decisions,
        ROUND(
            COUNT(*) FILTER (
                WHERE retrieval_empty = true
                   OR conflicting_signals = true
                   OR (facts ->> 'context_validity') IN ('LOW_QUALITY', 'CONFLICTING', 'EMPTY')
            )::numeric / NULLIF(COUNT(*), 0),
            4
        ) AS retrieval_weakness_rate
    FROM decision_log;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        return _fetch_one_dict(cursor, query)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_high_confidence_proposal_count() -> dict[str, Any]:
    query = """
    SELECT
        COUNT(*) AS high_confidence_proposals
    FROM decision_log
    WHERE route = 'PROPOSE'
      AND confidence = 'HIGH';
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        return _fetch_one_dict(cursor, query)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_route_distribution() -> dict[str, int]:
    query = """
    SELECT
        route,
        COUNT(*) AS count
    FROM decision_log
    GROUP BY route
    ORDER BY count DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = _fetch_many_dicts(cursor, query)
        return _to_kv_map(rows, key_field="route")

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_retrieval_score_by_service() -> list[dict[str, Any]]:
    query = """
    SELECT
        service_domain,
        ROUND(AVG(retrieval_score_avg)::numeric, 6) AS avg_retrieval_score,
        COUNT(*) AS count
    FROM decision_log
    WHERE retrieval_score_avg IS NOT NULL
    GROUP BY service_domain
    ORDER BY avg_retrieval_score DESC;
    """

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        return _fetch_many_dicts(cursor, query)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_all_decision_metrics() -> dict[str, Any]:
    """
    Aggregated entry point for dashboards / CLI / ad hoc analytics.
    """
    return {
        "summary": get_decision_summary_metrics(),
        "safe_proposals": get_safe_proposal_metrics(),
        "retrieval_weakness": get_retrieval_weakness_metrics(),
        "high_confidence_proposals": get_high_confidence_proposal_count(),
        "breakdowns": {
            "route_distribution": get_route_distribution(),
            "escalation_types": get_escalation_breakdown(),
            "retrieval_confidence": get_retrieval_confidence_breakdown(),
            "grounding_verdict": get_grounding_verdict_breakdown(),
            "warnings": get_warning_breakdown(),
        },
        "latency": get_latency_metrics(),
        "retrieval_score_by_service": get_retrieval_score_by_service(),
    }