from pathlib import Path
import json,shutil
root=Path(__file__).resolve().parents[1]
npm=root/'workbench/node_modules';out=root/'docs/licenses-workbench';out.mkdir(exist_ok=True)
records=[]
for manifest in npm.rglob('package.json'):
 try:p=json.loads(manifest.read_text())
 except Exception:continue
 if not p.get('name') or not p.get('version'):continue
 licenses=[f for f in manifest.parent.iterdir() if f.is_file() and f.name.lower().startswith(('license','copying','notice','copyright'))]
 name=p['name'].replace('/','__').replace('@','')
 for f in licenses:
  target=out/(name+'-'+p['version']);target.mkdir(exist_ok=True);shutil.copy2(f,target/f.name)
 records.append({'name':p['name'],'version':p['version'],'license':p.get('license'),'license_files':[f.name for f in licenses]})
(out/'packages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('Collected npm license records:',len(records))
