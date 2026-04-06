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
from self_healing_agent.agent.nodes.build_decision_log import build_decision_log
from self_healing_agent.agent.nodes.persist_decision_log import persist_decision_log
from self_healing_agent.agent.nodes.error_notification import send_error_notification
from self_healing_agent.agent.router.router_functions import (
    parse_raw_incident_text_router,
    validate_input_router,
    retrive_document_router,
    query_rewrite_and_retry_router,
    retrieval_policy_router,
    invoke_llm_router,
    grounding_check_router,
    # build_decision_router,
    action_policy_router,
)


def build_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("parse_raw_incident_text", parse_raw_incident_details)
    graph_builder.add_node("send_error_notification", send_error_notification)
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
    graph_builder.add_node("build_decision_log", build_decision_log)
    graph_builder.add_node("persist_decision_log", persist_decision_log)
    
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
            "build_decision": "build_decision",
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

    # graph_builder.add_conditional_edges(
    #     "build_decision",
    #     build_decision_router,
    #     {
    #         "build_proposal_output": "build_proposal_output",
    #         "build_investigation_request": "build_investigation_request",
    #     },
    # )
    graph_builder.add_conditional_edges(
        "evaluate_action_policy",
        action_policy_router,
        {
            "build_proposal_output": "build_proposal_output",
            "build_investigation_request": "build_investigation_request",
        },
    )

    graph_builder.add_edge("build_proposal_output", "build_decision_log")
    graph_builder.add_edge("build_investigation_request", "build_decision_log")
    graph_builder.add_edge("build_decision_log", "persist_decision_log")
    graph_builder.add_edge("persist_decision_log", END)
    graph_builder.add_edge("send_error_notification", END)

    return graph_builder.compile()