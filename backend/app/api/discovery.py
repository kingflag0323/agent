"""Explicit, bounded RFC1918 TCP discovery. No credential guessing or exploit probes."""
import asyncio
import ipaddress
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.database import store
from app.api.management import Asset
router=APIRouter(prefix='/api/assets')
TASKS=set()
PRIVATE=[ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
class Discovery(BaseModel):
    cidr:str
    ports:list[int]=Field(default=[22,80,443,8080,8081,3306],min_length=1,max_length=12)

def scope(cidr,ports):
    try:network=ipaddress.ip_network(cidr,strict=False)
    except ValueError:raise ValueError('请输入 IPv4 地址或 CIDR') from None
    if network.version!=4 or network.num_addresses>256 or not any(network.subnet_of(n) for n in PRIVATE):raise ValueError('仅支持明确指定的 RFC1918 内网，单次最多 /24（256 个地址）')
    if any(not 1<=p<=65535 for p in ports):raise ValueError('端口范围 1–65535')
    return [str(ip) for ip in network.hosts()]

async def probe(host,port):
    try:
        _,writer=await asyncio.wait_for(asyncio.open_connection(host,port),timeout=.8)
        writer.close()
        try:await writer.wait_closed()
        except OSError:pass
        return port
    except (TimeoutError,OSError):return None

async def execute(job):
    semaphore=asyncio.Semaphore(48)
    async def one(host,port):
        async with semaphore:return await probe(host,port)
    job['status']='running';store.put('discoveries',job)
    try:
        for offset in range(0,len(job['hosts']),8):
            batch=job['hosts'][offset:offset+8]
            results=await asyncio.gather(*(asyncio.gather(*(one(host,p) for p in job['ports'])) for host in batch))
            for host,result in zip(batch,results):
                ports=[p for p in result if p]
                if ports:
                    existing=next((a for a in store.all_rows('assets') if a['host']==host),None)
                    asset=existing or dict(Asset(name=host,host=host,environment='discovered').model_dump(),id='asset-'+uuid.uuid4().hex[:12],source='discovery')
                    asset.update(observed_ports=ports,last_seen=store.now(),updated_at=store.now())
                    store.put('assets',asset);job['found'].append({'asset_id':asset['id'],'host':host,'ports':ports})
                job['checked']+=1
            store.put('discoveries',job)
        job['status']='completed'
    except asyncio.CancelledError:job['status']='interrupted';raise
    except Exception:job['status']='failed';job['error']='发现任务失败，已有资产记录保留'
    finally:job['finished_at']=store.now();store.put('discoveries',job)

@router.post('/discovery',status_code=202)
async def start(body:Discovery):
    hosts=scope(body.cidr,body.ports)
    if TASKS:raise HTTPException(409,'已有资产发现任务运行中')
    job={'id':'discovery-'+uuid.uuid4().hex[:12],'cidr':body.cidr,'hosts':hosts,'ports':sorted(set(body.ports)),'status':'queued','checked':0,'total':len(hosts),'found':[],'created_at':store.now()}
    store.put('discoveries',job)
    task=asyncio.create_task(execute(job));TASKS.add(task);task.add_done_callback(TASKS.discard)
    return job
@router.get('/discovery/{id}')
def progress(id:str):
    job=store.get('discoveries',id)
    if not job:raise HTTPException(404,'发现任务不存在')
    return job
