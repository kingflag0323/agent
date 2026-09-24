from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from app.database import store
from app.code_analysis.projects import allowed_root, source_files
from app.code_analysis.ast_index import index_sources

FIXES={
 'B608':('SQL Injection','CWE-89','将用户输入与 SQL 结构分离，使用参数化查询；同时限制返回字段及数据库权限。','query = "SELECT id, name, email FROM users WHERE id = ?"\nreturn connection.execute(query, (user_id,)).fetchall()'),
 'B602':('Command Injection','CWE-78','移除 shell=True，使用参数数组；对主机名/IP 做允许列表校验，禁止把输入拼接到 shell 命令。','import ipaddress\naddress = str(ipaddress.ip_address(host))\nreturn subprocess.check_output(["ping", "-c", "1", address], shell=False, timeout=5)'),
 'B307':('Code Injection','CWE-95','避免 eval；使用明确的数据格式解析和允许列表。',''),
 'B506':('Unsafe Deserialization','CWE-502','使用 yaml.safe_load 并限制输入大小。',''),
}

def scan(project,config):
    root=allowed_root(project['path']);files,skipped=source_files(root,int(config['max_files']),int(config['max_file_kb']))
    sources={p.relative_to(root).as_posix():p.read_text(encoding='utf-8',errors='replace') for p in files}
    index=index_sources(sources)
    hashes={file:hashlib.sha256(code.encode()).hexdigest() for file,code in sources.items()}
    snapshot=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='sxf-scan-') as tmp:
        workspace=Path(tmp)/'source';workspace.mkdir()
        for file,code in sources.items():
            if file.endswith('.py'):
                p=workspace/file;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(code,encoding='utf-8')
        # Isolated mode ignores user PYTHONPATH. Input .bandit configuration and nosec cannot suppress findings.
        env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','BANDIT','GIT'))}
        env['PYTHONUTF8']='1'
        command = [sys.executable,'--bandit-worker'] if getattr(sys,'frozen',False) else [sys.executable,'-I','-m','bandit']
        output_file=Path(tmp)/'bandit.json'
        result=subprocess.run(command+['-r',str(workspace),'-f','json','-o',str(output_file),'--ignore-nosec','-q'],cwd=tmp,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',timeout=int(config['timeout']),**({'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}))
        if result.returncode not in (0,1): raise ValueError('Bandit 扫描失败；未将失败误报为无漏洞')
        try: raw=json.loads(output_file.read_text(encoding='utf-8'))
        except (OSError,ValueError): raise ValueError('Bandit 未返回有效 JSON') from None
        findings=[]
        for r in raw.get('results',[]):
            file=Path(r['filename']).relative_to(workspace).as_posix();line=r['line_number'];rule=r['test_id']
            kind,cwe,fix,patch=FIXES.get(rule,(r['test_name'],'CWE-'+str(r.get('issue_cwe',{}).get('id','unknown')),'根据 Bandit 规则说明人工确认风险，采用安全 API。',''))
            fn=next((f for f in index['functions'] if f['file']==file and f['line']<=line<=f['end_line']),None)
            lines=sources[file].splitlines();start=max(1,line-3);end=min(len(lines),line+4)
            findings.append({'id':'finding-'+hashlib.sha256(f'{snapshot}:{file}:{line}:{rule}'.encode()).hexdigest()[:12], 'rule':rule,'type':kind,'cwe':cwe,'severity':r['issue_severity'].lower(),'confidence':r['issue_confidence'].lower(),'file':file,'line':line,'function':fn['name'] if fn else '<module>','description':r['issue_text'],'code':'\n'.join(lines[start-1:end]),'code_start':start,'fix':fix,'patch':patch,'source':'Bandit','kind':'Static Finding','file_sha256':hashes[file],'reference':r.get('more_info','')})
        errors=[{'file':str(e.get('filename','')).replace(str(workspace)+'/',''),'error':e.get('reason','scanner error')} for e in raw.get('errors',[])]
    from app.code_analysis.php_analysis import analyze as analyze_php
    php=analyze_php(sources,hashes)
    findings.extend(php['findings']);errors.extend(php['errors'])
    scan_id='scan-'+uuid.uuid4().hex[:12]
    output={'id':scan_id,'project_id':project['id'],'created_at':store.now(),'status':'partial' if index['errors'] or errors else 'completed','scanner':'Bandit + Python AST + Tree-sitter PHP','findings':findings,'index':index,'snapshot':snapshot,'sources':sources,'hashes':hashes,'file_count':len(files),'php_files':php['php_files'],'python_files':sum(f.endswith('.py') for f in sources),'skipped':skipped,'errors':index['errors']+errors,'limitations':['当前语义路由与调用图仅支持 Python 直接装饰器及可解析的函数导入；不等价于完整跨函数污点证明。','其他语言可浏览，但未运行 SAST。装饰器前缀、动态调用与多态可能无法解析。']+php['limitations']}
    store.put('scans',output);project['last_scan_id']=scan_id;project['file_count']=len(files);store.put('projects',project)
    return output
