import re
from urllib.parse import urlsplit, unquote, parse_qs
from app.code_analysis.ast_index import call_path

# Only observed HTTP fields are used for entrypoint extraction, never LLM text.
def http_entries(evidence):
    found=[]
    direct_ids={e['id'] for e in evidence if e['title']=='关联告警 / HTTP 举证'}
    def walk(value,ev_id):
        if isinstance(value,dict):
            for key,v in value.items():
                if key in ('requestHead','url') and isinstance(v,str):
                    m=re.search(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD)\s+(\S+)\s+HTTP/',v)
                    url=m.group(2) if m else v if key=='url' else None
                    if url:
                        parsed=urlsplit(url);path=unquote(parsed.path)
                        if path.startswith('/'):
                            found.append({'path':path,'method':m.group(1) if m else None,'query':parsed.query,'payload':unquote(parsed.query),'parameters':list(parse_qs(parsed.query,keep_blank_values=True)),'evidence_id':ev_id,'direct_alert':ev_id in direct_ids,'origin':'requestHead' if m else 'url'})
                else: walk(v,ev_id)
        elif isinstance(value,list):
            for v in value: walk(v,ev_id)
    for e in evidence:
        if e['kind'] in ('Fact','Demo Fact'): walk(e['content'],e['id'])
    unique={}
    for x in found:
        key=(x['path'],x['method'],x['query']);unique.setdefault(key,x)
    return list(unique.values())

def attack_class(event,entries):
    payload=' '.join(e['payload'] for e in entries).lower()
    name=(event['attack_type']+' '+event['name']).lower()
    if ('sql' in name or '注入' in name and '数据库' in name) or re.search(r"\bunion\s+select\b|\bor\s+['\d].*=",payload): return 'SQL Injection','CWE-89'
    if 'command' in name or '命令' in name: return 'Command Injection','CWE-78'
    return event['attack_type'],None

def correlate(event,evidence,scan,web_path="/"):
    entries=http_entries(evidence);kind,cwe=attack_class(event,entries);matches=[];candidates=[]
    for entry in entries:
        for route in scan['index']['routes']:
            if entry['path']!=route['path'] or entry['method'] and entry['method'] not in route['methods']: continue
            candidates.append(route)
            for finding in scan['findings']:
                if finding['cwe']!=cwe: continue
                chain=call_path(scan['index'],route['function_id'],finding['file'],finding['line'])
                if not chain: continue
                params=sorted(set(entry['parameters']) & set(route['parameters']))
                reasons=[f"HTTP 路径 {entry['path']} 与装饰器路由完全匹配",f"AST 可解析调用链到达 {finding['file']}:{finding['line']}",f"Bandit {finding['rule']} 报告 {finding['cwe']}，与攻击类别一致"]
                if params: reasons.append('请求参数与入口函数参数匹配：'+', '.join(params))
                matches.append({'finding':finding,'entry':entry,'route':route,'chain':chain,'confidence':'high' if params and entry['method'] and entry['direct_alert'] else 'medium','reasons':reasons,'evidence_ids':[entry['evidence_id']],'kind':'AI Inference','method':'deterministic AST + SAST correlation','limitations':['调用图可达性不是完整污点证明；需人工检查沿途校验与清洗。','尚未验证线上部署版本与此代码快照一致。','HTTP 状态码和静态漏洞不能证明这次利用成功。']})
    for entry in entries:
        for finding in scan['findings']:
            if finding.get('language')!='php' or finding['cwe']!=cwe:continue
            path=web_path.rstrip('/')+'/'+finding['file']
            if entry['path']!=path:continue
            trace=finding['trace']
            matches.append({'finding':finding,'entry':entry,'route':{'path':path,'parameters':finding['parameters']},'chain':trace,'confidence':'medium','reasons':[f"HTTP 路径与部署前缀 + PHP 文件完全匹配：{path}",f"Tree-sitter PHP 识别 HTTP 参数 {', '.join(finding['parameters'])} 经赋值到达 {finding['file']}:{finding['line']}",f"规则 {finding['rule']} / {finding['cwe']} 与攻击类别一致"],'evidence_ids':[entry['evidence_id']],'kind':'AI Inference','method':'PHP syntax + bounded intrafile data propagation','limitations':['分支与清洗逻辑需要复核，当前不是完整跨过程污点证明。','尚未验证容器镜像与源码版本一致；此结果不证明攻击成功。']})
    dedup={}
    for m in matches:
        key=m['finding']['id']
        if key not in dedup or m['confidence']=='high': dedup[key]=m
    matches=list(dedup.values())
    return {'attack_type':kind,'entries':entries,'matched_routes':candidates,'matches':matches,'verdict':'likely_vulnerable_path' if matches else 'insufficient_evidence','confidence':matches[0]['confidence'] if matches else 'low','summary':f'发现 {len(matches)} 处与攻击入口可达且类型一致的漏洞候选，需人工确认实际利用。' if matches else '未找到足够证据将该事件关联到漏洞代码；不等于项目不存在漏洞。','method':'规则分类 + HTTP 入口精确匹配 + Python AST / PHP 语法规则 + SAST'}
