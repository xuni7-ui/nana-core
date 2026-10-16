import json,os,signal,subprocess,sys
from uuid import uuid4
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.agency import OfflineGoalPolicy
from nana_core.continuity.agency_contracts import OfflineProgram
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.contracts import LivingRuntimeConfig,SECOND
from nana_core.presence.authority import VirtualClock
from .helpers import fresh
from .test_agency import setup,start


def test_sigkill_after_effect_verifies_same_action_without_second_execution(tmp_path):
    proc=subprocess.run([sys.executable,'-m','tests.living_autonomy.crash_worker',str(tmp_path)],env={'PYTHONPATH':str(__import__('pathlib').Path('src').resolve())},timeout=15,capture_output=True)
    assert proc.returncode==-signal.SIGKILL
    path=tmp_path/'subject'/'self.db';world=tmp_path/'world'/'effect.fixture.json'
    with NanaRuntime(path,RuntimeConfig(schema_target=11,living=LivingRuntimeConfig(),scopes=('lab',),entity_id='synthetic-person'),clock=VirtualClock()) as r:
        p=OfflineProgram(program_id='fixture.reading',scope='lab',motivation_source='PROJECT_COMPLETION',source_resource='synthetic://source/document',output_resource='synthetic://card/one')
        r.work.configure_agency(OfflineGoalPolicy((p,)),OfflineEffectPort(r.identity_id,world))
        assert r.store.all('actions')[0]['state']=='DISPATCHING'
        r.step()
        assert r.store.all('actions')[0]['state']=='SUCCEEDED'
        assert len(json.loads(world.read_text())['effects'])==1
        assert len([a for a in r.store.all('attempts') if a['kind']=='EXECUTE' and a['started_at_us'] is not None])==1
        assert len(r.store.all('subject_cycles'))==2
        assert r.store.all('jobs')[0]['cursor']==1


@pytest.mark.parametrize('version',[7,8,9,10])
def test_explicit_11_preserves_history_no_new_tables_or_implicit_upgrade(tmp_path,version):
    path=tmp_path/'subject'/'self.db';a=OperatorAuthority()
    with ContinuityStore(path,VirtualClock(),schema_target=version) as s:original=IdentityService(s,a).current()
    with ContinuityStore(path,VirtualClock(),schema_target=11) as s:
        assert IdentityService(s,a).current()==original
        assert not s.db.execute('PRAGMA foreign_key_check').fetchall()
        assert s.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]==39


def test_portable_11_keeps_goals_journal_but_not_old_runtime_authority(tmp_path):
    path=tmp_path/'subject'/'self.db';clock=VirtualClock()
    with fresh(path,clock=clock) as r:
        _,mid=setup(r,tmp_path/'world'/'effect.fixture.json');start(r,mid);r.step();clock.advance(SECOND);r.step()
        identity=r.identity_id;old_epoch=r.lease.epoch;goal=r.store.all('goals')[0]['goal_id']
    with ContinuityStore(path,clock,schema_target=11) as source:
        target=str(uuid4());controller=PortableTransferAuthority()
        export=SubjectPackageService(source,controller).export(tmp_path/'subject.zip',destination_id=target,source_commit='4ad273f540bf8ac2988854b68a689685333e8c67',authority=controller)
    destination=PortableTransferAuthority(destination_id=target,destination_root=tmp_path/'imported')
    restored=SubjectPackageService.import_quarantined(export['path'],tmp_path/'imported',expected_sha256=export['sha256'],destination_id=target,authority=destination)
    with ContinuityStore(restored,clock,schema_target=11) as s:
        SubjectPackageService(s,destination).activate(transfer_id=export['manifest'].transfer_id,destination_id=target,authority=destination)
        assert s.identity['identity_id']==identity and s.one('goals',goal)
        assert all(g['revoked'] for g in s.all('grants'))
        assert all(j['owner_epoch'] is None for j in s.all('jobs'))
    with NanaRuntime(restored,RuntimeConfig(schema_target=11,living=LivingRuntimeConfig(),scopes=('lab',),entity_id='synthetic-person'),clock=clock) as r:
        assert r.lease.epoch>old_epoch
        assert r.work.agency is None
        assert r.store.identity['identity_id']==identity
