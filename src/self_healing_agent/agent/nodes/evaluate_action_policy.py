from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.config.config_loader import load_yaml_config
from self_healing_agent.policy.action_policy_resolver import resolve_action_policy
from self_healing_agent.tools.registry import AVAILABLE_TOOL_FAMILIES

def evaluate_action_policy(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    try:
        actions_policy = load_yaml_config("configs/policies/actions.yaml")
        services_policy = load_yaml_config("configs/policies/services.yaml")

        action_policy_decision = resolve_action_policy(
            structured_input=state.get("structured_input", {}),
            decision=state.get("decision", {}),
            context_validation=state.get("context_validation", {}),
            grounding_check=state.get("grounding_check", {}),
            autonomy_mode=state.get("autonomy_mode", "OFF"),
            actions_policy=actions_policy,
            services_policy=services_policy,
        )

        trace.append("evaluate_action_policy:ok")

        return {
            "action_policy_decision": action_policy_decision,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except Exception as exc:
        warnings.append("ACTION_POLICY_EVALUATION_FAILED")
        trace.append("evaluate_action_policy:error")

        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Action policy evaluation failed: {exc}",
        }
