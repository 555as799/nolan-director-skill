"""Build the self-contained Nolan Skill repository with Python's standard library."""
from __future__ import annotations
from collections import Counter
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parent
SKILL = ROOT/'skills/nolan-director'
VERSION = '4.1.3'

def dump(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def public_skill_files(base=SKILL):
    rules=load(ROOT/'release-files.json')
    for p in sorted(base.rglob('*')):
        if not p.is_file() or p.is_symlink():
            continue
        rel=p.relative_to(base)
        if not p.resolve().is_relative_to(base.resolve()):
            raise ValueError('Skill path escapes package')
        if any(part.casefold() in {s.casefold() for s in rules['exclude_components']} or part.casefold().startswith('.env') for part in rel.parts):
            continue
        if p.suffix.casefold() in {s.casefold() for s in rules['exclude_suffixes']}:
            continue
        yield p

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def normalize(card):
    c = dict(card)
    correction = load(ROOT/'data/runtime-corrections.json')['corrections'].get(c['id'])
    if correction:
        for key,value in list(c.items()):
            if isinstance(value,str):
                for old,new in correction['replace'].items():
                    value=value.replace(old,new)
                c[key]=value
        c['runtime_correction']=correction['reason']
    typ = c['evidence_type']
    c['source_review'] = 'inherited_v3.2.2_not_individually_rechecked_in_v4'
    c['kind'] = 'example' if typ.startswith(('original_testing','original_dialogue')) else 'craft'
    if typ == 'contextual_public_interview_paraphrase':
        c['kind'] = 'experience' if c.get('speaker') == 'Christopher Nolan' else 'collaborator'
        match = re.search(r'研究转述：(.*?)(?:\n|$)',c['text'])
        c['fact'] = match.group(1) if match else ''
        c['inference'] = c.get('conditional_decision','')
        c['limits'] = c.get('not_implied','')
    return c

def build():
    provenance = load(ROOT/'data/migration-provenance.json')
    corpus_path = ROOT/'data/legacy-corpus.json'
    if sha(corpus_path) != provenance['copied_corpus_sha256']:
        raise ValueError('Immutable legacy input changed; add refinements instead')
    corpus = load(corpus_path)
    shutil.copyfile(corpus_path,SKILL/'assets/director-corpus.json')
    cards = [normalize(c) for c in corpus['cards']]
    sources = dict(corpus['sources'])
    seed = load(ROOT/'data/verified-seed.json')
    mapping = {}
    for s in seed['sources']:
        existing = next((sid for sid,v in sources.items() if s['url'] in v.get('urls',[])),None)
        sid = existing or 'V4-'+s['id']
        mapping[s['id']] = sid
        if not existing:
            sources[sid] = {'id':sid,'description':s['title'],'urls':[s['url']]}
        sources[sid]['v4_checked_scope'] = s['verification']
        sources[sid]['v4_checked_on'] = s['verified_on']
    for c in seed['cards']:
        cards.append({'id':'V4-'+c['id'],'title':c['title'],'keywords':' '.join(c.get('works',[])+c['tags']),
                      'text':c['fact']+'\n原创迁移：'+c['inference']+'\n练习：'+c['exercise'],
                      'fact':c['fact'],'inference':c['inference'],'limits':'；'.join(c['limits']),
                      'source_ids':[mapping[c['source_id']]],'evidence_type':'public_self_report_paraphrase',
                      'kind':'experience','speaker':'Christopher Nolan','source_review':'relevant_passage_checked_2026-10-07',
                      'source_file':'references/verified-supplement.json','locator':c['locator'],
                      'relationship':c.get('relationship','public_self_report'),'related_ids':[]})
    dump(SKILL/'references/verified-supplement.json',seed)
    refinements = load(ROOT/'research/primary-refinements.json')
    dump(SKILL/'references/primary-refinements.json',refinements)
    lookup = {c['id']:c for c in cards}
    for review in refinements['reviewed_existing']:
        c = lookup[review['id']]
        if review['source_id'] not in c['source_ids']:
            raise ValueError('Review attributed to wrong source: '+c['id'])
        c['source_review'] = 'relevant_passage_checked_'+review.get('reviewed_on',refinements['reviewed_on'])
        c['review_record'] = review
    for c in refinements['cards']:
        cards.append({**c,'source_ids':[c['source_id']],
                      'text':c['fact']+'\n原创迁移：'+c['inference']+'\n不能推出：'+c['limits'],
                      'evidence_type':'public_self_report_paraphrase','kind':'experience','speaker':'Christopher Nolan',
                      'source_review':'relevant_passage_checked_2026-10-07',
                      'source_file':'references/primary-refinements.json',
                      'relationship':'structured_refinement_of_existing_sources'})
    expansion = load(ROOT/'research/expansion-agent.json')
    dump(SKILL/'references/experience-expansion.json',expansion)
    source_map = {}
    for s in expansion['sources']:
        existing = next((sid for sid,v in sources.items()
                         if s['url'].rstrip('/') in [u.rstrip('/') for u in v.get('urls',[])]),None)
        sid = existing or s['id']
        source_map[s['id']] = sid
        if not existing:
            sources[sid] = {'id':sid,'description':s['title'],'urls':[s['url']]}
        sources[sid].setdefault('passage_reviews',[]).append(s)
    for c in expansion['cards']:
        personal = c['speaker']=='Christopher Nolan'
        cards.append({**c,'source_ids':[source_map[c['source_id']]],
                      'keywords':' '.join(c['keywords']),
                      'text':c['question_context']+'\n公开转述：'+c['fact']+'\n当时条件：'+c['decision_context']+'\n'+c['inference']+'\n'+c['current_application']+'\n不可推出：'+c['limits'],
                      'kind':'experience' if personal else 'collaborator',
                      'evidence_type':'public_self_report_paraphrase' if personal else 'attributed_collaborator_paraphrase',
                      'source_review':'relevant_passage_checked_'+c['reviewed_on'],
                      'source_file':'references/experience-expansion.json',
                      'related_ids':c['related_existing_ids']})
    for c in cards:
        if any(s not in sources for s in c['source_ids']):
            raise ValueError('Broken source '+c['id'])
    by_id = {c['id']:c for c in cards}
    events = load(ROOT/'data/experience-events.json')
    for event in events['events']:
        for cid in event['card_ids']:
            c = by_id[cid]
            if c['kind']!='experience' or c.get('experience_event'):
                raise ValueError('Invalid or duplicate experience event: '+cid)
            c['experience_event'] = event['id']
            c['same_experience_cards'] = [x for x in event['card_ids'] if x!=cid]
    from validate_library import validate
    validate({'cards':cards,'sources':sources})
    payload = {'cards':cards,'sources':sources}
    digest = hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    library = {'version':VERSION,'revision':'experience-and-intent-2','content_sha256':digest,'private_project_data':False,
               'baseline_cards':len(corpus['cards']),'supplement_cards':len(seed['cards']),
               'refined_cards':len(refinements['cards']),'expanded_cards':len(expansion['cards']),**payload}
    dump(SKILL/'assets/library.json',library)
    spec = importlib.util.spec_from_file_location('nolan_recall',SKILL/'scripts/recall.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    db = SKILL/'assets/library.sqlite'
    with closing(sqlite3.connect(db)) as con:
        con.executescript('DROP TABLE IF EXISTS search; DROP TABLE IF EXISTS cards; DROP TABLE IF EXISTS metadata; CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT); CREATE TABLE cards (id TEXT PRIMARY KEY,kind TEXT,payload TEXT); CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED,lex);')
        con.execute('INSERT INTO metadata VALUES (?,?)',('content_sha256',digest))
        con.execute('INSERT INTO metadata VALUES (?,?)',('analyzer_version',module.ANALYZER_VERSION))
        for c in cards:
            con.execute('INSERT INTO cards VALUES (?,?,?)',(c['id'],c['kind'],json.dumps(c,ensure_ascii=False)))
            con.execute('INSERT INTO search VALUES (?,?)',(c['id'],' '.join(module.lexical(c))))
        con.commit()
        con.execute('VACUUM')
    card_dir = SKILL/'references/cards'; card_dir.mkdir(exist_ok=True)
    for c in cards:
        lines = ['# '+c['id']+' · '+c['title'], '',
                 '- 类型：'+c['kind']+' / '+c['evidence_type'],
                 '- 说话者：'+c.get('speaker','未逐条标明；不可直接作为个人历史自述'),
                 '- 核验：'+c['source_review'],
                 '- 原资料：`'+c['source_file']+'`（路径相对 Skill 根目录）','']
        if c.get('fact'):
            lines += ['## 公开事实的研究转述',c['fact'],'','## 原创迁移',c.get('inference',''),'',
                      '## 不可推出',c.get('limits','不得把新建议归因为历史原话。'),'']
        lines += ['## 完整研究记录',c['text'],'','## 来源与定位',c.get('locator','按链接核对相关段落。')]
        for sid in c['source_ids']:
            lines += ['- ['+sid+']('+u+')' for u in sources[sid].get('urls',[])]
        if not c['source_ids']:
            lines += ['无历史来源；本卡是编辑创作分析或原创示例。']
        if c.get('same_experience_cards'):
            lines += ['', '同一经历的其他采访记录（保留各自细节与语境）：']
            lines += ['- ['+cid+']('+cid+'.md)' for cid in c['same_experience_cards']]
        (card_dir/(c['id']+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    index = ['# 资料索引','',f'{len(cards)} 张卡：继承 {len(corpus["cards"])} 张，补入 {len(seed["cards"])} 张卡、细化 {len(refinements["cards"])} 张公开经历，再扩展 {len(expansion["cards"])} 张有语境的公开经历及合作回忆；含重合事实，不是同等数量的独立经历。',
             '先按影片或关键词定位，再读相关单卡；下面只是目录，不能凭标题编造事实。已核对补充卡适合直接核读；继承卡的逐项复核状态在卡内。','',
             '## 影片入口']
    index += ['- ['+c['title']+'](cards/'+c['id']+'.md)' for c in cards if c['id'].startswith('F')]
    index += ['', '## 公开经历与阅读（归属于诺兰）']
    index += ['- ['+c['id']+' '+c['title']+'](cards/'+c['id']+'.md) · '+c['keywords'] for c in cards if c['kind']=='experience']
    index += ['', '## 主题入口',
              '- 结构、倒叙、时间与观众信息：K01、K02、J01—J03；阅读影响见 V4-N003。',
              '- 演员、排练、协作：K11、J16、QA12-D01、QA12-D02；不同主创归属见下面目录。',
              '- 镜头、距离、画幅、空间：K03—K05、J05、J09；画面技术问答见 L01—L48（原创应用）。',
              '- 声音、配乐、剪辑：K06、K10、J06、J07、QA12-DB02。',
              '- 预算、实拍、技术协作：K12、K16、J10、J12；低预算经验见 V4-N004。',
              '- 语气、接话、回应反驳：VP、VE、QA12-I 系列；VC 是原创中文示范。','', '## 全卡目录']
    for kind,label in [('craft','创作研究：事实与分析混合，核对原归属'),('collaborator','其他主创的经验'),('example','原创练习与对话示例：不是历史事实')]:
        index += ['', '### '+label]
        index += ['- ['+c['id']+' '+c['title']+'](cards/'+c['id']+'.md)' for c in cards if c['kind']==kind]
    (SKILL/'references/library-index.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    summary = {'version':VERSION,'baseline_files_verified_at_migration':provenance['baseline_manifest_entries_checked'],
               'cards':len(cards),'source_entries':len(sources),'types':dict(Counter(c['kind'] for c in cards)),
               'film_entries':sum(c['id'].startswith('F') for c in cards),'passage_checked_supplement_cards':len(seed['cards']),
               'passage_checked_refined_cards':len(refinements['cards']),
               'passage_checked_expansion_cards':len(expansion['cards']),
               'existing_cards_rechecked':len(refinements['reviewed_existing']),
               'total_passage_checked_cards':sum(c['source_review'].startswith('relevant_passage_checked_') for c in cards),
               'all_baseline_sources_rechecked':False,'new_weight_training':False,'workbuddy_native_import_tested':False,'content_sha256':digest}
    dump(ROOT/'validation/build-summary.json',summary)
    package()
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def package():
    from audit_readiness import current_evaluation
    dist = ROOT/'dist'; dist.mkdir(exist_ok=True)
    for name in ('LICENSE','NOTICE.md'):
        shutil.copyfile(ROOT/name,SKILL/name)
    evaluation=current_evaluation(ROOT,VERSION)
    dump(SKILL/'assets/product-status.json',{
        'version':VERSION,
        'stage':'release_candidate',
        'revision':'experience-led-dialogue-2',
        'delivery_scope':'portable_persona_skill',
        'parameter_training_required_for_current_scope':False,
        'ready_for_final_release':False,
        'model_weights_trained_this_session':False,
        'large_scale_new_corpus_completed':False,
        'generated_dialogue_evaluation_completed':evaluation['completed'],
        'current_revision_evaluation_status':evaluation['status'],
        'current_revision_evaluation_record':evaluation['directory']+'/version-mapping.json',
        'dialogue_evaluation_scope':'small_sample_independent_ai_trials_not_customer_host_validation',
        'workbuddy_native_import_tested':False,
        'prior_workbuddy_activation_observed':True,
        'prior_workbuddy_dialogue_quality':'user_rejected_4.1.0_and_4.1.2',
        'current_workbuddy_dialogue_quality':'not_yet_observed',
        'note':'Packaging and retrieval checks are not evidence of persona or creative quality.'
    })
    standard = (SKILL/'SKILL.md').read_text(encoding='utf-8')
    end = standard.index('\n---',4)+4
    body = standard[end:]
    wb_header = '\n'.join(['---','name: nolan-director','display_name: 诺兰导演','display_name_en: Nolan Director',
                          'description: 诺兰导演 AI 演绎，第一人称创作对话，含公开经历与影片资料库。用户要求和诺兰聊剧本、镜头、表演、剪辑或声音时使用。',
                          'description_zh: 基于公开资料的诺兰导演 AI 演绎，非真人或本人授权产品。',
                          'description_en: First-person Nolan creative roleplay with a sourced film library; an AI simulation, not the real person or an endorsed product.',
                          'category: writing','version: '+VERSION,'author: CineMatrix','---'])
    wb_skill = wb_header+body
    dump(SKILL/'assets/integrity.json',{'version':VERSION,'files':[
        {'path':str(p.relative_to(SKILL)).replace('\\','/'),'sha256':sha(p)}
        for p in public_skill_files() if p.name!='integrity.json']})
    for name,prefix,override in [(f'nolan-director-{VERSION}-workbuddy.zip','',wb_skill),(f'nolan-director-{VERSION}-portable.zip','nolan-director/',None)]:
        with zipfile.ZipFile(dist/name,'w',zipfile.ZIP_DEFLATED) as z:
            for p in public_skill_files():
                rel=p.relative_to(SKILL).as_posix()
                if override and rel=='SKILL.md':
                    z.writestr(prefix+rel,override)
                elif override and rel=='assets/integrity.json':
                    info=load(p)
                    for row in info['files']:
                        if row['path']=='SKILL.md': row['sha256']=hashlib.sha256(override.encode()).hexdigest()
                    z.writestr(prefix+rel,json.dumps(info,ensure_ascii=False,indent=2)+'\n')
                else:
                    z.write(p,prefix+rel)
    dump(dist/'SHA256.json',{p.name:sha(p) for p in sorted(dist.glob('*.zip'))})

if __name__ == '__main__':
    build()
