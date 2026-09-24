import asyncio
import copy
import traceback
from app.database import store
from app.xdr.adapter import XDRAdapter
from app.code_analysis.scanner import scan
from app.correlation.engine import correlate
from app.agent.evidence import collect, evidence
from app.llm.provider import LLMProvider

class Workflow:
    def __init__(self,job,config):
        self.job=job; self.config=config; self.steps=0
    def save(self): store.put('investigations',self.job)
    async def step(self,name,tool,note,fn):
        self.steps+=1
        if self.steps>self.config['agent']['max_steps']: raise ValueError('已达到 Max Steps，调查停止；不会生成伪完成报告')
        item={'name':name,'tool':tool,'note':note,'status':'running','started_at':store.now()}
        self.job['timeline'].append(item);self.save()
        if self.config['agent']['debug']:print(f"[Agent] {self.job['id']} step={name} tool={tool} started",flush=True)
        try:
            result=await fn()
            item['status']='completed';item['finished_at']=store.now();self.save();return result
        except Exception:
            item['status']='failed';item['finished_at']=store.now();self.save();raise
    async def execute(self):
        self.job['status']='running';self.save()
        event=self.job['event'];project=self.job['project'];cfg=self.config
        async def plan():
            is_web=any(word in (event['attack_type']+' '+event['name']).lower() for word in ('sql','注入','web','command','网站'))
            return {'include_network':is_web,'tools':['get_event_proof','get_alerts','get_alert_proof','get_host','get_ip_entities']+(['get_network_records'] if is_web else [])+['static_analysis','find_route','get_call_context','correlate','review'],'rationale':'Web 攻击读取 HTTP/网络举证；非 Web 事件优先读取事件、告警和实体。无 HTTP 入口时不强行关联代码。'}
        self.job['plan']=await self.step('Planner','plan_tools','基于事件类型选择只读工具',plan)
        bundle=await self.step('Evidence collection','xdr.collect','读取事件、关联告警、资产及选中的网络日志',lambda:XDRAdapter(cfg['xdr']).bundle(event,self.job['plan']['include_network']))
        from app.xdr.targets import destination_ips
        self.job['target_ips']=destination_ips(bundle['alerts'])
        self.job['target_assets']=[{k:a.get(k) for k in ('id','name','host','project_id','web_path','web_url')} for a in store.all_rows('assets') if a['host'] in self.job['target_ips']]
        self.job['evidence']=collect(bundle); self.job['warnings']=bundle['warnings'];self.save()
        result=await self.step('Static analysis','bandit + ast + php','生成代码快照，运行 Bandit / PHP 规则与语法分析',lambda:asyncio.to_thread(scan,project,cfg['audit']))
        self.job['scan_id']=result['id'];self.job['snapshot']=result['snapshot']
        if result['errors']:self.job['warnings'].append(f"扫描有 {len(result['errors'])} 个文件错误，结论仅覆盖成功分析的文件")
        if not result['python_files'] and not result.get('php_files'):self.job['warnings'].append('当前项目无受支持的 Python / PHP 文件；未对其他语言执行 SAST')
        for f in result['findings']:
            self.job['evidence'].append(evidence('Static Finding',f['source'],f['type']+' · '+f['file']+':'+str(f['line']),f,'scan:'+result['id']))
        async def correlate_code():
            assets=[a for a in self.job['target_assets'] if a.get('project_id')==project['id']]
            prefix=assets[0].get('web_path','/') if len(assets)==1 else '/'
            return correlate(event,self.job['evidence'],result,prefix)
        correlation=await self.step('Attack → Code','find_route / get_call_context','验证 HTTP 路由、类型匹配及跨文件静态可达性',correlate_code)
        for m in correlation['matches']:
            finding_ev=next(e for e in self.job['evidence'] if e['kind']=='Static Finding' and e['content']['id']==m['finding']['id'])
            m['evidence_ids'].append(finding_ev['id'])
            for f in m['chain']:
                code=result['sources'][f['file']];lines=code.splitlines()
                item=evidence('Static Finding','PHP syntax' if f['file'].endswith('.php') else 'Python AST',f['name'],{'file':f['file'],'line':f['line'],'code':'\n'.join(lines[f['line']-1:f['end_line']]),'sha256':result['hashes'][f['file']]},'scan:'+result['id'])
                if not any(e['id']==item['id'] for e in self.job['evidence']): self.job['evidence'].append(item)
                m['evidence_ids'].append(item['id'])
        self.job['correlation']=correlation; self.save()
        from app.agent.knowledge import context as knowledge_context
        self.job['agent_context']=knowledge_context(event['name']+' '+event['attack_type']+' '+str(correlation))
        self.save()
        async def llm():
            try:
                # Never send entire repositories: only bounded observed evidence and matching code.
                context={'event':{'name':event['name'],'attack_type':event['attack_type'],'source':event['source']},'references':self.job['agent_context'],'correlation':correlation,'evidence':[{'id':e['id'],'kind':e['kind'],'title':e['title'],'content':e['content']} for e in self.job['evidence']]}
                return await LLMProvider(cfg['llm']).analyze(context)
            except ValueError as e:
                self.job['warnings'].append('LLM 未完成：'+str(e))
                return {'provider':'unavailable','kind':'AI Inference','text':'外部模型不可用。保留可复核的静态关联结果，未生成模型结论。','verified':False}
        self.job['analysis']=await self.step('Analysis','llm_provider','生成有来源的辅助研判；模型不能覆盖静态关联结果',llm)
        if self.job['analysis'].get('truncated'):self.job['warnings'].append('模型输出达到额度上限，正文可能不完整；可在设置中提高 Max Tokens 后重新调查')
        if cfg['agent']['reviewer']:
            async def review():
                ids={e['id'] for e in self.job['evidence']}
                valid=all(all(id in ids for id in m['evidence_ids']) and m['chain'] for m in correlation['matches'])
                if not valid: raise ValueError('Reviewer 拒绝：存在缺失证据或空调用链')
                return {'status':'passed','checks':['证据引用完整','代码来自本次扫描快照','Fact / Static Finding / AI Inference 分离','未将静态可达性或 HTTP 200 宣称为利用成功'],'limitations':result['limitations']}
            self.job['review']=await self.step('Reviewer','validate_evidence','复核证据 ID、代码快照和结论边界',review)
        else: self.job['review']={'status':'skipped','checks':[],'limitations':result['limitations']}
        async def report(): return {'created_at':store.now(),'title':event['name'],'summary':correlation['summary']}
        self.job['report']=await self.step('Report','write_report','保存不可变证据快照与调查报告',report)
        from app.agent.remediation import eligible_assets, remediate
        self.job['remediation_pending']=bool(eligible_assets(self.job))
        self.job['status']='completed';self.job['completed_at']=store.now();self.save()
        if self.job['remediation_pending']:
            try:self.job['remediation']=await remediate(self.job)
            finally:
                self.job['remediation_pending']=False
                self.save()

async def run_job(id,config):
    job=store.get('investigations',id);workflow=Workflow(job,copy.deepcopy(config))
    try:
        await asyncio.wait_for(workflow.execute(),timeout=config['agent']['timeout'])
    except asyncio.CancelledError:
        if job['status']!='completed':
            job['status']='interrupted';job['error']='服务关闭中，调查未完成';workflow.save()
        raise
    except Exception as e:
        if job['status']=='completed':
            job['warnings'].append('修复等待中断，请在智能体修复记录中查看最终状态');workflow.save();return
        job['status']='failed';job['error']='调查超时' if isinstance(e,TimeoutError) else str(e) if isinstance(e,ValueError) else '调查执行失败，请查看服务日志'
        for step in job['timeline']:
            if step['status']=='running':step['status']='failed'
        workflow.save()
        if not isinstance(e,(ValueError,TimeoutError)): traceback.print_exc()
