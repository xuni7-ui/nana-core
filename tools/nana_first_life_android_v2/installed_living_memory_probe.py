"""Continue an already qualified installed DEV home; no repeated gateway/models.

External qualification only, not included in the ordinary runtime archive.
Uses the same Subject left by installed_note_recall_probe, adds synthetic source
consolidation/cold readback and validates current authority after withdrawal.
"""
import argparse
import json
import re
import sqlite3
from pathlib import Path
import sys
import time


def run(bundle,work,prior,case_id="beacon",require_body_free_usage=False,previous_bundle=None):
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}",case_id):raise ValueError("SYNTHETIC_CASE_ID_REQUIRED")
    if not __debug__:raise ValueError('QUALIFICATION_REQUIRES_ASSERTIONS')
    sys.dont_write_bytecode=True
    bundle=Path(bundle).resolve();work=Path(work).resolve();home=work/'life'
    report=json.loads(Path(prior).read_text())
    source=json.loads((bundle/'runtime.json').read_text())['source_commit']
    marker=json.loads((home/'nana-space-development.json').read_text())
    old_source=report.get('source_commit')
    if old_source!=source:
        if previous_bundle is None:raise ValueError('PREVIOUS_DEV_BUNDLE_REQUIRED')
        old=json.loads((Path(previous_bundle).resolve()/'runtime.json').read_text())
        new=json.loads((bundle/'runtime.json').read_text())
        keys=('schema_version','bundle_version','supported_platform','secret_binding_contract','archive_ingress_contract','bilibili_life_contract','platform_runtime_contract','private_context_contract')
        if old['source_commit']!=old_source or any(old.get(k)!=new.get(k) for k in keys) or not set(old['features'])<=set(new['features']):
            raise ValueError('DEV_UPGRADE_CONTRACT_MISMATCH')
    if (report.get('execution')!='ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD'
            or marker!={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':report.get('subject_id')}
            or Path(sys.prefix).resolve()!=bundle/'.venv'):
        raise ValueError('INSTALLED_DEV_BINDING_REQUIRED')
    sys.path.insert(0,str(bundle/'src'))
    from nana_core.life.application import LifeApplication
    from nana_core.life.live_api.supervisor import existing_identity
    from nana_core.life.durability import size_view,capacity_plan
    from nana_core.presence.authority import VirtualClock
    from nana_core.presence.resources import resource_state
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.cold_history import ColdHistoryService
    from nana_core.life.portable_runtime import owner_alive,status
    if owner_alive(status(home/'subject/self.db')):raise ValueError('STOPPED_DEV_OWNER_REQUIRED')
    identity,lineage,_=existing_identity(home)
    if (identity,lineage)!=(report['subject_id'],report['lineage_binding']):raise ValueError('SAME_SUBJECT_REQUIRED')
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
    clock=VirtualClock(max(time.time_ns()//1000,high))
    beacon='INSTALLED_DREAM_'+case_id.upper()
    text='SYNTHETIC installed original-source detail. '*24+beacon+' is Friday at the north gate.'
    query=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='world.social',
        task='SYNTHETIC query '+beacon,task_privacy_class='PROJECT',query_terms=(beacon,),max_input_tokens=16384)
    policy=ContextPolicy(policy_id='installed-dream',allowed_scopes=('project-work',),readable_privacy=('PROJECT',))
    with LifeApplication(home,clock=clock) as app:
        app.pause();store=app.runtime.store;calls=store.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]
        memory=MemoryService(store)
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.installed.dream',
            source_reference='installed-living-source.'+case_id,source_kind='DIRECT_OBSERVATION'),text=text,
            event_time_us=11,observed_time_us=app.runtime.clock.utc_now_us(),privacy_class='PROJECT'))
        mid=memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,
            epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,importance=.9,significance=.8))
        assembler=ContextAssembler(store,app.runtime.authority)
        before=assembler.assemble(query,policy,pinned_only=True,conversation_topic='daily')
        assert not any('Friday at the north gate' in b.data_json for b in before.blocks)
        maintenance=app.runtime.work.maintenance;maintenance.interval=1_000_000;maintenance.discover()
        summary=None
        # Drive persisted due times, as D does; do not assume a one-second
        # polling window can cover a paced backlog or shorten Runtime pacing.
        for _ in range(256):
            due=store.db.execute("SELECT min(due_at_us) FROM jobs WHERE work_kind='SCAN' AND state='WAITING'").fetchone()[0]
            # A long persisted idle interval still needs the original lease
            # heartbeats; jumping across its TTL is not a living Runtime.
            while clock.utc_now_us()<due:
                clock.advance(min(app.runtime.config.heartbeat_us,due-clock.utc_now_us()))
                app.runtime.lease.heartbeat()
            activity=maintenance.slice()
            if not activity or not activity.get('candidate_record_id'):continue
            rid=activity['candidate_record_id'];head,body=maintenance.candidate(rid)
            if mid not in body['memory_ids']:continue
            cycle=app.runtime.subject.run(SubjectInput(kind='WAKE',origin='SELF_WAKE',source_key='synthetic.installed.dream-review.'+rid,
                entity_id='project-user',scope='project-work',observed_at_us=head['created_at_us'],
                source_memory_ids=tuple(body['memory_ids']),memory_review_id=rid))
            summary=maintenance.adopt(rid,cycle);assert summary;break
        assert summary
        after=assembler.assemble(query,policy,pinned_only=True,conversation_topic='daily')
        assert any(b.kind=='CONSOLIDATED_RECALL' and 'Friday at the north gate' in b.data_json for b in after.blocks)
        cold=ColdHistoryService(store,app.runtime.authority)
        snapshot=cold.create(home/'backups'/('living-cold-'+case_id+'.sqlite'),authority=app.runtime.authority)
        assert cold.open(snapshot['path'],scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',)).memory(mid)['text']==text
        sizes=size_view(store)
        capacity=capacity_plan(app.config.model_copy(update={'state_capacity_policy':'DISK_AWARE'}),sizes,home)
        assert capacity['backup_status']=='HEADROOM_ONLY_NOT_BACKUP_OR_DR_QUALIFICATION'
        resources=resource_state(store,app.runtime.config)
        day=app.runtime.clock.utc_now_us()//86_400_000_000*86_400_000_000
        daily=store.db.execute('SELECT count(*) FROM cognitive_requests WHERE created_at_us>=?',(day,)).fetchone()[0]
        assert resources.calls==daily and resources.real_usage_reported_calls==0
        assert resources.fixture_usage_reported_calls+resources.usage_missing_or_invalid_calls==daily
        if require_body_free_usage:
            assert resources.fixture_usage_reported_calls==daily and resources.usage_missing_or_invalid_calls==0
            assert store.db.execute("SELECT count(*) FROM core_meta WHERE substr(key,1,16)='cognition.usage.'").fetchone()[0]==calls
        # Earlier source withdrawal can legitimately erase derived usage records;
        # missing is not zero tokens or a refunded reservation.
    clock.advance(72*3_600_000_000)
    with LifeApplication(home,clock=clock) as app:
        app.pause();store=app.runtime.store
        assert app.runtime.identity_id==identity
        assembler=ContextAssembler(store,app.runtime.authority)
        after=assembler.assemble(query,policy,pinned_only=True,conversation_topic='daily')
        assert any(b.kind=='CONSOLIDATED_RECALL' and 'Friday at the north gate' in b.data_json for b in after.blocks)
        cold=ColdHistoryService(store,app.runtime.authority)
        view=cold.open(snapshot['path'],scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
        assert view.memory(mid)['text']==text
        app.forget(mid)
        after=assembler.assemble(query,policy,pinned_only=True,conversation_topic='daily')
        assert not any('Friday at the north gate' in b.data_json for b in after.blocks)
        assert store.one('memories',summary)['lifecycle']=='DELETED'
        assert store.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]==calls
        if require_body_free_usage:
            assert store.db.execute("SELECT count(*) FROM core_meta WHERE substr(key,1,16)='cognition.usage.'").fetchone()[0]==calls
    assert existing_identity(home)[:2]==(identity,lineage)
    return {'execution':'ACTUAL_INSTALLED_DEV_CONTINUATION_NOT_CLOUD','source_commit':source,
        'subject_id':identity,'same_gateway_subject_and_lineage':True,'previous_source':old_source,'dev_upgrade_contract_checked':old_source!=source,'no_repository_pythonpath':True,
        'original_C_consolidation_changes_later_context':True,'virtual_72h_restart_and_source_withdrawal':True,
        'managed_cold_readback':True,'cold_initial_file_bytes':snapshot['initial_file_bytes'],
        'cold_file_bytes':snapshot['file_bytes'],'cold_allocated_bytes':snapshot['allocated_bytes'],
        'main_history_evicted':False,'total_disk_reclaimed':False,'capacity':capacity,
        'usage':resources.model_dump(mode='json'),'additional_model_calls':0,'real_provider_calls':0,
        'body_free_usage_required_and_preserved':require_body_free_usage,
        'physical_phone':'NOT_RUN','real_cross_day_companionship':'NOT_RUN','apk_rebuilt':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case-id',default='beacon');p.add_argument('--require-body-free-usage',action='store_true');p.add_argument('--previous-bundle',type=Path)
    args=p.parse_args();result=run(args.bundle,args.work,args.prior,args.case_id,args.require_body_free_usage,args.previous_bundle)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
