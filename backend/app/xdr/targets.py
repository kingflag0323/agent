"""Target identity comes from authenticated alert destination fields, not HTTP Host."""
import ipaddress

def destination_ips(alerts):
    found=set()
    def walk(value):
        if isinstance(value,dict):
            for key,v in value.items():
                if key in ('dstIp','dstIps','destIp'):
                    for item in v if isinstance(v,list) else [v]:
                        if isinstance(item,str):
                            try:found.add(str(ipaddress.ip_address(item)))
                            except ValueError:pass
                elif key not in ('requestHead','requestBody','responseHead','responseBody','rawProofData'):
                    if isinstance(v,(dict,list)):walk(v)
        elif isinstance(value,list):
            for item in value:walk(item)
    walk(alerts);return sorted(found)
