-- ============================================================
-- decision_log_metrics.sql
-- Core metrics and trust/readiness queries for Self-Healing Agent
-- ============================================================


-- 1. Proposal rate
SELECT
    COUNT(*) AS total_decisions,
    COUNT(*) FILTER (WHERE route = 'PROPOSE') AS propose_count,
    ROUND(
        COUNT(*) FILTER (WHERE route = 'PROPOSE')::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS proposal_rate
FROM decision_log;


-- 2. Escalation rate
SELECT
    COUNT(*) AS total_decisions,
    COUNT(*) FILTER (WHERE route <> 'PROPOSE') AS escalation_count,
    ROUND(
        COUNT(*) FILTER (WHERE route <> 'PROPOSE')::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS escalation_rate
FROM decision_log;


-- 3. Escalation type breakdown
SELECT
    escalation_type,
    COUNT(*) AS count
FROM decision_log
GROUP BY escalation_type
ORDER BY count DESC;


-- 4. Retrieval confidence distribution
SELECT
    policy_checks -> 'retrieval' ->> 'confidence' AS retrieval_confidence,
    COUNT(*) AS count
FROM decision_log
GROUP BY retrieval_confidence
ORDER BY count DESC;


-- 5. Grounding verdict distribution
SELECT
    policy_checks -> 'grounding' ->> 'verdict' AS grounding_verdict,
    COUNT(*) AS count
FROM decision_log
GROUP BY grounding_verdict
ORDER BY count DESC;


-- 6. Average retrieval score overall
SELECT
    ROUND(AVG(retrieval_score_avg)::numeric, 6) AS avg_retrieval_score
FROM decision_log
WHERE retrieval_score_avg IS NOT NULL;


-- 7. Average retrieval score by service
SELECT
    service_domain,
    ROUND(AVG(retrieval_score_avg)::numeric, 6) AS avg_retrieval_score,
    COUNT(*) AS count
FROM decision_log
WHERE retrieval_score_avg IS NOT NULL
GROUP BY service_domain
ORDER BY avg_retrieval_score DESC;


-- 8. Warning frequency breakdown
SELECT
    unnest(warnings) AS warning,
    COUNT(*) AS count
FROM decision_log
GROUP BY warning
ORDER BY count DESC;


-- 9. Decision latency overall
SELECT
    ROUND(AVG(decision_latency_ms)::numeric, 2) AS avg_latency_ms,
    MIN(decision_latency_ms) AS min_latency_ms,
    MAX(decision_latency_ms) AS max_latency_ms
FROM decision_log
WHERE decision_latency_ms IS NOT NULL;


-- 10. Decision latency by route
SELECT
    route,
    ROUND(AVG(decision_latency_ms)::numeric, 2) AS avg_latency_ms,
    COUNT(*) AS count
FROM decision_log
WHERE decision_latency_ms IS NOT NULL
GROUP BY route
ORDER BY avg_latency_ms DESC;


-- 11. Safe proposal rate
SELECT
    COUNT(*) FILTER (
        WHERE route = 'PROPOSE'
          AND (facts ->> 'context_validity') = 'VALID'
          AND (facts ->> 'grounding_verdict') = 'GROUNDED'
    ) AS safe_proposals,
    COUNT(*) AS total_decisions,
    ROUND(
        COUNT(*) FILTER (
            WHERE route = 'PROPOSE'
              AND (facts ->> 'context_validity') = 'VALID'
              AND (facts ->> 'grounding_verdict') = 'GROUNDED'
        )::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS safe_proposal_rate
FROM decision_log;


-- 12. Retrieval weakness rate
SELECT
    COUNT(*) FILTER (
        WHERE retrieval_empty = true
           OR conflicting_signals = true
           OR (facts ->> 'context_validity') IN ('LOW_QUALITY', 'CONFLICTING', 'EMPTY')
    ) AS weak_retrieval_cases,
    COUNT(*) AS total_decisions,
    ROUND(
        COUNT(*) FILTER (
            WHERE retrieval_empty = true
               OR conflicting_signals = true
               OR (facts ->> 'context_validity') IN ('LOW_QUALITY', 'CONFLICTING', 'EMPTY')
        )::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS retrieval_weakness_rate
FROM decision_log;


-- 13. High-confidence proposal count
SELECT
    COUNT(*) AS high_confidence_proposals
FROM decision_log
WHERE route = 'PROPOSE'
  AND confidence = 'HIGH';


-- 14. Route distribution
SELECT
    route,
    COUNT(*) AS count
FROM decision_log
GROUP BY route
ORDER BY count DESC;