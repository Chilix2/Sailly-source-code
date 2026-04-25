-- ─────────────────────────────────────────────────────────────────────────────
-- Operator dashboard queries (9.O9 single-dashboard — operator tab)
-- Audience: restaurant managers / operations team.
-- All queries target the read replica. Parameterise :tenant_id as needed.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. Total calls today / this week (headline numbers) ─────────────────────
SELECT
    COUNT(*) FILTER (WHERE call_started_at >= current_date)                AS calls_today,
    COUNT(*) FILTER (WHERE call_started_at >= date_trunc('week', now()))   AS calls_this_week
FROM google_calls;


-- ── 2. Disposition breakdown today (donut chart) ─────────────────────────────
SELECT
    COALESCE(disposition, 'unknown')                                        AS disposition,
    COUNT(*)                                                                AS n,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)                    AS pct
FROM google_calls
WHERE call_started_at >= current_date
GROUP BY disposition
ORDER BY n DESC;


-- ── 3. Calls per hour today (bar chart) ─────────────────────────────────────
SELECT
    date_trunc('hour', call_started_at)                                    AS hour,
    COUNT(*)                                                                AS calls
FROM google_calls
WHERE call_started_at >= current_date
GROUP BY hour
ORDER BY hour;


-- ── 4. Top reasons callers transferred to human, last 7d (table) ────────────
--    Uses transfer_reason from the transfer_to_human tool result stored in
--    google_turn_metrics.tools_called or audit_log.
SELECT
    al.args ->> 'reason'                                                    AS reason,
    COUNT(*)                                                                AS transfers
FROM audit_log al
WHERE
    al.tool_name = 'transfer_to_human'
    AND al.created_at > now() - interval '7 days'
GROUP BY reason
ORDER BY transfers DESC
LIMIT 20;


-- ── 5. Pending callbacks (table — live) ─────────────────────────────────────
SELECT
    id,
    call_sid,
    phone,
    name,
    context_summary,
    scheduled_for,
    created_at
FROM callback_queue
WHERE
    status = 'pending'
    AND (scheduled_for IS NULL OR scheduled_for >= now())
ORDER BY scheduled_for ASC NULLS LAST
LIMIT 100;


-- ── 6. Order volume trend, last 7d (line chart) ──────────────────────────────
--    Counts successful create_order audit entries per day.
SELECT
    date_trunc('day', al.created_at)                                        AS day,
    al.args ->> 'tenant_id'                                                 AS tenant_id,
    COUNT(*)                                                                 AS orders
FROM audit_log al
WHERE
    al.tool_name = 'create_order'
    AND al.success = TRUE
    AND al.created_at > now() - interval '7 days'
GROUP BY day, tenant_id
ORDER BY day;


-- ── 7. Bot-handled vs. transferred rate, last 7d ────────────────────────────
SELECT
    date_trunc('day', call_started_at)                                      AS day,
    COUNT(*) FILTER (WHERE disposition = 'resolved')                        AS resolved,
    COUNT(*) FILTER (WHERE disposition LIKE 'transferred%')                 AS transferred,
    COUNT(*) FILTER (WHERE disposition = 'abandoned')                       AS abandoned,
    COUNT(*)                                                                 AS total
FROM google_calls
WHERE call_started_at > now() - interval '7 days'
GROUP BY day
ORDER BY day;


-- ── 8. Cost summary per tenant this month ────────────────────────────────────
SELECT
    tenant_id,
    ROUND(SUM(call_cost_eur)::NUMERIC, 4)                                   AS total_cost_eur,
    COUNT(*)                                                                 AS calls
FROM google_calls
WHERE call_started_at >= date_trunc('month', now())
GROUP BY tenant_id
ORDER BY total_cost_eur DESC;
