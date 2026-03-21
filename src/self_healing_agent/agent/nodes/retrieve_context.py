from typing import Any
from self_healing_agent.agent.state import AgentState
from self_healing_agent.retrieval.retrieval_service import retrieve_incident_context
def retrieve_documents(state: AgentState) -> dict[str, Any]:
    structured_input = state.get("structured_input", {})
    incident_context = retrieve_incident_context(structured_input)

    evidence_candidates = incident_context.get("retrieved_docs", [])
    retrieval_stages = incident_context.get("retrieval_stages", [])
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
        trace.append("retrieve_documents:ok")

    return {
        "evidence_candidates": evidence_candidates,
        "retrieval_stages": retrieval_stages,
        "rco": rco,
        "filtered_evidence": filtered_evidence,
        "evidence_valid": evidence_valid,
        "warnings": warnings,
        "trace": trace,

        # ✅ ONLY structured errors
        "error_flag": status == "ERROR",
        "errors": errors,
    }