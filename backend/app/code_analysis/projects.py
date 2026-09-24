"""Bounded source ingestion. Never execute repository code, hooks or dependencies."""
from pathlib import Path, PurePosixPath, PureWindowsPath
import os
import shutil
import stat
import subprocess
import tempfile
import uuid
import zipfile
import io
import httpx
from urllib.parse import urlsplit, quote
from app.core.config import ALLOWED_ROOTS, REPOS
from app.database import store

EXTENSIONS={'.py','.java','.js','.jsx','.ts','.tsx','.go','.rb','.php','.rs','.json','.yaml','.yml','.md','.txt','.sql'}
IGNORE={'.git','.venv','venv','node_modules','dist','build','__pycache__','.idea','.next'}
MAX_BYTES=25*1024*1024

def repository_root():
    from app.core.settings import load
    root=Path(load()['workspace']['working_directory']).expanduser().resolve();root.mkdir(parents=True,exist_ok=True);return root

def allowed_roots():
    from app.core.settings import load
    return ALLOWED_ROOTS+[Path(load()['workspace']['working_directory']).expanduser().resolve()]+[Path(p['path']).resolve() for p in store.all_rows('projects') if p.get('path')]

def allowed_root(path):
    p=Path(path).expanduser().resolve()
    if not any(p.is_relative_to(root) for root in allowed_roots()): raise ValueError('本地路径不在允许的代码目录中。通过 SXF_REPO_ROOTS 添加代码目录后重启。')
    if not p.is_dir(): raise ValueError('代码目录不存在')
    return p

def source_files(root, max_files=1000, max_file_kb=512):
    root=Path(root).resolve(); files=[];total=0;skipped=0
    for parent,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in IGNORE and not d.startswith('.') and not (Path(parent)/d).is_symlink())
        for name in sorted(names):
            p=Path(parent)/name
            if p.is_symlink() or name.startswith('.') or p.suffix.lower() not in EXTENSIONS: skipped+=1;continue
            resolved=p.resolve()
            if not resolved.is_relative_to(root) or not p.is_file(): raise ValueError('非法代码文件路径')
            size=p.stat().st_size
            if size>max_file_kb*1024: skipped+=1;continue
            total+=size
            if len(files)>=max_files or total>MAX_BYTES: raise ValueError('代码超过扫描限制；请缩小代码项目范围')
            files.append(p)
    return files,skipped

def create(name,path,source='local'):
    root=allowed_root(path);files,skipped=source_files(root)
    if not files: raise ValueError('没有可读取的源代码文件')
    return store.put('projects',{'id':'proj-'+uuid.uuid4().hex[:12],'name':name,'path':str(root),'source':source,'created_at':store.now(),'file_count':len(files),'skipped':skipped,'last_scan_id':None})

def import_zip(name,upload):
    dest=repository_root()/('zip-'+uuid.uuid4().hex[:12]);dest.mkdir()
    try:
        with zipfile.ZipFile(upload) as z:
            entries=z.infolist()
            if len(entries)>2000 or sum(i.file_size for i in entries)>MAX_BYTES: raise ValueError('ZIP 超过 2000 文件或解压 25 MB 上限')
            for entry in entries:
                p=PurePosixPath(entry.filename)
                mode=entry.external_attr >> 16
                if p.is_absolute() or PureWindowsPath(entry.filename).drive or ':' in entry.filename or '..' in p.parts or '\\' in entry.filename or stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode): raise ValueError('ZIP 含路径穿越、符号链接或特殊文件')
                if entry.flag_bits & 1: raise ValueError('不支持加密 ZIP')
                if entry.is_dir(): continue
                if any(part in IGNORE or part.startswith('.') for part in p.parts): continue
                if p.suffix.lower() not in EXTENSIONS: continue
                if entry.file_size>512*1024: raise ValueError('ZIP 中单个文件超过 512 KB')
                target=dest/str(p);target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(entry) as src,target.open('wb') as out: shutil.copyfileobj(src,out)
        return create(name,dest,'zip')
    except Exception:
        shutil.rmtree(dest);raise

def import_git(name,url,branch):
    parsed=urlsplit(url)
    hosts=os.environ.get('SXF_GIT_HOSTS','github.com,gitlab.com').split(',')
    if parsed.scheme!='https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.query or parsed.fragment: raise ValueError('只支持允许域名的公开 HTTPS Git URL（默认 github.com / gitlab.com）')
    if branch and (branch.startswith('-') or len(branch)>150 or any(x in branch for x in ['..','~','^',':','\\',' ','\n'])): raise ValueError('无效 Git branch')
    if not shutil.which('git'):
        return import_github_archive(name,url,branch)
    dest=repository_root()/('git-'+uuid.uuid4().hex[:12])
    # No shell, hooks, submodules, LFS smudge or inherited Git config/credentials.
    with tempfile.TemporaryDirectory() as empty_home:
        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':empty_home,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0','GIT_LFS_SKIP_SMUDGE':'1','GIT_ALLOW_PROTOCOL':'https'}
        args=['git','-c','core.hooksPath=/dev/null','-c','http.followRedirects=false','-c','credential.helper=','clone','--depth','1','--single-branch','--no-tags']
        if branch: args+=['--branch',branch]
        try:
            r=subprocess.run(args+['--',url,str(dest)],env=env,capture_output=True,timeout=90,**({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
            if r.returncode: raise ValueError('Git clone 失败：检查公开仓库地址、分支与网络')
            return create(name,dest,'git')
        except Exception:
            if dest.exists(): shutil.rmtree(dest)
            raise

def read_file(project,relative):
    root=allowed_root(project['path']); p=root/relative
    if p.is_symlink() or not p.resolve().is_relative_to(root) or p.suffix.lower() not in EXTENSIONS or any(part.startswith('.') or part in IGNORE for part in Path(relative).parts): raise ValueError('拒绝访问代码目录以外或隐藏文件')
    if not p.is_file() or p.stat().st_size>1024*1024: raise ValueError('文件不存在或超过读取限制')
    return p.read_text(encoding='utf-8',errors='replace')


def import_github_archive(name,url,branch):
    """Public GitHub snapshot fallback for Windows without Git; bounded HTTPS download."""
    parsed=urlsplit(url)
    parts=parsed.path.strip('/').removesuffix('.git').split('/')
    if parsed.hostname!='github.com' or len(parts)!=2 or any(not p or p.startswith('.') for p in parts):
        raise ValueError('未找到系统 Git。无 Git 模式仅支持公开 GitHub owner/repository URL；其他来源请用 ZIP。')
    owner,repo=parts
    endpoint='https://api.github.com/repos/'+quote(owner,safe='')+'/'+quote(repo,safe='')
    try:
        # Respect explicit user proxy settings for public GitHub, with no repository-controlled redirects.
        with httpx.Client(timeout=30,follow_redirects=False,headers={'Accept':'application/vnd.github+json','User-Agent':'Sentinel-SOC/0.1'}) as c:
            r=c.get(endpoint+'/commits/'+quote(branch or 'HEAD',safe=''))
            if r.status_code!=200: raise ValueError('无法解析公开 GitHub 仓库/分支；可能不存在、网络不可用或 API 速率受限')
            commit=r.json().get('sha','')
            if len(commit)!=40 or any(ch not in '0123456789abcdef' for ch in commit):raise ValueError('GitHub 未返回有效 commit SHA')
            r=c.get(endpoint+'/zipball/'+commit)
            location=r.headers.get('location','');target=urlsplit(location)
            if r.status_code!=302 or target.scheme!='https' or target.hostname!='codeload.github.com' or target.username or target.port not in (None,443):raise ValueError('GitHub 未返回允许的源码下载地址')
            content=bytearray()
            with c.stream('GET',location) as response:
                if response.status_code!=200:raise ValueError('GitHub 源码下载失败')
                for block in response.iter_bytes(65536):
                    content.extend(block)
                    if len(content)>MAX_BYTES:raise ValueError('GitHub 源码压缩包超过 25 MB')
        project=import_zip(name,io.BytesIO(content))
        root=Path(project['path']);children=list(root.iterdir())
        if len(children)==1 and children[0].is_dir():project['path']=str(children[0])
        project.update({'source':'git','git_url':url,'branch':branch or 'HEAD','commit':commit,'import_method':'github-archive'})
        return store.put('projects',project)
    except httpx.HTTPError:raise ValueError('公开 GitHub 连接失败，请检查网络或使用 ZIP 导入') from None
