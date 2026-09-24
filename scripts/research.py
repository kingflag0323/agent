import urllib.request,json,concurrent.futures,base64,os
from pathlib import Path
os.environ['NO_PROXY']='';os.environ['no_proxy']=''
repos=['fastapi/full-stack-fastapi-template','dfir-iris/iris-web','langchain-ai/langgraph','PyCQA/bandit','semgrep/semgrep','shadcn-ui/ui']
def get(repo):
 try:
  base='https://api.github.com/repos/'+repo
  def req(url):return json.load(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'sxf-research'}),timeout=30))
  r=req(base); contents=req(base+'/contents');issues=req(base+'/issues?state=open&per_page=3');lic=req(base+'/license');read=req(base+'/readme')
  p=Path('docs/research')/repo.replace('/','--');p.mkdir(exist_ok=True)
  (p/'LICENSE').write_bytes(base64.b64decode(lic['content']));(p/'README.upstream.md').write_bytes(base64.b64decode(read['content']))
  result={k:r.get(k) for k in ['full_name','html_url','pushed_at','archived','stargazers_count','forks_count','open_issues_count','license','language']};result['root']=[x['name'] for x in contents];result['issues']=[{'title':x['title'],'url':x['html_url']} for x in issues];(p/'metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
 except Exception as e:return {'repo':repo,'error':str(e)}
for r in concurrent.futures.ThreadPoolExecutor().map(get,repos):print(json.dumps(r,ensure_ascii=False))
