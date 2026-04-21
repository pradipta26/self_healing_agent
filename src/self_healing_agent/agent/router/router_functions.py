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
    return "build_investigation_request"


def invoke_llm_router(state: AgentState):
    if not state.get("error_flag", True):
        return "check_grounding"
    return "send_error_notification"


def grounding_check_router(state: AgentState):
    if not state.get("error_flag", True):
        return "grounding_policy_decision"
    return "send_error_notification"


def action_policy_router(state: AgentState):
    action_policy = state.get("action_policy_decision", {})
    execution_mode = action_policy.get("execution_mode", "BLOCKED")

    if execution_mode == "BLOCKED":
        return "build_investigation_request"

    if execution_mode == "PROPOSE_ONLY":
        return "build_proposal_output"

    if execution_mode == "APPROVAL_REQUIRED":
        return "build_approval_request"

    if execution_mode == "AUTO_EXECUTE":
        return "pre_execution_guard"

    return "build_investigation_request"


def decision_log_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"
    if state.get("approval_request", {}).get("request_id"):
        return "persist_approval_request"
    return "END"


def persist_approval_request_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"
    return "build_approval_requested_event"


def persist_approval_requested_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"
    return "hitl_approval"


def hitl_approval_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"
    return "build_approval_response_event"


def build_approval_response_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"
    return "persist_lifecycle_event_approval_response"


def persist_approval_response_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    approval_response = state.get("approval_response", {})
    status = str(approval_response.get("status", "PENDING")).strip().upper()

    if status == "APPROVED":
        return "pre_execution_guard"

    return "build_investigation_request"


def pre_execution_guard_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    guard = state.get("pre_execution_guard", {})
    if guard.get("ok"):
        return "prepare_tool_call"

    return "build_investigation_request"


def prepare_tool_call_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_tool_execution_log_start"


def execute_tool_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"
    return "tool_retry_gate"


def tool_retry_gate_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_tool_execution_log_finalize"


def build_tool_execution_log_start_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "persist_tool_execution_log_start"


def persist_tool_execution_log_start_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_tool_execution_event"


def build_tool_execution_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "persist_lifecycle_event_tool_execution"


def persist_lifecycle_event_tool_execution_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    lifecycle_event = state.get("lifecycle_event", {}) or {}
    event_type = str(lifecycle_event.get("event_type", "")).strip().upper()

    if event_type in {
        "TOOL_EXECUTION_STARTED",
        "TOOL_EXECUTION_RETRY_SCHEDULED",
        "ROLLBACK_EXECUTION_STARTED",
        "ROLLBACK_EXECUTION_RETRY_SCHEDULED",
    }:
        return "execute_tool"

    return "verify_tool_output"


def build_tool_execution_log_finalize_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "persist_tool_execution_log_finalize"


def persist_tool_execution_log_finalize_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_tool_execution_event"


def verify_tool_output_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_tool_output_verification_event"


def validate_action_result_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_action_validation_event"


def build_tool_output_verification_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "persist_lifecycle_event_tool_output_verification"


def persist_tool_output_verification_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    verification = state.get("tool_verification_result", {})
    if not verification.get("ok", False):
        return "build_investigation_request"

    execution_phase = str(state.get("execution_phase", "FORWARD")).strip().upper()
    if execution_phase == "ROLLBACK":
        return "verify_rollback"

    return "validate_action_result"


def build_action_validation_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "persist_lifecycle_event_action_validation"


def persist_action_validation_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    action_validation = state.get("action_verification_result", {})
    if action_validation.get("ok"):
        return "END"

    return "rollback_or_investigation"


def rollback_or_investigation_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    rollback_plan = state.get("rollback_plan", {}) or {}
    rollback_status = str(rollback_plan.get("status", "SKIPPED")).strip().upper()
    rollback_actions = rollback_plan.get("actions", []) or []

    if rollback_status == "PLANNED" and rollback_actions:
        return "prepare_rollback_tool_call"

    return "build_investigation_request"


def verify_rollback_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_rollback_verification_event"


def prepare_rollback_tool_call_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "build_tool_execution_log_start"


def build_rollback_verification_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    return "persist_lifecycle_event_rollback_verification"


def persist_rollback_verification_event_router(state: AgentState):
    if state.get("error_flag", False):
        return "send_error_notification"

    rollback_plan = state.get("rollback_plan", {}) or {}
    rollback_status = str(rollback_plan.get("status", "FAILED")).strip().upper()

    if rollback_status == "EXECUTED":
        return "END"

    return "build_investigation_request"