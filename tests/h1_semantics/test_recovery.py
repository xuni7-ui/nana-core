import json,os,signal,subprocess,sys
from pathlib import Path
import pytest
from nana_core.continuity.world_loop.reference import open_runtime,configure,context_policy
from nana_core.continuity.world_loop.semantic_harness import semantic_harness
from nana_core.continuity.world_loop.semantics import MediaSemanticService
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND

@pytest.mark.parametrize('cut',['decode','calling','proposed','belief','cycle'])
def test_actual_h1_sigkill_reopen_no_duplicate_provider_belief_cycle_or_goal(tmp_path,cut):
    p=subprocess.run([sys.executable,'-m','tests.h1_semantics.crash_worker',str(tmp_path),cut],capture_output=True,env={'PATH':os.defpath,'PYTHONPATH':str(Path('src').resolve())},timeout=25)
    assert p.returncode==-signal.SIGKILL,p.stderr.decode()[:800]
    clock=VirtualClock()
    with semantic_harness() as (t,state),open_runtime(tmp_path/'subject'/'self.db',clock) as r:
        configure(r,tmp_path,t,('synthetic://public',),grant=False,planner=False)
        rows=r.store.db.execute("SELECT * FROM cognitive_requests WHERE request_key='media:recover'").fetchall()
        s=MediaSemanticService(r.work.world.cognition)
        if cut=='decode':assert not rows
        elif cut=='calling':
            assert rows[0]['state']=='UNKNOWN';assert s.execute(rows[0]['request_id'])['replayed']
        elif cut in {'proposed','belief'}:
            cid=rows[0]['request_id'];assert rows[0]['state']=='PROPOSED'
            first=s.ground(cid,entity_id='device');second=s.ground(cid,entity_id='device');assert first==second
            assert len(first['belief_ids'])==len(set(first['belief_ids']))
            assert len([x for x in r.store.all('continuity_records') if x['record_kind']=='COGNITION_PROPOSAL'])==1
        else:
            before=len(r.store.all('subject_cycles'));assert before==1
            for _ in range(20):clock.advance(SECOND);r.step()
            assert len(r.store.all('subject_cycles'))==before
            assert r.store.all('open_concerns')[0]['state']=='DEFERRED'
        assert state['calls']==0
        assert not r.store.all('actions') and not r.store.all('goals')
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_h1_subject_package_retains_interpretation_not_provider_or_execution_handles(tmp_path):
    from uuid import uuid4
    from nana_core.continuity import ContinuityStore
    from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority
    from nana_core.continuity.world_loop.samples import media_samples
    from nana_core.continuity.world_loop.world import WorldModel
    from tests.h1_semantics.test_grounding import ingest
    clock=VirtualClock();path=tmp_path/'s'/'self.db';destination=str(uuid4());authority=PortableTransferAuthority()
    with semantic_harness() as (t,_),open_runtime(path,clock) as r:
        session=CognitionSession(r,t,context_policy());s=MediaSemanticService(session)
        raw=media_samples()['IMAGE'];mid=ingest(r,'IMAGE',raw);cid=s.prepare('portable',mid,raw);s.execute(cid);result=s.ground(cid,entity_id='device')
        pending=s.prepare('pending',mid,raw)
        with r.store.transaction('test.portable_calling') as tx:tx.update('cognitive_requests',pending,state='CALLING')
        identity=r.identity_id
    with ContinuityStore(path,clock,schema_target=13) as store:
        package=SubjectPackageService(store,authority).export(tmp_path/'h1.zip',destination_id=destination,source_commit='dcaf30fe1581c5fff19ab302a83b4b56e69487a0',authority=authority)
    receiver=PortableTransferAuthority(destination_id=destination,destination_root=tmp_path/'imported')
    target=SubjectPackageService.import_quarantined(package['path'],tmp_path/'imported',expected_sha256=package['sha256'],destination_id=destination,authority=receiver)
    with ContinuityStore(target,clock,schema_target=13) as store:SubjectPackageService(store,receiver).activate(transfer_id=package['manifest'].transfer_id,destination_id=destination,authority=receiver)
    with open_runtime(target,clock) as r,semantic_harness() as (t,state):
        assert r.identity_id==identity and r.work.world is None and r.work.agency is None
        s=MediaSemanticService(CognitionSession(r,t,context_policy()));s.session.recover()
        assert r.store.one('cognitive_requests',pending)['state']=='UNKNOWN'
        assert s.ground(cid,entity_id='device')==result and state['calls']==0
        belief=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',)).view('device','media.content.0')
        assert belief.state=='SUPPORTED_BELIEF' and belief.alternatives[0]['kind']=='MODEL_BELIEF'
        assert all(g['revoked'] for g in r.store.all('grants'))
