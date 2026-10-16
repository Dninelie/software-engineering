"""V1.2 document/contract and synthetic specification checks; not DB execution."""
import re,json

def run(root,text):
    results=[]
    def add(name,passed,detail): results.append(dict(name=name,passed=bool(passed),detail=detail))
    contract=json.loads((root/'spec'/'原子接口契约.json').read_text(encoding='utf-8'))['endpoints']
    directory=text.split('### 6.3 ')[1].split('### 6.4 ')[0]
    pairs=[]; ids=[]
    for a in contract:
        aid=a['id']; ids.append(aid); pairs.append((a['method'],a['path']))
        line=next((l for l in directory.splitlines() if l.startswith('|'+aid+' ')),None)
        add('原子接口 '+aid, line is not None and len(re.findall(r'\b(GET|POST|PUT|DELETE)\s+/',line))==1,'一ID一方法一路径')
        add('接口限制 '+aid,line is not None and all(x in line for x in ['T=','C=','I=','F=']) and a['timeoutSeconds'] in (5,10) and a['concurrencyPerSession'] in (1,4),'逐行预算/并发/窗口/频控与JSON一致')
        add('接口契约同步 '+aid,line is not None and f"{a['method']} {a['path']}" in line and a['input'] in line and a['output'] in line and a['guard'] in line,'文档与机器契约字段同步')
    add('41接口连续唯一',ids==[f'API{i:02}' for i in range(41)] and len(set(pairs))==41,'0—40，无合并/重复端点')
    trace=text.split('### 13.1 ')[1].split('### 13.2 ')[0]
    rules=[f'B-{i:02}' for i in range(1,11)]+['MR-1','HP-1','NT-1']
    for rule in rules:
        row=next((l for l in trace.splitlines() if l.startswith('|'+rule+'|')),None)
        add('规则独立追溯 '+rule,row is not None and row.count('|')==6,'F/N、设计、数据接口、验证四向映射')
    modules=json.loads((root/'spec'/'模块内部结构.json').read_text(encoding='utf-8'))
    for m in modules:
        add('五层内部结构 '+m['id'], all(len(m[k])>0 for k in ['api','application','domain','ports','adapters']),m['package'])
    checklist=(root/'spec'/'约束表达式清单.md').read_text(encoding='utf-8')
    for i in range(1,24): add(f'D{i:02}约束执行层',bool(re.search(r'\|D'+f'{i:02}'+r' ',checklist)),'数据库表达式+服务守卫+验证')
    core=(root/'spec'/'核心约束.sql').read_text(encoding='utf-8')
    for name,pattern in [('申请局部','c.id = ANY(p_claims)'),('SELECTED局部','c.id=ANY(p_claims)'),('记录局部','r.id=ANY(p_records)'),('OLD保留','OLD.found_id,OLD.lost_id'),('身份变更索引补查','IF identity_changed THEN')]:
        add('局部约束 '+name,pattern in core,'文本检查；PostgreSQL未执行')
    extended=(root/'spec'/'扩展关键约束.sql').read_text(encoding='utf-8')
    for pattern in ['bytes BETWEEN 1 AND 2097152','width BETWEEN 1 AND 4096','height BETWEEN 1 AND 4096',
        'num_nonnulls(record_content_id,claim_content_id,case_content_id)=1','PRIMARY KEY(job_id,slot)',
        'UNIQUE(event_id,handler)','reviewer_deadline_at<=LEAST','uq_one_redrive','ct_rule_immutable','score BETWEEN 40 AND 100']:
        add('扩展约束 '+pattern,pattern in extended,'CHECK/UQ/TG表达式存在；未声称SQL实测')
    for i in range(1,4): add(f'Q{i:02}可量化',bool(re.search(r'\|Q'+f'{i:02}'+r' ',text)),'第9.1节目标/钩子/失败处理')
    for i in range(1,5): add(f'OP{i:02}检查钩子',bool(re.search(r'\|OP'+f'{i:02}'+r' ',text)),'技术预算有对应DV')
    for score,expected in [(0,False),(35,False),(39,False),(40,True),(100,True)]:
        computed=0<=score<=100; stored=computed and score>=40
        add('候选落库边界 '+str(score),stored==expected,dict(computedRange='0—100',stored=stored))
    # Reference two-stage convergence: S is deliberately not rolled back with B.
    def stages(system, business, between_deadline=False):
        state='RESERVED'; events=0
        if system in ('ROLLBACK','UNKNOWN'): return state,events,503
        if system=='EXPIRED': state='EXPIRED'; events=1
        if between_deadline: state='EXPIRED'; events=1; return state,events,409
        code={'OK':200,'VERSION':409,'VALIDATION':400,'UNAUTHENTICATED':401,'FORBIDDEN':403,'FAILURE':503}[business]
        if state=='EXPIRED' and business=='OK': code=409
        return state,events,code
    for business,code in [('OK',409),('VERSION',409),('VALIDATION',400),('UNAUTHENTICATED',401),('FORBIDDEN',403),('FAILURE',503)]:
        actual=stages('EXPIRED',business)
        add('S提交B分支 '+business,actual==('EXPIRED',1,code),list(actual))
    for mode in ['ROLLBACK','UNKNOWN']:
        add('S失败不进B '+mode,stages(mode,'OK')==('RESERVED',0,503),'参考模型：S失败没有业务提交')
    add('S/B间隙达截止',stages('NO_CHANGE','OK',True)==('EXPIRED',1,409),'实时复检拒绝')
    def readable(result_version,current_version,visible=True): return visible and result_version==current_version
    add('候选竞态提交前',readable(8,8),'guard前v8仍有效')
    add('候选竞态提交后',not readable(8,9),'guard后旧候选剔除')
    add('候选竞态当前结果',readable(9,9),'重算v9可见')
    add('候选竞态隐藏',not readable(9,9,False),'新版本也不能绕过隐藏')
    add('候选竞态旧任务拒提交',not readable(8,9),'旧任务无覆盖/通知')
    add('DV表连续',re.findall(r'^\|DV(\d\d)/',text,re.M)==[f'{i:02}' for i in range(1,26)],'DV01—DV25完整单一表格')
    spec=__import__('importlib.util',fromlist=['util']).spec_from_file_location('third_checks',root/'evidence'/'第三轮修订检查.py')
    module=__import__('importlib.util',fromlist=['util']).module_from_spec(spec); spec.loader.exec_module(module)
    results.extend(module.run(root,text))
    return results
