"""Tree-sitter PHP syntax + bounded, intrafile source/assignment/sink rules.
Not a complete PHP taint engine; includes are only resolved for unique SQL wrappers.
"""
import hashlib
import re
from tree_sitter import Language,Parser
import tree_sitter_php

LIMITATIONS=['PHP 分析为 Tree-sitter 语法与有限文件内数据传播规则，不是完整污点证明。','PHP 动态包含、对象调用、框架路由、分支清洗与线上部署版本需进一步验证。']

def walk(node):
    yield node
    for child in node.named_children:yield from walk(child)

def analyze(sources,hashes):
    parser=Parser(Language(tree_sitter_php.language_php()));parsed={};errors=[];wrappers={}
    for file,source in sources.items():
        if not file.endswith('.php'):continue
        raw=source.encode();root=parser.parse(raw).root_node
        if root.has_error:errors.append({'file':file,'error':'PHP 语法解析不完整，未对该文件生成结论'});continue
        parsed[file]=(raw,root)
        for n in walk(root):
            if n.type!='function_definition':continue
            name=n.child_by_field_name('name');body=n.child_by_field_name('body')
            if not name or not body:continue
            for call in walk(body):
                fn=call.child_by_field_name('function') if call.type=='function_call_expression' else None
                if fn and fn.text==b'mysqli_query':
                    key=name.text.decode();wrappers.setdefault(key,[]).append({'file':file,'line':call.start_point.row+1,'end_line':call.end_point.row+1,'name':key+' → mysqli_query'})
    findings=[]
    for file,(raw,root) in parsed.items():
        source=sources[file];lines=source.splitlines();env={}
        import posixpath
        constants={};included={file}
        def literal(n):
            if n is None:return None
            if n.type=='variable_name':return constants.get(n.text.decode())
            if n.type in ('string','encapsed_string') and not any(x.type=='variable_name' for x in walk(n)):
                text=n.text.decode()
                return text[1:-1] if len(text)>1 and text[0] in ('\"', "'") and '\\' not in text else None
            if n.type=='binary_expression':
                left=n.child_by_field_name('left');right=n.child_by_field_name('right')
                if left and right and raw[left.end_byte:right.start_byte].strip()==b'.':
                    a=literal(left);b=literal(right)
                    if a is not None and b is not None:return a+b
            return None
        for n in walk(root):
            if n.type=='assignment_expression':
                left=n.child_by_field_name('left');value=literal(n.child_by_field_name('right'))
                if left and left.type=='variable_name' and value is not None:constants[left.text.decode()]=value
            if n.type in ('include_expression','include_once_expression','require_expression','require_once_expression') and n.named_children:
                path=literal(n.named_children[0])
                if path is not None:included.add(posixpath.normpath(posixpath.join(posixpath.dirname(file),path)))
        local_wrappers={k:[w for w in v if w['file'] in included] for k,v in wrappers.items()}

        def dependencies(node):
            result={'parameters':set(),'trace':[],'sanitized':set()}
            for n in walk(node):
                if n.type=='subscript_expression':
                    m=re.fullmatch(r"\$_(GET|POST|REQUEST)\s*\[\s*['\"]([^'\"]+)['\"]\s*\]",n.text.decode())
                    if m:
                        result['parameters'].add(m.group(2));result['trace'].append({'file':file,'line':n.start_point.row+1,'end_line':n.end_point.row+1,'name':'$_'+m.group(1)+'['+m.group(2)+']'})
                if n.type=='variable_name' and n.text.decode() in env:
                    known=env[n.text.decode()];result['parameters']|=known['parameters'];result['trace']+=known['trace'];result['sanitized']|=known['sanitized']
            for n in walk(node):
                if n.type=='function_call_expression':
                    fn=n.child_by_field_name('function');name=fn.text.decode().lower() if fn else ''
                    if name in ('intval','floatval','mysqli_real_escape_string','mysqli_escape_string'):result['sanitized'].add('sql')
                    if name in ('escapeshellarg','escapeshellcmd','intval'):result['sanitized'].add('command')
            return result
        def process(node):
            # Function-local environments do not leak into the file endpoint.
            nonlocal env
            if node.type in ('function_definition','method_declaration','anonymous_function'):
                saved=env;env={}
                for child in node.named_children:process(child)
                env=saved;return
            if node.type=='assignment_expression':
                left=node.child_by_field_name('left');right=node.child_by_field_name('right')
                if right:process(right)
                if left and right and left.type=='variable_name':
                    dep=dependencies(right)
                    if dep['parameters']:
                        dep['trace'].append({'file':file,'line':node.start_point.row+1,'end_line':node.end_point.row+1,'name':left.text.decode()+' 赋值'})
                        env[left.text.decode()]=dep
                    else:env.pop(left.text.decode(),None)
                return
            if node.type=='function_call_expression':
                fn=node.child_by_field_name('function');args=node.child_by_field_name('arguments')
                name=fn.text.decode().lower() if fn else '';arguments=args.named_children if args else []
                sql=name in ('mysqli_query','mysql_query') or len(local_wrappers.get(name,[]))==1
                command=name in ('shell_exec','system','passthru','exec')
                arg=arguments[1] if sql and name!='mysql_query' and len(arguments)>1 else arguments[0] if arguments else None
                if arg and (sql or command):
                    dep=dependencies(arg);kind='sql' if sql else 'command'
                    if dep['parameters'] and kind not in dep['sanitized']:
                        # SQL must have a SQL keyword in the local construction slice; bare input is also suspicious but excluded by this conservative rule.
                        trace=dep['trace']+[{'file':file,'line':node.start_point.row+1,'end_line':node.end_point.row+1,'name':name}]
                        if not sql or re.search(r'\b(select|insert|update|delete)\b',' '.join(lines[max(0,t['line']-1)] for t in trace if t['file']==file),re.I):
                            if sql and name in local_wrappers:trace+=local_wrappers[name]
                            unique=[]
                            for t in trace:
                                if t not in unique:unique.append(t)
                            line=node.start_point.row+1;rule='PHP-SQL-001' if sql else 'PHP-CMD-001';start=max(1,line-4)
                            findings.append({'id':'finding-'+hashlib.sha256(f'{hashes[file]}:{line}:{rule}'.encode()).hexdigest()[:12],'rule':rule,'type':'SQL Injection' if sql else 'Command Injection','cwe':'CWE-89' if sql else 'CWE-78','severity':'high','confidence':'medium','file':file,'line':line,'function':name,'description':'HTTP 输入经文件内赋值到达危险调用；需复核清洗与运行分支','code':'\n'.join(lines[start-1:line+3]),'code_start':start,'fix':'使用 mysqli_prepare / bind_param 参数化查询，禁止把输入拼接进 SQL。' if sql else '使用严格 IP 允许列表校验，避免 shell 拼接及任意命令执行。','patch':'','source':'Tree-sitter PHP rules','kind':'Static Finding','file_sha256':hashes[file],'reference':'','parameters':sorted(dep['parameters']),'trace':unique,'language':'php'})
            for child in node.named_children:process(child)
        process(root)
    return {'findings':findings,'errors':errors,'php_files':len(parsed),'limitations':LIMITATIONS}
