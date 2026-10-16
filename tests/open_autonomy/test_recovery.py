import json,os,signal,subprocess,sys
from pathlib import Path
from uuid import uuid4
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.code_skills import CodeSkillService
from .helpers import *
from .test_learning import number_learning

@pytest.mark.parametrize('mode',['action','learning'])
def test_actual_sigkill_same_action_and_partial_learning_consolidation(tmp_path,mode):
    child=subprocess.run([sys.executable,'-m','tests.open_autonomy.crash_worker',str(tmp_path),mode],env={'PYTHONPATH':str(Path('src').resolve()),'PATH':os.defpath},capture_output=True,timeout=15)
    assert child.returncode==-signal.SIGKILL
    with fresh(tmp_path/'s'/'self.db') as r:
        if mode=='action':
            before=len(r.store.all('subject_cycles'));configure(r,tmp_path/'w'/'world.fixture.json',(objective(),),grant=False)
            r.step()
            assert r.store.all('actions')[0]['state']=='SUCCEEDED'
            assert len([a for a in r.store.all('attempts') if a['kind']=='EXECUTE' and a['started_at_us'] is not None])==1
            assert len(json.loads((tmp_path/'w'/'world.fixture.json').read_text())['effects'])==1
            assert len(r.store.all('subject_cycles'))==before
        else:
            job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();assert job['cursor']==7
            assert len(r.store.all('lessons'))==1 and r.store.all('lessons')[0]['state']=='ACTIVE'
            r.work.configure_open_learning((number_learning(),));r.drain(24)
            job=r.store.one('jobs',job['job_id']);assert job['state']=='DONE' and job['cursor']==9
            assert len(r.store.all('lessons'))==1 and len(r.store.all('experiences'))==1

@pytest.mark.parametrize('version',[7,8,11])
def test_explicit_v12_migration_preserves_identity_and_default_schema(tmp_path,version):
    p=tmp_path/'s'/'self.db'
    with ContinuityStore(p,VirtualClock(),schema_target=version) as s:identity=s.identity['identity_id'];count=len(s.all('events'))
    with ContinuityStore(p,VirtualClock(),schema_target=12) as s:
        assert s.identity['identity_id']==identity and len(s.all('events'))==count
        assert not s.db.execute('PRAGMA foreign_key_check').fetchall()
        assert not s.db.execute("SELECT 1 FROM sqlite_master WHERE name='one_live_goal'").fetchone()
        assert s.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]==39
    assert RuntimeConfig(scopes=('a',),entity_id='a').schema_target==8

def test_v12_portable_transfer_preserves_multigoal_and_partial_learning_but_not_authority(tmp_path):
    clock=VirtualClock();p=tmp_path/'s'/'self.db'
    with fresh(p,clock) as r:
        a=objective();b=objective('fixture.second');port=configure(r,tmp_path/'w'/'world.fixture.json',(a,b))
        for obj in (a,b):port.seed_observation(obj.operators[0].resource,[1.2,2.3]);send(r,obj.objective_id,(cue(r,obj),));r.drain(3)
        r.work.configure_open_learning((number_learning(),))
        c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',topic_key='partial',program_id='learn.numbers',possible_behaviors=('LEARN',))
        mid=capture(r,'partial',c.model_dump_json(),predicate='concern.partial');send(r,'partial',(mid,))
        for _ in range(8):
            r.step()
            row=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
            if row and row['cursor']==2:break
        assert row['cursor']==2;identity=r.identity_id;epoch=r.lease.epoch
    target=str(uuid4());controller=PortableTransferAuthority()
    with ContinuityStore(p,clock,schema_target=12) as s:
        package=SubjectPackageService(s,controller).export(tmp_path/'subject.zip',destination_id=target,source_commit='30f7e6f5e0b6e935f7d27a2847a5107d261c4ef5',authority=controller)
    destination=PortableTransferAuthority(destination_id=target,destination_root=tmp_path/'imported')
    path=SubjectPackageService.import_quarantined(package['path'],tmp_path/'imported',expected_sha256=package['sha256'],destination_id=target,authority=destination)
    with ContinuityStore(path,clock,schema_target=12) as s:
        assert len(s.all('goals'))==2
        SubjectPackageService(s,destination).activate(transfer_id=package['manifest'].transfer_id,destination_id=target,authority=destination)
        assert all(g['revoked'] for g in s.all('grants')) and s.one('jobs',row['job_id'])['cursor']==2
    with NanaRuntime(path,RuntimeConfig(schema_target=12,living=LivingRuntimeConfig(),scopes=('lab',),entity_id='synthetic-person'),clock=clock) as r:
        assert r.identity_id==identity and r.lease.epoch>epoch
        assert r.work.agency is None and r.work.open_learning is None

def test_legacy_v11_goal_and_action_history_survives_v12_official_replay(tmp_path):
    from tests.living_autonomy.helpers import fresh as old_fresh
    from tests.living_autonomy.test_agency import setup,start
    p=tmp_path/'old'/'self.db';clock=VirtualClock()
    with old_fresh(p,clock=clock) as r:
        _,mid=setup(r,tmp_path/'world'/'old.fixture.json');start(r,mid);r.step()
        oldgoal=r.store.all('goals')[0]['goal_id'];action=r.store.all('actions')[0]['action_id']
    with ContinuityStore(p,clock,schema_target=12) as s:
        assert s.one('goals',oldgoal)['priority']==1 and s.one('actions',action)['state']=='SUCCEEDED'
        s.replay(tmp_path/'replayed'/'self.db')
    with ContinuityStore(tmp_path/'replayed'/'self.db',clock,schema_target=12) as s:
        assert s.one('goals',oldgoal) and s.one('actions',action)['state']=='SUCCEEDED'
        assert not s.db.execute('PRAGMA foreign_key_check').fetchall()
        assert json.loads(s.one('core_meta','recovery_quarantine')['value_json']) is True
