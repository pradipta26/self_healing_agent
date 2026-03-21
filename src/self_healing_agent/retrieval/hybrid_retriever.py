# self_healing_agent/src/self_healing_agent/retrieval/hybrid_retriever.py
from typing import Any

from psycopg2.extensions import connection as Connection

from self_healing_agent.utils.rag_utils import embed_text
from self_healing_agent.utils.utils import get_db_connection, get_logger

logger = get_logger(__name__)

SQL_QUERY_TEMPLATE = """
        SELECT
            ranked.parent_id,
            ranked.similarity
        FROM (
            SELECT
                parent_id,
                metric_name,
                incident_type,
                1 - (embedding <=> %s::vector) AS similarity,
                ROW_NUMBER() OVER (
                    PARTITION BY parent_id
                    ORDER BY embedding <=> %s::vector
                ) AS row_num
            FROM prdb_incident_chunk
            WHERE chunk_type = 'problem'
"""
STRICT_SQL_QUERY_TEMPLATE = (
    SQL_QUERY_TEMPLATE
    + """
          AND metric_name = %s
          AND incident_type = %s
        ) AS ranked
        WHERE ranked.row_num = 1
        ORDER BY ranked.similarity DESC
        LIMIT %s
"""
)

METRIC_SQL_QUERY_TEMPLATE = (
    SQL_QUERY_TEMPLATE
    + """
          AND metric_name = %s
        ) AS ranked
        WHERE ranked.row_num = 1
        ORDER BY ranked.similarity DESC
        LIMIT %s
"""
)

BROAD_SQL_QUERY_TEMPLATE = (
    SQL_QUERY_TEMPLATE
    + """
        ) AS ranked
        WHERE ranked.row_num = 1
        ORDER BY ranked.similarity DESC
        LIMIT %s
"""
)


def _vector_to_pg(value: list[float]) -> str:
    return "[" + ",".join(str(x) for x in value) + "]"


def _search_problem_chunks(
    conn: Connection,
    vector_str: str,
    metric_name: str | None = None,
    incident_type: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:

    if limit <= 0:
        return {
            "status": "OK",
            "matches": [],
            "errors": [],
        }

    if metric_name and incident_type:
        sql_query = STRICT_SQL_QUERY_TEMPLATE
        query_params = (vector_str, vector_str, metric_name, incident_type, limit)
    elif metric_name:
        sql_query = METRIC_SQL_QUERY_TEMPLATE
        query_params = (vector_str, vector_str, metric_name, limit)
    else:
        sql_query = BROAD_SQL_QUERY_TEMPLATE
        query_params = (vector_str, vector_str, limit)

    cur = conn.cursor()
    try:
        cur.execute(sql_query, query_params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        matches = [dict(zip(columns, row)) for row in rows]
        return {
            "status": "OK",
            "matches": matches,
            "errors": [],
        }
    except Exception as e:
        logger.error(f"Error searching problem chunks: {e}")
        return {
            "status": "ERROR",
            "matches": [],
            "errors": [
                {
                    "stage": "SEARCH",
                    "error_type": "DB_ERROR",
                    "message": f"Error searching problem chunks: {e}",
                }
            ],
        }
    finally:
        cur.close()


def fetch_resolution_chunks_by_parent_id(
    conn: Connection,
    parent_id: int,
    vector_str: str,
) -> dict[str, Any]:

    if not parent_id:
        return {
            "status": "NOT_FOUND",
            "match": None,
            "errors": [],
        }

    sql_query = """
        SELECT
            problem.id,
            problem.parent_id,
            problem.service_domain,
            problem.app_name,
            problem.datacenter,
            problem.incident_type,
            problem.metric_name,
            problem.chunk_text AS problem_text,
            problem.chunk_text_normalized AS problem_text_normalized,
            1 - (problem.embedding <=> %s::vector) AS similarity,
            resolution.chunk_text AS resolution_text,
            resolution.chunk_text_normalized AS resolution_text_normalized
        FROM prdb_incident_chunk AS problem
        LEFT JOIN prdb_incident_chunk AS resolution
            ON resolution.parent_id = problem.parent_id
           AND resolution.chunk_type = 'resolution'
        WHERE problem.parent_id = %s
          AND problem.chunk_type = 'problem'
        ORDER BY problem.embedding <=> %s::vector, resolution.id
        LIMIT 1
    """

    cur = conn.cursor()
    try:
        cur.execute(sql_query, (vector_str, parent_id, vector_str))
        row = cur.fetchone()
        if row is None:
            return {
                "status": "NOT_FOUND",
                "match": None,
                "errors": [],
            }

        columns = [desc[0] for desc in cur.description]
        return {
            "status": "OK",
            "match": dict(zip(columns, row)),
            "errors": [],
        }
    except Exception as e:
        logger.error(f"Error fetching resolution chunk by parent id {parent_id}: {e}")
        return {
            "status": "ERROR",
            "match": None,
            "errors": [
                {
                    "stage": "RESOLUTION_FETCH",
                    "error_type": "DB_ERROR",
                    "message": f"Error fetching resolution chunk by parent id {parent_id}: {e}",
                }
            ],
        }
    finally:
        cur.close()


def _append_matches(
    conn: Connection,
    vector_str: str,
    search_matches: list[dict[str, Any]],
    retrieval_level: str,
    all_matches: list[dict[str, Any]],
    seen_parent_ids: set[int],
    errors: list[dict[str, str]],
) -> None:
    for search_match in search_matches:
        parent_id = search_match["parent_id"]
        if parent_id in seen_parent_ids:
            continue

        resolution_result = fetch_resolution_chunks_by_parent_id(conn, parent_id, vector_str)

        if resolution_result["status"] == "ERROR":
            errors.extend(resolution_result["errors"])
            continue

        if resolution_result["status"] == "NOT_FOUND":
            errors.append(
                {
                    "stage": "RESOLUTION_FETCH",
                    "retrieval_stage": retrieval_level,
                    "error_type": "NOT_FOUND",
                    "message": f"No problem/resolution row found for parent_id={parent_id}",
                }
            )
            continue
        match = resolution_result["match"]
        match["retrieval_level"] = retrieval_level
        all_matches.append(match)
        seen_parent_ids.add(parent_id)


def hybrid_retrieve(
    query_text: str,
    metric_name: str | None,
    incident_type: str | None,
    limit: int = 5,
) -> dict[str, Any]:

    if limit <= 0:
        return {
            "status": "OK",
            "matches": [],
            "errors": [],
        }

    conn = None
    all_matches: list[dict[str, Any]] = []
    seen_parent_ids: set[int] = set()
    errors: list[dict[str, str]] = []

    try:
        try:
            query_embedding = embed_text(query_text)
            vector_str = _vector_to_pg(query_embedding)
        except Exception as e:
            logger.error(f"Error embedding query text: {e}")
            return {
                "status": "ERROR",
                "matches": [],
                "errors": [
                    {
                        "stage": "EMBEDDING",
                        "error_type": "EMBEDDING_ERROR",
                        "message": f"Error embedding query text: {e}",
                    }
                ],
            }

        try:
            conn = get_db_connection()
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return {
                "status": "ERROR",
                "matches": [],
                "errors": [
                    {
                        "stage": "DB_CONNECTION",
                        "error_type": "DB_ERROR",
                        "message": f"Error connecting to database: {e}",
                    }
                ],
            }

        strict_result = _search_problem_chunks(
            conn=conn,
            vector_str=vector_str,
            metric_name=metric_name,
            incident_type=incident_type,
            limit=limit,
        )
        errors.extend([{
                **err,
                "retrieval_stage": "STRICT",
            } for err in strict_result["errors"]]
                if strict_result["status"] == "ERROR" else []
        )
        _append_matches(
            conn=conn,
            vector_str=vector_str,
            search_matches=strict_result["matches"],
            retrieval_level="STRICT",
            all_matches=all_matches,
            seen_parent_ids=seen_parent_ids,
            errors=errors,
        )
        if len(all_matches) >= limit:
            return {
                "status": "PARTIAL_ERROR" if errors else "OK",
                "matches": all_matches[:limit],
                "errors": errors,
            }

        current_limit = limit - len(all_matches)
        if current_limit > 0:
            metric_result = _search_problem_chunks(
                conn=conn,
                vector_str=vector_str,
                metric_name=metric_name,
                limit=current_limit,
            )

            errors.extend([{
                **err,
                "retrieval_stage": "METRIC_ONLY",
                } for err in metric_result["errors"]]
                    if metric_result["status"] == "ERROR" else []
            )
            
            _append_matches(
                conn=conn,
                vector_str=vector_str,
                search_matches=metric_result["matches"],
                retrieval_level="METRIC_ONLY",
                all_matches=all_matches,
                seen_parent_ids=seen_parent_ids,
                errors=errors,
            )
            if len(all_matches) >= limit:
                return {
                    "status": "PARTIAL_ERROR" if errors else "OK",
                    "matches": all_matches[:limit],
                    "errors": errors,
                }

        current_limit = limit - len(all_matches)
        if current_limit > 0:
            broad_result = _search_problem_chunks(
                conn=conn,
                vector_str=vector_str,
                limit=current_limit,
            )

            errors.extend([{
                **err,
                "retrieval_stage": "BROAD",
                } for err in broad_result["errors"]]
                    if broad_result["status"] == "ERROR" else []
            )

            _append_matches(
                conn=conn,
                vector_str=vector_str,
                search_matches=broad_result["matches"],
                retrieval_level="BROAD",
                all_matches=all_matches,
                seen_parent_ids=seen_parent_ids,
                errors=errors,
            )

        if all_matches:
            return {
                "status": "PARTIAL_ERROR" if errors else "OK",
                "matches": all_matches[:limit],
                "errors": errors,
            }

        if errors:
            return {
                "status": "ERROR",
                "matches": [],
                "errors": errors,
            }

        return {
            "status": "OK",
            "matches": [],
            "errors": [],
        }

    finally:
        if conn is not None:
            conn.close()


# Example usage:
if __name__ == "__main__":
    query = (
        "B6VV service. service instance incident. in BDC datacenter. "
        "application DVSB2B POSCOMMON B2B. metric Active Threads. "
        "reason active threads exceeded threshold."
    )

    result = hybrid_retrieve(
        query_text=query,
        metric_name="Active Threads",
        incident_type="Service Instance",
        limit=3,
    )

    from pprint import pprint
    pprint(result)