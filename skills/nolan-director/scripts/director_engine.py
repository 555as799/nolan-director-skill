#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only craft retrieval and scene-contract diagnostics; standard library only."""
import argparse
from collections import defaultdict, deque
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    'voice': '对话 解释 观众 期待 视点 合作 主张 取舍 细节 限制',
    'narrative': '人物 欲望 动机 叙事 信息 因果 主题 认识 表演',
    'camera': '相机 摄影 机位 视点 距离 景别 运动 构图 焦距',
    'editing': '剪辑 镜头 切点 相邻 时间 节奏 顺序 期待 回忆',
    'sound': '声音 听觉 声源 位置 环境 配乐 静音 距离',
    'look': '胶片 格式 曝光 景深 高光 肤色 颗粒 材质 运动',
    'production': '实拍 特效 AI 生成 合成 接触 排练 预算 安全',
    'adaptation': '真实 经历 改编 帮助 救援 归返 记忆 事实',
    'memory': '记忆 主观 信息 回忆 抽象形象 剪辑 时间 声音',
    'reunion': '重逢 人物 表演 关系 视点 相机 距离',
    'water': '水下 海面 水面 身体 接触 浪 视点 声音 实拍',
    'grain': '胶片 颗粒 曝光 格式 高光 运动 交付',
    'joy': '快乐 人物 表演 关系 日常 情感',
    'time': '时间 节奏 信息 顺序 期待 剪辑',
}


def load_corpus():
    """Read the canonical library, including newly reviewed cards and sources."""
    return json.loads((ROOT/'assets/library.json').read_text(encoding='utf-8'))


def recall(query, limit=8, budget=11000, focus=None, mode='craft'):
    """Compatibility adapter; all ranking and evidence policy lives in recall.py.

    The historical conversation spelling now maps to experience: Nolan-attributed
    public accounts. Use craft for collaborators, retaining their own attribution.
    Output mode and budget semantics are those of the canonical engine.
    """
    modes = {'craft':'craft', 'conversation':'experience', 'examples':'examples'}
    if mode not in modes:
        raise ValueError('unsupported legacy recall mode')
    focus = [] if focus is None else ([focus] if isinstance(focus,str) else focus)
    if not isinstance(focus,list) or any(not isinstance(f,str) or f not in ALIASES for f in focus):
        raise ValueError('focus must contain supported legacy topic names')
    if not isinstance(query,str) or not query.strip():
        raise ValueError('query must not be empty')
    # A direct ID is a lookup, not a topic query; focus must not obscure it.
    exact_id = focus and query.strip().lower() in {c['id'].lower() for c in load_corpus()['cards']}
    expanded = query if exact_id else ' '.join([query]+[ALIASES[f] for f in focus])
    spec = importlib.util.spec_from_file_location('nolan_canonical_recall', ROOT/'scripts/recall.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.recall(expanded, limit=limit, budget=budget, mode=modes[mode], root=ROOT)


def read_plan(path):
    value=json.load(sys.stdin) if path=='-' else json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value,dict):
        raise ValueError('plan root must be an object')
    return value


def diagnose(plan):
    if not isinstance(plan,dict):
        raise ValueError('plan root must be an object')
    errors=[]
    warnings=[]
    def issue(code,path,detail):
        errors.append({'code':code,'path':path,'detail':detail})
    groups={}
    ids={}
    for group in ('facts','decisions','beats','shots','transitions','claims'):
        rows=plan.get(group)
        if not isinstance(rows,list):
            issue('missing_group',group,'expected an array, empty allowed when not applicable');rows=[]
        groups[group]=rows
        if group not in ('transitions','claims'):
            for i,row in enumerate(rows):
                path=f'{group}[{i}]'
                if not isinstance(row,dict):
                    issue('invalid_row',path,'expected an object');continue
                rid=row.get('id')
                if not isinstance(rid,str) or not rid.strip():
                    issue('missing_id',path,'nonempty id required');continue
                if rid in ids:
                    issue('duplicate_id',path,rid)
                ids[rid]=(group,row)
    if not groups['beats'] or not groups['shots']:
        issue('incomplete_scene','beats/shots','complete scene contract requires beats and shots')
    for group in ('facts','decisions'):
        for i,row in enumerate(groups[group]):
            if not isinstance(row,dict):continue
            choices={'confirmed','proposed','unknown'} if group=='facts' else {'adopted','proposed','rejected'}
            if row.get('status') not in choices:
                issue('invalid_status',f'{group}[{i}]','must distinguish confirmed/adopted from proposal or unknown')
            for key in ('text','source') if group=='facts' else ('text',):
                if not isinstance(row.get(key),str) or not row[key].strip():issue('empty_field',f'{group}[{i}].{key}','provide text/provenance')
    for group in ('beats','shots'):
        for i,row in enumerate(groups[group]):
            if not isinstance(row,dict):continue
            required=('purpose','action','change') if group=='beats' else ('purpose','action','camera','sound')
            for key in required:
                v=row.get(key)
                if not isinstance(v,(str,dict)) or not v:
                    issue('empty_field',f'{group}[{i}].{key}','specific decision required')
            refs=row.get('fact_refs')
            if not isinstance(refs,list):issue('fact_refs_missing',f'{group}[{i}]','list confirmed facts used as fixed constraints; proposals remain proposals')
            else:
                for rid in refs:
                    if not isinstance(rid,str):issue('invalid_reference',f'{group}[{i}].fact_refs','expected string IDs')
                    elif rid not in ids or ids[rid][0]!='facts':issue('unknown_fact',f'{group}[{i}]',rid)
                    elif ids[rid][1].get('status')!='confirmed':issue('unconfirmed_fact',f'{group}[{i}]',rid)
            if group=='shots':
                bid=row.get('beat_id')
                if not isinstance(bid,str) or bid not in ids or ids[bid][0]!='beats':issue('unknown_beat',f'shots[{i}].beat_id',str(bid))
    for rid,(group,row) in ids.items():
        deps=row.get('dependencies',[])
        if not isinstance(deps,list):issue('invalid_dependencies',rid,'expected ID array');continue
        for dep in deps:
            if not isinstance(dep,str):issue('invalid_dependency',rid,'expected string IDs')
            elif dep not in ids:issue('unknown_dependency',rid,str(dep))
            elif ids[dep][0]=='decisions' and ids[dep][1].get('status')!='adopted':issue('unadopted_dependency',rid,str(dep))
    graph={rid:[d for d in row.get('dependencies',[]) if isinstance(d,str)] for rid,(_,row) in ids.items() if isinstance(row.get('dependencies',[]),list)}
    visiting=set();done=set()
    def visit(rid):
        if rid in visiting:issue('cyclic_dependency',rid,'dependency graph must be acyclic');return
        if rid in done:return
        visiting.add(rid)
        for dep in graph.get(rid,[]):
            if dep in graph:visit(dep)
        visiting.remove(rid);done.add(rid)
    for rid in graph:visit(rid)
    pairs={}
    for i,t in enumerate(groups['transitions']):
        if not isinstance(t,dict):issue('invalid_transition',str(i),'expected object');continue
        pair=(t.get('from'),t.get('to'))
        if not all(isinstance(rid,str) for rid in pair):
            issue('invalid_transition_reference',str(i),'from/to must be string shot IDs');continue
        if pair in pairs:issue('duplicate_transition',str(i),str(pair))
        pairs[pair]=t
        for key in ('cut_reason','picture_anchor','sound_bridge'):
            if not isinstance(t.get(key),str) or not t[key].strip():issue('empty_transition',f'transitions[{i}].{key}','explain this actual cut/bridge')
        for rid in pair:
            if rid not in ids or ids[rid][0]!='shots':issue('unknown_transition_shot',str(i),str(rid))
    shots=[x for x in groups['shots'] if isinstance(x,dict)]
    for a,b in zip(shots,shots[1:]):
        if not all(isinstance(x.get('id'),str) for x in (a,b)) or (a.get('id'),b.get('id')) not in pairs:issue('missing_cut',(str(a.get('id','?'))+'→'+str(b.get('id','?'))),'adjacent shots require a transition')
    durations=[s.get('duration_seconds') for s in shots]
    if any(d is not None for d in durations):
        if not all(isinstance(d,(int,float)) and not isinstance(d,bool) and math.isfinite(d) and d>0 for d in durations):issue('invalid_duration','shots','either omit all durations or use positive finite values throughout')
        elif plan.get('target_duration_seconds') is not None:
            target=plan['target_duration_seconds']
            if not isinstance(target,(int,float)) or isinstance(target,bool) or not math.isfinite(target) or target<=0:issue('invalid_target_duration','target_duration_seconds','positive finite number required')
            elif abs(sum(durations)-target)>.05:issue('duration_mismatch','shots','sum differs from stated target')
    known_sources=load_corpus()['sources']
    for i,c in enumerate(groups['claims']):
        if not isinstance(c,dict):issue('invalid_claim',str(i),'expected object');continue
        if c.get('type') not in {'source_fact','editorial_interpretation','original_proposal'}:issue('claim_type',f'claims[{i}]','identify source fact, interpretation or proposal')
        if c.get('type')=='source_fact':
            refs=c.get('source_ids',[])
            if not isinstance(refs,list) or not refs:issue('unsourced_claim',f'claims[{i}]','source fact requires registered source IDs')
            else:
                for sid in refs:
                    if not isinstance(sid,str):issue('invalid_source_reference',f'claims[{i}]','expected string source IDs')
                    elif sid not in known_sources:issue('unknown_source',f'claims[{i}]',sid)
    warnings.append('Structural diagnostics cannot prove artistic quality, every factual omission, precise source interpretation, or safe physical feasibility. Independent critique and production review remain required.')
    return {'valid':not errors,'errors':errors,'warnings':warnings,'shots':len(shots)}


def affected(plan,changed):
    if not isinstance(plan,dict):raise ValueError('plan root must be an object')
    if not isinstance(changed,list) or any(not isinstance(r,str) or not r for r in changed):raise ValueError('changed must contain string IDs')
    ids={}
    for group in ('facts','decisions','beats','shots'):
        rows=plan.get(group,[])
        if not isinstance(rows,list):raise ValueError(group+' must be an array')
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id']:raise ValueError(group+' rows require string IDs')
            if row['id'] in ids:raise ValueError('duplicate ID: '+row['id'])
            ids[row['id']]=row
    reverse=defaultdict(set)
    for rid,row in ids.items():
        deps=row.get('dependencies',[]);facts=row.get('fact_refs',[])
        if not isinstance(deps,list) or not isinstance(facts,list):raise ValueError('dependencies/fact_refs must be arrays: '+rid)
        refs=deps+facts
        if row.get('beat_id'):refs.append(row['beat_id'])
        for dep in refs:
            if not isinstance(dep,str):raise ValueError('references must contain string IDs: '+rid)
            reverse[dep].add(rid)
    unknown=sorted(set(changed)-ids.keys())
    seen=set(changed);queue=deque(changed)
    while queue:
        for node in sorted(reverse[queue.popleft()]):
            if node not in seen:seen.add(node);queue.append(node)
    transition_rows=plan.get('transitions',[])
    if not isinstance(transition_rows,list):raise ValueError('transitions must be an array')
    transitions=[]
    for t in transition_rows:
        if not isinstance(t,dict) or not all(isinstance(t.get(k),str) for k in ('from','to')):raise ValueError('transitions require string from/to shot IDs')
        if t['from'] in seen or t['to'] in seen:transitions.append(t)
    return {'changed':changed,'unknown_changed_ids':unknown,'affected_nodes':sorted(seen-set(changed)),'affected_transitions':transitions,'operation':'read-only; no automatic adoption or file mutation'}


def main():
    # Scene JSON and retrieval output use one portable encoding on pipes/consoles.
    for stream in (sys.stdin,sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('recall');r.add_argument('--query',required=True);r.add_argument('--limit',type=int,default=8);r.add_argument('--budget',type=int,default=11000);r.add_argument('--focus',action='append',choices=list(ALIASES))
    r.add_argument('--mode',choices=['craft','conversation','examples'],default='craft')
    v=sub.add_parser('validate');v.add_argument('plan')
    a=sub.add_parser('affected');a.add_argument('plan');a.add_argument('--changed',action='append',required=True)
    args=parser.parse_args()
    try:
        if args.command=='recall':result=recall(args.query,args.limit,args.budget,args.focus,args.mode)
        elif args.command=='validate':result=diagnose(read_plan(args.plan))
        else:result=affected(read_plan(args.plan),args.changed)
        print(json.dumps(result,ensure_ascii=False,separators=(',', ':')) if args.command=='recall' else json.dumps(result,ensure_ascii=False,indent=2))
        if args.command=='validate' and not result['valid']:sys.exit(2)
    except (OSError,ValueError,TypeError,KeyError) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False));sys.exit(1)


if __name__=='__main__':
    main()
