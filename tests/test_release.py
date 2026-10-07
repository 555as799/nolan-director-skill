"""Offline checks: these do not score WorkBuddy's generated dialogue."""
import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/nolan-director'
spec = importlib.util.spec_from_file_location('recall',SKILL/'scripts/recall.py')
recall = importlib.util.module_from_spec(spec); spec.loader.exec_module(recall)
LIBRARY = json.loads((SKILL/'assets/library.json').read_text(encoding='utf-8'))
VERSION = json.loads((ROOT/'release-files.json').read_text(encoding='utf-8'))['version']

class ReleaseTests(unittest.TestCase):
    def test_baseline_preserved(self):
        old = json.loads((SKILL/'assets/director-corpus.json').read_text(encoding='utf-8'))
        corrections = json.loads((ROOT/'data/runtime-corrections.json').read_text(encoding='utf-8'))['corrections']
        newer = {c['id']:c for c in LIBRARY['cards']}
        for card in old['cards']:
            for key,value in card.items():
                if card['id'] in corrections and isinstance(value,str):
                    for before,after in corrections[card['id']]['replace'].items():
                        value=value.replace(before,after)
                self.assertEqual(newer[card['id']][key],value)

    def test_source_and_file_links(self):
        self.assertEqual(len({c['id'] for c in LIBRARY['cards']}),len(LIBRARY['cards']))
        for card in LIBRARY['cards']:
            self.assertTrue((SKILL/card['source_file']).is_file(),card['id'])
            self.assertTrue((SKILL/'references/cards'/(card['id']+'.md')).is_file())
            for sid in card['source_ids']:
                self.assertIn(sid,LIBRARY['sources'])
        text = (SKILL/'SKILL.md').read_text(encoding='utf-8')
        for path in re.findall(r'@(references/[\w./-]+)',text):
            self.assertTrue((SKILL/path).exists(),path)

    def test_personal_attribution(self):
        for card in LIBRARY['cards']:
            if card['kind']=='experience':
                self.assertEqual(card['speaker'],'Christopher Nolan')
                self.assertTrue(card['source_ids'])
                self.assertTrue(card['fact'])
        dp=next(c for c in LIBRARY['cards'] if c['id']=='QA12-DP01')
        self.assertEqual(dp['kind'],'collaborator')

    def test_no_examples_in_default(self):
        ids={c['id'] for c in LIBRARY['cards'] if c['kind']=='example'}
        for query in ('快乐 漂流','胶片 颗粒 测试','VC02'):
            self.assertFalse(ids.intersection(c['id'] for c in recall.recall(query)['cards']))

    def test_experience_excludes_collaborators(self):
        result=recall.recall('Wally Pfister 致命魔术 布光',mode='experience',budget=20000)
        self.assertTrue(all(c['speaker']=='Christopher Nolan' for c in result['cards']))

    def test_sqlite_json_parity(self):
        for query in ('Waterland','白夜追凶 排练','星际穿越 配乐','盗梦空间 走廊','QA12-DP01','!!!'):
            a=recall.recall(query,backend='sqlite',budget=20000)
            b=recall.recall(query,backend='json',budget=20000)
            a.pop('backend');b.pop('backend')
            self.assertEqual(a,b)

    def test_budget_and_navigable_stub(self):
        for budget in (1000,1400,2500,7000):
            result=recall.recall('F10',limit=12,budget=budget)
            self.assertLessEqual(len(recall.encoded(result)),budget)
            self.assertTrue(result['cards'])
            for card in result['cards']:
                if card['truncated']:
                    self.assertIn('read_required',card)
                    self.assertNotIn('fact',card)

    def test_unrelated_and_invalid_queries(self):
        self.assertEqual(recall.recall('zzzzunfindable98765')['cards'],[])
        for args in ({'query':''},{'query':'x','limit':0},{'query':'x','budget':500},{'query':'x','mode':'bad'}):
            with self.assertRaises(ValueError): recall.recall(**args)

    def test_missing_corrupt_and_stale_database_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets').mkdir()
            shutil.copyfile(SKILL/'assets/library.json',root/'assets/library.json')
            self.assertEqual(recall.recall('Waterland',root=root)['backend'],'json-bm25')
            (root/'assets/library.sqlite').write_bytes(b'not a database')
            self.assertEqual(recall.recall('Waterland',root=root)['backend'],'json-bm25')
            shutil.copyfile(SKILL/'assets/library.sqlite',root/'assets/library.sqlite')
            with closing(sqlite3.connect(root/'assets/library.sqlite')) as con:
                con.execute('UPDATE metadata SET value=?',('stale',))
                con.commit()
            self.assertEqual(recall.recall('Waterland',root=root)['backend'],'json-bm25')

    def test_zip_manifest_and_workbuddy_metadata(self):
        for name,prefix in [(f'nolan-director-{VERSION}-workbuddy.zip',''),(f'nolan-director-{VERSION}-portable.zip','nolan-director/')]:
            with zipfile.ZipFile(ROOT/'dist'/name) as z:
                self.assertIsNone(z.testzip())
                self.assertIn(prefix+'SKILL.md',z.namelist())
                for path in z.namelist():
                    self.assertNotIn('..',Path(path).parts)
                    self.assertFalse(path.startswith(('/','\\')))
                    self.assertNotIn('__pycache__',path)
                manifest=json.loads(z.read(prefix+'assets/integrity.json'))
                self.assertEqual(manifest['version'],VERSION)
                self.assertEqual(json.loads(z.read(prefix+'assets/library.json'))['version'],VERSION)
                for row in manifest['files']:
                    self.assertEqual(hashlib.sha256(z.read(prefix+row['path'])).hexdigest(),row['sha256'])
                if not prefix:
                    header=z.read('SKILL.md').decode('utf-8').split('---')[1]
                    for field in ('name','description','description_zh','description_en','version','author'):
                        self.assertRegex(header,r'(?m)^'+field+r':\s*\S+')

    def test_relocated_customer_package(self):
        with tempfile.TemporaryDirectory(prefix='nolan_客户_') as tmp:
            with zipfile.ZipFile(ROOT/f'dist/nolan-director-{VERSION}-workbuddy.zip') as z:
                z.extractall(tmp)
            result=recall.recall('Waterland',root=Path(tmp),mode='experience',backend='sqlite')
            # Two verified interviews describe this same reading experience.
            self.assertIn(result['cards'][0]['id'],{'V4-N003','EXP-RD01'})

    def test_situation_card_links_and_positive_selection(self):
        catalog=json.loads((SKILL/'references/situations.json').read_text(encoding='utf-8'))
        ids={c['id'] for c in LIBRARY['cards']}
        for s in catalog['situations']:
            self.assertTrue(set(s['experience_ids']+s['craft_ids']).issubset(ids))
        for query,expected in [
            ('没有钱拍大场面，你以前怎么处理？',{'V4-N004','EXP-ASC02'}),
            ('我的画面很漂亮，但感觉离这个人很远。',{'EXP-ASC01','K03'}),
            ('为什么我的两条线来回切，观众越来越糊涂？',{'V4-N001','V4-N003','EXP-DGA17A'}),
            ('设备太少，就我们几个人能拍出什么？',{'V4-N004','K16'}),
        ]:
            result=recall.recall(query,budget=16000)
            self.assertTrue(expected.intersection(c['id'] for c in result['cards']))

    def test_situation_negation_and_explicit_context(self):
        cases=recall.resolve_situations('不是没有钱，是演员要求再来一条。',SKILL)
        self.assertNotIn('limited_resources',[s['id'] for s in cases])
        self.assertIn('actor_process',[s['id'] for s in cases])
        result=recall.recall('那怎么办？',situation='limited_resources',mode='experience')
        self.assertTrue({'V4-N004','EXP-ASC02'}.intersection(c['id'] for c in result['cards']))
        with self.assertRaises(ValueError): recall.recall('那怎么办？',situation='not_a_situation')

    def test_situation_modes_parity(self):
        for query in ('没有钱拍大场面','画面很漂亮，但感觉离这个人很远','两条线来回切'):
            a=recall.recall(query,backend='sqlite');b=recall.recall(query,backend='json')
            a.pop('backend');b.pop('backend');self.assertEqual(a,b)


# These are developer-selected retrieval regressions, not a held-out quality benchmark.
RETRIEVAL_CASES = [
    ('Waterland','experience',{'V4-N003','EXP-RD01'}),
    ('读书 多时间线','experience',{'V4-N003','EXP-RD01'}),
    ('白夜追凶 Pacino Swank 排练','experience',{'QA12-D01'}),
    ('盗梦空间 旋转走廊','craft',{'V4-N002'}),
    ('Following 低预算','experience',{'V4-N004'}),
    ('演员 临时再拍一次','craft',{'QA12-D02'}),
    ('Wally Pfister 致命魔术 布光','craft',{'QA12-DP01'}),
    ('剪辑 重复解释','craft',{'VE02'}),
    ('星际穿越 配乐 Zimmer','craft',{'QA12-DB02'}),
    ('快乐 漂流','examples',{'VC01','VC02'}),
    ('QA12-DP01','craft',{'QA12-DP01'}),
]

def regression_test(query,mode,expected):
    def run(self):
        result=recall.recall(query,mode=mode,limit=4,budget=20000)
        found={c['id'] for c in result['cards']}
        self.assertTrue(expected.intersection(found),(query,expected,found))
    return run

for i,(query,mode,expected) in enumerate(RETRIEVAL_CASES):
    setattr(ReleaseTests,'test_retrieval_'+str(i+1).zfill(2),regression_test(query,mode,expected))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReleaseTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'retrieval_cases':len(RETRIEVAL_CASES),'status':'passed' if result.wasSuccessful() else 'failed',
            'scope':'offline packaging, provenance separation and selected retrieval regressions only',
            'generated_dialogue_evaluated':False,'workbuddy_native_import_tested':False}
    (ROOT/'validation/offline-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
