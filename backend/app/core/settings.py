from copy import deepcopy
import re
from urllib.parse import urlsplit
from app.core.config import DEFAULTS
from app.database import store

def load():
    s = deepcopy(DEFAULTS)
    for row in store.all_rows('settings'):
        if row['id'] in s:
            s[row['id']].update(row['value'])
    return s

def public():
    s = load()
    for group,key in [('llm','api_key'),('ti','api_key'),('xdr','token'),('xdr','access_key'),('xdr','secret_key'),('xdr','auth_code')]:
        s[group][key + '_configured'] = bool(s[group].pop(key))
    return s

def save(body):
    s = load()
    for group, value in body.items():
        if group not in DEFAULTS or not isinstance(value, dict): raise ValueError('无效设置分组')
        for key, val in value.items():
            if key not in DEFAULTS[group]: raise ValueError('无效设置字段: ' + key)
            default = DEFAULTS[group][key]
            if isinstance(default,bool) and not isinstance(val,bool): raise ValueError('需要布尔值: ' + key)
            if isinstance(default,(float,int)) and not isinstance(default,bool) and (not isinstance(val,(float,int)) or isinstance(val,bool)): raise ValueError('需要数值: ' + key)
            if isinstance(default,str) and not isinstance(val,str): raise ValueError('需要字符串: ' + key)
            if key in ('api_key','token','access_key','secret_key','auth_code') and val == '': continue
            s[group][key] = val
    if s['xdr']['mode'] not in ('demo','live') or s['llm']['mode'] not in ('mock','compatible'): raise ValueError('无效模式')
    if s['llm']['thinking_mode'] not in ('auto','disabled','enabled'):raise ValueError('推理模式无效')
    if s['xdr']['auth_type'] not in ('token','aksk','auth_code'): raise ValueError('无效 XDR 认证方式')
    for group in ('xdr','llm'):
        u = s[group]['base_url']
        if u and (urlsplit(u).scheme not in ('https','http') or not urlsplit(u).hostname or urlsplit(u).username or urlsplit(u).query or urlsplit(u).fragment): raise ValueError('Base URL 必须是无凭据的 HTTP(S) 地址')
        if not 1 <= s[group]['timeout'] <= 120: raise ValueError('Timeout 范围 1–120 秒')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,63}',s['xdr']['auth_header']): raise ValueError('无效认证头')
    if s['xdr']['auth_header'].lower() in ('host','content-length','connection','transfer-encoding'): raise ValueError('禁止覆盖该请求头')
    for text in [s['xdr']['access_key'], s['xdr']['secret_key'], s['xdr']['auth_code'], s['xdr']['token'], s['xdr']['auth_scheme'], s['llm']['api_key'],s['ti']['api_key']]:
        if '\r' in text or '\n' in text: raise ValueError('认证字段不能包含换行')
    if not 0 <= s['llm']['temperature'] <= 2 or not 100 <= s['llm']['max_tokens'] <= 8000: raise ValueError('LLM 参数超出范围')
    if not 5 <= s['agent']['max_steps'] <= 50 or not 10 <= s['agent']['timeout'] <= 600: raise ValueError('Agent 参数超出范围')
    if not 1 <= s['audit']['max_files'] <= 2000 or not 1 <= s['audit']['max_file_kb'] <= 1024 or not 5 <= s['audit']['timeout'] <= 120: raise ValueError('扫描参数超出范围')
    if s['ti']['provider'] not in ('cisa','nvd'):raise ValueError('情报源仅支持 CISA / NVD')
    if not 1<=s['ti']['interval_hours']<=168 or not 1<=s['ti']['lookback_days']<=30:raise ValueError('情报同步间隔 1–168 小时，回溯 1–30 天')
    from pathlib import Path
    for path in s['workspace'].values():
        if not path or not Path(path).is_absolute() or '\x00' in path:raise ValueError('工作目录与报告目录须为本机绝对路径')
        if Path(path).exists() and not Path(path).is_dir():raise ValueError('所选路径不是目录')
    for group,val in s.items(): store.put('settings',{'id':group,'value':val})
    return public()
