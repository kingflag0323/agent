import json
from PySide6.QtCore import QObject, QUrl, QTimer, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class Client(QObject):
    failure = Signal(str)
    def __init__(self,base='http://127.0.0.1:8000',parent=None):
        super().__init__(parent);self.base=base.rstrip('/');self.network=QNetworkAccessManager(self)
    def request(self,path,callback,method='GET',body=None,on_error=None):
        req=QNetworkRequest(QUrl(self.base+'/api'+path))
        req.setRawHeader(b'X-Sentinel-Client',b'console')
        req.setHeader(QNetworkRequest.ContentTypeHeader,'application/json')
        req.setTransferTimeout(150000)
        data=json.dumps(body,ensure_ascii=False).encode() if body is not None else b''
        reply=self.network.sendCustomRequest(req,method.encode(),data)
        def finish():
            raw=bytes(reply.readAll());status=reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            try:
                payload=json.loads(raw) if raw else {}
                if reply.error()!=QNetworkReply.NoError or not status or status>=400:
                    detail=payload.get('detail',reply.errorString())
                    message=detail if isinstance(detail,str) else json.dumps(detail,ensure_ascii=False)
                    if on_error:on_error(message)
                    else:self.failure.emit(message)
                else:callback(payload)
            except (ValueError,TypeError):
                message='服务返回格式异常，请检查 Backend 日志'
                if on_error:on_error(message)
                else:self.failure.emit(message)
            finally:reply.deleteLater()
        reply.finished.connect(finish)
        return reply
    def upload(self,path,name,filename,callback,on_error=None):
        from PySide6.QtNetwork import QHttpMultiPart,QHttpPart
        from PySide6.QtCore import QFile,QIODevice
        req=QNetworkRequest(QUrl(self.base+'/api'+path));req.setRawHeader(b'X-Sentinel-Client',b'console');req.setTransferTimeout(150000)
        multipart=QHttpMultiPart(QHttpMultiPart.FormDataType)
        text=QHttpPart();text.setHeader(QNetworkRequest.ContentDispositionHeader,'form-data; name="name"');text.setBody(name.encode());multipart.append(text)
        part=QHttpPart();part.setHeader(QNetworkRequest.ContentDispositionHeader,'form-data; name="file"; filename="project.zip"');part.setHeader(QNetworkRequest.ContentTypeHeader,'application/zip')
        file=QFile(filename,multipart)
        if not file.open(QIODevice.ReadOnly):
            self.failure.emit('无法读取 ZIP');multipart.deleteLater();return
        part.setBodyDevice(file);multipart.append(part)
        reply=self.network.post(req,multipart);multipart.setParent(reply)
        def done():
            try:
                data=json.loads(bytes(reply.readAll()))
                if reply.error()!=QNetworkReply.NoError:
                    message=str(data.get('detail',reply.errorString()))
                    if on_error:on_error(message)
                    else:self.failure.emit(message)
                else:callback(data)
            except ValueError:self.failure.emit('ZIP 导入失败')
            reply.deleteLater()
        reply.finished.connect(done)
    def download(self,path,callback):
        req=QNetworkRequest(QUrl(self.base+'/api'+path));reply=self.network.get(req)
        def done():
            if reply.error()==QNetworkReply.NoError:callback(bytes(reply.readAll()))
            else:self.failure.emit('报告导出失败：'+reply.errorString())
            reply.deleteLater()
        reply.finished.connect(done)
