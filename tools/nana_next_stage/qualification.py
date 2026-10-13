"""Fixture qualification results; real dependencies cannot become PASS here."""
from pathlib import Path
import json
from nana_core.storage import Store, canonical
from .fixtures import DATASET, seed_phase_a, capture
from .memory import PhaseAPrototype, ZERO
from .semantic import prepare, evaluate

GATES = {
    'N01': ('Identity restart/replay', 'READY_OFFLINE', 'Actual model/host/identity adoption'),
    'N02': ('Epistemic/provenance separation', 'READY_OFFLINE', 'Authorized real legacy sample'),
    'N03': ('Temporal correction and conflicting statements', 'READY_OFFLINE', 'Real semantic extraction'),
    'N04': ('SelfFrame and self-change candidate only', 'PARTIAL', 'Approved identity-growth commit/rollback interface'),
    'N05': ('Scoped synthetic relationship persistence', 'PARTIAL', 'Real entity binding and split protocol'),
    'N06': ('OFFERED commitment persistence only', 'PARTIAL', 'Accept/renegotiate/fulfilment protocol and Goal linkage'),
    'N11': ('Retrieval suppression and fixture checkpoint replay', 'PARTIAL', 'Physical purge and authenticated revocation/backup anchors'),
    'N12': ('Observation coverage contract', 'READY_OFFLINE', 'Real source coverage/freshness measurement'),
    'N13': ('Bounded context and stale/withdrawal checks', 'PARTIAL', 'Model tokenizer and semantic context quality'),
    'E12': ('Original proposal plus behavior and Phase A understanding', 'READY_OFFLINE', 'Two authorized distinct real development models'),
}


def matrix(tests=None):
    """No fixture result can authorize a real gate or claim real execution."""
    return {'schema_version':1,'provenance':'SYNTHETIC_FIXTURE',
        'gates':{key:{'scope':label,'readiness':readiness,
                    'real_acceptance':'NOT_RUN_REAL_DEPENDENCY','remaining':remaining}
                 for key,(label,readiness,remaining) in GATES.items()},
        'tests':tests or {'status':'SEE_TEST_EVIDENCE'},'E12':'NOT_RUN',
        'SMALL_REAL_MEMORY_SHADOW':'NOT_RUN_REAL_DEPENDENCY',
        'FIRST_REAL_ASTRBOT_SHADOW':'UNCHANGED_OTHER_EXECUTOR',
        'ready_to_continue_after_first_real_shadow':True,
        'meaning':'Offline preparation available; does not grant real-data/model/production access.'}


def qualify(output):
    root=Path(output);root.mkdir(parents=True,exist_ok=False)
    path=root/'fixture-memory.db'
    checks={}
    with Store(path) as store:
        proto=PhaseAPrototype(store);report,ids=seed_phase_a(proto)
        identity=store.identity;times={e['event_id']:e['occurred_at_us'] for e in store.all('events')}
        checks['import_count']=len(proto.memories())==report['input_count']==6
        checks['record_rejections_reported']=len(report['results'])==6
        duplicate=proto.import_capture(capture())
        checks['dedup']=all(r['status']=='DUPLICATE' for r in duplicate['results']) and len(proto.memories())==6
        context=proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',max_chars=16000)
        checks['context_ready_and_verified']=context['manifest']['status']=='READY' and proto.verify_context(context)
        checks['partial_coverage_honest']=context['manifest']['observation_coverage'][0]['completeness']=='PARTIAL'
        checks['correction']=proto.assessments(DATASET,as_of='2026-09-04T10:00:00+00:00')[0]['current_claim_ids']==['synthetic:new-preference']
        frame=proto.self_frame()
        checks['offered_commitment_not_accepted']=frame['commitments'][0]['status']=='OFFERED'
        checks['self_growth_not_applied']=frame['identity_growth_applied'] is False
        store.backup(root/'stale-backup.db')
        checkpoint=proto.withdraw(ids['new-preference'])
        checks['no_old_belief_resurrection']=proto.assessments(DATASET,as_of='2026-09-04T10:00:00+00:00')[0]['status']=='UNASSESSED_WITHDRAWN_SUPPORT'
        checks['withdrawn_dependent_commitment_hidden']=not proto.self_frame()['commitments']
        checks['original_evidence_retained_not_purged']=bool(store.artifact(store.event(ids['new-preference'])['artifact_id']))
        checks['original_times_preserved']=all(store.event(k)['occurred_at_us']==v for k,v in times.items())
        checks['no_execution_objects']=all(not store.all(t) for t in ZERO)
        store.backup(root/'backup.db');store.replay(root/'replay.db')
    with Store(path) as store:
        proto=PhaseAPrototype(store)
        checks['restart_same_identity']=store.identity==identity
        checks['restart_same_relationship']=proto.self_frame()['relationships']==frame['relationships']
        persisted_offer=proto._get('commitment:synthetic:reading-promise')
        checks['restart_offer_record_preserved']=(persisted_offer['status']=='OFFERED'
            and persisted_offer['due_at']=='2026-09-05T10:00:00+00:00')
        checks['restart_withdrawn_source_hidden']=ids['new-preference'] not in proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',max_chars=16000)['manifest']['selected_memory_ids']
    for name in ('stale-backup.db','backup.db','replay.db'):
        with Store(root/name) as store:
            proto=PhaseAPrototype(store);proto.apply_withdrawal_checkpoint(checkpoint)
            checks[name+'_quarantined_no_resurrection']=(store.identity==identity
                and store.one('core_meta','recovery_quarantine')['value_json']=='true'
                and store.one('memory_items',ids['new-preference'])['status']=='RETRACTED'
                and not proto.self_frame()['commitments'] and all(not store.all(t) for t in ZERO))
    prepare(root/'e12-snapshot')
    semantic=evaluate(root/'e12-snapshot',root/'e12-not-run')
    checks['e12_not_run_zero_calls']=semantic['E12']=='NOT_RUN' and semantic['real_model_attempts']==0
    report=matrix()
    report.update(engineering_gate='PASS' if all(checks.values()) else 'FAIL',
        checks=checks,identity=identity,fixture_record_count=6,duplicate_count=6,
        original_context=context,physical_purge='NOT_IMPLEMENTED',real_model_calls=0,
        real_memory_records_read=0,production_operations=0)
    (root/'qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report
