-- 02_repeat_ladder.sql  (SIMULATED DATA)
-- Of first-time buyers, how many climb to a 2nd and 3rd order, and how fast?
-- Only buyers whose first order is at least 28 days before the data cut-off (25 Oct 2026),
-- so everyone had a full 28 days. The 3rd order within 28 days is the onboarding north-star.

WITH firsts AS (
    SELECT user_id, MIN(order_time) AS first_time
    FROM orders GROUP BY user_id
),
eligible AS (
    SELECT * FROM firsts WHERE julianday(first_time) <= julianday('2026-10-25') - 28
),
ladder AS (
    SELECT e.user_id,
           MAX(o.order_number = 2 AND julianday(o.order_time) - julianday(e.first_time) <= 7)  AS o2_7d,
           MAX(o.order_number = 2 AND julianday(o.order_time) - julianday(e.first_time) <= 14) AS o2_14d,
           MAX(o.order_number = 2 AND julianday(o.order_time) - julianday(e.first_time) <= 28) AS o2_28d,
           MAX(o.order_number = 3 AND julianday(o.order_time) - julianday(e.first_time) <= 28) AS o3_28d,
           MAX(CASE WHEN o.order_number = 1 THEN o.has_produce END)                           AS produce_first
    FROM eligible e JOIN orders o USING (user_id)
    GROUP BY e.user_id
)
SELECT CASE WHEN produce_first = 1 THEN 'first order had produce' ELSE 'no produce in first order' END AS segment,
       COUNT(*)                          AS first_time_buyers,
       ROUND(100.0 * AVG(o2_7d), 1)      AS pct_2nd_order_7d,
       ROUND(100.0 * AVG(o2_14d), 1)     AS pct_2nd_order_14d,
       ROUND(100.0 * AVG(o2_28d), 1)     AS pct_2nd_order_28d,
       ROUND(100.0 * AVG(o3_28d), 1)     AS pct_3rd_order_28d
FROM ladder GROUP BY 1
UNION ALL
SELECT 'All', COUNT(*), ROUND(100.0 * AVG(o2_7d), 1), ROUND(100.0 * AVG(o2_14d), 1),
       ROUND(100.0 * AVG(o2_28d), 1), ROUND(100.0 * AVG(o3_28d), 1)
FROM ladder;
