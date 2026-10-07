"""Offline retrieval, with optional SQLite FTS5 and an identical JSON fallback."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import json
import math
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
ALIASES = (
    ('读书', '阅读', '文学', 'waterland', '水之乡', '书籍'),
    ('排练', '表演', '演员', 'pacino', 'swank', 'rehearsal'),
    ('低成本', '没钱', '预算', '资源', 'low budget'),
    ('多时间线', '非线性', '倒叙', '信息', '叙事', 'narrative'),
    ('机位', '透视', '相机', '距离', 'camera'),
    ('剪辑', '切点', '节奏', 'editing'),
    ('配乐', '声音', '听觉', '音乐', 'sound'),
    ('胶片', '颗粒', '曝光', '质感', 'film look'),
    ('追随', 'following'), ('记忆碎片', 'memento'),
    ('白夜追凶', 'insomnia'), ('侠影之谜', 'batman begins'),
    ('致命魔术', 'the prestige'), ('黑暗骑士', 'the dark knight'),
    ('盗梦空间', 'inception'), ('黑暗骑士崛起', 'the dark knight rises'),
    ('星际穿越', 'interstellar'), ('敦刻尔克', 'dunkirk'),
    ('信条', 'tenet'), ('奥本海默', 'oppenheimer'), ('奥德赛', 'the odyssey'),
)

def tokens(text):
    out = []
    for part in re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', str(text).lower()):
        if re.fullmatch(r'[\u3400-\u9fff]+', part):
            out.extend(part[i:i+2] for i in range(len(part)-1))
            if len(part) == 1:
                out.append(part)
        else:
            out.append(part)
    return out

def lexical(card):
    return tokens(' '.join(str(card.get(k, '')) for k in ('id','title','keywords','text','fact','inference')))

def allowed(card, mode):
    if mode == 'experience':
        return card['kind'] == 'experience'
    if mode == 'examples':
        return card['kind'] == 'example'
    if mode == 'voice':
        return card['id'].startswith(('VP','VE','VDC','QA12')) and card['kind'] != 'example'
    return card['kind'] != 'example'

def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

def recall(query, mode='craft', limit=4, budget=7000, root=ROOT, backend='auto'):
    if not query.strip():
        raise ValueError('query must not be empty')
    if mode not in ('craft','experience','examples','voice'):
        raise ValueError('unsupported mode')
    if not 1 <= limit <= 12 or not 1000 <= budget <= 50000:
        raise ValueError('limit must be 1..12; budget must be 1000..50000 characters')
    library = json.loads((root/'assets/library.json').read_text(encoding='utf-8'))
    cards = [c for c in library['cards'] if allowed(c, mode)]
    raw = set(tokens(query))
    expanded = set(raw)
    qlower = query.lower()
    for group in ALIASES:
        if any(word in qlower for word in group):
            expanded.update(tokens(' '.join(group)))
    expanded = set(sorted(expanded)[:160])
    used = 'json-bm25'
    candidate_ids = None
    # FTS is an accelerator, not a separate source of knowledge. A stale index
    # must never silently override canonical JSON or discard new records.
    if backend != 'json' and (root/'assets/library.sqlite').exists():
        try:
            with closing(sqlite3.connect((root/'assets/library.sqlite').resolve().as_uri()+'?mode=ro', uri=True)) as con:
                signature = con.execute('SELECT value FROM metadata WHERE key=?', ('content_sha256',)).fetchone()
                if signature and signature[0] == library['content_sha256']:
                    expression = ' OR '.join('"'+t+'"' for t in sorted(expanded))
                    if expression:
                        candidate_ids = {r[0] for r in con.execute('SELECT id FROM search WHERE search MATCH ?', (expression,))}
                    else:
                        candidate_ids = set()
                    used = 'sqlite-fts5+bm25'
        except (sqlite3.Error, OSError):
            pass
    if backend == 'sqlite' and used == 'json-bm25':
        raise ValueError('SQLite index unavailable or stale; use auto/json or rebuild')
    counts = [Counter(lexical(c)) for c in cards]
    df = Counter(t for count in counts for t in count)
    avg = sum(map(lambda c: sum(c.values()), counts))/max(1,len(counts))
    ranked = []
    for card, count in zip(cards, counts):
        exact = card['id'].lower() == qlower.strip()
        if candidate_ids is not None and card['id'] not in candidate_ids and not exact:
            continue
        length = sum(count.values())
        score = 0.0
        for term in expanded:
            tf = count[term]
            if not tf:
                continue
            idf = math.log(1+(len(cards)-df[term]+0.5)/(df[term]+0.5))
            score += idf * tf*2.2/(tf+1.2*(0.25+0.75*length/max(avg,1))) * (1 if term in raw else 0.22)
        score += 2.0*len(raw.intersection(tokens(card['title'])))
        if exact:
            score += 10000
        if score > 0:
            ranked.append((score,card))
    ranked.sort(key=lambda pair:(-pair[0],pair[1]['id']))
    result = {'version':library['version'],'backend':used,'mode':mode,'matches':len(ranked),
              'budget_unit':'serialized Unicode characters','cards':[],'sources':{},
              'note':'Evidence and original applications are separate. Imported sources were not all rechecked in v4.'}
    for score,card in ranked:
        if len(result['cards']) >= limit:
            break
        item = {k:card[k] for k in ('id','title','kind','speaker','source_review','fact','inference','limits','text','source_ids','source_file') if card.get(k)}
        item['card_file'] = 'references/cards/'+card['id']+'.md'
        item['score'] = round(score,3)
        item['truncated'] = False
        new_sources = dict(result['sources'])
        for sid in card['source_ids']:
            s = library['sources'][sid]
            new_sources[sid] = {'urls':s.get('urls',[])}
        trial = {**result,'cards':result['cards']+[item], 'sources':new_sources}
        if len(encoded(trial)) > budget:
            # Never return a half fact as an authoritative memory. Return a
            # navigable stub with its limits intact, or stop at the prior result.
            item.pop('text',None)
            item.pop('fact',None)
            item.pop('inference',None)
            item['truncated'] = True
            item['read_required'] = 'Read card_file before making a factual claim.'
            trial = {**result,'cards':result['cards']+[item], 'sources':new_sources}
        if len(encoded(trial)) <= budget:
            result = trial
        elif not result['cards']:
            stub = {'id':card['id'],'card_file':item['card_file'],'truncated':True,
                    'read_required':'Read the full card and its sources before use.'}
            result['cards'].append(stub)
            break
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query',required=True)
    parser.add_argument('--mode',choices=['craft','experience','examples','voice'],default='craft')
    parser.add_argument('--limit',type=int,default=4)
    parser.add_argument('--budget',type=int,default=7000,help='Maximum serialized Unicode characters, not tokens')
    parser.add_argument('--backend',choices=['auto','json','sqlite'],default='auto')
    args = parser.parse_args()
    try:
        print(encoded(recall(**vars(args))))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc)+'\n')

if __name__ == '__main__':
    main()
