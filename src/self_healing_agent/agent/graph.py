from langgraph.graph import END, START, StateGraph

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.nodes.parse_raw_incident_text import parse_raw_incident_details
from self_healing_agent.agent.nodes.validate_input import validate_input
from self_healing_agent.agent.nodes.retrieve_context import retrieve_documents
from self_healing_agent.agent.nodes.context_validator import validate_context
from self_healing_agent.agent.nodes.rewrite_and_retry import query_rewrite_and_retry
from self_healing_agent.agent.nodes.retrieval_policy import retrieval_policy_decision
from self_healing_agent.agent.nodes.invoke_llm import invoke_llm
from self_healing_agent.agent.nodes.grounding_check import grounding_check
from self_healing_agent.agent.nodes.grounding_policy import grounding_policy_decision
from self_healing_agent.agent.nodes.build_decision import build_decision
from self_healing_agent.agent.nodes.evaluate_action_policy import evaluate_action_policy
from self_healing_agent.agent.nodes.build_proposal import build_proposal_output
from self_healing_agent.agent.nodes.build_investigation_request import build_investigation_request
from self_healing_agent.agent.nodes.build_approval_request import build_approval_request
from self_healing_agent.agent.nodes.build_decision_log import build_decision_log
from self_healing_agent.agent.nodes.persist_decision_log import persist_decision_log
from self_healing_agent.agent.nodes.persist_approval_request import persist_approval_request

from self_healing_agent.agent.nodes.build_approval_requested_event import build_approval_requested_event
from self_healing_agent.agent.nodes.build_approval_response_event import build_approval_response_event
from self_healing_agent.agent.nodes.build_tool_execution_event import build_tool_execution_event
from self_healing_agent.agent.nodes.build_tool_output_verification_event import build_tool_output_verification_event
from self_healing_agent.agent.nodes.build_action_validation_event import build_action_validation_event
from self_healing_agent.agent.nodes.persist_lifecycle_event import persist_lifecycle_event

from self_healing_agent.agent.nodes.build_tool_execution_log_start import build_tool_execution_log_start
from self_healing_agent.agent.nodes.persist_tool_execution_log_start import persist_tool_execution_log_start
from self_healing_agent.agent.nodes.build_tool_execution_log_finalize import build_tool_execution_log_finalize
from self_healing_agent.agent.nodes.persist_tool_execution_log_finalize import persist_tool_execution_log_finalize

from self_healing_agent.agent.nodes.hitl_approval import hitl_approval
from self_healing_agent.agent.nodes.pre_execution_guard import pre_execution_guard
from self_healing_agent.agent.nodes.prepare_tool_call import prepare_tool_call
from self_healing_agent.agent.nodes.execute_tool import execute_tool
from self_healing_agent.agent.nodes.tool_retry_gate import tool_retry_gate
from self_healing_agent.agent.nodes.verify_tool_output import verify_tool_output
from self_healing_agent.agent.nodes.validate_action_result import validate_action_result

from self_healing_agent.agent.nodes.rollback_or_investigation import rollback_or_investigation
from self_healing_agent.agent.nodes.prepare_rollback_tool_call import prepare_rollback_tool_call
from self_healing_agent.agent.nodes.verify_rollback import verify_rollback
from self_healing_agent.agent.nodes.build_rollback_verification_event import build_rollback_verification_event

from self_healing_agent.agent.nodes.error_notification import send_error_notification

from self_healing_agent.agent.router.router_functions import (
    parse_raw_incident_text_router,
    validate_input_router,
    retrive_document_router,
    query_rewrite_and_retry_router,
    retrieval_policy_router,
    invoke_llm_router,
    grounding_check_router,
    action_policy_router,
    decision_log_router,
    persist_approval_request_router,
    persist_approval_requested_event_router,
    hitl_approval_router,
    build_approval_response_event_router,
    persist_approval_response_event_router,
    pre_execution_guard_router,
    prepare_tool_call_router,
    build_tool_execution_log_start_router,
    persist_tool_execution_log_start_router,
    execute_tool_router,
    tool_retry_gate_router,
    build_tool_execution_log_finalize_router,
    persist_tool_execution_log_finalize_router,
    verify_tool_output_router,
    validate_action_result_router,
    build_tool_execution_event_router,
    persist_lifecycle_event_tool_execution_router,
    build_tool_output_verification_event_router,
    persist_tool_output_verification_event_router,
    build_action_validation_event_router,
    persist_action_validation_event_router,
    rollback_or_investigation_router,
    prepare_rollback_tool_call_router,
    verify_rollback_router,
    build_rollback_verification_event_router,
    persist_rollback_verification_event_router,
)


def build_graph(checkpointer=None):
    graph_builder = StateGraph(AgentState)

    # Core decisioning nodes
    graph_builder.add_node("parse_raw_incident_text", parse_raw_incident_details)
    graph_builder.add_node("validate_input", validate_input)
    graph_builder.add_node("retrieve_documents", retrieve_documents)
    graph_builder.add_node("validate_context", validate_context)
    graph_builder.add_node("query_rewrite_and_retry", query_rewrite_and_retry)
    graph_builder.add_node("retrieval_policy_decision", retrieval_policy_decision)
    graph_builder.add_node("invoke_llm", invoke_llm)
    graph_builder.add_node("check_grounding", grounding_check)
    graph_builder.add_node("grounding_policy_decision", grounding_policy_decision)
    graph_builder.add_node("build_decision", build_decision)
    graph_builder.add_node("evaluate_action_policy", evaluate_action_policy)
    graph_builder.add_node("build_proposal_output", build_proposal_output)
    graph_builder.add_node("build_investigation_request", build_investigation_request)
    graph_builder.add_node("build_approval_request", build_approval_request)
    graph_builder.add_node("build_decision_log", build_decision_log)
    graph_builder.add_node("persist_decision_log", persist_decision_log)
    graph_builder.add_node("persist_approval_request", persist_approval_request)

    # Approval lifecycle nodes
    graph_builder.add_node("build_approval_requested_event", build_approval_requested_event)
    graph_builder.add_node("persist_lifecycle_event_approval_requested", persist_lifecycle_event)
    graph_builder.add_node("build_approval_response_event", build_approval_response_event)
    graph_builder.add_node("persist_lifecycle_event_approval_response", persist_lifecycle_event)

    # Tool / execution lifecycle nodes
    graph_builder.add_node("build_tool_execution_log_start", build_tool_execution_log_start)
    graph_builder.add_node("persist_tool_execution_log_start", persist_tool_execution_log_start)
    graph_builder.add_node("build_tool_execution_log_finalize", build_tool_execution_log_finalize)
    graph_builder.add_node("persist_tool_execution_log_finalize", persist_tool_execution_log_finalize)
    graph_builder.add_node("build_tool_execution_event", build_tool_execution_event)
    graph_builder.add_node("persist_lifecycle_event_tool_execution", persist_lifecycle_event)
    graph_builder.add_node("build_tool_output_verification_event", build_tool_output_verification_event)
    graph_builder.add_node("persist_lifecycle_event_tool_output_verification", persist_lifecycle_event)
    graph_builder.add_node("build_action_validation_event", build_action_validation_event)
    graph_builder.add_node("persist_lifecycle_event_action_validation", persist_lifecycle_event)

    # Execution pipeline nodes
    graph_builder.add_node("hitl_approval", hitl_approval)
    graph_builder.add_node("pre_execution_guard", pre_execution_guard)
    graph_builder.add_node("prepare_tool_call", prepare_tool_call)
    graph_builder.add_node("execute_tool", execute_tool)
    graph_builder.add_node("tool_retry_gate", tool_retry_gate)
    graph_builder.add_node("verify_tool_output", verify_tool_output)
    graph_builder.add_node("validate_action_result", validate_action_result)
    # Rollback / investigation nodes
    graph_builder.add_node("rollback_or_investigation", rollback_or_investigation)
    graph_builder.add_node("prepare_rollback_tool_call", prepare_rollback_tool_call)
    graph_builder.add_node("verify_rollback", verify_rollback)
    graph_builder.add_node("build_rollback_verification_event", build_rollback_verification_event)
    graph_builder.add_node("persist_lifecycle_event_rollback_verification", persist_lifecycle_event)
    # Error handling
    graph_builder.add_node("send_error_notification", send_error_notification)

    # Start
    graph_builder.add_edge(START, "parse_raw_incident_text")

    graph_builder.add_conditional_edges(
        "parse_raw_incident_text",
        parse_raw_incident_text_router,
        {
            "validate_input": "validate_input",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "validate_input",
        validate_input_router,
        {
            "retrieve_documents": "retrieve_documents",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "retrieve_documents",
        retrive_document_router,
        {
            "validate_context": "validate_context",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_edge("validate_context", "retrieval_policy_decision")

    graph_builder.add_conditional_edges(
        "retrieval_policy_decision",
        retrieval_policy_router,
        {
            "invoke_llm": "invoke_llm",
            "query_rewrite_and_retry": "query_rewrite_and_retry",
            "build_investigation_request": "build_investigation_request",
        },
    )

    graph_builder.add_conditional_edges(
        "query_rewrite_and_retry",
        query_rewrite_and_retry_router,
        {
            "validate_context": "validate_context",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "invoke_llm",
        invoke_llm_router,
        {
            "check_grounding": "check_grounding",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "check_grounding",
        grounding_check_router,
        {
            "grounding_policy_decision": "grounding_policy_decision",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_edge("grounding_policy_decision", "build_decision")
    graph_builder.add_edge("build_decision", "evaluate_action_policy")

    graph_builder.add_conditional_edges(
        "evaluate_action_policy",
        action_policy_router,
        {
            "pre_execution_guard": "pre_execution_guard",
            "build_proposal_output": "build_proposal_output",
            "build_approval_request": "build_approval_request",
            "build_investigation_request": "build_investigation_request",
        },
    )

    graph_builder.add_edge("build_proposal_output", "build_decision_log")
    graph_builder.add_edge("build_approval_request", "build_decision_log")
    graph_builder.add_edge("build_decision_log", "persist_decision_log")

    graph_builder.add_conditional_edges(
        "persist_decision_log",
        decision_log_router,
        {
            "END": END,
            "persist_approval_request": "persist_approval_request",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_approval_request",
        persist_approval_request_router,
        {
            "build_approval_requested_event": "build_approval_requested_event",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_edge(
        "build_approval_requested_event",
        "persist_lifecycle_event_approval_requested",
    )

    graph_builder.add_conditional_edges(
        "persist_lifecycle_event_approval_requested",
        persist_approval_requested_event_router,
        {
            "hitl_approval": "hitl_approval",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "hitl_approval",
        hitl_approval_router,
        {
            "build_approval_response_event": "build_approval_response_event",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "build_approval_response_event",
        build_approval_response_event_router,
        {
            "persist_lifecycle_event_approval_response": "persist_lifecycle_event_approval_response",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_lifecycle_event_approval_response",
        persist_approval_response_event_router,
        {
            "pre_execution_guard": "pre_execution_guard",
            "build_investigation_request": "build_investigation_request",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "pre_execution_guard",
        pre_execution_guard_router,
        {
            "prepare_tool_call": "prepare_tool_call",
            "build_investigation_request": "build_investigation_request",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "prepare_tool_call",
        prepare_tool_call_router,
        {
            "build_tool_execution_log_start": "build_tool_execution_log_start",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "build_tool_execution_log_start",
        build_tool_execution_log_start_router,
        {
            "persist_tool_execution_log_start": "persist_tool_execution_log_start",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_tool_execution_log_start",
        persist_tool_execution_log_start_router,
        {
            "build_tool_execution_event": "build_tool_execution_event",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "build_tool_execution_event",
        build_tool_execution_event_router,
        {
            "persist_lifecycle_event_tool_execution": "persist_lifecycle_event_tool_execution",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_lifecycle_event_tool_execution",
        persist_lifecycle_event_tool_execution_router,
        {
            "execute_tool": "execute_tool",
            "verify_tool_output": "verify_tool_output",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "execute_tool",
        execute_tool_router,
        {
            "tool_retry_gate": "tool_retry_gate",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "tool_retry_gate",
        tool_retry_gate_router,
        {
            "build_tool_execution_log_finalize": "build_tool_execution_log_finalize",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "build_tool_execution_log_finalize",
        build_tool_execution_log_finalize_router,
        {
            "persist_tool_execution_log_finalize": "persist_tool_execution_log_finalize",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_tool_execution_log_finalize",
        persist_tool_execution_log_finalize_router,
        {
            "build_tool_execution_event": "build_tool_execution_event",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "verify_tool_output",
        verify_tool_output_router,
        {
            "build_tool_output_verification_event": "build_tool_output_verification_event",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "build_tool_output_verification_event",
        build_tool_output_verification_event_router,
        {
            "persist_lifecycle_event_tool_output_verification": "persist_lifecycle_event_tool_output_verification",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_lifecycle_event_tool_output_verification",
        persist_tool_output_verification_event_router,
        {
            "validate_action_result": "validate_action_result",
            "verify_rollback": "verify_rollback",
            "build_investigation_request": "build_investigation_request",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "validate_action_result",
        validate_action_result_router,
        {
            "build_action_validation_event": "build_action_validation_event",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "build_action_validation_event",
        build_action_validation_event_router,
        {
            "persist_lifecycle_event_action_validation": "persist_lifecycle_event_action_validation",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_lifecycle_event_action_validation",
        persist_action_validation_event_router,
        {
            "END": END,
            "rollback_or_investigation": "rollback_or_investigation",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "verify_rollback",
        verify_rollback_router,
        {
            "build_rollback_verification_event": "build_rollback_verification_event",
            "send_error_notification": "send_error_notification",
        },
    )
    
    graph_builder.add_conditional_edges(
        "rollback_or_investigation",
        rollback_or_investigation_router,
        {
            "prepare_rollback_tool_call": "prepare_rollback_tool_call",
            "build_investigation_request": "build_investigation_request",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "prepare_rollback_tool_call",
        prepare_rollback_tool_call_router,
        {
            "build_tool_execution_log_start": "build_tool_execution_log_start",
            "send_error_notification": "send_error_notification",
        },
    )

    # (Obsolete rollback execution event nodes removed)

    graph_builder.add_conditional_edges(
        "build_rollback_verification_event",
        build_rollback_verification_event_router,
        {
            "persist_lifecycle_event_rollback_verification": "persist_lifecycle_event_rollback_verification",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_conditional_edges(
        "persist_lifecycle_event_rollback_verification",
        persist_rollback_verification_event_router,
        {
            "END": END,
            "build_investigation_request": "build_investigation_request",
            "send_error_notification": "send_error_notification",
        },
    )

    graph_builder.add_edge("build_investigation_request", END)
    graph_builder.add_edge("send_error_notification", END)

    return graph_builder.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    # Visualize Graph
    from pathlib import Path
    from langgraph.checkpoint.memory import InMemorySaver

    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    mermaid = graph.get_graph(xray=False).draw_mermaid()
    Path("graph.mmd").write_text(mermaid)
    print("Wrote graph.mmd")
    # png = graph.get_graph(xray=False).draw_mermaid_png()
    # Path("graph.png").write_bytes(png)
    # print("Wrote graph.png")


