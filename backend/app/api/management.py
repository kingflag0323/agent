import hashlib
import re
import uuid
from pathlib import PurePosixPath
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from app.database import store
from app.agent.knowledge import retrieve

router=APIRouter(prefix='/api')

def required(table,id):
    item=store.get(table,id)
    if not item:raise HTTPException(404,'记录不存在')
    return item

class Asset(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    host:str=Field(min_length=1,max_length=253)
    owner:str=Field(default='',max_length=100)
    environment:str=Field(default='test',max_length=50)
    description:str=Field(default='',max_length=2000)
    project_id:str=''
    web_url:str=Field(default='',max_length=500)
    web_path:str=Field(default='/',max_length=300)
    tags:list[str]=Field(default_factory=list,max_length=20)
    ssh_port:int=Field(default=22,ge=1,le=65535)
    ssh_user:str=Field(default='',max_length=64)
    key_path:str=Field(default='',max_length=1000)
    fingerprint:str=Field(default='',max_length=100)
    remote_root:str=Field(default='',max_length=1000)
    allowed_files:list[str]=Field(default_factory=list,max_length=100)
    verify_argv:list[str]=Field(default_factory=list,max_length=30)
    auto_repair:bool=False

def validate_asset(data):
    a=data.model_dump()
    if not re.fullmatch(r'[A-Za-z0-9.:%_-]+',a['host']):raise ValueError('主机应为 IP 或域名，不能包含 URL 或命令')
    if a['web_url']:
        from urllib.parse import urlsplit
        u=urlsplit(a['web_url'])
        if u.scheme not in ('http','https') or u.hostname!=a['host'] or u.username or u.password or u.query or u.fragment:raise ValueError('Web URL 必须是本资产主机的 HTTP(S) 地址，不含凭据或参数')
    if not a['web_path'].startswith('/') or '..' in PurePosixPath(a['web_path']).parts or any(x in a['web_path'] for x in ('?','#','\\','\x00')):raise ValueError('Web 路径须为 / 或 /pikachu 等部署前缀')
    if any(len(t)>60 for t in a['tags']):raise ValueError('资产标签最长 60 字')
    if a['project_id']:required('projects',a['project_id'])
    for p in a['allowed_files']:
        if not p or '\\' in p or '\x00' in p or PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts or not p.endswith('.py'):raise ValueError('修复范围须为仓库内 Python 文件的相对路径')
    if a['remote_root'] and (not a['remote_root'].startswith('/') or '..' in PurePosixPath(a['remote_root']).parts or a['remote_root']=='/' or '\x00' in a['remote_root']):raise ValueError('远程目录须为非根目录的绝对 POSIX 路径')
    if any(not x or len(x)>1000 or '\x00' in x for x in a['verify_argv']):raise ValueError('验证命令参数无效')
    if a['auto_repair'] and not all([a['project_id'],a['ssh_user'],a['key_path'],re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',a['fingerprint']),a['remote_root'],a['allowed_files'],a['verify_argv']]):raise ValueError('启用自主修复前需配置项目、SSH 密钥、主机 SHA256 指纹、远程目录、授权文件与验证命令')
    return a

@router.get('/assets')
def assets():return store.all_rows('assets')
@router.post('/assets')
def create_asset(data:Asset):
    return store.put('assets',dict(validate_asset(data),id='asset-'+uuid.uuid4().hex[:12],updated_at=store.now()))
@router.put('/assets/{id}')
def edit_asset(id:str,data:Asset):
    previous=required('assets',id)
    return store.put('assets',{**previous,**validate_asset(data),'id':id,'updated_at':store.now()})
@router.delete('/assets/{id}')
def delete_asset(id:str):
    required('assets',id);store.delete('assets',id);return {'deleted':True}
@router.post('/assets/{id}/test')
def test_asset(id:str):
    from app.agent.remediation import connect
    a=required('assets',id)
    with connect(a) as client:
        with client.open_sftp() as sftp:
            root=sftp.normalize(a['remote_root'] or '.')
    return {'connected':True,'remote_root':root,'message':'已校验指纹并完成只读 SFTP 连接；未修改主机'}

class Document(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=120)
    content:str=Field(min_length=1,max_length=64000)
    enabled:bool=True

def table_for(kind):
    if kind not in ('skills','knowledge'):raise HTTPException(404,'未知资源')
    return kind
@router.get('/agent/resources/{kind}')
def documents(kind:str):return store.all_rows(table_for(kind))
@router.post('/agent/resources/{kind}')
def import_document(kind:str,data:Document):
    table=table_for(kind)
    if len(store.all_rows(table))>=100:raise ValueError('每类最多 100 份文档，请先清理旧版本')
    return store.put(table,dict(data.model_dump(),id='doc-'+uuid.uuid4().hex[:12],sha256=hashlib.sha256(data.content.encode()).hexdigest(),updated_at=store.now()))
@router.put('/agent/resources/{kind}/{id}')
def update_document(kind:str,id:str,data:Document):
    table=table_for(kind);required(table,id)
    return store.put(table,dict(data.model_dump(),id=id,sha256=hashlib.sha256(data.content.encode()).hexdigest(),updated_at=store.now()))
@router.delete('/agent/resources/{kind}/{id}')
def delete_document(kind:str,id:str):
    table=table_for(kind);required(table,id);store.delete(table,id);return {'deleted':True}
@router.get('/agent/search')
def search(q:str=''):return retrieve(q[:2000])
@router.get('/remediations')
def remediations():return store.all_rows('remediations')
@router.post('/investigations/{id}/repair')
async def repair(id:str):
    from app.agent.remediation import remediate
    job=required('investigations',id)
    if job.get('remediation_pending'):raise HTTPException(409,'该调查已有自主修复正在执行')
    result=await remediate(job)
    job=required('investigations',id);job['remediation']=result;store.put('investigations',job)
    return result
