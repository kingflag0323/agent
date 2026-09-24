"""Reproducibly extract the supplied Eolink HTML without executing its JavaScript."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
inputs=list(root.glob('*.html'))
if not inputs:raise SystemExit('No XDR HTML documents found')
for p in inputs:print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
s=inputs[0].read_text(encoding='utf-8-sig')
data,_=json.JSONDecoder().raw_decode(s.split('var projectJSON = ',1)[1])
(root/'docs/xdr-api.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
endpoints=[]
for group in data['apiGroupList']:
 for api in group.get('apiList',[]):
  b=api['baseInfo'];endpoints.append({'group':group['groupName'],'name':b['apiName'],'uri':b.get('apiURI'),'type':b.get('apiRequestType'),'note':b.get('apiNoteRaw'),'request':api.get('requestInfo'),'headers':api.get('headerInfo'),'response':api.get('resultInfo'),'example':b.get('apiSuccessMock')})
(root/'docs/xdr-endpoints.json').write_text(json.dumps(endpoints,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(endpoints)} endpoint definitions extracted')
