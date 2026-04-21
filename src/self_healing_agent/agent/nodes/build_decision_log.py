from __future__ import annotations

from typing import Any
from time import time

from self_healing_agent.agent.state import AgentState, DecisionLog


def _to_int_list(values: list[Any]) -> list[int]:
    result: list[int] = []
    for value in values:
        text = str(value).strip()
        if text.isdigit():
            result.append(int(text))
    return result


def _compute_retrieval_score_avg(evidence_candidates: list[dict[str, Any]]) -> float | None:
    rerank_scores: list[float] = []
    vector_scores: list[float] = []

    for doc in evidence_candidates:
        rerank_score = doc.get("rerank_score")
        if isinstance(rerank_score, (int, float)):
            rerank_scores.append(float(rerank_score))

        vector_score = doc.get("vector_score")
        if isinstance(vector_score, (int, float)):
            vector_scores.append(float(vector_score))

    if rerank_scores:
        return round(sum(rerank_scores) / len(rerank_scores), 6)

    if vector_scores:
        return round(sum(vector_scores) / len(vector_scores), 6)

    return None


def _derive_action_families(context_validation: dict[str, Any]) -> list[str]:
    raw_families = context_validation.get("facts", {}).get("action_families", []) or []
    families = sorted({str(f).strip().upper() for f in raw_families if str(f).strip().upper() != "OTHER"})
    return families


def _build_evidence_snapshot(
    grounding_check: dict[str, Any],
    filtered_evidence: list[Any],
) -> list[Any]:
    grounded_doc_ids = [str(doc_id).strip() for doc_id in grounding_check.get("used_evidence_doc_ids", []) or []]
    grounded_doc_id_set = {doc_id for doc_id in grounded_doc_ids if doc_id}

    if grounded_doc_id_set:
        grounded_snippets: list[Any] = []
        for doc in filtered_evidence:
            if isinstance(doc, dict):
                parent_doc_id = str(doc.get("parent_doc_id", "")).strip()
                doc_id = str(doc.get("doc_id", "")).strip()
                if parent_doc_id in grounded_doc_id_set or doc_id in grounded_doc_id_set:
                    grounded_snippets.append(doc)
                    continue

            text = str(doc)
            for grounded_doc_id in grounded_doc_ids:
                if grounded_doc_id and f"parent_doc_id={grounded_doc_id}" in text:
                    grounded_snippets.append(doc)
                    break

        if grounded_snippets:
            return grounded_snippets

    return filtered_evidence



def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None



def _safe_int_latency(start_ms: Any, now_ms: int) -> int | None:
    if not isinstance(start_ms, int):
        return None
    if start_ms > now_ms:
        return None
    return now_ms - start_ms


def build_decision_log(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    context_validation = state.get("context_validation", {}) or {}
    filtered_evidence = state.get("filtered_evidence", []) or []
    evidence_candidates = state.get("evidence_candidates", []) or []

    grounding_check = state.get("grounding_check", {})
    query_rewrite = state.get("query_rewrite")
    rco = state.get("rco", {})

    used_evidence_doc_ids = grounding_check.get("used_evidence_doc_ids", []) or []
    retrieved_doc_ids = [
        str(doc.get("doc_id")).strip()
        for doc in evidence_candidates
        if isinstance(doc, dict) and doc.get("doc_id") is not None
    ]

    autonomy_mode = state.get("autonomy_mode", "OFF")
    kill_switch_state = state.get("kill_switch_state", "DISABLED")
    action_policy = state.get("action_policy_decision", {})
    now_ms = int(time() * 1000)
    start_ms = state.get("decision_start_time_ms")
    decision_latency_ms = _safe_int_latency(start_ms, now_ms)

    # Build decision log entry
    decision_log: DecisionLog = {
        # Identity / correlation
        "decision_id": decision.get("decision_id", ""),
        "trace_id": state.get("trace_id", ""),
        "incident_id": state.get("incident_id", ""),
        "source_incident_id": state.get("source_incident_id", ""),

        # Execution mode / safety gates at decision time
        "autonomy_mode": autonomy_mode,
        "kill_switch_state": kill_switch_state,
        "dry_run": autonomy_mode != "LIVE",

        # Decision outcome
        "policy_version": decision.get("policy_version", "v1"),
        "route": decision.get("route", "HITL_INVESTIGATION"),
        "confidence": decision.get("confidence", "UNKNOWN"),
        "actionability": decision.get("actionability", "INSUFFICIENT_EVIDENCE"),
        "escalation_type": decision.get("escalation_type", "INSUFFICIENT_EVIDENCE"),
        "summary": decision.get("summary", ""),
        "trigger_codes": decision.get("trigger_codes", []) or [],

        # Retrieval Quality Metrics
        "retrieval_score_avg": _compute_retrieval_score_avg(evidence_candidates),
        "retrieval_empty": len(filtered_evidence) == 0,
        "conflicting_signals": context_validation.get("validity") == "CONFLICTING",

        # Policy gates
        "policy_checks": {
            "retrieval": {
                "route": state.get("retrieval_policy_route"),
                "confidence": rco.get("confidence"),
                "context_validity": context_validation.get("validity"),
            },
            "grounding": {
                "verdict": grounding_check.get("verdict"),
                "grounded": _safe_bool(grounding_check.get("ok")),
            },
            "autonomy": {
                "mode": autonomy_mode,
                "execution_mode": action_policy.get("execution_mode"),
                "effective_level": action_policy.get("effective_autonomy_level"),
                "allowed": _safe_bool(action_policy.get("allowed")),
                "blast_radius": action_policy.get("blast_radius"),
                "action_families": action_policy.get("action_families") or _derive_action_families(context_validation),
            },
        },

        # Evidence and intent references
        "evidence_ref_ids": _to_int_list(used_evidence_doc_ids),
        #"evidence_snapshot": state.get("evidence_snapshot", {}),
        "evidence_snapshot": _build_evidence_snapshot(grounding_check, filtered_evidence),

        # Execution planning metadata
        "execution_phase": state.get("execution_phase"),
        "planned_tool_name": state.get("tool_call", {}).get("tool_name"),
        "planned_tool_executor": state.get("tool_definition", {}).get("executor"),

        "tool_plan_hash": None,

        # RAG / retrieval references
        "rco_summary": rco.get("summary"),
        "retrieved_doc_ids": retrieved_doc_ids,
        "query_rewrite": query_rewrite,

        # Model references
        "model_name": state.get("llm_model_name"),
        "model_version": state.get("llm_model_version"),

        # Timing
        "decision_latency_ms": decision_latency_ms,
        # Metadata
        "timestamp_utc": state.get("timestamp_utc", ""),
        "schema_version": "v1",
    }

    trace.append("build_decision_log:ok")

    return {
        "decision_log": decision_log,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }