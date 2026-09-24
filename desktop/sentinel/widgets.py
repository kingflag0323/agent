import json
import re
from datetime import datetime
from PySide6.QtCore import Qt,QRectF,QPointF,QRegularExpression
from PySide6.QtGui import QColor,QFont,QPainter,QPainterPath,QLinearGradient,QPen,QSyntaxHighlighter,QTextCharFormat,QTextCursor
from PySide6.QtWidgets import QWidget,QLabel,QFrame,QVBoxLayout,QHBoxLayout,QPushButton,QScrollArea,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPlainTextEdit,QTextEdit,QSizePolicy,QLayout
from . import theme
from .theme import COLORS
color=theme.color

LABELS={'critical':'严重','high':'高危','medium':'中危','low':'低危','info':'信息','open':'待处置','investigating':'处置中','completed':'已完成','running':'运行中','queued':'排队中','failed':'失败','interrupted':'已中断','closed':'已关闭','not_scanned':'未扫描','partial':'部分完成','protected':'已防护','contained':'已遏制','pending':'挂起','accepted':'接受风险','passed':'通过','skipped':'未启用'}

def label(text='',kind='',wrap=False):
    w=QLabel(str(text));w.setTextFormat(Qt.PlainText)
    if kind:w.setObjectName(kind)
    w.setWordWrap(wrap)
    return w

def button(text,fn=None,primary=False):
    w=QPushButton(text);w.setCursor(Qt.PointingHandCursor)
    if primary:w.setObjectName('primary')
    if fn:w.clicked.connect(fn)
    return w

def clear(layout):
    while layout.count():
        item=layout.takeAt(0)
        if item.widget():item.widget().deleteLater()
        if item.layout():clear(item.layout())

def row(*widgets,stretch=False):
    w=QWidget();l=QHBoxLayout(w);l.setContentsMargins(0,0,0,0);l.setSpacing(12)
    for x in widgets:l.addWidget(x)
    if stretch:l.addStretch()
    return w

def badge(text,key=None):
    k=key or text;w=label(LABELS.get(text,text));w.setProperty('badge',k if k in COLORS else 'info')
    w.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
    return w

def page_header(eyebrow,title,description,actions=None):
    w=QWidget();r=QHBoxLayout(w);r.setContentsMargins(0,0,0,12);left=QVBoxLayout();left.setSpacing(7)
    left.addWidget(label(eyebrow,'eyebrow'));left.addWidget(label(title,'title'));left.addWidget(label(description,'muted',True));r.addLayout(left,1)
    if actions:r.addWidget(actions,0,Qt.AlignVCenter)
    return w

class Panel(QFrame):
    def __init__(self,title='',subtitle='',action=None):
        super().__init__();self.setObjectName('panel');self.box=QVBoxLayout(self);self.box.setContentsMargins(20,18,20,18);self.box.setSpacing(15)
        if title:
            h=QHBoxLayout();v=QVBoxLayout();v.addWidget(label(title,'sectionTitle'))
            if subtitle:v.addWidget(label(subtitle,'muted',True))
            h.addLayout(v,1)
            if action:h.addWidget(action)
            self.box.addLayout(h)
    def add(self,w,stretch=0):self.box.addWidget(w,stretch);return w

class Page(QScrollArea):
    def __init__(self):
        super().__init__();self.setWidgetResizable(True);self.setFrameShape(QFrame.NoFrame)
        self.body=QWidget();self.body.setObjectName('content');self.layout=QVBoxLayout(self.body);self.layout.setContentsMargins(30,26,30,24);self.layout.setSpacing(20);self.layout.setAlignment(Qt.AlignTop);self.setWidget(self.body)
    def refresh(self):pass

class Table(QTableWidget):
    def __init__(self,headers):
        super().__init__(0,len(headers));self.setHorizontalHeaderLabels(headers);self.verticalHeader().hide();self.setShowGrid(False);self.setAlternatingRowColors(False);self.setSelectionBehavior(QAbstractItemView.SelectRows);self.setSelectionMode(QAbstractItemView.SingleSelection);self.setEditTriggers(QAbstractItemView.NoEditTriggers);self.setWordWrap(False);self.setSortingEnabled(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.verticalHeader().setDefaultSectionSize(65);self.setMinimumHeight(240)
    def populate(self,rows):
        self.setRowCount(len(rows))
        for i,values in enumerate(rows):
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.setItem(i,j,item)
        self.setMaximumHeight(max(130,min(650,len(rows)*65+45)))
    def severity(self,row,col,key):
        item=self.item(row,col)
        if item:item.setData(Qt.UserRole,key);item.setForeground(QColor(COLORS.get(key,color('muted'))));item.setText('●  '+LABELS.get(key,key))
    def refresh_theme(self):
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item=self.item(r,c)
                if item and item.data(Qt.UserRole):item.setForeground(QColor(COLORS.get(item.data(Qt.UserRole),color('muted'))))

def date(value):
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone().strftime('%m-%d  %H:%M:%S')
    except (ValueError,TypeError,AttributeError):return '未提供'

class CodeHighlighter(QSyntaxHighlighter):
    def highlightBlock(self,text):
        patterns=[(r'\b(def|class|return|import|from|as|if|else|for|in|with|try|except|raise|async|await|True|False|None)\b',color('accent')),(r'\b\d+\b',color('orange')),(r'"[^"\n]*"|\x27[^\x27\n]*\x27',color('green')),(r'#.*$',color('muted')),(r'@[\w.]+',color('yellow'))]
        for pattern,tint in patterns:
            for m in re.finditer(pattern,text):
                fmt=QTextCharFormat();fmt.setForeground(QColor(tint));self.setFormat(m.start(),m.end()-m.start(),fmt)

class CodeViewer(QPlainTextEdit):
    def __init__(self):
        super().__init__();self.setReadOnly(True);self.setLineWrapMode(QPlainTextEdit.NoWrap);self.highlighter=CodeHighlighter(self.document());self.setMinimumHeight(180)
    def refresh_theme(self):
        self.highlighter.rehighlight()
        selections=self.extraSelections()
        for selection in selections:selection.format.setBackground(QColor(color('highlight')))
        self.setExtraSelections(selections)
    def show_code(self,text,start=1,highlight=None):
        self.setPlainText('\n'.join(f'{i+start:4}  {line}' for i,line in enumerate(text.splitlines())))
        self.setExtraSelections([])
        if highlight is not None:
            index=highlight-start
            if 0<=index<self.document().blockCount():
                cursor=QTextCursor(self.document().findBlockByNumber(index));self.setTextCursor(cursor)
                selection=QTextEdit.ExtraSelection();selection.cursor=cursor;selection.format.setBackground(QColor(color('highlight')));selection.format.setProperty(QTextCharFormat.FullWidthSelection,True);self.setExtraSelections([selection]);self.centerCursor()

class TrendChart(QWidget):
    def __init__(self,values):super().__init__();self.values=values;self.setMinimumHeight(220)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);w=self.width();h=self.height();left=30;right=w-25;top=12;bottom=h-28
        maximum=max(2,max((x['events'] for x in self.values),default=2));height=bottom-top
        p.setFont(QFont('DejaVu Sans',9))
        for i in range(5):
            y=bottom-i*height/4;p.setPen(QPen(QColor(color('border')),1,Qt.DashLine));p.drawLine(QPointF(left,y),QPointF(right,y));p.setPen(QColor(color('muted')));p.drawText(0,int(y)+4,str(round(maximum*i/4,1)))
        for key,tint in [('events',color('accent')),('high',color('orange'))]:
            pts=[QPointF(left+i*(right-left)/max(1,len(self.values)-1),bottom-v[key]/maximum*height) for i,v in enumerate(self.values)]
            if not pts:continue
            path=QPainterPath(pts[0])
            for pt in pts[1:]:path.lineTo(pt)
            if key=='events':
                fill=QPainterPath(path);fill.lineTo(right,bottom);fill.lineTo(left,bottom);fill.closeSubpath();gradient=QLinearGradient(0,top,0,bottom);c=QColor(tint);c.setAlpha(65);gradient.setColorAt(0,c);c.setAlpha(0);gradient.setColorAt(1,c);p.fillPath(fill,gradient)
            p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor(tint),2.4));p.drawPath(path)
            for pt in pts:p.setBrush(QColor(tint));p.drawEllipse(pt,3,3)
        p.setPen(QColor(color('muted')))
        for i,v in enumerate(self.values):p.drawText(int(left+i*(right-left)/max(1,len(self.values)-1))-14,h-5,v['date'])

class DonutChart(QWidget):
    palette=theme.CHART
    def __init__(self,values):super().__init__();self.values=values;self.setMinimumHeight(160)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);size=130;rect=QRectF((self.width()-size)/2,12,size,size);total=sum(x['value'] for x in self.values);angle=90*16
        for i,x in enumerate(self.values):
            span=round(x['value']/max(1,total)*360*16);p.setPen(QPen(QColor(self.palette[i%len(self.palette)]),15));p.drawArc(rect,angle,-max(0,span-50));angle-=span
        p.setPen(QColor(color('text')));p.setFont(QFont('DejaVu Sans',27,QFont.Bold));p.drawText(rect,Qt.AlignCenter,str(total));p.setFont(QFont('DejaVu Sans',8));p.setPen(QColor(color('muted')));p.drawText(QRectF(rect.x(),rect.y()+92,rect.width(),20),Qt.AlignCenter,'EVENTS')

class ChainWidget(QWidget):
    def __init__(self,nodes):super().__init__();self.nodes=nodes;self.setMinimumHeight(190)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),QColor(color('code')));p.setPen(QPen(QColor(color('border')),1))
        for x in range(8,self.width(),18):
            for y in range(8,self.height(),18):p.drawPoint(x,y)
        n=len(self.nodes);gap=36;width=(self.width()-24-gap*max(0,n-1))/max(n,1)
        for i,node in enumerate(self.nodes):
            x=12+i*(width+gap);rect=QRectF(x,24,width,140);tint=QColor(color('orange' if i==n-1 else 'accent' if i==0 else 'green'))
            p.setBrush(QColor(color('panel')));p.setPen(QPen(QColor(color('border')),1));p.drawRoundedRect(rect,7,7)
            p.setPen(QPen(tint,3));p.drawLine(QPointF(x+8,25),QPointF(x+width-8,25))
            p.setPen(tint);p.setFont(QFont('Microsoft YaHei UI',9,QFont.Bold));p.drawText(rect.adjusted(12,12,-8,-88),Qt.AlignLeft,node['role'])
            p.setPen(QColor(color('text')));p.setFont(QFont('Consolas',10,QFont.Bold));p.drawText(rect.adjusted(12,44,-8,-27),Qt.TextWordWrap,node['name'])
            p.setPen(QColor(color('muted')));p.setFont(QFont('Consolas',8));p.drawText(rect.adjusted(12,108,-7,0),Qt.AlignLeft,node['location'])
            if i<n-1:
                path=QPainterPath(QPointF(x+width,94));path.cubicTo(x+width+gap/2,94,x+width+gap/2,94,x+width+gap,94)
                p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor(color('accent')),2));p.drawPath(path)
            for px in (x,x+width):p.setBrush(tint);p.setPen(QPen(QColor(color('panel')),2));p.drawEllipse(QPointF(px,94),4,4)
