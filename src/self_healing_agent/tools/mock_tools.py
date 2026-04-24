from __future__ import annotations

from typing import Any



def _base_response(
    tool_name: str,
    args: dict[str, Any],
    ok: bool,
    message: str,
    *,
    error: str = "",
    error_code: str = "",
    transient: bool = False,
    side_effect_committed: bool = False,
) -> dict[str, Any]:
    meta = args.get("_meta", {})
    return {
        "ok": ok,
        "raw": {
            "execution_mode": "MOCK",
            "tool_name": tool_name,
            "message": message,
            "meta": {
                "trace_id": meta.get("trace_id"),
                "incident_id": meta.get("incident_id"),
                "decision_id": meta.get("decision_id"),
                "tool_step": meta.get("tool_step"),
                "attempt": meta.get("attempt"),
            },
        },
        "error": error,
        "error_code": error_code,
        "transient": transient,
        "side_effect_committed": side_effect_committed,
    }


def _simulated_response(tool_name: str, args: dict[str, Any], outcome: str) -> dict[str, Any]:
    normalized = str(outcome).strip().upper()

    if normalized == "TRANSIENT_TIMEOUT":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=False,
            message=f"Transient failure simulated for {tool_name}.",
            error="Transient failure simulated.",
            error_code="TRANSIENT_TIMEOUT",
            transient=True,
            side_effect_committed=False,
        )

    if normalized == "FATAL_POLICY_VIOLATION":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=False,
            message=f"Fatal failure simulated for {tool_name}.",
            error="Fatal policy violation simulated.",
            error_code="FATAL_POLICY_VIOLATION",
            transient=False,
            side_effect_committed=False,
        )

    if normalized == "PARTIAL_SIDE_EFFECT":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=False,
            message=f"Partial side effect simulated for {tool_name}.",
            error="Tool failed after partial side effect.",
            error_code="PARTIAL_SIDE_EFFECT",
            transient=False,
            side_effect_committed=True,
        )

    if normalized == "SUCCESS":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=True,
            message=f"Success simulated for {tool_name}.",
            error="",
            error_code="",
            transient=False,
            side_effect_committed=True,
        )

    return _base_response(
        tool_name=tool_name,
        args=args,
        ok=False,
        message=f"Unknown simulated outcome for {tool_name}: {normalized}.",
        error=f"Unknown simulated outcome: {normalized}",
        error_code="UNKNOWN_SIMULATED_OUTCOME",
        transient=False,
        side_effect_committed=False,
    )



def mock_tool_execute(tool_call: dict[str, Any]) -> dict[str, Any]:
    """
    Dummy tool execution layer.

    Simulates execution of a real tool based on tool_call.
    This is where real integrations (K8s, DB, etc.) will be plugged in later.

    Contract:
    - Always returns normalized ToolResult fields.
    - `error_code` and `transient` are explicit.
    - `side_effect_committed` indicates whether a side effect may already have happened.
    """
    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).strip().upper()
    args = tool_call.get("args", {}) or {}

    # Preferred test hook: one explicit simulated outcome in args.
    simulated_outcome = args.get("simulate_outcome")
    if simulated_outcome:
        return _simulated_response(tool_name=tool_name, args=args, outcome=simulated_outcome)

    # Backward-compatible boolean flags for older call sites/tests.
    if args.get("simulate_transient_error"):
        return _simulated_response(tool_name=tool_name, args=args, outcome="TRANSIENT_TIMEOUT")

    if args.get("simulate_fatal_error"):
        return _simulated_response(tool_name=tool_name, args=args, outcome="FATAL_POLICY_VIOLATION")

    if args.get("simulate_partial_side_effect"):
        return _simulated_response(tool_name=tool_name, args=args, outcome="PARTIAL_SIDE_EFFECT")

    if tool_name in {"RESTART_SERVICE", "RESTART_PREVIOUS_INSTANCE"}:
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=True,
            message=f"Restart simulated for hosts={args.get('hosts')} instances={args.get('instances')}",
            error="",
            error_code="",
            transient=False,
            side_effect_committed=True,
        )

    if tool_name == "CLEAR_CACHE":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=True,
            message="Cache clear simulated successfully.",
            error="",
            error_code="",
            transient=False,
            side_effect_committed=True,
        )

    return _base_response(
        tool_name=tool_name,
        args=args,
        ok=True,
        message=f"Generic mock execution completed for {tool_name}.",
        error="",
        error_code="",
        transient=False,
        side_effect_committed=True,
    )
