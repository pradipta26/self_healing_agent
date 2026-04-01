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


def build_decision_log(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    grounding_check = state.get("grounding_check", {})
    query_rewrite = state.get("query_rewrite")
    rco = state.get("rco", {})
    evidence_candidates = state.get("evidence_candidates", [])

    used_evidence_doc_ids = grounding_check.get("used_evidence_doc_ids", [])
    retrieved_doc_ids = [
        str(doc.get("doc_id"))
        for doc in evidence_candidates
        if doc.get("doc_id") is not None
    ]

    autonomy_mode = state.get("autonomy_mode", "OFF")
    kill_switch_state = state.get("kill_switch_state", "DISABLED")

    now_ms = int(time() * 1000)
    start_ms = state.get("decision_start_time_ms")
    decision_latency_ms = None

    if isinstance(start_ms, int):
        decision_latency_ms = now_ms - start_ms

    # Build decision log entry
    decision_log: DecisionLog = {
        # Identity / correlation
        "decision_id": decision.get("decision_id", ""),
        "trace_id": state.get("trace_id", ""),
        "incident_id": state.get("incident_id", ""),

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

        # Retrieval Quality Metrics
        "retrieval_score_avg": _compute_retrieval_score_avg(state.get("evidence_candidates", [])), 
        "retrieval_empty": len(state.get("filtered_evidence", [])) == 0, 
        "conflicting_signals": state.get("context_validation", {}).get("validity") == "CONFLICTING",

        # Policy gates
        "policy_checks": {
            "retrieval": {
                "route": state.get("retrieval_policy_route"),
                "confidence": state.get("rco", {}).get("confidence"),
            },
            "grounding": {
                "verdict": state.get("grounding_check", {}).get("verdict"),
            },
            "actionability": {
                "family": state.get("context_validation", {}).get("facts", {}).get("action_families", []),
                "allowed": state.get("proposal_output", {}).get("approval_required", True) == False,
            },
            "autonomy": {
                "mode": state.get("autonomy_mode"),
                "effective_level": "L1" if state.get("autonomy_mode") == "SHADOW" else "L2" if state.get("autonomy_mode") == "LIVE" else "L0",
            }
        },

        # Evidence and intent references
        "evidence_ref_ids": _to_int_list(used_evidence_doc_ids),
        "evidence_snapshot": state.get("evidence_snapshot", {}),

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