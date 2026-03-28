from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def grounding_policy_decision(state: AgentState) -> dict[str, Any]:
    grounding_check = state.get("grounding_check", {})
    verdict = grounding_check.get("verdict", "NOT_GROUNDED")

    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    if verdict == "GROUNDED":
        trace.append("grounding_policy:proceed")
        return {
            "grounding_policy_route": "PROCEED",
            "grounding_escalation_type": "NONE",
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    if verdict == "PARTIALLY_GROUNDED":
        warnings.append("GROUNDEDNESS_FAILED")
        trace.append("grounding_policy:hitl_investigation_partial")
        return {
            "grounding_policy_route": "HITL_INVESTIGATION",
            "grounding_escalation_type": "INSUFFICIENT_EVIDENCE",
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    warnings.append("GROUNDEDNESS_FAILED")
    trace.append("grounding_policy:hitl_investigation_not_grounded")
    return {
        "grounding_policy_route": "HITL_INVESTIGATION",
        "grounding_escalation_type": "CONFIDENCE_EVIDENCE_MISMATCH",
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }