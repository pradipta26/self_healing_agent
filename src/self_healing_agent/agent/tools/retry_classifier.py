from __future__ import annotations

from typing import Any


RETRYABLE_ERROR_CODES = {
    "TRANSIENT_TIMEOUT",
    "TRANSIENT_NETWORK",
    "TRANSIENT_RATE_LIMIT",
    "TRANSIENT_DEPENDENCY_UNAVAILABLE",
}

NON_RETRYABLE_ERROR_CODES = {
    "FATAL_POLICY_VIOLATION",
    "FATAL_INVALID_INPUT",
    "FATAL_UNSUPPORTED_ACTION",
    "FATAL_TARGET_NOT_FOUND",
    "TOOL_OUTPUT_MALFORMED",
    "PARTIAL_SIDE_EFFECT",
    "TOOL_EXECUTION_EXCEPTION",
    "UNKNOWN_SIMULATED_OUTCOME",
}


def classify_tool_failure(tool_result: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministically classify tool failure using structured fields first,
    and only fall back to error text when necessary.

    Returns:
        {
            "failure_type": "TRANSIENT" | "PERMANENT" | "UNKNOWN" | "NONE",
            "retryable": bool,
            "reason_code": str,
            "side_effect_committed": bool,
        }
    """
    if tool_result.get("ok", False):
        return {
            "failure_type": "NONE",
            "retryable": False,
            "reason_code": "",
            "side_effect_committed": bool(tool_result.get("side_effect_committed", False)),
        }

    error_code = str(tool_result.get("error_code", "")).strip().upper()
    transient = bool(tool_result.get("transient", False))
    side_effect_committed = bool(tool_result.get("side_effect_committed", False))
    error_text = str(tool_result.get("error", "")).strip().upper()

    if side_effect_committed:
        return {
            "failure_type": "PERMANENT",
            "retryable": False,
            "reason_code": error_code or "PARTIAL_SIDE_EFFECT",
            "side_effect_committed": True,
        }

    if error_code in RETRYABLE_ERROR_CODES:
        return {
            "failure_type": "TRANSIENT",
            "retryable": True,
            "reason_code": error_code,
            "side_effect_committed": False,
        }

    if error_code in NON_RETRYABLE_ERROR_CODES:
        return {
            "failure_type": "PERMANENT",
            "retryable": False,
            "reason_code": error_code,
            "side_effect_committed": False,
        }

    if transient:
        return {
            "failure_type": "TRANSIENT",
            "retryable": True,
            "reason_code": error_code or "TRANSIENT_TOOL_FAILURE",
            "side_effect_committed": False,
        }

    if any(token in error_text for token in {"TIMEOUT", "RATE LIMIT", "NETWORK", "UNAVAILABLE"}):
        return {
            "failure_type": "TRANSIENT",
            "retryable": True,
            "reason_code": error_code or "TRANSIENT_TOOL_FAILURE",
            "side_effect_committed": False,
        }

    return {
        "failure_type": "UNKNOWN",
        "retryable": False,
        "reason_code": error_code or "TOOL_EXECUTION_FAILED",
        "side_effect_committed": False,
    }