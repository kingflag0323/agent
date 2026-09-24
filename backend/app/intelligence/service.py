"""Public CVE feeds with durable upserts, bounded downloads and periodic sync."""
import asyncio
import hashlib
from datetime import datetime,timedelta,timezone
import httpx
from app.database import store
from app.core import settings
LOCK=asyncio.Lock()
CISA='https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
CISA_MIRROR='https://raw.githubusercontent.com/cisagov/kev-data/main/known_exploited_vulnerabilities.json'
NVD='https://services.nvd.nist.gov/rest/json/cves/2.0'

async def fetch(url,headers=None,params=None):
    async with httpx.AsyncClient(timeout=httpx.Timeout(30,connect=8),trust_env=False,follow_redirects=False) as client:
        async with client.stream('GET',url,headers=headers,params=params) as response:
            if response.status_code!=200:raise ValueError('情报源返回 HTTP '+str(response.status_code))
            data=bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data)>24*1024*1024:raise ValueError('情报响应超过 24 MB 上限')
    import json
    try:return json.loads(data)
    except ValueError:raise ValueError('情报源返回无效 JSON') from None

def normalize(provider,data):
    out=[]
    if provider=='cisa':
        if not isinstance(data.get('vulnerabilities'),list):raise ValueError('CISA 数据结构无效')
        for v in data['vulnerabilities']:
            out.append({'cve':v['cveID'],'title':v['vulnerabilityName'],'description':v['shortDescription'],'vendor':v['vendorProject'],'product':v['product'],'date':v['dateAdded'],'date_kind':'KEV 收录日期','severity':'unknown','score':None,'known_exploited':True,'action':v.get('requiredAction',''),'references':['https://www.cisa.gov/known-exploited-vulnerabilities-catalog'],'upstream_modified':data.get('dateReleased','')})
    else:
        if not isinstance(data.get('vulnerabilities'),list):raise ValueError('NVD 数据结构无效')
        for item in data['vulnerabilities']:
            v=item['cve'];metrics=v.get('metrics',{});metric=(metrics.get('cvssMetricV40') or metrics.get('cvssMetricV31') or metrics.get('cvssMetricV30') or [{}])[0].get('cvssData',{})
            description=next((d['value'] for d in v.get('descriptions',[]) if d.get('lang')=='en'),'')
            out.append({'cve':v['id'],'title':v['id'],'description':description,'vendor':'','product':'','date':v['published'],'date_kind':'NVD 发布日期','severity':metric.get('baseSeverity','unknown').lower(),'score':metric.get('baseScore'),'known_exploited':bool(v.get('cisaExploitAdd')),'action':v.get('cisaRequiredAction',''),'references':[x['url'] for x in v.get('references',[])][:10],'upstream_modified':v.get('lastModified','')})
    for row in out:
        row.update(id=provider+':'+row['cve'],provider=provider,fetched_at=store.now())
    return out

async def sync():
    if LOCK.locked():raise ValueError('已有情报同步运行中')
    async with LOCK:
        cfg=settings.load()['ti'];provider=cfg['provider'];state=store.get('ti_sync',provider) or {'id':provider}
        state.update(status='running',attempted_at=store.now());store.put('ti_sync',state)
        try:
            if provider=='cisa':
                try:
                    data=await fetch(CISA);state['source_url']=CISA
                except (httpx.HTTPError,ValueError):
                    data=await fetch(CISA_MIRROR);state['source_url']=CISA_MIRROR
                rows=normalize(provider,data)
            else:
                end=datetime.now(timezone.utc);start=end-timedelta(days=cfg['lookback_days']);rows=[];offset=0
                while True:
                    params={'pubStartDate':start.isoformat(timespec='milliseconds'),'pubEndDate':end.isoformat(timespec='milliseconds'),'resultsPerPage':2000,'startIndex':offset}
                    data=await fetch(NVD,{'apiKey':cfg['api_key']} if cfg['api_key'] else {},params)
                    page=normalize(provider,data);rows.extend(page);offset+=len(page)
                    if offset>=int(data.get('totalResults',0)):break
                    if not page or offset>=10000:raise ValueError('NVD 数据超过单次 10000 条，请缩短回溯窗口；旧数据保留')
                    await asyncio.sleep(6)
            # No deletion on feed failures or moving NVD windows.
            for row in rows:store.put('intelligence',row)
            state.update(status='completed',last_success=store.now(),count=len(rows),error='')
        except asyncio.CancelledError:
            state.update(status='interrupted',error='服务停止，同步未完成');raise
        except Exception as exc:
            state.update(status='failed',error=str(exc) if isinstance(exc,ValueError) else '同步失败（'+type(exc).__name__+'）')
        finally:store.put('ti_sync',state)
        return state

async def scheduler():
    while True:
        cfg=settings.load()['ti'];state=store.get('ti_sync',cfg['provider']) or {}
        stamp=state.get('attempted_at')
        due=not stamp or (datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds()>=cfg['interval_hours']*3600
        if cfg['enabled'] and due and not LOCK.locked():await sync()
        await asyncio.sleep(30)
