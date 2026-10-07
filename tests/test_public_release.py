import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from export_source import selected_files, public_bytes, validate_test_evidence
from validate_library import validate
from build import public_skill_files
from audit_readiness import current_evaluation

class PublicReleaseTests(unittest.TestCase):
    def test_public_export_excludes_customer_files_and_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rules=json.loads((ROOT/'release-files.json').read_text(encoding='utf-8'))
            (root/'release-files.json').write_text(json.dumps(rules),encoding='utf-8')
            paths=['skills/nolan-director/SKILL.md','skills/nolan-director/projects/customer.md',
                   'skills/nolan-director/.env.local','skills/nolan-director/auth.key',
                   'private/notes.md','validation/trial-project-b/project.md',
                   'skills/nolan-director/.ENV.local','skills/nolan-director/Private/customer.md',
                   'skills/nolan-director/key.KEY']
            for name in paths:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test')
            chosen={p.relative_to(root).as_posix() for p in selected_files(root)}
            self.assertIn(paths[0],chosen)
            self.assertTrue(set(paths[1:]).isdisjoint(chosen))
            skill_files={p.relative_to(root).as_posix() for p in public_skill_files(root/'skills/nolan-director')}
            self.assertEqual(skill_files,{paths[0]})

    def test_source_export_requires_selected_evidence_and_trees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rules={'root_files':['README.md'],'selected_files':['evals/current/review.json'],
                   'trees':['tests'],'exclude_components':[],'exclude_suffixes':[]}
            (root/'release-files.json').write_text(json.dumps(rules),encoding='utf-8')
            (root/'README.md').write_text('readme',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Missing required'):
                selected_files(root,require_complete=True)
            (root/'tests').mkdir();review=root/'evals/current/review.json'
            review.parent.mkdir(parents=True);review.write_text('{}',encoding='utf-8')
            self.assertEqual(len(selected_files(root,require_complete=True)),2)

    def test_source_export_rejects_old_or_changed_test_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);skill=root/'skills/nolan-director';assets=skill/'assets'
            assets.mkdir(parents=True);(root/'validation').mkdir()
            (root/'release-files.json').write_text(json.dumps({'version':'4.1.2'}),encoding='utf-8')
            (assets/'library.json').write_text(json.dumps({'version':'4.1.2'}),encoding='utf-8')
            (skill/'SKILL.md').write_text('frozen runtime',encoding='utf-8')
            integrity=assets/'integrity.json'
            integrity.write_text(json.dumps({'files':[{'path':'SKILL.md','sha256':hashlib.sha256((skill/'SKILL.md').read_bytes()).hexdigest()}]}),encoding='utf-8')
            report={'version':'4.1.1','suite':'full_offline_suite','status':'passed',
                    'skill_integrity_sha256':hashlib.sha256(integrity.read_bytes()).hexdigest()}
            output=root/'validation/offline-tests.json'
            output.write_text(json.dumps(report),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'current release version'):validate_test_evidence(root)
            report['version']='4.1.2';output.write_text(json.dumps(report),encoding='utf-8')
            self.assertEqual(validate_test_evidence(root),'4.1.2')
            (skill/'SKILL.md').write_text('edited after test',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'changed after build'):validate_test_evidence(root)

    def test_public_tool_records_redact_home_paths_outside_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'evals/current/candidate.json';p.parent.mkdir(parents=True)
            sample={'assistant':'这个镜头我会留长一点。','tool_arguments':{'python':'C:/Users/Example/.cache/runtime/python.exe'},
                    'stderr':'C:\\Users\\Example\\.cache\\runtime\\engine.py'}
            p.write_text(json.dumps(sample,ensure_ascii=False),encoding='utf-8')
            clean=json.loads(public_bytes(p,root))
            self.assertEqual(clean['assistant'],sample['assistant'])
            self.assertNotIn('Example',json.dumps(clean))

    def test_current_review_requires_complete_matching_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'evals/release-4.1.2';folder.mkdir(parents=True)
            old=root/'evals/independent-trials/review.json';old.parent.mkdir()
            old.write_text('{"status":"passed"}',encoding='utf-8')
            self.assertFalse(current_evaluation(root,'4.1.2')['completed'])
            records={'requests.json':{'sessions':[{'id':'sample','turns':['一个镜头']} ]},
                     'baseline.json':[{'assistant':'第一版'}],
                     'candidate.json':[{'assistant':'第二版','files_read':[str(root/'skills/nolan-director/SKILL.md')]}],
                     'review.json':{'reviewed_turns':1,'finding':'limited sample'}}
            for name,data in records.items():
                (folder/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            mapping={'version':'4.1.2','review_status':'pending','evidence_public_sha256':{
                name:hashlib.sha256(public_bytes(folder/name,root)).hexdigest() for name in records}}
            path=folder/'version-mapping.json'
            path.write_text(json.dumps(mapping),encoding='utf-8')
            self.assertFalse(current_evaluation(root,'4.1.2')['completed'])
            mapping['review_status']='completed';path.write_text(json.dumps(mapping),encoding='utf-8')
            self.assertTrue(current_evaluation(root,'4.1.2')['completed'])
            self.assertFalse(current_evaluation(root,'4.1.2')['quality_acceptance_inferred'])
            # The published redacted copies retain the same verifiable evaluation binding.
            for name in records:
                payload=public_bytes(folder/name,root);(folder/name).write_bytes(payload)
            self.assertTrue(current_evaluation(root,'4.1.2')['completed'])
            (folder/'candidate.json').write_text('[{"assistant":"changed after review"}]',encoding='utf-8')
            self.assertFalse(current_evaluation(root,'4.1.2')['completed'])

    def test_audit_paths_are_portable_without_rewriting_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'evals/independent-trials/agent.json';p.parent.mkdir(parents=True)
            sample=[{'assistant':'我会先保留这句。','files_read':['C:/Users/Example/work/nolan-v4/skills/nolan-director/SKILL.md']}]
            p.write_text(json.dumps(sample,ensure_ascii=False),encoding='utf-8')
            clean=json.loads(public_bytes(p,root))
            self.assertEqual(clean[0]['assistant'],sample[0]['assistant'])
            self.assertEqual(clean[0]['files_read'],['skills/nolan-director/SKILL.md'])

    def test_library_rejects_false_first_person_and_broken_evidence(self):
        library=json.loads((ROOT/'skills/nolan-director/assets/library.json').read_text(encoding='utf-8'))
        validate(library)
        for change in ('speaker','source_ids','related_ids'):
            data=copy.deepcopy(library)
            card=next(c for c in data['cards'] if c['kind']=='experience')
            card[change]={'speaker':'Hans Zimmer','source_ids':['missing-source'],'related_ids':['missing-card']}[change]
            with self.assertRaises(ValueError):validate(data)

    def test_reviewed_expansion_remains_separate_from_original_proposals(self):
        library=json.loads((ROOT/'skills/nolan-director/assets/library.json').read_text(encoding='utf-8'))
        expansion=json.loads((ROOT/'research/expansion-agent.json').read_text(encoding='utf-8'))
        cards={c['id']:c for c in library['cards']}
        for original in expansion['cards']:
            c=cards[original['id']]
            for field in ('fact','inference','current_application','limits','speaker','locator','question_context'):
                self.assertEqual(c[field],original[field])
            self.assertEqual(c['kind']=='experience',c['first_person_eligibility']=='nolan_public_self_report')

    def test_core_navigation_resolves_to_actual_cards(self):
        import re
        core=ROOT/'skills/nolan-director/references/session-core.md'
        for name in re.findall(r'\]\((cards/[^)]+)\)',core.read_text(encoding='utf-8')):
            self.assertTrue((core.parent/name).is_file(),name)

    def test_same_experience_does_not_consume_multiple_retrieval_slots(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('dedup_recall',ROOT/'skills/nolan-director/scripts/recall.py')
        recall=importlib.util.module_from_spec(spec);spec.loader.exec_module(recall)
        result=recall.recall('Waterland 阅读 时间线',mode='experience',budget=18000)
        ids={c['id'] for c in result['cards']}
        self.assertEqual(len(ids & {'V4-N003','EXP-RD01'}),1)
        direct=recall.recall('EXP-RD01',mode='experience')
        self.assertEqual(direct['cards'][0]['id'],'EXP-RD01')
