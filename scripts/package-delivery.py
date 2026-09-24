"""Package the already built and tested Double Pupil desktop, excluding local data."""
from pathlib import Path
import hashlib,json,shutil,zipfile,subprocess
root=Path(__file__).resolve().parents[1]
stage=Path('/mnt/c/Users/ICS/AppData/Local/SentinelBuild/workbench-release/DoublePupil')
release=root/'release';target=release/'DoublePupil'
if target.exists(): shutil.rmtree(target)
shutil.copytree(stage,target)
shutil.copy2('/mnt/c/Users/ICS/AppData/Local/SentinelBuild/double-pupil-v04-live-check.json',root/'docs/double-pupil-live-check.json')
shutil.copy2(root/'docs/使用说明.md',target/'使用说明.md')
shutil.copy2(root/'docs/使用说明.md',target/'使用说明.txt')
(target/'docs').mkdir(exist_ok=True)
for name in ['DOUBLE_PUPIL_V04.md','DOUBLE_PUPIL.md','ACCEPTANCE.md']:
 shutil.copy2(root/'docs'/name,target/'docs'/name)
archive=release/'Double-Pupil-Windows-x64.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(target.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(release))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
manifest={'product':'Double Pupil','version':'0.4.0','platform':'Windows x64','canvas':'retained','backend_tests':45,'desktop_acceptance_groups':16,'live_xdr':json.loads((root/'docs/double-pupil-live-check.json').read_text()),'real_ssh_remediation_executed':False,'automatic_recipe':'sqlite-parameterization-v1','portable_archive':{'name':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive)},'executable_sha256':sha(target/'DoublePupil.exe'),'data_directory':'%LOCALAPPDATA%/Sentinel/data (compatibility)'}
manifest['overview_acceptance']=json.loads((root/'docs/screenshots-overview/result.json').read_text())
manifest['desktop_acceptance']=json.loads((root/'docs/screenshots-double-pupil-v04/result.json').read_text())
(root/'docs/workbench-delivery.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
source=release/'Double-Pupil-source.zip'
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in filter(None,tracked):
  f=root/name
  if f.is_file():z.write(f,Path('Double-Pupil-source')/name)
manifest['source_archive']={'name':source.name,'bytes':source.stat().st_size,'sha256':sha(source)}
(release/'Double-Pupil-delivery.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'portable_mb':round(archive.stat().st_size/1024**2,1),'source_mb':round(source.stat().st_size/1024**2,1),'status':'ready'}))
