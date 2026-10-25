"""Simulated onboarding event stream for a FirstClub-like quality-first grocery app.

EVERYTHING HERE IS SIMULATED. FirstClub's real data is not public. The simulation is
calibrated to (a) public FirstClub figures and (b) real habit patterns measured in the
84.51 Complete Journey grocery dataset (see ../README.md, "Calibration"). It exists to
build and test the tracking, SQL and experiment-readout pipeline, not to produce findings.

Outputs (in ../data):
  mixpanel_events.csv   one row per event, ready for Mixpanel CSV import
  firstclub_sim.db      SQLite: users, orders, funnel_events (same data, for SQL)

Usage:
  python sim/simulate.py                 # baseline (current gift-led onboarding)
  python sim/simulate.py --planted-test  # A/B test data with a PLANTED +4 pt effect,
                                         # used only to check the readout query recovers it
"""
import argparse, os, sqlite3
import numpy as np, pandas as pd

P = dict(
    seed=42,
    n_installs=20000,
    start='2026-06-29', weeks=12,              # installs spread over 12 weeks
    observe_until='2026-10-25',                # data cut-off
    # --- acquisition mix & funnel (assumptions, labelled in README) ---
    channels={'organic': .35, 'performance_ads': .35, 'referral': .20, 'offline': .10},
    channel_first_order_lift={'organic': 1.0, 'performance_ads': .85, 'referral': 1.25, 'offline': 1.05},
    localities={  # name: (city, share, serviceable probability)
        'Indiranagar': ('Bengaluru', .13, .97), 'Koramangala': ('Bengaluru', .14, .97),
        'HSR Layout': ('Bengaluru', .12, .95), 'Whitefield': ('Bengaluru', .12, .85),
        'JP Nagar': ('Bengaluru', .09, .90), 'Hebbal': ('Bengaluru', .08, .80),
        'Jayanagar': ('Bengaluru', .08, .92), 'Sarjapur Road': ('Bengaluru', .09, .75),
        'Gachibowli': ('Hyderabad', .07, .55), 'Jubilee Hills': ('Hyderabad', .04, .50),
        'Kondapur': ('Hyderabad', .04, .45)},
    p_signup=.74, p_browse=.93, p_add_to_cart=.62, p_first_order=.70,
    categories=['Fruits & Vegetables', 'Dairy & Eggs', 'Bakery', 'Staples', 'Snacks & Beverages'],
    # --- repeat behaviour (calibrated: ~70% place a 2nd order; active users ~4+ orders/month) ---
    rate_mean_per_week=0.75,      # latent order rate of an engaged household
    rate_shape=1.6,               # spread of household order rates (Gamma shape)
    weekly_churn_new=.16,         # chance of drifting away each week before habit forms
    weekly_churn_habit=.025,      # ... after the 3rd order (habit formed)
    p_produce_first=.62,          # share of first orders containing fresh produce
    produce_rate_boost=1.12,      # produce buyers order a little more often (direction from real data)
    aov_mean=1200, aov_sigma=.45, # order value: lognormal, mean ~INR 1,200 (public figure)
    gift_cost=150,                # assumed cost of a first-orders gift, INR
    gift_orders=3,                # current onboarding: gifts on orders 1-3 (public reviews)
    planted_effect_pp=4.0,        # documentation only: the planted effect size (see churn_new line)
)

def simulate(planted_test=False, out_dir=None):
    rng = np.random.default_rng(P['seed'] + (1 if planted_test else 0))
    start = pd.Timestamp(P['start']); end = pd.Timestamp(P['observe_until'])
    n = P['n_installs']
    loc_names = list(P['localities']); loc_share = np.array([P['localities'][l][1] for l in loc_names])
    users = pd.DataFrame({
        'user_id': [f'u{i:05d}' for i in range(n)],
        'install_time': start + pd.to_timedelta(rng.uniform(0, P['weeks'] * 7, n), unit='D'),
        'channel': rng.choice(list(P['channels']), n, p=list(P['channels'].values())),
        'locality': rng.choice(loc_names, n, p=loc_share / loc_share.sum()),
    })
    users['city'] = users.locality.map(lambda l: P['localities'][l][0])
    users['install_week'] = ((users.install_time - start).dt.days // 7 + 1).astype(int)
    users['arm'] = 'baseline'
    if planted_test:
        users['arm'] = rng.choice(['control_gift_led', 'treatment_produce_led'], n)

    events, orders = [], []
    def ev(uid, t, name, **props):
        events.append(dict(event=name, distinct_id=uid, time=t, **props))

    for u in users.itertuples(index=False):
        t = u.install_time
        ev(u.user_id, t, 'App Installed', channel=u.channel, city=u.city, locality=u.locality)
        t += pd.Timedelta(minutes=rng.uniform(1, 10))
        serviceable = rng.random() < P['localities'][u.locality][2]
        ev(u.user_id, t, 'Location Checked', locality=u.locality, serviceable=bool(serviceable))
        if not serviceable:
            if rng.random() < .35:
                ev(u.user_id, t + pd.Timedelta(minutes=1), 'Waitlist Joined', locality=u.locality)
            continue
        if rng.random() > P['p_browse']:
            continue
        cat = rng.choice(P['categories'], p=[.38, .2, .14, .16, .12])
        t += pd.Timedelta(minutes=rng.uniform(1, 6))
        ev(u.user_id, t, 'Category Viewed', category=cat)
        if rng.random() > P['p_add_to_cart']:
            continue
        t += pd.Timedelta(minutes=rng.uniform(1, 8))
        ev(u.user_id, t, 'Added to Cart', category=cat)
        if rng.random() > P['p_signup']:          # sign-up is asked at checkout (browse without login)
            continue
        ev(u.user_id, t + pd.Timedelta(minutes=1), 'Signed Up', channel=u.channel)
        if rng.random() > min(.95, P['p_first_order'] * P['channel_first_order_lift'][u.channel]):
            continue

        # ---- first and repeat orders ----
        produce_first = rng.random() < P['p_produce_first']
        rate = rng.gamma(P['rate_shape'], P['rate_mean_per_week'] / P['rate_shape'])
        rate *= P['produce_rate_boost'] if produce_first else 1.0
        churn_new = P['weekly_churn_new']
        if planted_test and u.arm == 'treatment_produce_led':
            churn_new *= 0.72   # planted: lower early churn in treatment; equals ~+4 pts on 3rd order in 28d (checked on an 80K-user run)
        t_order = t + pd.Timedelta(minutes=rng.uniform(2, 15))
        k = 0
        while t_order <= end:
            k += 1
            has_produce = produce_first if k == 1 else rng.random() < .55 + .1 * produce_first
            value = float(np.round(rng.lognormal(np.log(P['aov_mean']) - P['aov_sigma'] ** 2 / 2, P['aov_sigma']), 0))
            gift = (k <= P['gift_orders']) if u.arm != 'treatment_produce_led' else (k == 1)
            nudge = (u.arm == 'treatment_produce_led' and k == 2)
            props = dict(order_number=k, order_value=value, items=int(max(1, rng.poisson(10))),
                         has_produce=bool(has_produce), gift_applied=bool(gift),
                         produce_credit_applied=bool(nudge), arm=u.arm)
            ev(u.user_id, t_order, 'Order Placed', **props)
            orders.append(dict(user_id=u.user_id, order_time=t_order, **props))
            # time to next order: exponential gap, with weekly churn checks
            gap_days = rng.exponential(7 / rate)
            churn = churn_new if k < 3 else P['weekly_churn_habit']
            if rng.random() < 1 - (1 - churn) ** max(gap_days / 7, .5):
                break
            t_order += pd.Timedelta(days=gap_days)

    ev_df = pd.DataFrame(events).sort_values('time').reset_index(drop=True)
    od = pd.DataFrame(orders)
    out_dir = out_dir or os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(out_dir, exist_ok=True)
    suffix = '_planted_test' if planted_test else ''
    con = sqlite3.connect(os.path.join(out_dir, f'firstclub_sim{suffix}.db'))
    u_out = users.copy(); u_out['install_time'] = u_out.install_time.dt.strftime('%Y-%m-%d %H:%M:%S')
    u_out.to_sql('users', con, if_exists='replace', index=False)
    o_out = od.copy(); o_out['order_time'] = o_out.order_time.dt.strftime('%Y-%m-%d %H:%M:%S')
    o_out.to_sql('orders', con, if_exists='replace', index=False)
    f_out = ev_df[ev_df.event != 'Order Placed'][['event', 'distinct_id', 'time']].copy()
    f_out['time'] = f_out.time.dt.strftime('%Y-%m-%d %H:%M:%S'); f_out.columns = ['event', 'user_id', 'event_time']
    f_out.to_sql('funnel_events', con, if_exists='replace', index=False)
    con.close()
    if not planted_test:   # Mixpanel file: unix-seconds time, IST-free UTC timestamps
        mp = ev_df.copy()
        mp['time'] = (mp.time - pd.Timestamp('1970-01-01')) // pd.Timedelta('1s')
        mp['$insert_id'] = [f'e{i:07d}' for i in range(len(mp))]
        for c in ('order_number', 'items'):
            mp[c] = mp[c].astype('Int64')
        for c in ('serviceable', 'has_produce', 'gift_applied', 'produce_credit_applied'):
            mp[c] = mp[c].map({True: 'true', False: 'false'})
        mp.to_csv(os.path.join(out_dir, 'mixpanel_events.csv'), index=False)
    return users, od, ev_df

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--planted-test', action='store_true')
    a = ap.parse_args()
    users, od, ev_df = simulate(planted_test=a.planted_test)
    buyers = od.user_id.nunique()
    per_user = od.groupby('user_id').order_number.max()
    print(f'installs {len(users):,} | first-order buyers {buyers:,} | orders {len(od):,} | events {len(ev_df):,}')
    print(f'2nd order (any time) {100 * (per_user >= 2).mean():.1f}% | AOV INR {od.order_value.mean():,.0f}')
