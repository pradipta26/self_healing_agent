from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState, ProposalOutput
from self_healing_agent.grounding.evidence_helpers import get_cited_evidence


def build_proposal_output(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    decision = state.get("decision", {})
    structured_input = state.get("structured_input", {})
    model_output = state.get("model_output", {})
    filtered_evidence = state.get("filtered_evidence", [])

    route = decision.get("route")

    if route != "PROPOSE":
        trace.append("build_proposal_output:skipped_non_propose")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    service = structured_input.get("service_domain", "UNKNOWN")
    env = structured_input.get("env", "DEV")
    category = model_output.get("category", "UNKNOWN")
    summary = model_output.get("description", "No summary available.")
    proposals = model_output.get("remediation", [])
    
    cited_evidence = get_cited_evidence(model_output, filtered_evidence)

    proposal_output: ProposalOutput = {
        "service": service,
        "env": env,
        "category": category,
        "summary": summary,
        "evidence": cited_evidence,
        "proposals": proposals,
        "approval_required": False,
    }

    trace.append("build_proposal_output:ok")

    return {
        "proposal_output": proposal_output,
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }