"""Enforce research attribution and data integrity before generating runtime assets."""
from pathlib import Path
import json
import re

def validate(library):
    cards, sources = library['cards'], library['sources']
    ids = {c['id'] for c in cards}
    if len(ids) != len(cards):
        raise ValueError('Duplicate card IDs')
    for c in cards:
        for key in ('id','title','kind','evidence_type','source_file','source_review','text'):
            if not isinstance(c.get(key),str) or not c[key].strip():
                raise ValueError(f'{c.get("id")}: missing {key}')
        if not re.fullmatch(r'[A-Za-z0-9-]+',c['id']):
            raise ValueError('Unsafe card ID')
        if c['kind'] not in ('experience','collaborator','craft','example'):
            raise ValueError('Unknown evidence kind')
        if not isinstance(c['source_ids'],list) or set(c['source_ids'])-sources.keys():
            raise ValueError(f'{c["id"]}: unresolved sources')
        if set(c.get('related_ids',[]))-ids:
            raise ValueError(f'{c["id"]}: unresolved related cards')
        if c['kind'] in ('experience','collaborator'):
            if not c.get('fact') or not c.get('speaker') or not c['source_ids']:
                raise ValueError('Experience needs speaker, fact and source')
            if (c['speaker']=='Christopher Nolan') != (c['kind']=='experience'):
                raise ValueError('Personal experience attribution mismatch')
        if c['source_review'].startswith('relevant_passage_checked_'):
            if not c.get('locator') and not c.get('review_record'):
                raise ValueError(f'{c["id"]}: reviewed fact needs passage locator')
        if c.get('first_person_eligibility')=='nolan_public_self_report' and c['kind']!='experience':
            raise ValueError('Collaborator incorrectly eligible for personal recollection')
    return {'cards':len(cards),'sources':len(sources),'status':'passed'}

if __name__=='__main__':
    p=Path(__file__).resolve().parent/'skills/nolan-director/assets/library.json'
    print(json.dumps(validate(json.loads(p.read_text(encoding='utf-8')))))
