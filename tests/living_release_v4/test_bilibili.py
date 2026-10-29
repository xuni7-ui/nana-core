import pytest

from nana_core.contracts import CoreError
from nana_core.life.bilibili import BilibiliPublicTransport, BilibiliSourceAdapter, PublicReading


def test_public_transport_bounds_and_no_ambient_credentials():
    port = BilibiliPublicTransport()
    with pytest.raises(CoreError, match="BILIBILI_READ_NOT_AUTHORIZED"):
        port.video("BV1t55v6DE2v")
    assert port.calls == 0
    allowed = BilibiliPublicTransport(authorized=True)
    with pytest.raises(CoreError, match="BILIBILI_VIDEO_ID_INVALID"):
        allowed.video("https://private.invalid/")
    assert allowed.calls == 0


def test_original_memory_world_concern_c_and_withdrawal(tmp_path):
    from nana_core.life.application import LifeApplication
    from nana_core.life.config import load_config, update_config
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.world_loop.world import WorldModel
    from nana_core.continuity.world_loop.cognition import CognitionReply, StructuredProposal, InterestProposal
    from nana_core.storage import digest
    from tests.first_life_android_v2.test_supervisor import owned
    from tests.provider_routing.helpers import fixture_router, update

    home, _, _ = owned(tmp_path)
    cfg = load_config(home)
    update_config(home, cfg.model_copy(update={"revision": cfg.revision + 1, "provider_calls_per_day": 2,
                  "provider_calls_per_hour": 2, "per_provider_calls_per_day": 2,
                  "provider_total_calls_limit": 2}), expected_revision=cfg.revision)
    router, config, authority, registry, ports = fixture_router(tmp_path / "router")
    provider = config.load().providers[0].model_copy(update={"permitted_privacy": ("PUBLIC", "PROJECT")})
    update(config, authority, "UPSERT_PROVIDER", provider=provider)
    route = config.load().routes[0].model_copy(update={"permitted_privacy": ("PUBLIC", "PROJECT")})
    update(config, authority, "SET_CAPABILITY_ROUTE", route=route)
    model = config.load().models[0]
    registry.unregister(model.model_profile_id)
    registry.register(model.descriptor(provider), ports[0])

    def exchange(request):
        ports[0].calls += 1
        return CognitionReply(request_id=request.request_id, request_digest=digest(request.model_dump(mode="json")),
            provider_id=ports[0].provider_id, model_id=ports[0].model_id, origin="SYNTHETIC",
            proposal=StructuredProposal(interpretation="The publisher metadata raises a bounded question about source reliability.",
                source_refs=request.primary_source_refs, confidence=.7,
                interests=(InterestProposal(topic="bilibili-source-reliability", motivation_source="CURIOSITY",
                    source_memory_ids=request.primary_source_refs, interpretation="Consider the source before endorsing its claims.",
                    expected_value="HIGH", possible_behaviors=("EXPLORE", "WATCH")),)), cost_micro=0, billing="FIXTURE_ZERO")

    ports[0].exchange = exchange
    with LifeApplication(home, router=router) as app:
        adapter = BilibiliSourceAdapter(app)
        reading = PublicReading("BV1t55v6DE2v", "VIDEO_METADATA", app.runtime.clock.utc_now_us(),
                                {"bvid": "BV1t55v6DE2v", "title": "Fixture source, not a real watch", "coverage": "METADATA_ONLY_NOT_WATCHED"}, "SYNTHETIC_FIXTURE")
        identity = app.runtime.identity_id
        mid = adapter.ingest(reading)
        assert adapter.ingest(reading) == mid
        assert len(adapter.history(privacy=("PROJECT",))["items"]) == 1
        assert adapter.history(privacy=("PUBLIC",))["items"] == []
        assert adapter.history(privacy=("PROJECT",), scope="different-scope")["items"] == []
        assert adapter.history(privacy=("PROJECT",), entity_id="different-entity")["items"] == []
        result = adapter.interpret(mid)
        assert result["state"] == "INTERPRETED_NOT_WATCHED" and result["concern_ids"]
        assert result["queue_id"] is not None and ports[0].calls == 1
        for _ in range(8):
            app.tick()
            if app.runtime.store.one("runtime_queue", result["queue_id"])["state"] == "DONE":
                break
        assert app.runtime.store.one("runtime_queue", result["queue_id"])["state"] == "DONE"
        assert app.runtime.store.all("subject_cycles")
        world = WorldModel(app.runtime.store, scopes=app.runtime.config.scopes, privacy_classes=("PROJECT",))
        assert world.view(result["entity_id"], "publication.interpretation").state == "SUPPORTED_BELIEF"
        MemoryService(app.runtime.store, app.runtime.authority).forget(mid, app.runtime.authority)
        assert world.view(result["entity_id"], "publication.interpretation").state == "UNKNOWN"
        with pytest.raises(CoreError):
            adapter.ingest(reading)
        assert app.runtime.identity_id == identity and not app.runtime.store.all("grants")


@pytest.mark.parametrize("context_privacy", ["PROJECT", "PERSONAL"])
def test_model_interpretation_retains_all_context_dependencies_and_privacy(tmp_path, context_privacy):
    from types import SimpleNamespace
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.world_loop.cognition import CognitionSession, StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    from tests.world_loop.helpers import fresh, policy, capture

    with fresh(tmp_path / "self.db") as runtime, provider_harness(proposer=lambda request: StructuredProposal(
            interpretation="A bounded source comparison", source_refs=request.primary_source_refs)) as (transport, _):
        adapter = BilibiliSourceAdapter(SimpleNamespace(runtime=runtime))
        source = adapter.ingest(PublicReading("BV1t55v6DE2v", "VIDEO_METADATA", runtime.clock.utc_now_us(),
            {"bvid": "BV1t55v6DE2v", "title": "Synthetic source"}, "SYNTHETIC_FIXTURE"))
        extra = capture(runtime, "comparison-context", {"context": "Synthetic comparison context"}, privacy=context_privacy)
        session = CognitionSession(runtime, transport, policy())
        proposal = session.execute(session.prepare("source-comparison", "INTERPRET", (source, extra)))["record_id"]
        if context_privacy == "PERSONAL":
            with pytest.raises(CoreError, match="BILIBILI_DERIVATION_PRIVACY_DENIED"):
                adapter.apply_proposal(source, session, proposal)
            return
        derived = adapter.apply_proposal(source, session, proposal)["derived_memory_id"]
        memory = MemoryService(runtime.store, runtime.authority)
        assert memory.read(derived)["privacy_class"] == "PROJECT"
        assert runtime.store.db.execute("SELECT 1 FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY' AND parent_id=?",
            (derived, extra)).fetchone()
        memory.forget(extra, runtime.authority)
        with pytest.raises(CoreError):
            memory.read(derived)
