from __future__ import annotations

import uuid
from typing import Any

from self_healing_agent.agent.state import AgentState, DecisionSnapshot


def _build_trigger_codes(state: AgentState) -> list[str]:
    trigger_codes: list[str] = []

    if state.get("kill_switch_state") == "ENABLED":
        trigger_codes.append("AUTONOMY_DISABLED_KILLSWITCH")

    context_validation = state.get("context_validation", {})
    validity = context_validation.get("validity")

    if validity == "CONFLICTING":
        trigger_codes.append("RETRIEVAL_CONFLICTING")
    elif validity == "LOW_QUALITY":
        trigger_codes.append("CONTEXT_LOW_QUALITY")
    elif validity == "EMPTY":
        trigger_codes.append("RETRIEVAL_EMPTY")

    grounding_check = state.get("grounding_check", {})
    if grounding_check.get("verdict") != "GROUNDED":
        trigger_codes.append("GROUNDEDNESS_FAILED")

    return trigger_codes


def _compute_service_match(state: AgentState) -> bool:
    structured_input = state.get("structured_input", {})
    expected_service = structured_input.get("service_domain")

    evidence_candidates = state.get("evidence_candidates", [])
    if not expected_service or not evidence_candidates:
        return False

    top_service = evidence_candidates[0].get("service")
    return top_service == expected_service


def build_decision(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    retrieval_policy_route = state.get("retrieval_policy_route", "HITL_INVESTIGATION")
    retrieval_escalation_type = state.get("retrieval_escalation_type", "INSUFFICIENT_EVIDENCE")

    grounding_policy_route = state.get("grounding_policy_route", "HITL_INVESTIGATION")
    grounding_escalation_type = state.get("grounding_escalation_type", "INSUFFICIENT_EVIDENCE")

    model_output = state.get("model_output", {})
    kill_switch_state = state.get("kill_switch_state", "DISABLED")

    # -----------------------------
    # route / escalation resolution
    # -----------------------------
    if kill_switch_state == "ENABLED":
        route = "HITL_INVESTIGATION"
        escalation_type = "POLICY_VIOLATION"
        required_human_role = "INVESTIGATOR"
        actionability = "INSUFFICIENT_EVIDENCE"
        summary = "Autonomy is disabled by kill switch. Human investigation required."

    elif retrieval_policy_route != "PROCEED":
        route = "HITL_INVESTIGATION"
        escalation_type = retrieval_escalation_type
        required_human_role = "INVESTIGATOR"
        actionability = (
            "CONFLICTING_SIGNALS"
            if retrieval_escalation_type == "CONFLICTING_SIGNALS"
            else "INSUFFICIENT_EVIDENCE"
        )
        summary = "Retrieval policy blocked progression due to insufficient or conflicting evidence."

    elif grounding_policy_route != "PROCEED":
        route = "HITL_INVESTIGATION"
        escalation_type = grounding_escalation_type
        required_human_role = "INVESTIGATOR"
        actionability = (
            "CONFLICTING_SIGNALS"
            if grounding_escalation_type == "CONFLICTING_SIGNALS"
            else "INSUFFICIENT_EVIDENCE"
        )
        summary = "Grounding policy blocked progression because model claims were not sufficiently supported by evidence."

    else:
        route = "PROPOSE"
        escalation_type = "NONE"
        required_human_role = "NONE"
        actionability = model_output.get("actionability", "INSUFFICIENT_EVIDENCE")
        summary = "Evidence and grounding passed. Proposal can be generated."

    decision: DecisionSnapshot = {
        "decision_id": str(uuid.uuid4()),
        "policy_version": "v1",
        "route": route,
        "confidence": model_output.get("confidence", "UNKNOWN"),
        "actionability": actionability,
        "escalation_type": escalation_type,
        "trigger_codes": _build_trigger_codes(state),
        "service_match": _compute_service_match(state),
        "required_human_role": required_human_role,
        "summary": summary,
        "facts": {
            "retrieval_policy_route": retrieval_policy_route,
            "grounding_policy_route": grounding_policy_route,
            "retrieval_escalation_type": retrieval_escalation_type,
            "grounding_escalation_type": grounding_escalation_type,
            "grounding_verdict": state.get("grounding_check", {}).get("verdict"),
            "context_validity": state.get("context_validation", {}).get("validity"),
            "top_evidence_doc_ids": state.get("grounding_check", {}).get("used_evidence_doc_ids", []),
        },
    }

    trace.append(f"build_decision:{route.lower()}")

    return {
        "decision": decision,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }