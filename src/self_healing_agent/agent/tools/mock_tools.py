from __future__ import annotations

from typing import Any


def _base_response(tool_name: str, args: dict[str, Any], ok: bool, message: str, error: str = "") -> dict[str, Any]:
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
    }


def mock_tool_execute(tool_call: dict[str, Any]) -> dict[str, Any]:
    """
    Dummy tool execution layer.

    Simulates execution of a real tool based on tool_call.
    This is where real integrations (K8s, DB, etc.) will be plugged in later.
    """
    tool_name = str(tool_call.get("tool_name", "UNKNOWN")).upper()
    args = tool_call.get("args", {})

    if args.get("simulate_transient_error"):
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=False,
            message=f"Transient failure simulated for {tool_name}.",
            error="TRANSIENT_TIMEOUT",
        )

    if args.get("simulate_fatal_error"):
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=False,
            message=f"Fatal failure simulated for {tool_name}.",
            error="FATAL_POLICY_VIOLATION",
        )

    if tool_name == "RESTART":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=True,
            message=f"Restart simulated for hosts={args.get('hosts')} instances={args.get('instances')}",
        )

    if tool_name == "FAILOVER":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=True,
            message="Failover simulated successfully.",
        )

    if tool_name == "CLEANUP":
        return _base_response(
            tool_name=tool_name,
            args=args,
            ok=True,
            message="Cleanup simulated successfully.",
        )

    return _base_response(
        tool_name=tool_name,
        args=args,
        ok=True,
        message=f"Generic mock execution completed for {tool_name}.",
    )
