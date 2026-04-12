
from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState


def check_tool_preconditions(state: AgentState) -> dict[str, Any]:
    """
    Dummy tool precondition layer.

    Purpose:
    --------
    Before executing any action (restart, failover, cleanup, etc.),
    we verify whether the action is still needed.

    This is a placeholder implementation.
    Later this should dispatch to action-family-specific logic.

    Returns:
    --------
    {
        "ok": bool,
        "reason": str
    }
    """

    action_policy = state.get("action_policy_decision", {})
    action_families = action_policy.get("action_families", [])

    # -----------------------------
    # Basic validation
    # -----------------------------
    if not action_families:
        return {
            "ok": False,
            "reason": "ACTION_FAMILY_MISSING",
        }

    primary_action = str(action_families[0]).upper()

    # -----------------------------
    # Dummy logic per action type
    # -----------------------------

    # Example: RESTART action
    if primary_action == "RESTART":
        # In real world:
        # - check JVM health
        # - check pod/container status
        # - check if already restarted recently
        return {
            "ok": True,
            "reason": "TARGET_STILL_UNHEALTHY",
        }

    # Example: FAILOVER action
    if primary_action == "FAILOVER":
        # In real world:
        # - check active region
        # - verify current traffic routing
        return {
            "ok": True,
            "reason": "FAILOVER_REQUIRED",
        }

    # Example: CLEANUP action
    if primary_action == "CLEANUP":
        # In real world:
        # - check disk usage
        # - check temp files existence
        return {
            "ok": True,
            "reason": "CLEANUP_REQUIRED",
        }

    # -----------------------------
    # Default fallback
    # -----------------------------
    return {
        "ok": True,
        "reason": "PRECONDITION_PASSED",
    }