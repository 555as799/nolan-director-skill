"""Report evidence coverage and product readiness without treating packaging as quality."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def current_evaluation(root=ROOT, version=None):
    """Current evidence must be complete and bound to the actual reviewed records.

    This verifies evaluation completion, not a favorable review or product quality.
    Public-byte hashes remain verifiable after machine-path redaction during export.
    """
    from export_source import public_bytes
    version=version or read(root/'release-files.json')['version']
    folder=root/f'evals/release-{version}'
    names=('requests.json','baseline.json','candidate.json','review.json','version-mapping.json')
    missing=[name for name in names if not (folder/name).is_file()]
    result={'version':version,'status':'incomplete','completed':False,
            'directory':folder.relative_to(root).as_posix(),'missing_records':missing,
            'quality_acceptance_inferred':False,'scope':'independent_ai_proxy_comparison_not_customer_host_validation'}
    if missing:
        return result
    try:
        records={name:read(folder/name) for name in names}
    except (ValueError,OSError) as error:
        result['issue']='Unreadable evaluation record: '+type(error).__name__
        return result
    mapping=records['version-mapping.json']
    if not isinstance(mapping,dict) or mapping.get('version')!=version:
        result['issue']='Version mapping does not identify this release'
        return result
    if mapping.get('review_status')!='completed':
        result['issue']='Current comparison review is not marked completed'
        return result
    expected=mapping.get('evidence_public_sha256',{})
    if not isinstance(expected,dict):
        result['issue']='Invalid reviewed-record hashes'
        return result
    mismatches=[]
    for name in names[:-1]:
        if not records[name] or not isinstance(records[name],(dict,list)):
            mismatches.append(name)
        elif expected.get(name)!=hashlib.sha256(public_bytes(folder/name,root)).hexdigest():
            mismatches.append(name)
    if mismatches:
        result['issue']='Missing or mismatched reviewed-record hashes'
        result['mismatched_records']=mismatches
        return result
    result.update(status='completed',completed=True,
                  records=[(folder/name).relative_to(root).as_posix() for name in names])
    return result

def audit():
    library = read(ROOT/'skills/nolan-director/assets/library.json')
    cards = library['cards']
    software = read(ROOT/'validation/offline-tests.json')
    behavior = read(ROOT/'evals/behavior-cases.json')
    old_training = read(ROOT/'data/prior-training-summary.json')
    current=current_evaluation()
    host_feedback_path = ROOT/'validation/host-feedback-summary.json'
    host_feedback = read(host_feedback_path) if host_feedback_path.is_file() else {}
    sources = library['sources']
    history = [c for c in cards if c['kind']=='experience']
    checked = [c for c in cards if c['source_review'].startswith('relevant_passage_checked_')]
    indexed = {s for c in cards for s in c['source_ids']}
    url_counts = Counter(u.rstrip('/') for s in sources.values() for u in s.get('urls',[]))
    trials=[]
    for name in ('agent-a.json','agent-b.json'):
        path=ROOT/'evals/independent-trials'/name
        if path.is_file():
            rows=read(path)
            trials.append({'record':path.relative_to(ROOT).as_posix(),
                           'sessions':len({r['session'] for r in rows}),'assistant_turns':len(rows)})
    reviews=[]
    for name in ('review.json','review-b.json'):
        path=ROOT/'evals/independent-trials'/name
        if path.is_file():
            reviews.append(path.relative_to(ROOT).as_posix())
    report = {
        'stage':'release_candidate',
        'ready_for_final_release':False,
        'date':datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
        'version':read(ROOT/'release-files.json')['version'],
        'customer_host_feedback':host_feedback,
        'counts':{
            'cards':len(cards),
            'card_kinds':dict(Counter(c['kind'] for c in cards)),
            'source_registry_entries':len(sources),
            'source_entries_referenced_by_cards':len(indexed),
            'registered_source_entries_without_card_links':sorted(set(sources)-indexed),
            'film_navigation_entries':sum(c['id'].startswith('F') for c in cards),
            'structured_nolan_self_report_candidates':len(history),
            'sources_supporting_structured_nolan_self_reports':sorted({s for c in history for s in c['source_ids']}),
            'v4_cards_with_relevant_passage_review':len(checked),
            'v4_cards_with_inherited_review_only':len(cards)-len(checked),
            'original_example_cards':sum(c['kind']=='example' for c in cards),
            'v4_behavior_cases_prepared':len(behavior['cases']),
            'v4_behavior_cases_executed':0,
            'independent_trial_sessions':sum(t['sessions'] for t in trials),
            'independent_trial_assistant_turns':sum(t['assistant_turns'] for t in trials),
        },
        'claims_not_supported':[
            'Card count equals independent real Nolan experiences',
            'Every registered source has been independently reverified in full',
            '13 film entries are 13 films studied shot by shot',
            'The new corpus has been used to train model weights',
            'Passing offline tests proves conversational or creative quality',
            'The current revision has passed customer WorkBuddy creative acceptance',
            'Positive proxy-agent reviews outweigh a real customer-host failure',
        ],
        'software_validation':software,
        'independent_dialogue_trials':{
            'records':trials,'reviews':reviews,
            'release_scope':'historical_trials_predating_current_revision',
            'type':'independent_ai_generations_and_separate_ai_review',
            'limits':'small samples; logical sessions share one agent context per cohort; no human blind ratings, voice evaluation, customer-host model comparison or general accuracy claim',
        },
        'current_revision_dialogue_evaluation':current,
        'prior_training_record':{
            'source':'user_supplied_archive_not_reproduced_this_session',
            'runs':old_training['training_runs'],
            'data':old_training['training_data'],
            'new_training_run_this_session':False,
        },
        'coverage_limits':[
            'Structured self-report cards cover only a subset of the source registry; other cards mix research summaries and applications.',
            'No complete verified reading history or complete film/scene analysis is available.',
            'New passage-reviewed cards overlap with old concepts; the current build is not a corpus deduplication study.',
            'Independent AI trials were run; no held-out old/new comparison on the customer model has been run.',
            'MIT and NOTICE define authored-content scope; third-party works remain separately attributed. Publication status is separate from creative acceptance.',
        ],
        'duplicate_source_urls':{u:n for u,n in url_counts.items() if n>1},
        'acceptance_gates':{
            'baseline_migration':'passed',
            'offline_retrieval_and_packaging':software['status'],
            'source_by_source_evidence_audit':'incomplete',
            'corpus_expansion':{'added_cards_with_overlap':len(cards)-library['baseline_cards'],
                                'inherited_cards_rechecked':len(read(ROOT/'research/primary-refinements.json')['reviewed_existing'])},
            'model_parameter_training':'not_done_not_required_for_current_skill_scope',
            'generated_dialogue_and_creative_evaluation':current['status'],
            'historical_ai_trial_evidence':'available' if reviews else 'not_run',
            'workbuddy_native_customer_workflow':'4.1.0_and_4.1.2_activation_observed_dialogue_rejected;4.1.3_unverified',
            'open_source_release_preparation':'prepared' if all((ROOT/p).is_file() for p in ('LICENSE','NOTICE.md','README.en.md','.github/workflows/validate.yml')) else 'incomplete',
        },
    }
    (ROOT/'validation/product-readiness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'stage':report['stage'],'counts':report['counts'],'gates':report['acceptance_gates']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    audit()
