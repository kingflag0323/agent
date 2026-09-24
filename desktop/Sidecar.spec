from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules,collect_data_files,copy_metadata
root=Path(SPECPATH).parent
hidden=collect_submodules('bandit')+collect_submodules('uvicorn')+collect_submodules('app')
datas=[(str(root/'demo'),'demo'),(str(root/'docs/licenses'),'licenses')]+collect_data_files('bandit')+collect_data_files('docx')+collect_data_files('tree_sitter_php')
for name in ['bandit','stevedore']:datas+=copy_metadata(name)
a=Analysis([str(root/'desktop/sidecar.py')],pathex=[str(root/'backend')],binaries=[],datas=datas,hiddenimports=hidden,excludes=['PySide6','shiboken6','tkinter'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='sentinel-backend',console=True,icon=str(root/'desktop/sentinel.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='sentinel-backend')
