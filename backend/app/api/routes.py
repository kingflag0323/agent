import asyncio
import io
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.core import settings
from app.core.config import ALLOWED_ROOTS
from app.database import store
from app.xdr.adapter import XDRAdapter,CAPABILITIES
from app.xdr.labels import attack_label
from app.code_analysis import projects, scanner
from app.agent.workflow import run_job
from app.agent.report import markdown
from app.llm.provider import LLMProvider

router=APIRouter(prefix='/api')
TASKS=set()

def required(table,id):
    item=store.get(table,id)
    if not item: raise HTTPException(404,'记录不存在')
    return item

def active_events():
    mode=settings.load()['xdr']['mode'];source='demo' if mode=='demo' else 'live'
    return sorted([{**x,'attack_type':attack_label(x)} for x in store.all_rows('events') if x['source']==source],key=lambda x:x.get('time') or '',reverse=True)

@router.get('/health')
def health(): return {'status':'ok','database':'sqlite','version':'0.1.0'}

@router.get('/dashboard')
def dashboard():
    events=active_events();ids={e['id'] for e in events};jobs=[j for j in store.all_rows('investigations') if j['event']['id'] in ids];projects_list=store.all_rows('projects');scans=[store.get('scans',p['last_scan_id']) for p in projects_list if p.get('last_scan_id')];counts=Counter(e['severity'] for e in events);today=datetime.now(timezone.utc).date();trend=[]
    for i in range(6,-1,-1):
        day=str(today-timedelta(days=i));es=[e for e in events if (e.get('time') or '').startswith(day)]
        trend.append({'date':day[5:],'events':len(es),'high':sum(e['severity'] in ('high','critical') for e in es)})
    linked={j['event']['id'] for j in jobs if j['status']=='completed' and j.get('correlation',{}).get('matches')}
    assets=Counter(e['asset'] for e in events)
    return {'mode':settings.load()['xdr']['mode'],'total':len(events),'today':sum((e.get('time') or '').startswith(str(today)) for e in events),'severity':dict(counts),'assets':len({e['asset_ip'] for e in events if e['asset_ip']}),'vulnerabilities':sum(len(s['findings']) for s in scans if s),'linked':len(linked),'investigations':len(jobs),'running':sum(j['status'] in ('running','queued') for j in jobs),'trend':trend,'types':[{'name':k,'value':v} for k,v in Counter(e['attack_type'] for e in events).items()],'risk_assets':[{'name':k,'count':v} for k,v in assets.most_common(5)],'recent':events[:5],'jobs':[{'id':j['id'],'name':j['event']['name'],'status':j['status']} for j in jobs[:4]],'scope':'当前数据源已同步事件；Live 为最近 7 天，Demo 为固定场景。今日按 UTC 统计。'}

@router.get('/events')
def events(q:str='',severity:str='',status:str='',page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
    rows=[e for e in active_events() if (not q or q.lower() in (e['name']+e['asset']+e['asset_ip']+e['attack_type']).lower()) and (not severity or e['severity']==severity) and (not status or e['status']==status)]
    return {'items':rows[(page-1)*page_size:page*page_size],'total':len(rows),'page':page,'page_size':page_size}

@router.post('/events/sync')
async def sync():
    rows=await XDRAdapter(settings.load()['xdr']).events()
    for row in rows:
        previous=store.get('events',row['id'])
        if previous:row['project_id']=previous.get('project_id')
        store.put('events',row)
    return {'count':len(rows),'mode':settings.load()['xdr']['mode']}

@router.get('/events/{id}')
def event(id:str):
    e=required('events',id);jobs=[j for j in store.all_rows('investigations') if j['event']['id']==id]
    bindings=[a for a in store.all_rows('assets') if a['host']==e.get('asset_ip') and a.get('project_id')]
    if not e.get('project_id') and len(bindings)==1:e={**e,'project_id':bindings[0]['project_id'],'asset_id':bindings[0]['id']}
    return {**e,'attack_type':attack_label(e),'investigations':[{'id':j['id'],'status':j['status'],'created_at':j['created_at']} for j in jobs]}

@router.get('/events/{id}/evidence')
async def event_evidence(id:str):
    from app.agent.evidence import collect
    bundle=await XDRAdapter(settings.load()['xdr']).bundle(required('events',id))
    return {'evidence':collect(bundle),'warnings':bundle['warnings'],'source':bundle['source']}

class Binding(BaseModel): project_id:str
@router.put('/events/{id}/project')
def bind(id:str,body:Binding):
    e=required('events',id);required('projects',body.project_id);e['project_id']=body.project_id;store.put('events',e);return e

class InvestigationInput(BaseModel):
    event_id:str
    project_id:str

@router.post('/investigations',status_code=202)
async def investigate(body:InvestigationInput):
    event=required('events',body.event_id);project=required('projects',body.project_id)
    if len(TASKS)>=2: raise HTTPException(429,'同时最多运行 2 个调查，请稍后重试')
    for j in store.all_rows('investigations'):
        if j['event']['id']==event['id'] and j['project']['id']==project['id'] and j['status'] in ('queued','running'): return {'id':j['id'],'status':j['status']}
    job={'id':'inv-'+uuid.uuid4().hex[:12],'event':event,'project':project,'status':'queued','created_at':store.now(),'timeline':[],'evidence':[],'warnings':[]}
    store.put('investigations',job)
    task=asyncio.create_task(run_job(job['id'],settings.load()));TASKS.add(task);task.add_done_callback(TASKS.discard)
    return {'id':job['id'],'status':'queued'}

@router.get('/investigations')
def investigations():
    return [{k:v for k,v in j.items() if k in ('id','event','project','status','created_at','completed_at','error','correlation','report')} for j in store.all_rows('investigations')]

@router.get('/investigations/{id}')
def investigation(id:str): return required('investigations',id)

@router.get('/investigations/{id}/report')
def report(id:str,format:Literal['markdown','json','docx']='markdown'):
    j=required('investigations',id)
    if j['status']!='completed': raise HTTPException(409,'调查尚未完成，不能导出正式报告')
    if format=='docx':
        from app.agent.report import word
        return Response(word(j),media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',headers={'Content-Disposition':f'attachment; filename="{id}.docx"'})
    if format=='json': return j
    return Response(markdown(j),media_type='text/markdown; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{id}.md"'})

@router.get('/projects')
def list_projects():
    result=[]
    for p in store.all_rows('projects'):
        s=store.get('scans',p.get('last_scan_id',''))
        result.append({**p,'findings_count':len(s['findings']) if s else 0,'scan_status':s['status'] if s else 'not_scanned'})
    return result

class ProjectInput(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    source:Literal['local','git']='local'
    path:str=Field(default='',max_length=1000)
    git_url:str=Field(default='',max_length=1000)
    branch:str=Field(default='',max_length=150)

@router.post('/projects',status_code=201)
async def create_project(body:ProjectInput):
    if body.source=='local': return await asyncio.to_thread(projects.create,body.name,body.path)
    return await asyncio.to_thread(projects.import_git,body.name,body.git_url,body.branch)

@router.post('/projects/upload',status_code=201)
async def upload_project(name:str=Form(...,min_length=1,max_length=100),file:UploadFile=File(...)):
    data=await file.read(projects.MAX_BYTES+1)
    if len(data)>projects.MAX_BYTES: raise HTTPException(413,'ZIP 超过 25 MB')
    import zipfile
    try: return await asyncio.to_thread(projects.import_zip,name,io.BytesIO(data))
    except zipfile.BadZipFile: raise ValueError('无效 ZIP 文件') from None

@router.get('/projects/{id}/files')
def files(id:str):
    p=required('projects',id);files,skipped=projects.source_files(projects.allowed_root(p['path']))
    return {'files':[f.relative_to(p['path']).as_posix() for f in files],'skipped':skipped}

@router.get('/projects/{id}/file')
def file_content(id:str,path:str): return {'path':path,'content':projects.read_file(required('projects',id),path)}

@router.post('/projects/{id}/scan')
async def scan_project(id:str):
    result=await asyncio.to_thread(scanner.scan,required('projects',id),settings.load()['audit'])
    return {k:v for k,v in result.items() if k!='sources'}

@router.get('/projects/{id}/scan')
def last_scan(id:str):
    p=required('projects',id)
    if not p.get('last_scan_id'):return None
    return {k:v for k,v in required('scans',p['last_scan_id']).items() if k!='sources'}

@router.get('/settings')
def get_settings():return {**settings.public(),'allowed_roots':[str(p) for p in projects.allowed_roots()]}

@router.put('/settings')
def update_settings(body:dict):return settings.save(body)

@router.post('/settings/test/{provider}')
async def test_connection(provider:Literal['xdr','llm']):
    cfg=settings.load()
    if provider=='xdr':
        if cfg['xdr']['mode']=='demo' and cfg['xdr'].get('auth_type','token')=='token':return {'ok':True,'mode':'demo','message':'Demo 适配器可用；未测试真实 XDR 连接'}
        data=await XDRAdapter(cfg['xdr']).request('events',{'page':1,'pageSize':5})
        return {'ok':True,'mode':'live','message':'事件列表返回 Success','items':len(data.get('item',[])) if isinstance(data,dict) else 0}
    result=await LLMProvider(cfg['llm']).analyze({'task':'Connection test only. Reply OK.'})
    return {'ok':True,'mode':cfg['llm']['mode'],'message':'Mock Provider 可用；未调用外部模型' if result['provider']=='mock' else '模型 API 连接成功'}

@router.get('/capabilities')
def capabilities():return {'documented_endpoint_count':129,'implemented':[{'name':n,'method':m,'path':p,'description':d,'status':'contract_implemented_not_live_verified'} for n,m,p,d in CAPABILITIES],'unsupported':[{'name':'threat_intelligence_lookup','reason':'Unsupported by current XDR API；只能读取实体已有情报标签'},{'name':'authentication_exchange','reason':'材料提供 AK/SK 与授权码签名；未提供在线密钥申请/交换接口'},{'name':'assets_success_schema','reason':'资产列表文档仅给出 InvalidParameter 响应；使用事件主机实体获取资产'}]}
