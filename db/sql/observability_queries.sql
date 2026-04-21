-- ============================================================
-- observability_queries.sql
-- Execution, rollback, and action-outcome observability queries
-- for Self-Healing Agent
-- ============================================================


-- 1. Tool attempt volume overall
SELECT
    COUNT(*) AS total_tool_attempts,
    COUNT(*) FILTER (WHERE execution_phase = 'FORWARD') AS forward_attempts,
    COUNT(*) FILTER (WHERE execution_phase = 'ROLLBACK') AS rollback_attempts
FROM tool_execution_log;


-- 2. Tool attempt volume by tool
SELECT
    tool_name,
    execution_phase,
    COUNT(*) AS attempt_count
FROM tool_execution_log
GROUP BY tool_name, execution_phase
ORDER BY attempt_count DESC, tool_name;


-- 3. Tool success / failure rate overall
SELECT
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE ok = true) AS success_count,
    COUNT(*) FILTER (WHERE ok = false) AS failure_count,
    ROUND(
        COUNT(*) FILTER (WHERE ok = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS success_rate,
    ROUND(
        COUNT(*) FILTER (WHERE ok = false)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS failure_rate
FROM tool_execution_log;


-- 3a. Tool success / failure rate overall (time-bounded)
-- Replace :start_time_utc and :end_time_utc with actual timestamps in your SQL client if needed.
SELECT
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE ok = true) AS success_count,
    COUNT(*) FILTER (WHERE ok = false) AS failure_count,
    ROUND(
        COUNT(*) FILTER (WHERE ok = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS success_rate,
    ROUND(
        COUNT(*) FILTER (WHERE ok = false)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS failure_rate
FROM tool_execution_log
WHERE timestamp_utc >= :start_time_utc
  AND timestamp_utc < :end_time_utc;


-- 4. Tool success / failure rate by tool
SELECT
    tool_name,
    execution_phase,
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE ok = true) AS success_count,
    COUNT(*) FILTER (WHERE ok = false) AS failure_count,
    ROUND(
        COUNT(*) FILTER (WHERE ok = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS success_rate,
    ROUND(
        COUNT(*) FILTER (WHERE ok = false)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS failure_rate
FROM tool_execution_log
GROUP BY tool_name, execution_phase
ORDER BY total_attempts DESC, tool_name;


-- 5. Retry decision distribution overall
SELECT
    retry_decision,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0), 4) AS ratio
FROM tool_execution_log
GROUP BY retry_decision
ORDER BY count DESC;


-- 6. Retry rate by tool
SELECT
    tool_name,
    execution_phase,
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE retry_decision = 'RETRY_TOOL') AS retry_count,
    ROUND(
        COUNT(*) FILTER (WHERE retry_decision = 'RETRY_TOOL')::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS retry_rate
FROM tool_execution_log
GROUP BY tool_name, execution_phase
ORDER BY retry_rate DESC, total_attempts DESC, tool_name;


-- 6a. Retry rate by tool (time-bounded)
-- Replace :start_time_utc and :end_time_utc with actual timestamps in your SQL client if needed.
SELECT
    tool_name,
    execution_phase,
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE retry_decision = 'RETRY_TOOL') AS retry_count,
    ROUND(
        COUNT(*) FILTER (WHERE retry_decision = 'RETRY_TOOL')::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS retry_rate
FROM tool_execution_log
WHERE timestamp_utc >= :start_time_utc
  AND timestamp_utc < :end_time_utc
GROUP BY tool_name, execution_phase
ORDER BY retry_rate DESC, total_attempts DESC, tool_name;


-- 7. Failure type distribution
SELECT
    COALESCE(failure_type, 'UNSPECIFIED') AS failure_type,
    execution_phase,
    COUNT(*) AS count
FROM tool_execution_log
GROUP BY COALESCE(failure_type, 'UNSPECIFIED'), execution_phase
ORDER BY count DESC, failure_type;


-- 8. Error code breakdown
SELECT
    COALESCE(NULLIF(error_code, ''), 'NO_ERROR_CODE') AS error_code,
    execution_phase,
    COUNT(*) AS count
FROM tool_execution_log
GROUP BY COALESCE(NULLIF(error_code, ''), 'NO_ERROR_CODE'), execution_phase
ORDER BY count DESC, error_code;


-- 9. Side-effect committed rate overall
SELECT
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE side_effect_committed = true) AS side_effect_committed_count,
    ROUND(
        COUNT(*) FILTER (WHERE side_effect_committed = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS side_effect_committed_rate
FROM tool_execution_log;


-- 9a. Side-effect committed rate overall (time-bounded)
-- Replace :start_time_utc and :end_time_utc with actual timestamps in your SQL client if needed.
SELECT
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE side_effect_committed = true) AS side_effect_committed_count,
    ROUND(
        COUNT(*) FILTER (WHERE side_effect_committed = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS side_effect_committed_rate
FROM tool_execution_log
WHERE timestamp_utc >= :start_time_utc
  AND timestamp_utc < :end_time_utc;


-- 10. Side-effect committed rate by tool
SELECT
    tool_name,
    execution_phase,
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE side_effect_committed = true) AS side_effect_committed_count,
    ROUND(
        COUNT(*) FILTER (WHERE side_effect_committed = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS side_effect_committed_rate
FROM tool_execution_log
GROUP BY tool_name, execution_phase
ORDER BY side_effect_committed_rate DESC, total_attempts DESC, tool_name;


-- 11. Rollback invocation / success / failure summary from lifecycle events
SELECT
    COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_SUCCEEDED') AS rollback_success_count,
    COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_FAILED') AS rollback_failure_count,
    COUNT(*) FILTER (
        WHERE event_type IN ('ROLLBACK_VERIFICATION_SUCCEEDED', 'ROLLBACK_VERIFICATION_FAILED')
    ) AS rollback_verification_count,
    ROUND(
        COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_SUCCEEDED')::numeric /
        NULLIF(
            COUNT(*) FILTER (
                WHERE event_type IN ('ROLLBACK_VERIFICATION_SUCCEEDED', 'ROLLBACK_VERIFICATION_FAILED')
            ),
            0
        ),
        4
    ) AS rollback_success_rate
FROM decision_lifecycle_event;


-- 11a. Rollback invocation / success / failure summary from lifecycle events (time-bounded)
-- Replace :start_time_utc and :end_time_utc with actual timestamps in your SQL client if needed.
SELECT
    COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_SUCCEEDED') AS rollback_success_count,
    COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_FAILED') AS rollback_failure_count,
    COUNT(*) FILTER (
        WHERE event_type IN ('ROLLBACK_VERIFICATION_SUCCEEDED', 'ROLLBACK_VERIFICATION_FAILED')
    ) AS rollback_verification_count,
    ROUND(
        COUNT(*) FILTER (WHERE event_type = 'ROLLBACK_VERIFICATION_SUCCEEDED')::numeric /
        NULLIF(
            COUNT(*) FILTER (
                WHERE event_type IN ('ROLLBACK_VERIFICATION_SUCCEEDED', 'ROLLBACK_VERIFICATION_FAILED')
            ),
            0
        ),
        4
    ) AS rollback_success_rate
FROM decision_lifecycle_event
WHERE timestamp_utc >= :start_time_utc
  AND timestamp_utc < :end_time_utc;


-- 12. Rollback execution attempt count from tool log
SELECT
    COUNT(*) AS rollback_attempts,
    COUNT(*) FILTER (WHERE ok = true) AS rollback_tool_successes,
    COUNT(*) FILTER (WHERE ok = false) AS rollback_tool_failures,
    ROUND(
        COUNT(*) FILTER (WHERE ok = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS rollback_tool_success_rate
FROM tool_execution_log
WHERE execution_phase = 'ROLLBACK';


-- 12a. Rollback execution attempt count from tool log (time-bounded)
-- Replace :start_time_utc and :end_time_utc with actual timestamps in your SQL client if needed.
SELECT
    COUNT(*) AS rollback_attempts,
    COUNT(*) FILTER (WHERE ok = true) AS rollback_tool_successes,
    COUNT(*) FILTER (WHERE ok = false) AS rollback_tool_failures,
    ROUND(
        COUNT(*) FILTER (WHERE ok = true)::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS rollback_tool_success_rate
FROM tool_execution_log
WHERE execution_phase = 'ROLLBACK'
  AND timestamp_utc >= :start_time_utc
  AND timestamp_utc < :end_time_utc;


-- 13. Action validation success / failure summary from lifecycle events
SELECT
    COUNT(*) FILTER (WHERE event_type = 'ACTION_VALIDATION_SUCCEEDED') AS action_validation_success_count,
    COUNT(*) FILTER (WHERE event_type = 'ACTION_VALIDATION_FAILED') AS action_validation_failure_count,
    COUNT(*) FILTER (
        WHERE event_type IN ('ACTION_VALIDATION_SUCCEEDED', 'ACTION_VALIDATION_FAILED')
    ) AS action_validation_total,
    ROUND(
        COUNT(*) FILTER (WHERE event_type = 'ACTION_VALIDATION_SUCCEEDED')::numeric /
        NULLIF(
            COUNT(*) FILTER (
                WHERE event_type IN ('ACTION_VALIDATION_SUCCEEDED', 'ACTION_VALIDATION_FAILED')
            ),
            0
        ),
        4
    ) AS action_validation_success_rate
FROM decision_lifecycle_event;


-- 13a. Action validation success / failure summary from lifecycle events (time-bounded)
-- Replace :start_time_utc and :end_time_utc with actual timestamps in your SQL client if needed.
SELECT
    COUNT(*) FILTER (WHERE event_type = 'ACTION_VALIDATION_SUCCEEDED') AS action_validation_success_count,
    COUNT(*) FILTER (WHERE event_type = 'ACTION_VALIDATION_FAILED') AS action_validation_failure_count,
    COUNT(*) FILTER (
        WHERE event_type IN ('ACTION_VALIDATION_SUCCEEDED', 'ACTION_VALIDATION_FAILED')
    ) AS action_validation_total,
    ROUND(
        COUNT(*) FILTER (WHERE event_type = 'ACTION_VALIDATION_SUCCEEDED')::numeric /
        NULLIF(
            COUNT(*) FILTER (
                WHERE event_type IN ('ACTION_VALIDATION_SUCCEEDED', 'ACTION_VALIDATION_FAILED')
            ),
            0
        ),
        4
    ) AS action_validation_success_rate
FROM decision_lifecycle_event
WHERE timestamp_utc >= :start_time_utc
  AND timestamp_utc < :end_time_utc;


-- 14. Tool attempt sequence for a single incident (for operator investigation)
-- Replace :incident_id with an actual incident id in your SQL client if needed.
SELECT
    incident_id,
    source_incident_id,
    execution_phase,
    tool_step,
    attempt,
    tool_name,
    ok,
    error_code,
    failure_type,
    retry_decision,
    side_effect_committed,
    timestamp_utc
FROM tool_execution_log
WHERE incident_id = :incident_id
ORDER BY tool_step, attempt, id;


-- 15. Decision + execution correlation summary
SELECT
    d.incident_id,
    d.route,
    d.escalation_type,
    d.confidence,
    d.actionability,
    COUNT(t.id) AS tool_attempts,
    COUNT(*) FILTER (WHERE t.execution_phase = 'ROLLBACK') AS rollback_attempts,
    COUNT(*) FILTER (WHERE t.retry_decision = 'RETRY_TOOL') AS retry_attempts,
    COUNT(*) FILTER (WHERE t.side_effect_committed = true) AS side_effect_cases
FROM decision_log d
LEFT JOIN tool_execution_log t
    ON d.incident_id = t.incident_id
GROUP BY
    d.incident_id,
    d.route,
    d.escalation_type,
    d.confidence,
    d.actionability
ORDER BY tool_attempts DESC, d.incident_id;


-- 16. Recent execution failures (operator triage query)
SELECT
    incident_id,
    source_incident_id,
    execution_phase,
    tool_name,
    attempt,
    error_code,
    failure_type,
    retry_decision,
    side_effect_committed,
    timestamp_utc
FROM tool_execution_log
WHERE ok = false
ORDER BY timestamp_utc DESC
LIMIT 100;