"""Dependency-free CFBD pilot. Run python pipeline.py --help."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import sqlite3
import statistics
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = 'https://api.collegefootballdata.com'

def api_key():
    key = os.environ.get('CFBD_API_KEY', '').strip()
    if key:
        return key
    env_file = ROOT / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            name, separator, value = line.strip().partition('=')
            if separator and name.strip() == 'CFBD_API_KEY':
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                return value.strip()
    return ''

def fetch(endpoint, params):
    query = urlencode(sorted(params.items()))
    cache = ROOT / 'raw' / (endpoint.strip('/').replace('/', '_') + '_' + hashlib.sha256(query.encode()).hexdigest()[:16] + '.json')
    if cache.exists():
        return json.loads(cache.read_text(encoding='utf-8'))['data']
    key = api_key()
    if not key:
        raise ValueError('Add CFBD_API_KEY to the local .env file or environment before downloading.')
    request = Request(BASE + endpoint + '?' + query, headers={'Authorization': 'Bearer ' + key})
    # Sequential, conservative requests. Stop on errors; no burst retries.
    time.sleep(1)
    with urlopen(request, timeout=90) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError('Expected an array from ' + endpoint)
    cache.parent.mkdir(exist_ok=True)
    temporary = cache.with_suffix('.tmp')
    temporary.write_text(json.dumps({'endpoint': endpoint, 'params': params, 'data': data}), encoding='utf-8')
    temporary.replace(cache)
    return data

def database(path):
    path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS games(id INTEGER PRIMARY KEY, season INTEGER, body TEXT);
    CREATE TABLE IF NOT EXISTS teams(season INTEGER, id INTEGER, body TEXT, PRIMARY KEY(season,id));
    CREATE TABLE IF NOT EXISTS plays(id TEXT PRIMARY KEY, season INTEGER, body TEXT);
    CREATE TABLE IF NOT EXISTS drives(id TEXT PRIMARY KEY, season INTEGER, body TEXT);
    ''')
    return conn

def ingest(conn, season):
    teams = fetch('/teams/fbs', {'year': season})
    games = fetch('/games', {'year': season, 'seasonType': 'regular'})
    for table, rows in [('teams', teams), ('games', games)]:
        for row in rows:
            if table == 'teams':
                conn.execute('INSERT OR REPLACE INTO teams VALUES(?,?,?)', (season, row['id'], json.dumps(row)))
            else:
                conn.execute('INSERT OR REPLACE INTO games VALUES(?,?,?)', (row['id'], season, json.dumps(row)))
    # Derive weeks from schedule, including week zero when present.
    for week in sorted({g['week'] for g in games}):
        plays = fetch('/plays', {'year': season, 'week': week, 'seasonType': 'regular'})
        conn.executemany('INSERT OR REPLACE INTO plays VALUES(?,?,?)', [(str(p['id']), season, json.dumps(p)) for p in plays])
        conn.commit()
        print(f'{season} week {week}: {len(plays)} records (cached or downloaded)')
    conn.commit()

def ingest_drives(conn, season):
    rows = fetch('/drives', {'year': season, 'seasonType': 'regular'})
    conn.executemany('INSERT OR REPLACE INTO drives VALUES(?,?,?)',
                     [(str(r['id']), season, json.dumps(r)) for r in rows])
    conn.commit()
    print(f'{season}: {len(rows)} drive records', flush=True)

def export(conn, folder):
    conn.executescript((ROOT / 'views.sql').read_text(encoding='utf-8'))
    folder.mkdir(exist_ok=True)
    for view in ['team_game_metrics', 'quality_audit']:
        cursor = conn.execute('SELECT * FROM ' + view)
        with (folder / (view + '.csv')).open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([d[0] for d in cursor.description])
            writer.writerows(cursor)

def signals(baseline, values):
    """Exploratory I chart and two-sided standardized CUSUM, fixed Phase I."""
    if len(baseline) < 8:
        raise ValueError('Need at least 8 baseline games; more are preferable.')
    mean = statistics.mean(baseline)
    sigma = statistics.mean(abs(b-a) for a, b in zip(baseline, baseline[1:])) / 1.128
    if sigma <= 0:
        raise ValueError('Baseline moving range is zero; cannot estimate limits.')
    positive = negative = 0.0
    result = []
    for i, value in enumerate(values):
        z = (value - mean) / sigma
        positive = max(0, positive + z - 0.5)
        negative = max(0, negative - z - 0.5)
        result.append({'index': i+1, 'mean_ppa': value, 'center': mean,
                       'lcl': mean-3*sigma, 'ucl': mean+3*sigma,
                       'outside_3sigma': abs(z)>3,
                       'cusum_positive': positive, 'cusum_negative': negative,
                       'cusum_signal': max(positive, negative)>5})
    return result

def write_rows(path, rows):
    if not rows:
        raise ValueError('No rows to write.')
    path.parent.mkdir(exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def demo():
    rng = random.Random(41)
    baseline = [rng.gauss(0.1, 0.08) for _ in range(24)]
    observations = [rng.gauss(0.1, 0.08) for _ in range(8)] + [rng.gauss(0.5, 0.08) for _ in range(8)]
    rows = signals(baseline, observations)
    for row in rows:
        row['data_kind'] = 'SYNTHETIC - NOT FOOTBALL EVIDENCE'
    write_rows(ROOT / 'demo' / 'synthetic_control_chart.csv', rows)
    print('Synthetic demo completed. No real football finding has been calculated.')

def analyze(args):
    with Path(args.metrics).open(encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r['team'] == args.team and r['mean_ppa'] != '' and int(r['ppa_n']) >= 20]
    rows.sort(key=lambda r: (r['game_date'], r['game_id']))
    baseline = [float(r['mean_ppa']) for r in rows if int(r['season']) == args.baseline_season]
    target = [r for r in rows if int(r['season']) == args.season]
    computed = signals(baseline, [float(r['mean_ppa']) for r in target])
    for row, source in zip(computed, target):
        row.update({k: source[k] for k in ['game_id', 'game_date', 'team', 'opponent', 'ppa_n']})
        row['post_change'] = source['game_date'][:10] > args.change_date
        row['status'] = 'EXPLORATORY UNADJUSTED; NOT CAUSAL'
    write_rows(ROOT / 'local' / 'control_chart.csv', computed)
    print(f'{len(baseline)} baseline games; {len(target)} target games; {sum(r["post_change"] for r in computed)} after change.')
    print('Opponent adjustment, dependence checks and placebo calibration are still required.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    pull = sub.add_parser('pull')
    pull.add_argument('--seasons', nargs='+', type=int, required=True)
    drives = sub.add_parser('drives')
    drives.add_argument('--seasons', nargs='+', type=int, required=True)
    study = sub.add_parser('analyze')
    study.add_argument('--metrics', default=str(ROOT / 'local' / 'team_game_metrics.csv'))
    study.add_argument('--team', required=True)
    study.add_argument('--baseline-season', type=int, required=True)
    study.add_argument('--season', type=int, required=True)
    study.add_argument('--change-date', required=True, help='YYYY-MM-DD announcement date; first later game is post-change')
    args = parser.parse_args()
    if args.command == 'demo':
        demo()
    elif args.command in ('pull', 'drives'):
        with database(ROOT / 'local' / 'football.sqlite') as conn:
            for season in args.seasons:
                if args.command == 'pull':
                    ingest(conn, season)
                else:
                    ingest_drives(conn, season)
            if args.command == 'pull':
                export(conn, ROOT / 'local')
    else:
        if args.baseline_season >= args.season:
            parser.error('Use an earlier season for the fixed baseline.')
        analyze(args)

if __name__ == '__main__':
    main()
