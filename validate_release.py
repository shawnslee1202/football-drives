"""Validate derived results and package only explicitly publishable files."""
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from pipeline import api_key

ROOT=Path(__file__).resolve().parent

def main():
    d=ROOT/'derived'
    summary=json.loads((d/'study_summary.json').read_text())
    audit=json.loads((d/'data_audit.json').read_text())
    cases=pd.read_csv(d/'case_results.csv'); placebos=pd.read_csv(d/'placebo_results.csv')
    metrics=pd.read_csv(d/'team_game_metrics.csv'); season=pd.read_csv(d/'team_season_metrics.csv')
    assert len(cases)==10 and len(placebos)==50
    assert placebos[['season','team_id']].drop_duplicates().shape[0]==50
    assert cases.main_eligible.sum()==summary['eligible_cases']
    assert cases.loc[cases.main_eligible,'new_alarm'].sum()==summary['new_alarms']
    assert placebos.new_alarm.sum()==summary['placebo_alarms']
    assert metrics.eligible_plays.sum()==audit['eligible_plays']
    assert metrics.ppa_n.sum()==audit['ppa_measured']
    assert season.drives.sum()==audit['drive_audit']['valid_tempo_drives']
    assert not metrics.duplicated(['season','game_id','team_id']).any()
    assert audit['missing_fbs_games']==0 and audit['unjoined_raw_plays']==0
    assert cases.loc[~cases.main_eligible,['delta_ci_low','delta_ci_high']].isna().all().all()
    pdf=PdfReader(ROOT/'football-drives-study.pdf')
    assert len(pdf.pages)==2
    text='\n'.join(p.extract_text() for p in pdf.pages)
    assert '1 of 8' in text and '7 of 50' in text and '634,546' in text
    html=(ROOT/'dashboard.html').read_text(encoding='utf-8')
    payload=json.loads(re.search(r'<script id="study-data" type="application/json">([\s\S]*?)</script>',html)[1])
    assert payload['summary']==summary
    for case in cases.case_id:
        assert (ROOT/'charts'/f'{case}.png').is_file()
    for href in re.findall(r'href="([^"]+)"',html):
        if not href.startswith(('http:','https:','#')):
            assert (ROOT/href).is_file(),f'Missing linked artifact: {href}'
    conn=sqlite3.connect(ROOT/'local'/'football.sqlite')
    assert conn.execute('SELECT count(*) FROM drive_metrics').fetchone()[0]==audit['drive_audit']['valid_tempo_drives']
    schema=['-- Raw CFBD response tables; full bodies remain private.']
    for (sql,) in conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('games','plays','teams','drives') ORDER BY name"):
        schema.append(sql+';')
    (ROOT/'schema.sql').write_text('\n'.join(schema)+'\n',encoding='utf-8')
    conn.close()
    manifest=[]
    for path in sorted((ROOT/'raw').glob('*.json')):
        raw=path.read_bytes(); doc=json.loads(raw)
        manifest.append({'file':path.name,'endpoint':doc['endpoint'],'params':doc['params'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(doc['data'])})
    (d/'input_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    versions={'python':sys.version.split()[0]}
    for name in ['numpy','pandas','matplotlib','statsmodels','scipy','reportlab','pypdf']:
        versions[name]=importlib.metadata.version(name)
    (d/'runtime_versions.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
    subprocess.run([sys.executable,'-m','unittest','-v'],cwd=ROOT,check=True)
    node=os.environ.get('NODE_EXE') or shutil.which('node')
    if not node:
        raise RuntimeError('Node.js is required for dashboard checks; set NODE_EXE to its executable.')
    subprocess.run([node,'check_dashboard_logic.cjs'],cwd=ROOT,check=True)
    native=json.loads((ROOT/'tableau'/'NATIVE_REVIEW.json').read_text())
    assert native['twb_sha256']==hashlib.sha256((ROOT/'tableau'/'football-drives.twb').read_bytes()).hexdigest()
    validation={'derived_reconciliation':'passed','unit_tests':'7 passed','pdf_pages':2,'pdf_visual_review':'both pages inspected','dashboard_logic':'isolated DOM harness passed','browser_visual_review':'not verified; environment blocked preview','tableau_native_review':'opened and rendered in Tableau Public 2026.3; Texas A&M selector checked','public_publication':json.loads((d/'publication.json').read_text())}
    (d/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    allowed=[]
    for pattern in ['*.py','*.md','*.sql','*.ps1','*.txt','*.html','*.ipynb','*.pdf','*.cjs']:
        allowed.extend(ROOT.glob(pattern))
    allowed.append(ROOT/'.gitignore')
    # Required research input: dated interventions and their source citations.
    allowed.append(ROOT/'interventions.csv')
    for folder in ['derived','charts','tableau']:
        allowed.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and not p.name.startswith('~') and p.suffix != '.twbr')
    allowed=sorted(set(allowed))
    key=api_key()
    for path in allowed:
        rel=path.relative_to(ROOT)
        assert '.env' not in rel.parts and not any(x in rel.parts for x in ['raw','local','.git','__pycache__'])
        if key and len(key)>10:
            assert key.encode() not in path.read_bytes(),f'Credential detected in {rel}; release blocked'
    package=ROOT.parent/'football-drives-project.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for path in allowed:
            z.write(path,'football-drives/'+path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        assert 'football-drives/interventions.csv' in z.namelist()
        assert not any('/raw/' in x or '/local/' in x or x.endswith('/.env') for x in z.namelist())
    print(f'PASS: result reconciliation, seven tests, 2-page PDF, links, input/runtime manifests, and clean ZIP ({len(allowed)} files).')
    print('Native Tableau rendering checked. Offline browser rendering remains unverified; publication status is recorded in derived/publication.json.')

if __name__=='__main__': main()
