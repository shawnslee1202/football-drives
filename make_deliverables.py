"""Create scientific plots, the two-page report and an offline review dashboard."""
import contextlib
import io
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'local'/'matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor,white
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle

NAVY='#172E40'; TEAL='#087E8B'; RED='#B34737'; GOLD='#D49B31'; MUTED='#556573'
CHARTS=ROOT/'charts'

def save(fig,name):
    fig.savefig(CHARTS/name,dpi=170,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def make_charts(cases,points,teams,bottles,summary):
    CHARTS.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':NAVY,'text.color':NAVY,'axes.titleweight':'bold'})
    eligible=cases[cases.main_eligible].iloc[::-1]
    fig,ax=plt.subplots(figsize=(8.2,3.5))
    for i,r in enumerate(eligible.itertuples()):
        color=TEAL if r.new_alarm else MUTED
        ax.errorbar(r.adjusted_delta,i,xerr=[[r.adjusted_delta-r.delta_ci_low],[r.delta_ci_high-r.adjusted_delta]],fmt='o',color=color,capsize=3)
    ax.set_yticks(range(len(eligible)),[f'{r.team} {r.season}' for r in eligible.itertuples()])
    ax.axvline(0,color='#AAB5BC',lw=1)
    ax.set_xlabel('First four post-change games minus prior-season baseline (adjusted PPA/play)')
    ax.set_title('Most estimated changes remain imprecise',loc='left',pad=13)
    ax.grid(axis='x',alpha=.15)
    fig.tight_layout()
    save(fig,'effect_sizes.png')
    fig,ax=plt.subplots(figsize=(6.2,2.6))
    ax.barh(['Coaching-change cases','Matched placebo dates'],[summary['new_alarms']/summary['eligible_cases']*100,summary['placebo_rate']*100],color=[TEAL,'#8696A1'],height=.5)
    for i,(k,n) in enumerate([(summary['new_alarms'],summary['eligible_cases']),(summary['placebo_alarms'],summary['placebo_n'])]):
        ax.text(100*k/n+.7,i,f'{k}/{n} ({100*k/n:.1f}%)',va='center',fontsize=11)
    ax.set_xlim(0,25); ax.set_xlabel('New alarm within four eligible games (%)'); ax.invert_yaxis()
    ax.set_title('Alarms also appear at placebo dates',loc='left'); fig.tight_layout()
    save(fig,'alarm_comparison.png')
    for case in cases.itertuples():
        g=points[points.case_id==case.case_id].sort_values('game_index')
        fig,axes=plt.subplots(3,1,figsize=(10.5,7.6),sharex=True,gridspec_kw={'height_ratios':[2,1,1]})
        x=g.game_index.to_numpy(); ax=axes[0]
        ax.axhspan(g.lcl.iloc[0],g.ucl.iloc[0],color=TEAL,alpha=.055)
        ax.axhline(g.center.iloc[0],color=MUTED,lw=1,label='Prior-season center')
        ax.axhline(g.lcl.iloc[0],color=RED,ls='--',lw=1,label='3-sigma limits')
        ax.axhline(g.ucl.iloc[0],color=RED,ls='--',lw=1)
        ax.plot(x,g.adjusted_ppa,'o-',color=NAVY,lw=1.5,label='Adjusted game PPA')
        alarm=g.weco_alarm
        ax.scatter(g.loc[alarm,'game_index'],g.loc[alarm,'adjusted_ppa'],s=80,facecolor='none',edgecolor=RED,lw=2,label='WECO alarm',zorder=5)
        ax.set_ylabel('Adjusted PPA/play')
        ax.set_title(f'{case.team} {case.season} | {case.status}',loc='left',pad=15)
        ax.legend(fontsize=8,ncol=2,loc='best')
        axes[1].plot(x,g.cusum_positive,color=TEAL,label='Positive CUSUM')
        axes[1].plot(x,g.cusum_negative,color=RED,label='Negative CUSUM')
        axes[1].axhline(5,color=MUTED,ls='--',lw=1)
        axes[1].set_ylabel('CUSUM'); axes[1].legend(fontsize=8,ncol=2,loc='upper left')
        axes[2].plot(x,g.mr,'o-',color=MUTED,ms=3)
        axes[2].axhline(g.mr_ucl.iloc[0],color=RED,ls='--',lw=1)
        axes[2].axhline(g.mr_center.iloc[0],color=MUTED,lw=.7)
        axes[2].set_ylabel('Moving range')
        for a in axes:
            a.axvline(case.prechange_n+.5,color=GOLD,lw=1.8)
            a.axvspan(case.prechange_n+.5,min(case.prechange_n+4.5,len(g)+.5),color=GOLD,alpha=.09)
            a.grid(alpha=.12); a.set_xlim(.5,len(g)+.5)
        axes[2].set_xticks(x,[f'{r.local_date[5:]}\n{r.opponent}' for r in g.itertuples()],rotation=30,ha='right',fontsize=8)
        axes[2].set_xlabel('Eligible games in chronological order; gold line = coaching change; shading = primary follow-up')
        fig.tight_layout()
        save(fig,f'{case.case_id}.png')
    fig,ax=plt.subplots(figsize=(8,4.5))
    for season,color in zip([2021,2022,2023],['#AAB5BC',TEAL,GOLD]):
        t=teams[teams.season==season]
        ax.scatter(t.plays_per_minute,t.points_per_drive,s=18,alpha=.65,c=color,label=str(season))
    ax.set_xlabel('Eligible offensive snaps per possession minute (game clock)')
    ax.set_ylabel('Points per drive (TD=6; FG=3)'); ax.set_title('Faster game-clock pace is not a clear scoring advantage',loc='left')
    ax.legend(title='Season'); ax.grid(alpha=.15); fig.tight_layout(); save(fig,'tempo_scatter.png')
    b=bottles[(bottles.team=='Nebraska')&(bottles.season==2022)]
    labels=[(zone,dist) for zone in ['Own half','Opponent half','Red zone'] for dist in ['1-3','4-6','7-10','11+']]
    matrix=np.full((4,12),np.nan); sizes=np.zeros((4,12),dtype=int)
    for r in b.itertuples():
        j=labels.index((r.field_zone,r.distance_bucket)); sizes[int(r.down)-1,j]=r.snaps
        if r.display_eligible: matrix[int(r.down)-1,j]=r.gap_pp
    fig,ax=plt.subplots(figsize=(10,3.4))
    im=ax.imshow(np.ma.masked_invalid(matrix),cmap='RdBu',vmin=-25,vmax=25,aspect='auto')
    for i in range(4):
        for j in range(12):
            if np.isfinite(matrix[i,j]): ax.text(j,i,f'{matrix[i,j]:+.0f}\nn={sizes[i,j]}',ha='center',va='center',fontsize=8,color='white' if abs(matrix[i,j])>15 else NAVY)
    ax.set_yticks(range(4),['1st down','2nd down','3rd down','4th down'])
    ax.set_xticks(range(12),[f'{z}\n{d} yards' for z,d in labels],rotation=35,ha='right',fontsize=8)
    ax.set_title('Nebraska 2022 | next-snap conversion gap vs other FBS teams',loc='left',pad=12)
    fig.colorbar(im,ax=ax,label='Percentage points'); fig.tight_layout(); save(fig,'bottleneck_example.png')

def paragraph(c,text,x,y,width,size=10,color=NAVY,leading=None):
    style=ParagraphStyle('body',fontName='Helvetica',fontSize=size,leading=leading or size*1.35,textColor=HexColor(color))
    p=Paragraph(text,style); _,h=p.wrap(width,1000); p.drawOn(c,x,y-h); return y-h

def pdf_report(cases,summary,audit,tempo):
    path=ROOT/'football-drives-study.pdf'
    c=canvas.Canvas(str(path),pagesize=(612,792))
    c.setTitle('Drives as a Production Line - Coaching-Change Study')
    def shell(page,subtitle):
        c.setFillColor(HexColor(NAVY)); c.rect(0,708,612,84,fill=1,stroke=0)
        c.setFillColor(white); c.setFont('Helvetica-Bold',20); c.drawString(42,752,'Drives as a Production Line')
        c.setFont('Helvetica',10); c.drawString(42,730,subtitle)
        c.setFillColor(HexColor(MUTED)); c.setFont('Helvetica',8)
        c.drawString(42,24,'FBS play-by-play | 2021-2023 | Retrospective study | October 22, 2026')
        c.drawRightString(570,24,f'{page} / 2')
    shell(1,'Did offensive efficiency shift after a mid-season coaching change?')
    y=681
    y=paragraph(c,f'<b>{summary["new_alarms"]} of {summary["eligible_cases"]}</b> eligible coaching changes produced a new control-chart alarm within four games.',42,y,528,20,leading=25)
    y=paragraph(c,f'The identical procedure flagged <b>{summary["placebo_alarms"]} of {summary["placebo_n"]} matched placebo dates ({summary["placebo_rate"]:.0%})</b>. This small observational sample does not show a clear concentration of alarms after the selected changes.',42,y-12,528,10.5)
    c.drawImage(str(CHARTS/'alarm_comparison.png'),42,392,width=528,height=153,preserveAspectRatio=True,anchor='c')
    y=375
    y=paragraph(c,'<b>What the number means</b>',42,y,528,12)
    y=paragraph(c,'The new alarm belongs to Nebraska in 2022 and is a downward WECO signal. Charlotte had an alarm before its change. Texas A&amp;M and Boise State have only one and three eligible follow-up games, respectively, so neither enters the four-game comparison. No first CUSUM crossing landed within one eligible game of a change.',42,y-7,528,10)
    y=paragraph(c,'<b>Method</b>',42,y-17,528,12)
    y=paragraph(c,'Ten documented coaching changes; fixed prior-season baselines of 11-12 games. Opponent and home-field effects are fitted only on the prior season, excluding the focal offense from training. Per-game adjusted PPA is monitored with I-MR charts, four Western Electric rules and a date-blind two-sided CUSUM (k=0.5, h=5). A new alarm must first arise in the four-game follow-up, with no earlier target-season alarm.',42,y-7,528,9.6)
    y=paragraph(c,'<b>Why caution changes the conclusion</b>',42,y-16,528,12)
    y=paragraph(c,'The Nebraska alarm disappears when baseline sigma uses the sample standard deviation instead of moving ranges. The placebo rate has an approximate 95% Wilson interval of 7%-26%; controls are not known to be change-free. Four games offer limited precision, and coaching changes coincide with injuries, staff changes and schedule shifts. An alarm is not proof of a coaching effect; no alarm is not proof of no effect.',42,y-7,528,9.6)
    c.showPage(); shell(2,'Evidence, data quality and practical interpretation')
    y=685
    y=paragraph(c,'<b>All ten cases remain visible</b>',42,y,528,13)
    data=[['Team / season','Post games','Primary classification','Delta PPA*']]
    for r in cases.itertuples():
        data.append([f'{r.team} {r.season}',str(r.followup_n),r.status,f'{r.adjusted_delta:+.3f}' if r.main_eligible else 'Not assessed'])
    table=Table(data,colWidths=[160,62,210,96],rowHeights=[23]+[22]*10)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor(NAVY)),('TEXTCOLOR',(0,0),(-1,0),white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8.5),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#F1F5F6'),white]),('ALIGN',(1,0),(1,-1),'CENTER'),('ALIGN',(-1,0),(-1,-1),'RIGHT')]))
    table.wrap(528,400); table.drawOn(c,42,y-255)
    y=y-269
    y=paragraph(c,'*First-four-game mean minus prior-season adjusted baseline; descriptive, not causal. Bootstrap intervals and all sensitivity variants are in the companion tables. Boise State includes the conference championship classified as regular season by CFBD.',42,y,528,8.4)
    y=paragraph(c,'<b>Coverage and exclusions</b>',42,y-15,528,12)
    y=paragraph(c,f'{audit["raw_plays"]:,} raw plays; {audit["eligible_plays"]:,} eligible offensive plays; {audit["ppa_measured"]:,} with PPA. All {audit["expected_completed_fbs_games"]:,} completed FBS-vs-FBS games have records. Regulation only; kneels, spikes, penalties, special teams and fourth-quarter margins above 28 are excluded. Drive analysis retains {audit["drive_audit"]["valid_tempo_drives"]:,} drives after clock/outcome checks; 78 ambiguous drive IDs are excluded. Complete game coverage does not guarantee every play is recorded correctly.',42,y-7,528,9.3)
    y=paragraph(c,'<b>Secondary result: tempo</b>',42,y-15,528,12)
    y=paragraph(c,f'An additional eligible snap per possession minute is associated with {tempo["tempo_coefficient"]:+.3f} points per drive (95% interval {tempo["ci_low"]:+.3f} to {tempo["ci_high"]:+.3f}), controlling for offense, defense, season, starting field position and home field. The interval includes zero. This is game-clock pace, not real-time tempo. Points count offensive TDs as six and field goals as three; conversions are excluded.',42,y-7,528,9.3)
    y=paragraph(c,'<b>Sources and reproducibility</b>',42,y-15,528,12)
    y=paragraph(c,'Data provided by <link href="https://collegefootballdata.com" color="#087E8B">CollegeFootballData.com</link>. Signal rules follow the <link href="https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm" color="#087E8B">NIST control-chart guidance</link> and <link href="https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm" color="#087E8B">CUSUM guidance</link>. Dated intervention sources, exclusions and limitations appear in interventions.csv and PROTOCOL.md. Scripts, derived tables, an analysis notebook and an offline dashboard accompany this report. The analysis plan was recorded after inspecting the Texas A&amp;M pilot; it is not a preregistration.',42,y-7,528,8.6)
    if y<40: raise ValueError(f'PDF content overflow: y={y}')
    c.save()

def notebook():
    cells=[]; count=0
    def md(text): cells.append({'cell_type':'markdown','metadata':{},'source':text.splitlines(True)})
    def code(source):
        nonlocal count
        count+=1
        capture=io.StringIO()
        with contextlib.redirect_stdout(capture): exec(source,namespace)
        cells.append({'cell_type':'code','metadata':{},'source':source.splitlines(True),'execution_count':count,'outputs':[{'output_type':'stream','name':'stdout','text':capture.getvalue().splitlines(True)}]})
    namespace={}
    md('# Drives as a Production Line\nExecuted analysis companion. The tables below are real derived data. Read PROTOCOL.md before interpreting alarms. Run from the repository folder. The full pipeline is reproduced by run-study.ps1; raw data remains local.')
    code("from pathlib import Path\nimport pandas as pd, json\nroot = Path.cwd()\nif not (root / 'derived').exists():\n    root = root / 'outputs' / 'football-drives'\nsummary = json.loads((root / 'derived' / 'study_summary.json').read_text())\nprint(json.dumps(summary, indent=2))")
    md('## Ten verified changes\nTwo cases have insufficient follow-up. The first-four-game outcome is compared with a prior-season baseline, not interpreted as a causal effect.')
    code("cases = pd.read_csv(root / 'derived' / 'case_results.csv')\nprint(cases[['team','season','baseline_n','followup_n','status','adjusted_delta']].to_string(index=False))")
    md('## Matched placebo dates\nThe same whole-season scan and new-alarm rule are used. These are not proven null cases, and the 50 units contain 48 distinct teams.')
    code("placebos = pd.read_csv(root / 'derived' / 'placebo_results.csv')\nprint(f'Placebo new alarms: {placebos.new_alarm.sum()} / {len(placebos)}')\nprint(placebos[['team','season','fake_first_post_date','new_alarm']].head(10).to_string(index=False))")
    md('## Sensitivity\nDo not select the variant that gives the most interesting result.')
    code("s = pd.read_csv(root / 'derived' / 'sensitivity.csv')\nprint(s[s.main_eligible].groupby('variant').agg(cases=('case_id','size'),new_alarms=('new_alarm','sum')).to_string())")
    md('## Secondary tempo model\nThis regression is descriptive and uses game-clustered standard errors.')
    code("print((root / 'derived' / 'tempo_model.json').read_text())")
    md('## Data quality\nAll expected games are represented; that does not prove within-game completeness.\n\n![Effect-size intervals](charts/effect_sizes.png)\n\n![Tempo scatter](charts/tempo_scatter.png)')
    code("print((root / 'derived' / 'data_audit.json').read_text())")
    md('## Rebuild\nFrom a terminal with requirements.txt installed: `python build_tables.py`, `python study.py`, `python secondary.py`, `python make_deliverables.py`. Download first with `python pipeline.py pull --seasons 2021 2022 2023` and `python pipeline.py drives --seasons 2021 2022 2023`. Set CFBD_API_KEY in the local .env file. Never commit raw/ or .env.')
    nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},'nbformat':4,'nbformat_minor':4}
    (ROOT/'analysis.ipynb').write_text(json.dumps(nb,indent=2),encoding='utf-8')

def main():
    cases=pd.read_csv(ROOT/'derived'/'case_results.csv')
    points=pd.read_csv(ROOT/'derived'/'control_chart_points.csv')
    teams=pd.read_csv(ROOT/'derived'/'team_season_metrics.csv')
    bottles=pd.read_csv(ROOT/'derived'/'bottlenecks.csv')
    summary=json.loads((ROOT/'derived'/'study_summary.json').read_text())
    audit=json.loads((ROOT/'derived'/'data_audit.json').read_text())
    tempo=json.loads((ROOT/'derived'/'tempo_model.json').read_text())
    make_charts(cases,points,teams,bottles,summary)
    pdf_report(cases,summary,audit,tempo)
    old=Path.cwd()
    try:
        os.chdir(ROOT); notebook()
    finally: os.chdir(old)
    payload={'cases':json.loads(cases.to_json(orient='records')),'teams':json.loads(teams.to_json(orient='records')),
             'bottlenecks':json.loads(bottles.to_json(orient='records')),'summary':summary,'tempo':tempo,'audit':audit}
    html=(ROOT/'dashboard_template.html').read_text(encoding='utf-8').replace('__DATA__',json.dumps(payload).replace('</','<\\/'))
    (ROOT/'dashboard.html').write_text(html,encoding='utf-8')
    print('Created charts, two-page PDF, executed notebook and offline dashboard.')

if __name__=='__main__': main()
