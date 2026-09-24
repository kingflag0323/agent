import ast
from pathlib import PurePosixPath

def module_name(file): return str(PurePosixPath(file).with_suffix('')).replace('/','.')

def index_sources(sources):
    functions=[];routes=[];errors=[];imports={}
    for file,code in sources.items():
        if not file.endswith('.py'): continue
        try: tree=ast.parse(code)
        except (SyntaxError,ValueError) as e: errors.append({'file':file,'error':str(e)});continue
        aliases={};module=module_name(file)
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                prefix=node.module or ''
                if node.level:
                    parts=module.split('.')[:-node.level];prefix='.'.join(parts+[prefix]) if prefix else '.'.join(parts)
                for a in node.names: aliases[a.asname or a.name]=(prefix+'.'+a.name).strip('.')
            elif isinstance(node,ast.Import):
                for a in node.names: aliases[a.asname or a.name]=a.name
        imports[file]=aliases
        for node in tree.body:
            nodes=[(node,None)] if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) else [(n,node.name) for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))] if isinstance(node,ast.ClassDef) else []
            for fn,cls in nodes:
                name=(cls+'.' if cls else '')+fn.name
                calls=[]
                for n in ast.walk(fn):
                    if isinstance(n,ast.Call):
                        try: raw=ast.unparse(n.func)
                        except Exception: continue
                        first,*rest=raw.split('.')
                        calls.append({'name':raw,'target':'.'.join([aliases.get(first,first)]+rest),'line':n.lineno})
                f={'id':module+'.'+name,'name':name,'file':file,'line':fn.lineno,'end_line':fn.end_lineno,'parameters':[a.arg for a in fn.args.args],'calls':calls}
                functions.append(f)
                for d in fn.decorator_list:
                    if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr in ('get','post','put','patch','delete','route') and d.args and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str):
                        methods=['GET']
                        if d.func.attr!='route': methods=[d.func.attr.upper()]
                        else:
                            for kw in d.keywords:
                                if kw.arg=='methods' and isinstance(kw.value,(ast.List,ast.Tuple)): methods=[x.value for x in kw.value.elts if isinstance(x,ast.Constant)]
                        routes.append({'path':d.args[0].value,'methods':methods,'function_id':f['id'],'file':file,'line':d.lineno,'parameters':f['parameters']})
    ids={f['id'] for f in functions}
    for f in functions:
        for c in f['calls']:
            candidates=[c['target'],module_name(f['file'])+'.'+c['name']]
            c['resolved']=next((x for x in candidates if x in ids),None)
    return {'functions':functions,'routes':routes,'errors':errors}

def call_path(index,start,file,line):
    by_id={f['id']:f for f in index['functions']};queue=[(start,[])];seen=set()
    while queue:
        id,path=queue.pop(0)
        if id in seen or len(path)>10: continue
        seen.add(id);fn=by_id.get(id)
        if not fn: continue
        chain=path+[fn]
        if fn['file']==file and fn['line']<=line<=fn['end_line']: return chain
        for call in fn['calls']:
            if call['resolved']: queue.append((call['resolved'],chain))
    return []
