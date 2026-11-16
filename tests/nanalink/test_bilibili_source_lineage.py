"""A governed Bilibili watch keeps the exact source's withdrawal lineage."""
import json
import pytest

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.life.bilibili import BilibiliPublicTransport
from tests.living_release_v4.bilibili_loopback import counterpart
from tests.living_release_v4.test_bilibili_reads import grant, proposal, setup
from tests.world_loop.helpers import fresh, policy


def test_original_source_withdrawal_removes_watch_and_frame_experiences(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (model, _), \
            fresh(tmp_path/'subject.db', Clock()) as runtime:
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9)
        read, source = setup(runtime, opener, transport)
        session = CognitionSession(runtime, model, policy())
        concerns = ConcernService(runtime, resources=(read.port.registry.resource,))
        interpreted = session.execute(session.prepare('lineage-interest', 'INTERPRET', (source,)))
        concerns.offer(interpreted['record_id'])
        event = read.port.bind_event(concerns.opportunity().input, source, discover=False, visual=True)
        cycle = runtime.subject.run(event)
        grant(runtime, read, limit=10)
        _, action = read.propose(cycle.intention_id, expected_revision=1,
                                 args=read.port.args_for_cycle(cycle.cycle_id, source), input_memory_ids=(source,))
        assert read.dispatch(cycle.intention_id, action, expected_revision=1) == 'SUCCEEDED'
        receipt = json.loads(read.kernel.payload(runtime.store.one('actions', action), 'result_json'))
        video, frames = receipt['source_memory_id'], receipt['frame_memory_ids']
        assert len(frames) == 3 and not platform['posts']
        identity = runtime.identity_id
        memory = MemoryService(runtime.store, runtime.authority)
        memory.forget(source, runtime.authority)
        for mid in (video, *frames):
            with pytest.raises(CoreError):
                memory.read(mid)
        with pytest.raises(CoreError):
            read.kernel.payload(runtime.store.one('actions', action), 'result_json')
    with fresh(tmp_path/'subject.db', Clock()) as reopened:
        assert reopened.identity_id == identity
        memory = MemoryService(reopened.store)
        for mid in (video, *frames):
            with pytest.raises(CoreError):
                memory.read(mid)
        from nana_core.actions import ActionKernel
        with pytest.raises(CoreError):
            ActionKernel(reopened.store, None, reopened.authority).payload(reopened.store.one('actions', action), 'result_json')


def test_source_withdrawn_during_fetch_is_not_retained_or_replayed(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (model, _), \
            fresh(tmp_path/'subject.db', Clock()) as runtime:
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9)
        read, source = setup(runtime, opener, transport)
        session = CognitionSession(runtime, model, policy())
        concerns = ConcernService(runtime, resources=(read.port.registry.resource,))
        interpreted = session.execute(session.prepare('race-interest', 'INTERPRET', (source,)))
        concerns.offer(interpreted['record_id'])
        event = read.port.bind_event(concerns.opportunity().input, source, discover=False, visual=True)
        cycle = runtime.subject.run(event)
        grant(runtime, read, limit=10)
        _, action = read.propose(cycle.intention_id, expected_revision=1,
                                 args=read.port.args_for_cycle(cycle.cycle_id, source), input_memory_ids=(source,))
        original = transport.read_video
        def fetch_and_withdraw(*args, **kwargs):
            result = original(*args, **kwargs)
            MemoryService(runtime.store, runtime.authority).forget(source, runtime.authority)
            return result
        transport.read_video = fetch_and_withdraw
        with pytest.raises(CoreError, match='ACTION_PAYLOAD_SOURCE_NOT_CURRENT'):
            read.dispatch(cycle.intention_id, action, expected_revision=1)
        request_count = len(platform['requests'])
        assert request_count > 0 and not platform['posts']
        rows = runtime.store.db.execute("SELECT COUNT(*) FROM continuity_evidence WHERE source_namespace='recorded.project.bilibili.frames'").fetchone()[0]
        assert rows == 0
        active = runtime.store.db.execute("SELECT COUNT(*) FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.bilibili' AND m.lifecycle='ACTIVE'").fetchone()[0]
        assert active == 0
        assert runtime.store.one('actions', action)['state'] == 'UNKNOWN'
        try:
            read.dispatch(cycle.intention_id, action, expected_revision=1)
        except CoreError:
            pass
        assert len(platform['requests']) == request_count


def test_same_video_with_distinct_source_lineage_withdraws_independently(tmp_path):
    from types import SimpleNamespace
    from nana_core.life.bilibili import BilibiliSourceAdapter, PublicReading
    from tests.world_loop.helpers import capture
    with fresh(tmp_path/'subject.db', Clock()) as runtime:
        a = capture(runtime, 'source-a', {'synthetic': 'independent source A'})
        b = capture(runtime, 'source-b', {'synthetic': 'independent source B'})
        adapter = BilibiliSourceAdapter(SimpleNamespace(runtime=runtime, policy=policy()))
        reading = PublicReading('same-video', 'VIDEO_READING', runtime.clock.utc_now_us(),
            {'bvid':'BV1t55v6DE2v', 'cid':8, 'coverage':'METADATA_ONLY_NOT_WATCHED'}, 'SYNTHETIC_FIXTURE')
        first = adapter.ingest(reading, parents=(a,))
        second = adapter.ingest(reading, parents=(b,))
        assert first != second
        memory = MemoryService(runtime.store, runtime.authority)
        memory.forget(a, runtime.authority)
        with pytest.raises(CoreError):
            memory.read(first)
        assert memory.read(second)['memory_id'] == second


def test_governed_watch_semantic_belief_withdraws_with_original_source(tmp_path):
    from types import SimpleNamespace
    from nana_core.continuity.provider_config import CapabilityRoute, ProviderProfile
    from nana_core.continuity.provider_routing import CapabilityRouter, RoutingPolicy, RuntimeProviderFactory
    from nana_core.continuity.providers import ProviderRegistry
    from nana_core.continuity.world_loop.semantic_harness import semantic_proposer
    from nana_core.continuity.world_loop.world import WorldModel
    from nana_core.life.bilibili_frames import BilibiliFrameService
    from tests.provider_routing.helpers import Resolver, config_service, model, update

    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (interest_wire, _), \
            provider_harness(semantic_proposer) as (vision_wire, vision_metrics), \
            fresh(tmp_path/'subject.db', Clock()) as runtime:
        config, authority = config_service(tmp_path/'config/providers.json')
        provider = ProviderProfile(provider_profile_id='frames.loopback', display_name='SYNTHETIC_LOOPBACK',
            protocol='SYNTHETIC_LOOPBACK', base_url=vision_wire.endpoint.removesuffix('/chat/completions'),
            locality='LOCAL_FIXTURE', permitted_privacy=('PUBLIC','PROJECT'))
        profile = model('model.frames', provider.provider_profile_id, ('VISION',)).model_copy(update={'remote_model_id':'harness-v1'})
        update(config, authority, 'UPSERT_PROVIDER', provider=provider)
        update(config, authority, 'UPSERT_MODEL', model=profile)
        update(config, authority, 'SET_CAPABILITY_ROUTE', route=CapabilityRoute(operation='VISION',
            primary_model_profile_id=profile.model_profile_id, permitted_privacy=('PUBLIC','PROJECT')))
        router = CapabilityRouter(config, RuntimeProviderFactory(ProviderRegistry(), Resolver(), RoutingPolicy(allow_synthetic_loopback=True)))
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9)
        read, source = setup(runtime, opener, transport)
        app = read.port.app
        app.router = router
        app.config = SimpleNamespace(provider_wire_bytes_per_day=4_000_000, provider_context_tokens=16000,
            provider_output_tokens=4096, provider_timeout_ms=3000, provider_cost_ceiling_micro=0,
            provider_total_calls_limit=2, provider_total_reserved_cost_micro=0, provider_calls_per_hour=2,
            provider_calls_per_day=2, per_provider_calls_per_day=2)
        session = CognitionSession(runtime, interest_wire, policy())
        concerns = ConcernService(runtime, resources=(read.port.registry.resource,))
        interpretation = session.execute(session.prepare('source-semantic-interest', 'INTERPRET', (source,)))
        concerns.offer(interpretation['record_id'])
        event = read.port.bind_event(concerns.opportunity().input, source, discover=False, visual=True)
        cycle = runtime.subject.run(event)
        grant(runtime, read, limit=10)
        _, action = read.propose(cycle.intention_id, expected_revision=1,
                                 args=read.port.args_for_cycle(cycle.cycle_id, source), input_memory_ids=(source,))
        assert read.dispatch(cycle.intention_id, action, expected_revision=1) == 'SUCCEEDED'
        receipt = json.loads(read.kernel.payload(runtime.store.one('actions', action), 'result_json'))
        frame = max(receipt['frame_memory_ids'], key=lambda mid:
                    json.loads(MemoryService(runtime.store).read(mid)['text'])['source']['at_seconds'])
        result = BilibiliFrameService(app).interpret(frame)
        assert result['state'] == 'SAMPLED_FRAME_INTERPRETED' and vision_metrics['calls'] == 1
        assert result['source_locator']['source_memory_id'] == frame and result['source_locator']['at_seconds'] == 10
        world = WorldModel(runtime.store, scopes=('world',), privacy_classes=('PROJECT',))
        assert world.view(result['entity_id'], 'publication.visual.0').state == 'SUPPORTED_BELIEF'
        MemoryService(runtime.store, runtime.authority).forget(source, runtime.authority)
        assert world.view(result['entity_id'], 'publication.visual.0').state == 'UNKNOWN'
        with pytest.raises(CoreError):
            MemoryService(runtime.store).read(result['semantic_memory_ids'][0])
        assert vision_metrics['calls'] == 1 and not platform['posts']
