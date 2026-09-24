from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLineEdit,QComboBox,QMessageBox
from .widgets import Page,Panel,Table,label,button,badge,row,page_header,clear,date,TrendChart,DonutChart
from .theme import COLORS

class Dashboard(Page):
    def __init__(self,client,navigate):
        super().__init__();self.client=client;self.navigate=navigate;self.loaded=False
        self.layout.addWidget(page_header('SECURITY OVERVIEW','安全态势总览','从攻击现场到漏洞代码，让每一次安全调查都有据可循。',button('↻  同步事件',self.sync)))
        self.container=QWidget();self.box=QVBoxLayout(self.container);self.box.setContentsMargins(0,0,0,0);self.box.setSpacing(20);self.layout.addWidget(self.container)
        self.timer=QTimer(self);self.timer.setInterval(12000);self.timer.timeout.connect(lambda:self.refresh() if self.isVisible() else None);self.timer.start()
    def sync(self):self.client.request('/events/sync',lambda _:self.refresh(),'POST')
    def refresh(self):self.client.request('/dashboard',self.render)
    def render(self,d):
        clear(self.box);self.loaded=True
        self.box.addWidget(row(badge('DEMO WORKSPACE' if d['mode']=='demo' else 'LIVE XDR','demo' if d['mode']=='demo' else 'live'),label(d['scope'],'muted',True)))
        stats=QHBoxLayout();stats.setSpacing(14)
        values=[('安全事件',d['total'],f"今日新增 {d['today']}",'high'),('高危与严重',d['severity'].get('high',0)+d['severity'].get('critical',0),f"中危 {d['severity'].get('medium',0)} · 低危 {d['severity'].get('low',0)}",'critical'),('受影响资产',d['assets'],'按资产 IP 去重','low'),('代码静态发现',d['vulnerabilities'],'来自各项目最新扫描','static'),('已关联攻击',d['linked'],f"{d['investigations']} 次调查 · {d['running']} 个运行中",'live')]
        for title,value,sub,color in values:
            card=Panel();card.box.setSpacing(10);card.add(label(title,'muted'));v=label(f'{value:02}','value');v.setProperty('tone',color);card.add(v);card.add(label(sub,'muted'));stats.addWidget(card,1)
        self.box.addLayout(stats)
        charts=QHBoxLayout();charts.setSpacing(18);trend=Panel('攻击活动趋势','最近 7 天 · 当前数据源',badge('● 全部事件   ● 高危 / 严重','static'));trend.add(TrendChart(d['trend']));charts.addWidget(trend,2)
        types=Panel('攻击类型分布',f"{d['total']} 个事件 · 按事件类型聚合");types.add(DonutChart(d['types']))
        for i,t in enumerate(d['types']):
            r=row(label('● '+t['name']),label(str(t['value'])));r.layout().itemAt(0).widget().setProperty('chartIndex',str(i%6));r.layout().setStretch(0,1);types.add(r)
        charts.addWidget(types,1);self.box.addLayout(charts)
        banner=Panel();banner.setObjectName('banner');banner.add(row(label('✧   告警之后，找到真正需要修复的代码。','sectionTitle'),button('体验 Attack → Code  ↗',lambda:self.navigate('event','demo-001'),True)));banner.add(label('XDR Evidence   →   AI Investigation   →   Vulnerable Code','muted'));self.box.addWidget(banner)
        lower=QHBoxLayout();recent=Panel('最近安全事件',action=button('查看全部 ↗',lambda:self.navigate('events')));table=Table(['事件名称','风险等级','受影响资产','发现时间']);table.populate([[e['name'],e['severity'],e['asset_ip'],date(e['time'])] for e in d['recent']]);table.cellDoubleClicked.connect(lambda r,c:self.navigate('event',d['recent'][r]['id']))
        for i,e in enumerate(d['recent']):table.severity(i,1,e['severity'])
        recent.add(table);recent.add(label('双击事件行进入详情','muted'));lower.addWidget(recent,3)
        side=Panel('风险资产 / AI 任务')
        for asset in d['risk_assets']:side.add(row(label(asset['name']),badge(str(asset['count'])+' 事件','high')))
        side.add(label('AI INVESTIGATIONS','eyebrow'))
        for job in d['jobs'][:3]:
            b=button(job['name'],lambda checked=False,id=job['id']:self.navigate('job',id));b.setToolTip(job['status']);side.add(b)
        if not d['jobs']:side.add(label('打开安全事件，启动第一项调查。','muted',True))
        side.box.addStretch();lower.addWidget(side,1);self.box.addLayout(lower)

class EventsPage(Page):
    def __init__(self,client,navigate):
        super().__init__();self.client=client;self.navigate=navigate;self.rows=[];self.page=1
        self.layout.addWidget(page_header('SECURITY OPERATIONS','安全运营','聚合安全事件与攻击举证，从异常信号开始深入调查。',button('↻  同步 XDR',self.sync)))
        panel=Panel();self.search=QLineEdit();self.search.setPlaceholderText('搜索事件、资产或 IP…');self.severity=QComboBox();self.severity.addItem('全部风险等级','')
        for key,title in [('critical','严重'),('high','高危'),('medium','中危'),('low','低危')]:self.severity.addItem(title,key)
        self.status=QComboBox();self.status.addItem('全部状态','');self.status.addItem('待处置','open');self.status.addItem('已处置','closed');panel.add(row(self.search,self.severity,self.status))
        self.table=Table(['事件 / 攻击类型','风险等级','资产 / IP','发现时间','XDR 状态','来源']);self.table.setMinimumHeight(440);self.table.setMaximumHeight(900);self.table.cellDoubleClicked.connect(self.open);panel.add(self.table)
        self.count=label('读取中…','muted');self.prev=button('上一页',lambda:self.change_page(-1));self.next=button('下一页',lambda:self.change_page(1));self.open_button=button('打开选中事件  ↗',self.open_selected,True);panel.add(row(self.count,self.prev,self.next,self.open_button));self.layout.addWidget(panel)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.reset)
        self.search.textChanged.connect(lambda:self.timer.start());self.severity.currentIndexChanged.connect(self.reset);self.status.currentIndexChanged.connect(self.reset)
    def sync(self):self.client.request('/events/sync',lambda _:self.refresh(),'POST')
    def reset(self):self.page=1;self.refresh()
    def change_page(self,d):self.page+=d;self.refresh()
    def refresh(self):
        from urllib.parse import urlencode
        query=urlencode({'q':self.search.text(),'severity':self.severity.currentData(),'status':self.status.currentData(),'page':self.page,'page_size':10});self.client.request('/events?'+query,self.render)
    def render(self,d):
        self.rows=d['items'];self.table.populate([[e['name']+'\n'+e['attack_type'],e['severity'],e['asset']+'\n'+e['asset_ip'],date(e['time']),e['status'],'Demo' if e['source']=='demo' else 'Live'] for e in self.rows]);self.count.setText(f"共 {d['total']} 个事件  ·  第 {self.page} 页  ·  双击进入详情")
        for i,e in enumerate(self.rows):self.table.severity(i,1,e['severity']);self.table.severity(i,4,e['status'])
        self.prev.setEnabled(self.page>1);self.next.setEnabled(self.page*10<d['total']);self.open_button.setEnabled(bool(self.rows))
        if self.rows:self.table.selectRow(0)
    def open(self,r,c=0):
        if 0<=r<len(self.rows):self.navigate('event',self.rows[r]['id'])
    def open_selected(self):self.open(self.table.currentRow())

class JobsPage(Page):
    def __init__(self,client,navigate,reports=False):
        super().__init__();self.client=client;self.navigate=navigate;self.reports=reports;self.rows=[]
        self.layout.addWidget(page_header('INVESTIGATION REPORTS' if reports else 'AGENT WORKSPACE','调查报告' if reports else 'AI Agent 调查','工具执行、证据采集、代码关联及复核均可回溯。',button('从安全事件开始  ↗',lambda:navigate('events'),True)))
        p=Panel();self.table=Table(['调查事件','代码项目','任务状态','漏洞候选','创建时间']);self.table.setMinimumHeight(440);self.table.cellDoubleClicked.connect(self.open);p.add(self.table);p.add(button('打开选中调查',lambda:self.open(self.table.currentRow())));self.layout.addWidget(p)
        self.timer=QTimer(self);self.timer.setInterval(3000);self.timer.timeout.connect(lambda:self.refresh() if self.isVisible() else None);self.timer.start()
    def refresh(self):self.client.request('/investigations',self.render)
    def render(self,jobs):
        selected=self.rows[self.table.currentRow()]['id'] if 0<=self.table.currentRow()<len(self.rows) else None
        self.rows=[j for j in jobs if not self.reports or j['status']=='completed'];self.table.populate([[j['event']['name'],j['project']['name'],j['status'],str(len(j.get('correlation',{}).get('matches',[]))) if j.get('correlation') else '—',date(j['created_at'])] for j in self.rows])
        for i,j in enumerate(self.rows):
            self.table.severity(i,2,j['status'])
            if j['id']==selected:self.table.selectRow(i)
        if selected is None and self.rows:self.table.selectRow(0)
    def open(self,r,c=0):
        if 0<=r<len(self.rows):self.navigate('job',self.rows[r]['id'])
