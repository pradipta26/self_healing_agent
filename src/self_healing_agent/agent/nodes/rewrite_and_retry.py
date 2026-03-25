from typing import Any
from self_healing_agent.agent.state import AgentState
from self_healing_agent.retrieval.retrieval_service import rewrite_query_and_retry


def query_rewrite_and_retry(state: AgentState) -> dict[str, Any]:
    original_query_text = state['retrieval_stages'][0]['query_used']
    structured_input = state['structured_input']
    context_validity: str = state["context_validation"]["validity"]

    incident_context = rewrite_query_and_retry(
        original_query=original_query_text, 
        structured_input=structured_input, context_validity=context_validity
    )
    
    query_rewrite_artifact = incident_context['query_rewrite_artifact']
    evidence_candidates = incident_context.get("retrieved_docs", [])[:3] # take top 3

    current_retrieval_stages = incident_context.get("retrieval_stages", [])
    retrieval_stages = state.get("retrieval_stages", []) + current_retrieval_stages 

    rco = incident_context.get("retrieval_confidence", {})
    errors = incident_context.get("errors", [])
    status = incident_context.get("status", "ERROR")

    # -----------------------------
    # filtered evidence
    # -----------------------------
    filtered_evidence = [
        doc.get("snippet")
        for doc in evidence_candidates
        if doc.get("snippet")
    ][:3]

    # -----------------------------
    # evidence validity
    # -----------------------------
    evidence_valid = bool(
        rco.get("is_sufficient", False)
        and rco.get("validity") == "VALID"
        and filtered_evidence
    )

    # -----------------------------
    # warnings + trace
    # -----------------------------
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))
    
    if status == "ERROR":
        warnings.append("RETRIEVAL_EMPTY")
        trace.append("retrieve_documents:error")

    elif status == "PARTIAL_ERROR":
        warnings.append("CONTEXT_LOW_QUALITY")
        trace.append("retrieve_documents:partial_error")

    elif not evidence_candidates:
        warnings.append("RETRIEVAL_EMPTY")
        trace.append("retrieve_documents:empty")

    elif not evidence_valid:
        warnings.append("CONTEXT_LOW_QUALITY")
        trace.append("retrieve_documents:low_quality")

    else:
        trace.append("query_rewrite_and_retry:ok")

    error_flag = False
    error_message = None

    if errors:
        warnings.extend(
            f"{err.get('stage')}:{err.get('error_type')}"
            for err in errors
        )

        error_flag = True
        error_message = "; ".join(
            err.get("message", "") for err in errors if err.get("message")
        )
    return {
        "query_rewrite": query_rewrite_artifact,
        "evidence_candidates": evidence_candidates,
        "retrieval_stages": retrieval_stages,
        "rco": rco,
        "filtered_evidence": filtered_evidence,
        "evidence_valid": evidence_valid,
        "warnings": warnings,
        "trace": trace,

        # ✅ ONLY structured errors
        "error_flag": error_flag,
        "error_message": error_message
    }