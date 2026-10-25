"""Retrospective ten-case SPC study; rules fixed in PROTOCOL.md."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'derived'
SEED = 20261022

def weco(z):
    z = np.asarray(z,dtype=float)
    rows = []
    for i,v in enumerate(z):
        r1 = abs(v)>3
        r2 = i>=2 and any(np.sum(s*z[i-2:i+1]>2)>=2 for s in [1,-1])
        r3 = i>=4 and any(np.sum(s*z[i-4:i+1]>1)>=4 for s in [1,-1])
        r4 = i>=7 and any(np.all(s*z[i-7:i+1]>0) for s in [1,-1])
        rows.append([r1,r2,r3,r4])
    return np.array(rows,dtype=bool).reshape((-1,4))

def control(baseline, values, sigma_method='mr',h=5):
    b = np.asarray(baseline,dtype=float)
    y = np.asarray(values,dtype=float)
    if len(b)<8 or not np.isfinite(b).all() or not np.isfinite(y).all():
        raise ValueError('Invalid or insufficient baseline')
    center = b.mean()
    mr_bar = np.abs(np.diff(b)).mean()
    sigma = mr_bar/1.128 if sigma_method=='mr' else b.std(ddof=1)
    if sigma<=1e-10:
        raise ValueError('Degenerate baseline')
    z = (y-center)/sigma
    rules = weco(z)
    cp=cm=0.0
    rows=[]
    for i,value in enumerate(y):
        cp=max(0,cp+z[i]-0.5)
        cm=max(0,cm-z[i]-0.5)
        rows.append(dict(game_index=i+1,value=value,z=z[i],center=center,sigma=sigma,lcl=center-3*sigma,ucl=center+3*sigma,
                         mr=np.nan if i==0 else abs(value-y[i-1]),mr_center=mr_bar,mr_ucl=3.267*mr_bar,
                         we1=bool(rules[i,0]),we2=bool(rules[i,1]),we3=bool(rules[i,2]),we4=bool(rules[i,3]),
                         weco_alarm=bool(rules[i].any()),cusum_positive=cp,cusum_negative=cm,cusum_alarm=max(cp,cm)>h))
    result=pd.DataFrame(rows)
    result['combined_alarm']=result.weco_alarm|result.cusum_alarm
    return result,dict(center=float(center),sigma=float(sigma),baseline_weco_alarms=int(weco((b-center)/sigma).any(axis=1).sum()),baseline_n=len(b))

def first_alarm(frame,column):
    indices=np.flatnonzero(frame[column].to_numpy())
    return int(indices[0]) if len(indices) else None

def classify(frame,post_index):
    first=first_alarm(frame,'combined_alarm')
    enough=len(frame)-post_index>=4
    return dict(followup_n=len(frame)-post_index,main_eligible=enough,
                preexisting_alarm=first is not None and first<post_index,
                new_alarm=bool(enough and first is not None and post_index<=first<post_index+4),
                first_alarm_index=first)

class Adjuster:
    def __init__(self,metrics):
        self.metrics=metrics
        self.cache={}

    def fit(self,season,team_id):
        key=(season,team_id)
        if key in self.cache:
            return self.cache[key]
        train=self.metrics[(self.metrics.season==season-1)&(self.metrics.team_id!=team_id)&self.metrics.chart_eligible].copy()
        offense=sorted(train.team_id.unique())
        defense=sorted(train.opponent_id.unique())
        # Drop one level per factor and use an intercept; no penalization.
        X=np.column_stack([np.ones(len(train)),train.home_indicator.to_numpy()]+
                          [(train.team_id==x).to_numpy(dtype=float) for x in offense[1:]]+
                          [(train.opponent_id==x).to_numpy(dtype=float) for x in defense[1:]])
        root_w=np.sqrt(train.ppa_n.to_numpy(dtype=float))
        beta,_,rank,_=np.linalg.lstsq(X*root_w[:,None],train.mean_ppa.to_numpy()*root_w,rcond=None)
        effects={int(defense[0]):0.0}
        start=2+len(offense)-1
        effects.update({int(d):float(beta[start+i]) for i,d in enumerate(defense[1:])})
        fit=dict(effects=effects,home=float(beta[1]),training_n=len(train),rank=int(rank),columns=X.shape[1],
                 train_rmse=float(np.sqrt(np.average((train.mean_ppa-X@beta)**2,weights=train.ppa_n))))
        if rank<X.shape[1]:
            raise ValueError(f'Unidentified fixed effects for {key}: rank {rank}/{X.shape[1]}')
        self.cache[key]=fit
        return fit

    def series(self,season,team_id,min_plays=20):
        fit=self.fit(season,team_id)
        rows=self.metrics[(self.metrics.team_id==team_id)&self.metrics.season.isin([season-1,season])&self.metrics.chart_eligible&(self.metrics.ppa_n>=min_plays)].copy()
        rows['defense_adjustment']=rows.opponent_id.map(fit['effects'])
        unknown=int(rows.defense_adjustment.isna().sum())
        rows=rows.dropna(subset=['defense_adjustment']).sort_values(['local_date','game_id'])
        rows['adjusted_ppa']=rows.mean_ppa-rows.defense_adjustment-fit['home']*rows.home_indicator
        return rows[rows.season==season-1].reset_index(drop=True),rows[rows.season==season].reset_index(drop=True),fit,unknown

def bootstrap_delta(b,y,seed):
    rng=np.random.default_rng(seed)
    deltas=rng.choice(y,(2000,len(y)),replace=True).mean(axis=1)-rng.choice(b,(2000,len(b)),replace=True).mean(axis=1)
    return float(np.mean(y)-np.mean(b)),*map(float,np.quantile(deltas,[0.025,0.975]))

def wilson(k,n):
    p=k/n; z=1.96; denom=1+z*z/n
    mid=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return [mid-half,mid+half]

def run():
    metrics=pd.read_csv(OUT/'team_game_metrics.csv')
    cases=pd.read_csv(ROOT/'interventions.csv')
    adjust=Adjuster(metrics)
    results=[]; points=[]; base_points=[]; sensitivities=[]
    for ci,case in cases.iterrows():
        ids=metrics.loc[(metrics.team==case.team)&(metrics.season==case.season),'team_id'].unique()
        if len(ids)!=1:
            raise ValueError(f'Cannot resolve case team ID: {case.team}')
        team_id=int(ids[0])
        b,t,fit,unknown=adjust.series(int(case.season),team_id)
        post=int((t.local_date<=case.change_date).sum())
        chart,ref=control(b.adjusted_ppa,t.adjusted_ppa)
        outcome=classify(chart,post)
        delta,lo,hi=bootstrap_delta(b.adjusted_ppa.to_numpy(),t.adjusted_ppa.to_numpy()[post:post+4],SEED+ci)
        if len(t)-post<4:
            lo=hi=float('nan')
        cfirst=first_alarm(chart,'cusum_alarm')
        wfirst=first_alarm(chart,'weco_alarm')
        rows=dict(case_id=case.case_id,team=case.team,team_id=team_id,season=int(case.season),change_date=case.change_date,
                  first_affected_date=t.iloc[post].local_date,first_affected_week=int(t.iloc[post].week),
                  prechange_n=post,target_n=len(t),**ref,**outcome,adjusted_delta=delta,delta_ci_low=lo,delta_ci_high=hi,
                  all_followup_delta=float(t.adjusted_ppa.iloc[post:].mean()-b.adjusted_ppa.mean()),
                  first_cusum_date='' if cfirst is None else t.iloc[cfirst].local_date,
                  first_cusum_week=None if cfirst is None else int(t.iloc[cfirst].week),
                  cusum_delay_games=None if cfirst is None else cfirst-post,
                  cusum_near_change=bool(cfirst is not None and abs(cfirst-post)<=1),
                  first_weco_date='' if wfirst is None else t.iloc[wfirst].local_date,
                  unknown_opponent_games=unknown,model_train_n=fit['training_n'],model_rank=fit['rank'],model_columns=fit['columns'],source_url=case.source_url)
        rows['status']='insufficient follow-up' if not outcome['main_eligible'] else ('preexisting alarm' if outcome['preexisting_alarm'] else ('new post-change alarm' if outcome['new_alarm'] else 'no new alarm'))
        results.append(rows)
        chart=pd.concat([t.reset_index(drop=True),chart],axis=1)
        chart['case_id']=case.case_id
        chart['post_change']=chart.index>=post
        chart['primary_window']=(chart.index>=post)&(chart.index<post+4)
        points.append(chart)
        b=b.copy(); b['case_id']=case.case_id
        b['center']=ref['center']; b['sigma']=ref['sigma']; b['z']=(b.adjusted_ppa-ref['center'])/ref['sigma']
        b['weco_alarm']=weco(b.z).any(axis=1)
        base_points.append(b)
        for name,column,sigma,h,nmin in [('raw','mean_ppa','mr',5,20),('sample_sd','adjusted_ppa','sd',5,20),('cusum_h4','adjusted_ppa','mr',4,20),('cusum_h6','adjusted_ppa','mr',6,20),('min40','adjusted_ppa','mr',5,40)]:
            bb,tt,_,_=adjust.series(int(case.season),team_id,nmin)
            try:
                cc,rr=control(bb[column],tt[column],sigma,h)
                pp=int((tt.local_date<=case.change_date).sum())
                ss=classify(cc,pp)
                sensitivities.append(dict(case_id=case.case_id,variant=name,**ss,baseline_n=len(bb),target_n=len(tt)))
            except ValueError:
                sensitivities.append(dict(case_id=case.case_id,variant=name,main_eligible=False,baseline_n=len(bb),target_n=len(tt)))
        print(f'{case.team} {case.season}: {rows["status"]}; baseline {len(b)}, follow-up {len(t)-post}',flush=True)
    result=pd.DataFrame(results)
    result.to_csv(OUT/'case_results.csv',index=False)
    pd.concat(points,ignore_index=True).to_csv(OUT/'control_chart_points.csv',index=False)
    pd.concat(base_points,ignore_index=True).to_csv(OUT/'baseline_points.csv',index=False)
    pd.DataFrame(sensitivities).to_csv(OUT/'sensitivity.csv',index=False)

    # Selection uses only identity/calendar/sample sizes, never efficiency or alarms.
    rng=np.random.default_rng(SEED)
    banned=set(zip(result.season,result.team_id))
    used=set(); placebos=[]
    eligible=result[result.main_eligible].reset_index(drop=True)
    grouped={(int(s),int(i)):g.sort_values(['local_date','game_id']) for (s,i),g in metrics[metrics.chart_eligible].groupby(['season','team_id'])}
    for trial in range(50):
        matched=eligible.iloc[trial%len(eligible)]
        pool=[key for key,g in grouped.items() if key[0]==matched.season and key not in banned and key not in used and
              (key[0]-1,key[1]) in grouped and len(grouped[(key[0]-1,key[1])])>=8 and len(g)>=matched.prechange_n+3]
        rng.shuffle(pool)
        found=False
        for season,team_id in pool:
            b,t,fit,unknown=adjust.series(season,team_id)
            choices=[j for j in [int(matched.prechange_n)-1,int(matched.prechange_n),int(matched.prechange_n)+1] if j>=1 and len(t)-j>=4]
            if len(b)<8 or not choices:
                continue
            post=int(rng.choice(choices))
            chart,ref=control(b.adjusted_ppa,t.adjusted_ppa)
            outcome=classify(chart,post)
            placebos.append(dict(trial=trial+1,matched_case=matched.case_id,season=season,team_id=team_id,team=t.iloc[0].team,
                                 fake_first_post_date=t.iloc[post].local_date,prechange_n=post,**ref,**outcome))
            used.add((season,team_id)); found=True; break
        if not found:
            raise ValueError('Insufficient matched placebo units')
        if trial%10==9:
            print(f'{trial+1}/50 matched placebo units complete',flush=True)
    placebo=pd.DataFrame(placebos)
    placebo.to_csv(OUT/'placebo_results.csv',index=False)
    k=int(eligible.new_alarm.sum()); q=int(placebo.new_alarm.sum())
    summary=dict(case_count=len(result),eligible_cases=len(eligible),new_alarms=k,preexisting_alarms=int(eligible.preexisting_alarm.sum()),
                 insufficient_followup=int((~result.main_eligible).sum()),baseline_flagged_cases=int((result.baseline_weco_alarms>0).sum()),
                 eligible_baseline_flagged=int((eligible.baseline_weco_alarms>0).sum()),placebo_n=len(placebo),placebo_alarms=q,
                 placebo_rate=q/len(placebo),placebo_wilson_95=wilson(q,len(placebo)),placebo_unique_teams=int(placebo.team_id.nunique()),
                 cusum_near_change=int(result.cusum_near_change.sum()),seed=SEED)
    (OUT/'study_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    run()
