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
from nana_core.life.bilibili import BilibiliPublicTransport, BilibiliSourceAdapter
from nana_core.life.bilibili_frames import BilibiliFrameService, VideoFrame
from tests.world_loop.helpers import fresh, policy
from tests.living_release_v4.bilibili_loopback import counterpart
from tests.living_release_v4.test_bilibili_reads import setup, proposal, grant


def test_actual_storyboard_bytes_timestamps_original_memory_and_withdrawal(tmp_path):
    with counterpart() as (opener, platform), fresh(tmp_path / "self.db", Clock()) as r:
        transport = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE", request_limit=9)
        transport.opener = opener
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
        transport.opener = opener
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
        public.opener = opener
        reading = public.read_video("BV1t55v6DE2v", visual=True)
        source = BilibiliSourceAdapter(app).ingest(reading)
        service = BilibiliFrameService(app)
        mid = service.capture(source, reading.frames)[0]
        result = service.interpret(mid)
        assert result["state"] == "SAMPLED_FRAME_INTERPRETED" and metrics["calls"] == 1
        claim = MemoryService(r.store).read(result["semantic_memory_ids"][0])
        assert claim["authority"] == "INFERRED" and claim["source_provenance"]["source_kind"] == "MODEL_DERIVATION"
        assert service.interpret(mid)["semantic_memory_ids"] == result["semantic_memory_ids"] and metrics["calls"] == 1
        world = WorldModel(r.store, scopes=("world",), privacy_classes=("PROJECT",))
        assert world.view(result["entity_id"], "publication.visual.0").state == "SUPPORTED_BELIEF"
        MemoryService(r.store, r.authority).forget(source, r.authority)
        assert world.view(result["entity_id"], "publication.visual.0").state == "UNKNOWN"
