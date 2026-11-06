import json
from uuid import uuid4
import zipfile
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.commitments import CommitmentService, CommitmentCandidate
from nana_core.continuity.subject import SubjectLoop, SubjectInput
from nana_core.continuity.relational.bootstrap import SubjectBootstrapService, SubjectBootstrapAuthority, primary_user_view
from nana_core.continuity.relational.contracts import RelationalAnchorSpec
from nana_core.continuity.portable import SubjectPackageService, PortableTransferAuthority, verify_package
from nana_core.presence.authority import RuntimeLease,VirtualClock
from nana_core.presence.contracts import RuntimeConfig
from nana_core.storage import canonical, digest

BASE='e26288e8ffcc1697b1a1f86b55f304b76d9b04ed'


def populated(store,operator):
    clock=store.clock
    result=SubjectLoop(store,scopes=('lab',)).run(SubjectInput(source_key='synthetic.portable.history',kind='INTERACTION',origin='USER',entity_id='person-a',scope='lab',text='A fictional ongoing project and promise',significance='HIGH',observed_at_us=clock.utc_now_us()))
    mid=store.all('subject_events')[-1]['memory_id']
    service=CommitmentService(store,operator)
    cid=service.propose(CommitmentCandidate(entity_id='person-a',scope='lab',description='Continue a fictional project',support_memory_ids=(mid,)))
    service.transition(cid,'ADOPTED',expected_revision=1,authority=operator)
    boot=SubjectBootstrapAuthority()
    SubjectBootstrapService(store,boot).install(RelationalAnchorSpec(identity_id=store.identity['identity_id'],anchor_id='primary',entity_id='person-a',role_kind='PRIMARY_USER',role_label='companion',scope='lab',revision=1,effective_from_us=clock.utc_now_us()),boot)
    from nana_core.continuity.projects import ProjectService,ProjectContent
    ProjectService(store,operator).save(project_id='synthetic-project',entity_id='person-a',scope='lab',content=ProjectContent(goal='Maintain a fictional shared project',current_state='Synthetic development',next_actions=('Review the fictional milestone',)),source_memory_ids=(mid,),expected_revision=0,authority=operator)
    return cid,mid


def test_export_import_same_subject_retired_source_fresh_epoch(subject,tmp_path):
    store,operator=subject;cid,mid=populated(store,operator)
    lease=RuntimeLease(store,RuntimeConfig(schema_target=10,scopes=('lab',),entity_id='person-a'))
    old_epoch=lease.acquire();lease.release();store._runtime_guard=None
    authority=PortableTransferAuthority();target=str(uuid4())
    result=SubjectPackageService(store,authority).export(tmp_path/'subject.zip',destination_id=target,source_commit=BASE,authority=authority)
    manifest,files=verify_package(result['path'],expected_sha256=result['sha256'])
    assert set(files)=={'manifest.json','privacy.json','subject.sqlite'}
    assert 'backups' not in json.loads(files['privacy.json'])
    assert str(tmp_path).encode() not in files['subject.sqlite']
    with pytest.raises(CoreError,match='SOURCE_RETIRED'):
        MemoryService(store).entity('cannot-write','PERSON')
    with pytest.raises(CoreError,match='SOURCE_RETIRED'):
        RuntimeLease(store,RuntimeConfig(schema_target=10,scopes=('lab',),entity_id='person-a')).acquire()
    destination_authority=PortableTransferAuthority(destination_id=target,destination_root=tmp_path/'machine-b')
    destination=SubjectPackageService.import_quarantined(result['path'],tmp_path/'machine-b',expected_sha256=result['sha256'],destination_id=target,authority=destination_authority)
    with ContinuityStore(destination,VirtualClock(),schema_target=10) as restored:
        assert restored.identity==store.identity
        assert restored.all('subject_cycles')==store.all('subject_cycles')
        assert restored.all('projects')==store.all('projects')
        assert restored.all('runtime_lease')==[]
        assert CommitmentService(restored,operator).get(cid).state=='ADOPTED'
        assert primary_user_view(restored,scope='lab',privacy_classes=('PERSONAL',)).spec.entity_id=='person-a'
        with pytest.raises(CoreError,match='QUARANTINED'):
            MemoryService(restored).entity('cannot-yet-write','PERSON')
        SubjectPackageService(restored,destination_authority).activate(transfer_id=manifest.transfer_id,destination_id=target,authority=destination_authority)
        newlease=RuntimeLease(restored,RuntimeConfig(schema_target=10,scopes=('lab',),entity_id='person-a'))
        assert newlease.acquire()>old_epoch
        assert MemoryService(restored).read(mid)['text']=='A fictional ongoing project and promise'
        newlease.release()
    with pytest.raises(CoreError,match='CLEAN_DESTINATION'):
        SubjectPackageService.import_quarantined(result['path'],tmp_path/'machine-b',expected_sha256=result['sha256'],destination_id=target,authority=destination_authority)


def test_package_tamper_unknown_machine_metadata_and_target_rejected(subject,tmp_path):
    store,_=subject;authority=PortableTransferAuthority();target=str(uuid4())
    # Unknown host configuration is rejected, not filtered out of immutable history.
    store._put('core_meta',{'key':'provider.configuration','value_json':canonical({'credential_ref':'not-a-secret'})})
    service=SubjectPackageService(store,authority)
    with pytest.raises(CoreError,match='UNSUPPORTED_MACHINE_METADATA'):
        service.export(tmp_path/'blocked.zip',destination_id=target,source_commit=BASE,authority=authority)
    store.db.execute("DELETE FROM core_meta WHERE key='provider.configuration'")
    result=service.export(tmp_path/'subject.zip',destination_id=target,source_commit=BASE,authority=authority)
    with pytest.raises(CoreError,match='DESTINATION_MISMATCH'):
        SubjectPackageService.import_quarantined(result['path'],tmp_path/'bad',expected_sha256=result['sha256'],destination_id=str(uuid4()),authority=authority)
    data=bytearray((tmp_path/'subject.zip').read_bytes());data[-5]^=1
    (tmp_path/'bad.zip').write_bytes(data)
    with pytest.raises(CoreError,match='INTEGRITY'):
        verify_package(tmp_path/'bad.zip',expected_sha256=result['sha256'])


def test_deleted_sources_remain_erased_after_package_and_official_replay(subject,tmp_path):
    store,operator=subject;_,mid=populated(store,operator)
    MemoryService(store,operator).forget(mid,operator)
    authority=PortableTransferAuthority();target=str(uuid4())
    result=SubjectPackageService(store,authority).export(tmp_path/'deleted.zip',destination_id=target,source_commit=BASE,authority=authority)
    destination_authority=PortableTransferAuthority(destination_id=target,destination_root=tmp_path/'restored')
    path=SubjectPackageService.import_quarantined(result['path'],tmp_path/'restored',expected_sha256=result['sha256'],destination_id=target,authority=destination_authority)
    with ContinuityStore(path,store.clock,schema_target=10) as restored:
        with pytest.raises(CoreError,match='UNAVAILABLE'):MemoryService(restored).read(mid)
        restored.replay(tmp_path/'replayed'/'self.db')
    with ContinuityStore(tmp_path/'replayed'/'self.db',store.clock,schema_target=10) as replayed:
        with pytest.raises(CoreError,match='UNAVAILABLE'):MemoryService(replayed).read(mid)
        assert replayed.one('core_meta','recovery_quarantine')['value_json']=='true'


def test_destination_binding_and_old_grants_do_not_migrate_as_authority(subject,tmp_path):
    from nana_core.actions import ActionKernel
    from nana_core.contracts import GrantSpec
    from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
    store,operator=subject
    kernel=ActionKernel(store,OfflineEffectPort(store.identity['identity_id'],tmp_path/'world.fixture.json'),operator)
    now=store.clock.utc_now_us()
    grant=kernel.grant(GrantSpec(capabilities=('reading.source.read',),resources=('synthetic://source/one',),not_before_us=now,expires_at_us=now+100000000),operator)
    kernel.set_budgets({'write_attempts':2,'external_requests':2,'cost_micro_units':2},operator)
    controller=PortableTransferAuthority();target=str(uuid4())
    package=SubjectPackageService(store,controller).export(tmp_path/'authority.zip',destination_id=target,source_commit=BASE,authority=controller)
    destination=PortableTransferAuthority(destination_id=target,destination_root=tmp_path/'bound')
    with pytest.raises(CoreError,match='DESTINATION_BINDING'):
        SubjectPackageService.import_quarantined(package['path'],tmp_path/'other',expected_sha256=package['sha256'],destination_id=target,authority=destination)
    path=SubjectPackageService.import_quarantined(package['path'],tmp_path/'bound',expected_sha256=package['sha256'],destination_id=target,authority=destination)
    with ContinuityStore(path,store.clock,schema_target=10) as restored:
        # This is history until explicit activation; quarantine prevents realization.
        manifest=package['manifest']
        SubjectPackageService(restored,destination).activate(transfer_id=manifest.transfer_id,destination_id=target,authority=destination)
        assert restored.one('grants',grant)['revoked']==1
        assert all(b['limit_value']==b['spent'] for b in restored.all('budgets'))
        assert restored.one('core_meta','cloud.shadow_runtime')
        with pytest.raises(CoreError,match='ALREADY_ACTIVATED'):
            SubjectPackageService(restored,destination).activate(transfer_id=manifest.transfer_id,destination_id=target,authority=destination)


def test_rebuildable_index_substitution_is_not_ignored(subject, tmp_path):
    store, operator = subject
    store.db.execute('DROP INDEX memory_source_binding')
    store.db.execute('CREATE INDEX memory_source_binding ON memories(scope)')
    authority = PortableTransferAuthority()
    with pytest.raises(CoreError, match='PORTABLE_SCHEMA_DRIFT'):
        SubjectPackageService(store, authority).export(
            tmp_path/'bad-index.zip', destination_id=str(uuid4()), source_commit=BASE, authority=authority)
