from self_healing_agent.agent.state import AgentState


def parse_raw_incident_text_router(state: AgentState):
    if not state.get("error_flag", True):
        return "validate_input"
    return "send_error_notification"


def validate_input_router(state: AgentState):
    if not state.get("error_flag", True):
        return "retrieve_documents"
    return "send_error_notification"


def retrive_document_router(state: AgentState):
    if not state.get("error_flag", True):
        return "validate_context"
    return "send_error_notification"


def query_rewrite_and_retry_router(state: AgentState):
    if not state.get("error_flag", True):
        return "validate_context"
    return "send_error_notification"


def retrieval_policy_router(state: AgentState):
    route = state.get("retrieval_policy_route", "")
    if route == "PROCEED":
        return "invoke_llm"
    if route == "RETRY":
        return "query_rewrite_and_retry"
    return "build_decision"


def invoke_llm_router(state: AgentState):
    if not state.get("error_flag", True):
        return "check_grounding"
    return "send_error_notification"


def grounding_check_router(state: AgentState):
    if not state.get("error_flag", True):
        return "grounding_policy_decision"
    return "send_error_notification"


# def build_decision_router(state: AgentState):
#     route = state.get("decision", {}).get("route", "")
#     if route == "PROPOSE":
#         return "build_proposal_output"
#     return "build_investigation_request"

def action_policy_router(state: AgentState):
    decision_route = state.get("decision", {}).get("route", "")
    action_policy = state.get("action_policy_decision", {})

    execution_mode = action_policy.get("execution_mode", "BLOCKED")

    # Step 1: If decision itself is not PROPOSE → investigation
    if decision_route != "PROPOSE":
        return "build_investigation_request"

    # Step 2: Apply action policy
    if execution_mode == "BLOCKED":
        return "build_investigation_request"

    # For now (V1), everything else goes to proposal
    return "build_proposal_output"