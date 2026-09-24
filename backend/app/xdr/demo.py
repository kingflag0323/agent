from datetime import datetime, timedelta, timezone
from copy import deepcopy
from app.database import store

SCENARIOS = [
 ('SQL 注入攻击 · 用户查询接口','SQL Injection','critical','/api/user',"id=1%27%20OR%20%271%27%3D%271",'shop-api-prod','10.20.1.15',0),
 ('系统命令注入 · 运维诊断接口','Command Injection','high','/api/diagnostic','host=127.0.0.1%3Bwhoami','shop-api-prod','10.20.1.15',0),
 ('SQL 注入探测 · 健康检查接口','SQL Injection','medium','/api/health',"id=1%27%20OR%201%3D1",'shop-api-prod','10.20.1.15',1),
 ('SSH 登录失败次数异常','Brute Force','medium','', '', 'bastion-01','10.20.2.8',1),
 ('外联可疑域名 · 待补充证据','Suspicious DNS','low','', '', 'worker-02','10.20.3.22',2),
 ('Web 服务目录探测','Reconnaissance','low','/robots.txt','', 'web-gateway','10.20.1.2',3),
]

def seed():
    if store.get('events','demo-001'): return
    t = datetime.now(timezone.utc)
    for i,(name,kind,severity,path,query,asset,ip,days) in enumerate(SCENARIOS):
        at = (t-timedelta(days=days, minutes=i*17+4)).isoformat()
        id = f'demo-{i+1:03}'
        store.put('events', {'id':id,'name':name,'attack_type':kind,'severity':severity,'asset':asset,'asset_ip':ip,'source_ip':f'198.51.100.{42+i}', 'time':at,'status':'open', 'source':'demo','project_id':'demo-shop' if i<3 else None, 'alert_ids':[f'alert-{id}'], 'path':path,'query':query,'description':'合成演示事件；不代表真实攻击已发生或利用已成功。','raw':{'fixture':'demo/xdr','scenario':i+1}})

def bundle(event):
    e=deepcopy(event);id=e['id'];http=bool(e['path'])
    alert={'uuId':e['alert_ids'][0],'name':e['name'],'srcIp':e['source_ip'],'dstIp':e['asset_ip'],'threatSubTypeDesc':e['attack_type'],'attackResult':0,'stage':30 if http else 20,'lastTime':e['time']}
    proof={'name':e['name'],'uuId':id,'alertTimeLine':[{'alertId':alert['uuId'],'name':e['name'],'stage':alert['stage'],'lastTime':e['time']}]}
    records=[]
    if http:
        request=f"GET {e['path']}{'?' + e['query'] if e['query'] else ''} HTTP/1.1\r\nHost: shop.example.test\r\nUser-Agent: demo-fixture/1.0"
        alert['proof']=[{'dataType':'http','requestHead':request,'requestBody':'','responseHead':'HTTP/1.1 200 OK','responseBody':'[demo response omitted; exploitation outcome unknown]'}]
        records=[{'uuId':'net-'+id,'srcIp':e['source_ip'],'dstIp':e['asset_ip'],'dstPort':443,'l7Protocol':'http','recordTimestamp':e['time'],'requestHead':request,'url':e['path']+'?'+e['query'],'attackState':0}]
    else: alert['proof']=[{'dataType':'raw','rawProofData':e['description']}]
    return {'event':e,'proof':proof,'alerts':[alert], 'network':records, 'assets':[{'hostIp':e['asset_ip'],'assetName':e['asset'],'hostAssetId':'demo-asset-01'}], 'entities':[{'ip':e['source_ip'],'threatLevel':0,'intelligenceTag':[]}], 'warnings':[], 'source':'demo'}
