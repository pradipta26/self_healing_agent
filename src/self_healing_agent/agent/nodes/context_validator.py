from typing import Any
from self_healing_agent.agent.state import AgentState
from self_healing_agent.retrieval.context_validation_service import validate_retrieval_context


def validate_context(state: AgentState) -> dict[str, Any]:
    retrieved_docs = state.get("evidence_candidates", [])
    filtered_evidence = state.get("filtered_evidence", [])
    rco = state.get("rco", {})

    context_validation = validate_retrieval_context(
        retrieved_docs,
        filtered_evidence,
        rco,
    )

    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    evidence_valid = bool(
        context_validation.get("ok", False)
        and context_validation.get("validity") == "VALID"
    )

    if evidence_valid:
        trace.append("retry_context_validation:ok")
        warnings = [warning for warning in warnings if "CONFLICTING" not in warning
                    and warning not in {"CONTEXT_LOW_QUALITY", "RETRIEVAL_EMPTY"}]

    else:
        validity = context_validation.get("validity", "LOW_QUALITY")
        if validity == "CONFLICTING":
            warnings.append("RETRIEVAL_CONFLICTING")
        elif validity == "LOW_QUALITY":
            warnings.append("CONTEXT_LOW_QUALITY")
        elif validity == "EMPTY":
            warnings.append("RETRIEVAL_EMPTY")

        trace.append(f"context_validation:{validity.lower()}")

    return {
        "context_validation": context_validation,
        "evidence_valid": evidence_valid,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }