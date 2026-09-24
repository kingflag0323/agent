from pathlib import Path
from importlib.metadata import distributions
import shutil,json,sys
out=Path(sys.argv[1] if len(sys.argv)>1 else 'docs/licenses');out.mkdir(parents=True,exist_ok=True);result=[]
for d in distributions():
 name=d.metadata['Name'];version=d.version;lic=d.metadata.get('License-Expression') or d.metadata.get('License','');copied=[]
 for f in d.files or []:
  if any(x in str(f).lower() for x in ['licenses/','license.txt','license.md','/license','copying','notice']):
   source=Path(d.locate_file(f))
   if source.is_file():
    dest=out/name/str(f).replace('../','').replace('\\','/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);copied.append(str(dest.relative_to(out)))
 result.append({'name':name,'version':version,'license':lic[:3000],'notices':copied})
(out.parent/'dependencies.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
