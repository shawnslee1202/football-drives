"""Summarize the completed local pilot without exposing raw plays or credentials."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    conn = sqlite3.connect(ROOT / 'local' / 'football.sqlite')
    counts = conn.execute('SELECT season,count(*) FROM plays GROUP BY season').fetchall()
    with (ROOT / 'local' / 'team_game_metrics.csv').open(encoding='utf-8') as f:
        metrics = list(csv.DictReader(f))
    with (ROOT / 'local' / 'control_chart.csv').open(encoding='utf-8') as f:
        chart = list(csv.DictReader(f))
    with (ROOT / 'local' / 'quality_audit.csv').open(encoding='utf-8') as f:
        audit = list(csv.DictReader(f))
    dispositions = {}
    for row in audit:
        dispositions[row['disposition']] = dispositions.get(row['disposition'],0)+int(row['records'])
    post = [r for r in chart if r['post_change']=='True']
    lines = ['# Texas A&M pilot: real-data run', '',
             '**Exploratory, unadjusted results. This is not a causal conclusion or the completed study.**', '',
             f'The 2023 series contains {len(chart)} eligible team-games, with {len(post)} after the November 12 coaching announcement. The planned minimum follow-up is four games; fewer means insufficient follow-up for the proposed study.', '',
             '## Download and cleaning', '', '| Season | Raw play records |', '|---|---:|']
    for season, count in counts:
        lines.append(f'| {season} | {count:,} |')
    lines.extend(['', f'Exported {len(metrics):,} team-game rows across both seasons.', '',
                  '| Cleaning disposition | Records |', '|---|---:|'])
    for name, count in sorted(dispositions.items()):
        lines.append(f'| {name} | {count:,} |')
    lines.extend(['', 'Raw counts include records outside the study scope. Filters are sequential, so each excluded record has one first exclusion reason.', '',
                  '## Texas A&M: 2023', '',
                  '| Game date (UTC) | Opponent | PPA observations | Mean PPA | Beyond 3 sigma | CUSUM alarm | After change |',
                  '|---|---|---:|---:|---|---|---|'])
    for r in chart:
        lines.append(f'| {r["game_date"][:10]} | {r["opponent"]} | {r["ppa_n"]} | {float(r["mean_ppa"]):.3f} | {r["outside_3sigma"]} | {r["cusum_signal"]} | {r["post_change"]} |')
    baseline = [r for r in metrics if r['team']=='Texas A&M' and r['season']=='2022' and int(r['ppa_n'])>=20]
    lines.extend(['', f'Fixed baseline: {len(baseline)} eligible 2022 games. Center = {float(chart[0]["center"]):.3f} PPA; limits = [{float(chart[0]["lcl"]):.3f}, {float(chart[0]["ucl"]):.3f}].', '',
                  '## Interpretation and remaining work', '',
                  'An alarm is a diagnostic flag, not proof of a coaching effect. No alarm does not establish that nothing changed. CUSUM runs across the full target season and retains its accumulated state after an alarm.', '',
                  'Opponent adjustment, baseline stability, sample-size/dependence checks, matched placebo calibration, and a broader intervention sample remain unfinished. Prior-season personnel and staff changes can affect comparability.', '',
                  'Cleaning uses the preceding observed score in game order because sampled scoring records contain post-play scores. Missing records and tied-clock ordering can still affect this reconstruction. Kneels/spikes and special-teams descriptions are filtered with text rules that need broader validation.', '',
                  'Data provided by [CollegeFootballData.com](https://collegefootballdata.com). Intervention source: [Texas A&M announcement](https://12thman.com/news/2023/11/12/texas-am-athletics-announces-change-in-football-leadership).'])
    (ROOT / 'pilot-results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))
    conn.close()

if __name__ == '__main__':
    main()
