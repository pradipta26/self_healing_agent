from __future__ import annotations

"""
 Monitoring / Metrics Contract

This module defines the canonical metric vocabulary for the self-healing agent.
It is intentionally lightweight: names first, emission later.

Why this exists:
- prevent ad-hoc metric naming
- keep monitoring vocabulary consistent across nodes
- make instrumentation reviewable
- preserve operator-facing semantics

Note:
These are metric identifiers / semantic names, not Prometheus/OpenTelemetry bindings yet.
"""


# -----------------------------------------------------------------------------
# System metrics
# -----------------------------------------------------------------------------
AGENT_RUNS_STARTED = "agent_runs_started"
AGENT_RUNS_COMPLETED = "agent_runs_completed"
AGENT_RUNS_FAILED = "agent_runs_failed"
AGENT_RUN_LATENCY_MS = "agent_run_latency_ms"
ERROR_NOTIFICATIONS_SENT = "error_notifications_sent"


# -----------------------------------------------------------------------------
# Retrieval / context metrics
# -----------------------------------------------------------------------------
RETRIEVAL_EMPTY_RATE = "retrieval_empty_rate"
RETRIEVAL_LOW_SCORE_RATE = "retrieval_low_score_rate"
QUERY_REWRITE_RATE = "query_rewrite_rate"
CONTEXT_VALIDATION_FAILURE_RATE = "context_validation_failure_rate"
RETRIEVAL_RETRY_COUNT = "retrieval_retry_count"


# -----------------------------------------------------------------------------
# Grounding / evidence metrics
# -----------------------------------------------------------------------------
GROUNDING_FAILURE_RATE = "grounding_failure_rate"
UNSUPPORTED_CLAIM_RATE = "unsupported_claim_rate"
CONTEXT_INSUFFICIENT_RATE = "context_insufficient_rate"
EVIDENCE_USAGE_DENSITY = "evidence_usage_density"


# -----------------------------------------------------------------------------
# Decision / autonomy metrics
# -----------------------------------------------------------------------------
ROUTE_DISTRIBUTION = "route_distribution"
AUTONOMY_MODE_DISTRIBUTION = "autonomy_mode_distribution"
ACTIONABILITY_DISTRIBUTION = "actionability_distribution"
ESCALATION_REASON_DISTRIBUTION = "escalation_reason_distribution"
APPROVAL_REQUIRED_RATE = "approval_required_rate"
APPROVAL_REJECT_RATE = "approval_reject_rate"
INVESTIGATION_ROUTE_RATE = "investigation_route_rate"


# -----------------------------------------------------------------------------
# Tool / execution metrics
# -----------------------------------------------------------------------------
TOOL_ATTEMPT_COUNT = "tool_attempt_count"
TOOL_SUCCESS_RATE = "tool_success_rate"
TOOL_FAILURE_RATE = "tool_failure_rate"
TOOL_RETRY_RATE = "tool_retry_rate"
RETRY_ATTEMPT_COUNT = "retry_attempt_count"
FAILURE_TYPE_DISTRIBUTION = "failure_type_distribution"
SIDE_EFFECT_COMMITTED_RATE = "side_effect_committed_rate"


# -----------------------------------------------------------------------------
# Rollback metrics
# -----------------------------------------------------------------------------
ROLLBACK_INVOCATION_RATE = "rollback_invocation_rate"
ROLLBACK_SUCCESS_RATE = "rollback_success_rate"
ROLLBACK_FAILURE_RATE = "rollback_failure_rate"
ROLLBACK_SKIPPED_RATE = "rollback_skipped_rate"


# -----------------------------------------------------------------------------
# Action validation metrics
# -----------------------------------------------------------------------------
ACTION_VALIDATION_SUCCESS_RATE = "action_validation_success_rate"
ACTION_VALIDATION_FAILURE_RATE = "action_validation_failure_rate"
POST_ACTION_INVESTIGATION_RATE = "post_action_investigation_rate"


# -----------------------------------------------------------------------------
# Groupings
# -----------------------------------------------------------------------------
SYSTEM_METRICS = {
    AGENT_RUNS_STARTED,
    AGENT_RUNS_COMPLETED,
    AGENT_RUNS_FAILED,
    AGENT_RUN_LATENCY_MS,
    ERROR_NOTIFICATIONS_SENT,
}

RETRIEVAL_METRICS = {
    RETRIEVAL_EMPTY_RATE,
    RETRIEVAL_LOW_SCORE_RATE,
    QUERY_REWRITE_RATE,
    CONTEXT_VALIDATION_FAILURE_RATE,
    RETRIEVAL_RETRY_COUNT,
}

GROUNDING_METRICS = {
    GROUNDING_FAILURE_RATE,
    UNSUPPORTED_CLAIM_RATE,
    CONTEXT_INSUFFICIENT_RATE,
    EVIDENCE_USAGE_DENSITY,
}

DECISION_METRICS = {
    ROUTE_DISTRIBUTION,
    AUTONOMY_MODE_DISTRIBUTION,
    ACTIONABILITY_DISTRIBUTION,
    ESCALATION_REASON_DISTRIBUTION,
    APPROVAL_REQUIRED_RATE,
    APPROVAL_REJECT_RATE,
    INVESTIGATION_ROUTE_RATE,
}

EXECUTION_METRICS = {
    TOOL_ATTEMPT_COUNT,
    TOOL_SUCCESS_RATE,
    TOOL_FAILURE_RATE,
    TOOL_RETRY_RATE,
    RETRY_ATTEMPT_COUNT,
    FAILURE_TYPE_DISTRIBUTION,
    SIDE_EFFECT_COMMITTED_RATE,
}

ROLLBACK_METRICS = {
    ROLLBACK_INVOCATION_RATE,
    ROLLBACK_SUCCESS_RATE,
    ROLLBACK_FAILURE_RATE,
    ROLLBACK_SKIPPED_RATE,
}

ACTION_VALIDATION_METRICS = {
    ACTION_VALIDATION_SUCCESS_RATE,
    ACTION_VALIDATION_FAILURE_RATE,
    POST_ACTION_INVESTIGATION_RATE,
}

ALL_METRICS = (
    SYSTEM_METRICS
    | RETRIEVAL_METRICS
    | GROUNDING_METRICS
    | DECISION_METRICS
    | EXECUTION_METRICS
    | ROLLBACK_METRICS
    | ACTION_VALIDATION_METRICS
)


# -----------------------------------------------------------------------------
# Optional helper maps
# -----------------------------------------------------------------------------
METRIC_TO_GROUP = {
    metric: "system" for metric in SYSTEM_METRICS
} | {
    metric: "retrieval" for metric in RETRIEVAL_METRICS
} | {
    metric: "grounding" for metric in GROUNDING_METRICS
} | {
    metric: "decision" for metric in DECISION_METRICS
} | {
    metric: "execution" for metric in EXECUTION_METRICS
} | {
    metric: "rollback" for metric in ROLLBACK_METRICS
} | {
    metric: "action_validation" for metric in ACTION_VALIDATION_METRICS
}