\echo '=== Model Status Summary ==='
SELECT evaluation_status, COUNT(*)
FROM llm_models
GROUP BY evaluation_status
ORDER BY evaluation_status;

\echo ''
\echo '=== Verified Routing Candidates ==='
SELECT m.id, m.routing_key, rs.quality_score, rs.latency_score, rs.cost_score
FROM llm_models m
JOIN llm_model_routing_settings rs ON rs.model_id = m.id
WHERE m.evaluation_status = 'verified'
  AND rs.enabled_for_routing = TRUE
  AND rs.is_evaluated_for_routing = TRUE
ORDER BY m.id;

\echo ''
\echo '=== Provisional Pending Live ==='
SELECT m.id, m.routing_key, m.evaluation_version
FROM llm_models m
WHERE m.evaluation_status = 'provisional'
ORDER BY m.id;

\echo ''
\echo '=== Rejected Models ==='
SELECT m.id, m.routing_key, m.evaluation_version, m.last_evaluated_at
FROM llm_models m
WHERE m.evaluation_status = 'rejected'
ORDER BY m.last_evaluated_at DESC NULLS LAST, m.id DESC;

\echo ''
\echo '=== Recent Live Runs ==='
SELECT r.id, m.routing_key, r.status, r.sample_size, r.summary, r.created_at
FROM model_benchmark_runs r
JOIN llm_models m ON m.id = r.model_id
WHERE r.benchmark_kind = 'live'
ORDER BY r.id DESC
LIMIT 20;

\echo ''
\echo '=== Recent Heuristic Runs ==='
SELECT r.id, m.routing_key, r.status, r.summary, r.created_at
FROM model_benchmark_runs r
JOIN llm_models m ON m.id = r.model_id
WHERE r.benchmark_kind = 'heuristic'
ORDER BY r.id DESC
LIMIT 20;

\echo ''
\echo '=== Failed Live Runs ==='
SELECT r.id, m.routing_key, r.status, r.summary
FROM model_benchmark_runs r
JOIN llm_models m ON m.id = r.model_id
WHERE r.benchmark_kind = 'live'
  AND r.status <> 'completed'
ORDER BY r.id DESC
LIMIT 30;

\echo ''
\echo '=== Safety Check (must be 0 rows) ==='
SELECT m.id, m.routing_key, m.evaluation_status, rs.enabled_for_routing, rs.is_evaluated_for_routing
FROM llm_models m
JOIN llm_model_routing_settings rs ON rs.model_id = m.id
WHERE m.evaluation_status <> 'verified'
  AND (rs.enabled_for_routing = TRUE OR rs.is_evaluated_for_routing = TRUE);
