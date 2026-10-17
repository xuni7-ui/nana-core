import io,json,os
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.sensors.adapters import FileImportAdapter
from nana_core.continuity.sensors.application import PerceptionSettingsService
from nana_core.continuity.application import SubjectApplication,FrontendPolicy
from nana_core.continuity.world_loop.world import WorldModel
from tests.world_loop.helpers import fresh,policy
from .helpers import *
from nana_core.continuity.world_loop.samples import media_samples

def watch(r,c,mid):
    cue=ConcernCue(cue_kind='DISCOVERY',topic_key='sensor',motivation_source='CURIOSITY',possible_behaviors=('WATCH',))
    memory=MemoryService(r.store);eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.h2-watch',source_reference=mid,source_kind='MODEL_DERIVATION'),text=cue.model_dump_json(),privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()))
    cmid=memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='INFERENCE',source_evidence_id=eid,text=cue.model_dump_json(),derived_from=(mid,),predicate_key='concern.sensor'))
    cycle=r.subject.run(SubjectInput(source_key='synthetic.h2-watch.'+mid,kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(mid,cmid),observed_at_us=r.clock.utc_now_us()))
    assert cycle.judgment.stance=='WATCH';return cycle

def test_watch_sourced_host_bound_and_desire_survives_denial(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);value=c.observe(c.request('screen.a',request_id='watch'))
        cycle=watch(r,c,value['memory_id']);c.watch_from_cycle(cycle.cycle_id,'screen.a');p=c.configuration.load().sources[0]
        assert c.interval_ms(p)==5000
        assert c.interval_ms(p.model_copy(update={'min_interval_ms':10000}))==10000
        before=r.store.one('subject_cycles',cycle.cycle_id);c.host_allow=lambda p:False
        r.clock.source.advance(200000)
        with pytest.raises(CoreError,match='BLOCKED_BY_HOST'):c.observe(c.request('screen.a',request_id='blocked'))
        assert r.store.one('subject_cycles',cycle.cycle_id)==before and adapter.captures==1
        c.state['sources']['screen.a']['watch']['until_us']=0;assert c.interval_ms(p)==30000

@pytest.mark.parametrize('mode',['symlink','hardlink','oversize','fifo','directory','traversal','device','ancestor'])
def test_file_import_security_zero_bytes(tmp_path,mode):
    root=tmp_path/'public';root.mkdir();path=root/'sample';path.write_bytes(png())
    with fresh(tmp_path/'subject/self.db') as r:
        c,old,m,a=setup(r,tmp_path,kind='FILE_IMPORT')
        if mode=='symlink':path.unlink();path.symlink_to(root/'elsewhere')
        if mode=='hardlink':os.link(path,root/'another')
        if mode=='oversize':path.write_bytes(b'x'*131073)
        if mode=='fifo':path.unlink();os.mkfifo(path)
        if mode=='directory':path.unlink();path.mkdir()
        if mode in {'traversal','ancestor'}:
            if mode=='ancestor':link=tmp_path/'linked';link.symlink_to(root,target_is_directory=True)
            with pytest.raises(CoreError):FileImportAdapter(r.clock,link if mode=='ancestor' else root,'sample' if mode=='ancestor' else '../sample')
            return
        port=FileImportAdapter(r.clock,'/dev' if mode=='device' else root,'null' if mode=='device' else 'sample',max_bytes=131072)
        resolver=HostPerceptionResolver();resolver.bind('fixture','sample',port);c.resolver=resolver
        result=c.observe(c.request('screen.a',request_id='file'))
        assert result['state']=='FAILED' and port.bytes_read==0 and m.calls==0

@pytest.mark.parametrize('modality,ops',[('IMAGE',('VISION',)),('AUDIO',('AUDIO_UNDERSTAND',)),('VIDEO',('VIDEO_UNDERSTAND',))])
def test_generated_file_import_actual_decode(tmp_path,modality,ops):
    root=tmp_path/'public';root.mkdir();raw=png() if modality=='IMAGE' else media_samples()[modality];(root/'sample').write_bytes(raw)
    with fresh(tmp_path/'subject/self.db') as r:
        c,old,m,a=setup(r,tmp_path,kind='FILE_IMPORT',modality=modality,data=raw,ops=ops)
        port=FileImportAdapter(r.clock,root,'sample',modality=modality,max_bytes=16777216);resolver=HostPerceptionResolver();resolver.bind('fixture','sample',port);c.resolver=resolver
        result=c.observe(c.request('screen.a',request_id='file'));assert result['state']=='GROUNDED' and port.bytes_read==len(raw)

def test_provider_disabled_capture_survives_and_route_swap_history(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);first=c.observe(c.request('screen.a',request_id='a'));assert first['state']=='GROUNDED'
        ps=c.router.config;pa=ps._ProviderConfigService__authority
        update(ps,pa,'DISABLE_PROVIDER',target_id='fixture.semantic');r.clock.source.advance(3000000)
        second=c.observe(c.request('screen.a',request_id='b'));assert second['state']=='DEFERRED' and c.records.memory.read(second['memory_id']) and m.calls==1
        update(ps,pa,'ENABLE_PROVIDER',target_id='fixture.semantic');r.clock.source.advance(3000000)
        third=c.observe(c.request('screen.a',request_id='c'));assert third['state']=='GROUNDED' and m.calls==2
        assert c.records.memory.read(first['memory_id'])
        # A later capture may use another exact profile; original call provenance stays frozen.
        old_request=c.records.read(r.store.db.execute('SELECT record_id FROM cognitive_requests ORDER BY created_at_us,rowid LIMIT 1').fetchone()[0])['payload']['request']
        pp=ps.load().providers[0];other=model('model.other',pp.provider_profile_id,('VISION',)).model_copy(update={'remote_model_id':'different-fixture'})
        update(ps,pa,'UPSERT_MODEL',model=other);other_port=SemanticFixture(pp.provider_profile_id,other.remote_model_id)
        c.perception.session._registry.register(other.descriptor(pp),other_port)
        update(ps,pa,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='VISION',primary_model_profile_id=other.model_profile_id))
        r.clock.source.advance(200000);fourth=c.observe(c.request('screen.a',request_id='d'));assert fourth['state']=='GROUNDED' and other_port.calls==1
        assert old_request['route_snapshot']['model_profile_id']=='model.semantic'
        latest=c.records.read(r.store.db.execute('SELECT record_id FROM cognitive_requests ORDER BY created_at_us DESC,rowid DESC LIMIT 1').fetchone()[0])['payload']['request']
        assert latest['route_snapshot']['model_profile_id']=='model.other'


@pytest.mark.parametrize('privacy',['PERSONAL','SECRET'])
def test_remote_semantic_denied_local_capture_survives(tmp_path,privacy):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path,privacy=privacy)
        ps=c.router.config;pa=ps._ProviderConfigService__authority
        remote=ProviderProfile(provider_profile_id='remote.denied',display_name='Remote',protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://api.example/v1',locality='REMOTE',secret_ref='unused.reference',permitted_privacy=('PUBLIC','PERSONAL'))
        update(ps,pa,'UPSERT_PROVIDER',provider=remote);mp=model('model.denied',remote.provider_profile_id,('VISION',));update(ps,pa,'UPSERT_MODEL',model=mp)
        update(ps,pa,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='VISION',primary_model_profile_id=mp.model_profile_id,permitted_privacy=('PUBLIC','PERSONAL','SECRET')))
        value=c.observe(c.request('screen.a',request_id='private'));assert value['state']=='DEFERRED' and value['semantic']['VISION']=='DENIED' and c.records.memory.read(value['memory_id'])
        assert m.calls==0 and c.router.factory.secret_state(remote)=='MISSING'

def test_forget_closure_restart_no_resurrection(tmp_path):
    db=tmp_path/'subject/self.db'
    with fresh(db) as r:
        c,adapter,m,a=setup(r,tmp_path);req=c.request('screen.a',request_id='deleted');v=c.observe(req);mid=v['memory_id']
        claims=[x['memory_id'] for x in r.store.all('memories') if x['epistemic_kind']=='INFERENCE'];assert claims
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        for x in claims:
            with pytest.raises(CoreError):MemoryService(r.store).read(x)
        assert c.observe(req)['reason']=='SOURCE_RETIRED';identity=r.identity_id
    with fresh(db) as r:
        c,adapter,m,a=setup_existing(r,tmp_path)
        assert r.identity_id==identity and c.observe(req)['reason']=='SOURCE_RETIRED' and m.calls==0

def test_frontend_config_cas_redacted_no_authority(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);c.attach();service=PerceptionSettingsService(c,a)
        app=SubjectApplication(r.store,r.subject,r.authority,providers=c.perception.session._registry,perception_settings=service)
        fp=FrontendPolicy(context=policy(),entity_id='observer',commands=('VIEW_PERCEPTION','CONFIGURE_PERCEPTION','REQUEST_CAPTURE'))
        one=app.session(fp);two=app.session(fp);before=r.store.snapshot();view=one.view('PERCEPTION_SETTINGS').data_json
        assert 'resource_ref' not in view and 'adapter_ref' not in view
        one.perception_command(SourceCommand(operation='DISABLE_PERCEPTION_SOURCE',expected_revision=1,target_id='screen.a'))
        with pytest.raises(CoreError,match='REVISION_CONFLICT'):two.perception_command(SourceCommand(operation='ENABLE_PERCEPTION_SOURCE',expected_revision=1,target_id='screen.a'))
        assert r.store.snapshot()==before
        one.perception_command(SourceCommand(operation='ENABLE_PERCEPTION_SOURCE',expected_revision=2,target_id='screen.a'))
        assert one.request_capture(source_id='screen.a',request_id='front',expected_revision=3)['state']=='REQUESTED'
        assert adapter.bytes_read==0;assert r.step()['perception']['state']=='GROUNDED'
        for name in ['store','authority','camera_handle','microphone_handle','resource_ref']:assert not hasattr(one,name)
        assert 'raw_media' in one.view('PERCEPTION_STATUS').data_json

def test_authenticated_manager_veto_never_changes_watch(tmp_path):
    from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint
    from nana_core.continuity.autonomy.contracts import RealizationTarget
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);v=c.observe(c.request('screen.a',request_id='seen'));cycle=watch(r,c,v['memory_id']);old=r.store.one('subject_cycles',cycle.cycle_id)
        controller=GovernanceController(r.store,r.authority);now=r.clock.utc_now_us()
        controller.install(ManagerConstraint(constraint_id='no.capture',revision=1,issuer=r.authority.principal,source_reference='host.policy',identity_id=r.identity_id,scope='world',targets=(RealizationTarget(capability='perception.capture',operation='READ',resource='synthetic://perception/screen.a',resource_class='ORDINARY'),),effective_from_us=now,expires_at_us=now+10000000,reason_code='HOST_DISABLED'),r.authority)
        r.clock.source.advance(200000)
        with pytest.raises(CoreError,match='MANAGER_BLOCKED'):c.observe(c.request('screen.a',request_id='blocked'))
        assert adapter.captures==1 and r.store.one('subject_cycles',cycle.cycle_id)==old
        assert c.status(c.policy)['sources'][0]['last_block']['stage']=='MANAGER'
