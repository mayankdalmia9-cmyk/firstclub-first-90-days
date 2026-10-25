-- 01_onboarding_funnel.sql  (SIMULATED DATA)
-- Install -> first order funnel: where do new users drop off, by city?
-- Users can browse without logging in; sign-up happens at checkout.
-- Each step counts users who reached it; conversion is vs the previous step.

WITH steps AS (
    SELECT u.user_id,
           u.city,
           MAX(f.event = 'Category Viewed')                                   AS browsed,   -- only possible if pincode is served
           MAX(f.event = 'Added to Cart')                                     AS added_to_cart,
           MAX(f.event = 'Signed Up')                                         AS signed_up,
           EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id)        AS first_order
    FROM users u
    LEFT JOIN funnel_events f USING (user_id)
    GROUP BY u.user_id, u.city
),
by_city AS (
    SELECT city, COUNT(*) AS installs, SUM(browsed) AS browsed, SUM(added_to_cart) AS carted,
           SUM(signed_up) AS signed_up, SUM(first_order) AS ordered
    FROM steps GROUP BY city
    UNION ALL
    SELECT 'All', COUNT(*), SUM(browsed), SUM(added_to_cart), SUM(signed_up), SUM(first_order)
    FROM steps
)
SELECT city,
       installs, browsed, carted, signed_up, ordered,
       ROUND(100.0 * browsed   / installs, 1)  AS pct_browse_of_installs,
       ROUND(100.0 * carted    / browsed, 1)   AS pct_cart_of_browse,
       ROUND(100.0 * signed_up / carted, 1)    AS pct_signup_of_cart,
       ROUND(100.0 * ordered   / signed_up, 1) AS pct_order_of_signup,
       ROUND(100.0 * ordered   / installs, 1)  AS pct_install_to_first_order
FROM by_city;
