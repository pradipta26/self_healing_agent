from self_healing_agent.agent.state import AgentState


def parse_raw_incident_text_router(state: AgentState):
    if not state.get('error_flag', True):
        return 'validate_input'
    return 'send_error_notification'


def validate_input_router(state: AgentState):
    if not state.get('error_flag', True):
        return 'retrieve_documents'
    return 'send_error_notification'


def retrive_document_router(state: AgentState):
    if not state.get('error_flag', True):
        return 'validate_context'
    return 'send_error_notification'


def context_validation_policy_router(state: AgentState):
    route = state.get('retrieval_policy_route', '')
    if route == 'PROCEED':
        return 'execute_llm_call'
    elif route == 'RETRY':
        return 'query_rewrite_and_retry'
    
    return 'hilt_investigation'

def query_rewrite_and_retry_router(state: AgentState):
    if not state.get('error_flag', True):
        return 'validate_context'
    return 'send_error_notification'
