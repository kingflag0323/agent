from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QStackedWidget,QButtonGroup,QFrame,QSizePolicy,QComboBox
from .client import Client
from .theme import ThemeController
from .widgets import label,button,badge,row
from .overview import Dashboard,EventsPage,JobsPage
from .investigation import EventPage,JobPage
from .audit import AuditPage
from .settings_page import SettingsPage

class MainWindow(QMainWindow):
    def __init__(self,base='http://127.0.0.1:8000'):
        super().__init__();self.setWindowTitle('Sentinel — XDR × AI × Code | 原生桌面安全运营平台');self.resize(1500,980);self.setMinimumSize(1120,740);self.theme=ThemeController(self)
        self.client=Client(base,self);self.client.failure.connect(self.notify);central=QWidget();shell=QHBoxLayout(central);shell.setContentsMargins(0,0,0,0);shell.setSpacing(0);self.setCentralWidget(central)
        sidebar=QWidget();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(92);side=QVBoxLayout(sidebar);side.setContentsMargins(8,18,8,14);side.setSpacing(10);brand=label('◈  S','brand');brand.setAlignment(Qt.AlignCenter);side.addWidget(brand);side.addSpacing(16)
        self.nav={};self.group=QButtonGroup(self);self.group.setExclusive(True)
        for key,title in [('dashboard','◫\n态势'),('events','◎\n事件'),('audit','⌘\n代码'),('jobs','✧\n调查'),('reports','▤\n报告')]:
            b=button(title,lambda checked=False,k=key:self.navigate(k));b.setObjectName('nav');b.setCheckable(True);self.group.addButton(b);side.addWidget(b);self.nav[key]=b
        side.addStretch();b=button('⚙\n设置',lambda:self.navigate('settings'));b.setObjectName('nav');b.setCheckable(True);self.group.addButton(b);self.nav['settings']=b;side.addWidget(b);side.addStretch();self.source_badge=badge('DEMO','demo');side.addWidget(self.source_badge);side.addWidget(label('只读调查','muted'));shell.addWidget(sidebar)
        right=QWidget();right_box=QVBoxLayout(right);right_box.setContentsMargins(0,0,0,0);right_box.setSpacing(0)
        top=QFrame();top.setObjectName('toolbar');top.setFixedHeight(56);topbar=QHBoxLayout(top);topbar.setContentsMargins(30,0,30,0);topbar.addWidget(label('SENTINEL','eyebrow'));topbar.addSpacing(16);self.crumb=label('Workspace  /  Overview','muted');topbar.addWidget(self.crumb);topbar.addStretch();self.backend_status=label('● Backend connected','muted');topbar.addWidget(self.backend_status);topbar.addSpacing(20);self.theme_select=QComboBox();self.theme_select.setAccessibleName('外观主题');self.theme_select.setToolTip('日间 / 夜间 / 跟随操作系统；自动保存');
        for text,key in [('☀ 日间','light'),('☾ 夜间','dark'),('◐ 跟随系统','system')]:self.theme_select.addItem(text,key)
        self.theme_select.setCurrentIndex(self.theme_select.findData(self.theme.mode));self.theme_select.currentIndexChanged.connect(lambda _:self.theme.set_mode(self.theme_select.currentData()));topbar.addWidget(self.theme_select);right_box.addWidget(top)
        self.stack=QStackedWidget();right_box.addWidget(self.stack,1);shell.addWidget(right,1)
        self.pages={'dashboard':Dashboard(self.client,self.navigate),'events':EventsPage(self.client,self.navigate),'audit':AuditPage(self.client,self.navigate),'jobs':JobsPage(self.client,self.navigate),'reports':JobsPage(self.client,self.navigate,True),'event':EventPage(self.client,self.navigate),'job':JobPage(self.client,self.navigate),'settings':SettingsPage(self.client,self.refresh_mode)}
        for page in self.pages.values():self.stack.addWidget(page)
        self.statusBar().showMessage('原生 Qt 桌面客户端 · 数据与代码保留在本机 · 双击事件开始调查')
        self.current='dashboard';self.navigate('dashboard');self.refresh_mode()
    def navigate(self,key,id=None):
        self.current=key;page=self.pages[key];self.stack.setCurrentWidget(page);navkey={'event':'events','job':'jobs'}.get(key,key)
        if navkey in self.nav:self.nav[navkey].setChecked(True)
        self.crumb.setText('Workspace  /  '+{'dashboard':'安全态势总览','events':'安全运营','event':'事件详情','audit':'代码审计','jobs':'AI Agent','job':'调查详情','reports':'调查报告','settings':'系统设置'}[key])
        if id:page.load(id)
        else:page.refresh()
    def notify(self,message):
        self.statusBar().showMessage(message,15000)
        self.statusBar().setToolTip(message)
        # Non-modal error presentation lets active investigations keep updating.
        if not hasattr(self,'notice'):
            from PySide6.QtWidgets import QLabel
            self.notice=QLabel(self);self.notice.setWordWrap(True);self.notice.setTextFormat(Qt.PlainText);self.notice.setObjectName('notice');self.notice.hide();self.notice_timer=QTimer(self);self.notice_timer.setSingleShot(True);self.notice_timer.timeout.connect(self.notice.hide)
        self.notice.setText(message);self.notice.setFixedWidth(min(670,self.width()-100));self.notice.adjustSize();self.notice.move(self.width()-self.notice.width()-30,75);self.notice.show();self.notice.raise_();self.notice_timer.start(10000)
    def refresh_mode(self):
        def done(data):
            mode=data['xdr']['mode'];self.source_badge.setText('DEMO' if mode=='demo' else 'LIVE XDR');self.source_badge.setProperty('badge','demo' if mode=='demo' else 'live');self.source_badge.style().unpolish(self.source_badge);self.source_badge.style().polish(self.source_badge);self.backend_status.setText('● 本机服务已连接 · '+('离线规则模式' if data['llm']['mode']=='mock' else '外部模型'))
        self.client.request('/settings',done)
