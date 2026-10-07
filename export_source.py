"""Export only the public release allowlist, never workspace or training archives."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parent

def selected_files(root=ROOT, require_complete=False):
    rules=json.loads((root/'release-files.json').read_text(encoding='utf-8'))
    declared=rules['root_files']+rules['selected_files']
    for name in declared+rules['trees']:
        if Path(name).is_absolute() or not (root/name).resolve().is_relative_to(root.resolve()):
            raise ValueError('Release path escaped repository: '+name)
    if require_complete:
        missing=[p for p in declared if not (root/p).is_file() or (root/p).is_symlink()]
        missing.extend(p for p in rules['trees'] if not (root/p).is_dir() or (root/p).is_symlink())
        if missing:
            raise ValueError('Missing required release files or trees: '+str(missing))
    candidates=[root/p for p in declared]
    for folder in rules['trees']:
        candidates.extend((root/folder).rglob('*'))
    allowed=[]
    for p in candidates:
        if not p.is_file() or p.is_symlink():
            continue
        rel=p.relative_to(root)
        if not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Release path escaped repository')
        excluded={part.casefold() for part in rules['exclude_components']}
        suffixes={suffix.casefold() for suffix in rules['exclude_suffixes']}
        if any(part.casefold() in excluded or part.casefold().startswith('.env') for part in rel.parts) or p.suffix.casefold() in suffixes:
            continue
        allowed.append(p)
    if require_complete:
        filtered=set(declared)-{p.relative_to(root).as_posix() for p in allowed}
        if filtered:
            raise ValueError('Required release files were excluded: '+str(sorted(filtered)))
    return sorted(set(allowed))

def public_bytes(p,root=ROOT):
    """Redact machine-specific paths only; keep actual dialogue and failures intact."""
    rel=p.relative_to(root).as_posix()
    if rel.startswith('evals/') and p.suffix=='.json':
        data=json.loads(p.read_text(encoding='utf-8'))
        prefixes=[(root.as_posix()+'/', ''),(root.parent.as_posix(),'<workspace>')]
        if isinstance(data,dict):
            python_path=data.get('model_environment',{}).get('python_used')
            if python_path:prefixes.insert(0,(python_path.replace('\\','/'),'<python>'))
        def clean(value):
            if isinstance(value,list):
                return [clean(v) for v in value]
            if isinstance(value,dict):
                result={k:clean(v) for k,v in value.items()}
                if 'files_read' in result:
                    result['files_read']=[v.replace('\\','/').split('/nolan-v4/')[-1]
                                          for v in result['files_read']]
                return result
            if isinstance(value,str):
                for old,new in prefixes:
                    value=value.replace(old,new).replace(old.replace('/','\\'),new)
                # Tool records can contain interpreter paths outside this repository.
                # Preserve the machine-relative suffix without publishing a Windows login.
                value=re.sub(r'(?i)\b[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s\"\'<>]+',
                             '<user-home>',value)
                return value
            return value
        return (json.dumps(clean(data),ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    return p.read_bytes()

def validate_test_evidence(root=ROOT):
    report=json.loads((root/'validation/offline-tests.json').read_text(encoding='utf-8'))
    version=json.loads((root/'release-files.json').read_text(encoding='utf-8'))['version']
    if report['status']!='passed':
        raise ValueError('Run passing offline tests before exporting')
    if report.get('suite')!='full_offline_suite' or report.get('version')!=version:
        raise ValueError('Run the full offline suite for the current release version')
    integrity=root/'skills/nolan-director/assets/integrity.json'
    if not integrity.is_file() or report.get('skill_integrity_sha256')!=hashlib.sha256(integrity.read_bytes()).hexdigest():
        raise ValueError('Skill changed after offline validation; rebuild and rerun the full suite')
    skill=root/'skills/nolan-director'
    for row in json.loads(integrity.read_text(encoding='utf-8'))['files']:
        path=skill/row['path']
        if not path.resolve().is_relative_to(skill.resolve()) or not path.is_file() or path.is_symlink():
            raise ValueError('Invalid file in tested Skill manifest: '+row['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Skill file changed after build: '+row['path'])
    library=json.loads((root/'skills/nolan-director/assets/library.json').read_text(encoding='utf-8'))
    if library.get('version')!=version:
        raise ValueError('Build the current release version before exporting')
    return version

def export():
    version=validate_test_evidence()
    target=ROOT/f'dist/nolan-director-{version}-source.zip'
    files=selected_files(require_complete=True)
    from audit_readiness import current_evaluation
    if not current_evaluation(ROOT,version)['completed']:
        raise ValueError('Complete and bind the current revision comparison review before exporting')
    manifest={'version':version,'note':'Evaluation machine paths are redacted in public copies. Source hashes preserve the link to the original reviewed records; public hashes verify the distributed files. Dialogue wording and observed failures are otherwise unchanged.','files':[]}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(files)):
            relative=p.relative_to(ROOT).as_posix()
            payload=public_bytes(p)
            original=p.read_bytes()
            manifest['files'].append({'path':relative,'source_sha256':hashlib.sha256(original).hexdigest(),
                                      'public_sha256':hashlib.sha256(payload).hexdigest(),
                                      'path_redacted':json.loads(payload)!=json.loads(original) if p.suffix=='.json' and relative.startswith('evals/') else False})
            z.writestr(f'nolan-director-{version}-source/'+relative,payload)
        z.writestr(f'nolan-director-{version}-source/PUBLIC-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip():
            raise ValueError('Source ZIP CRC failed')
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('Duplicate source paths')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'dist').glob('*.zip'))}
    (ROOT/'dist/SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_archive':str(target),'files':len(set(files))+1,'bytes':target.stat().st_size},ensure_ascii=False))

if __name__=='__main__':
    export()
