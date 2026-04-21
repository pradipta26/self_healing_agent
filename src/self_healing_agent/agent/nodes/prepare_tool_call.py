from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.tools.registry import AVAILABLE_TOOL_FAMILIES
from self_healing_agent.agent.tools.resolver import resolve_precondition

def prepare_tool_call(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    structured_input = state.get("structured_input", {})
    action_policy = state.get("action_policy_decision", {})
    decision = state.get("decision", {})
    approval_response = state.get("approval_response", {})
    model_output = state.get("model_output", {})

    if str(approval_response.get("status", "")).strip().upper() != "APPROVED":
        trace.append("prepare_tool_call:not_approved")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Tool preparation attempted without APPROVED approval response.",
        }

    action_families = action_policy.get("action_families", [])
    if not action_families:
        trace.append("prepare_tool_call:missing_action_family")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "No action families available for tool preparation.",
        }

    decision_id = state.get("decision_id") or decision.get("decision_id")
    if not decision_id:
        trace.append("prepare_tool_call:missing_decision_id")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "decision_id is missing for tool preparation.",
        }

    trace_id = state.get("trace_id", "")
    incident_id = state.get("incident_id", "")
    tool_step = int(state.get("tool_step", 0)) + 1
    attempt = int(state.get("attempt", 0)) or 1

    primary_family = str(action_families[0]).upper()

    tool_definition = AVAILABLE_TOOL_FAMILIES.get(primary_family, {}) or {}
    if not tool_definition:
        trace.append("prepare_tool_call:tool_definition_missing")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Tool definition is missing for action family {primary_family}.",
        }

    tool_name = str(tool_definition.get("tool_name", "")).strip()
    if not tool_name:
        trace.append("prepare_tool_call:tool_name_missing")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"tool_name is missing in registry for action family {primary_family}.",
        }
    
    # Build rollback plan from structured registry metadata
    tool_meta = tool_definition
    rollback_meta = tool_meta.get("rollback")

    if rollback_meta:
        rollback_tool_name = rollback_meta.get("tool_name")
        args_template = rollback_meta.get("args_template", {}) or {}

        rollback_args = {
            key: value.format(
                service=structured_input.get("service_domain", ""),
                env=structured_input.get("env", ""),
            ) if isinstance(value, str) else value
            for key, value in args_template.items()
        }

        rollback_action = {
            "tool_name": rollback_tool_name,
            "args": rollback_args,
            "idempotency_key": f"{decision_id}:rollback:{primary_family}",
        }

        rollback_plan = {
            "status": "PLANNED",
            "reason": f"Rollback available via {rollback_tool_name}",
            "actions": [rollback_action],
            "notes": [],
            "artifacts": {},
        }
    else:
        rollback_plan = {
            "status": "SKIPPED",
            "reason": "No rollback capability defined for this tool.",
            "actions": [],
            "notes": [],
            "artifacts": {},
        }
    meta = {
        "trace_id": trace_id,
        "incident_id": incident_id,
        "decision_id": decision_id,
        "tool_step": tool_step,
        "attempt": attempt,
    }

    precondition_name = tool_definition.get("precondition")
    try:
        precondition_fn = resolve_precondition(precondition_name)
    except ValueError as exc:
        trace.append("prepare_tool_call:precondition_resolution_failed")
        return {
            "tool_definition": tool_definition,
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": str(exc),
        }

    if precondition_fn is not None:
        tool_precondition_result = precondition_fn(state)
    else:
        tool_precondition_result = {
            "ok": True,
            "reason": "NO_PRECONDITION_CONFIGURED",
            "facts": {},
        }

    if not tool_precondition_result.get("ok", False):
        trace.append("prepare_tool_call:precondition_failed")
        return {
            "tool_definition": tool_definition,
            "tool_precondition_result": tool_precondition_result,
            "rollback_plan": rollback_plan,
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Tool precondition failed: {tool_precondition_result.get('reason', 'UNKNOWN')}",
        }

    tool_args = {
        "service": structured_input.get("service_domain"),
        "env": structured_input.get("env"),
        "datacenter": structured_input.get("datacenter"),
        "app_name": structured_input.get("app_name"),
        "hosts": structured_input.get("hosts", []) or [],
        "instances": structured_input.get("instances", []) or [],
        "metric_names": structured_input.get("metric_names", []) or [],
        "reason": structured_input.get("reason", ""),
        "proposed_actions": model_output.get("remediation", []) or [],
        "_meta": meta,
    }

    idempotency_key = (
        f"{decision_id}:"
        f"{incident_id or 'unknown_incident'}:"
        f"{primary_family}:"
        f"{structured_input.get('service_domain', 'unknown_service')}:"
        f"{structured_input.get('env', 'unknown_env')}"
    )

    tool_call = {
        "tool_name": tool_name,
        "args": tool_args,
        "idempotency_key": idempotency_key,
    }

    trace.append(f"prepare_tool_call:{tool_name}:ok")

    return {
        "tool_step": tool_step,
        "attempt": attempt,
        "tool_definition": tool_definition,
        "tool_precondition_result": tool_precondition_result,
        "tool_call": tool_call,
        "rollback_plan": rollback_plan,
        "execution_phase": "FORWARD", # For original tool call cycle, "BACKWARD" for rollback cycle
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }