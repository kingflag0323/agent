"""Conservative SQLite repair recipe + pinned SSH, no model-generated shell execution."""
import ast
import asyncio
import base64
import difflib
import hashlib
import posixpath
import shlex
import stat
import threading
import time
import uuid
from contextlib import contextmanager
from app.database import store

_LOCK=threading.Lock()
def digest(data):return hashlib.sha256(data).hexdigest()

def eligible_assets(job):
    if job.get('event',{}).get('source')!='live':return []
    return [a for a in store.all_rows('assets') if a['auto_repair'] and a['project_id']==job['project']['id'] and a['host'] in job.get('target_ips',[job['event'].get('asset_ip')])]

def sqlite_patch(source, finding):
    """Only direct sqlite3 connection, one local concatenation, one execute; fail closed."""
    if finding['rule']!='B608':raise ValueError('此规则尚无可自动验证的修复配方，请人工修复')
    tree=ast.parse(source)
    if not any(isinstance(n,ast.Import) and any(a.name=='sqlite3' and a.asname is None for a in n.names) for n in tree.body):raise ValueError('仅支持明确导入 sqlite3 的参数化查询配方')
    for fn in (n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)):
        for stmt in fn.body:
            if not (isinstance(stmt,ast.Assign) and len(stmt.targets)==1 and isinstance(stmt.targets[0],ast.Name) and stmt.lineno<=finding['line']<=stmt.end_lineno):continue
            v=stmt.value
            if not (isinstance(v,ast.BinOp) and isinstance(v.op,ast.Add) and isinstance(v.left,ast.Constant) and isinstance(v.left.value,str) and isinstance(v.right,ast.Name)):continue
            sql=v.left.value
            # Do not parameterize identifiers, quoted values, multiple statements, or operators.
            import re
            if not re.fullmatch(r'(?is)SELECT\s+[\w\s,.*]+\s+FROM\s+\w+\s+WHERE\s+\w+\s*=\s*',sql):continue
            q=stmt.targets[0].id
            uses=[n for n in ast.walk(fn) if isinstance(n,ast.Name) and n.id==q]
            calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and len(n.args)==1 and not n.keywords and isinstance(n.args[0],ast.Name) and n.args[0].id==q and isinstance(n.func,ast.Attribute) and n.func.attr=='execute' and isinstance(n.func.value,ast.Name)]
            if len(uses)!=2 or len(calls)!=1:continue
            call=calls[0];conn=call.func.value.id
            assignments=[n for n in fn.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==conn]
            if len(assignments)!=1:continue
            cv=assignments[0].value
            if not (isinstance(cv,ast.Call) and isinstance(cv.func,ast.Attribute) and isinstance(cv.func.value,ast.Name) and cv.func.value.id=='sqlite3' and cv.func.attr=='connect' and assignments[0].lineno<stmt.lineno<call.lineno):continue
            # Prevent intervening reassignment/side effects before parameter evaluation.
            body=fn.body
            if body.index(stmt)+1>=len(body) or not (body[body.index(stmt)+1].lineno<=call.lineno<=body[body.index(stmt)+1].end_lineno):continue
            lines=source.encode().splitlines(keepends=True)
            def offsets(n):return sum(map(len,lines[:n.lineno-1]))+n.col_offset,sum(map(len,lines[:n.end_lineno-1]))+n.end_col_offset
            edits=[(*offsets(v),repr(sql+'?').encode()),(*offsets(call),(ast.get_source_segment(source,call.func)+'('+q+', ('+v.right.id+',))').encode())]
            patched=source.encode()
            for start,end,text in sorted(edits,reverse=True):patched=patched[:start]+text+patched[end:]
            result=patched.decode();ast.parse(result)
            return result
    raise ValueError('SQL 结构不满足自动修复配方，未改写文件')

@contextmanager
def connect(asset):
    import paramiko
    if not asset.get('fingerprint') or not asset.get('key_path') or not asset.get('ssh_user'):raise ValueError('请配置 SSH 用户、私钥路径与经核实的 SHA256 主机指纹')
    class Pinned(paramiko.MissingHostKeyPolicy):
        def missing_host_key(self, client, hostname, key):
            actual='SHA256:'+base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
            if actual!=asset['fingerprint']:raise ValueError('SSH 主机指纹不匹配，连接已拒绝')
    client=paramiko.SSHClient();client.set_missing_host_key_policy(Pinned())
    try:
        client.connect(asset['host'],port=asset['ssh_port'],username=asset['ssh_user'],key_filename=asset['key_path'],allow_agent=False,look_for_keys=False,timeout=10,auth_timeout=10,banner_timeout=10,channel_timeout=10)
        yield client
    except ValueError:raise
    except Exception as exc:raise ValueError('SSH 操作失败（'+type(exc).__name__+'），请检查连接、密钥、权限及远程状态') from None
    finally:client.close()

def remote_path(sftp,root,file):
    if not file or file.startswith('/') or '..' in file.split('/') or '\\' in file:raise ValueError('非法文件路径')
    root=posixpath.normpath(root)
    if root=='/' or not root.startswith('/') or sftp.normalize(root)!=root:raise ValueError('远程目录不是规范绝对路径或包含符号链接')
    path=posixpath.join(root,file)
    if sftp.normalize(path)!=path or not stat.S_ISREG(sftp.lstat(path).st_mode):raise ValueError('拒绝符号链接或非普通文件')
    return path

def read(sftp,path):
    with sftp.open(path,'rb') as f:data=f.read(512001)
    if len(data)>512000:raise ValueError('远程文件超过修复大小上限')
    return data

def verify(client,asset):
    command='cd -- '+shlex.quote(asset['remote_root'])+' && '+shlex.join(asset['verify_argv'])
    stdin,stdout,stderr=client.exec_command(command,timeout=30);stdin.close();channel=stdout.channel
    deadline=time.monotonic()+30;output=bytearray()
    try:
        while True:
            for ready,recv in ((channel.recv_ready,channel.recv),(channel.recv_stderr_ready,channel.recv_stderr)):
                if ready():
                    part=recv(4096)
                    if len(output)<16000:output.extend(part[:16000-len(output)])
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():break
            if time.monotonic()>deadline:raise ValueError('远程验证超时；远端命令可能仍需管理员检查')
            time.sleep(.03)
        code=channel.recv_exit_status()
        return code,output.decode('utf-8','replace')
    finally:channel.close()

def deploy(asset,record,before,after):
    if not _LOCK.acquire(blocking=False):raise ValueError('已有修复正在执行，请稍后再试')
    try:
        # Re-read authorization immediately before connecting.
        current=store.get('assets',asset['id'])
        if current!=asset or not current['auto_repair']:raise ValueError('资产授权已变更，请重新分析')
        with connect(asset) as client, client.open_sftp() as sftp:
            if store.get('assets',asset['id'])!=asset:raise ValueError('SSH 连接期间资产授权发生变化，停止修复')
            path=remote_path(sftp,asset['remote_root'],record['file'])
            original=read(sftp,path)
            if digest(original)!=digest(before):raise ValueError('远程文件与扫描快照不一致，拒绝覆盖')
            attributes=sftp.stat(path)
            mode=stat.S_IMODE(attributes.st_mode)
            if mode & 0o6000:raise ValueError('拒绝修改带特殊权限的文件')
            backup=path+'.double-pupil-'+record['id']+'.bak';temp=path+'.double-pupil-'+record['id']+'.tmp'
            with sftp.open(backup,'wx') as f:f.write(original)
            sftp.chmod(backup,0o600)
            if read(sftp,backup)!=original:raise ValueError('备份校验失败')
            record.update(status='backed_up',backup=backup);store.put('remediations',record)
            with sftp.open(temp,'wx') as f:f.write(after)
            sftp.chmod(temp,mode)
            temp_attributes=sftp.stat(temp)
            if (attributes.st_uid,attributes.st_gid)!=(temp_attributes.st_uid,temp_attributes.st_gid):raise ValueError('原文件所有者/组与 SSH 写入身份不一致，拒绝替换')
            if read(sftp,temp)!=after:raise ValueError('临时文件校验失败')
            remote_path(sftp,asset['remote_root'],record['file'])
            if read(sftp,path)!=before:raise ValueError('写入前检测到远程文件变化，停止修复')
            if store.get('assets',asset['id'])!=asset:raise ValueError('写入前资产授权发生变化，停止修复')
            record['status']='deploying';store.put('remediations',record)
            # Server must support atomic POSIX rename. No unsafe delete-and-rename fallback.
            try:
                sftp.posix_rename(temp,path)
                record['status']='verifying';store.put('remediations',record)
                if read(sftp,path)!=after:raise ValueError('写入后哈希校验失败')
                code,output=verify(client,asset);record['verification']={'exit_code':code,'output':output}
                if code:raise ValueError('验证命令失败')
                record['status']='verified';record['message']='已部署并通过配置的验证命令；不代表完整业务安全证明'
            except Exception:
                try:
                    if read(sftp,path)==after:
                        rollback=temp+'.rollback'
                        with sftp.open(rollback,'wx') as f:f.write(original)
                        sftp.chmod(rollback,mode);sftp.posix_rename(rollback,path)
                        if read(sftp,path)!=original:raise ValueError('回滚校验失败')
                        record['status']='rolled_back';record['message']='部署或验证失败，原始文件已恢复；验证命令的其他副作用不在文件回滚范围'
                    elif read(sftp,path)==before:record['status']='not_applied';record['message']='未应用修复，原文件保持不变'
                    else:record['status']='recovery_required';record['message']='远程文件发生并发变化，未覆盖；请根据备份人工恢复'
                except Exception:record['status']='recovery_required';record['message']='连接中断或回滚失败，请检查远程文件及备份'
    finally:_LOCK.release()

def perform(job):
    record={'id':'repair-'+uuid.uuid4().hex[:12],'investigation_id':job['id'],'created_at':store.now(),'status':'planning'}
    store.put('remediations',record)
    try:
        assets=eligible_assets(job)
        if len(assets)!=1:raise ValueError('需要唯一匹配事件 IP、代码项目且已授权自主修复的资产；演示事件不连接 SSH')
        if job['status']!='completed' or job.get('review',{}).get('status')!='passed':raise ValueError('调查与证据复核尚未完成')
        asset=assets[0];matches=[m for m in job.get('correlation',{}).get('matches',[]) if m.get('confidence')=='high' and m['finding']['file'] in asset['allowed_files']]
        if len(matches)!=1:raise ValueError('需要唯一高置信关联且漏洞文件在授权清单内')
        if any(x.get('asset_id')==asset['id'] and x['status']=='recovery_required' for x in store.all_rows('remediations')):raise ValueError('该资产存在待恢复记录，请先人工核实远程状态')
        finding=matches[0]['finding'];snapshot=store.get('scans',job['scan_id'])
        before=snapshot['sources'][finding['file']];after=sqlite_patch(before,finding)
        record.update(asset_id=asset['id'],file=finding['file'],recipe='sqlite-parameterization-v1',before_sha256=digest(before.encode()),after_sha256=digest(after.encode()),diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=finding['file'],tofile=finding['file'])))
        # Actual Bandit check in an isolated temporary project; never execute repository code locally.
        import tempfile
        from pathlib import Path
        from app.core.config import DATA
        from app.core import settings
        from app.code_analysis.scanner import scan
        (DATA/'repositories').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='repair-',dir=DATA/'repositories') as folder:
            p=Path(folder)/finding['file'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(after,encoding='utf-8',newline='')
            project={'id':'validation-'+record['id'],'path':folder,'name':'Repair validation'}
            try:check=scan(project,settings.load()['audit'])
            finally:store.delete('projects',project['id'])
            record['validation_scan_id']=check['id']
            if check['errors'] or any(f['rule']=='B608' for f in check['findings']):raise ValueError('修复后扫描未通过')
            old_rules={f['rule'] for f in snapshot['findings'] if f['file']==finding['file']}
            if any(f['rule'] not in old_rules for f in check['findings']):raise ValueError('修复引入新的扫描告警')
        record['status']='validated';store.put('remediations',record)
        deploy(asset,record,before.encode(),after.encode())
    except Exception as exc:
        record['status']='blocked' if isinstance(exc,ValueError) else 'failed'
        record['message']=str(exc) if isinstance(exc,ValueError) else '修复执行异常（'+type(exc).__name__+'）'
    record['finished_at']=store.now();store.put('remediations',record);return record

async def remediate(job):
    # Journal persists even if caller disconnects; thread owns transaction and rollback.
    return await asyncio.to_thread(perform,job)
