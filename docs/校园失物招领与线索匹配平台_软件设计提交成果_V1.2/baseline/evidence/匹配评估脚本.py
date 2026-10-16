"""QP-1 CSV验证与指标复算。标准库；空模板/错误返回2；不证明实际采样或平台实现。"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from uuid import UUID

CATEGORIES={'CARD','KEY','ELECTRONIC','BOOK','CLOTHING','OTHER'}
HEADERS={
    'samples.csv':['sampleId','queryId','targetId','pairToken','category','labelA','labelB','finalLabel','finalTargetId','adjudicatorId','split','snapshotRef','sourceRef','evidenceRef','consentRef'],
    'labels_a.csv':['sampleId','annotatorId','decision','targetId','reasonCode','evidenceRef','lockedAt'],
    'labels_b.csv':['sampleId','annotatorId','decision','targetId','reasonCode','evidenceRef','lockedAt'],
    'adjudications.csv':['sampleId','adjudicatorId','decision','finalTargetId','reason','evidenceRefs','decidedAt','labelsAVersion','labelsBVersion'],
    'candidates.csv':['sampleId','rank','candidateId','score','partC','partK','partL','partT','ruleVersion'],
    'usability.csv':['participantId','taskId','deviceWidth','browserVersion','startedAt','endedAt','durationSeconds','correct','assistance','systemKind','failureCode'],
}

def load(directory,name):
    p=directory/name
    with p.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f)
        if r.fieldnames!=HEADERS[name]: raise ValueError(name+'表头与QP-1不一致')
        rows=list(r)
        if any(None in x or any(v is None for v in x.values()) for x in rows): raise ValueError(name+'列数不一致')
    return rows

def unique(rows,key,name):
    keys=[x[key] for x in rows]
    if any(not k for k in keys) or len(set(keys))!=len(keys): raise ValueError(name+'缺ID或存在重复'+key)
    return dict(zip(keys,rows))

def uuid(s):
    try: UUID(s)
    except (ValueError,AttributeError): raise ValueError('无效UUID: '+s)

def timestamp(s):
    t=datetime.fromisoformat(s)
    if t.tzinfo is None: raise ValueError('标注时间必须带时区')
    return t

def evaluate(directory,kind):
    samples=load(directory,'samples.csv')
    if len(samples)!=100: raise ValueError('固定验收分母必须100组；当前'+str(len(samples)))
    pool=unique(samples,'sampleId','samples')
    unique(samples,'queryId','samples'); unique(samples,'targetId','samples'); unique(samples,'pairToken','samples')
    la=unique(load(directory,'labels_a.csv'),'sampleId','labels_a')
    lb=unique(load(directory,'labels_b.csv'),'sampleId','labels_b')
    adj=unique(load(directory,'adjudications.csv'),'sampleId','adjudications')
    if set(la)!=set(pool) or set(lb)!=set(pool) or not set(adj)<=set(pool): raise ValueError('标注或裁决sampleId与样本集不一致')
    versions={k:hashlib.sha256((directory/k).read_bytes()).hexdigest() for k in ('labels_a.csv','labels_b.csv')}
    counts={c:0 for c in CATEGORIES}
    for sid,s in pool.items():
        for field in ('queryId','targetId','finalTargetId'): uuid(s[field])
        if s['category'] not in CATEGORIES: raise ValueError('类别不在字典')
        counts[s['category']]+=1
        if s['split'] not in ('ACCEPTANCE','RECOVERY'): raise ValueError('不能用开发集验收')
        for key in ('snapshotRef','sourceRef','evidenceRef','consentRef'):
            if not s[key]: raise ValueError(sid+'缺少'+key)
        a,b=la[sid],lb[sid]
        for label in (a,b):
            if not label['annotatorId'] or not label['evidenceRef'] or not label['reasonCode']: raise ValueError('标注凭证不完整')
            if label['decision'] not in ('MATCH','REJECT','UNCERTAIN'): raise ValueError('未知标注结论')
            if label['decision']=='MATCH': uuid(label['targetId'])
            timestamp(label['lockedAt'])
        if a['annotatorId']==b['annotatorId']: raise ValueError('A/B不能是同一人')
        if s['labelA']!=a['decision'] or s['labelB']!=b['decision']: raise ValueError('汇总标签与原标注不一致')
        agreement=a['decision']==b['decision']=='MATCH' and a['targetId']==b['targetId']
        if agreement:
            final=a['targetId']
            if sid in adj: raise ValueError('无分歧却存在裁决，应检查归档版本')
        else:
            if sid not in adj: raise ValueError(sid+'标注有分歧且无裁决')
            c=adj[sid]
            if c['adjudicatorId'] in (a['annotatorId'],b['annotatorId']) or not c['adjudicatorId']: raise ValueError('裁决员不能是A/B')
            if c['decision']!='MATCH' or not c['reason'] or not c['evidenceRefs']: raise ValueError('未裁决为MATCH的样本不能入配对验收')
            if timestamp(c['decidedAt'])<max(timestamp(a['lockedAt']),timestamp(b['lockedAt'])): raise ValueError('裁决时间早于标注锁定')
            if c['labelsAVersion']!=versions['labels_a.csv'] or c['labelsBVersion']!=versions['labels_b.csv']: raise ValueError('裁决引用的标注指纹不一致')
            if s['adjudicatorId']!=c['adjudicatorId']: raise ValueError('裁决身份汇总不一致')
            final=c['finalTargetId']; uuid(final)
        if s['finalLabel']!='MATCH' or s['finalTargetId']!=final or s['targetId']!=final: raise ValueError('最终真值不一致')
    if any(n<10 for n in counts.values()): raise ValueError('六个类别各至少10组')
    if len({s['split'] for s in samples})!=1: raise ValueError('不能混用首次验收与恢复集')
    candidates=load(directory,'candidates.csv'); by={sid:[] for sid in pool}
    for c in candidates:
        sid=c['sampleId']
        if sid not in by: raise ValueError('候选引用未知样本')
        uuid(c['candidateId'])
        rank=int(c['rank']); score=int(c['score'])
        parts=[int(c[k]) for k in ('partC','partK','partL','partT')]
        if parts[0] not in (0,35) or parts[1] not in (0,15) or parts[2] not in (0,25) or parts[3] not in (0,10,25): raise ValueError('MR-1分项非法')
        if not 1<=rank<=10 or not 40<=score<=100 or sum(parts)!=score or c['ruleVersion']!='MR-1': raise ValueError('候选阈值、rank、总分或版本非法')
        by[sid].append(c)
    hits=0; empty=0; failures=[]
    for sid,cs in by.items():
        cs.sort(key=lambda c:int(c['rank']))
        if [int(c['rank']) for c in cs]!=list(range(1,len(cs)+1)): raise ValueError('rank重复或不连续')
        if len({c['candidateId'] for c in cs})!=len(cs): raise ValueError('候选ID重复')
        if [int(c['score']) for c in cs]!=sorted((int(c['score']) for c in cs),reverse=True): raise ValueError('候选分数顺序错误')
        if not cs: empty+=1
        if pool[sid]['targetId'] in [c['candidateId'] for c in cs]: hits+=1
        else: failures.append(dict(sampleId=sid,empty=not cs,candidateIds=[c['candidateId'] for c in cs]))
    met=hits>=80 and empty<=10
    return dict(runKind=kind,分母=100,命中数=hits,Top10命中率=hits/100,无候选数=empty,无候选率=empty/100,
                分层样本数=counts,统计门槛达到=met,统计建议='NORMAL_ELIGIBLE' if met else 'SEARCH_FIRST',
                真实质量Gate通过=False,Gate说明='脚本只复算CSV；真实许可/采样/快照/候选生成、100%检索覆盖与5人SYSTEM试用须另附证据。SYNTHETIC永不支持真实Gate。',
                失败样本=failures,输入SHA256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob('*.csv'))})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',required=True,type=Path)
    parser.add_argument('--run-kind',choices=['REAL','SYNTHETIC'],required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=evaluate(args.data_dir,args.run_kind)
    except (ValueError,KeyError,OSError) as e:
        print('输入无效，不生成通过报告：'+str(e),file=sys.stderr)
        return 2
    result['执行时间']=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"命中{result['命中数']}/100；空候选{result['无候选数']}/100；{result['统计建议']}；真实Gate未验证")
    return 0

if __name__=='__main__': sys.exit(main())
