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


def _derive_action_families(context_validation) -> list[str]:
    raw_families = context_validation.get("facts", {}).get("action_families", [])
    families = sorted({f for f in raw_families if f != "OTHER"})
    return families


def _build_evidence_snapshot(grounding_check, filtered_evidence) -> list[str]:
    grounded_doc_ids = { str(doc_id) for doc_id in grounding_check.get("used_evidence_doc_ids", [])}

    if grounded_doc_ids:
        grounded_snippets = []
        for grounded_doc_id in grounded_doc_ids:
            for doc in filtered_evidence:
                if f'parent_doc_id={grounded_doc_id}' in doc:
                    grounded_snippets.append(doc)
                    break
        
        if grounded_snippets:
            return grounded_snippets

    return filtered_evidence



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
    action_policy = state.get("action_policy_decision", {})
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
            "autonomy": {
                "mode": state.get("autonomy_mode"),
                "execution_mode": action_policy.get("execution_mode"),
                "effective_level": action_policy.get("effective_autonomy_level"),
                "allowed": action_policy.get("allowed"),
                "blast_radius": action_policy.get("blast_radius"),
                "action_families": action_policy.get("action_families"),
            }
        },

        # Evidence and intent references
        "evidence_ref_ids": _to_int_list(used_evidence_doc_ids),
        #"evidence_snapshot": state.get("evidence_snapshot", {}),
        "evidence_snapshot":_build_evidence_snapshot(state.get("grounding_check", {}), state.get("filtered_evidence", [])),
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