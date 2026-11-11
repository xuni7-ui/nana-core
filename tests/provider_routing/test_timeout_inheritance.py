"""Configured finite deadlines reach original requests and real loopback HTTP."""
import pytest
from nana_core.continuity.world_loop.cognition import CognitionSession, CognitionBudget
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.provider_routing import RoutingPolicy, RouteRequest
from tests.world_loop.helpers import fresh, capture, policy
from .helpers import fixture_router, update


def request_data(session,runtime,request_id):
    return session.records.read(runtime.store.one('cognitive_requests',request_id)['record_id'])['payload']['request']


def test_default_budget_reaches_each_original_http_call_independently(tmp_path,monkeypatch):
    with fresh(tmp_path/'subject/self.db') as runtime,provider_harness() as (port,calls):
        original=port.opener.open;timeouts=[]
        def open_once(request,*,timeout):
            timeouts.append(timeout);return original(request,timeout=timeout)
        monkeypatch.setattr(port.opener,'open',open_once)
        session=CognitionSession(runtime,port,policy());mid=capture(runtime,'default-phases',{'data':'SYNTHETIC independent phases'})
        ids=[]
        for role in ('INTERPRET','GOALS'):
            cid=session.prepare('default-'+role,role,(mid,));ids.append(cid)
            data=request_data(session,runtime,cid)
            assert data['deadline_us']-data['created_at_us']==120000000
            # An admitted default request remains current after the old3s cap,
            # rather than merely reporting a larger timeout to the transport.
            runtime.clock.source.advance(4_000_000)
            assert session.execute(cid)['state']=='PROPOSED'
            runtime.clock.source.advance(5_000_000)
        assert timeouts==[120,120] and calls['calls']==2
        assert session.execute(ids[0])['replayed'] and calls['calls']==2
        assert not runtime.store.all('actions') and not runtime.store.all('grants')


@pytest.mark.parametrize('request_limit,provider_limit,host_limit,expected',[
    (330000,450000,600000,330000),
    (500000,180000,600000,180000),
    (500000,450000,210000,210000),
])
def test_exact_model_without_a_route_inherits_only_real_configured_ceilings(tmp_path,request_limit,provider_limit,host_limit,expected):
    router,config,authority,_,ports=fixture_router(tmp_path)
    update(config,authority,'REMOVE_CAPABILITY_ROUTE',target_id='COGNITION')
    provider=config.load().providers[0].model_copy(update={'default_timeout_ms':provider_limit})
    update(config,authority,'UPSERT_PROVIDER',provider=provider)
    router.factory.policy=RoutingPolicy(timeout_ceiling_ms=host_limit)
    target=router.resolve(RouteRequest(operation='COGNITION',timeout_ms=request_limit,
        exact_provider_profile_id='fixture.a',exact_model_profile_id='model.a'),policy())
    assert target.snapshot.route_revision is None and target.snapshot.effective.timeout_ms==expected
    with fresh(tmp_path/'subject/self.db') as runtime:
        mid=capture(runtime,'configured-exact',{'data':'SYNTHETIC configured timeout'})
        session=target.cognition_session(runtime)
        cid=session.prepare('configured-exact','INTERPRET',(mid,))
        data=request_data(session,runtime,cid)
        assert data['budget']['timeout_ms']==expected
        assert data['deadline_us']-data['created_at_us']==expected*1000
        assert session.execute(cid)['state']=='PROPOSED' and ports[0].calls==1
        assert ports[1].calls==0


def test_explicit_route_and_explicit_short_budget_still_limit_and_expire(tmp_path):
    router,config,authority,_,ports=fixture_router(tmp_path)
    update(config,authority,'UPSERT_PROVIDER',provider=config.load().providers[0].model_copy(update={'default_timeout_ms':450000}))
    update(config,authority,'SET_CAPABILITY_ROUTE',route=config.load().routes[0].model_copy(update={'timeout_ceiling_ms':170000}))
    router.factory.policy=RoutingPolicy(timeout_ceiling_ms=600000)
    target=router.resolve(RouteRequest(operation='COGNITION',timeout_ms=500000,
        exact_provider_profile_id='fixture.a',exact_model_profile_id='model.a'),policy())
    assert target.snapshot.effective.timeout_ms==170000
    with fresh(tmp_path/'subject/self.db') as runtime:
        mid=capture(runtime,'explicit-short',{'data':'SYNTHETIC explicitly short budget'})
        session=target.cognition_session(runtime)
        cid=session.prepare('explicit-short','INTERPRET',(mid,),budget=CognitionBudget(timeout_ms=50))
        old=request_data(session,runtime,cid)
        assert old['budget']['timeout_ms']==50
        runtime.clock.source.advance(51_000)
        assert session.execute(cid)['state']=='STALE' and ports[0].calls==ports[1].calls==0
        assert request_data(session,runtime,cid)==old
