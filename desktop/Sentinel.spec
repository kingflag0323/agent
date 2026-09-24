# Build on Windows using scripts/build-windows.ps1. Keep Qt DLLs replaceable (onedir).
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata
root=Path(SPECPATH).parent
hidden=collect_submodules('bandit')+collect_submodules('uvicorn')+collect_submodules('app')+collect_submodules('sentinel')
datas=[(str(root/'demo'),'demo'),(str(root/'desktop'/'sentinel.ico'),'desktop'),(str(root/'docs'/'licenses'),'licenses')]
for package in ['bandit','stevedore','pbr','PySide6','shiboken6']:
    try:datas+=copy_metadata(package)
    except Exception:pass
datas+=collect_data_files('bandit')
a=Analysis([str(root/'desktop'/'main.py')],pathex=[str(root/'desktop'),str(root/'backend')],binaries=[],datas=datas,hiddenimports=hidden,hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick','tkinter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='Sentinel',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon=str(root/'desktop'/'sentinel.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='Sentinel')
