from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QCheckBox
from .widgets import Page,Panel,label,button,row,page_header,clear,badge

class SettingsPage(Page):
    def __init__(self,client,on_saved=None):
        super().__init__();self.client=client;self.on_saved=on_saved;self.fields={};self.loaded=False
        self.save_button=button('保存配置',self.save,True);self.layout.addWidget(page_header('SYSTEM SETTINGS','系统设置','配置 XDR、模型与调查工具。凭据仅保存在本机后台，不会回显。',self.save_button));self.notice=label('','muted',True);self.layout.addWidget(self.notice)
        columns=QHBoxLayout();left=QVBoxLayout();right=QVBoxLayout();columns.addLayout(left,1);columns.addLayout(right,1);self.layout.addLayout(columns)
        self.xdr=Panel('XDR Connection','已提供地址：172.20.0.140；支持材料所述 AK/SK 签名或授权码；TLS 默认校验。');xform=QFormLayout();xform.setVerticalSpacing(14)
        self.field(xform,'xdr','mode','数据模式','combo',[('Demo 合成数据','demo'),('Live XDR','live')]);self.field(xform,'xdr','base_url','Base URL');self.field(xform,'xdr','auth_type','认证方式','combo',[('AK/SK · HMAC-SHA256','aksk'),('平台授权码','auth_code'),('自定义 Token','token')]);self.field(xform,'xdr','access_key','Access Key','secret');self.field(xform,'xdr','secret_key','Secret Key','secret');self.field(xform,'xdr','auth_code','平台授权码','secret');self.field(xform,'xdr','auth_header','认证 Header');self.field(xform,'xdr','auth_scheme','认证前缀');self.field(xform,'xdr','token','Token / API Key','secret');self.field(xform,'xdr','timeout','超时（秒）','int',(1,120));self.field(xform,'xdr','verify_tls','校验 TLS 证书','bool');self.field(xform,'xdr','ca_bundle','自定义 CA 文件');self.xdr.box.addLayout(xform);self.xdr.add(label('AK/SK 或授权码模式对每次只读请求签名；Token 与前缀仅用于自定义 Token 模式。','muted',True));self.xdr.add(button('测试已保存的 XDR 配置',lambda:self.test('xdr')));left.addWidget(self.xdr)
        llm=Panel('LLM Provider','OpenAI-compatible Chat Completions 协议');form=QFormLayout();form.setVerticalSpacing(14)
        self.field(form,'llm','mode','模型模式','combo',[('Mock · 离线规则模式','mock'),('OpenAI-compatible API','compatible')]);self.field(form,'llm','base_url','Base URL');self.field(form,'llm','api_key','API Key','secret');self.field(form,'llm','model','Model');self.field(form,'llm','temperature','Temperature','float',(0,2));self.field(form,'llm','timeout','Timeout（秒）','int',(1,120));self.field(form,'llm','max_tokens','Max Tokens','int',(100,8000));llm.box.addLayout(form);llm.add(label('Base URL 应含服务所需前缀（如 /v1）。启用外部模型后，调查相关证据与代码片段将发送到你配置的服务。','muted',True));llm.add(button('测试已保存的模型配置',lambda:self.test('llm')));right.addWidget(llm)
        agent=Panel('Agent Controls','原生可审计工作流');form=QFormLayout();self.field(form,'agent','max_steps','Max Steps','int',(5,50));self.field(form,'agent','timeout','Timeout（秒）','int',(10,600));self.field(form,'agent','reviewer','证据 Reviewer','bool');self.field(form,'agent','debug','Debug 日志','bool');agent.box.addLayout(form);left.addWidget(agent)
        audit=Panel('Code Audit','Bandit + Python AST · 源代码仅静态读取');form=QFormLayout();self.field(form,'audit','max_files','最大文件数','int',(1,2000));self.field(form,'audit','max_file_kb','单文件上限（KB）','int',(1,1024));self.field(form,'audit','timeout','扫描超时（秒）','int',(5,120));audit.box.addLayout(form);self.roots=label('','mono',True);audit.add(self.roots);right.addWidget(audit)
        capabilities=Panel('XDR 接口能力边界','只读调用；无封禁、隔离或处置操作。');self.caps=QVBoxLayout();capabilities.box.addLayout(self.caps);self.layout.addWidget(capabilities)
    def field(self,form,group,key,title,kind='text',opts=None):
        if kind=='combo':
            w=QComboBox()
            for text,value in opts:w.addItem(text,value)
        elif kind=='bool':w=QCheckBox('启用')
        elif kind in ('int','float'):
            w=QSpinBox() if kind=='int' else QDoubleSpinBox();w.setRange(*opts)
            if kind=='float':w.setSingleStep(0.1)
        else:
            w=QLineEdit()
            if kind=='secret':w.setEchoMode(QLineEdit.Password);w.setPlaceholderText('留空保留已有密钥')
        form.addRow(title,w);self.fields[(group,key)]=(w,kind)
    def refresh(self):self.client.request('/settings',self.populate);self.client.request('/capabilities',self.capabilities)
    def populate(self,data):
        for (group,key),(w,kind) in self.fields.items():
            if kind=='secret':w.clear();w.setPlaceholderText('已配置 · 留空保留' if data[group].get(key+'_configured') else '尚未配置')
            elif kind=='combo':w.setCurrentIndex(w.findData(data[group][key]))
            elif kind=='bool':w.setChecked(data[group][key])
            elif kind in ('int','float'):w.setValue(data[group][key])
            else:w.setText(str(data[group][key]))
        self.roots.setText('允许本地代码目录：\n'+'\n'.join(data['allowed_roots']));self.loaded=True
    def capabilities(self,data):
        clear(self.caps)
        self.caps.addWidget(label(f"已梳理 {data['documented_endpoint_count']} 个文档接口；实现 {len(data['implemented'])} 个只读能力。认证与接口权限以连接测试结果为准。",'muted',True))
        for item in data['implemented']:self.caps.addWidget(label(item['method']+'  '+item['path']+'    '+item['description'],'mono',True))
        for item in data['unsupported']:self.caps.addWidget(label('Unsupported · '+item['reason'],'muted',True))
    def save(self):
        if not self.loaded:return
        body={}
        for (group,key),(w,kind) in self.fields.items():
            value=w.currentData() if kind=='combo' else w.isChecked() if kind=='bool' else w.value() if kind in ('int','float') else w.text()
            body.setdefault(group,{})[key]=value
        self.save_button.setEnabled(False)
        def done(data):
            self.save_button.setEnabled(True);self.notice.setText('✓ 配置已保存。测试按钮使用刚保存的配置。')
            for (group,key),(w,kind) in self.fields.items():
                if kind=='secret':w.clear();w.setPlaceholderText('已配置 · 留空保留' if data[group].get(key+'_configured') else '尚未配置')
            if self.on_saved:self.on_saved()
        def fail(message):self.save_button.setEnabled(True);self.notice.setText('保存失败：'+message)
        self.client.request('/settings',done,'PUT',body,fail)
    def test(self,provider):
        self.notice.setText('正在测试已保存的 '+provider.upper()+' 配置…')
        self.client.request('/settings/test/'+provider,lambda d:self.notice.setText('✓ '+d['message']),'POST',on_error=lambda error:self.notice.setText('测试失败：'+error))
