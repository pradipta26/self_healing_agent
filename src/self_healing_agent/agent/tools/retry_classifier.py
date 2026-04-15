from __future__ import annotations

from typing import Any


def classify_tool_failure(tool_result: dict[str, Any]) -> dict[str, Any]:
    error_text = str(tool_result.get("error", "")).strip().upper()

    retryable_map = {
        "TRANSIENT_TIMEOUT": "TOOL_TIMEOUT",
        "TRANSIENT_NETWORK": "TOOL_EXECUTION_FAILED",
        "TRANSIENT_RATE_LIMIT": "TOOL_EXECUTION_FAILED",
        "TRANSIENT_DEPENDENCY_UNAVAILABLE": "TOOL_EXECUTION_FAILED",
    }

    permanent_map = {
        "FATAL_POLICY_VIOLATION": "TOOL_EXECUTION_FAILED",
        "FATAL_INVALID_INPUT": "TOOL_EXECUTION_FAILED",
        "FATAL_UNSUPPORTED_ACTION": "TOOL_EXECUTION_FAILED",
        "FATAL_TARGET_NOT_FOUND": "TOOL_EXECUTION_FAILED",
        "TOOL_OUTPUT_MALFORMED": "TOOL_OUTPUT_MALFORMED",
    }

    if error_text in retryable_map:
        return {
            "failure_type": "TRANSIENT",
            "retryable": True,
            "reason_code": retryable_map[error_text],
        }

    if error_text in permanent_map:
        return {
            "failure_type": "PERMANENT",
            "retryable": False,
            "reason_code": permanent_map[error_text],
        }

    return {
        "failure_type": "UNKNOWN",
        "retryable": False,
        "reason_code": "TOOL_EXECUTION_FAILED",
    }