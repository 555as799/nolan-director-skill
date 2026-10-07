"""Canonical evidence and scene-dependency integration, without a model API."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/nolan-director'
spec = importlib.util.spec_from_file_location('scene_engine',SKILL/'scripts/director_engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def scene():
    new_source = next(s for s in engine.load_corpus()['sources'] if s.startswith('EXP-S-'))
    return {
        'facts':[{'id':'F1','text':'作者确认房门锁着','source':'作者','status':'confirmed'},
                 {'id':'F2','text':'作者确认次日晴朗','source':'作者','status':'confirmed'}],
        'decisions':[{'id':'D1','text':'保留开门失败动作','status':'adopted','dependencies':['F1']}],
        'beats':[{'id':'B1','purpose':'建立阻力','action':'拉门','change':'发现门锁','fact_refs':['F1'],'dependencies':['D1']},
                 {'id':'B2','purpose':'改变办法','action':'找钥匙','change':'找到钥匙','fact_refs':['F1'],'dependencies':[]},
                 {'id':'B3','purpose':'独立场景','action':'次日出门','change':'走入阳光','fact_refs':['F2'],'dependencies':[]}],
        'shots':[{'id':'S1','beat_id':'B1','purpose':'看清失败','action':'拉动门把','camera':'侧面中景','sound':'门锁声','fact_refs':['F1'],'dependencies':[]},
                 {'id':'S2','beat_id':'B2','purpose':'承接失败','action':'取出钥匙','camera':'手部近景','sound':'钥匙声','fact_refs':['F1'],'dependencies':['S1']},
                 {'id':'S3','beat_id':'B3','purpose':'新的日常','action':'走进院子','camera':'固定全景','sound':'鸟鸣','fact_refs':['F2'],'dependencies':[]}],
        'transitions':[{'from':'S1','to':'S2','cut_reason':'动作改变','picture_anchor':'手','sound_bridge':'钥匙声'},
                       {'from':'S2','to':'S3','cut_reason':'次日省略','picture_anchor':'门','sound_bridge':'鸟鸣先入'}],
        'claims':[{'text':'引用公开研究材料','type':'source_fact','source_ids':[new_source]}]
    }


class SceneIntegrationTests(unittest.TestCase):
    def test_new_canonical_source_is_valid(self):
        result=engine.diagnose(scene())
        self.assertTrue(result['valid'],result['errors'])

    def test_unknown_source_is_rejected(self):
        plan=scene();plan['claims'][0]['source_ids']=['NO-SUCH-SOURCE']
        self.assertIn('unknown_source',{e['code'] for e in engine.diagnose(plan)['errors']})

    def test_unadopted_decision_cannot_be_fixed_dependency(self):
        for status in ('proposed','rejected'):
            with self.subTest(status=status):
                plan=scene();plan['decisions'][0]['status']=status
                self.assertIn('unadopted_dependency',{e['code'] for e in engine.diagnose(plan)['errors']})

    def test_unconfirmed_fact_is_not_fixed_constraint(self):
        plan=scene();plan['facts'][0]['status']='proposed'
        self.assertIn('unconfirmed_fact',{e['code'] for e in engine.diagnose(plan)['errors']})

    def test_action_dependency_propagates_locally_without_mutation(self):
        plan=scene();before=copy.deepcopy(plan)
        result=engine.affected(plan,['S1'])
        self.assertEqual(result['affected_nodes'],['S2'])
        self.assertNotIn('S3',result['affected_nodes'])
        self.assertEqual(len(result['affected_transitions']),2)
        self.assertEqual(plan,before)

    def test_fact_and_decision_dependencies_propagate_transitively(self):
        result=engine.affected(scene(),['F1'])
        self.assertEqual(set(result['affected_nodes']),{'D1','B1','B2','S1','S2'})
        self.assertNotIn('S3',result['affected_nodes'])

    def test_unknown_changed_id_does_not_expand_other_shots(self):
        result=engine.affected(scene(),['MISSING'])
        self.assertEqual(result['unknown_changed_ids'],['MISSING'])
        self.assertEqual(result['affected_nodes'],[])

    def test_legacy_recall_sees_new_experience(self):
        result=engine.recall('EXP-TE01',mode='conversation',focus=['camera'],limit=2)
        self.assertEqual(result['mode'],'experience')
        self.assertEqual(result['cards'][0]['id'],'EXP-TE01')

    def test_legacy_examples_remain_separate(self):
        result=engine.recall('胶片 颗粒',mode='examples',limit=3)
        self.assertTrue(result['cards'])
        self.assertTrue(all(c.get('kind')=='example' for c in result['cards']))

    def test_legacy_focus_and_serialized_budget(self):
        result=engine.recall('视点',focus=['camera'],budget=1000)
        self.assertTrue(result['cards'])
        self.assertLessEqual(len(json.dumps(result,ensure_ascii=False,separators=(',',':'))),1000)

    def test_legacy_cli_output_honors_budget(self):
        process=subprocess.run([sys.executable,'-X','utf8',str(SKILL/'scripts/director_engine.py'),
            'recall','--query','EXP-TE01','--mode','conversation','--budget','1000'],
            capture_output=True,text=True,encoding='utf-8',check=True)
        self.assertLessEqual(len(process.stdout.strip()),1000)
        self.assertEqual(json.loads(process.stdout)['cards'][0]['id'],'EXP-TE01')

    def test_bad_reference_types_report_diagnostics(self):
        plan=scene();plan['shots'][0]['fact_refs']=[{}];plan['shots'][0]['dependencies']=[[]]
        plan['transitions'][0]['from']={};plan['claims'][0]['source_ids']=[{}]
        codes={e['code'] for e in engine.diagnose(plan)['errors']}
        self.assertTrue({'invalid_reference','invalid_dependency','invalid_transition_reference','invalid_source_reference'} <= codes)

    def test_invalid_duration_target_is_diagnostic(self):
        plan=scene()
        for shot in plan['shots']:shot['duration_seconds']=2
        plan['target_duration_seconds']='six'
        self.assertIn('invalid_target_duration',{e['code'] for e in engine.diagnose(plan)['errors']})

    def test_malformed_affected_dependencies_raise_clear_error(self):
        plan=scene();plan['shots'][0]['dependencies']={}
        with self.assertRaisesRegex(ValueError,'dependencies/fact_refs'):
            engine.affected(plan,['S1'])

    def test_both_retrieval_clis_emit_utf8_under_legacy_codepage(self):
        env={**os.environ,'PYTHONIOENCODING':'cp1252','PYTHONUTF8':'0'}
        commands=[['recall.py','--query','演员排练','--mode','experience'],
                  ['director_engine.py','recall','--query','演员排练','--mode','conversation']]
        for script,*arguments in commands:
            with self.subTest(script=script):
                completed=subprocess.run([sys.executable,str(SKILL/'scripts'/script),*arguments],
                    env=env,capture_output=True,check=True)
                result=json.loads(completed.stdout.decode('utf-8'))
                self.assertTrue(result['cards'])
                self.assertTrue(any(any('\u3400'<=char<='\u9fff' for char in card.get('title',''))
                                    for card in result['cards']))

    def test_scene_json_stdin_is_utf8_under_legacy_codepage(self):
        env={**os.environ,'PYTHONIOENCODING':'cp1252','PYTHONUTF8':'0'}
        plan=scene();plan['shots'][0]['dependencies'].append('不存在的依赖')
        completed=subprocess.run([sys.executable,str(SKILL/'scripts/director_engine.py'),'validate','-'],
            input=json.dumps(plan,ensure_ascii=False).encode('utf-8'),env=env,capture_output=True)
        self.assertEqual(completed.returncode,2)
        result=json.loads(completed.stdout.decode('utf-8'))
        self.assertIn('不存在的依赖',[e['detail'] for e in result['errors']])


if __name__=='__main__':
    unittest.main()
