"""Regenerate the simulated data and run every SQL file. Results go to results/*.csv.

    python run_all.py
"""
import glob, os, sqlite3, subprocess, sys
import pandas as pd

pd.set_option('display.width', 220)
here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
subprocess.run([sys.executable, 'sim/simulate.py'], check=True)
subprocess.run([sys.executable, 'sim/simulate.py', '--planted-test'], check=True)
os.makedirs('results', exist_ok=True)

for path in sorted(glob.glob('sql/*.sql')):
    db = 'data/firstclub_sim_planted_test.db' if 'readout' in path else 'data/firstclub_sim.db'
    con = sqlite3.connect(db)
    body = '\n'.join(l for l in open(path).read().splitlines() if not l.strip().startswith('--'))
    df = pd.read_sql(body.strip().rstrip(';'), con)
    name = os.path.splitext(os.path.basename(path))[0]
    df.to_csv(f'results/{name}.csv', index=False)
    print(f'\n=== {name} ===\n{df.to_string(index=False)}')

subprocess.run([sys.executable, 'analysis/power_and_breakeven.py'], check=True)
