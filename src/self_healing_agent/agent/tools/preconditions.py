from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState, ToolPreconditionResult



def _build_result(ok: bool, reason: str, facts: dict[str, Any] | None = None) -> ToolPreconditionResult:
    return {
        "ok": ok,
        "reason": reason,
        "facts": facts or {},
    }



def check_restart_service_preconditions(state: AgentState) -> ToolPreconditionResult:
    """
    Dummy precondition contract for forward restart execution.

    Real implementation can later check things like:
    - target still unhealthy
    - restart has not already happened recently
    - target instance/pod still exists
    """
    structured_input = state.get("structured_input", {}) or {}
    hosts = structured_input.get("hosts", []) or []
    instances = structured_input.get("instances", []) or []

    return _build_result(
        ok=True,
        reason="RESTART_PRECONDITION_PASSED",
        facts={
            "host_count": len(hosts),
            "instance_count": len(instances),
        },
    )



def check_restart_rollback_preconditions(state: AgentState) -> ToolPreconditionResult:
    """
    Dummy precondition contract for restart rollback execution.

    Real implementation can later check things like:
    - previous instance still exists
    - rollback target is reachable
    - rollback action is still safe to execute
    """
    rollback_plan = state.get("rollback_plan", {}) or {}
    rollback_actions = rollback_plan.get("actions", []) or []

    return _build_result(
        ok=bool(rollback_actions),
        reason="ROLLBACK_PRECONDITION_PASSED" if rollback_actions else "ROLLBACK_ACTION_MISSING",
        facts={
            "rollback_action_count": len(rollback_actions),
        },
    )


def check_clear_cache_preconditions(state: AgentState) -> ToolPreconditionResult:
    """
    Dummy precondition contract for cache-clearing execution.

    Real implementation can later check things like:
    - cache pressure still exists
    - target cache path/keyspace still exists
    - cleanup is still required
    """
    structured_input = state.get("structured_input", {}) or {}
    service = structured_input.get("service_domain", "")
    env = structured_input.get("env", "")

    return _build_result(
        ok=True,
        reason="CLEAR_CACHE_PRECONDITION_PASSED",
        facts={
            "service": service,
            "env": env,
        },
    )


def check_tool_preconditions(state: AgentState) -> ToolPreconditionResult:
    """
    Backward-compatible generic precondition entry point.

    This remains as a safe fallback for older call sites, but Step 3.4 should
    prefer registry-driven named precondition resolution through resolver.py.
    """
    action_policy = state.get("action_policy_decision", {}) or {}
    action_families = action_policy.get("action_families", []) or []

    if not action_families:
        return _build_result(
            ok=False,
            reason="ACTION_FAMILY_MISSING",
            facts={},
        )

    primary_action = str(action_families[0]).upper()

    if primary_action == "RESTART_SERVICE":
        return check_restart_service_preconditions(state)

    if primary_action == "CLEAR_CACHE":
        return check_clear_cache_preconditions(state)

    return _build_result(
        ok=True,
        reason="PRECONDITION_PASSED",
        facts={"action_family": primary_action},
    )