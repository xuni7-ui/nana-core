import json
from uuid import uuid4
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore
from nana_core.continuity.application import SubjectApplication,FrontendPolicy
from nana_core.continuity.provider_routing import *
from nana_core.continuity.provider_config import *
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority,verify_package
from nana_core.presence import NanaRuntime
from tests.world_loop.helpers import fresh,capture,policy
from .helpers import *
BASE='ba798b201ff2f7ba671a2cb9939d9692b59fd93f'

def test_frontend_settings_cas_no_subject_mutation_or_authority(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        s,a=config_service(tmp_path/'host/providers.json');reg=ProviderRegistry();resolver=Resolver(('host.test',));factory=RuntimeProviderFactory(reg,resolver,RoutingPolicy())
        app=SubjectApplication(r.store,r.subject,r.authority,providers=reg,provider_settings=ProviderSettingsService(s,a,factory))
        fp=FrontendPolicy(context=policy(),entity_id='observer',commands=('VIEW_PROVIDER_SETTINGS','CONFIGURE_PROVIDERS','CHANGE_SETTING'))
        first=app.session(fp);second=app.session(fp);before=r.store.snapshot()
        assert json.loads(first.view('PROVIDER_SETTINGS').data_json)['revision']==0
        p=provider();out=first.provider_command(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=0,provider=p));assert json.loads(out.data_json)['revision']==1
        with pytest.raises(CoreError,match='REVISION_CONFLICT'):second.provider_command(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=0,provider=provider('fixture.b')))
        first.provider_command(ProviderCommand(operation='UPSERT_MODEL',expected_revision=1,model=model('model.vision',p.provider_profile_id,('VISION',))))
        first.provider_command(ProviderCommand(operation='SET_CAPABILITY_ROUTE',expected_revision=2,route=CapabilityRoute(operation='VISION',primary_model_profile_id='model.vision')))
        first.provider_command(ProviderCommand(operation='DISABLE_PROVIDER',expected_revision=3,target_id=p.provider_profile_id))
        projection=json.loads(first.view('PROVIDER_SETTINGS').data_json)
        assert projection['providers'][0]['secret_state']=='UNCONFIGURED' and not projection['providers'][0]['enabled']
        assert 'secret_ref' not in projection['providers'][0] and 'TEST_ONLY_NOT_SECRET' not in first.view('PROVIDER_SETTINGS').data_json
        assert r.store.snapshot()==before and resolver.resolved==0
        for name in ['store','authority','secret_resolver','config_file_handle','credential']:assert not hasattr(first,name)
        with pytest.raises(CoreError,match='SETTING_DENIED'):first.change_setting('authority','all')
        with pytest.raises(ValueError):ProviderProfile(provider_profile_id='remote.a',display_name='A',protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://api.example/v1',locality='REMOTE',permitted_privacy=('SECRET',))
        denied=app.session(FrontendPolicy(context=policy(),entity_id='observer',commands=()))
        with pytest.raises(CoreError,match='COMMAND_DENIED'):denied.view('PROVIDER_SETTINGS')
        with pytest.raises(CoreError,match='COMMAND_DENIED'):denied.provider_command(ProviderCommand(operation='DISABLE_PROVIDER',expected_revision=4,target_id=p.provider_profile_id))
        assert json.loads(first.view('PROVIDERS').data_json)=={'descriptors':[]}


def test_subjectpackage_excludes_host_config_and_same_subject_uses_new_host(tmp_path):
    router,s,a,registry,ports=fixture_router(tmp_path/'machine-a')
    # Unused remote config still must not travel with the Subject.
    update(s,a,'UPSERT_PROVIDER',provider=ProviderProfile(provider_profile_id='host.remote',display_name='Host-only',protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://private-config.example/v1',locality='REMOTE',secret_ref='machine-a.reference'))
    db=tmp_path/'a/subject/self.db'
    with fresh(db) as r:
        mid=capture(r,'history',{'fact':'A public synthetic lasting observation'});identity=r.identity_id;clock=r.clock.source;runtime_config=r.config
        target=router.resolve(RouteRequest(operation='COGNITION'),policy());ss=target.cognition_session(r);cid=ss.prepare('host-a','INTERPRET',(mid,));assert ss.execute(cid)['state']=='PROPOSED'
    controller=PortableTransferAuthority();destination_id=str(uuid4())
    with ContinuityStore(db,clock,schema_target=13) as store:
        package=SubjectPackageService(store,controller).export(tmp_path/'subject.zip',destination_id=destination_id,source_commit=BASE,authority=controller)
        manifest,files=verify_package(package['path'],expected_sha256=package['sha256'])
        assert set(files)=={'manifest.json','privacy.json','subject.sqlite'}
        for needle in [b'private-config.example',b'machine-a.reference',b'TEST_ONLY_NOT_SECRET',str(s._path).encode()]:assert all(needle not in raw for raw in files.values())
    (tmp_path/'machine-b').mkdir(mode=0o700)
    dest=PortableTransferAuthority(destination_id=destination_id,destination_root=tmp_path/'machine-b/subject')
    imported=SubjectPackageService.import_quarantined(package['path'],tmp_path/'machine-b/subject',expected_sha256=package['sha256'],destination_id=destination_id,authority=dest)
    with ContinuityStore(imported,clock,schema_target=13) as store:
        assert store.identity['identity_id']==identity
        SubjectPackageService(store,dest).activate(transfer_id=manifest.transfer_id,destination_id=destination_id,authority=dest)
    # New host has no route by default. Explicitly construct its own config.
    sb,ab=config_service(tmp_path/'machine-b/host/providers.json');reg=ProviderRegistry();pb=provider('other.host');mb=model('model.otherhost',pb.provider_profile_id)
    with pytest.raises(CoreError,match='ROUTE_UNAVAILABLE'):CapabilityRouter(sb,RuntimeProviderFactory(reg,Resolver(),RoutingPolicy())).resolve(RouteRequest(operation='COGNITION'),policy())
    update(sb,ab,'UPSERT_PROVIDER',provider=pb);update(sb,ab,'UPSERT_MODEL',model=mb);update(sb,ab,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=mb.model_profile_id))
    port=FixtureCognitionTransport(mb.descriptor(pb));reg.register(mb.descriptor(pb),port)
    with NanaRuntime(imported,runtime_config,clock=clock) as r:
        target=CapabilityRouter(sb,RuntimeProviderFactory(reg,Resolver(),RoutingPolicy())).resolve(RouteRequest(operation='COGNITION'),policy());session=target.cognition_session(r)
        old=r.store.one('cognitive_requests',cid);history=session.records.read(old['record_id'])['payload']['request'];assert history['route_snapshot']['provider_profile_id']=='fixture.a'
        c2=session.prepare('host-b','INTERPRET',(mid,));assert session.execute(c2)['state']=='PROPOSED'
        assert r.identity_id==identity and port.calls==1
        assert r.store.db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_multi_provider_life_restart_disable_remove_no_history_delete(tmp_path):
    s,a=config_service(tmp_path/'host/providers.json');reg=ProviderRegistry();objects={}
    specs=[('fixture.a','model.text',('COGNITION',)),('fixture.b','model.vision',('VISION',)),('fixture.c','model.embed',('EMBED',)),('fixture.d','model.fallback',('VISION',))]
    for pid,mid,ops in specs:
        p=provider(pid);m=model(mid,pid,ops);update(s,a,'UPSERT_PROVIDER',provider=p);update(s,a,'UPSERT_MODEL',model=m)
        port=FixtureCognitionTransport(m.descriptor(p)) if ops==('COGNITION',) else FixtureMediaPort();reg.register(m.descriptor(p),port);objects[mid]=port
    for op,mid,fallback in [('COGNITION','model.text',()),('VISION','model.vision',('model.fallback',)),('EMBED','model.embed',())]:update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation=op,primary_model_profile_id=mid,fallback_model_profile_ids=fallback))
    router=CapabilityRouter(s,RuntimeProviderFactory(reg,Resolver(),RoutingPolicy()))
    with fresh(tmp_path/'subject/self.db') as r:
        mid=capture(r,'public',{'source':'synthetic image description'});identity=r.identity_id
        cog=router.resolve(RouteRequest(operation='COGNITION'),policy()).cognition_session(r);cid=cog.prepare('one','INTERPRET',(mid,));assert cog.execute(cid)['state']=='PROPOSED'
        for op in ['VISION','EMBED']:assert router.resolve(RouteRequest(operation=op),policy()).media(r.store,(mid,),scopes=('world',))['proposal']
        app=SubjectApplication(r.store,r.subject,r.authority,providers=reg,provider_settings=ProviderSettingsService(s,a,router.factory))
        client=app.session(FrontendPolicy(context=policy(),entity_id='observer',commands=('VIEW_PROVIDER_SETTINGS','CONFIGURE_PROVIDERS')))
        client.provider_command(ProviderCommand(operation='DISABLE_PROVIDER',expected_revision=s.load().revision,target_id='fixture.b'))
        target=router.resolve(RouteRequest(operation='VISION'),policy());assert target.snapshot.provider_profile_id=='fixture.d' and target.snapshot.selection=='FALLBACK'
        target.media(r.store,(mid,),scopes=('world',));history=cog.records.read(r.store.one('cognitive_requests',cid)['record_id'])
    s2=ProviderConfigService(s._path,ProviderConfigurationAuthority());assert s2.load()==s.load()
    with fresh(tmp_path/'subject/self.db') as r:
        assert r.identity_id==identity
        with pytest.raises(CoreError,match='PROFILE_IN_USE'):update(s,a,'REMOVE_PROVIDER',target_id='fixture.d')
        with pytest.raises(CoreError,match='MODEL_PROFILE_IN_USE'):update(s,a,'REMOVE_MODEL',target_id='model.fallback')
        update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='VISION',primary_model_profile_id='model.vision'));update(s,a,'REMOVE_MODEL',target_id='model.fallback');update(s,a,'REMOVE_PROVIDER',target_id='fixture.d')
        assert r.store.one('cognitive_requests',cid)['state']=='PROPOSED'
        from nana_core.continuity.records import RecordService
        assert RecordService(r.store).read(history['record_id'])==history
        assert not r.store.all('subject_cycles') and not r.store.all('grants')
