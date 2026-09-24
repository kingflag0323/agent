"""Human-readable categories from platform text, never invented numeric mappings."""
import re

TRANSLATIONS = {'sql injection':'SQL 注入', 'command injection':'命令注入', 'brute force':'暴力破解', 'suspicious dns':'可疑 DNS', 'reconnaissance':'侦察扫描', 'unknown':'未分类威胁'}

def readable(value):
    values = value if isinstance(value, list) else [value]
    return list(dict.fromkeys(str(v).strip() for v in values if isinstance(v, str) and v.strip() and not re.fullmatch(r'[\d\s,;|/-]+',v.strip()) and v.strip().lower() not in ('unknown','none','null')))

def attack_label(event):
    raw = event.get('raw') or {}
    for key in ('incidentThreatTypeName','incidentThreatTypeDesc','threatTypeDesc'):
        names = readable(raw.get(key))
        if names:return ' / '.join(names)
    names = readable(event.get('attack_type')) or readable(raw.get('incidentThreatType'))
    if names:return TRANSLATIONS.get(names[0].lower(), ' / '.join(names))
    tags = readable(raw.get('riskTag'))
    tags = [t for t in tags if t not in ('异常操作','疑似业务误报','业务误报')]
    if len(tags)==1:return tags[0]
    names = readable(raw.get('threatDefineName'))
    names = [n for n in names if n != '未知威胁']
    if names:return ' / '.join(names)
    return '多类型威胁' if tags else '未分类威胁'
