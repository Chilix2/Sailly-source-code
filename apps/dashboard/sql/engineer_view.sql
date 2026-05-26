-- ─────────────────────────────────────────────────────────────────────────────
-- Engineer dashboard queries (9.O9 single-dashboard — engineer tab)
-- All queries target the read replica (see Task C4).
-- Replace :tenant_id with the tenant filter, or remove the WHERE clause to
-- see all tenants.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. p50/p95/p99 total latency per stage, last 24h (line chart) ────────────
--    Frontend: render one series per p-level per stage.
SELECT
    date_trunc('hour', ts)                                                  AS hour,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY stt_ms)                   AS p50_stt,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY stt_ms)                   AS p95_stt,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY stt_ms)                   AS p99_stt,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY extract_ms)               AS p50_extract,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY extract_ms)               AS p95_extract,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY extract_ms)               AS p99_extract,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY l2_ms)                    AS p50_l2,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY l2_ms)                    AS p95_l2,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY l2_ms)                    AS p99_l2,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tool_ms)                  AS p50_tool,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tool_ms)                  AS p95_tool,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY tool_ms)                  AS p99_tool,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_ms)                 AS p50_total,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_ms)                 AS p95_total,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_ms)                 AS p99_total
FROM google_turn_metrics
WHERE ts > now() - interval '24 hours'
GROUP BY hour
ORDER BY hour;


-- ── 2. Error rate per error_code, last 24h (table) ───────────────────────────
--    Frontend: show top codes by frequency in a sortable table.
SELECT
    unnest(error_codes)                                                     AS error_code,
    COUNT(*)                                                                AS occurrences,
    COUNT(DISTINCT call_sid)                                                AS affected_calls,
    ROUND(
        COUNT(*)::NUMERIC / NULLIF((
            SELECT COUNT(*) FROM google_turn_metrics
            WHERE ts > now() - interval '24 hours'
        ), 0) * 100,
    2)                                                                      AS pct_of_turns
FROM google_turn_metrics
WHERE
    ts > now() - interval '24 hours'
    AND error_codes IS NOT NULL
    AND array_length(error_codes, 1) > 0
GROUP BY error_code
ORDER BY occurrences DESC
LIMIT 20;


-- ── 3. Policy rule fire counts, last 7d (top-10 table) ───────────────────────
--    Requires a policy_events table or JSONB tapping from layer3_changes.
--    If tracking via error_codes array, adapt the filter below:
SELECT
    unnest(error_codes)                                                     AS rule_code,
    COUNT(*)                                                                AS fires
FROM google_turn_metrics
WHERE ts > now() - interval '7 days'
GROUP BY rule_code
ORDER BY fires DESC
LIMIT 10;


-- ── 4. Token cost per tenant (stacked area, 7d) ──────────────────────────────
SELECT
    date_trunc('day', ts)                                                   AS day,
    tenant_id,
    ROUND(SUM(cost_eur)::NUMERIC, 4)                                       AS total_cost_eur,
    SUM(prompt_tokens_in + prompt_tokens_out +
        COALESCE(extract_tokens_in, 0) + COALESCE(extract_tokens_out, 0)) AS total_tokens
FROM google_turn_metrics
WHERE
    ts > now() - interval '7 days'
    AND cost_eur IS NOT NULL
GROUP BY day, tenant_id
ORDER BY day, tenant_id;


-- ── 5. Per-tool latency p95, last 24h (table) ────────────────────────────────
--    tool_durations is JSONB: {"create_order": 245, "send_sms": 88}
--    Expand the JSONB into rows for aggregation.
SELECT
    kv.key                                                                  AS tool_name,
    COUNT(*)                                                                AS call_count,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY (kv.value::TEXT)::INT)   AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY (kv.value::TEXT)::INT)   AS p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY (kv.value::TEXT)::INT)   AS p99_ms
FROM google_turn_metrics,
     jsonb_each(tool_durations) AS kv
WHERE
    ts > now() - interval '24 hours'
    AND tool_durations IS NOT NULL
GROUP BY kv.key
ORDER BY p95_ms DESC;


-- ── 6. ASR confidence distribution, last 7d ──────────────────────────────────
SELECT
    width_bucket(asr_confidence, 0, 1, 10)                                 AS bucket,
    COUNT(*)                                                                AS turns
FROM google_turn_metrics
WHERE
    ts > now() - interval '7 days'
    AND asr_confidence IS NOT NULL
GROUP BY bucket
ORDER BY bucket;


-- ── 7. Active node distribution (heatmap / table), last 7d ──────────────────
SELECT
    active_node,
    COUNT(*)                                                                AS turn_count,
    ROUND(AVG(total_ms))                                                    AS avg_total_ms,
    ROUND(AVG(l2_ms))                                                       AS avg_l2_ms
FROM google_turn_metrics
WHERE ts > now() - interval '7 days'
GROUP BY active_node
ORDER BY turn_count DESC;
