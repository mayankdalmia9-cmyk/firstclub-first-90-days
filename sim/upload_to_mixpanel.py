"""Upload data/mixpanel_events.csv (SIMULATED events) to your own Mixpanel project.

Uses Mixpanel's /import API with your project token. Standard library only.

    python sim/upload_to_mixpanel.py YOUR_PROJECT_TOKEN            # US data residency (default)
    python sim/upload_to_mixpanel.py YOUR_PROJECT_TOKEN --region in  # if your project is in India residency

Find the token in Mixpanel: Settings (gear) > Project Settings > Access Keys > Project Token.
"""
import argparse, base64, csv, gzip, json, os, time, urllib.request, urllib.error

HOSTS = {'us': 'api.mixpanel.com', 'eu': 'api-eu.mixpanel.com', 'in': 'api-in.mixpanel.com'}
NUMERIC = {'order_number': int, 'items': int, 'order_value': float, 'time': int}
BOOL = {'serviceable', 'has_produce', 'gift_applied', 'produce_credit_applied'}

def rows(path):
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            props = {'distinct_id': r.pop('distinct_id'), 'time': int(r.pop('time')),
                     '$insert_id': r.pop('$insert_id'), 'data_source': 'simulated'}
            name = r.pop('event')
            for k, v in r.items():
                if v == '':
                    continue
                if k in NUMERIC:
                    v = NUMERIC[k](float(v))
                elif k in BOOL:
                    v = (v == 'true')
                props[k] = v
            yield {'event': name, 'properties': props}

def send(batch, token, host):
    body = gzip.compress(json.dumps(batch).encode())
    auth = base64.b64encode(f'{token}:'.encode()).decode()
    req = urllib.request.Request(f'https://{host}/import?strict=1', data=body, method='POST', headers={
        'Content-Type': 'application/json', 'Content-Encoding': 'gzip', 'Authorization': f'Basic {auth}'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** (attempt + 1)); continue
            raise SystemExit(f'Mixpanel rejected the batch ({e.code}): {e.read().decode()[:500]}')
    raise SystemExit('Too many retries (rate limited). Try again in a minute.')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('--region', default='us', choices=HOSTS)
    a = ap.parse_args()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'mixpanel_events.csv')
    batch, sent = [], 0
    for ev in rows(path):
        batch.append(ev)
        if len(batch) == 2000:
            send(batch, a.token, HOSTS[a.region]); sent += len(batch); batch = []
            print(f'sent {sent:,} events', end='\r')
    if batch:
        send(batch, a.token, HOSTS[a.region]); sent += len(batch)
    print(f'\nDone: {sent:,} simulated events imported. They may take a few minutes to appear.')
