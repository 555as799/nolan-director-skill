"""Run the whole offline suite and write a machine-readable release report."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={'version':json.loads((ROOT/'release-files.json').read_text(encoding='utf-8'))['version'],
        'suite':'full_offline_suite',
        'skill_integrity_sha256':hashlib.sha256((ROOT/'skills/nolan-director/assets/integrity.json').read_bytes()).hexdigest(),
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'status':'passed' if result.wasSuccessful() else 'failed',
        'scope':'offline retrieval, attribution, source export boundaries, package integrity',
        'generated_dialogue_evaluated':False,'workbuddy_native_import_tested':False}
(ROOT/'validation').mkdir(exist_ok=True)
(ROOT/'validation/offline-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() else 1)
