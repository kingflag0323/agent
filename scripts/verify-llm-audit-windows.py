"""Run one real configured LLM audit through the installed Windows desktop."""
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

expect.set_options(timeout=180000)

root=Path(os.environ['LOCALAPPDATA'])/'SentinelBuild'
project_name=sys.argv[1] if len(sys.argv)>1 else os.environ.get('AUDIT_PROJECT_NAME','Shop API · 演示项目')
exe=Path(os.environ['LOCALAPPDATA'])/'Programs/DoublePupil/DoublePupil.exe'
output=root/'llm-audit-live';output.mkdir(exist_ok=True)
proc=subprocess.Popen([str(exe),'--remote-debugging-port=9236'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(150):
        try:urllib.request.urlopen('http://127.0.0.1:9236/json/version',timeout=1);break
        except Exception:time.sleep(.2)
    with sync_playwright() as p:
        browser=p.chromium.connect_over_cdp('http://127.0.0.1:9236')
        context=browser.contexts[0]
        page=context.pages[0] if context.pages else context.wait_for_event('page',timeout=30000)
        page.set_default_timeout(180000)
        page.get_by_role('button',name='代码审计',exact=True).click()
        project=page.evaluate("async(name)=>{const rows=await window.desktop.request('/projects');return rows.find(p=>p.name===name)||rows.find(p=>p.name.toLowerCase().includes(name.toLowerCase()))}",project_name)
        assert project,project_name
        page.get_by_label('代码项目').select_option(project['id'])
        page.get_by_role('button',name='运行扫描',exact=True).click()
        expect(page.get_by_role('button',name='运行扫描',exact=True)).to_be_enabled()
        result=page.evaluate("id=>window.desktop.request('/projects/'+id+'/scan')",project['id'])
        assert result['ai_audit']['status'] in ('completed','partial'),result['ai_audit']
        assert result['ai_audit']['model'] and result['ai_audit']['model']!='mock'
        assert result['ai_audit']['chunks_analyzed']>0
        expect(page.get_by_text('AI 审计 · '+result['ai_audit']['status'],exact=False)).to_be_visible()
        page.screenshot(path=str(output/'code-audit-llm.png'))
        summary={'project':project['name'],**{key:result.get(key) for key in ('id','snapshot','status','scanner','static_findings_count','ai_findings_count','ai_confirmed_count','ai_audit')}}
        (output/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False))
        browser.close()
finally:
    proc.terminate()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill()
