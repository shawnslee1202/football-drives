"""Generate the Tableau workbook using verified native extracts and aggregate tables."""
from pathlib import Path
import json
import hashlib
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'tableau'

def sub(parent,tag,**attrs):
    return ET.SubElement(parent,tag,{k.replace('_','-'):str(v) for k,v in attrs.items()})

def main():
    data_dir=DEST/'Data'; data_dir.mkdir(parents=True,exist_ok=True)
    teams=pd.read_csv(ROOT/'derived'/'team_season_metrics.csv')
    tempo=teams[['team','season','plays_per_minute','points_per_drive','drives']].copy()
    tempo['team_season']=tempo.team+' '+tempo.season.astype(str)
    tempo.to_csv(data_dir/'tempo.csv',index=False)
    b=pd.read_csv(ROOT/'derived'/'bottlenecks.csv')
    b=b[b.display_eligible].copy(); b['case']=b.team+' '+b.season.astype(str)
    b['state']=b.field_zone+' / '+b.distance_bucket+' yards'; b['down_label']=b.down.astype(str)+' down'
    b[['case','state','down_label','gap_pp','snaps','conversion_rate','fbs_other_rate']].to_csv(data_dir/'bottleneck.csv',index=False)
    p=pd.read_csv(ROOT/'derived'/'control_chart_points.csv'); cases=pd.read_csv(ROOT/'derived'/'case_results.csv')
    rows=[]
    for case in cases.itertuples():
        g=p[p.case_id==case.case_id]; label=f'{case.team} {case.season}'
        for r in g.itertuples():
            for series,value in [('Adjusted PPA (z)',r.z),('Upper limit',3),('Lower limit',-3),('Center',0)]:
                rows.append(dict(case=label,relative_game=r.game_index-case.prechange_n-1,series=series,value=value))
        for value in [min(-4,g.z.min()),max(4,g.z.max())]:
            rows.append(dict(case=label,relative_game=-.5,series='Coaching change',value=value))
    control=pd.DataFrame(rows)
    # Include a path dimension to preserve both endpoints of the vertical intervention line.
    control['path_order']=control.groupby(['case','series']).cumcount()+1
    control['path_order']=control.path_order.map(lambda x:f'{x:03d}')
    control.to_csv(data_dir/'control.csv',index=False)
    extract_manifest=json.loads((data_dir/'extract_manifest.json').read_text())
    for name in ['tempo','bottleneck','control']:
        assert hashlib.sha256((data_dir/(name+'.csv')).read_bytes()).hexdigest()==extract_manifest[name]['csv_sha256'], 'Refresh native extracts after changing source tables'
        assert hashlib.sha256((data_dir/(name+'.hyper')).read_bytes()).hexdigest()==extract_manifest[name]['hyper_sha256'], 'Extract changed; refresh its provenance manifest'
    wb=ET.Element('workbook',{'source-platform':'win','version':'18.1','source-build':'2026.3.0 (20263.26.1015.1742)'})
    datasources=sub(wb,'datasources'); sheets=sub(wb,'worksheets')
    specs=[('Tempo versus points','tempo',tempo,'plays_per_minute','points_per_drive','Circle','season','team_season',None),
           ('State bottlenecks','bottleneck',b[['case','state','down_label','gap_pp','snaps','conversion_rate','fbs_other_rate']],'state','down_label','Square','gap_pp',None,'Nebraska 2022'),
           ('Control chart - zero is first affected game','control',control,'relative_game','value','Line','series',None,'Nebraska 2022')]
    for sheet_name,name,frame,x,y,mark,color,detail,filter_value in specs:
        dsname='textscan.'+name
        ds=sub(datasources,'datasource',caption=name,inline='true',name=dsname,version='18.1')
        conn=sub(ds,'connection',**{'class':'federated'})
        named=sub(sub(conn,'named-connections'),'named-connection',caption=name,name='textscan.source_'+name)
        sub(named,'connection',**{'class':'textscan','directory':'Data','filename':name+'.csv','password':'','server':''})
        relation=sub(conn,'relation',connection='textscan.source_'+name,name=name,table=f'[{name}#csv]',type='table')
        columns=sub(relation,'columns',character_set='UTF-8',header='yes',locale='en_US',separator=',')
        numeric={c for c in frame if pd.api.types.is_numeric_dtype(frame[c]) and c not in ['season','path_order']}
        for i,c in enumerate(frame):
            sub(columns,'column',datatype='real' if c in numeric else 'string',name=c,ordinal=i)
            sub(ds,'column',datatype='real' if c in numeric else 'string',name=f'[{c}]',role='measure' if c in numeric else 'dimension',type='quantitative' if c in numeric else 'nominal')
        extract_path=data_dir/(name+'.hyper')
        if extract_path.exists():
            extract=sub(ds,'extract',enabled='true',count='-1',units='records')
            ec=sub(extract,'connection',**{'class':'hyper','dbname':'Data/'+name+'.hyper','schema':'Extract','access_mode':'readonly'})
            sub(ec,'relation',name='Extract',table='[Extract].[Extract]',type='table')
        sheet=sub(sheets,'worksheet',name=sheet_name); table=sub(sheet,'table'); view=sub(table,'view')
        refs=sub(view,'datasources'); sub(refs,'datasource',caption=name,name=dsname)
        dependencies=sub(view,'datasource-dependencies',datasource=dsname)
        def ref(c):
            return f'[{dsname}].[{"avg" if c in numeric else "none"}:{c}:{"qk" if c in numeric else "nk"}]'
        for c in frame:
            sub(dependencies,'column',datatype='real' if c in numeric else 'string',name=f'[{c}]',role='measure' if c in numeric else 'dimension',type='quantitative' if c in numeric else 'nominal')
            sub(dependencies,'column-instance',column=f'[{c}]',derivation='Avg' if c in numeric else 'None',name=f'[{"avg" if c in numeric else "none"}:{c}:{"qk" if c in numeric else "nk"}]',pivot='key',type='quantitative' if c in numeric else 'nominal')
        if filter_value:
            f=sub(view,'filter',**{'class':'categorical','column':ref('case')})
            sub(f,'groupfilter',function='member',level='[none:case:nk]',member='"'+filter_value+'"')
            sub(sub(view,'slices'),'column').text=ref('case')
        sub(view,'aggregation',value='true'); sub(table,'style')
        panes=sub(table,'panes'); pane=sub(panes,'pane'); sub(sub(pane,'view'),'breakdown',value='auto')
        sub(pane,'mark',**{'class':mark})
        enc=sub(pane,'encodings'); sub(enc,'color',column=ref(color))
        if detail: sub(enc,'lod',column=ref(detail))
        if name=='control': sub(enc,'path',column=ref('path_order'))
        if name=='bottleneck':
            sub(enc,'text',column=ref('gap_pp'))
            sub(sub(sub(pane,'style'),'style-rule',element='mark'),'format',attr='mark-labels-show',value='true')
        sub(table,'rows').text=ref(y); sub(table,'cols').text=ref(x)
    dashboards=sub(wb,'dashboards'); dash=sub(dashboards,'dashboard',name='Football production line')
    sub(dash,'style'); sub(dash,'size',maxheight=850,maxwidth=1300,minheight=850,minwidth=1300,sizing_mode='fixed')
    zones=sub(dash,'zones')
    for i,(spec,x,y,w,h) in enumerate([(specs[0],0,12000,48000,40000),(specs[1],48000,12000,52000,40000),(specs[2],0,62000,100000,38000)],1):
        sub(zones,'zone',h=h,id=i,name=spec[0],w=w,x=x,y=y)
    heading=sub(zones,'zone',type='text',h=10000,id=4,w=100000,x=0,y=0)
    ft=sub(heading,'formatted-text')
    sub(ft,'run',bold='true',fontsize='16').text='Football as a production process | 2021–2023\n'
    sub(ft,'run',fontsize='10').text='1 of 8 new coaching-change alarms vs 7 of 50 placebo dates. Retrospective, noncausal. Data: CollegeFootballData.com.'
    for i,spec,x,w in [(5,specs[1],48000,52000),(6,specs[2],0,48000)]:
        sub(zones,'zone',type='filter',name=spec[0],param=f'[textscan.{spec[1]}].[none:case:nk]',mode='dropdown',h=9000,id=i,w=w,x=x,y=52000)
    windows=sub(wb,'windows')
    for spec in specs:
        window=sub(windows,'window',**{'class':'worksheet','name':spec[0]})
        cards=sub(window,'cards')
        if spec[-1]:
            edge=sub(cards,'edge',name='right'); strip=sub(edge,'strip',size=180)
            sub(strip,'card',type='filter',mode='dropdown',param=f'[textscan.{spec[1]}].[none:case:nk]')
        sub(sub(window,'viewpoint'),'zoom',type='entire-view')
    dashboard_window=sub(windows,'window',**{'class':'dashboard','name':'Football production line','maximized':'true'})
    viewpoints=sub(dashboard_window,'viewpoints')
    for spec in specs:
        sub(sub(viewpoints,'viewpoint',name=spec[0]),'zoom',type='entire-view')
    sub(dashboard_window,'active',id='1')
    ET.indent(wb)
    path=DEST/'football-drives.twb'; ET.ElementTree(wb).write(path,encoding='utf-8',xml_declaration=True)
    parsed=ET.parse(path)
    assert len(parsed.findall('.//worksheet'))==3
    for connection in parsed.findall('.//connection'):
        if connection.attrib['class']=='textscan':
            assert (DEST/connection.attrib['directory']/connection.attrib['filename']).exists()
        elif connection.attrib['class']=='hyper':
            assert (DEST/connection.attrib['dbname']).exists()
    with zipfile.ZipFile(DEST/'football-drives.twbx','w',zipfile.ZIP_DEFLATED) as z:
        z.write(path,path.name)
        for pattern in ['*.csv','*.hyper']:
            for file in data_dir.glob(pattern): z.write(file,'Data/'+file.name)
    review_path=DEST/'NATIVE_REVIEW.json'
    review=json.loads(review_path.read_text()) if review_path.exists() else {}
    verified=review.get('twb_sha256')==hashlib.sha256(path.read_bytes()).hexdigest()
    (DEST/'VALIDATION.json').write_text(json.dumps({'xml_parse':'passed','worksheet_count':3,'local_connections_resolve':True,'native_tableau_open':'passed; see NATIVE_REVIEW.json' if verified else 'requires review of this workbook revision','publication':review.get('publication','not published')},indent=2),encoding='utf-8')
    print('Created Tableau workbook with three native extracts. Native review current:',verified)

if __name__=='__main__': main()
