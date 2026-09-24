from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QSplitter,QTreeWidget,QTreeWidgetItem,QComboBox,QDialog,QFormLayout,QLineEdit,QFileDialog,QTabWidget,QDialogButtonBox,QProgressBar
from .widgets import Page,Panel,Table,CodeViewer,label,button,badge,row,page_header,clear,date

class ImportDialog(QDialog):
    def __init__(self,client,on_created,parent=None):
        super().__init__(parent);self.client=client;self.on_created=on_created;self.setWindowTitle('添加代码项目');self.resize(650,430)
        box=QVBoxLayout(self);box.setContentsMargins(25,25,25,25);box.setSpacing(17);box.addWidget(label('添加代码项目','title'));box.addWidget(label('源代码只用于静态分析；不会安装依赖或执行项目。','muted',True));form=QFormLayout();self.name=QLineEdit();self.name.setPlaceholderText('例如：订单服务');form.addRow('项目名称',self.name);self.source=QComboBox();self.source.addItem('本地代码目录','local');self.source.addItem('ZIP 压缩包','zip');self.source.addItem('公开 Git Repository','git');form.addRow('导入方式',self.source);self.path=QLineEdit();self.browse=button('浏览…',self.choose);form.addRow('路径 / Git URL',row(self.path,self.browse));self.branch=QLineEdit();self.branch.setPlaceholderText('留空使用默认分支');form.addRow('Git Branch',self.branch);box.addLayout(form)
        self.notice=label('本地目录需在 Settings 显示的允许目录范围中。ZIP 最大 25 MB。','muted',True);box.addWidget(self.notice);self.error=label('','muted',True);box.addWidget(self.error);box.addStretch();self.submit=button('导入项目',self.create,True);box.addWidget(row(button('取消',self.reject),self.submit));self.source.currentIndexChanged.connect(self.change)
    def change(self):self.browse.setEnabled(self.source.currentData()!='git');self.branch.setEnabled(self.source.currentData()=='git')
    def choose(self):
        if self.source.currentData()=='zip':filename,_=QFileDialog.getOpenFileName(self,'选择 ZIP','','ZIP (*.zip)')
        else:filename=QFileDialog.getExistingDirectory(self,'选择代码目录')
        if filename:self.path.setText(filename)
    def create(self):
        name=self.name.text().strip();path=self.path.text().strip();source=self.source.currentData()
        if not name or not path:self.error.setText('请填写项目名称与路径 / URL。');return
        self.submit.setEnabled(False);self.error.setText('正在导入…')
        def success(project):self.on_created(project);self.accept()
        def failed(message):self.error.setText(message);self.submit.setEnabled(True)
        if source=='zip':self.client.upload('/projects/upload',name,path,success,failed)
        else:self.client.request('/projects',success,'POST',{'name':name,'source':source,'path':path if source=='local' else '', 'git_url':path if source=='git' else '', 'branch':self.branch.text()},failed)

class AuditPage(Page):
    def __init__(self,client,navigate):
        super().__init__();self.client=client;self.navigate=navigate;self.projects=[];self.scan=None;self.project_id=None;self.sources={};self.selected_finding=None
        self.layout.addWidget(page_header('CODE SECURITY','代码审计','静态扫描、路由定位与源代码上下文，在一个原生工作区完成。',button('＋ 添加项目',self.add_project,True)))
        self.picker=QComboBox();self.picker.setMinimumWidth(350);self.picker.currentIndexChanged.connect(self.choose_project);self.scan_button=button('▷  运行静态扫描',self.run_scan,True);self.info=label('请选择代码项目','muted');self.layout.addWidget(row(self.picker,self.scan_button,self.info));self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.hide();self.layout.addWidget(self.progress)
        splitter=QSplitter(Qt.Horizontal);self.tree=QTreeWidget();self.tree.setHeaderLabel('文件树');self.tree.setMinimumWidth(190);self.tree.currentItemChanged.connect(self.select_file);splitter.addWidget(self.tree)
        source=QWidget();s=QVBoxLayout(source);s.setContentsMargins(10,0,0,0);self.file_label=label('SOURCE CODE','mono');s.addWidget(self.file_label);self.viewer=CodeViewer();self.viewer.setMinimumHeight(310);s.addWidget(self.viewer);splitter.addWidget(source);splitter.setStretchFactor(1,4);splitter.setSizes([210,900]);self.layout.addWidget(splitter)
        self.findings_panel=Panel('静态发现',action=badge('Static Finding','static'));self.findings=Table(['漏洞类型 / 规则','Severity','CWE','File / Line','Function']);self.findings.cellClicked.connect(self.select_finding);self.findings_panel.add(self.findings);self.layout.addWidget(self.findings_panel)
        self.detail=Panel('发现详情 / 修复建议');self.layout.addWidget(self.detail)
    def refresh(self):self.client.request('/projects',self.render_projects)
    def render_projects(self,projects):
        self.projects=projects;previous=self.project_id;self.picker.blockSignals(True);self.picker.clear()
        for p in projects:self.picker.addItem(p['name']+'   ·   '+str(p['file_count'])+' files',p['id'])
        index=self.picker.findData(previous);self.picker.setCurrentIndex(index if index>=0 else 0);self.picker.blockSignals(False);self.choose_project()
    def add_project(self):
        def created(project):self.project_id=project['id'];self.refresh()
        ImportDialog(self.client,created,self).exec()
    def choose_project(self):
        self.project_id=self.picker.currentData();self.scan=None;self.selected_finding=None;self.viewer.clear();self.findings.populate([]);clear(self.detail.box)
        if not self.project_id:return
        current=self.project_id
        self.client.request('/projects/'+current+'/files',lambda d:self.render_files(d) if self.project_id==current else None)
        self.client.request('/projects/'+current+'/scan',lambda d:self.render_scan(d) if self.project_id==current else None)
    def render_files(self,data):
        self.tree.clear();nodes={}
        for file in data['files']:
            parent=None;parts=file.split('/')
            for i,part in enumerate(parts):
                key='/'.join(parts[:i+1])
                if key not in nodes:
                    item=QTreeWidgetItem([('▸ ' if i<len(parts)-1 else '◇ ')+part]);nodes[key]=item
                    if parent:parent.addChild(item)
                    else:self.tree.addTopLevelItem(item)
                    if i==len(parts)-1:item.setData(0,Qt.UserRole,file)
                parent=nodes[key]
        self.tree.expandAll();self.info.setText(f"{len(data['files'])} 个源文件 · {data['skipped']} 个已排除")
        if data['files']:
            first=next((key for key in data['files'] if key.endswith('.py')),data['files'][0]);self.tree.setCurrentItem(nodes[first])
    def select_file(self,item,previous=None):
        if not item or not item.data(0,Qt.UserRole):return
        file=item.data(0,Qt.UserRole);self.show_file(file)
    def show_file(self,file,highlight=None):
        from urllib.parse import quote
        current=self.project_id;self.file_label.setText(file+' · 当前工作目录内容')
        def done(d):
            if self.project_id==current and self.file_label.text().startswith(file+' ·'):self.viewer.show_code(d['content'],1,highlight)
        self.client.request('/projects/'+current+'/file?path='+quote(file,safe=''),done)
    def run_scan(self):
        if not self.project_id:return
        self.scan_button.setEnabled(False);self.progress.show();current=self.project_id;self.info.setText('Bandit + Python AST 正在扫描…')
        def done(scan):
            self.scan_button.setEnabled(True);self.progress.hide()
            if self.project_id==current:self.render_scan(scan)
        def error(message):self.scan_button.setEnabled(True);self.progress.hide();self.info.setText('扫描失败');self.client.failure.emit(message)
        self.client.request('/projects/'+current+'/scan',done,'POST',on_error=error)
    def render_scan(self,scan):
        self.scan=scan
        if not scan:self.info.setText('尚未扫描 · 点击运行静态扫描');return
        rows=scan['findings'];self.findings.populate([[f['type']+' / '+f['rule'],f['severity'],f['cwe'],f"{f['file']}:{f['line']}",f['function']] for f in rows])
        for i,f in enumerate(rows):self.findings.severity(i,1,f['severity'])
        self.info.setText(f"{scan['python_files']} Python 文件 · {len(rows)} 个发现 · {scan['status']} · {date(scan['created_at'])}")
        clear(self.detail.box)
        if not scan['python_files']:self.detail.add(label('当前项目没有 Python 文件。支持代码浏览，但此版本未运行其他语言的语义分析。','muted',True))
        for error in scan['errors']:self.detail.add(label(str(error),'muted',True))
        if rows:self.findings.selectRow(0);self.select_finding(0,0)
    def select_finding(self,r,c=0):
        if not self.scan or not 0<=r<len(self.scan['findings']):return
        f=self.scan['findings'][r];self.selected_finding=f;self.show_file(f['file'],f['line']);clear(self.detail.box);self.detail.add(row(label(f['type']+' · '+f['function'],'sectionTitle'),badge(f['severity']),badge(f['cwe'],'static')))
        self.detail.add(label(f['description'],wrap=True));self.detail.add(label('以下代码来自扫描快照；上方文件查看器显示当前工作目录，可能已有更改。','muted',True));source=CodeViewer();source.show_code(f['code'],f['code_start'],f['line']);source.setFixedHeight(155);self.detail.add(source);self.detail.add(label('修复建议：'+f['fix'],wrap=True))
        if f['patch']:
            fix=CodeViewer();fix.show_code(f['patch']);fix.setFixedHeight(140);self.detail.add(fix)
        self.detail.add(label(f"来源 Bandit {f['rule']} · 文件 SHA-256 {f['file_sha256']}",'mono',True))
