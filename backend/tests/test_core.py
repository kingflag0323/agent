import asyncio
import io
import json
import zipfile
from pathlib import Path
import httpx
import pytest
from app.core import settings
from app.core.config import ROOT,DEFAULTS,DATA
from app.database import store
from app.agent.workflow import run_job
from app.code_analysis.scanner import scan
from app.code_analysis.projects import import_zip,read_file
from app.xdr.adapter import XDRAdapter,normalize,CAPABILITIES,XDRError
from app.agent.evidence import collect
from app.xdr.demo import bundle
from app.correlation.engine import correlate

def create_job(event_id,config=None):
    id='test-'+event_id
    job={'id':id,'event':store.get('events',event_id),'project':store.get('projects','demo-shop'),'status':'queued','created_at':store.now(),'timeline':[],'evidence':[],'warnings':[]}
    store.put('investigations',job);asyncio.run(run_job(id,config or settings.load()));return store.get('investigations',id)

def test_sql_complete_evidence_chain(client):
    j=create_job('demo-001');assert j['status']=='completed',j.get('error')
    m=j['correlation']['matches'][0];assert m['finding']['cwe']=='CWE-89';assert [f['name'] for f in m['chain']]==['user_controller','get_user','find_user'];assert m['finding']['line']==6
    assert m['confidence']=='high';assert j['analysis']['provider']=='mock'
    assert {e['kind'] for e in j['evidence']}=={'Demo Fact','Static Finding'}
    ids={e['id'] for e in j['evidence']};assert all(id in ids for id in m['evidence_ids'])
    report=client.get(f"/api/investigations/{j['id']}/report");assert report.status_code==200;assert '参数化查询' in report.text

def test_command_chain_and_negative_control(client):
    positive=create_job('demo-002');assert positive['correlation']['matches'][0]['finding']['cwe']=='CWE-78'
    negative=create_job('demo-003');assert negative['status']=='completed';assert negative['correlation']['matches']==[];assert negative['correlation']['verdict']=='insufficient_evidence'
    ssh=create_job('demo-004');assert ssh['correlation']['matches']==[];assert not ssh['plan']['include_network']

def test_persistence_and_dashboard(client):
    a=client.get('/api/dashboard').json();assert a['total']==6;assert sum(a['severity'].values())==a['total'];assert a['assets']==4
    assert sum(t['events'] for t in a['trend'])==6
    assert client.get('/api/events?q=SQL').json()['total']==2
    assert client.get('/api/events?page=0').status_code==422
    assert client.get('/api/events/missing').status_code==404
    event=store.get('events','demo-001');store.put('events',event);assert store.get('events',event['id'])==event

def test_settings_secrets_and_validation(client):
    r=client.put('/api/settings',json={'llm':{'api_key':'test-secret'},'xdr':{'token':'xdr-secret'}})
    assert r.status_code==200;assert 'test-secret' not in r.text;assert 'xdr-secret' not in r.text
    assert client.get('/api/settings').json()['llm']['api_key_configured']
    client.put('/api/settings',json={'llm':{'api_key':''}});assert settings.load()['llm']['api_key']=='test-secret'
    assert client.put('/api/settings',json={'xdr':{'auth_header':'Host'}}).status_code==400
    assert client.put('/api/settings',json={'agent':{'max_steps':0}}).status_code==400
    assert client.put('/api/settings',json={'llm':{'base_url':'file:///etc/passwd'}}).status_code==400
    assert client.put('/api/settings',json={'audit':{'max_files':True}}).status_code==400

def test_browser_request_boundary(client):
    assert client.post('/api/events/sync',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/events/sync',headers={'X-Sentinel-Client':''}).status_code==403
    assert client.get('/api/settings',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403

def zip_bytes(name,content):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr(name,content)
    b.seek(0);return b

def test_zip_local_path_and_limits(client):
    for name in ['../escape.py','C:/escape.py','dir/file.py:stream','\\\\server/share/a.py']:
        with pytest.raises(ValueError,match='穿越'):import_zip('bad',zip_bytes(name,'print(1)'))
    z=zip_bytes('nested/app.py','def hello():\n    return 1\n');p=import_zip('good',z);assert read_file(p,'nested/app.py').startswith('def hello')
    with pytest.raises(ValueError):read_file(p,'../../../etc/passwd')
    assert client.post('/api/projects',json={'name':'private','path':'/etc'}).status_code==400
    assert client.post('/api/projects',json={'name':'unsafe','source':'git','git_url':'file:///tmp/repo'}).status_code==400
    assert client.post('/api/projects/upload',data={'name':'bad'},files={'file':('x.zip',b'not a zip')}).status_code==400

def test_xdr_document_contract_and_normalization(client):
    documented=json.loads((ROOT/'backend/tests/fixtures/xdr-endpoints.json').read_text(encoding='utf-8'))
    for cap,method,path,note in CAPABILITIES:
        assert any(x['uri']==path and x['type']==(0 if method=='POST' else 1) for x in documented)
    n=normalize({'uuId':'abc','incidentSeverity':4,'hostIp':'10.0.0.1','endTime':1700000000,'dealStatus':40})
    assert n['severity']=='critical';assert n['source']=='live';assert n['status']=='closed';assert n['time'].startswith('2023')
    with pytest.raises(XDRError):normalize({'name':'no uuid'})

def test_live_xdr_transport(monkeypatch,client):
    requests=[]
    def handler(req):
        requests.append(req);assert req.headers['Authorization']=='Bearer example'
        if req.url.path.endswith('/incidents/list'):return httpx.Response(200,json={'code':'Success','data':{'total':1,'item':[{'uuId':'live-1','incidentSeverity':3,'name':'test'}]}})
        return httpx.Response(200,json={'code':'Unknown.GeneralError','message':'token.not.exist'})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    cfg={**DEFAULTS['xdr'],'mode':'live','base_url':'https://xdr.test','token':'example'}
    result=asyncio.run(XDRAdapter(cfg).events());assert result[0]['source']=='live';assert json.loads(requests[0].content)['pageSize']==200
    with pytest.raises(XDRError):asyncio.run(XDRAdapter(cfg).request('event_proof',uuid='foo'))

def test_repaired_code_does_not_correlate(client):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        for p in (ROOT/'demo/shop').glob('*.py'):
            code=p.read_text(encoding='utf-8')
            if p.name=='repository.py':code=code.replace('"SELECT id, name, email FROM users WHERE id = " + user_id','"SELECT id, name, email FROM users WHERE id = ?"').replace('connection.execute(query)','connection.execute(query, (user_id,))')
            z.writestr(p.name,code)
    b.seek(0);project=import_zip('fixed',b);s=scan(project,DEFAULTS['audit']);e=store.get('events','demo-001');c=correlate(e,collect(bundle(e)),s);assert not c['matches'];assert all(f['rule']!='B608' for f in s['findings'])

def test_max_steps_failure_not_completed(client):
    cfg=settings.load();cfg['agent']['max_steps']=5
    j=create_job('demo-001',cfg);assert j['status']=='failed';assert 'Max Steps' in j['error'];assert client.get('/api/investigations/'+j['id']+'/report').status_code==409

def test_scan_syntax_error_is_partial(client):
    p=import_zip('syntax-error',zip_bytes('bad.py','def !!! invalid'))
    s=scan(p,DEFAULTS['audit']);assert s['status']=='partial';assert s['errors']

def test_llm_contract_and_failure(monkeypatch,client):
    from app.llm.provider import LLMProvider
    calls=[]
    def handler(req):
        calls.append(json.loads(req.content));return httpx.Response(200,json={'choices':[{'message':{'content':'Test inference [ev-123]'}}]})
    original=httpx.AsyncClient;monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    cfg={**DEFAULTS['llm'],'mode':'compatible','base_url':'https://model.test/v1','model':'test-model','api_key':'example'}
    result=asyncio.run(LLMProvider(cfg).analyze({'evidence':'untrusted source'}));assert result['kind']=='AI Inference';assert result['verified'] is False;assert 'untrusted DATA' in calls[0]['messages'][0]['content']

def test_nested_package_paths_are_portable(client):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('web/routes.py','from fastapi import APIRouter\nfrom web.repository import find\nrouter=APIRouter()\n@router.get("/api/user")\ndef user(id: str):\n    return find(id)\n')
        z.writestr('web/repository.py','import sqlite3\ndef find(id):\n    db=sqlite3.connect(":memory:")\n    return db.execute("SELECT * FROM users WHERE id=" + id).fetchall()\n')
    b.seek(0);project=import_zip('nested',b);s=scan(project,DEFAULTS['audit']);assert 'web/routes.py' in s['sources'];assert all('\\' not in f['file'] for f in s['findings'])
    e=store.get('events','demo-001');c=correlate(e,collect(bundle(e)),s);assert c['matches'];assert [f['id'] for f in c['matches'][0]['chain']]==['web.routes.user','web.repository.find']

def test_github_archive_without_git(monkeypatch,client):
    import shutil
    from app.code_analysis.projects import import_git
    monkeypatch.setattr(shutil,'which',lambda _:None)
    archive=zip_bytes('owner-repo-abc/src/app.py','def hi():\n    return 1\n').getvalue()
    sha='a'*40
    def handler(req):
        if '/commits/' in req.url.path:return httpx.Response(200,json={'sha':sha})
        if '/zipball/' in req.url.path:return httpx.Response(302,headers={'location':'https://codeload.github.com/test/repo/zip/'+sha})
        return httpx.Response(200,content=archive)
    original=httpx.Client;monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    p=import_git('Git snapshot','https://github.com/test/repo.git','main');assert p['commit']==sha;assert p['source']=='git';assert read_file(p,'src/app.py').startswith('def hi')
