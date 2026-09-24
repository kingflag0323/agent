import copy
import io
import stat
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from app.database import store
from app.agent.knowledge import context,retrieve
from app.agent import remediation as r
from app.api.management import Asset,validate_asset

SOURCE='import sqlite3\ndef find_user(user_id):\n    c = sqlite3.connect(":memory:")\n    query = "SELECT id FROM users WHERE id = " + user_id\n    return c.execute(query).fetchall()\n'

def test_asset_crud_and_authorization(client):
    a=client.post('/api/assets',json={'name':'测试资产','host':'192.0.2.10','project_id':'demo-shop'}).json()
    assert a['id'] and not a['auto_repair']
    body={k:v for k,v in a.items() if k not in ('id','updated_at')}
    body['name']='已更新';assert client.put('/api/assets/'+a['id'],json=body).json()['name']=='已更新'
    body['auto_repair']=True;assert client.put('/api/assets/'+a['id'],json=body).status_code==400
    body['auto_repair']=False;body['allowed_files']=['../secret.py'];assert client.put('/api/assets/'+a['id'],json=body).status_code==400
    assert client.delete('/api/assets/'+a['id']).status_code==200
    assert client.put('/api/assets/'+a['id'],json={'name':'x','host':'x'}).status_code==404

def test_knowledge_import_retrieve_disable_delete(client):
    d=client.post('/api/agent/resources/knowledge',json={'name':'SQL 防御','content':'SQL 注入应使用参数化查询。禁止拼接用户输入。'}).json()
    assert len(d['sha256'])==64
    assert any(h['document_id']==d['id'] for h in retrieve('SQL 注入'))
    assert context('SQL')['knowledge']
    assert client.put('/api/agent/resources/knowledge/'+d['id'],json={'name':d['name'],'content':d['content'],'enabled':False}).status_code==200
    assert not any(h['document_id']==d['id'] for h in retrieve('SQL 注入'))
    assert client.post('/api/agent/resources/settings',json={'name':'x','content':'x'}).status_code==404
    assert client.delete('/api/agent/resources/knowledge/'+d['id']).status_code==200

def test_recipe_sql_injection_behavior(monkeypatch):
    patched=r.sqlite_patch(SOURCE,{'rule':'B608','line':4})
    assert 'c.execute(query, (user_id,))' in patched
    import sqlite3
    connection=sqlite3.connect(':memory:');connection.execute('create table users (id text)');connection.execute("insert into users values ('123')")
    # Exercise the generated expression with the actual SQLite engine, including attack input.
    monkeypatch.setattr(sqlite3,'connect',lambda *_:connection)
    namespace={};exec(compile(patched,'fixed.py','exec'),namespace)
    assert namespace['find_user']('123')==[('123',)]
    assert namespace['find_user']('123 OR 1=1')==[]
    for source in (SOURCE.replace('SELECT id FROM users WHERE id = ','SELECT * FROM '), SOURCE.replace('sqlite3.connect','other.connect'), SOURCE.replace('return c.execute','print(query)\n    return c.execute')):
        with pytest.raises(ValueError):r.sqlite_patch(source,{'rule':'B608','line':4})
    with pytest.raises(ValueError):r.sqlite_patch(SOURCE,{'rule':'B602','line':4})

class File(io.BytesIO):
    def __init__(self,fs,path,mode):
        self.fs=fs;self.path=path;self.mode=mode
        if 'x' in mode and path in fs.files:raise IOError('exists')
        super().__init__(fs.files.get(path,b'') if 'r' in mode else b'')
    def close(self):
        if 'w' in self.mode:self.fs.files[self.path]=self.getvalue()
        super().close()
class SFTP:
    def __init__(self):self.files={'/srv/app/repository.py':b'before'};self.symlink=False
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def normalize(self,p):return '/outside/file.py' if self.symlink and p.endswith('.py') else p
    def lstat(self,p):return SimpleNamespace(st_mode=stat.S_IFREG|0o644,st_uid=1000,st_gid=1000)
    stat=lstat
    def open(self,p,m):return File(self,p,m)
    def chmod(self,*args):pass
    def posix_rename(self,a,b):self.files[b]=self.files.pop(a)

def setup_deploy(client,monkeypatch):
    fs=SFTP();ssh=SimpleNamespace(open_sftp=lambda:fs)
    @contextmanager
    def connect(a):yield ssh
    monkeypatch.setattr(r,'connect',connect)
    asset={'id':'fake-asset','auto_repair':True,'remote_root':'/srv/app'};store.put('assets',asset)
    record={'id':'fake-repair','file':'repository.py'}
    return fs,asset,record

def test_ssh_deploy_backup_and_verified(client,monkeypatch):
    fs,a,record=setup_deploy(client,monkeypatch);monkeypatch.setattr(r,'verify',lambda *_:(0,'tests passed'))
    r.deploy(a,record,b'before',b'after')
    assert record['status']=='verified' and fs.files['/srv/app/repository.py']==b'after'
    assert fs.files[record['backup']]==b'before'
    store.delete('assets',a['id'])

def test_ssh_verification_failure_rolls_back(client,monkeypatch):
    fs,a,record=setup_deploy(client,monkeypatch);monkeypatch.setattr(r,'verify',lambda *_:(1,'failure'))
    r.deploy(a,record,b'before',b'after')
    assert record['status']=='rolled_back' and fs.files['/srv/app/repository.py']==b'before'
    store.delete('assets',a['id'])

def test_ssh_snapshot_and_symlink_refused(client,monkeypatch):
    fs,a,record=setup_deploy(client,monkeypatch)
    with pytest.raises(ValueError):r.deploy(a,record,b'wrong snapshot',b'after')
    assert len(fs.files)==1
    fs.symlink=True
    with pytest.raises(ValueError):r.deploy(a,record,b'before',b'after')
    store.delete('assets',a['id'])

def test_demo_never_ssh(client,monkeypatch):
    job={'id':'demo-repair','event':{'source':'demo'},'project':{'id':'demo-shop'},'status':'completed'}
    assert not r.eligible_assets(job)
    assert r.perform(job)['status']=='blocked'


def test_concurrent_remote_change_never_overwritten(client,monkeypatch):
    fs,a,record=setup_deploy(client,monkeypatch)
    def changed(*args):
        fs.files['/srv/app/repository.py']=b'operator changed file'
        return 1,'failed'
    monkeypatch.setattr(r,'verify',changed)
    r.deploy(a,record,b'before',b'after')
    assert record['status']=='recovery_required'
    assert fs.files['/srv/app/repository.py']==b'operator changed file'
    store.delete('assets',a['id'])

def test_pinned_host_key_mismatch(monkeypatch):
    import paramiko
    class Client:
        def set_missing_host_key_policy(self,policy):self.policy=policy
        def connect(self,*args,**kwargs):self.policy.missing_host_key(self,'host',SimpleNamespace(asbytes=lambda:b'wrong server key'))
        def close(self):pass
    monkeypatch.setattr(paramiko,'SSHClient',Client)
    with pytest.raises(ValueError,match='指纹不匹配'):
        with r.connect({'fingerprint':'SHA256:expected','key_path':'unused','ssh_user':'test','host':'host','ssh_port':22}):pass
