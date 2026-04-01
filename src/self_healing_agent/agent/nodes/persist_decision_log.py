import json
from typing import Any
from psycopg2.extras import Json

from self_healing_agent.agent.state import AgentState
from self_healing_agent.utils.db_utils import get_db_connection

from self_healing_agent.utils.utils import get_logger

logger = get_logger(__name__)

def _get_primary_metric(structured_input: dict[str, Any]) -> str | None:
    metric_names = structured_input.get("metric_names", []) or []
    return metric_names[0] if metric_names else None


def _get_primary_host(structured_input: dict[str, Any]) -> str | None:
    hosts = structured_input.get("hosts", []) or []
    return hosts[0] if hosts else None


def persist_decision_log(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision_log = state.get("decision_log", {})
    decision = state.get("decision", {})
    structured_input = state.get("structured_input", {})

    if not decision_log:
        trace.append("persist_decision_log:missing_decision_log")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Decision log is missing from state.",
        }

    sql = """
    INSERT INTO decision_log (
        decision_id,
        trace_id,
        incident_id,
        parent_incident_id,

        autonomy_mode,
        kill_switch_state,
        dry_run,

        policy_version,
        route,
        confidence,
        actionability,
        escalation_type,
        required_human_role,
        service_match,

        incident_type,
        service_domain,
        metric_name,
        datacenter,
        app_name,
        host,
        reason,

        trigger_codes,
        warnings,
        summary,
        facts,
        policy_checks,

        evidence_ref_ids,
        retrieved_doc_ids,
        evidence_snapshot,
        rco_summary,
        query_rewrite,

        retrieval_score_avg,
        retrieval_empty,
        conflicting_signals,

        tool_plan_hash,

        execution_status,
        rollback_status,

        human_decision,
        human_reason,

        structured_input,
        decision_snapshot,

        model_name,
        model_version,

        decision_latency_ms,
        schema_version,
        timestamp_utc
    )
    VALUES (
        %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s,
        %s, %s,
        %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s
    )
    """

    values = (
        # Identity / correlation
        decision_log.get("decision_id"),
        decision_log.get("trace_id"),
        decision_log.get("incident_id"),
        decision_log.get("parent_incident_id"),

        # Runtime mode / safety state
        decision_log.get("autonomy_mode"),
        decision_log.get("kill_switch_state"),
        decision_log.get("dry_run"),

        # Decision outcome
        decision_log.get("policy_version"),
        decision_log.get("route"),
        decision_log.get("confidence"),
        decision_log.get("actionability"),
        decision_log.get("escalation_type"),
        decision.get("required_human_role"),
        decision.get("service_match"),

        # Canonical context at decision time
        structured_input.get("incident_type"),
        structured_input.get("service_domain"),
        _get_primary_metric(structured_input),
        structured_input.get("datacenter"),
        structured_input.get("app_name"),
        _get_primary_host(structured_input),
        structured_input.get("reason"),

        # Explainability / audit
        decision.get("trigger_codes", []),
        warnings,
        decision.get("summary"),
        Json(decision.get("facts", {})),
        Json(decision_log.get("policy_checks", {})),

        # Evidence / retrieval references
        decision_log.get("evidence_ref_ids", []),
        decision_log.get("retrieved_doc_ids", []),
        Json(decision_log.get("evidence_snapshot", {})),
        decision_log.get("rco_summary"),
        Json(decision_log.get("query_rewrite")) if decision_log.get("query_rewrite") is not None else None,

        # Retrieval quality signals
        decision_log.get("retrieval_score_avg"),
        decision_log.get("retrieval_empty"),
        decision_log.get("conflicting_signals"),

        # Tool / execution references
        decision_log.get("tool_plan_hash"),

        # Execution outcome linkage
        decision_log.get("execution_status", "SKIPPED"),
        decision_log.get("rollback_status", "SKIPPED"),

        # Human outcome feedback
        decision_log.get("human_decision"),
        decision_log.get("human_reason"),

        # Raw committed artifacts for auditability
        Json(structured_input),
        Json(decision),

        # Model metadata
        decision_log.get("model_name"),
        decision_log.get("model_version"),

        # Metadata
        decision_log.get("decision_latency_ms"),
        decision_log.get("schema_version"),
        decision_log.get("timestamp_utc"),
    )

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(sql, values)
        conn.commit()

        trace.append("persist_decision_log:ok")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        if conn is not None:
            conn.rollback()

        warnings.append("DECISION_LOG_PERSIST_FAILED")
        trace.append("persist_decision_log:error")

        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Failed to persist decision log: {exc}",
        }

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()