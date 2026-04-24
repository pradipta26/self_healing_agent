from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from self_healing_agent.agent.state import AgentState
from self_healing_agent.agent.nodes.helpers.execution_policy_fingerprint import build_execution_policy_fingerprint
from self_healing_agent.clients.hawkeye_client import (
    get_incident_runtime_status,
    claim_incident_if_open,
)
from self_healing_agent.tools.preconditions import check_tool_preconditions


APPROVAL_TTL_SECONDS = int(os.environ.get('HITL_APPROVAL_TTL_SECONDS') or 1800)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


# def _build_execution_policy_fingerprint(state: AgentState) -> dict[str, Any]:
#     """
#     Build execution control-plane fingerprint.

#     This captures approval-time execution assumptions that must still hold
#     before we allow action execution.
#     """
#     system_readiness = state.get("system_readiness", {})
#     action_policy = state.get("action_policy_decision", {})

#     return {
#         "kill_switch_state": system_readiness.get("kill_switch_state"),
#         "autonomy_mode": system_readiness.get("autonomy_mode"),
#         "effective_autonomy_level": action_policy.get("effective_autonomy_level"),
#         "execution_mode": action_policy.get("execution_mode"),
#     }


def _is_approval_fresh(approval_response: dict[str, Any]) -> tuple[bool, str]:
    approved_at = _parse_iso(approval_response.get("timestamp_utc"))
    if approved_at is None:
        return False, "APPROVAL_TIMESTAMP_MISSING"

    age_seconds = (datetime.now(timezone.utc) - approved_at).total_seconds()
    if age_seconds > APPROVAL_TTL_SECONDS:
        return False, "APPROVAL_EXPIRED"

    return True, "APPROVAL_FRESH"


def _has_system_state_changed(
    previous_fingerprint: dict[str, Any],
    current_fingerprint: dict[str, Any],
) -> tuple[bool, str]:
    if previous_fingerprint != current_fingerprint:
        return True, "SYSTEM_STATE_CHANGED"
    return False, "SYSTEM_STATE_STABLE"


def pre_execution_guard(state: AgentState) -> dict[str, Any]:
    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    approval_response = state.get("approval_response", {})
    incident_id = state.get("incident_id", "")

    if str(approval_response.get("status", "")).strip().upper() != "APPROVED":
        trace.append("pre_execution_guard:not_approved")
        return {
            "pre_execution_guard": {
                "ok": False,
                "reason": "APPROVAL_NOT_APPROVED",
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": "Pre-execution guard called without APPROVED approval response.",
        }

    # 1. Incident still active? / 3. Another actor already owns remediation?
    incident_runtime = get_incident_runtime_status(incident_id)
    incident_status = str(incident_runtime.get("status", "UNKNOWN")).strip().upper()
    owner = incident_runtime.get("owner")

    if incident_status == "CLOSED":
        trace.append("pre_execution_guard:incident_closed")
        return {
            "pre_execution_guard": {
                "ok": False,
                "reason": "INCIDENT_NOT_OPEN",
                "incident_status": incident_status,
                "owner": owner,
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }
    actor_id = state.get("thread_id", "self_healing_agent")
    claim_owner = owner

    if incident_status == "PROCESSING":
        if owner != actor_id:
            trace.append("pre_execution_guard:incident_processing_other_owner")
            return {
                "pre_execution_guard": {
                    "ok": False,
                    "reason": "INCIDENT_ALREADY_PROCESSING",
                    "incident_status": incident_status,
                    "owner": owner,
                },
                "warnings": warnings,
                "trace": trace,
                "error_flag": False,
                "error_message": None,
            }

        trace.append("pre_execution_guard:incident_already_claimed_by_same_actor")

    elif incident_status == "OPEN":
        claim_result = claim_incident_if_open(
            incident_id=incident_id,
            actor_id=actor_id,
        )
        if not claim_result.get("claimed", False):
            trace.append("pre_execution_guard:claim_failed")
            return {
                "pre_execution_guard": {
                    "ok": False,
                    "reason": "INCIDENT_ALREADY_OWNED",
                    "incident_status": claim_result.get("status", incident_status),
                    "owner": claim_result.get("owner"),
                },
                "warnings": warnings,
                "trace": trace,
                "error_flag": False,
                "error_message": None,
            }

        claim_owner = claim_result.get("owner")
        trace.append("pre_execution_guard:incident_claimed")

    else:
        trace.append("pre_execution_guard:unexpected_incident_status")
        return {
            "pre_execution_guard": {
                "ok": False,
                "reason": "INCIDENT_STATUS_UNKNOWN",
                "incident_status": incident_status,
                "owner": owner,
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    # 5. Approval still fresh?
    approval_fresh, approval_reason = _is_approval_fresh(approval_response)
    if not approval_fresh:
        trace.append("pre_execution_guard:approval_not_fresh")
        return {
            "pre_execution_guard": {
                "ok": False,
                "reason": approval_reason,
                "incident_status": incident_status,
                "owner": claim_owner,
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    # 2. Action still needed?
    precondition_result = check_tool_preconditions(state)
    if not precondition_result.get("ok", False):
        trace.append("pre_execution_guard:action_not_needed")
        return {
            "pre_execution_guard": {
                "ok": False,
                "reason": precondition_result.get("reason", "ACTION_NO_LONGER_NEEDED"),
                "incident_status": incident_status,
                "owner": claim_owner,
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    # 4. System state changed?
    # V1 execution-policy drift check:
    # this compares approval-time execution control assumptions with current state.
    # (kill-switch, autonomy mode, autonomy level, execution mode)
    # Future: extend with runtime topology/state drift signals.
    original_fingerprint = state.get("initial_execution_policy_fingerprint", {})
    current_fingerprint = build_execution_policy_fingerprint(state)

    if not original_fingerprint:
        trace.append("pre_execution_guard:missing_original_fingerprint")

    state_changed, state_change_reason = _has_system_state_changed(
        original_fingerprint or current_fingerprint,
        current_fingerprint,
    )
    if state_changed:
        trace.append("pre_execution_guard:system_state_changed")
        return {
            "pre_execution_guard": {
                "ok": False,
                "reason": state_change_reason,
                "incident_status": incident_status,
                "owner": claim_owner,
                "current_fingerprint": current_fingerprint,
            },
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    trace.append("pre_execution_guard:ok")
    return {
        "pre_execution_guard": {
            "ok": True,
            "reason": "READY_TO_EXECUTE",
            "incident_status": incident_status,
            "owner": claim_owner,
            "approval_fresh": True,
            "action_needed": True,
            "state_changed": False,
            "current_fingerprint": current_fingerprint,
        },
        "warnings": warnings,
        "trace": trace,
        "error_flag": False,
        "error_message": None,
    }
