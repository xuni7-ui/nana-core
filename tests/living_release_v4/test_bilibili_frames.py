import hashlib
import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from nana_core.contracts import CoreError
from nana_core.clock import Clock
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.life.bilibili import BilibiliPublicTransport, BilibiliSourceAdapter, BilibiliLoopbackOpener
from nana_core.life.bilibili_frames import BilibiliFrameService, VideoFrame
from tests.world_loop.helpers import fresh, policy
from tests.living_release_v4.bilibili_loopback import counterpart
from tests.living_release_v4.test_bilibili_reads import setup, proposal, grant


def test_actual_storyboard_bytes_timestamps_original_memory_and_withdrawal(tmp_path):
    with counterpart() as (opener, platform), fresh(tmp_path / "self.db", Clock()) as r:
        transport = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE", request_limit=9)
        transport.opener = BilibiliLoopbackOpener(opener.endpoint)
        reading = transport.read_video("BV1t55v6DE2v", visual=True)
        assert [f.at_seconds for f in reading.frames] == [0, 5, 10]
        assert transport.calls == 7 and platform["posts"] == 0
        assert reading.payload["coverage"] == "SAMPLED_VIDEO_FRAMES_NOT_FULL_WATCH"
        assert reading.payload["watched"] is False
        with Image.open(io.BytesIO(reading.frames[1].png)) as image:
            assert image.getpixel((5, 5)) == (255, 0, 0)
        app = SimpleNamespace(runtime=r)
        source = BilibiliSourceAdapter(app).ingest(reading)
        frames = BilibiliFrameService(app)
        ids = frames.capture(source, reading.frames)
        assert frames.capture(source, reading.frames) == ids
        assert frames.coverage(source)["visual_frames"] == 3
        row = MemoryService(r.store).read(ids[0])
        assert json.loads(row["text"])["source_byte_digest"] == hashlib.sha256(reading.frames[0].png).hexdigest()
        MemoryService(r.store, r.authority).forget(source, r.authority)
        assert frames.coverage(source)["visual_frames"] == 0
        with pytest.raises(CoreError):
            MemoryService(r.store).read(ids[0])


def test_watch_is_original_c_manager_grant_kernel_bounded_read(tmp_path):
    with (
        counterpart() as (opener, platform),
        provider_harness(proposer=proposal) as (cognition, _),
        fresh(tmp_path / "self.db", Clock()) as r,
    ):
        read, source = setup(
            r, opener, BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE", request_limit=9)
        )
        session = CognitionSession(r, cognition, policy())
        concerns = ConcernService(r, resources=(read.port.registry.resource,))
        interpreted = session.execute(session.prepare("frame-interest", "INTERPRET", (source,)))
        concerns.offer(interpreted["record_id"])
        event = read.port.bind_event(concerns.opportunity().input, source, discover=False, visual=True)
        judged = r.subject.run(event)
        assert judged.realization_target.capability == "bilibili.public.watch"
        grant(r, read, limit=10)
        _, action = read.propose(
            judged.intention_id, expected_revision=1, args=read.port.args_for_cycle(judged.cycle_id, source)
        )
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "SUCCEEDED"
        payload = json.loads(read.kernel.payload(r.store.one("actions", action), "result_json"))
        assert len(payload["frame_memory_ids"]) == 3 and transport_calls(read) == 7
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "SUCCEEDED"
        assert len(platform["requests"]) == 7 and platform["posts"] == 0


def transport_calls(read):
    return read.port.transport.calls


def test_frame_correlation_and_cdn_boundary(tmp_path):
    with counterpart() as (opener, _), fresh(tmp_path / "self.db", Clock()) as r:
        transport = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE", request_limit=9)
        transport.opener = BilibiliLoopbackOpener(opener.endpoint)
        reading = transport.read_video("BV1t55v6DE2v", visual=True)
        app = SimpleNamespace(runtime=r)
        source = BilibiliSourceAdapter(app).ingest(reading)
        f = reading.frames[0]
        with pytest.raises(CoreError, match="BILIBILI_FRAME_CORRELATION_MISMATCH"):
            BilibiliFrameService(app).capture(
                source, (VideoFrame("BV0000000000", f.cid, f.at_seconds, f.png, f.origin),)
            )
        calls = transport.calls
        for url in (
            "https://127.0.0.1/frame.png",
            "file:///frame.png",
            "https://i0.hdslb.com@evil.invalid/a.png",
            "https://i0.hdslb.com/a.png?token=x",
            "https://i0.hdslb.com/a.png#frag",
        ):
            with pytest.raises(CoreError):
                transport._raw(url, image=True)
        assert transport.calls == calls


def test_acquired_frame_uses_real_router_original_h1_world_and_source_lifecycle(tmp_path):
    from nana_core.continuity.provider_config import ProviderProfile, CapabilityRoute
    from nana_core.continuity.provider_routing import CapabilityRouter, RuntimeProviderFactory, RoutingPolicy
    from nana_core.continuity.providers import ProviderRegistry
    from nana_core.continuity.world_loop.semantic_harness import semantic_proposer
    from nana_core.continuity.world_loop.world import WorldModel
    from tests.provider_routing.helpers import config_service, model, update, Resolver

    with (
        counterpart() as (opener, _),
        provider_harness(semantic_proposer) as (wire, metrics),
        fresh(tmp_path / "self.db", Clock()) as r,
    ):
        config, authority = config_service(tmp_path / "config/providers.json")
        provider = ProviderProfile(
            provider_profile_id="frames.loopback",
            display_name="SYNTHETIC_LOOPBACK",
            protocol="SYNTHETIC_LOOPBACK",
            base_url=wire.endpoint.removesuffix("/chat/completions"),
            locality="LOCAL_FIXTURE",
            permitted_privacy=("PUBLIC", "PROJECT"),
        )
        profile = model("model.frames", provider.provider_profile_id, ("VISION",)).model_copy(
            update={"remote_model_id": "harness-v1"}
        )
        update(config, authority, "UPSERT_PROVIDER", provider=provider)
        update(config, authority, "UPSERT_MODEL", model=profile)
        update(
            config,
            authority,
            "SET_CAPABILITY_ROUTE",
            route=CapabilityRoute(
                operation="VISION",
                primary_model_profile_id=profile.model_profile_id,
                permitted_privacy=("PUBLIC", "PROJECT"),
            ),
        )
        router = CapabilityRouter(
            config, RuntimeProviderFactory(ProviderRegistry(), Resolver(), RoutingPolicy(allow_synthetic_loopback=True))
        )
        app = SimpleNamespace(
            runtime=r,
            policy=policy(),
            router=router,
            config=SimpleNamespace(
                provider_wire_bytes_per_day=4_000_000,
                provider_context_tokens=16000,
                provider_output_tokens=4096,
                provider_timeout_ms=3000,
                provider_cost_ceiling_micro=0,
                provider_total_calls_limit=2,
                provider_total_reserved_cost_micro=0,
                provider_calls_per_hour=2,
                provider_calls_per_day=2,
                per_provider_calls_per_day=2,
            ),
        )
        public = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE", request_limit=9)
        public.opener = BilibiliLoopbackOpener(opener.endpoint)
        reading = public.read_video("BV1t55v6DE2v", visual=True)
        source = BilibiliSourceAdapter(app).ingest(reading)
        service = BilibiliFrameService(app)
        mid = service.capture(source, reading.frames)[-1]
        frame_at=reading.frames[-1].at_seconds
        assert frame_at>0
        result = service.interpret(mid)
        assert result["state"] == "SAMPLED_FRAME_INTERPRETED" and metrics["calls"] == 1
        claim = MemoryService(r.store).read(result["semantic_memory_ids"][0])
        assert claim["authority"] == "INFERRED" and claim["source_provenance"]["source_kind"] == "MODEL_DERIVATION"
        locator=json.loads(claim['text'])['source_locator']
        assert locator==result['source_locator']
        assert locator['source_memory_id']==mid and locator['bvid']=='BV1t55v6DE2v'
        assert locator['cid']==reading.frames[-1].cid and locator['at_seconds']==frame_at
        assert locator['timeline_basis']=='PUBLISHER_REPORTED_STORYBOARD_TIME'
        assert locator['coverage']=='PUBLISHER_STORYBOARD_SAMPLE_NOT_FULL_WATCH'
        assert locator['full_video_watched'] is False
        # Source offset is not a model's claim of a long watched interval.
        assert json.loads(claim['text'])['semantic']['start_s']==0
        assert service.interpret(mid)["semantic_memory_ids"] == result["semantic_memory_ids"] and metrics["calls"] == 1
        world = WorldModel(r.store, scopes=("world",), privacy_classes=("PROJECT",))
        assert world.view(result["entity_id"], "publication.visual.0").state == "SUPPORTED_BELIEF"
        from nana_core.continuity.world_loop.cognition import StructuredProposal,InterestProposal
        seen=[]
        def next_interpret(request):
            seen.append(request)
            context=json.loads(request.context_json)
            item=next(json.loads(block['data_json']) for block in context['blocks']
                if block['kind']=='MEMORY' and result['semantic_memory_ids'][0] in block['source_memory_ids'])
            assert json.loads(item['text'])['source_locator']==locator
            return StructuredProposal(interpretation='SYNTHETIC cited sample may warrant further exploration, not a whole video experience',
                source_refs=request.primary_source_refs,interests=(InterestProposal(topic='sampled-visual-detail',
                    motivation_source='CURIOSITY',source_memory_ids=(result['semantic_memory_ids'][0],),expected_value='HIGH',
                    possible_behaviors=('EXPLORE',),interpretation='Consider the cited publisher sample without assuming unseen video content'),))
        with provider_harness(proposer=next_interpret) as (text_wire,text_metrics):
            text_session=CognitionSession(r,text_wire,policy())
            outcome=text_session.execute(text_session.prepare('frame-offset-followup','INTERPRET',tuple(result['semantic_memory_ids'])))
            assert outcome['state']=='PROPOSED' and text_metrics['calls']==1
            from nana_core.life.bilibili import BilibiliReadRealization
            read=BilibiliReadRealization(app,public)
            concerns=ConcernService(r,resources=(read.port.registry.resource,));concerns.offer(outcome['record_id'])
            event=concerns.opportunity().input
            choice=r.subject.run(event)
            assert choice.intention.behavior=='EXPLORE'
        assert len(seen)==1 and metrics['calls']==1
        from nana_core.storage import canonical
        data=json.loads(claim['text']);without={k:v for k,v in data.items() if k!='source_locator'}
        print(json.dumps({'measurement':'frame-source-locator','at_seconds':frame_at,
            'added_bytes_per_semantic_memory':len(claim['text'].encode())-len(canonical(without).encode()),
            'vision_http_calls':metrics['calls'],'followup_interpret_calls':text_metrics['calls'],
            'followup_request_json_bytes':len(seen[0].model_dump_json().encode()),
            'subject_behavior':choice.intention.behavior,'model_belief_not_truth':result['proposal_not_truth'],
            'real_model_calls':0,'provider_tokens':None}))
        MemoryService(r.store, r.authority).forget(source, r.authority)
        assert world.view(result["entity_id"], "publication.visual.0").state == "UNKNOWN"
        with pytest.raises(CoreError,match='MEMORY_UNAVAILABLE'):
            MemoryService(r.store).read(claim['memory_id'])


@pytest.mark.parametrize('bad_sample',[None,{'bvid':'BV1t55v6DE2v','cid':9,'at_seconds':86401,
    'coverage':'PUBLISHER_STORYBOARD_SAMPLE_NOT_FULL_WATCH'}])
def test_invalid_frame_locator_is_rejected_before_provider_dispatch(tmp_path,bad_sample):
    from nana_core.continuity.world_loop.semantic_harness import semantic_harness
    from nana_core.continuity.world_loop.samples import media_samples
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    from nana_core.storage import canonical
    from tests.h1_semantics.test_grounding import ingest,setup as semantic_setup
    with fresh(tmp_path/'self.db') as r,semantic_harness() as (transport,metrics):
        raw=media_samples()['IMAGE'];base=ingest(r,'IMAGE',raw);memory=MemoryService(r.store)
        body=json.loads(memory.read(base)['text']);body['source']=bad_sample;text=canonical(body)
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',
            source_namespace='recorded.project.bilibili.frames',source_reference='synthetic-invalid-locator',
            source_kind='DIRECT_OBSERVATION'),text=text,privacy_class='PROJECT',observed_time_us=r.clock.utc_now_us()))
        mid=memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.EPISODIC,
            epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text))
        service=semantic_setup(r,transport)
        with pytest.raises(CoreError,match='MEDIA_FRAME_LOCATOR_INVALID'):service.prepare('bad-frame-locator',mid,raw)
        assert metrics['calls']==0 and not r.store.all('cognitive_requests')
