from __future__ import annotations

from typing import Any

from self_healing_agent.agent.tools.registry import AVAILABLE_TOOL_FAMILIES
from self_healing_agent.agent.state import (
    ActionPolicyDecision,
    BlastRadiusLevel,
    HumanRole,
)


_AUTONOMY_RANK = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "L3": 3,
    "L4": 4,
}

_RANK_TO_AUTONOMY = {value: key for key, value in _AUTONOMY_RANK.items()}

_BLAST_RADIUS_RANK = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "UNKNOWN": 99,
}


def _derive_action_families(context_validation: dict[str, Any]) -> list[str]:
    raw_families = context_validation.get("facts", {}).get("action_families", [])
    families = sorted({str(f).upper() for f in raw_families if str(f).upper() != "OTHER"})
    return families or ["UNKNOWN"]


def _derive_blast_radius(structured_input: dict[str, Any]) -> BlastRadiusLevel:
    incident_type = structured_input.get("incident_type")

    if incident_type in {"System Instance", "Host Infrastructure"}:
        return "LOW"
    if incident_type in {"System DC", "Service Instance"}:
        return "MEDIUM"
    if incident_type in {"Service DC"}:
        return "HIGH"

    return "UNKNOWN"


def _more_restrictive_level(level_a: str, level_b: str) -> str:
    rank = min(_AUTONOMY_RANK.get(level_a, 0), _AUTONOMY_RANK.get(level_b, 0))
    return _RANK_TO_AUTONOMY[rank]


def _level_to_execution_mode(level: str) -> str:
    if level == "L0":
        return "BLOCKED"
    if level == "L1":
        return "PROPOSE_ONLY"
    if level == "L2":
        return "APPROVAL_REQUIRED"
    return "AUTO_EXECUTE"


def _autonomy_mode_cap(autonomy_mode: str) -> str:
    if autonomy_mode == "OFF":
        return "L0"
    if autonomy_mode == "SHADOW":
        return "L1"
    if autonomy_mode == "LIVE":
        return "L4"
    return "L0"


def _get_required_human_role_for_block(
    action_policy: dict[str, Any] | None,
    default_role: HumanRole = "INVESTIGATOR",
) -> HumanRole:
    if not action_policy:
        return default_role

    role = action_policy.get("required_human_role_if_blocked", default_role)
    if role in {"NONE", "INVESTIGATOR", "APPROVER", "SME_REVIEW", "INCIDENT_COMMANDER"}:
        return role
    return default_role


def _get_env_execution_mode(action_policy: dict[str, Any], env: str) -> str:
    mode = (
        action_policy.get("execution_mode_by_env", {}).get(env)
        or action_policy.get("execution_mode_by_env", {}).get("default")
        or "PROPOSE_ONLY"
    )
    return mode


def _execution_mode_to_level(execution_mode: str) -> str:
    if execution_mode == "BLOCKED":
        return "L0"
    if execution_mode == "PROPOSE_ONLY":
        return "L1"
    if execution_mode == "APPROVAL_REQUIRED":
        return "L2"
    return "L3"


def _proposal_only_result(
    *,
    blast_radius: BlastRadiusLevel,
    action_families: list[str],
    reasons: list[str],
) -> ActionPolicyDecision:
    return {
        "allowed": True,
        "effective_autonomy_level": "L1",
        "execution_mode": "PROPOSE_ONLY",
        "required_human_role": "NONE",
        "blast_radius": blast_radius,
        "action_families": action_families,
        "reasons": reasons,
    }


def _blast_radius_allowed(derived_radius: str, max_radius: str) -> bool:
    derived_rank = _BLAST_RADIUS_RANK.get(derived_radius, 99)
    max_rank = _BLAST_RADIUS_RANK.get(max_radius, 99)
    return derived_rank <= max_rank


def resolve_action_policy(
    *,
    structured_input: dict[str, Any],
    decision: dict[str, Any],
    context_validation: dict[str, Any],
    grounding_check: dict[str, Any],
    autonomy_mode: str,
    actions_policy: dict[str, Any],
    services_policy: dict[str, Any],
) -> ActionPolicyDecision:
    service_domain = structured_input.get("service_domain", "")
    env = structured_input.get("env", "DEV")

    action_families = [str(f).upper() for f in _derive_action_families(context_validation)]
    blast_radius = _derive_blast_radius(structured_input)

    reasons: list[str] = []
    required_human_role: HumanRole = "NONE"

    # --------------------------------------------------
    # hard gates from current decision quality
    # --------------------------------------------------
    if decision.get("route") != "PROPOSE":
        reasons.append("Decision route is not PROPOSE, so action execution is not eligible.")
        return {
            "allowed": False,
            "effective_autonomy_level": "L0",
            "execution_mode": "BLOCKED",
            "required_human_role": "INVESTIGATOR",
            "blast_radius": blast_radius,
            "action_families": action_families,
            "reasons": reasons,
        }

    if grounding_check.get("verdict") != "GROUNDED":
        reasons.append("Grounding verdict is not GROUNDED.")
        return {
            "allowed": False,
            "effective_autonomy_level": "L0",
            "execution_mode": "BLOCKED",
            "required_human_role": "INVESTIGATOR",
            "blast_radius": blast_radius,
            "action_families": action_families,
            "reasons": reasons,
        }

    if context_validation.get("validity") != "VALID":
        reasons.append("Context validity is not VALID.")
        return {
            "allowed": False,
            "effective_autonomy_level": "L0",
            "execution_mode": "BLOCKED",
            "required_human_role": "INVESTIGATOR",
            "blast_radius": blast_radius,
            "action_families": action_families,
            "reasons": reasons,
        }

    # --------------------------------------------------
    # start with least restrictive runtime cap
    # --------------------------------------------------
    effective_level = _autonomy_mode_cap(autonomy_mode)

    if autonomy_mode == "OFF":
        reasons.append("Autonomy mode OFF blocks action execution.")
    elif autonomy_mode == "SHADOW":
        reasons.append("Autonomy mode SHADOW caps execution to proposal only.")
    elif autonomy_mode == "LIVE":
        reasons.append("Autonomy mode LIVE allows policy-based execution.")

    # --------------------------------------------------
    # apply service-level cap
    # --------------------------------------------------
    default_service_policy = services_policy.get("default_service_policy", {})
    service_policy = services_policy.get("services", {}).get(service_domain, default_service_policy)

    service_max_level = service_policy.get("max_autonomy_level", "L1")
    effective_level = _more_restrictive_level(effective_level, service_max_level)
    reasons.append(f"Service policy caps autonomy at {service_max_level}.")

    blocked_action_families = set(service_policy.get("blocked_action_families", []))
    service_action_overrides = service_policy.get("action_overrides", {})

    # --------------------------------------------------
    # apply action-family policies (most restrictive wins)
    # --------------------------------------------------
    actions_root = actions_policy.get("actions", {})
    resolved_roles: list[HumanRole] = []

    proposal_only_families: list[str] = []

    for family in action_families:
        action_policy = actions_root.get(family) or actions_root.get("UNKNOWN", {})

        if family in blocked_action_families:
            proposal_only_families.append(family)
            reasons.append(
                f"Service policy blocks autonomous execution for action family {family}; downgrading to proposal only."
            )
            continue

        if not action_policy.get("allowed", False):
            reasons.append(f"Action family {family} is not allowed by policy.")
            return {
                "allowed": False,
                "effective_autonomy_level": "L0",
                "execution_mode": "BLOCKED",
                "required_human_role": _get_required_human_role_for_block(action_policy),
                "blast_radius": blast_radius,
                "action_families": action_families,
                "reasons": reasons,
            }
 
        required_grounding = action_policy.get("required_grounding")
        if required_grounding and grounding_check.get("verdict") != required_grounding:
            proposal_only_families.append(family)
            reasons.append(
                f"Action family {family} requires grounding verdict {required_grounding}; downgrading to proposal only."
            )
            continue

        required_context_validity = set(action_policy.get("required_context_validity", []))
        if required_context_validity and context_validation.get("validity") not in required_context_validity:
            proposal_only_families.append(family)
            reasons.append(
                f"Action family {family} requires context validity in {sorted(required_context_validity)}; downgrading to proposal only."
            )
            continue

        action_default_level = action_policy.get("default_autonomy_level", "L1")
        effective_level = _more_restrictive_level(effective_level, action_default_level)
        reasons.append(f"Action family {family} caps autonomy at {action_default_level}.")

        # env execution mode, with service override if available
        env_execution_mode = _get_env_execution_mode(action_policy, env)
        override = service_action_overrides.get(family, {})
        if override:
            env_execution_mode = (
                override.get("execution_mode_by_env", {}).get(env)
                or env_execution_mode
            )

        env_level = _execution_mode_to_level(env_execution_mode)
        effective_level = _more_restrictive_level(effective_level, env_level)
        reasons.append(f"Environment {env} maps action family {family} to {env_execution_mode}.")

        max_blast_radius = action_policy.get("max_blast_radius", "UNKNOWN")
        if not _blast_radius_allowed(blast_radius, max_blast_radius):
            proposal_only_families.append(family)
            reasons.append(
                f"Derived blast radius {blast_radius} exceeds policy max {max_blast_radius} for {family}; downgrading to proposal only."
            )
            continue

        if family not in AVAILABLE_TOOL_FAMILIES:
            proposal_only_families.append(family)
            reasons.append(
                f"Tool not registered for action family {family}; downgrading to proposal only."
            )
            continue

        resolved_roles.append(_get_required_human_role_for_block(action_policy))

    if proposal_only_families:
        effective_level = _more_restrictive_level(effective_level, "L1")

    if effective_level == "L1" and proposal_only_families:
        return _proposal_only_result(
            blast_radius=blast_radius,
            action_families=action_families,
            reasons=reasons,
        )

    # --------------------------------------------------
    # final mode
    # --------------------------------------------------
    execution_mode = _level_to_execution_mode(effective_level)

    if execution_mode in {"BLOCKED", "PROPOSE_ONLY"}:
        if execution_mode == "BLOCKED":
            required_human_role = "INVESTIGATOR"
        else:
            required_human_role = "NONE"
    elif execution_mode == "APPROVAL_REQUIRED":
        required_human_role = "APPROVER"
    else:
        required_human_role = "NONE"

    return {
        "allowed": execution_mode != "BLOCKED",
        "effective_autonomy_level": effective_level,
        "execution_mode": execution_mode,
        "required_human_role": required_human_role,
        "blast_radius": blast_radius,
        "action_families": action_families,
        "reasons": reasons,
    }