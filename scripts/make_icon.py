from pathlib import Path
import struct
from PySide6.QtCore import Qt,QPointF,QByteArray,QBuffer,QIODevice
from PySide6.QtGui import QImage,QPainter,QColor,QPen,QPolygonF
image=QImage(256,256,QImage.Format_ARGB32);image.fill(QColor('#111724'));p=QPainter(image);p.setRenderHint(QPainter.Antialiasing)
p.setPen(QPen(QColor('#af92ff'),11));p.setBrush(QColor('#262039'));p.drawPolygon(QPolygonF([QPointF(128,32),QPointF(224,128),QPointF(128,224),QPointF(32,128)]));p.setPen(Qt.NoPen);p.setBrush(QColor('#b7a0ff'));p.drawPolygon(QPolygonF([QPointF(128,72),QPointF(184,128),QPointF(128,184),QPointF(72,128)]));p.setBrush(QColor('#67d8bb'));p.drawEllipse(QPointF(128,128),16,16);p.end()
b=QByteArray();buffer=QBuffer(b);buffer.open(QIODevice.WriteOnly);image.save(buffer,'PNG');png=bytes(b)
Path('desktop/sentinel.ico').write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(png),22)+png)
