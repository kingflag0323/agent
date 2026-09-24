"""Application-wide native palettes. UI preferences are local, separate from API secrets."""
from pathlib import Path
import os
from PySide6.QtCore import QObject, QSettings, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

PALETTES={
 'dark':dict(bg='#10141c',panel='#181e28',surface='#202936',border='#303b4c',text='#e7edf6',muted='#9cabc0',accent='#78adff',primary='#2563eb',hover='#29384d',selected='#233c60',code='#121923',danger='#ff939d',orange='#ffb47a',green='#6ddcbd',blue='#80b8ff',yellow='#e8cf80',highlight='#49313d'),
 'light':dict(bg='#f3f6fb',panel='#ffffff',surface='#edf2f8',border='#ced8e5',text='#1c2b40',muted='#52667e',accent='#215fc4',primary='#245edb',hover='#e3ecf9',selected='#dceaff',code='#f7f9fd',danger='#b7223c',orange='#9c4a10',green='#087762',blue='#1d60b1',yellow='#80620e',highlight='#ffe3e7')
}
CURRENT='dark'
COLORS={}
CHART=[]

def color(name):return PALETTES[CURRENT][name]
def update_colors():
    COLORS.update({k:color(v) for k,v in {'critical':'danger','high':'orange','medium':'yellow','low':'blue','info':'muted','demo':'accent','live':'green','completed':'green','running':'accent','queued':'muted','failed':'danger','interrupted':'orange','open':'orange','high-confidence':'green','static':'accent','fact':'green','inference':'yellow'}.items()})
    CHART[:]=[color(k) for k in ('accent','orange','green','blue','yellow','muted')]
update_colors()

QSS='''
* { font-family: "Microsoft YaHei UI", "Noto Sans CJK SC", "DejaVu Sans"; font-size:13px; }
QWidget { color:@text; }
QMainWindow, QDialog, QWidget#content { background:@bg; }
QWidget#sidebar, QFrame#toolbar { background:@panel; border:1px solid @border; }
QFrame#panel,QFrame#stat { background:@panel; border:1px solid @border; border-radius:8px; }
QFrame#banner { background:@selected; border:1px solid @border; border-radius:8px; }
QLabel { background:transparent; border:none; }
QLabel#muted,QLabel#mono { color:@muted; }
QLabel#mono { font-family:"Consolas","DejaVu Sans Mono",monospace; font-size:11px; }
QLabel#eyebrow { color:@accent; font-size:10px; font-weight:700; letter-spacing:1px; }
QLabel#title { font-size:25px; font-weight:700; }
QLabel#sectionTitle { font-size:15px; font-weight:600; }
QLabel#value { font-size:31px; font-weight:600; }
QLabel#brand { color:@accent; font-size:21px; font-weight:700; }
QLabel#notice { background:@panel; color:@danger; border:1px solid @danger; border-radius:8px; padding:14px; }
QPushButton { background:@surface; border:1px solid @border; border-radius:6px; padding:8px 12px; color:@text; }
QPushButton:hover { background:@hover; border-color:@accent; }
QPushButton:pressed { background:@selected; }
QPushButton:disabled { color:@muted; background:@surface; }
QPushButton#primary { background:@primary; border:1px solid @primary; color:white; font-weight:600; }
QPushButton#primary:hover { background:#3478e8; }
QPushButton#nav { background:transparent; border:none; text-align:center; padding:12px 3px; color:@muted; font-size:12px; }
QPushButton#nav:checked { background:@selected; color:@accent; border-left:3px solid @accent; }
QPushButton#nav:hover { background:@hover; color:@text; }
QPushButton#link { background:transparent; border:none; color:@accent; padding:4px; }
QPushButton#danger { color:@danger; }
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox { background:@panel; border:1px solid @border; border-radius:6px; padding:8px; min-height:19px; selection-background-color:@selected; selection-color:@text; }
QLineEdit:focus,QComboBox:focus { border-color:@accent; }
QComboBox::drop-down { border:none; width:24px; }
QComboBox QAbstractItemView { background:@panel; color:@text; selection-background-color:@selected; selection-color:@text; padding:5px; }
QCheckBox { spacing:8px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid @muted; border-radius:4px; background:@surface; }
QCheckBox::indicator:checked { background:@primary; border-color:@accent; }
QTableWidget { background:@panel; border:none; gridline-color:@border; outline:0; selection-background-color:@selected; selection-color:@text; alternate-background-color:@surface; }
QTableWidget::item { padding:10px 8px; border-bottom:1px solid @border; }
QHeaderView::section,QTableCornerButton::section { background:@surface; color:@muted; border:none; padding:12px 8px; font-size:11px; }
QScrollArea { border:none; background:transparent; }
QScrollArea > QWidget > QWidget { background:transparent; }
QScrollBar:vertical { background:@bg; width:8px; }
QScrollBar::handle:vertical { background:@border; border-radius:4px; min-height:30px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar:horizontal { background:@bg; height:8px; }
QScrollBar::handle:horizontal { background:@border; min-width:30px; }
QTabWidget::pane { border:none; background:transparent; }
QTabBar::tab { color:@muted; background:transparent; padding:12px 18px; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:@accent; border-bottom:2px solid @accent; }
QTabBar::tab:hover { background:@hover; }
QPlainTextEdit,QTextEdit { background:@code; color:@text; border:1px solid @border; border-radius:6px; padding:12px; font-family:"Consolas","DejaVu Sans Mono",monospace; font-size:12px; selection-background-color:@selected; selection-color:@text; }
QTreeWidget,QListWidget { background:@panel; color:@text; border:1px solid @border; border-radius:6px; outline:0; }
QTreeWidget::item,QListWidget::item { padding:8px 5px; }
QTreeWidget::item:selected,QListWidget::item:selected { background:@selected; color:@text; }
QSplitter::handle { background:@border; }
QProgressBar { background:@surface; border:none; border-radius:3px; max-height:5px; }
QProgressBar::chunk { background:@accent; }
QToolTip { color:@text; background:@panel; border:1px solid @border; padding:7px; }
QStatusBar { background:@panel; color:@muted; border-top:1px solid @border; }
QMessageBox { background:@panel; }
'''

def stylesheet():
    result=QSS
    for key,value in PALETTES[CURRENT].items():result=result.replace('@'+key,value)
    for key,value in COLORS.items():
        result+=f'\nQLabel[tone="{key}"] {{ color:{value}; }}\nQLabel[badge="{key}"] {{ color:{value}; background:{color("surface")}; border:1px solid {color("border")}; border-radius:5px; padding:4px 7px; font-size:11px; }}'
    for i,value in enumerate(CHART):result+=f'\nQLabel[chartIndex="{i}"] {{ color:{value}; }}'
    return result

class ThemeController(QObject):
    changed=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.settings=QSettings(str(Path(os.environ['SXF_DATA_DIR'])/'desktop.ini'),QSettings.IniFormat)
        self.mode=str(self.settings.value('appearance/mode','system'))
        if self.mode not in ('system','light','dark'):self.mode='system'
        self.effective=None
        QApplication.instance().styleHints().colorSchemeChanged.connect(lambda *_:self.apply())
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.poll);self.timer.start();self.apply()
    def system_theme(self):
        if os.name=='nt':
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                    return 'light' if winreg.QueryValueEx(key,'AppsUseLightTheme')[0] else 'dark'
            except OSError:pass
        return 'dark' if QApplication.instance().styleHints().colorScheme()==Qt.ColorScheme.Dark else 'light'
    def set_mode(self,mode):
        if mode not in ('system','light','dark'):return
        self.mode=mode;self.settings.setValue('appearance/mode',mode);self.settings.sync();self.apply()
    def poll(self):
        if self.mode=='system':self.apply()
    def apply(self):
        global CURRENT
        effective=self.system_theme() if self.mode=='system' else self.mode
        if effective==self.effective:return
        self.effective=effective;CURRENT=effective;update_colors();app=QApplication.instance()
        pal=QPalette()
        for role,key in [(QPalette.Window,'bg'),(QPalette.WindowText,'text'),(QPalette.Base,'panel'),(QPalette.AlternateBase,'surface'),(QPalette.Text,'text'),(QPalette.Button,'surface'),(QPalette.ButtonText,'text'),(QPalette.Highlight,'selected'),(QPalette.HighlightedText,'text'),(QPalette.ToolTipBase,'panel'),(QPalette.ToolTipText,'text'),(QPalette.PlaceholderText,'muted'),(QPalette.Link,'accent')]:pal.setColor(role,QColor(color(key)))
        app.setPalette(pal);app.setStyleSheet(stylesheet())
        for widget in app.allWidgets():
            if hasattr(widget,'refresh_theme'):widget.refresh_theme()
            widget.update()
        self.changed.emit(effective)
