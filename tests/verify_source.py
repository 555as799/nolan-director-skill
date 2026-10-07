"""Build and test the exported source in an isolated directory, not its original workspace."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
version=json.loads((ROOT/'release-files.json').read_text(encoding='utf-8'))['version']
archive=ROOT/f'dist/nolan-director-{version}-source.zip'
steps=[]
with tempfile.TemporaryDirectory(prefix='nolan_source_') as tmp:
    target=Path(tmp).resolve()
    with zipfile.ZipFile(archive) as z:
        prefix=f'nolan-director-{version}-source/'
        manifest=json.loads(z.read(prefix+'PUBLIC-MANIFEST.json'))
        for entry in manifest['files']:
            if hashlib.sha256(z.read(prefix+entry['path'])).hexdigest()!=entry['public_sha256']:
                raise ValueError('Public source checksum mismatch: '+entry['path'])
        for entry in z.namelist():
            if not (target/entry).resolve().is_relative_to(target):
                raise ValueError('Unsafe archive path')
        z.extractall(target)
    repo=target/f'nolan-director-{version}-source'
    for script in ('build.py','tests/run_all.py','audit_readiness.py','export_source.py'):
        done=subprocess.run([sys.executable,'-X','utf8',script],cwd=repo,capture_output=True,text=True,encoding='utf-8',timeout=120)
        steps.append({'command':'python '+script,'exit_code':done.returncode})
        if done.returncode:
            print(done.stdout);print(done.stderr);raise SystemExit(done.returncode)
    expected=json.loads((ROOT/'skills/nolan-director/assets/library.json').read_text(encoding='utf-8'))['content_sha256']
    actual=json.loads((repo/'skills/nolan-director/assets/library.json').read_text(encoding='utf-8'))['content_sha256']
    if actual!=expected: raise ValueError('Relocated build changed research content')
    report={'status':'passed','version':version,'steps':steps,'same_corpus_sha256':actual,
            'input_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'offline_tests':json.loads((repo/'validation/offline-tests.json').read_text(encoding='utf-8')),
            'scope':'isolated source extraction/build/test/export; not a WorkBuddy client test'}
(ROOT/'validation/source-rebuild.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
