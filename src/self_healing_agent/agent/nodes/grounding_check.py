from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.grounding.grounding_service import check_grounding


def grounding_check(state: AgentState) -> dict[str, Any]:
    model_output = state.get("model_output", {})
    filtered_evidence = state.get("filtered_evidence", [])
    evidence_candidates = state.get("evidence_candidates", [])

    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    grounding_result = check_grounding(
        model_output=model_output,
        filtered_evidence=filtered_evidence,
        evidence_candidates=evidence_candidates,
    )

    verdict = grounding_result.get("verdict", "NOT_GROUNDED")

    if verdict == "GROUNDED":
        trace.append("grounding_check:grounded")

    elif verdict == "PARTIALLY_GROUNDED":
        warnings.append("GROUNDEDNESS_FAILED")
        trace.append("grounding_check:partially_grounded")

    else:
        warnings.append("GROUNDEDNESS_FAILED")
        trace.append("grounding_check:not_grounded")

    return {
        "grounding_check": grounding_result,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }