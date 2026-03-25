from typing import Any
from self_healing_agent.agent.state import AgentState

RETRIVAL_MAX_ATTEMPTS: int = 2  # max_attempts = 2
def retrieval_policy_decision(state: AgentState) -> dict[str, Any]:
    context_validation = state.get("context_validation", {})
    validity = context_validation.get("validity", "LOW_QUALITY")

    retrieval_stages = state.get("retrieval_stages", [])
    attempt_count = len(retrieval_stages)

    # -----------------------------
    # VALID → proceed
    # -----------------------------
    if validity == "VALID":
        return {
            "retrieval_policy_route": "PROCEED",
            "retrieval_escalation_type": "NONE",
        }

    # -----------------------------
    # Retry allowed
    # -----------------------------
    if attempt_count < RETRIVAL_MAX_ATTEMPTS:
        return {
            "retrieval_policy_route": "RETRY",
            "retrieval_escalation_type": "NONE",
        }

    # -----------------------------
    # Retry exhausted → escalate
    # -----------------------------
    if validity == "CONFLICTING":
        retrieval_escalation_type = "CONFLICTING_SIGNALS"
    else:
        retrieval_escalation_type = "INSUFFICIENT_EVIDENCE"

    return {
        "retrieval_policy_route": "ESCALATE",
        "retrieval_escalation_type": retrieval_escalation_type,
    }