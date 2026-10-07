#!/usr/bin/env python3
"""Retrieve connected source-grounded craft concepts, not ready-made answers."""
import argparse,json,re
from pathlib import Path

def terms(t):
    h=re.findall(r"[\u4e00-\u9fff]+",t)
    return set(re.findall(r"[a-z0-9-]+",t.lower()))|{s[i:i+2] for s in h for i in range(len(s)-1)}

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('query');p.add_argument('--top',type=int,default=3)
a=p.parse_args()
data=json.loads((Path(__file__).resolve().parents[1]/'references/craft-knowledge-map.json').read_text())
byid={x['id']:x for x in data['nodes']};q=terms(a.query)
scores=sorted([(len(q&terms(x['topic']+' '+x['keywords'])),x['id']) for x in data['nodes']],reverse=True)
primary=[i for score,i in scores if score][:max(1,min(a.top,6))]
if not primary:
    print('没有词面匹配；按当前意图读取方法/影片资料并推理，不将未匹配解释为不能回答。')
else:
    related=list(dict.fromkeys(j for i in primary for j in byid[i]['related_ids'] if j not in primary))[:4]
    print(json.dumps({'primary':[byid[i] for i in primary],'related':[byid[i] for i in related],'use':'Use concepts to make a new current-scene decision; never paste a retrieved example as the answer.'},ensure_ascii=False,indent=2))
