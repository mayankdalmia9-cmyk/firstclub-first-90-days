-- 04_gift_cost.sql  (SIMULATED DATA; gift cost of INR 150 is an assumption)
-- What does the current gift-led onboarding (gifts on orders 1-3) cost,
-- and how much of it goes to buyers who never reach a 3rd order?

WITH g AS (
    SELECT user_id,
           SUM(gift_applied)                       AS gifts,
           MAX(order_number)                       AS orders_placed
    FROM orders
    GROUP BY user_id
)
SELECT COUNT(*)                                                      AS first_time_buyers,
       SUM(gifts)                                                    AS gifts_given,
       SUM(gifts) * 150                                              AS gift_cost_inr,
       ROUND(1.0 * SUM(gifts) * 150 / COUNT(*), 0)                   AS gift_cost_per_buyer_inr,
       SUM(orders_placed >= 3)                                       AS buyers_reaching_3rd_order,
       ROUND(1.0 * SUM(gifts) * 150 / SUM(orders_placed >= 3), 0)    AS gift_cost_per_3rd_order_buyer_inr,
       ROUND(100.0 * SUM(CASE WHEN orders_placed < 3 THEN gifts ELSE 0 END) / SUM(gifts), 1)
                                                                     AS pct_gift_spend_on_buyers_who_stop_before_3rd
FROM g;
