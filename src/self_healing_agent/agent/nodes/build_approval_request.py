from __future__ import annotations

from typing import Any
from uuid import uuid4

from self_healing_agent.agent.state import AgentState, ApprovalRequest
from self_healing_agent.agent.nodes.helpers.execution_policy_fingerprint import build_execution_policy_fingerprint

def _build_notes(
    decision: dict[str, Any],
    action_policy_decision: dict[str, Any],
) -> list[str]:
    notes: list[str] = []

    confidence = decision.get("confidence")
    if confidence:
        notes.append(f"Decision confidence: {confidence}.")

    actionability = decision.get("actionability")
    if actionability:
        notes.append(f"Decision actionability: {actionability}.")

    execution_mode = action_policy_decision.get("execution_mode")
    if execution_mode:
        notes.append(f"Resolved execution mode: {execution_mode}.")

    blast_radius = action_policy_decision.get("blast_radius")
    if blast_radius:
        notes.append(f"Derived blast radius: {blast_radius}.")

    return notes


def _build_questions(action_policy_decision: dict[str, Any]) -> list[str]:
    blast_radius = action_policy_decision.get("blast_radius", "UNKNOWN")
    action_families = action_policy_decision.get("action_families", [])

    questions = [
        "Do you approve the proposed action based on the grounded evidence provided?",
        "Is there any operational reason this action should not be taken right now?",
    ]

    if blast_radius in {"MEDIUM", "HIGH", "UNKNOWN"}:
        questions.append(
            "Is the derived blast radius acceptable for the current incident scope?"
        )

    if action_families:
        questions.append(
            f"Are these action families acceptable: {', '.join(action_families)}?"
        )

    return questions


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

def build_approval_request(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    action_policy_decision = state.get("action_policy_decision", {})
    model_output = state.get("model_output", {})
    structured_input = state.get("structured_input", {})

    proposed_actions = model_output.get("remediation", [])
    evidence = _build_evidence_snapshot(state.get("grounding_check", {}), 
                                        state.get("filtered_evidence", []))
    initial_execution_policy_fingerprint = build_execution_policy_fingerprint(state)
    approval_request: ApprovalRequest = {
        "request_id": str(uuid4()),
        "decision": decision,
        "action_policy_decision": action_policy_decision,

        # Incident identity / source context
        "incident_id": state.get("incident_id", ""),
        "incident_raw": state.get("incident_raw", ""),
        "service": structured_input.get("service_domain", ""),
        "env": structured_input.get("env", "DEV"),
        "timestamp_utc": state.get("timestamp_utc", ""),

        # Approval context
        "proposed_actions": proposed_actions,
        "evidence": evidence,
        "blast_radius": action_policy_decision.get("blast_radius", "UNKNOWN"),
        "required_human_role": action_policy_decision.get("required_human_role", "APPROVER"),
        "reasons": action_policy_decision.get("reasons", []),

        # Human guidance
        "notes": _build_notes(decision, action_policy_decision),
        "questions": _build_questions(action_policy_decision),
    }

    trace.append("build_approval_request:ok")

    return {
        "approval_request": approval_request,
        "initial_execution_policy_fingerprint": initial_execution_policy_fingerprint,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }