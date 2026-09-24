import asyncio
import hashlib
import io
import zipfile
import pytest
from app.database import store
from app.core import settings
from app.core.config import DATA,REPOS
from app.api import discovery
from app.intelligence import service
from app.code_analysis.php_analysis import analyze
from app.correlation.engine import correlate
from app.agent.evidence import evidence
from app.agent.report import word

SOURCES={'vul/sqli.php':'''<?php
$ROOT='../';
include_once $ROOT.'inc/mysql.php';
$name=$_GET['name'];
$query="SELECT id FROM users WHERE name='$name'";
$result=execute($link,$query);
''','inc/mysql.php':'''<?php
function execute($link,$query){return mysqli_query($link,$query);}
''','other/mysql.php':'''<?php
function execute($link,$query){return mysqli_query($link,$query);}
'''}

def php_scan(sources):
    hashes={k:hashlib.sha256(v.encode()).hexdigest() for k,v in sources.items()}
    r=analyze(sources,hashes)
    return {**r,'index':{'routes':[],'functions':[]},'sources':sources,'hashes':hashes}

def test_php_included_wrapper_trace_and_exact_route():
    result=php_scan(SOURCES)
    assert len(result['findings'])==1
    f=result['findings'][0]
    assert (f['file'],f['line'],f['cwe'])==('vul/sqli.php',6,'CWE-89')
    assert f['trace'][-1]['file']=='inc/mysql.php'
    e=evidence('Fact','XDR','关联告警 / HTTP 举证',{'requestHead':'GET /pikachu/vul/sqli.php?name=test HTTP/1.1'},'test')
    event={'name':'SQL Injection','attack_type':'SQL Injection'}
    assert not correlate(event,[e],result)['matches']
    matches=correlate(event,[e],result,'/pikachu')['matches'];assert len(matches)==1 and matches[0]['confidence']=='medium'
    assert not correlate({'name':'SSH login','attack_type':'Brute Force'},[e],result,'/pikachu')['matches']

def test_php_no_guessing_unresolved_wrapper_and_sanitized():
    source=dict(SOURCES);source['vul/sqli.php']=source['vul/sqli.php'].replace("include_once $ROOT.'inc/mysql.php';",'')
    assert php_scan(source)['findings']==[]
    source=dict(SOURCES);source['vul/sqli.php']=source['vul/sqli.php'].replace("$name=$_GET['name']","$name=intval($_GET['name'])")
    assert php_scan(source)['findings']==[]
    assert php_scan({'x.php':"<?php $s='shell_exec($_GET[x])'; // mysqli_query($link,$_GET[x]);"})['findings']==[]

def test_php_command_rule():
    r=php_scan({'a.php':"<?php $ip=$_POST['ip']; shell_exec('ping '.$ip);"})
    assert r['findings'][0]['cwe']=='CWE-78'
    assert r['findings'][0]['parameters']==['ip']
    assert php_scan({'a.php':"<?php $ip=escapeshellarg($_POST['ip']); shell_exec('ping '.$ip);"})['findings']==[]

def test_discovery_scope_boundary():
    assert discovery.scope('172.20.0.252/32',[80])==['172.20.0.252']
    for cidr in ['8.8.8.8','127.0.0.1','169.254.1.0/24','172.20.0.0/16','::1','10.0.0.0/7']:
        with pytest.raises(ValueError):discovery.scope(cidr,[80])
    with pytest.raises(ValueError):discovery.scope('10.0.0.1',[65536])

def test_discovery_upsert_preserves_binding(client,monkeypatch):
    asset=client.post('/api/assets',json={'name':'Owned asset','host':'172.20.0.252','owner':'owner','project_id':'demo-shop'}).json()
    async def probe(host,port):return port if port==80 else None
    monkeypatch.setattr(discovery,'probe',probe)
    job={'id':'discovery-test','hosts':['172.20.0.252'],'ports':[22,80],'status':'queued','checked':0,'total':1,'found':[]}
    asyncio.run(discovery.execute(job));updated=store.get('assets',asset['id'])
    assert job['status']=='completed' and updated['observed_ports']==[80]
    assert updated['owner']=='owner' and updated['project_id']=='demo-shop'
    store.delete('assets',asset['id'])

def test_intelligence_upsert_and_failure_preserves_data(client,monkeypatch):
    sample={'dateReleased':'2026-09-22','vulnerabilities':[{'cveID':'CVE-2099-1000','vulnerabilityName':'Test vulnerability','shortDescription':'description','vendorProject':'Vendor','product':'Product','dateAdded':'2026-09-22','requiredAction':'Patch'}]}
    async def fake(*args,**kwargs):return sample
    monkeypatch.setattr(service,'fetch',fake)
    settings.save({'ti':{'provider':'cisa','enabled':False}})
    assert asyncio.run(service.sync())['status']=='completed'
    assert asyncio.run(service.sync())['count']==1
    rows=client.get('/api/intelligence?q=CVE-2099-1000').json();assert rows['total']==1
    assert rows['items'][0]['date_kind']=='KEV 收录日期' and rows['items'][0]['score'] is None
    async def failed(*args,**kwargs):raise ValueError('HTTP 503')
    monkeypatch.setattr(service,'fetch',failed)
    assert asyncio.run(service.sync())['status']=='failed'
    assert client.get('/api/intelligence?q=CVE-2099-1000').json()['total']==1

def test_nvd_normalization_and_settings_mask(client):
    data={'vulnerabilities':[{'cve':{'id':'CVE-2099-2000','published':'2026-09-22','descriptions':[{'lang':'en','value':'Description'}],'metrics':{'cvssMetricV31':[{'cvssData':{'baseScore':9.8,'baseSeverity':'CRITICAL'}}]}}}]}
    r=service.normalize('nvd',data)[0];assert r['score']==9.8 and r['severity']=='critical' and not r['known_exploited']
    response=client.put('/api/settings',json={'ti':{'api_key':'test-nvd-secret'}})
    assert response.status_code==200 and 'test-nvd-secret' not in response.text
    assert response.json()['ti']['api_key_configured']
    assert client.put('/api/settings',json={'ti':{'interval_hours':0}}).status_code==400

def test_workspace_directory_applies_to_imports(client):
    from app.code_analysis.projects import repository_root,allowed_root
    path=DATA/'configured-workspace';path.mkdir(exist_ok=True)
    try:
        assert client.put('/api/settings',json={'workspace':{'working_directory':str(path)}}).status_code==200
        assert repository_root()==path and allowed_root(path)==path
        assert client.put('/api/settings',json={'workspace':{'working_directory':'relative/path'}}).status_code==400
    finally:settings.save({'workspace':{'working_directory':str(REPOS)}})

def test_word_document_contains_trace_and_evidence(client):
    job={'id':'inv-word','status':'completed','event':{'name':'PHP 测试','source':'live','asset_ip':'172.20.0.252'},'project':{'name':'pikachu'},'timeline':[{'name':'Static analysis','tool':'Tree-sitter PHP','status':'completed','note':'分析代码'}],'correlation':{'summary':'找到候选','matches':[]},'evidence':[]}
    store.put('investigations',job)
    response=client.get('/api/investigations/inv-word/report?format=docx')
    assert response.status_code==200 and 'wordprocessingml' in response.headers['content-type']
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        xml=z.read('word/document.xml').decode();assert '调查思维链' in xml and 'Static analysis' in xml and 'pikachu' in xml

def test_php_workflow_end_to_end(client,monkeypatch):
    from app.code_analysis.projects import create
    from app.agent.workflow import run_job
    from app.xdr.adapter import XDRAdapter
    from app.xdr.demo import bundle
    root=DATA/'repositories/php-workflow';root.mkdir(parents=True,exist_ok=True)
    for file,source in SOURCES.items():
        path=root/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source,encoding='utf-8')
    project=create('PHP workflow fixture',root)
    event={**store.get('events','demo-001'),'path':'/vul/sqli.php','query':"name=test%27",'project_id':project['id']}
    async def fixture(self,*args,**kwargs):return bundle(event)
    monkeypatch.setattr(XDRAdapter,'bundle',fixture)
    job={'id':'inv-php-workflow','event':event,'project':project,'status':'queued','timeline':[],'evidence':[],'warnings':[],'created_at':store.now()}
    store.put('investigations',job);asyncio.run(run_job(job['id'],settings.load()))
    actual=store.get('investigations',job['id'])
    assert actual['status']=='completed',actual.get('error')
    match=actual['correlation']['matches'][0];assert match['finding']['line']==6
    assert match['chain'][-1]['file']=='inc/mysql.php'
    assert actual['review']['status']=='passed'
    assert any(e['source']=='PHP syntax' and e['content']['file']=='inc/mysql.php' for e in actual['evidence'])
    assert not actual['remediation_pending']
    assert client.get('/api/investigations/'+job['id']+'/report?format=docx').status_code==200

def test_destination_not_incident_host_or_http_header():
    from app.xdr.targets import destination_ips
    alerts=[{'srcIp':['172.16.125.188'],'dstIp':['172.20.0.252'],'proof':[{'requestHead':'GET / HTTP/1.1\r\nHost: attacker.example','requestBody':{'dstIp':'10.0.0.99'}}]}]
    assert destination_ips(alerts)==['172.20.0.252']

def test_deepseek_thinking_and_bounded_valid_context(monkeypatch):
    import httpx
    from app.llm.provider import LLMProvider,bounded_context
    captured={};original=httpx.AsyncClient
    def handler(request):
        import json
        captured.update(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'测试研判','reasoning_content':'DO NOT EXPOSE INTERNAL REASONING'},'finish_reason':'stop'}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    cfg={**settings.load()['llm'],'mode':'compatible','base_url':'https://api.deepseek.com','model':'deepseek-flash','thinking_mode':'auto'}
    result=asyncio.run(LLMProvider(cfg).analyze({'evidence':{'requestHead':'GET / HTTP/1.1\r\nCookie: session-secret','text':'x'*50000}}))
    assert captured['thinking']=={'type':'disabled'}
    assert 'session-secret' not in captured['messages'][1]['content']
    assert 'INTERNAL REASONING' not in str(result)
    import json
    assert isinstance(json.loads(captured['messages'][1]['content']),dict)


def test_attack_labels_use_platform_text_without_guessing_numeric_codes():
    from app.xdr.labels import attack_label
    assert attack_label({'attack_type':'020307','raw':{'riskTag':['SQL注入','疑似业务误报']}})=='SQL注入'
    assert attack_label({'attack_type':'020201','raw':{'riskTag':['SQL注入','命令执行'],'threatDefineName':['定向攻击']}})=='定向攻击'
    assert attack_label({'attack_type':'020404','raw':{'incidentThreatTypeName':'SSH 暴力破解'}})=='SSH 暴力破解'
    assert attack_label({'attack_type':'999999','raw':{}})=='未分类威胁'
    assert attack_label({'attack_type':'SQL Injection'})=='SQL 注入'
