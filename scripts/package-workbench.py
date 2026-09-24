"""Assemble an unpacked Windows Electron app from verified Electron + sidecar builds."""
from pathlib import Path
import shutil,zipfile,json
root=Path(__file__).resolve().parents[1]
windows=Path('/mnt/c/Users/ICS/AppData/Local/SentinelBuild')
archive=Path('/tmp/sxf-electron-download.log').read_text().strip().splitlines()[-1]
output=windows/'workbench-release/DoublePupil'
output.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as z:z.extractall(output)
shutil.move(output/'electron.exe',output/'DoublePupil.exe')
app=output/'resources/app';app.mkdir(parents=True,exist_ok=True)
for folder in ['electron','dist']:
 if (app/folder).exists():shutil.rmtree(app/folder)
 shutil.copytree(root/'workbench'/folder,app/folder)
(app/'package.json').write_text(json.dumps({'name':'double-pupil','version':'0.4.0','main':'electron/main.cjs','license':'GPL-3.0-only'}))
shutil.copytree(windows/'sidecar-release/sentinel-backend',output/'resources/backend',dirs_exist_ok=True)
shutil.copy2(root/'workbench/LICENSE',output/'LICENSE-DOUBLE-PUPIL-GPL3.txt')
shutil.copy2(root/'THIRD_PARTY_NOTICES.md',output/'THIRD_PARTY_NOTICES.md')
shutil.copy2(root/'workbench/UPSTREAM.md',output/'UPSTREAM.md')
print(output)
