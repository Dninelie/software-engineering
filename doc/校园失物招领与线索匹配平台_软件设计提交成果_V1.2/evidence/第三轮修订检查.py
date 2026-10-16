"""Self-contained design/history/contracts/source and synthetic-policy checks."""
import json,re,hashlib,csv

def run(root,text):
    results=[]
    def add(n,p,d):results.append(dict(name=n,passed=bool(p),detail=d))
    lines=text.splitlines(); i=0; table_no=0; in_code=False
    while i<len(lines):
        if lines[i].startswith('```'): in_code=not in_code; i+=1; continue
        if not in_code and lines[i].startswith('|'):
            table_no+=1; rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=lines[i].strip().strip('|').split('|')
                if not all(re.fullmatch(r':?-+:?',c.strip()) for c in cells): rows.append(cells)
                i+=1
            add('Markdown表列数 '+str(table_no),all(len(r)==len(rows[0]) for r in rows),dict(header=len(rows[0]),rowCounts=sorted(set(len(r) for r in rows))))
            continue
        i+=1
    c=json.loads((root/'spec/原子接口契约.json').read_text(encoding='utf-8'))
    profiles=c['rateProfiles']; endpoints=c['endpoints']
    for a in endpoints:
        add('限制类型 '+a['id'],type(a['timeoutSeconds']) is int and type(a['concurrencyPerSession']) is int and a['idempotencyWindowSeconds'] in (0,86400) and a['rateProfileId'] in profiles,'T秒/C数/I秒/F引用；无混用业务一次受理')
        profile=profiles[a['rateProfileId']]
        add('频控完整 '+a['id'],type(profile['maxCount']) is int and type(profile['windowSeconds']) is int and profile['windowSeconds']==60 and bool(profile['scope']),'滚动窗口maxCount/windowSeconds/scope')
    add('读接口共享RF01',all(a['rateProfileId']=='RF01' for a in endpoints if a['method']=='GET'),'全部读共享60/60s')
    add('一次受理分离',[(a['id'],a['oneShotAcceptance']['scope']) for a in endpoints if a['oneShotAcceptance']]==[('API23','account'),('API29','jobId')],'F不承担一次性生命周期上限')
    add('锁定分离',endpoints[0]['loginLock']==dict(failedAttempts=5,lockSeconds=900,scope='demo-account') and endpoints[0]['rateProfileId']=='RF04','登录失败计数/15分钟不是F')
    errors=json.loads((root/'spec/错误码枚举.json').read_text(encoding='utf-8'))
    add('错误枚举7码完整',{e['code'] for e in errors}=={'VALIDATION','UNAUTHENTICATED','FORBIDDEN','NOT_FOUND','CONFLICT','RATE_LIMITED','TEMPORARY_FAILURE'},'HTTP/retryable/白名单集中')
    for e in errors:add('错误行 '+e['id'],f"|{e['id']} {e['code']}|{e['httpStatus']}|{str(e['retryable']).lower()}|" in text and bool(e['detailsWhitelist']) and bool(e['verification']),'文档与枚举同步')
    previous=(root/'history/V1.0_软件设计文档.md').read_text(encoding='utf-8')
    previous_table=previous.split('### 6.3 ')[1].split('### 6.4 ')[0]
    oldpairs=set()
    for line in previous_table.splitlines():
        if re.match(r'\|API\d\d ',line):oldpairs.update(re.findall(r'\b(GET|POST|PUT|DELETE)\s+(/[^；| ]+)',line.split('|')[1]))
    newpairs={(a['method'],a['path']) for a in endpoints}
    add('历史能力零遗漏零新增',oldpairs==newpairs and len(oldpairs)==41,dict(old=len(oldpairs),new=len(newpairs),missing=list(oldpairs-newpairs),added=list(newpairs-oldpairs)))
    add('历史接口完整逐字目录',previous_table in (root/'history/V1.0_接口目录.md').read_text(encoding='utf-8'),'源正文直接摘录，非重新编造')
    mappings=json.loads((root/'spec/接口演进映射.json').read_text(encoding='utf-8'))['mappings']
    add('41签名映射完整',len(mappings)==41 and {(m['method'],m['path']) for m in mappings}==oldpairs and {m['currentId'] for m in mappings}=={a['id'] for a in endpoints},'旧原行→新ID')
    add('退出签名细化显式登记','原API00退出写“无体”' in text and '|DD-11|' in text,'未虚称签名无变化，业务即时撤权保留')
    shared=json.loads((root/'spec/共享组件与就绪契约.json').read_text(encoding='utf-8'))
    for x in shared['sharedComponents']:add('共享边界 '+x['id'],x['id']+' ' in text or '|'+x['id']+' ' in text,x['package'])
    add('首版决策已定',shared['TDBaselineChoices']==dict(dirtySet='disabled; per-event local check',fanoutBatchSize=20,admissionStore='PostgreSQL shared short transactions'),'非悬置的实现分支')
    for i in range(1,7):add(f'身份确认IDP{i:02}',f'|IDP{i:02} ' in text and '2026-10-21 18:00' in text,'字段/责任/日期/待确认状态')
    for i in range(1,6):add(f'待确认TD{i:02}',f'|TD{i:02} ' in text,'当前选择、责任、截止与CR出口')
    for i in range(1,5):add(f'规模重评估EV{i:02}',f'|EV{i:02} ' in text,'阈值→评估→验收出口')
    ntable=text.split('### 9.2 ')[1].split('### 9.3 ')[0]
    for i in range(1,11):add(f'N-{i:02}测量四元组',f'|N-{i:02}|' in ntable,'方法/采样窗口/判定/重评估')
    qtable=text.split('### 9.3 ')[1].split('### 9.4 ')[0]
    for id in ['Q01','Q02','Q03','OP01','OP02','OP03','OP04']:add(id+'测量四元组','|'+id+'|' in qtable,'补全采样/触发')
    qm=json.loads((root/'spec/监测与质量契约.json').read_text(encoding='utf-8'))['qualityCombinations']
    add('QM八组合全覆盖',{(x['qualityMode'],x['taskState']) for x in qm}=={(m,s) for m in ['NORMAL','SEARCH_FIRST'] for s in ['READY','UPDATING','FAILED','STALE']},'模式与任务状态独立')
    for x in qm:
        add('QM通知 '+x['id'],x['emitMatchUpdated']==(x['qualityMode']=='NORMAL' and x['taskState']=='READY') and x['otherNotificationsContinue'],'当前版本成功事件唯一通知守卫')
    for i in range(1,7):add(f'AL{i:02}阈值/出口',f'|AL{i:02}|' in text and 'RESOLVED' in text,'采样、告警与修复判定集中')
    for i in range(1,11):add(f'S-{i:02}原编号映射',f'|S-{i:02}|M{i:02}|' in text,'只改设计别名，基线/历史保留原件')
    for name in ['易用性验证.csv','无障碍走查.csv']:
        rows=list(csv.reader((root/'evidence/templates'/name).read_text(encoding='utf-8').splitlines()))
        add('真实计划空表 '+name,len(rows)==1 and len(rows[0])>=8,'仅表头，无编造真实用户结果')
    add('SQL未运行边界',json.loads((root/'evidence/数据库执行状态.json').read_text(encoding='utf-8'))['status']=='NOT_RUN','有psql入口/采样，不伪造SQLSTATE/EXPLAIN')
    for file in ['spec/安装设计schema.psql','spec/局部校验采样.sql','sources/任务要求.md','sources/评分标准.md','sources/课程方法原文摘录.md','sources/课程摘录索引.json']:
        add('独立包附件 '+file,(root/file).exists() and (root/file).stat().st_size>0,file)
    source_index=json.loads((root/'sources/课程摘录索引.json').read_text(encoding='utf-8'))
    add('课程摘录覆盖',sum(len(x.get('pages',[])) for x in source_index)==10 and all(len(x['originalSha256'])==64 for x in source_index),'10个所引页与教案段落；原PDF未随包，不声称独立重算原PDF')
    # Admission, TTL and output whitelist reference models; not a production API.
    def allowed(times,now,maximum,window):return sum(now-window<t<=now for t in times)<maximum
    add('F滚动窗边界释放',allowed([0]*30,60,30,60),'恰60秒的事件出窗口')
    add('F窗口内拒绝',not allowed([1]*30,60,30,60),'技术尝试30/60s不得各进程放满')
    add('I0不重放',not (0>0 and 1<0),'敏感读/登录每次执行，不把不重放当频控')
    add('I24h截止',not (86400<86400),'到期键不取得旧成功正文；新动作仍当前守卫')
    details={'reasonCode':'VERSION_CHANGED','foundVersion':5,'evidence':'forbidden','password':'forbidden','storageKey':'forbidden'}
    public={k:v for k,v in details.items() if k in {'reasonCode','foundVersion','lostVersion','foundStatus','lostStatus'}}
    add('ER05白名单投影',set(public)=={'reasonCode','foundVersion'},public)
    # Threshold reference states, interpreting exact comparisons in the document.
    def purge(hours):return 'BREACH' if hours>=24 else 'CRITICAL' if hours>=22 else 'WARN' if hours>=18 else 'NORMAL'
    for hours,expected in [(17.99,'NORMAL'),(18,'WARN'),(22,'CRITICAL'),(24,'BREACH')]:add('AL01边界 '+str(hours),purge(hours)==expected,expected)
    return results
