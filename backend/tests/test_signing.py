import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.xdr.signing import signed_request, decode_auth_code
from app.core import settings

@pytest.mark.parametrize('method,body',[('GET',None),('POST',{'page':1,'pageSize':200}),('POST',{'name':'中文测试 空格','ids':['b','a']}),('POST',{})])
def test_matches_provided_sdk(method,body):
    path=Path(__file__).resolve().parents[2]/'提供材料/aksk_py3.py'
    if not path.exists(): pytest.skip('User SDK reference is not distributed')
    spec=importlib.util.spec_from_file_location('reference_sdk',path)
    sdk=importlib.util.module_from_spec(spec);spec.loader.exec_module(sdk)
    date='20260920T120000Z';url='https://172.20.0.140/api/xdr/v1/incidents/list'
    cfg={'auth_type':'aksk','access_key':'test-access','secret_key':'test-secret'}
    headers,payload=signed_request(method,url,body,cfg,date)
    req=SimpleNamespace(url=url,method=method,params={},json=body,data=None,headers={'content-type':'application/json','sign-date':date})
    sdk.Signature(ak=cfg['access_key'],sk=cfg['secret_key']).signature(req)
    assert headers==req.headers
    assert payload==(json.dumps(body).encode() if method=='POST' and body else b'')


def test_authorization_code_and_missing_keys():
    from Crypto.Cipher import AES
    import hashlib
    fields=[str(i) for i in range(14)]
    key=hashlib.sha256('+'.join(fields[i] for i in (0,1,2,3,4,5,6,11)).encode()).digest()
    ak='a'*16;sk='b'*32
    for index,text in [(9,ak),(10,sk)]:fields[index]=AES.new(key,AES.MODE_CBC,iv=bytes(16)).encrypt(text.encode()).hex()
    code='|'.join(fields).encode().hex()
    assert decode_auth_code(code)==(ak,sk)
    cfg={'auth_type':'auth_code','auth_code':code}
    assert 'Access='+ak in signed_request('GET','https://example.test/path',None,cfg)[0]['Authorization']
    with pytest.raises(ValueError):decode_auth_code('invalid')
    with pytest.raises(ValueError):signed_request('GET','https://example.test',None,{'auth_type':'aksk'})


def test_signing_secrets_not_returned(client):
    saved=settings.save({'xdr':{'auth_type':'aksk','access_key':'test-access','secret_key':'test-secret','auth_code':'test-code'}})
    for key in ('access_key','secret_key','auth_code'):
        assert key not in saved['xdr']
        assert saved['xdr'][key+'_configured']
    settings.save({'xdr':{'secret_key':''}})
    assert settings.load()['xdr']['secret_key']=='test-secret'


def test_adapter_sends_signed_body(monkeypatch):
    import asyncio
    import httpx
    from app.core.config import DEFAULTS
    from app.xdr.adapter import XDRAdapter
    cfg={**DEFAULTS['xdr'],'auth_type':'aksk','access_key':'test-access','secret_key':'test-secret'}
    body={'page':1,'name':'中文'}
    def handler(req):
        expected,payload=signed_request('POST',str(req.url),body,cfg,req.headers['sign-date'])
        assert req.content==payload
        assert req.headers['Authorization']==expected['Authorization']
        return httpx.Response(200,json={'code':'Success','data':{'item':[]}})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    assert asyncio.run(XDRAdapter(cfg).request('events',body))=={'item':[]}


def test_signed_connection_test_rejects_missing_credentials(client):
    from app.database import store
    from app.core.config import DEFAULTS
    store.put('settings',{'id':'xdr','value':{**DEFAULTS['xdr'],'auth_type':'aksk'}})
    response=client.post('/api/settings/test/xdr')
    assert response.status_code==400
    assert 'Access Key / Secret Key' in response.text
