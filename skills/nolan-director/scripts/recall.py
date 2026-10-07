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
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
ANALYZER_VERSION = '2'
QUERY_STOP = set('我觉 觉得 一个 什么 怎么 怎样 为什 时候 这个 那个 不是 没有 就是 已经 好像 还是 现在 我们 你们 的话 但是 所以 可以 能够 不能 了吗 我想 帮我 给我 以前'.split())
QUERY_STOP.update('a an the i me my we us our you your he she it its they them their how what why when where who which can could would should shall will do does did have has had is am are was were be been being to of for from in on at by with as and or but if then than that this these those through while about into over under out up down not no yes so just only want need make work like would please tell know'.split())
# A small, auditable domain map, not a claim to implement general OpenCC.
TRADITIONAL = str.maketrans(dict(zip(
    '騎攝經驗該麼讓個來說鏡頭畫與導演觀眾聲樂讀書預算場劇憶隨間開關線時過後對話從簡體異準備習慣條現實選擇將會這為問題處關係滿親遠離樣動作資源錢據決',
    '骑摄经验该么让个来说镜头画与导演观众声乐读书预算场剧忆随间开关线时过后对话从简体异准备习惯条现实选择将会这为问题处关系满亲远离样动作资源钱据决')))
ALIASES = (
    ('读书', '阅读', '文学', 'waterland', '水之乡', '书籍'),
    ('排练', '表演', '演员', 'pacino', 'swank', 'rehearsal', 'rehearse', 'rehearsing', 'spontaneity', 'improvisation'),
    ('低成本', '没钱', '预算', '资源', 'low budget'),
    ('多时间线', '非线性', '倒叙', '信息', '叙事', 'narrative', 'timelines', 'time scales', 'chronology'),
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

FILM_ALIASES = ALIASES[8:]

def normalize_text(text):
    return unicodedata.normalize('NFKC', str(text)).translate(TRADITIONAL).lower()

def query_focus(query):
    """Conservatively isolate explicit topic changes; preserve the original query.

    The host still decides intent. This is finite lexical routing, not a semantic
    parser. A negative outcome ("不要让观众看不懂") remains a live concern, while
    a declined topic ("不需要低成本建议") is omitted from retrieval.
    """
    normalized = normalize_text(query)
    focus = re.compile(r'(?:现在|这次|本轮)?(?:只想|只需要|只处理|只谈|只改)|真正(?:的)?问题(?:是|在于)|我要知道|而是|\binstead\b')
    markers = list(focus.finditer(normalized))
    active = normalized[markers[-1].end():] if markers else normalized
    retained, excluded = [], []
    for clause in re.split(r'[，,。！？!?；;\n]+',active):
        clause = clause.strip()
        if not clause:
            continue
        negative = re.match(r'^(?:我(?:们)?|这次|现在|本轮|先)?(?:不需要|不想|不要|不用|无需|不必|不再|别|不是|并非|并不是)',clause)
        desired_prevention = re.match(r'^(?:我(?:们)?)?(?:不要|不想|别)(?:让|使)|^(?:并)?不是不',clause)
        english_declined = re.match(r"^(?:i |we )?(?:don['’]t need|do not need|no need for|don['’]t discuss|do not discuss|not about)\b",clause)
        if (negative and not desired_prevention) or english_declined:
            excluded.append(clause)
        else:
            retained.append(clause)
    return {'text':'；'.join(retained), 'excluded_clauses':excluded,
            'explicit_focus':bool(markers)}

def alias_in(text, word):
    if re.search(r'[a-z]',word):
        return re.search(r'(?<![a-z0-9])'+re.escape(word)+r'(?![a-z0-9])',text) is not None
    return word in text

def films_in(text):
    """Prefer a full title over an overlapping shorter title in a franchise."""
    matches = []
    for group in FILM_ALIASES:
        for word in group:
            pattern = re.escape(word)
            if re.search(r'[a-z]',word):
                pattern = r'(?<![a-z0-9])'+pattern+r'(?![a-z0-9])'
            matches.extend((m.start(),m.end(),group) for m in re.finditer(pattern,text))
    return {group for start,end,group in matches if not any(
        outer_start <= start and end <= outer_end and outer_end-outer_start > end-start
        for outer_start,outer_end,_ in matches)}

def tokens(text):
    out = []
    for part in re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', normalize_text(text)):
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

def resolve_situations(query, root, requested=None):
    path = root/'references/situations.json'
    if not path.exists():
        if requested:
            raise ValueError('Situation catalog unavailable')
        return []
    catalog = json.loads(path.read_text(encoding='utf-8'))['situations']
    known = {s['id'] for s in catalog}
    if requested and requested not in known:
        raise ValueError('Unknown situation: '+requested)
    def matches(s):
        for pattern in s['patterns']:
            for match in re.finditer(pattern,query,re.I):
                before = query[max(0,match.start()-6):match.start()]
                if not re.search(r'(不是|并非|并不是)\s*$',before):
                    return True
        return False
    return [s for s in catalog if s['id']==requested or matches(s)]

def recall(query, mode='craft', limit=4, budget=7000, root=ROOT, backend='auto', situation=None):
    if not query.strip():
        raise ValueError('query must not be empty')
    if mode not in ('craft','experience','examples','voice'):
        raise ValueError('unsupported mode')
    if not 1 <= limit <= 12 or not 1000 <= budget <= 50000:
        raise ValueError('limit must be 1..12; budget must be 1000..50000 characters')
    library = json.loads((root/'assets/library.json').read_text(encoding='utf-8'))
    cards = [c for c in library['cards'] if allowed(c, mode)]
    focus = query_focus(query)
    active_query = focus['text']
    raw = set(tokens(active_query))-QUERY_STOP
    expanded = set(raw)
    qlower = normalize_text(active_query)
    situations = resolve_situations(active_query,root,situation) if mode not in ('examples','voice') else []
    affinities = {}
    for s in situations:
        expanded.update(tokens(s['search_terms']))
        for key,weight in [('experience_ids',1.0),('craft_ids',0.8)]:
            for cid in s[key]:
                affinities[cid] = max(affinities.get(cid,0),weight)
    mentioned_films = films_in(qlower)
    for group in (*ALIASES[:8],*sorted(mentioned_films)):
        if any(alias_in(qlower,word) for word in group):
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
                analyzer = con.execute('SELECT value FROM metadata WHERE key=?', ('analyzer_version',)).fetchone()
                if signature and signature[0] == library['content_sha256'] and analyzer and analyzer[0] == ANALYZER_VERSION:
                    expression = ' OR '.join('"'+t+'"' for t in sorted(expanded))
                    if expression:
                        candidate_ids = {r[0] for r in con.execute('SELECT id FROM search WHERE search MATCH ?', (expression,))}
                    else:
                        candidate_ids = set()
                    candidate_ids.update(affinities)
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
        score += 18.0*affinities.get(card['id'],0)
        if mentioned_films:
            subject = normalize_text(' '.join(str(card.get(k,'')) for k in ('title','keywords','fact','text')))
            if mentioned_films.intersection(films_in(subject)):
                score += 10.0
        if exact:
            score += 10000
        if score > 0:
            ranked.append((score,card))
    ranked.sort(key=lambda pair:(-pair[0],pair[1]['id']))
    focus_summary = {'text':focus['text'][:160],
                     'excluded_clauses':[c[:80] for c in focus['excluded_clauses'][:2]],
                     'explicit_focus':focus['explicit_focus'],
                     'summary_truncated':len(focus['text'])>160 or len(focus['excluded_clauses'])>2
                         or any(len(c)>80 for c in focus['excluded_clauses'])}
    result = {'version':library['version'],'backend':used,'mode':mode,'matches':len(ranked),
              'situations':[s['id'] for s in situations],
              'query_interpretation':focus_summary,
              'budget_unit':'serialized Unicode characters','cards':[],'sources':{},
              'note':'Evidence and original applications are separate. Imported sources were not all rechecked in v4.'}
    used_events = set()
    for score,card in ranked:
        if len(result['cards']) >= limit:
            break
        event = card.get('experience_event')
        if event and event in used_events:
            continue
        item = {k:card[k] for k in ('id','title','kind','speaker','source_review','fact','inference','limits','text','source_ids','source_file') if card.get(k)}
        item['card_file'] = 'references/cards/'+card['id']+'.md'
        item['score'] = round(score,3)
        item['truncated'] = False
        if event:
            item['same_experience_cards'] = card.get('same_experience_cards',[])
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
            if event:
                used_events.add(event)
        elif not result['cards']:
            stub = {'id':card['id'],'card_file':item['card_file'],'truncated':True,
                    'read_required':'Read the full card and its sources before use.'}
            result['cards'].append(stub)
            break
    return result

def main():
    # CLI JSON is UTF-8 regardless of the Windows console/pipe code page.
    # Do not change process streams when this module is imported as a library.
    for stream in (sys.stdin,sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query',required=True)
    parser.add_argument('--mode',choices=['craft','experience','examples','voice'],default='craft')
    parser.add_argument('--limit',type=int,default=4)
    parser.add_argument('--budget',type=int,default=7000,help='Maximum serialized Unicode characters, not tokens')
    parser.add_argument('--backend',choices=['auto','json','sqlite'],default='auto')
    parser.add_argument('--situation',help='Optional editorial situation ID, selected from references/situations.json')
    args = parser.parse_args()
    try:
        print(encoded(recall(**vars(args))))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc)+'\n')

if __name__ == '__main__':
    main()
