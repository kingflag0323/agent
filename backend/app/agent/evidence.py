import hashlib
import json
from app.database.store import now

def evidence(kind,source,title,content,provenance):
    serialized=json.dumps(content,ensure_ascii=False,sort_keys=True)
    digest=hashlib.sha256(serialized.encode()).hexdigest()
    return {'id':'ev-'+digest[:12], 'kind':kind,'source':source,'title':title,'content':content,'provenance':provenance,'sha256':digest,'collected_at':now()}

def collect(bundle):
    label='Demo Fact' if bundle['source']=='demo' else 'Fact'
    prefix='Mock XDR' if bundle['source']=='demo' else 'XDR API'
    e=bundle['event'];uuid=e.get('external_id',e['id'])
    result=[evidence(label,prefix,'安全事件',e,'POST /api/xdr/v1/incidents/list'),evidence(label,prefix,'事件举证时间线',bundle['proof'],f'GET /api/xdr/v1/incidents/{uuid}/proof')]
    for a in bundle['alerts']:
        result.append(evidence(label,prefix,'关联告警 / HTTP 举证',a,f"GET /api/xdr/v1/alerts/{a.get('uuId','unknown')}/proof"))
    for n in bundle['network']:
        result.append(evidence(label,prefix,'网络日志（时间/IP 关联）',n,'POST /api/xdr/v1/analysislog/networksecurity/list'))
    for a in bundle['assets']:
        result.append(evidence(label,prefix,'受影响资产',a,f'GET /api/xdr/v1/incidents/{uuid}/entities/host'))
    if bundle['entities']: result.append(evidence(label,prefix,'IP 实体 / IOC 候选',bundle['entities'],f'GET /api/xdr/v1/incidents/{uuid}/entities/ip'))
    return result
