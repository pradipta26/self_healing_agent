from __future__ import annotations

import uuid
from typing import Any

from self_healing_agent.agent.state import AgentState, InvestigationRequest
from self_healing_agent.grounding.evidence_helpers import get_cited_evidence_or_fallback

def _build_investigation_questions(escalation_type: str) -> list[str]:
    if escalation_type == "CONFLICTING_SIGNALS":
        return [
            "Which evidence source should be trusted for this incident?",
            "Are conflicting recovery patterns expected for this service or environment?",
            "Does current runtime state support restart, defer, or another action?",
        ]

    if escalation_type == "CONFIDENCE_EVIDENCE_MISMATCH":
        return [
            "Which model claims are unsupported by the cited evidence?",
            "Should remediation be reformulated using only grounded evidence?",
            "Is additional human review needed before any proposal is shared?",
        ]

    if escalation_type == "POLICY_VIOLATION":
        return [
            "Was this escalation caused by a system policy gate or operational control?",
            "Is the current environment under a kill switch, freeze, or restricted mode?",
            "Should this incident remain manual until policy restrictions are cleared?",
        ]

    return [
        "What additional evidence is needed to reach a safe conclusion?",
        "Can the current runtime state of the affected service or component be confirmed manually?",
        "Are there missing diagnostics, logs, or health checks for this incident?",
    ]


def _build_data_to_collect(category: str) -> list[str]:
    base = [
        "Current application health check status",
        "Affected host and process runtime status",
        "Recent alert timeline and correlated logs",
    ]

    category_specific: dict[str, list[str]] = {
        "JVM": [
            "JVM process status on affected hosts",
            "Recent JVM restart history",
            "Application instance registration / status check",
        ],
        "DATABASE": [
            "Database connectivity status",
            "Recent DB session or lock metrics",
            "Relevant DB error logs",
        ],
        "NETWORK": [
            "Recent network error or timeout metrics",
            "Dependency connectivity status",
            "Relevant load balancer / gateway logs",
        ],
        "APPLICATION": [
            "Application instance health and runtime status",
            "Recent deployment or restart history",
            "Relevant application error logs",
        ],
        "DEPENDENCY": [
            "Downstream dependency health status",
            "Recent timeout or connection failure metrics",
            "Dependency-specific logs or alerts",
        ],
        "CONFIGURATION": [
            "Recent configuration changes",
            "Application startup/runtime configuration values",
            "Recent deployment or config rollout history",
        ],
        "STORAGE": [
            "Disk or filesystem utilization",
            "Recent storage growth / cleanup history",
            "Relevant storage-related system logs",
        ],
        "CPU": [
            "CPU utilization trend",
            "Process-level CPU consumers",
            "Recent workload spike or deployment history",
        ],
        "MEMORY": [
            "Memory utilization trend",
            "Heap / process memory usage",
            "Recent OOM or garbage collection indicators",
        ],
    }

    return base + category_specific.get(category, [])


def _infer_escalation_origin_step(state: AgentState) -> str | None:
    """
    Prefer deterministic control-plane source over raw trace parsing.
    Falls back to last meaningful trace item if needed.
    """
    decision = state.get("decision", {})
    escalation_type = decision.get("escalation_type", "NONE")

    if escalation_type == "POLICY_VIOLATION":
        return "build_decision"

    grounding_policy_route = state.get("grounding_policy_route")
    if grounding_policy_route and grounding_policy_route != "PROCEED":
        return "grounding_policy"

    grounding_check = state.get("grounding_check", {})
    if grounding_check.get("verdict") and grounding_check.get("verdict") != "GROUNDED":
        return "grounding_check"

    retrieval_policy_route = state.get("retrieval_policy_route")
    if retrieval_policy_route and retrieval_policy_route != "PROCEED":
        return "retrieval_policy"

    context_validation = state.get("context_validation", {})
    if context_validation.get("validity") and context_validation.get("validity") != "VALID":
        return "context_validation"

    trace = state.get("trace", [])
    if trace:
        return trace[-1]

    return None


def _build_escalation_reason(state: AgentState) -> str:
    decision = state.get("decision", {})
    escalation_type = decision.get("escalation_type", "INSUFFICIENT_EVIDENCE")

    if escalation_type == "CONFLICTING_SIGNALS":
        return "System escalated because available signals or evidence were conflicting."

    if escalation_type == "CONFIDENCE_EVIDENCE_MISMATCH":
        return "System escalated because model claims were not sufficiently supported by grounded evidence."

    if escalation_type == "POLICY_VIOLATION":
        return "System escalated because a policy or operational control blocked automated progression."

    return "System escalated because available evidence was insufficient for a safe proposal."


def _collect_query_attempts(state: AgentState) -> list[str]:
    retrieval_stages = state.get("retrieval_stages", [])
    attempts: list[str] = []

    for stage in retrieval_stages:
        query_used = stage.get("query_used")
        if isinstance(query_used, str) and query_used.strip():
            attempts.append(query_used.strip())

    # keep order, remove duplicates
    seen: set[str] = set()
    deduped: list[str] = []
    for item in attempts:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)

    return deduped


def build_investigation_request(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    structured_input = state.get("structured_input", {})
    model_output = state.get("model_output", {})
    filtered_evidence = state.get("filtered_evidence", [])
    context_validation = state.get("context_validation", {})
    grounding_check = state.get("grounding_check", {})

    if decision.get("route") != "HITL_INVESTIGATION":
        trace.append("build_investigation_request:skipped_non_hitl")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    evidence = get_cited_evidence_or_fallback(model_output, filtered_evidence)
    escalation_type = decision.get("escalation_type", "INSUFFICIENT_EVIDENCE")
    category = model_output.get("category", "UNKNOWN")

    notes: list[str] = []

    decision_summary = decision.get("summary")
    if decision_summary:
        notes.append(decision_summary)

    notes.extend(context_validation.get("issues", []))
    notes.extend(grounding_check.get("notes", []))

    investigation_request: InvestigationRequest = {
        "request_id": str(uuid.uuid4()),
        "decision": decision,

        # Incident identity / source context
        "incident_id": state.get("incident_id", "UNKNOWN"),
        "incident_raw": state.get("incident_raw", ""),
        "service": structured_input.get("service_domain", "UNKNOWN"),
        "env": structured_input.get("env", "DEV"),
        "timestamp_utc": state.get("timestamp_utc", ""),

        # Why escalated
        "suspected_issue": model_output.get(
            "description",
            "Investigation required due to insufficient confidence or evidence.",
        ),
        "escalation_origin_step": _infer_escalation_origin_step(state),
        "escalation_reason": _build_escalation_reason(state),
        "error_message": state.get("error_message"),
        "warnings": warnings,
        "trigger_codes": decision.get("trigger_codes", []),

        # What system tried
        "query_attempts": _collect_query_attempts(state),
        "evidence": evidence,
        "suggested_actions": model_output.get("remediation", []),

        # Human guidance
        "notes": notes,
        "questions": _build_investigation_questions(escalation_type),
        "data_to_collect": _build_data_to_collect(category),
        "rollback_plan": {
            "status": "SKIPPED",
            "reason": "No automated action executed. Rollback not applicable.",
        },
    }

    trace.append("build_investigation_request:ok")

    return {
        "investigation_request": investigation_request,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }