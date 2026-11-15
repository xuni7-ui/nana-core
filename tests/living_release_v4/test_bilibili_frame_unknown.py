"""A terminal unknown preserves its reservation, not a permanent visual lock."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.provider_config import ProviderProfile, CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter, RuntimeProviderFactory, RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.semantic_harness import semantic_proposer
from nana_core.life.bilibili import BilibiliPublicTransport, BilibiliSourceAdapter
from nana_core.life.bilibili_frames import BilibiliFrameService
from nana_core.presence.resources import resource_state
from tests.provider_routing.helpers import config_service, model, update, Resolver
from tests.world_loop.helpers import fresh, policy
from .bilibili_loopback import counterpart


@contextmanager
def visual_host(tmp_path):
    with counterpart() as (opener, _), provider_harness(semantic_proposer) as (wire, metrics), fresh(tmp_path/'self.db',Clock()) as runtime:
        config, authority=config_service(tmp_path/'config/providers.json')
        provider=ProviderProfile(provider_profile_id='frames.loopback',display_name='SYNTHETIC_LOOPBACK',
            protocol='SYNTHETIC_LOOPBACK',base_url=wire.endpoint.removesuffix('/chat/completions'),
            locality='LOCAL_FIXTURE',permitted_privacy=('PUBLIC','PROJECT'))
        profile=model('model.frames',provider.provider_profile_id,('VISION',)).model_copy(update={'remote_model_id':'harness-v1'})
        update(config,authority,'UPSERT_PROVIDER',provider=provider)
        update(config,authority,'UPSERT_MODEL',model=profile)
        update(config,authority,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='VISION',
            primary_model_profile_id=profile.model_profile_id,permitted_privacy=('PUBLIC','PROJECT')))
        app=SimpleNamespace(runtime=runtime,policy=policy(),router=CapabilityRouter(config,
            RuntimeProviderFactory(ProviderRegistry(),Resolver(),RoutingPolicy(allow_synthetic_loopback=True))),
            config=SimpleNamespace(provider_wire_bytes_per_day=4_000_000,provider_context_tokens=16000,
                provider_output_tokens=4096,provider_timeout_ms=100,provider_cost_ceiling_micro=0,
                provider_total_calls_limit=4,provider_total_reserved_cost_micro=0,provider_calls_per_hour=4,
                provider_calls_per_day=4,per_provider_calls_per_day=4))
        public=BilibiliPublicTransport(authorized=True,origin='SYNTHETIC_FIXTURE',request_limit=9);public.opener=opener
        reading=public.read_video('BV1t55v6DE2v',visual=True)
        parent=BilibiliSourceAdapter(app).ingest(reading)
        service=BilibiliFrameService(app);frames=service.capture(parent,reading.frames)
        yield app,service,frames,parent,metrics


@pytest.mark.parametrize('restart',[False,True])
def test_unknown_frame_never_replays_but_an_independent_frame_can_continue_within_budget(tmp_path,restart):
    with visual_host(tmp_path) as (app,service,frames,parent,metrics):
        metrics['delay']=.35
        unknown=service.interpret(frames[0])
        assert unknown['state']=='UNKNOWN' and metrics['calls']==1
        original=dict(app.runtime.store.one('cognitive_requests',unknown['request_id']))
        identity=app.runtime.identity_id;metrics['delay']=0
        def verify(service):
            result=service.interpret(frames[1])
            assert result['state']=='SAMPLED_FRAME_INTERPRETED' and metrics['calls']==2
            assert result['request_id']!=unknown['request_id']
            replay=service.interpret(frames[0])
            assert replay['state']=='UNKNOWN' and metrics['calls']==2
            assert dict(app.runtime.store.one('cognitive_requests',unknown['request_id']))==original
            state=resource_state(app.runtime.store,app.runtime.config)
            assert state.unresolved_terminal_calls==1 and state.unresolved_live_calls==0
            # The old unknown still consumes the ORIGINAL total reservation.
            app.config.provider_total_calls_limit=2
            with pytest.raises(CoreError,match='PROVIDER_TOTAL_CALL_BUDGET'):
                service.interpret(frames[2])
            assert metrics['calls']==2
            MemoryService(app.runtime.store,app.runtime.authority).forget(parent,app.runtime.authority)
            with pytest.raises(CoreError,match='MEMORY_UNAVAILABLE'):
                service.interpret(frames[1])
            assert metrics['calls']==2 and app.runtime.identity_id==identity
        if restart:
            app.runtime.stop()
            with fresh(tmp_path/'self.db',Clock()) as reopened:
                app.runtime=reopened;verify(BilibiliFrameService(app))
        else:
            verify(service)


def test_a_live_call_still_blocks_a_nested_visual_attempt(tmp_path,monkeypatch):
    with visual_host(tmp_path) as (app,service,frames,_,metrics):
        app.config.provider_timeout_ms=3000
        original=CognitionSession.accept;blocked=[]
        def accept(session,request_id,reply,**kwargs):
            assert app.runtime.store.one('cognitive_requests',request_id)['state']=='CALLING'
            with pytest.raises(CoreError,match='UNRESOLVED_PROVIDER_CALL_NO_RETRY'):
                service.interpret(frames[1])
            blocked.append(request_id)
            return original(session,request_id,reply,**kwargs)
        monkeypatch.setattr(CognitionSession,'accept',accept)
        result=service.interpret(frames[0])
        assert result['state']=='SAMPLED_FRAME_INTERPRETED'
        assert blocked==[result['request_id']] and metrics['calls']==1
