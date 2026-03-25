from langgraph.graph import END, START, StateGraph

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.nodes.parse_raw_incident_text import parse_raw_incident_details
from self_healing_agent.agent.nodes.validate_input import validate_input
from self_healing_agent.agent.nodes.retrieve_context import retrieve_documents
from self_healing_agent.agent.nodes.context_validator import validate_context
from self_healing_agent.agent.nodes.rewrite_and_retry import query_rewrite_and_retry
from self_healing_agent.agent.nodes.retrieval_policy import retrieval_policy_decision
from self_healing_agent.agent.nodes.error_notification import send_error_notification
from self_healing_agent.agent.router.router_functions import (
    parse_raw_incident_text_router, 
    validate_input_router, 
    retrive_document_router,
    query_rewrite_and_retry_router,
    context_validation_policy_router,
)



def build_graph():
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node('parse_raw_incident_text', parse_raw_incident_details)
    graph_builder.add_node('send_error_notification', send_error_notification)
    graph_builder.add_node('validate_input', validate_input)
    graph_builder.add_node("retrieve_documents", retrieve_documents)
    graph_builder.add_node("validate_context", validate_context)
    graph_builder.add_node("query_rewrite_and_retry", query_rewrite_and_retry)
    graph_builder.add_node("retrieval_policy_decision", retrieval_policy_decision)

    graph_builder.add_edge(START, "parse_raw_incident_text")
    graph_builder.add_conditional_edges(
        "parse_raw_incident_text",
        parse_raw_incident_text_router,
        {'validate_input': 'validate_input', 'send_error_notification': "send_error_notification"},
    )
    graph_builder.add_conditional_edges(
        "validate_input",
        validate_input_router,
        {'retrieve_documents': 'retrieve_documents', 'send_error_notification': "send_error_notification"},
    )
    graph_builder.add_conditional_edges(
        "retrieve_documents",
        retrive_document_router,
        {'validate_context': 'validate_context', 'send_error_notification': "send_error_notification"},
    )
    graph_builder.add_conditional_edges(
        "query_rewrite_and_retry",
        query_rewrite_and_retry_router,
        {
            "validate_context": "validate_context",
            "send_error_notification": "send_error_notification",
        },
    )
    graph_builder.add_edge("validate_context", "retrieval_policy_decision")
    
    graph_builder.add_conditional_edges(
        "retrieval_policy_decision",
        context_validation_policy_router,
        {'execute_llm_call':END, 'query_rewrite_and_retry': 'query_rewrite_and_retry', 'hitl_investigation':END},
    )

    graph_builder.add_edge("send_error_notification", END)

    return graph_builder.compile()

