"""Build reproducible derived analysis tables from private CFBD cache/SQLite."""
import json
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DERIVED = ROOT / 'derived'

def seconds(value):
    if not isinstance(value, dict) or value.get('minutes') is None or value.get('seconds') is None:
        return np.nan
    return value['minutes']*60+value['seconds']

def main():
    DERIVED.mkdir(exist_ok=True)
    conn = sqlite3.connect(ROOT/'local'/'football.sqlite')
    conn.executescript((ROOT/'views.sql').read_text())
    print('Reading classified FBS plays...', flush=True)
    p = pd.read_sql_query('SELECT * FROM classified_plays WHERE fbs_game=1',conn)
    assert not p[['team_id','opponent_id']].isna().any().any(), 'Unmapped team names'
    p['team_id'] = p.team_id.astype(int)
    p['opponent_id'] = p.opponent_id.astype(int)
    p['game_date'] = pd.to_datetime(p.game_date,utc=True)
    p['local_date'] = p.game_date.dt.tz_convert('America/Chicago').dt.strftime('%Y-%m-%d')
    p = p.sort_values(['game_id','period','clock_s','drive_number','play_number','play_id'],ascending=[True,True,False,True,True,True]).reset_index(drop=True)
    p['row_order'] = p.groupby('game_id').cumcount()
    e = p[p.disposition=='eligible'].copy()
    groups = ['season','game_id','team_id','opponent_id','team','opponent','week','local_date','home_indicator']
    metrics = e.groupby(groups,dropna=False).agg(eligible_plays=('play_id','size'),ppa_n=('ppa','count'),mean_ppa=('ppa','mean'),ppa_sd=('ppa','std')).reset_index()
    metrics['ppa_coverage'] = metrics.ppa_n/metrics.eligible_plays
    metrics['chart_eligible'] = (metrics.ppa_n>=20)&(metrics.ppa_coverage>=0.9)
    metrics.sort_values(['season','team_id','local_date']).to_csv(DERIVED/'team_game_metrics.csv',index=False)
    audit = pd.read_sql_query('SELECT * FROM quality_audit',conn)
    audit.to_csv(DERIVED/'quality_audit.csv',index=False)
    raw_counts = pd.read_sql_query('SELECT season,count(*) AS raw_plays FROM plays GROUP BY season',conn)
    games = [json.loads(x[0]) for x in conn.execute('SELECT body FROM games')]
    team_members = {(s,i) for s,i in conn.execute('SELECT season,id FROM teams')}
    expected = [g for g in games if (g['season'],g['homeId']) in team_members and (g['season'],g['awayId']) in team_members and g.get('completed')]
    seen = set(p.game_id)
    missing = [dict(season=g['season'],game_id=g['id'],home=g['homeTeam'],away=g['awayTeam']) for g in expected if g['id'] not in seen]
    pd.DataFrame(missing,columns=['season','game_id','home','away']).to_csv(DERIVED/'games_missing_plays.csv',index=False)

    # Exact adjacent records, so dropped penalties/timeouts do not create false snap intervals.
    next_clock = p.groupby('game_id').clock_s.shift(-1)
    next_period = p.groupby('game_id').period.shift(-1)
    next_drive = p.groupby('game_id').drive_id.shift(-1)
    next_status = p.groupby('game_id').disposition.shift(-1)
    next_team = p.groupby('game_id').team_id.shift(-1)
    p['interval_s'] = p.clock_s-next_clock
    pairs = (p.disposition=='eligible')&(next_status=='eligible')&(p.drive_id==next_drive)&(p.team_id==next_team)&(p.period==next_period)&p.interval_s.between(0,80)
    # No text claim of in-bounds if the record does not explicitly identify a tackle.
    inbound = p.play_type.isin(['Rush','Pass Reception'])&p.play_text.str.contains('tackl',regex=False)&~p.play_text.str.contains(r'out.of.bounds|out-of-bounds|sideline|touchdown|1st down|first down',regex=True)
    pace = p[pairs&inbound].groupby(['season','team_id']).agg(clean_interval_n=('interval_s','size'),clean_seconds_per_snap=('interval_s','mean')).reset_index()

    # Drive outcomes/clock data remain private. Publish only aggregated team and game metrics.
    drives = pd.DataFrame([json.loads(body)|{'season':s} for s,body in conn.execute('SELECT season,body FROM drives')])
    if drives.empty:
        raise ValueError('Download drives first: python pipeline.py drives --seasons 2021 2022 2023')
    snap_counts = e.groupby(['drive_id','game_id','team_id','opponent_id','team','season']).agg(eligible_snaps=('play_id','size')).reset_index()
    ambiguous_ids = set(snap_counts.loc[snap_counts.duplicated(['drive_id','game_id','season'],keep=False),'drive_id'])
    snap_counts = snap_counts[~snap_counts.drive_id.isin(ambiguous_ids)]
    drives = drives.rename(columns={'id':'drive_id','gameId':'game_id'})
    d = snap_counts.merge(drives,on=['drive_id','game_id','season'],how='left',validate='one_to_one')
    d['elapsed_s'] = d.elapsed.map(seconds)
    d['points'] = d.driveResult.map({
        'TD':6,'PASSING TD':6,'RUSHING TD':6,'FG':3,'FG GOOD':3,
        'PUNT':0,'INT':0,'FUMBLE':0,'DOWNS':0,'SF':0,'END OF HALF':0,'END OF GAME':0,
        'END OF 4TH QUARTER':0,'MISSED FG':0,'FG MISSED':0,'BLOCKED FG':0,'BLOCKED PUNT':0,
        'INT TD':0,'INT RETURN TOUCH':0,'FUMBLE TD':0,'FUMBLE RETURN TD':0,
        'PUNT TD':0,'PUNT RETURN TD':0,'MISSED FG TD':0})
    garbage_drives = set(p.loc[p.disposition=='garbage_time','drive_id'])
    valid = d.startPeriod.between(1,4)&d.endPeriod.between(1,4)&~d.drive_id.isin(garbage_drives)&d.elapsed_s.between(1,900)&d.points.notna()
    valid &= ~((d.startPeriod<=2)&(d.endPeriod>=3))
    valid &= d.team.eq(d.offense)
    drive_audit = {'eligible_snap_drives_after_ambiguity_filter':len(d),'ambiguous_drive_ids_excluded':len(ambiguous_ids),'offense_mismatch_count':int((d.team!=d.offense).sum()),'missing_drive_records':int(d.driveResult.isna().sum()),'garbage_drive_count':int(d.drive_id.isin(garbage_drives).sum()),'unknown_result_counts':d.loc[d.points.isna(),'driveResult'].fillna('MISSING').value_counts().to_dict(),'valid_tempo_drives':int(valid.sum())}
    d = d[valid].copy()
    d['start_yards_to_goal'] = d.startYardsToGoal
    d[['season','drive_id','game_id','team_id','opponent_id','team','eligible_snaps','elapsed_s','points','start_yards_to_goal']].to_csv(ROOT/'local'/'drive_metrics.csv',index=False)
    d[['season','drive_id','game_id','team_id','opponent_id','team','eligible_snaps','elapsed_s','points','start_yards_to_goal']].to_sql('drive_metrics_clean',conn,if_exists='replace',index=False)
    conn.executescript('DROP VIEW IF EXISTS drive_metrics; CREATE VIEW drive_metrics AS SELECT * FROM drive_metrics_clean;')
    dg = d.groupby(['season','game_id','team_id','opponent_id','team']).agg(drives=('drive_id','size'),snaps=('eligible_snaps','sum'),possession_s=('elapsed_s','sum'),points=('points','sum'),start_yards_to_goal=('start_yards_to_goal','mean')).reset_index()
    dg['plays_per_minute'] = 60*dg.snaps/dg.possession_s
    dg['points_per_drive'] = dg.points/dg.drives
    dg.to_csv(DERIVED/'team_game_drives.csv',index=False)
    summary = dg.groupby(['season','team_id','team']).agg(drives=('drives','sum'),snaps=('snaps','sum'),possession_s=('possession_s','sum'),points=('points','sum'),games=('game_id','nunique')).reset_index()
    summary['plays_per_minute'] = 60*summary.snaps/summary.possession_s
    summary['points_per_drive'] = summary.points/summary.drives
    summary['plays_per_drive'] = summary.snaps/summary.drives
    summary['offense_rank'] = summary.groupby('season').points_per_drive.rank(method='first',ascending=False).astype(int)
    summary['offense_count'] = summary.groupby('season').team_id.transform('size')
    summary['offense_group'] = np.where(summary.offense_rank<=10,'Top 10',np.where(summary.offense_rank>summary.offense_count-50,'Bottom 50','Middle'))
    summary.merge(pace,on=['season','team_id'],how='left').to_csv(DERIVED/'team_season_metrics.csv',index=False)

    # Conversion on this snap; not eventual conversion later in a series.
    states = e[e.distance.gt(0)&e.yards_to_goal.between(0,100)&e.yards_gained.notna()].copy()
    states['distance_bucket'] = pd.cut(states.distance,[0,3,6,10,np.inf],labels=['1-3','4-6','7-10','11+']).astype(str)
    states['field_zone'] = pd.cut(states.yards_to_goal,[-1,20,50,100],labels=['Red zone','Opponent half','Own half']).astype(str)
    states['conversion'] = ((states.yards_gained>=states.distance)|states.play_type.isin(['Passing Touchdown','Rushing Touchdown']))&~states.play_type.isin(['Interception','Interception Return Touchdown','Pass Interception Return','Fumble Recovery (Opponent)','Fumble Return Touchdown','Safety'])
    keys = ['season','down','distance_bucket','field_zone']
    cells = states.groupby(keys+['team_id','team']).agg(snaps=('play_id','size'),conversions=('conversion','sum')).reset_index()
    totals = states.groupby(keys).agg(fbs_snaps=('play_id','size'),fbs_conversions=('conversion','sum')).reset_index()
    cells = cells.merge(totals,on=keys)
    cells['conversion_rate'] = cells.conversions/cells.snaps
    cells['fbs_other_rate'] = (cells.fbs_conversions-cells.conversions)/(cells.fbs_snaps-cells.snaps)
    cells['gap_pp'] = 100*(cells.conversion_rate-cells.fbs_other_rate)
    cells['display_eligible'] = (cells.snaps>=20)&((cells.fbs_snaps-cells.snaps)>=20)
    cells = cells.merge(summary[['season','team_id','offense_group']],on=['season','team_id'])
    cells.to_csv(DERIVED/'bottlenecks.csv',index=False)
    cohorts = cells.groupby(keys+['offense_group']).agg(snaps=('snaps','sum'),conversions=('conversions','sum')).reset_index()
    cohorts['conversion_rate'] = cohorts.conversions/cohorts.snaps
    cohorts.to_csv(DERIVED/'bottleneck_cohorts.csv',index=False)
    missing_join = conn.execute("SELECT count(*) FROM plays p LEFT JOIN games g ON g.id=json_extract(p.body,'$.gameId') WHERE g.id IS NULL").fetchone()[0]
    manifest = dict(raw_plays=int(raw_counts.raw_plays.sum()),seasons=raw_counts.to_dict('records'),eligible_plays=len(e),ppa_measured=int(e.ppa.count()),team_games=len(metrics),expected_completed_fbs_games=len(expected),observed_fbs_games=len(seen),missing_fbs_games=len(missing),unjoined_raw_plays=missing_join,drive_audit=drive_audit,clean_interval_count=int(pace.clean_interval_n.sum()))
    (DERIVED/'data_audit.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)
    conn.close()

if __name__=='__main__':
    main()
