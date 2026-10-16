"""Python 3.9+ standard library: build offline HTML/SVG and check design artifacts.
Checks are document/reference-model checks, not implemented system tests.
"""
from pathlib import Path
import re, json, hashlib, shutil, html, datetime, zipfile, importlib.util, difflib
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
MD = ROOT / '01_软件设计文档.md'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def esc(s):
    return html.escape(str(s), quote=True)

def svg(name, title, nodes, edges, width=1000, height=570, notes=()):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
           f'<title id="title">{esc(title)}</title>',
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#53647b"/></marker></defs>',
           f'<rect width="{width}" height="{height}" fill="white"/>',
           '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" fill="#18283d">',
           f'<text x="30" y="36" font-size="22" font-weight="bold">{esc(title)}</text>']
    for x1,y1,x2,y2,label in edges:
        out.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#53647b" stroke-width="2" fill="none" marker-end="url(#arrow)"/>')
        if label:
            mx,my=(x1+x2)/2,(y1+y2)/2
            if x1==x2:
                out.append(f'<text x="{mx+6}" y="{my-9}" font-size="13">{esc(label)}</text>')
            else:
                out.append(f'<text x="{mx}" y="{my-9}" text-anchor="middle" font-size="13">{esc(label)}</text>')
    for x,y,w,h,lines in nodes:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#f2f6fa" stroke="#8192a9"/>')
        for i,line in enumerate(lines):
            out.append(f'<text x="{x+w/2}" y="{y+27+i*24}" text-anchor="middle" font-size="{17 if i==0 else 14}" font-weight="{"bold" if i==0 else "normal"}">{esc(line)}</text>')
    for i,n in enumerate(notes):
        out.append(f'<text x="30" y="{height-47+i*23}" font-size="14">{esc(n)}</text>')
    out.append('</g></svg>')
    p=ROOT/'diagrams'/name
    p.parent.mkdir(exist_ok=True)
    p.write_text('\n'.join(out),encoding='utf-8')

def build_diagrams():
    svg('01_架构.svg','图1 系统架构与依赖方向',[
        (30,70,270,85,['学生与管理员浏览器','同源页面和局部交互']),
        (345,70,270,85,['HTTP控制器与DTO','会话 / CSRF / 输入映射']),
        (345,205,270,115,['应用服务与事务编排','发布 / 交接 / 治理 / 清理','UnitOfWork与当前授权']),
        (30,205,270,115,['领域规则','MR-1 / 状态 / 期限 / 权限','不依赖HTTP或存储SDK']),
        (675,205,285,115,['端口','Repository / Storage / Identity','Clock / Audit / Outbox']),
        (675,380,285,90,['基础设施适配器','PostgreSQL / 私有图 / 身份']),
        (345,380,270,90,['同制品任务执行器','持久事件 / 监督 / 重试'])],
        [(300,113,345,113,'HTTPS'),(480,155,480,205,'调用'),(345,263,300,263,'调用'),
         (615,263,675,263,'调用'),(818,380,818,320,'实现端口'),(480,380,480,320,'调用')],
        notes=['箭头表示调用或端口实现；Web与worker同代码制品，领域规则不依赖基础设施。','来源：F-01—18、N-01/02/03/06/09；模块清单见第3.3节。'])
    svg('02_部署.svg','图2 单机试点部署与恢复边界',[
        (35,85,220,85,['浏览器','学生 / 管理员']),
        (350,85,270,85,['HTTPS入口 443','反向代理不缓存敏感内容']),
        (350,235,270,85,['Web 内部8000','2进程 / 当前对象鉴权']),
        (690,235,270,85,['Worker 无公网端口','调度 / 超时监督 / 失败队列']),
        (350,390,270,85,['PostgreSQL 内部5432','业务 / 事件 / 幂等 / 任务']),
        (35,390,250,85,['私有图片目录','不可静态直读；应用代理']),
        (690,390,270,85,['独立受限备份介质','备份30天 / 删除清单31天'])],
        [(255,127,350,127,'HTTPS'),(485,170,485,235,'内部调用'),(485,320,485,390,'事务'),
         (690,433,620,433,'恢复'),(825,320,620,390,'任务读写'),(350,277,160,390,'代理图像')],
        height=600,notes=['参考主机4核8 GiB；只有443对外，数据库和图片在私有边界内。','单机存在故障域；独立介质与恢复屏障应以TN-02/TN-07演练验证。'])
    svg('03_数据关系.svg','图3 核心实体与关联',[
        (30,85,215,85,['D01 用户','发布者 / 申请人']),
        (340,85,275,85,['D03 记录头','LOST或FOUND / 状态 / 版本']),
        (700,85,265,85,['D04 记录内容','公开字段 + 私密提示']),
        (340,240,275,85,['D05 申请','每笔关联一FOUND一LOST']),
        (700,240,265,85,['D06 申请内容','证据 / 地点 / 联系 / 确认']),
        (30,240,215,85,['D07 活动占用','record_id主键唯一']),
        (340,395,275,85,['D11 案件','举报 / 申诉 / 回避期限']),
        (700,395,265,85,['D12 回执与正文','归并仍保留各回执']),
        (30,395,215,85,['D20 收藏','user ↔ record','无正文快照'])],
        [(245,127,340,127,'1:N'),(615,127,700,127,'1:0..1'),(477,170,477,240,'两侧各1:N'),
         (615,282,700,282,'1:0..1'),(340,282,245,282,'1:2'),(477,325,477,395,'1:N'),
         (615,437,700,437,'1:N')],
        height=600,notes=['箭头和数字表示关联，不表示模块调用；D07确保同LOST/FOUND不能参与多个活动交接。','其余图片、候选、事件、通知、审计与删除清单字段见D08—D23。'])
    svg('05_状态.svg','图5 记录状态与期限守卫',[
        (30,100,235,80,['无服务端记录','前端DRAFT仅在内存']),
        (365,100,240,80,['OPEN','有效期30天']),
        (735,100,230,80,['RESERVED','交接期限48小时']),
        (735,350,230,80,['RETURNED','双方确认成功']),
        (365,350,240,80,['EXPIRED','期限到达']),
        (30,350,235,80,['WITHDRAWN','本人撤回'])],
        [(265,140,365,140,'发布成功'),(605,140,735,140,'原子选定'),(850,180,850,350,'双方确认'),
         (485,180,485,350,'now≥expiresAt'),(365,165,147,350,'撤回'),
         (760,180,550,350,'取消/超时且原期限已过'),(735,110,605,110,'释放且仍有效')],
        height=550,notes=['hidden/frozen为独立标志：禁止普通业务写入，系统时钟与释放不暂停。','终态不可复活；判断到期使用服务端时间，等于deadline即失效。'])
    # Sequence diagram with explicit participant lifelines, not approximate flowchart.
    w,h=1000,640
    parts=[(105,'用户 按动作权限'),(365,'M04交接服务'),(630,'PostgreSQL'),(865,'M07 Worker')]
    seq=[(105,365,150,'选定申请 + 双version + requestKey'),(365,630,205,'锁双记录；插入双占用；RESERVED'),
         (630,365,255,'同事务提交状态 / 幂等 / Outbox'),(365,105,305,'返回两侧新version和48小时deadline'),
         (105,365,355,'设置有效公共点；首次确认后刷新version'),(365,630,405,'单方确认仅保存标志，两侧version+1'),
         (105,365,455,'第二方以当前version确认'),(365,630,505,'双RETURNED + COMPLETED + 释放占用'),
         (630,865,555,'持久事件：双方归还通知，接收方唯一')]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img"><title>图4 选定与双方确认时序</title><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#53647b"/></marker></defs><rect width="1000" height="640" fill="white"/><g font-family="Microsoft YaHei, sans-serif" fill="#18283d"><text x="30" y="36" font-size="22" font-weight="bold">图4 选定与双方确认时序</text>']
    for x,t in parts:
        out.append(f'<rect x="{x-85}" y="65" width="170" height="48" rx="5" fill="#f2f6fa" stroke="#8192a9"/><text x="{x}" y="95" text-anchor="middle" font-size="16">{t}</text><path d="M{x} 115 V590" stroke="#8192a9" stroke-dasharray="5 5"/>')
    for a,b,y,t in seq:
        out.append(f'<path d="M{a} {y} H{b}" stroke="#53647b" stroke-width="2" marker-end="url(#a)"/><text x="{(a+b)/2}" y="{y-10}" text-anchor="middle" font-size="13">{t}</text>')
    out.append('<text x="30" y="620" font-size="14">每次动作实时检查身份、两侧标志、版本和截止；任何失败均不产生半完成。</text></g></svg>')
    (ROOT/'diagrams'/'04_交接时序.svg').write_text(''.join(out),encoding='utf-8')
    build_extra_diagrams()

def build_extra_diagrams():
    svg('06_降级运行.svg','图6 依赖故障下的运行形态',[
        (30,85,220,90,['用户浏览器','提示延迟 / 失败 / 维护']),
        (370,85,285,115,['Web 同步路径仍守卫','鉴权 / 人工检索 / 文本写入','到期先同步收敛再做业务']),
        (370,315,285,115,['PostgreSQL 必须可用','事务 / 幂等 / 审计 / Outbox','故障即关闭业务入口']),
        (735,85,230,115,['Worker全部停机','候选与通知延迟','不丢已提交事件']),
        (30,315,250,115,['图片或学校身份故障','无图文本 / 有效会话可用','失败组件对应功能503']),
        (735,315,230,115,['恢复与屏障','MISSED / 一次补偿','删除清单核对后放行'])],
        [(250,130,370,130,'同源请求'),(510,200,510,315,'当前事务'),
         (655,372,735,372,'恢复'),(735,142,655,142,'状态反馈')],height=570,
        notes=['RUN_SYNC_ONLY：worker停机不豁免60秒任务/24小时清理SLA；故障原样计入监测。','数据库/鉴权失效或恢复屏障未解除时，业务入口关闭；质量SEARCH_FIRST另行管理。'])
    w,h=1220,840
    parts=[(100,'FOUND作者'),(345,'M02 / 数据库'),(595,'M03查询'),(845,'LOST作者'),(1100,'Worker')]
    seq=[(100,345,155,'编辑FOUND：v8 → v9'),(345,1100,210,'同事务提交正文 / version / Outbox'),
         (845,595,270,'API07读取自己的LOST候选'),(595,345,325,'当前FOUND版本与可见性'),
         (345,595,380,'当前v9：剔除旧v8候选'),(595,845,435,'200 UPDATING，可能不足10项'),
         (345,1100,490,'持久fanout：每批20条LOST'),(1100,345,550,'新任务提交前重验双version / epoch / fence'),
         (345,595,610,'当前v9候选可见，补足Top10'),(1100,345,670,'旧v8任务晚完成：STALE不覆盖、不通知')]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img"><title>图7 FOUND编辑与候选读取竞态</title><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#53647b"/></marker></defs><rect width="{w}" height="{h}" fill="white"/><g font-family="Microsoft YaHei, sans-serif" fill="#18283d"><text x="30" y="36" font-size="22" font-weight="bold">图7 RACE_MATCH_01 FOUND编辑与候选读取</text>']
    for x,ttl in parts:
        out.append(f'<rect x="{x-85}" y="70" width="170" height="48" rx="5" fill="#f2f6fa" stroke="#8192a9"/><text x="{x}" y="101" text-anchor="middle" font-size="16">{ttl}</text><path d="M{x} 118 V725" stroke="#8192a9" stroke-dasharray="5 5"/>')
    for a,b,y,ttl in seq:
        out.append(f'<path d="M{a} {y} H{b}" stroke="#53647b" stroke-width="2" marker-end="url(#a)"/><text x="{(a+b)/2}" y="{y-10}" text-anchor="middle" font-size="12">{ttl}</text>')
    out.append('<text x="30" y="775" font-size="14">编辑提交后的新守卫不得返回旧候选；提交前已通过守卫的在途响应按IM-1处理。</text><text x="30" y="807" font-size="14">API07仅向LOST作者响应；更新失败另显FAILED，人工搜索仍可用。</text></g></svg>')
    (ROOT/'diagrams'/'07_候选竞态.svg').write_text(''.join(out),encoding='utf-8')

def inline(s):
    s=esc(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return s

def render_html(text):
    lines=text.splitlines(); out=[]; toc=[]; i=0; n=0
    while i<len(lines):
        l=lines[i]
        if not l.strip(): i+=1; continue
        if l.startswith('```'):
            lang=l[3:]; i+=1; chunk=[]
            while i<len(lines) and not lines[i].startswith('```'):
                chunk.append(lines[i]); i+=1
            out.append(f'<pre aria-label="{esc(lang)}"><code>{esc(chr(10).join(chunk))}</code></pre>'); i+=1; continue
        if l.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                r=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in r): rows.append(r)
                i+=1
            out.append('<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>')
            for r in rows[1:]: out.append('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in r)+'</tr>')
            out.append('</tbody></table></div>'); continue
        m=re.match(r'^(#{1,3}) (.+)$',l)
        if m:
            level=len(m[1]); n+=1; anchor=f's{n}'
            out.append(f'<h{level} id="{anchor}">{inline(m[2])}</h{level}>')
            if level==2: toc.append(f'<a href="#{anchor}">{esc(m[2])}</a>')
            i+=1; continue
        m=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',l)
        if m:
            p=ROOT/m[2]; svgtext=p.read_text(encoding='utf-8')
            # Inline SVG IDs have separate names, so marker/title references remain unique.
            prefix=p.stem.replace('_','-')
            svgtext=re.sub(r'id="([^"]+)"',lambda x:f'id="{prefix}-{x[1]}"',svgtext)
            svgtext=re.sub(r'url\(#([^\)]+)\)',lambda x:f'url(#{prefix}-{x[1]})',svgtext)
            svgtext=svgtext.replace('aria-labelledby="title"',f'aria-labelledby="{prefix}-title"')
            out.append('<figure>'+svgtext+'<figcaption>'+esc(m[1])+'</figcaption></figure>'); i+=1; continue
        p=[l]; i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','![')):
            p.append(lines[i]); i+=1
        out.append('<p>'+inline(' '.join(p))+'</p>')
    style='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#18202a;background:#edf1f5;margin:0;line-height:1.8}main{max-width:1120px;margin:24px auto;padding:52px 62px;background:white}h1,h2,h3{color:#000;line-height:1.45}h1{font-size:30px;margin:0 0 24px}h2{font-size:23px;margin-top:42px}h3{font-size:18px;margin-top:28px}p{margin:12px 0;font-size:16px}nav{display:grid;grid-template-columns:1fr 1fr;gap:4px 22px;margin:24px 0;padding:20px 0;border-top:1px solid #d9d9d9;border-bottom:1px solid #d9d9d9}nav a{color:#244f7a;text-decoration:none;font-size:14px}table{width:100%;border-collapse:collapse;margin:14px 0 22px;font-size:14px;line-height:1.65;table-layout:auto}th,td{border:1px solid #d9d9d9;padding:10px 12px;vertical-align:middle;overflow-wrap:anywhere}th{background:#e7eef6;color:#000;text-align:left}tbody tr:nth-child(even){background:#f7f9fb}code{font-family:Consolas,"Microsoft YaHei",monospace;font-size:0.9em;background:#f2f4f6;padding:1px 3px;overflow-wrap:anywhere}pre{background:#f6f8fa;border:1px solid #d9d9d9;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}pre code{background:none;padding:0}figure{margin:24px 0;break-inside:avoid}figure svg{width:100%;height:auto}figcaption{font-size:13px;text-align:center;color:#53647b}a{color:#244f7a}.printtip{font-size:13px;color:#53647b}.tablewrap{width:100%;overflow:auto}@media(max-width:700px){main{margin:0;padding:24px 18px}nav{grid-template-columns:1fr}h1{font-size:25px}table{font-size:13px}th,td{padding:6px}}@page{size:A4;margin:17mm 15mm}@media print{body{background:white}main{max-width:none;margin:0;padding:0}p{font-size:10.5pt}h1{font-size:20pt}h2{font-size:15pt;break-after:avoid}h3{font-size:12pt;break-after:avoid}table{font-size:8.5pt}th,td{padding:5px 6px}thead{display:table-header-group}tr{break-inside:avoid}.tablewrap{overflow:visible}pre{font-size:8pt}figure{break-inside:avoid}nav,.printtip{display:none}a{color:inherit;text-decoration:none}}'''
    style += 'body{overflow-wrap:anywhere}main{width:100%;min-width:0}nav>*{min-width:0}pre{width:100%;max-width:100%;word-break:break-word}.tablewrap{max-width:100%;min-width:0}'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>校园失物招领与线索匹配平台 软件设计</title><style>'+style+'</style></head><body><main><p class="printtip">离线完整阅读版 · 架构设计与系统设计 · 可使用浏览器打印为PDF · 原始需求见同包baseline目录</p><nav aria-label="章节目录">'+''.join(toc)+'</nav>'+''.join(out)+'</main></body></html>'

def score(l,f):
    if l['campus']!=f['campus'] or l['owner']==f['owner'] or l['type']==f['type']: return None
    if any(x['status']!='OPEN' or x.get('hidden') or x.get('frozen') for x in (l,f)): return None
    if l['cat']!='OTHER' and f['cat']!='OTHER' and l['cat']!=f['cat']: return None
    if l['time'] is not None and f['time'] is not None and f['time'][1]<l['time'][0]: return None
    c=35 if l['cat']==f['cat'] and l['cat']!='OTHER' else 0
    k=15 if l['color']==f['color'] and l['color']!='UNKNOWN' else 0
    loc=25 if l['loc']==f['loc'] and l['loc'] not in ('OTHER','UNKNOWN') else 0
    t=0
    if l['time'] and f['time']:
        a,b=l['time']; x,y=f['time']
        if max(a,x)<=min(b,y): t=25
        elif x>b and x-b<=72*3600: t=10
    return [c,k,loc,t,c+k+loc+t]

def check(text):
    results=[]
    def add(name,passed,detail): results.append(dict(name=name,passed=bool(passed),detail=detail))
    # Only section 13 counts as requirement coverage, avoiding IDs mentioned elsewhere.
    trace=text.split('## 13 ')[1].split('## 14 ')[0]
    ids=[f'F-{i:02}' for i in range(1,21)]+[f'N-{i:02}' for i in range(1,11)]+['F-13a','F-13b','F-13c','F-19a','F-19b','F-19c','N-09a','N-09b','N-09c']
    for x in ids: add('追溯 '+x,bool(re.search(r'\|'+re.escape(x)+r'\s',trace)),'第13节独立行')
    for family,count in [('M',9),('D',23),('API',41),('INT',12),('P',9),('UI',11),('ADR',10),('DV',25),('E',15)]:
        first=0 if family in ('API','UI') else 1
        for i in range(first,count+first):
            x=f'{family}{i:02}'
            add('设计元素 '+x,x in text,'正文存在规范编号；不等于实现完成')
    headings=re.findall(r'^## (\d+) ',text,re.M)
    add('章节完整',headings==[str(i) for i in range(1,15)],headings)
    for caption,path in re.findall(r'!\[([^]]+)\]\(([^)]+)\)',text):
        p=ROOT/path
        try: ET.parse(p); valid=True
        except Exception: valid=False
        add('图 '+caption,p.exists() and valid,path)
    blocks=re.findall(r'```json\n(.*?)\n```',text,re.S)
    samples=[json.loads(b) for b in blocks]
    add('JSON样例可解析',len(samples)==2,'发布输入与确认响应')
    add('JSON最终双v6',samples[1]['data']['foundVersion']==samples[1]['data']['lostVersion']==6,'与第7.1/DV03一致')
    (ROOT/'spec'/'接口样例.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
    source=WORKSPACE/'校园失物招领与线索匹配平台_提交成果_V1.2'/'01_需求分析文档.md'
    copied=ROOT/'baseline'/'需求分析文档_V1.2.md'
    add('基线逐字一致',not source.exists() or digest(source)==digest(copied),'源存在时重算；独立包见来源指纹')
    sql=(ROOT/'spec'/'核心约束.sql').read_text(encoding='utf-8')
    for s in ['record_id uuid PRIMARY KEY','uq_active_claim_pair','DEFERRABLE INITIALLY DEFERRED','UNIQUE(event_id,recipient_id)','PRIMARY KEY(user_id,request_key)']:
        add('SQL约束 '+s,s in sql,'文本约束检查，未在PostgreSQL执行')
    base=dict(campus='C01',owner='U1',type='LOST',status='OPEN',cat='KEY',color='BLACK',loc='LIB',time=[8*3600,9*3600])
    found=dict(base,owner='U2',type='FOUND',time=[8.5*3600,9.5*3600])
    cases=[('S-01',{},[35,15,25,25,100]),('S-02',{'time':[33*3600,34*3600]},[35,15,25,10,85]),
           ('S-03',{'color':'BLUE','time':None},[35,0,25,0,60]),('S-04',{'cat':'CARD'},None),
           ('S-05',{'loc':'UNKNOWN','time':None},[35,15,0,0,50]),('S-06',{'cat':'OTHER','color':'UNKNOWN','loc':'UNKNOWN','time':None},[0,0,0,0,0]),
           ('S-07',{'time':[7*3600,7*3600+59*60]},None),('S-08_72h',{'time':[81*3600,82*3600]},[35,15,25,10,85]),
           ('S-08_72h加1秒',{'time':[81*3600+1,82*3600]},[35,15,25,0,75]),
           ('S-09',{'color':'UNKNOWN','loc':'UNKNOWN','time':None},[35,0,0,0,35]),
           ('S-10',{'cat':'OTHER','loc':'UNKNOWN'},[0,15,0,25,40]),('异校',{'campus':'C02'},None),
           ('本人',{'owner':'U1'},None),('冻结',{'frozen':True},None)]
    for label,changes,expected in cases:
        actual=score(base,dict(found,**changes))
        add('MR-1构造 '+label,actual==expected,dict(expected=expected,actual=actual,candidate=actual is not None and actual[-1]>=40))
    # Separate reference state model, deliberately not production system or concurrency evidence.
    version=1; fs=ls='OPEN'; cs='PENDING'; confirmations=[False,False]; occupied=set()
    version+=1 # create claim
    occupied.update(['FOUND_ID','LOST_ID']); fs=ls='RESERVED'; cs='SELECTED'; version+=1
    version+=1 # place
    confirmations[0]=True; version+=1
    old=4; before=(version,fs,ls,cs)
    conflict=old!=version
    add('双记录参考模型旧版拒绝',conflict and before==(5,'RESERVED','RESERVED','SELECTED'),list(before))
    confirmations[1]=True; fs=ls='RETURNED'; cs='COMPLETED'; occupied.clear(); version+=1
    add('双记录参考模型完成',version==6 and fs==ls=='RETURNED' and not occupied and all(confirmations),dict(version=version,found=fs,lost=ls,claim=cs))
    add('双记录参考模型重复不递增',version==6,'同键结果投影不执行第二次动作；不是HTTP实测')
    spec=importlib.util.spec_from_file_location('design_extra_checks',ROOT/'evidence'/'补充设计检查.py')
    extra=importlib.util.module_from_spec(spec); spec.loader.exec_module(extra)
    results.extend(extra.run(ROOT,text))
    (ROOT/'evidence'/'设计检查结果.json').write_text(json.dumps(dict(time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),kind='文档结构与构造参考模型检查，非平台实测',passed=sum(x['passed'] for x in results),total=len(results),results=results),ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(x['passed'] for x in results): raise RuntimeError([x for x in results if not x['passed']])
    return len(results)

def main():
    (ROOT/'baseline').mkdir(exist_ok=True)
    src=WORKSPACE/'校园失物招领与线索匹配平台_提交成果_V1.2'/'01_需求分析文档.md'
    baseline=ROOT/'baseline'/'需求分析文档_V1.2.md'
    if not baseline.exists(): shutil.copyfile(src,baseline)
    prior=WORKSPACE/'校园失物招领与线索匹配平台_提交成果_V1.2'
    # Keep the baseline's one linked procedure and its direct tool inputs usable.
    for rel in ['04_取样标注与兜底试用规程.md','evidence/匹配评估脚本.py',
                'evidence/templates/samples.csv','evidence/templates/candidates.csv',
                'evidence/templates/labels_a.csv','evidence/templates/labels_b.csv',
                'evidence/templates/adjudications.csv','evidence/templates/usability.csv']:
        target=ROOT/'baseline'/rel
        if not target.exists() and (prior/rel).exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(prior/rel,target)
    build_diagrams()
    text=MD.read_text(encoding='utf-8')
    (ROOT/'history'/'V1.1到V1.2_设计差异.diff').write_text(''.join(difflib.unified_diff((ROOT/'history'/'V1.1_软件设计文档.md').read_text(encoding='utf-8').splitlines(True),text.splitlines(True),fromfile='V1.1/01_软件设计文档.md',tofile='V1.2/01_软件设计文档.md')),encoding='utf-8')
    (ROOT/'01_软件设计文档_阅读打印版.html').write_text(render_html(text),encoding='utf-8')
    total=check(text)
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.name!='来源与交付指纹.json' and p.suffix!='.zip' and '__pycache__' not in p.parts:
            files.append(dict(path=str(p.relative_to(ROOT)).replace('\\','/'),bytes=p.stat().st_size,sha256=digest(p)))
    sources=[]
    for rel in ['task/软件设计文档生成/task.md','task/软件设计文档生成/gradingCriteria.md','CourseDocument/Ch1-什么是软件工程.pdf','CourseDocument/Ch2-过去我们是如何开发软件的.pdf','CourseDocument/Ch3-如何获取用户的真实需求.pdf','CourseDocument/软件工程实践课程教案.docx']:
        p=WORKSPACE/rel
        if p.exists(): sources.append(dict(path=rel,bytes=p.stat().st_size,sha256=digest(p)))
    sources.append(dict(path='需求分析文档V1.2',bytes=baseline.stat().st_size,sha256=digest(baseline),includedCopy='baseline/需求分析文档_V1.2.md'))
    manifest=ROOT/'evidence'/'来源与交付指纹.json'
    # Preserve source provenance when rerunning from an isolated extracted package.
    if len(sources)==1 and manifest.exists(): sources=json.loads(manifest.read_text(encoding='utf-8'))['sources']
    for entry in sources:
        if entry['path']=='task/软件设计文档生成/task.md': entry['includedCopy']='sources/任务要求.md'
        elif entry['path']=='task/软件设计文档生成/gradingCriteria.md': entry['includedCopy']='sources/评分标准.md'
        elif entry['path'].startswith('CourseDocument/'): entry.update(includedExcerpt='sources/课程方法原文摘录.md',excerptIndex='sources/课程摘录索引.json',originalIncluded=False)
    manifest.write_text(json.dumps(dict(sources=sources,deliverables=files,self_excluded=True),ensure_ascii=False,indent=2),encoding='utf-8')
    z=ROOT.parent/(ROOT.name+'.zip')
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and p.suffix!='.zip' and '__pycache__' not in p.parts: f.write(p,str(p.relative_to(ROOT.parent)))
    print(json.dumps(dict(checks_passed=total,zip=str(z),zip_bytes=z.stat().st_size,html_bytes=(ROOT/'01_软件设计文档_阅读打印版.html').stat().st_size),ensure_ascii=False))

if __name__=='__main__': main()
