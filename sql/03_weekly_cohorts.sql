-- 03_weekly_cohorts.sql  (SIMULATED DATA)
-- Weekly cohort retention: group buyers by the week of their first order, then measure the
-- share who ordered again in each later week. Cells past the data cut-off are left out.

WITH firsts AS (
    SELECT user_id, MIN(order_time) AS first_time,
           CAST((julianday(MIN(order_time)) - julianday('2026-06-29')) / 7 AS INT) + 1 AS cohort_week
    FROM orders GROUP BY user_id
),
activity AS (
    SELECT DISTINCT f.user_id, f.cohort_week,
           CAST((julianday(o.order_time) - julianday(f.first_time)) / 7 AS INT) AS weeks_since_first
    FROM orders o JOIN firsts f USING (user_id)
),
size AS (SELECT cohort_week, COUNT(*) AS buyers FROM firsts GROUP BY cohort_week)
SELECT a.cohort_week,
       s.buyers                                      AS cohort_size,
       a.weeks_since_first,
       COUNT(*)                                      AS active_buyers,
       ROUND(100.0 * COUNT(*) / s.buyers, 1)         AS pct_active
FROM activity a JOIN size s USING (cohort_week)
WHERE a.weeks_since_first BETWEEN 0 AND 12
  AND a.cohort_week <= 12
  AND julianday('2026-06-29') + 7 * (a.cohort_week + a.weeks_since_first + 1) <= julianday('2026-10-25')   -- week fully observed for the whole cohort
GROUP BY a.cohort_week, a.weeks_since_first
ORDER BY a.cohort_week, a.weeks_since_first;
