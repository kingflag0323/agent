import json
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QTabWidget,QTreeWidget,QTreeWidgetItem,QSplitter,QPlainTextEdit,QComboBox,QFileDialog,QProgressBar,QHeaderView
from .widgets import Page,Panel,Table,CodeViewer,ChainWidget,label,button,badge,row,page_header,clear,date

class EvidencePanel(QWidget):
    def __init__(self):
        super().__init__();box=QVBoxLayout(self);box.setContentsMargins(0,10,0,0);self.items=[]
        self.split=QSplitter(Qt.Horizontal);self.tree=QTreeWidget();self.tree.setHeaderLabels(['证据 / 类型','来源']);self.tree.setMinimumWidth(300);self.tree.setColumnWidth(0,275)
        right=QWidget();r=QVBoxLayout(right);r.setContentsMargins(10,0,0,0);self.title=label('选择证据查看原始字段','sectionTitle');self.source=label('','mono',True);self.raw=QPlainTextEdit();self.raw.setReadOnly(True);self.hash=label('','mono',True);r.addWidget(self.title);r.addWidget(self.source);r.addWidget(self.raw,1);r.addWidget(self.hash);self.split.addWidget(self.tree);self.split.addWidget(right);self.split.setStretchFactor(1,2);box.addWidget(self.split);self.tree.currentItemChanged.connect(self.selected);self.setMinimumHeight(440)
    def set_items(self,items):
        selected=self.tree.currentItem().data(0,Qt.UserRole) if self.tree.currentItem() else None
        self.items=items;self.tree.clear();groups={}
        for e in items:
            if e['kind'] not in groups:
                group=QTreeWidgetItem([e['kind'],'']);self.tree.addTopLevelItem(group);groups[e['kind']]=group
            item=QTreeWidgetItem([e['title'],e['source']]);item.setData(0,Qt.UserRole,e['id']);item.setToolTip(0,e['id']);groups[e['kind']].addChild(item)
            if e['id']==selected:self.tree.setCurrentItem(item)
        self.tree.expandAll()
        if not self.tree.currentItem() and groups:self.tree.setCurrentItem(next(iter(groups.values())).child(0))
    def selected(self,item,previous=None):
        if not item:return
        e=next((e for e in self.items if e['id']==item.data(0,Qt.UserRole)),None)
        if not e:return
        self.title.setText(e['title']);self.source.setText(f"{e['kind']}  ·  {e['id']}\n{e['provenance']}");self.raw.setPlainText(json.dumps(e['content'],ensure_ascii=False,indent=2));self.hash.setText('SHA-256  '+e['sha256']+'\n采集时间 '+date(e['collected_at']))

class InvestigationView(QWidget):
    def __init__(self,client,navigate):
        super().__init__();self.client=client;self.navigate=navigate;self.job=None;self.signature=None;self.match_index=0
        self.box=QVBoxLayout(self);self.box.setContentsMargins(0,0,0,0);self.box.setSpacing(17)
        self.head=QWidget();self.head_layout=QHBoxLayout(self.head);self.head_layout.setContentsMargins(0,0,0,0);self.box.addWidget(self.head)
        self.steps=QWidget();self.steps_layout=QHBoxLayout(self.steps);self.steps_layout.setContentsMargins(0,0,0,0);self.steps_layout.setSpacing(8);self.box.addWidget(self.steps)
        self.progress=QProgressBar();self.progress.setRange(0,0);self.box.addWidget(self.progress)
        self.tabs=QTabWidget();self.correlation=QWidget();self.correlation_box=QVBoxLayout(self.correlation);self.correlation_box.setContentsMargins(0,18,0,0);self.correlation_box.setSpacing(18);self.correlation_box.setAlignment(Qt.AlignTop)
        self.evidence=EvidencePanel();self.analysis=QWidget();self.analysis_box=QVBoxLayout(self.analysis);self.analysis_box.setContentsMargins(0,18,0,0);self.analysis_box.setAlignment(Qt.AlignTop)
        self.timeline=Table(['步骤 / 工具','结果摘要','状态','开始时间'])
        self.tabs.addTab(self.correlation,'Attack → Code');self.tabs.addTab(self.evidence,'证据库');self.tabs.addTab(self.analysis,'研判与复核');self.tabs.addTab(self.timeline,'执行记录');self.box.addWidget(self.tabs)
    def set_job(self,job):
        signature=(job['id'],job['status'],tuple((s['name'],s['status']) for s in job['timeline']),len(job['evidence']))
        self.job=job
        if signature==self.signature:return
        self.signature=signature;clear(self.head_layout);clear(self.steps_layout)
        self.head_layout.addWidget(label('✧  AI Investigation','sectionTitle'));self.head_layout.addWidget(label(job['id']+' · '+date(job['created_at']),'mono'));self.head_layout.addStretch();self.head_layout.addWidget(badge(job['status']))
        if job['status']=='completed':self.head_layout.addWidget(button('↓  导出报告',self.export))
        for i,s in enumerate(job['timeline']):
            p=Panel();p.box.setContentsMargins(10,9,10,9);p.box.setSpacing(5);p.add(label(('✓  ' if s['status']=='completed' else '◌  ')+s['name']));p.add(label(s['status'],'muted'));self.steps_layout.addWidget(p,1)
        self.progress.setVisible(job['status'] in ('running','queued'))
        self.render_correlation();self.evidence.set_items(job['evidence']);self.tabs.setTabText(1,f"证据库 · {len(job['evidence'])}");clear(self.analysis_box)
        p=Panel('辅助研判',action=badge('AI Inference','inference'));a=job.get('analysis',{});p.add(label('Provider: '+a.get('provider','等待执行')+'  '+a.get('model',''),'mono'));text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(a.get('text','尚未生成。'));text.setMinimumHeight(190);p.add(text);self.analysis_box.addWidget(p)
        review=job.get('review',{});p=Panel('Reviewer · 证据复核',action=badge(review.get('status','等待执行')))
        for x in review.get('checks',[]):p.add(label('✓  '+x))
        for x in review.get('limitations',[]):p.add(label(x,'muted',True))
        for x in job.get('warnings',[]):p.add(label('⚠  '+x,'muted',True))
        p.add(label('代码快照 SHA-256: '+job.get('snapshot','等待扫描'),'mono',True));self.analysis_box.addWidget(p)
        self.timeline.populate([[s['name']+'\n'+s['tool'],s['note'],s['status'],date(s['started_at'])] for s in job['timeline']])
        self.timeline.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        for i,s in enumerate(job['timeline']):self.timeline.severity(i,2,s['status'])
    def render_correlation(self):
        clear(self.correlation_box);job=self.job;c=job.get('correlation')
        if job.get('error'):self.correlation_box.addWidget(label('调查未完成：'+job['error'],'muted',True))
        if not c:self.correlation_box.addWidget(label('正在收集证据并扫描代码。结果将自动更新…','muted'));return
        matches=c['matches'];m=matches[min(self.match_index,len(matches)-1)] if matches else None
        p=Panel('定位到可能被利用的代码路径' if m else '证据不足，未建立漏洞关联',action=badge('AI Inference','inference'));p.add(label(c['summary'],'muted',True));self.correlation_box.addWidget(p)
        if not m:
            p=Panel('调查边界');p.add(label(f"已提取 {len(c['entries'])} 个 HTTP 入口，匹配 {len(c['matched_routes'])} 个代码路由。",'muted'));p.add(label('攻击名称或代码仓库中存在漏洞，不足以证明这次请求可到达漏洞。请补充完整请求或正确的部署版本映射。','muted',True));self.correlation_box.addWidget(p);return
        top=row(badge(m['confidence'].upper()+' CONFIDENCE','high-confidence'),label('关联置信度 · 启发式等级，非统计概率','muted'),badge(m['finding']['cwe'],'static'))
        if len(matches)>1:
            combo=QComboBox()
            for candidate in matches:combo.addItem(f"{candidate['finding']['file']}:{candidate['finding']['line']}")
            combo.setCurrentIndex(self.match_index);combo.currentIndexChanged.connect(self.select_match);top.layout().addWidget(combo)
        self.correlation_box.addWidget(top)
        nodes=[{'role':'ATTACK ENTRY','name':f"{m['entry']['method'] or '?'} {m['entry']['path']}",'location':'HTTP request'}]
        for i,f in enumerate(m['chain']):nodes.append({'role':'ROUTER / SOURCE' if i==0 else 'VULNERABLE SINK' if i==len(m['chain'])-1 else 'SERVICE','name':f['name']+'()','location':f"{f['file']}:{f['line']}"})
        self.correlation_box.addWidget(ChainWidget(nodes))
        split=QHBoxLayout();left=Panel('漏洞代码',m['finding']['file']+':'+str(m['finding']['line']),badge('Static Finding','static'));viewer=CodeViewer();viewer.setMinimumHeight(235);viewer.show_code(m['finding']['code'],m['finding']['code_start'],m['finding']['line']);left.add(viewer);left.add(label(m['finding']['rule']+' · '+m['finding']['description'],'muted',True));split.addWidget(left,3)
        right=Panel('为什么关联到这里')
        for i,reason in enumerate(m['reasons']):right.add(label(f'{i+1:02}   {reason}',wrap=True))
        refs=button('查看引用的 '+str(len(m['evidence_ids']))+' 条证据  ↗',lambda:self.tabs.setCurrentIndex(1));right.add(refs);right.add(label('\n'.join(m['evidence_ids']),'mono'));split.addWidget(right,2);self.correlation_box.addLayout(split)
        fix=Panel('修复建议','建议代码 · 未自动修改代码仓库');fix.add(label(m['finding']['fix'],wrap=True))
        if m['finding']['patch']:
            code=CodeViewer();code.show_code(m['finding']['patch']);code.setFixedHeight(155);fix.add(code)
        for limitation in m['limitations']:fix.add(label('· '+limitation,'muted',True))
        self.correlation_box.addWidget(fix)
    def select_match(self,i):self.match_index=i;self.render_correlation()
    def export(self):
        filename,_=QFileDialog.getSaveFileName(self,'导出调查报告',self.job['id']+'.md','Markdown (*.md);;JSON (*.json)')
        if not filename:return
        if filename.endswith('.json'):
            try:Path(filename).write_text(json.dumps(self.job,ensure_ascii=False,indent=2),encoding='utf-8');self.window().statusBar().showMessage('报告已保存：'+filename,10000)
            except OSError:self.client.failure.emit('无法写入报告文件')
        else:
            def save(data):
                try:Path(filename).write_bytes(data);self.window().statusBar().showMessage('报告已保存：'+filename,10000)
                except OSError:self.client.failure.emit('无法写入报告文件')
            self.client.download('/investigations/'+self.job['id']+'/report',save)

class EventPage(Page):
    def __init__(self,client,navigate):
        super().__init__();self.client=client;self.navigate=navigate;self.id=None;self.event_data=None;self.job_id=None;self.pending=False
        self.title=page_header('SECURITY EVENT','事件详情','从 XDR 举证到漏洞代码。',button('← 返回事件列表',lambda:navigate('events')));self.layout.addWidget(self.title)
        self.meta=Panel();self.layout.addWidget(self.meta)
        self.project=QComboBox();self.project.setMinimumWidth(320);self.start=button('✧  AI Investigation',self.investigate,True);self.start.setObjectName('primary');self.start.setAccessibleName('AI Investigation');self.project.setAccessibleName('调查代码项目')
        self.layout.addWidget(row(label('部署对应项目','muted'),self.project,self.start));self.tabs=QTabWidget();self.overview=QWidget();self.overview_box=QVBoxLayout(self.overview);self.overview_box.setContentsMargins(0,15,0,0);self.evidence=EvidencePanel();self.overview_box.addWidget(self.evidence)
        self.job_container=QWidget();self.job_box=QVBoxLayout(self.job_container);self.job_box.setContentsMargins(0,15,0,0);self.job_picker=QComboBox();self.job_picker.currentIndexChanged.connect(self.pick_job);self.job_box.addWidget(self.job_picker);self.view=InvestigationView(client,navigate);self.job_box.addWidget(self.view)
        self.tabs.addTab(self.overview,'事件与 XDR Evidence');self.tabs.addTab(self.job_container,'AI 调查 / 代码关联');self.layout.addWidget(self.tabs)
        self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.poll)
    def load(self,id):
        self.id=id;self.event_data=None;self.job_id=None;self.view.hide();self.tabs.setCurrentIndex(0);self.evidence.set_items([]);self.job_picker.blockSignals(True);self.job_picker.clear();self.job_picker.blockSignals(False);self.refresh();self.timer.start()
    def refresh(self):
        if not self.id:return
        current=self.id
        self.client.request('/events/'+self.id,lambda e:self.render_event(e) if self.id==current else None)
        self.client.request('/events/'+self.id+'/evidence',lambda d:self.evidence.set_items(d['evidence']) if self.id==current else None)
        self.client.request('/projects',self.render_projects)
    def render_projects(self,rows):
        selected=self.project.currentData() or (self.event_data or {}).get('project_id');self.project.clear();self.project.addItem('请选择部署对应的代码项目',None)
        for p in rows:self.project.addItem(p['name'],p['id'])
        index=self.project.findData(selected)
        if index>=0:self.project.setCurrentIndex(index)
    def render_event(self,e):
        self.event_data=e;clear(self.meta.box);self.meta.add(row(badge(e['severity']),label(e['id'],'mono'),badge('Demo · 合成数据' if e['source']=='demo' else 'Live XDR',e['source'])))
        self.meta.add(label(e['name'],'title',True));self.meta.add(label(e['description'],'muted',True));self.meta.add(row(label('受影响资产\n'+e['asset']+' / '+e['asset_ip']),label('攻击类型\n'+e['attack_type']),label('最近发现\n'+date(e['time'])),label('关联告警\n'+str(len(e['alert_ids']))+' 个')))
        if e.get('project_id') and not self.project.currentData():
            index=self.project.findData(e['project_id'])
            if index>=0:self.project.setCurrentIndex(index)
        self.job_picker.blockSignals(True);self.job_picker.clear()
        for j in e['investigations']:self.job_picker.addItem(date(j['created_at'])+' · '+j['status']+' · '+j['id'],j['id'])
        if self.job_id:
            i=self.job_picker.findData(self.job_id)
            if i>=0:self.job_picker.setCurrentIndex(i)
        elif e['investigations']:self.job_id=e['investigations'][0]['id']
        self.job_picker.blockSignals(False)
        if self.job_id:self.poll()
    def investigate(self):
        project=self.project.currentData()
        if not project:self.client.failure.emit('请选择部署对应的代码项目');return
        self.start.setEnabled(False);self.start.setText('正在创建调查…');current=self.id
        def done(job):
            self.start.setEnabled(True);self.start.setText('✧  AI Investigation')
            if self.id!=current:return
            self.job_id=job['id'];self.view.signature=None;self.tabs.setCurrentIndex(1);self.poll();self.client.request('/events/'+self.id,self.render_event)
        def error(message):self.start.setEnabled(True);self.start.setText('✧  AI Investigation');self.client.failure.emit(message)
        self.client.request('/investigations',done,'POST',{'event_id':self.id,'project_id':project},error)
    def pick_job(self,i):
        id=self.job_picker.currentData()
        if id:self.job_id=id;self.view.signature=None;self.poll()
    def poll(self):
        if not self.isVisible() or not self.job_id or self.pending:return
        self.pending=True;current=self.job_id
        def done(job):
            self.pending=False
            if self.job_id==current:self.view.set_job(job);self.view.show()
        def error(message):self.pending=False;self.client.failure.emit(message)
        self.client.request('/investigations/'+current,done,on_error=error)

class JobPage(Page):
    def __init__(self,client,navigate):
        super().__init__();self.client=client;self.id=None;self.pending=False;self.layout.addWidget(page_header('INVESTIGATION DETAIL','调查详情','可追踪的证据快照、静态发现和代码关联。',button('← 返回任务列表',lambda:navigate('jobs'))));self.view=InvestigationView(client,navigate);self.layout.addWidget(self.view);self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.refresh);self.timer.start()
    def load(self,id):self.id=id;self.view.signature=None;self.refresh(force=True)
    def refresh(self,force=False):
        if not self.id or self.pending or not (self.isVisible() or force):return
        self.pending=True;current=self.id
        def done(job):
            self.pending=False
            if self.id==current:self.view.set_job(job)
        def error(message):self.pending=False;self.client.failure.emit(message)
        self.client.request('/investigations/'+current,done,on_error=error)
