"""Headless FastAPI sidecar for the Electron desktop; no Qt dependency."""
import os,sys,json,socket,threading,time
from pathlib import Path
if '--bandit-worker' in sys.argv:
    sys.argv=[sys.argv[0]]+sys.argv[sys.argv.index('--bandit-worker')+1:]
    from bandit.cli.main import main
    main();raise SystemExit
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
os.environ.setdefault('SXF_ROOT',str(ROOT))
data=Path(os.environ.get('SXF_DATA_DIR',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Sentinel'/'data')))
data.mkdir(parents=True,exist_ok=True);os.environ['SXF_DATA_DIR']=str(data)
repos=data/'repositories';repos.mkdir(exist_ok=True)
os.environ.setdefault('SXF_REPO_ROOTS',os.pathsep.join(map(str,[ROOT/'demo',repos,Path.home()/'Documents',Path.home()/'Desktop'])))
sys.path.insert(0,str(ROOT/'backend'))
if __name__=='__main__':
    # A byte-range lock prevents two workbench backends sharing the same database.
    lock=open(data/'workbench.lock','a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({'error':'该数据目录已有工作台在运行'}),flush=True);raise SystemExit(1)
    import uvicorn
    from app.main import app
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='warning',log_config=None))
    def parent_lifetime():
        try:sys.stdin.buffer.read()
        finally:server.should_exit=True
    threading.Thread(target=parent_lifetime,daemon=True).start()
    def ready():
        for _ in range(400):
            if server.started:
                print(json.dumps({'port':port}),flush=True);return
            time.sleep(.05)
    threading.Thread(target=ready,daemon=True).start()
    server.run(sockets=[sock])
