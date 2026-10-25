"""Descriptive tempo model; no causal interpretation."""
import json
from pathlib import Path
import pandas as pd
import statsmodels.formula.api as smf

ROOT=Path(__file__).resolve().parent

def main():
    d=pd.read_csv(ROOT/'derived'/'team_game_drives.csv')
    games=pd.read_csv(ROOT/'derived'/'team_game_metrics.csv')
    d=d.merge(games[['game_id','team_id','home_indicator']],on=['game_id','team_id'],validate='one_to_one')
    d=d[(d.drives>=5)&d.start_yards_to_goal.notna()].copy()
    model=smf.wls('points_per_drive ~ plays_per_minute + start_yards_to_goal + home_indicator + C(season) + C(team_id) + C(opponent_id)',data=d,weights=d.drives).fit(cov_type='cluster',cov_kwds={'groups':d.game_id})
    ci=model.conf_int().loc['plays_per_minute']
    result={'n_team_games':int(model.nobs),'n_games':int(d.game_id.nunique()),'tempo_coefficient':float(model.params['plays_per_minute']),
            'ci_low':float(ci.iloc[0]),'ci_high':float(ci.iloc[1]),'clustered_se':float(model.bse['plays_per_minute']),
            'r_squared':float(model.rsquared),'interpretation':'Descriptive association in points per drive (TD=6; FG=3; no conversions) per additional eligible snap per possession minute. Controls: offense, defense, season, field position and home field. Clustered by game. Not a causal tempo effect.'}
    (ROOT/'derived'/'tempo_model.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (ROOT/'derived'/'tempo_model.txt').write_text(model.summary().as_text(),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
