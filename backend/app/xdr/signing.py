"""Sangfor AK/SK wire protocol, implemented from user-supplied SDK contract.

No vendor SDK execution or secret logging. JSON is serialized once, then signed
and transmitted identically. Dates are UTC as required by the trailing Z.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit, quote, urlencode


def decode_auth_code(code):
    try:
        from Crypto.Cipher import AES
        fields = bytes.fromhex(code.strip()).decode('utf-8').split('|')
        if len(fields) != 14:
            raise ValueError()
        key = hashlib.sha256('+'.join(fields[i] for i in (0,1,2,3,4,5,6,11)).encode()).digest()
        def decrypt(value):
            raw = AES.new(key, AES.MODE_CBC, iv=bytes(16)).decrypt(bytes.fromhex(value))
            # Match the SDK: decrypted bytes are keys, not implicitly unpadded.
            return raw.decode('utf-8')
        return decrypt(fields[9]), decrypt(fields[10])
    except (ValueError, UnicodeError, IndexError):
        raise ValueError('授权码格式无效，请使用平台导出的完整授权码') from None


def signed_request(method, url, body, config, sign_date=None):
    ak, sk = config.get('access_key',''), config.get('secret_key','')
    if config.get('auth_type') == 'auth_code':
        if not config.get('auth_code'): raise ValueError('尚未配置 XDR 授权码')
        ak, sk = decode_auth_code(config['auth_code'])
    if not ak or not sk: raise ValueError('尚未配置 XDR Access Key / Secret Key')
    if any(c in ak for c in '\r\n'): raise ValueError('Access Key 包含非法换行')
    parsed = urlsplit(url)
    payload = json.dumps(body, ensure_ascii=True) if method == 'POST' and body else ''
    date = sign_date or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    headers = {'content-type':'application/json','sdk-host':parsed.netloc,
               'sdk-content-type':'application/json','sign-date':date}
    names = ';'.join(sorted(headers))
    canonical_headers = ''.join(f'{k}:{headers[k]}\n' for k in sorted(headers))
    path = parsed.path if parsed.path.endswith('/') else parsed.path+'/'
    # The supplied SDK sorts signed byte values, then removes ASCII spaces.
    # ensure_ascii JSON keeps request bytes ASCII (including Chinese fields).
    digest = hashlib.sha256(bytes(sorted(b for b in payload.encode() if b != 32))).hexdigest().upper()
    canonical = '\n'.join((method, quote(path,safe='/'), '', canonical_headers+names, digest))
    hashed = hashlib.sha256(canonical.encode()).hexdigest().upper()
    signature = hmac.new(sk.encode(), f'HMAC-SHA256\n{date}\n{hashed}'.encode(),hashlib.sha256).hexdigest().upper()
    headers['Authorization'] = f'algorithm=HMAC-SHA256, Access={ak}, SignedHeaders={names}, Signature={signature}'
    return headers, payload.encode()
