"""Native desktop launcher; frozen Windows build includes API, scanner, and fixtures."""
import os
import sys
from pathlib import Path

# Worker dispatch must precede UI/server imports. Never execute scanned source.
if '--bandit-worker' in sys.argv:
    if sys.stdout is None:sys.stdout=open(os.devnull,'w')
    if sys.stderr is None:sys.stderr=open(os.devnull,'w')
    sys.argv=[sys.argv[0]]+sys.argv[sys.argv.index('--bandit-worker')+1:]
    from bandit.cli.main import main
    main()
    raise SystemExit

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
os.environ.setdefault('SXF_ROOT',str(ROOT))
if sys.platform=='win32':
    data=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Sentinel'/'data'
    os.environ.setdefault('SXF_DATA_DIR',str(data));projects=data/'repositories';projects.mkdir(parents=True,exist_ok=True)
    allowed=[ROOT/'demo',projects,Path.home()/'Documents',Path.home()/'Desktop']
    os.environ.setdefault('SXF_REPO_ROOTS',os.pathsep.join(str(p) for p in allowed))
else:
    os.environ.setdefault('SXF_DATA_DIR',str(ROOT/'data'))
    if os.environ.get('WAYLAND_DISPLAY'):os.environ.setdefault('QT_QPA_PLATFORM','wayland')
for path in (ROOT/'backend',ROOT/'desktop'):
    if str(path) not in sys.path:sys.path.insert(0,str(path))

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--connect',help='Connect to an existing backend, e.g. http://127.0.0.1:8000');parser.add_argument('--screenshot');parser.add_argument('--self-test');parser.add_argument('--page',default='dashboard');parser.add_argument('--event',default='demo-001');args=parser.parse_args()
    # Capture failures for windowed packaged builds without a console.
    data=Path(os.environ['SXF_DATA_DIR']);data.mkdir(parents=True,exist_ok=True)
    log=None
    if getattr(sys,'frozen',False):
        log=open(data/'desktop.log','a',encoding='utf-8',buffering=1);sys.stdout=log;sys.stderr=log
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtCore import QTimer,QLockFile
    from PySide6.QtGui import QFont,QIcon,QFontDatabase
    app=QApplication(sys.argv[:1])
    if sys.platform!='win32':
        for font_path in ['/mnt/c/Windows/Fonts/msyh.ttc','/mnt/c/Windows/Fonts/msyhbd.ttc']:
            if Path(font_path).exists():QFontDatabase.addApplicationFont(font_path)
    app.setApplicationName('Sentinel');app.setOrganizationName('Sentinel');app.setFont(QFont('Microsoft YaHei UI' if sys.platform=='win32' else 'Noto Sans CJK SC',10))
    lock=QLockFile(str(data/'desktop.lock'));lock.setStaleLockTime(30000)
    if not args.connect and not lock.tryLock(100):
        QMessageBox.information(None,'Sentinel 已运行','该数据目录已有一个 Sentinel 实例，请使用已打开的窗口。');return 0
    icon=ROOT/'desktop'/'sentinel.ico'
    if icon.exists():app.setWindowIcon(QIcon(str(icon)))
    server=None;thread=None
    base=args.connect
    if not base:
        import socket,threading,time
        import uvicorn
        from app.main import app as api_app
        # Bind before launching to avoid port races. Each standalone instance gets its own loopback port.
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];base=f'http://127.0.0.1:{port}'
        server=uvicorn.Server(uvicorn.Config(api_app,host='127.0.0.1',port=port,log_level='warning',log_config=None))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        for _ in range(200):
            if server.started:break
            if not thread.is_alive():break
            time.sleep(.05)
        if not server.started:
            QMessageBox.critical(None,'Sentinel 启动失败','本机后台启动失败，请查看 data/desktop.log');return 1
    from sentinel.window import MainWindow
    window=MainWindow(base);window.show()
    if args.page in ('event','job'):window.navigate(args.page,args.event)
    elif args.page!='dashboard':window.navigate(args.page)
    if args.self_test:
        from sentinel.smoke import run
        def test():
            result=run(window,args.self_test);print(result);app.exit(0 if result['status']=='passed' else 1)
        QTimer.singleShot(500,test)
    if args.screenshot:

        def shot():window.grab().save(args.screenshot);app.quit()
        QTimer.singleShot(3500,shot)
    try:result=app.exec()
    finally:
        if server:server.should_exit=True
        if thread:thread.join(timeout=8)
        if log:log.flush()
    return result

if __name__=='__main__':raise SystemExit(main())
