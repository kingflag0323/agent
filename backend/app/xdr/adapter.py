"""Read-only Sangfor XDR contract derived from the supplied Eolink export."""
from urllib.parse import quote
from datetime import datetime, timezone
import time
import ssl
import httpx
from app.xdr import demo
from app.xdr.labels import attack_label
from app.xdr.signing import signed_request
from app.database import store

CAPABILITIES = [
 ('events','POST','/api/xdr/v1/incidents/list','事件列表 / uuIds 精确查询'),
 ('event_proof','GET','/api/xdr/v1/incidents/:uuid/proof','事件时间线'),
 ('alerts','POST','/api/xdr/v1/alerts/list','关联告警列表'),
 ('alert_proof','GET','/api/xdr/v1/alerts/:uuid/proof','HTTP 请求和响应举证'),
 ('network','POST','/api/xdr/v1/analysislog/networksecurity/list','按目的 IP 与事件时间窗口查询'),
 ('logs','POST','/api/xdr/v1/securitylog/list','通过日志 uuIds 查询'),
 ('host','GET','/api/xdr/v1/incidents/:uuid/entities/host','事件主机资产实体'),
 ('ip','GET','/api/xdr/v1/incidents/:uuid/entities/ip','外网 IP 实体及已有情报标签'),
 ('dns','GET','/api/xdr/v1/incidents/:uuid/entities/dns','DNS 实体及已有情报标签'),
 ('file','GET','/api/xdr/v1/incidents/:uuid/entities/file','文件实体'),
 ('process','GET','/api/xdr/v1/incidents/:uuid/entities/process','进程实体'),
]

class XDRError(ValueError): pass

def items(data):
    if isinstance(data,list): return data
    if isinstance(data,dict) and isinstance(data.get('item'),list): return data['item']
    return []

def normalize(r):
    if not r.get('uuId'): raise XDRError('XDR 事件缺少 uuId')
    timestamp=r.get('endTime')
    try: timestamp=datetime.fromtimestamp(float(timestamp),timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError): timestamp=None
    return {'id':'live-'+str(r['uuId']),'external_id':str(r['uuId']), 'name':r.get('name','未命名事件'), 'attack_type':attack_label({'raw':r}), 'severity':{-1:'info',0:'info',1:'low',2:'medium',3:'high',4:'critical'}.get(r.get('incidentSeverity'),'unknown'),'asset':r.get('branchName') or r.get('hostIp','未知资产'),'asset_ip':r.get('hostIp',''),'source_ip':'','time':timestamp,'status':{0:'open',10:'investigating',40:'closed',50:'pending',60:'accepted',70:'contained',30:'protected'}.get(r.get('dealStatus'),'unknown'),'source':'live','project_id':None,'alert_ids':r.get('alertIds',[]),'description':r.get('description',''),'raw':r}

class XDRAdapter:
    def __init__(self,config): self.config=config
    async def request(self,cap,body=None,uuid=None):
        cfg=self.config
        if not cfg['base_url']: raise XDRError('请先配置 XDR Base URL；文档未定义认证协议，请按现场网关填写认证头。')
        spec=next((x for x in CAPABILITIES if x[0]==cap),None)
        if not spec: raise XDRError('Unsupported by current XDR API')
        _,method,path,_=spec
        if ':uuid' in path:
            if not uuid: raise XDRError('缺少 uuid')
            path=path.replace(':uuid',quote(str(uuid),safe=''))
        headers={}
        if cfg.get('auth_type','token') == 'token' and cfg['token']: headers[cfg['auth_header']]=(cfg['auth_scheme']+' '+cfg['token']).strip()
        url=cfg['base_url'].rstrip('/')+path
        request_args={'json':body or {}} if method=='POST' else {}
        if cfg.get('auth_type','token') in ('aksk','auth_code'):
            try: headers, payload = signed_request(method,url,body,cfg)
            except ValueError as e: raise XDRError(str(e)) from None
            request_args={'content':payload} if method=='POST' else {}
        try:
            verify=ssl.create_default_context(cafile=cfg['ca_bundle']) if cfg['verify_tls'] and cfg.get('ca_bundle') else cfg['verify_tls']
            async with httpx.AsyncClient(timeout=cfg['timeout'],verify=verify,trust_env=False,follow_redirects=False) as c:
                r=await c.request(method,url,headers=headers,**request_args)
                if r.status_code>=300: raise XDRError(f'XDR HTTP {r.status_code}')
                if len(r.content)>10_000_000: raise XDRError('XDR 响应超过 10 MB')
                result=r.json()
        except (httpx.HTTPError, ValueError, OSError) as e:
            if isinstance(e,XDRError): raise
            raise XDRError('XDR 连接或 JSON 解析失败（请检查地址、证书与认证配置）') from None
        if not isinstance(result,dict) or result.get('code')!='Success': raise XDRError('XDR 未返回 Success；请检查网关认证和请求参数')
        return result.get('data',{})

    async def events(self):
        if self.config['mode']=='demo': return [e for e in store.all_rows('events') if e['source']=='demo']
        result=[];end=int(time.time())
        for page in range(1,11):
            data=await self.request('events',{'startTimestamp':end-7*86400,'endTimestamp':end,'timeField':'endTime','page':page,'pageSize':200})
            if not isinstance(data,dict) or not isinstance(data.get('item'),list): raise XDRError('XDR 事件列表响应不符合文档 data.item 结构')
            batch=items(data); result.extend(normalize(e) for e in batch)
            if len(batch)<200 or len(result)>=data.get('total',2000): return result
        raise XDRError('七日内事件超过 2000 条；当前 Demo 同步上限为 2000，未保存不完整结果')

    async def bundle(self,event,include_network=True):
        if event['source']=='demo': return demo.bundle(event)
        uuid=event['external_id']
        proof=await self.request('event_proof',uuid=uuid)
        alerts=[]; warnings=[]
        ids=event.get('alert_ids') or [x.get('alertId') for p in (proof if isinstance(proof,list) else [proof]) for x in p.get('alertTimeLine',[]) if x.get('alertId')]
        if isinstance(ids,str): ids=[ids]
        if len(ids)>10: warnings.append('关联告警超过 10 条，本次调查只读取前 10 条举证')
        if ids:
            data=await self.request('alerts',{'uuIds':ids[:10],'page':1,'pageSize':10})
            for a in items(data):
                try: a['detail']=await self.request('alert_proof',uuid=a['uuId'])
                except XDRError as e: warnings.append(str(e))
                alerts.append(a)
        assets=[]; entities=[];network=[]
        try: assets=items(await self.request('host',uuid=uuid))
        except XDRError as e: warnings.append('主机实体: '+str(e))
        try: entities=items(await self.request('ip',uuid=uuid))
        except XDRError as e: warnings.append('IP 实体: '+str(e))
        from app.xdr.targets import destination_ips
        destinations=destination_ips(alerts)
        if include_network and (destinations or event.get('asset_ip')):
            try:
                at=int(datetime.fromisoformat(event['time']).timestamp()) if event.get('time') else int(time.time())
                network=items(await self.request('network',{'dstIps':destinations[:10] or [event['asset_ip']],'startTimestamp':at-300,'endTimestamp':at+300,'page':1,'pageSize':50}))
                if len(network)==50: warnings.append('网络日志达到 50 条上限；仅为时间/IP 关联候选，不视为同一攻击的已确认因果证据')
            except XDRError as e: warnings.append('网络日志: '+str(e))
        return {'event':event,'proof':proof,'alerts':alerts,'assets':assets,'entities':entities,'network':network,'warnings':warnings,'source':'live'}
