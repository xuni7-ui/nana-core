import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.provider_routing import *
from nana_core.continuity.world_loop.cognition import CognitionBudget
from tests.world_loop.helpers import fresh,capture,policy
from .helpers import *

def test_primary_same_remote_model_different_provider_and_profile(tmp_path):
    router,s,a,registry,ports=fixture_router(tmp_path)
    assert len(registry.descriptors())==2 and len({d.model_id for d in registry.descriptors()})==1
    assert registry.cognition('model.a') is ports[0] and registry.cognition('model.b') is ports[1]
    target=router.resolve(RouteRequest(operation='COGNITION'),policy())
    assert target.snapshot.selection=='PRIMARY' and target.snapshot.remote_model_id=='qwen.same'
    with fresh(tmp_path/'subject/self.db') as r:
        mid=capture(r,'source',{'fact':'public fixture'});identity=r.identity_id
        session=target.cognition_session(r);cid=session.prepare('primary','INTERPRET',(mid,));result=session.execute(cid)
        assert result['state']=='PROPOSED' and ports[0].calls==1 and ports[1].calls==0
        observation=session.journal()[0]['routing'];assert observation['dispatch_status']=='RESPONSE_RECEIVED' and observation['snapshot']['selection']=='PRIMARY'
        body=session.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']
        assert body['route_snapshot']==target.snapshot.model_dump(mode='json') and 'base_url' not in body['route_snapshot'] and 'secret_ref' not in body['route_snapshot']
        update(s,a,'DISABLE_PROVIDER',target_id='fixture.a')
        fallback=router.resolve(RouteRequest(operation='COGNITION'),policy());assert fallback.snapshot.selection=='FALLBACK'
        assert fallback.snapshot.reasons[0].code=='PROFILE_DISABLED' and not fallback.snapshot.reasons[0].dispatched
        sess2=fallback.cognition_session(r);c2=sess2.prepare('fallback','INTERPRET',(mid,));assert sess2.execute(c2)['state']=='PROPOSED'
        assert ports[1].calls==1 and r.identity_id==identity
        assert session.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']==body
        assert not r.store.all('subject_cycles') and not r.store.all('goals') and not r.store.all('grants')

@pytest.mark.parametrize('reason',['disabled','unsupported','missing_secret','modality','runtime_unavailable'])
def test_pre_dispatch_fallback_exactly_once(tmp_path,reason):
    router,s,a,reg,ports=fixture_router(tmp_path)
    p=s.load().providers[0];m=s.load().models[0]
    if reason=='disabled':update(s,a,'DISABLE_PROVIDER',target_id=p.provider_profile_id)
    elif reason=='unsupported':update(s,a,'UPSERT_MODEL',model=m.model_copy(update={'operations':('EMBED',)}))
    elif reason=='modality':update(s,a,'UPSERT_MODEL',model=m.model_copy(update={'input_modalities':('IMAGE',)}))
    elif reason=='runtime_unavailable':reg.unregister('model.a')
    else:
        p=ProviderProfile(provider_profile_id=p.provider_profile_id,display_name='Remote',protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://api.example/v1',locality='REMOTE',secret_ref='missing.reference')
        update(s,a,'UPSERT_PROVIDER',provider=p)
        router.factory.policy=RoutingPolicy(allow_remote=True,allowed_remote_hosts=('api.example',))
    target=router.resolve(RouteRequest(operation='COGNITION'),policy());assert target.snapshot.selection=='FALLBACK'
    with fresh(tmp_path/'subject/self.db') as r:
        mid=capture(r,'source',{'fact':'fixture'});ss=target.cognition_session(r);cid=ss.prepare('once','INTERPRET',(mid,));assert ss.execute(cid)['state']=='PROPOSED'
        assert ss.execute(cid)['replayed']
    assert ports[0].calls==0 and ports[1].calls==1

@pytest.mark.parametrize('mode,expected',[('unknown','UNKNOWN'),('timeout','UNKNOWN'),('malformed','FAILED')])
def test_after_dispatch_never_fallback_restart_no_retry(tmp_path,mode,expected):
    router,s,a,reg,ports=fixture_router(tmp_path,modes=(mode,'ok'))
    with fresh(tmp_path/'subject/self.db') as r:
        t=router.resolve(RouteRequest(operation='COGNITION'),policy());ss=t.cognition_session(r)
        mid=capture(r,'source',{'fact':'fixture'});cid=ss.prepare('once','INTERPRET',(mid,));assert ss.execute(cid)['state']==expected
        assert ports[0].calls==1 and ports[1].calls==0
    with fresh(tmp_path/'subject/self.db') as r:
        update(s,a,'DISABLE_PROVIDER',target_id='fixture.a')
        target=router.resolve(RouteRequest(operation='COGNITION'),policy());session=target.cognition_session(r);session.recover()
        assert session.execute(cid)['replayed'] and ports[1].calls==0
        assert r.store.one('cognitive_requests',cid)['state']==expected


def test_exact_disabled_no_fallback_and_stale_prepared_cannot_switch(tmp_path):
    router,s,a,reg,ports=fixture_router(tmp_path)
    with fresh(tmp_path/'subject/self.db') as r:
        mid=capture(r,'source',{'fact':'fixture'});target=router.resolve(RouteRequest(operation='COGNITION'),policy());session=target.cognition_session(r);cid=session.prepare('pending','INTERPRET',(mid,))
        update(s,a,'DISABLE_PROVIDER',target_id='fixture.a')
        with pytest.raises(CoreError,match='PROFILE_DISABLED'):router.resolve(RouteRequest(operation='COGNITION',exact_provider_profile_id='fixture.a',exact_model_profile_id='model.a'),policy())
        fallback=router.resolve(RouteRequest(operation='COGNITION'),policy())
        assert fallback.cognition_session(r).execute(cid)['state']=='STALE'
        assert ports[0].calls==ports[1].calls==0
        # No new session can strip a pinned route and dispatch the old request.
        from nana_core.continuity.world_loop.cognition import CognitionSession
        assert CognitionSession(r,ports[0],policy()).execute(cid)['replayed']


def test_privacy_and_budget_are_intersections(tmp_path):
    router,s,a,reg,ports=fixture_router(tmp_path)
    router.factory.policy=RoutingPolicy(timeout_ceiling_ms=100,cost_ceiling=7,context_limit=4096,output_limit=128)
    target=router.resolve(RouteRequest(operation='COGNITION',timeout_ms=30000,cost_ceiling=999999,context_limit=64000,output_limit=8192),policy())
    assert target.snapshot.effective.timeout_ms==100 and target.snapshot.effective.cost_ceiling==7 and target.snapshot.effective.context_limit==4096 and target.snapshot.effective.output_limit==128
    with pytest.raises(CoreError,match='PRIVACY_DENIED'):router.resolve(RouteRequest(operation='COGNITION',privacy_class='PERSONAL'),policy())
    with fresh(tmp_path/'subject/self.db') as r:
        mid=capture(r,'source',{'fact':'fixture'});ss=target.cognition_session(r)
        cid=ss.prepare('bounded','INTERPRET',(mid,),budget=CognitionBudget(timeout_ms=30000,cost_ceiling_micro=500,input_tokens=64000,output_tokens=4096))
        budget=ss.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']['budget']
        assert budget=={'input_tokens':4096,'output_tokens':128,'timeout_ms':100,'cost_ceiling_micro':7}


def test_remote_personal_requires_context_and_route_and_provider(tmp_path):
    s,a=config_service(tmp_path/'host/providers.json');p=ProviderProfile(provider_profile_id='remote.a',display_name='A',protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://api.example/v1',locality='REMOTE',secret_ref='test.reference',permitted_privacy=('PUBLIC','PERSONAL'))
    update(s,a,'UPSERT_PROVIDER',provider=p);update(s,a,'UPSERT_MODEL',model=model('model.remote',p.provider_profile_id))
    update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='COGNITION',primary_model_profile_id='model.remote',permitted_privacy=('PUBLIC','PERSONAL','SECRET')))
    resolver=Resolver(('test.reference',));router=CapabilityRouter(s,RuntimeProviderFactory(ProviderRegistry(),resolver,RoutingPolicy(allow_remote=True,allowed_remote_hosts=('api.example',))))
    assert router.factory.secret_state(p)=='AVAILABLE'
    assert router.factory.secret_state(p.model_copy(update={'secret_ref':'missing.reference'}))=='MISSING'
    for privacy in ['PERSONAL','SECRET']:
        with pytest.raises(CoreError,match='PRIVACY_DENIED'):router.resolve(RouteRequest(operation='COGNITION',privacy_class=privacy),policy())
    allowed=policy().model_copy(update={'remote_privacy':('PUBLIC','PERSONAL','SECRET')})
    target=router.resolve(RouteRequest(operation='COGNITION',privacy_class='PERSONAL'),allowed)
    assert target.context_policy.remote_privacy==('PUBLIC','PERSONAL')
    assert 'TEST_ONLY_NOT_SECRET' not in target.snapshot.model_dump_json()+repr(target)
    with pytest.raises(CoreError,match='PRIVACY_DENIED'):router.resolve(RouteRequest(operation='COGNITION',privacy_class='SECRET'),allowed)
    target.port._credential=None


@pytest.mark.parametrize('ceiling',[0,2,26])
def test_routed_session_inherits_original_runtime_call_ceiling_instead_of_hidden_24(tmp_path,ceiling):
    router,configuration,authority,registry,ports=fixture_router(tmp_path)
    target=router.resolve(RouteRequest(operation='COGNITION'),policy())
    with fresh(tmp_path/'subject/self.db') as runtime:
        runtime.config=runtime.config.model_copy(update={'max_calls_per_day':ceiling})
        if ceiling==0:
            with pytest.raises(CoreError,match='COGNITION_DAILY_BUDGET'):target.cognition_session(runtime)
            assert not runtime.store.all('cognitive_requests')
            return
        mid=capture(runtime,'quota.source',{'fact':'SYNTHETIC call admission, never a paid request'})
        session=target.cognition_session(runtime)
        assert session.max_calls==ceiling
        for n in range(ceiling):session.prepare('quota.'+str(n),'INTERPRET',(mid,))
        with pytest.raises(CoreError,match='COGNITION_DAILY_BUDGET'):session.prepare('quota.over','INTERPRET',(mid,))
        assert len(runtime.store.all('cognitive_requests'))==ceiling
        assert all(row['state']=='PREPARED' for row in runtime.store.all('cognitive_requests'))
        assert ports[0].calls==ports[1].calls==0
