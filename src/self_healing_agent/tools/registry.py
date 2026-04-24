from __future__ import annotations

AVAILABLE_TOOL_FAMILIES = {
    "RESTART_SERVICE": {
        "tool_name": "restart_service",
        "action_family": "RESTART_SERVICE",
        "executor": "mock_tool_execute",
        "precondition": "check_restart_service_preconditions",
        "supports_rollback": True,
        "rollback": {
            "tool_name": "restart_previous_instance",
            "action_family": "RESTART_SERVICE",
            "executor": "mock_tool_execute",
            "precondition": "check_restart_rollback_preconditions",
            "args_template": {
                "service": "{service}",
                "env": "{env}",
            },
        },
    },
    "CLEAR_CACHE": {
        "tool_name": "clear_cache",
        "action_family": "CLEAR_CACHE",
        "executor": "mock_tool_execute",
        "precondition": "check_clear_cache_preconditions",
        "supports_rollback": False,
        "rollback": None,
    },
}