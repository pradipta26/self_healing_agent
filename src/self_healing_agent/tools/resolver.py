

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from self_healing_agent.tools.mock_tools import mock_tool_execute
from self_healing_agent.tools.preconditions import (
    check_clear_cache_preconditions,
    check_restart_rollback_preconditions,
    check_restart_service_preconditions,
)


ToolExecutor = Callable[[dict[str, Any]], dict[str, Any]]
ToolPrecondition = Callable[..., dict[str, Any]]


_EXECUTOR_REGISTRY: dict[str, ToolExecutor] = {
    "mock_tool_execute": mock_tool_execute,
}


_PRECONDITION_REGISTRY: dict[str, ToolPrecondition] = {
    "check_restart_service_preconditions": check_restart_service_preconditions,
    "check_restart_rollback_preconditions": check_restart_rollback_preconditions,
    "check_clear_cache_preconditions": check_clear_cache_preconditions,
}


def resolve_executor(executor_name: str) -> ToolExecutor:
    """
    Resolve a tool executor by registry name.

    Raises:
        ValueError: if the executor name is empty or unknown.
    """
    normalized = str(executor_name).strip()
    if not normalized:
        raise ValueError("Executor name is required for tool resolution.")

    executor = _EXECUTOR_REGISTRY.get(normalized)
    if executor is None:
        raise ValueError(f"Unknown tool executor: {normalized}")

    return executor


def resolve_precondition(precondition_name: str | None) -> ToolPrecondition | None:
    """
    Resolve an optional precondition function by registry name.

    Returns:
        Callable or None if no precondition is configured.

    Raises:
        ValueError: if a non-empty precondition name is unknown.
    """
    if precondition_name is None:
        return None

    normalized = str(precondition_name).strip()
    if not normalized:
        return None

    precondition = _PRECONDITION_REGISTRY.get(normalized)
    if precondition is None:
        raise ValueError(f"Unknown tool precondition: {normalized}")

    return precondition
