"""Experiment sizing and break-even economics for produce-led vs gift-led onboarding.

Inputs that come from the simulated baseline are read from data/firstclub_sim.db.
Public inputs: ~170,000 households acquired in FirstClub's first year (TechCrunch, Jun 2026),
AOV ~INR 1,200. Assumptions (labelled): gift cost, produce credit, contribution margin.
"""
import math, os, sqlite3
import pandas as pd

here = os.path.dirname(os.path.abspath(__file__))
con = sqlite3.connect(os.path.join(here, '..', 'data', 'firstclub_sim.db'))
CUTOFF = '2026-10-25'
WEEKLY_NEW_BUYERS = 170_000 / 52          # public: 170K households in first year
AOV = 1200

o = pd.read_sql('select user_id, order_number, order_time, order_value from orders', con, parse_dates=['order_time'])
first = o[o.order_number == 1].set_index('user_id').order_time
o['days'] = (o.order_time - o.user_id.map(first)).dt.total_seconds() / 86400

def rate(nth, within, maturity):
    elig = first[first <= pd.Timestamp(CUTOFF) - pd.Timedelta(days=maturity)].index
    hit = o[(o.user_id.isin(elig)) & (o.order_number == nth) & (o.days <= within)].user_id.nunique()
    return hit / len(elig), len(elig)

p3_28, n28 = rate(3, 28, 28)            # primary metric baseline
p2_90, n90 = rate(2, 90, 90)
p3_90, _ = rate(3, 90, 90)

# ---- 1. Power analysis: two-sided two-proportion z-test, alpha 0.05, power 0.80 ----
z_a, z_b = 1.959964, 0.841621
rows = []
for mde in (3, 4, 5):
    p1, p2 = p3_28, p3_28 + mde / 100
    n = math.ceil((z_a + z_b) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2)
    enrol_weeks = 2 * n / WEEKLY_NEW_BUYERS
    rows.append(dict(min_detectable_lift_pts=mde, buyers_per_arm=n, total_buyers=2 * n,
                     enrolment_weeks=round(enrol_weeks, 1), total_weeks_incl_28d_window=round(enrol_weeks + 4, 1)))
power = pd.DataFrame(rows)

# ---- 2. Value of one extra "3rd order in 28 days" buyer: extra orders in their first 90 days ----
elig90 = first[first <= pd.Timestamp(CUTOFF) - pd.Timedelta(days=90)].index
x = o[o.user_id.isin(elig90) & (o.days <= 90)]
per = x.groupby('user_id').agg(orders=('order_number', 'max'))
reached = set(x[(x.order_number == 3) & (x.days <= 28)].user_id)
per['reached'] = per.index.isin(reached)
extra_orders = per[per.reached].orders.mean() - per[~per.reached].orders.mean()

# ---- 3. Break-even: incentive cost per buyer, and the lift each arm needs ----
rows = []
for gift in (100, 150, 200):              # assumed gift cost, INR
    for margin in (0.10, 0.15, 0.20):     # assumed contribution margin
        credit = 60                       # assumed produce credit on order 2, INR
        cost_control = gift * (1 + p2_90 + p3_90)          # gifts on orders 1-3
        cost_treat = gift * 1 + credit * p2_90              # gift on order 1 + credit on order 2
        saving = cost_control - cost_treat                  # INR saved per new buyer
        value_per_converter = extra_orders * AOV * margin   # INR of 90-day contribution
        breakeven_pts = -100 * saving / value_per_converter # lift needed to break even (negative = can afford a drop)
        rows.append(dict(gift_cost_inr=gift, margin_pct=int(margin * 100),
                         control_cost_per_buyer=round(cost_control), treatment_cost_per_buyer=round(cost_treat),
                         saving_per_buyer=round(saving), value_per_extra_converter=round(value_per_converter),
                         breakeven_lift_pts=round(breakeven_pts, 1)))
be = pd.DataFrame(rows)

os.makedirs(os.path.join(here, '..', 'results'), exist_ok=True)
power.to_csv(os.path.join(here, '..', 'results', '06_power_analysis.csv'), index=False)
be.to_csv(os.path.join(here, '..', 'results', '07_breakeven.csv'), index=False)
pd.DataFrame([dict(baseline_3rd_order_28d_pct=round(100 * p3_28, 1), buyers_28d_eligible=n28,
                   p2_90d_pct=round(100 * p2_90, 1), p3_90d_pct=round(100 * p3_90, 1), buyers_90d_eligible=n90,
                   extra_orders_90d_per_converter=round(extra_orders, 2),
                   weekly_new_buyers_public=round(WEEKLY_NEW_BUYERS))]).to_csv(
    os.path.join(here, '..', 'results', '08_inputs.csv'), index=False)

print('\n=== inputs ===')
print(f'baseline 3rd order in 28d: {100*p3_28:.1f}% (n={n28}) | 2nd in 90d {100*p2_90:.1f}% | 3rd in 90d {100*p3_90:.1f}% (n={n90})')
print(f'extra orders in 90d for a 3rd-order-in-28d buyer: {extra_orders:.2f} | weekly new buyers (public): {WEEKLY_NEW_BUYERS:,.0f}')
print('\n=== 06_power_analysis ===\n' + power.to_string(index=False))
print('\n=== 07_breakeven ===\n' + be.to_string(index=False))
