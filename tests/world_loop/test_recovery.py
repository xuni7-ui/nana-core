import os,signal,subprocess,sys,json
from pathlib import Path
import pytest
from nana_core.continuity.world_loop.reference import open_runtime,configure
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority
from nana_core.continuity import ContinuityStore
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from .helpers import capture,policy

@pytest.mark.parametrize('cut',['calling','goal'])
def test_actual_sigkill_correlation_and_single_adopted_goal(tmp_path,cut):
    p=subprocess.run([sys.executable,'-m','tests.world_loop.crash_worker',str(tmp_path),cut],env={'PATH':os.defpath,'PYTHONPATH':str(Path('src').resolve())},capture_output=True,timeout=20)
    assert p.returncode==-signal.SIGKILL,p.stderr.decode()[:200]
    path=tmp_path/'subject'/'self.db';clock=VirtualClock()
    with provider_harness() as (transport,metrics),open_runtime(path,clock) as r:
        identity=r.identity_id;assert len(r.store.all('world_beliefs'))==1
        port=configure(r,tmp_path,transport,('synthetic://recover',),grant=False,planner=False)
        for _ in range(40):clock.advance(SECOND);r.step()
        assert r.work.world.world.view('device','available').state=='SUPPORTED_BELIEF'
        if cut=='calling':
            assert r.store.all('cognitive_requests')[0]['state']=='UNKNOWN' and metrics['calls']==0
            assert not r.store.all('goals')
        else:
            assert len(r.store.all('goals'))==1 and len(r.store.all('subject_goal_candidates'))==1
            assert r.store.all('open_concerns')[0]['state']=='ADOPTED'
            assert len([a for a in r.store.all('actions') if a['state']=='SUCCEEDED'])==1
            assert len(json.loads((tmp_path/'world'/'state.fixture.json').read_text())['effects'])==1
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()

@pytest.mark.parametrize('version',[7,8,12])
def test_forward_v13_with_old_ids_and_legacy_replay(tmp_path,version):
    path=tmp_path/'s'/'self.db'
    with ContinuityStore(path,VirtualClock(),schema_target=version) as s:
        from nana_core.actions import OperatorAuthority
        from nana_core.continuity.memory import MemoryService
        from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
        from nana_core.continuity.subject import SubjectLoop,SubjectInput
        from nana_core.continuity import IdentityService
        IdentityService(s,OperatorAuthority());memory=MemoryService(s);memory.entity('observer','PERSON')
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.migration',source_reference='old-history',source_kind='DIRECT_OBSERVATION'),text='Existing public development history',privacy_class='PUBLIC',observed_time_us=s.clock.utc_now_us()))
        mid=memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text='Existing public development history'))
        cycle=SubjectLoop(s,scopes=('world',)).run(SubjectInput(source_key='synthetic.old-history',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(mid,),privacy_class='PUBLIC',observed_at_us=s.clock.utc_now_us()))
        identity=s.identity['identity_id'];events=len(s.all('events'));prior_record_ids={r['record_id'] for r in s.all('continuity_records')}
    with ContinuityStore(path,VirtualClock(),schema_target=13) as s:
        assert s.identity['identity_id']==identity and len(s.all('events'))==events
        assert s.one('subject_cycles',cycle.cycle_id) and prior_record_ids=={r['record_id'] for r in s.all('continuity_records')}
        assert MemoryService(s).read(mid)['text']=='Existing public development history'
        assert not s.db.execute('PRAGMA foreign_key_check').fetchall()
        assert s.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]==43
        s.replay(tmp_path/'replay'/'self.db')
    with ContinuityStore(tmp_path/'replay'/'self.db',VirtualClock(),schema_target=13) as s:
        assert s.identity['identity_id']==identity and json.loads(s.one('core_meta','recovery_quarantine')['value_json'])


def test_v13_package_world_history_and_pending_call_not_execution_authority(tmp_path):
    from uuid import uuid4
    path=tmp_path/'s'/'self.db';clock=VirtualClock();target=str(uuid4());controller=PortableTransferAuthority()
    with provider_harness() as (transport,_),open_runtime(path,clock) as r:
        configure(r,tmp_path,transport,('synthetic://test',));mid=capture(r,'source',{'data':'public fixture'})
        cid=r.work.world.cognition.prepare('prepared','INTERPRET',(mid,));identity=r.identity_id
    with ContinuityStore(path,clock,schema_target=13) as s:
        package=SubjectPackageService(s,controller).export(tmp_path/'subject.zip',destination_id=target,source_commit='255ac99593219295b7126725bf6d51e1890051de',authority=controller)
    destination=PortableTransferAuthority(destination_id=target,destination_root=tmp_path/'imported')
    imported=SubjectPackageService.import_quarantined(package['path'],tmp_path/'imported',expected_sha256=package['sha256'],destination_id=target,authority=destination)
    with ContinuityStore(imported,clock,schema_target=13) as s:
        SubjectPackageService(s,destination).activate(transfer_id=package['manifest'].transfer_id,destination_id=target,authority=destination)
        assert s.one('cognitive_requests',cid)['state']=='PREPARED' and all(g['revoked'] for g in s.all('grants'))
    with open_runtime(imported,clock) as r,provider_harness() as (transport,metrics):
        assert r.identity_id==identity and r.work.world is None
        configure(r,tmp_path/'new-world',transport,('synthetic://test',),grant=False)
        assert r.store.one('cognitive_requests',cid)['state']=='UNKNOWN' and metrics['calls']==0


def test_post_judgment_context_failure_parks_without_repeated_cognition(tmp_path):
    from nana_core.contracts import CoreError
    class UnavailablePlanner:
        def plan(self,request):raise CoreError('INSUFFICIENT_CONTEXT_BUDGET')
    clock=VirtualClock()
    with provider_harness() as (transport,metrics),open_runtime(tmp_path/'s'/'self.db',clock) as r:
        configure(r,tmp_path,transport,('synthetic://recover',),planner=False)
        r.work.agency.policy.planner=UnavailablePlanner()
        mid=capture(r,'opportunity',{'opportunities':[{'topic':'recover','resource':'synthetic://recover','value':'HIGH'}]});r.work.world.observe(mid)
        for _ in range(12):clock.advance(SECOND);r.step()
        concern=r.store.all('open_concerns')[0]
        assert concern['state']=='PROPOSED' and not r.store.all('goals')
        assert len(r.store.all('subject_goal_candidates'))==1
        before=(len(r.store.all('subject_cycles')),metrics['calls'])
        for _ in range(8):clock.advance(SECOND);r.step()
        assert (len(r.store.all('subject_cycles')),metrics['calls'])==before
        assert r.store.db.execute("SELECT count(*) FROM events WHERE kind='world.concern_recovery_parked'").fetchone()[0]==1
