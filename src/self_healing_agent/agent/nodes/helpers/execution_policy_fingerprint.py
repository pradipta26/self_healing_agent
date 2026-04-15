from self_healing_agent.agent.state import AgentState, ExecutionPolicyFingerprint


def build_execution_policy_fingerprint(state: AgentState) -> ExecutionPolicyFingerprint:
    """
    Build execution control-plane fingerprint.

    This captures the execution-policy assumptions that must still hold
    before action execution is allowed.
    """
    action_policy = state.get("action_policy_decision", {})

    kill_switch_state = state.get("kill_switch_state")
    autonomy_mode = state.get("autonomy_mode")
    effective_autonomy_level = action_policy.get("effective_autonomy_level")
    execution_mode = action_policy.get("execution_mode")

    missing_fields: list[str] = []
    if kill_switch_state is None:
        missing_fields.append("kill_switch_state")
    if autonomy_mode is None:
        missing_fields.append("autonomy_mode")
    if effective_autonomy_level is None:
        missing_fields.append("action_policy_decision.effective_autonomy_level")
    if execution_mode is None:
        missing_fields.append("action_policy_decision.execution_mode")

    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(
            f"Missing execution-policy fingerprint fields: {missing}"
        )

    return {
        "kill_switch_state": kill_switch_state,
        "autonomy_mode": autonomy_mode,
        "effective_autonomy_level": effective_autonomy_level,
        "execution_mode": execution_mode,
    }