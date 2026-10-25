-- 05_experiment_readout.sql  (runs on data/firstclub_sim_planted_test.db)
-- A/B readout: control (gift-led) vs treatment (produce-led) on the primary metric,
-- % of first-time buyers placing a 3rd order within 28 days, with a 95% confidence interval.
-- VALIDATION ONLY: the test data has a PLANTED +4 pt effect. The point is to check that this
-- query recovers it, so the same query can be trusted on a real test.

WITH firsts AS (
    SELECT user_id, arm, MIN(order_time) AS first_time
    FROM orders GROUP BY user_id, arm
),
eligible AS (
    SELECT * FROM firsts WHERE julianday(first_time) <= julianday('2026-10-25') - 28
),
outcome AS (
    SELECT e.user_id, e.arm,
           MAX(o.order_number = 3 AND julianday(o.order_time) - julianday(e.first_time) <= 28) AS o3_28d,
           SUM(o.gift_applied) * 150 + SUM(o.produce_credit_applied) * 60                     AS incentive_cost_inr
    FROM eligible e JOIN orders o USING (user_id)
    GROUP BY e.user_id, e.arm
),
arms AS (
    SELECT arm, COUNT(*) AS n, AVG(o3_28d) AS p, AVG(incentive_cost_inr) AS cost
    FROM outcome GROUP BY arm
),
c AS (SELECT * FROM arms WHERE arm = 'control_gift_led'),
t AS (SELECT * FROM arms WHERE arm = 'treatment_produce_led')
SELECT c.n                                             AS control_buyers,
       t.n                                             AS treatment_buyers,
       ROUND(100 * c.p, 1)                             AS control_3rd_order_28d_pct,
       ROUND(100 * t.p, 1)                             AS treatment_3rd_order_28d_pct,
       ROUND(100 * (t.p - c.p), 1)                     AS lift_pct_points,
       ROUND(100 * ((t.p - c.p) - 1.96 * sqrt(c.p * (1 - c.p) / c.n + t.p * (1 - t.p) / t.n)), 1) AS ci95_low,
       ROUND(100 * ((t.p - c.p) + 1.96 * sqrt(c.p * (1 - c.p) / c.n + t.p * (1 - t.p) / t.n)), 1) AS ci95_high,
       ROUND(c.cost, 0)                                AS control_incentive_cost_per_buyer_inr,
       ROUND(t.cost, 0)                                AS treatment_incentive_cost_per_buyer_inr
FROM c, t;
