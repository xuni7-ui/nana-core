"""No supplied BV target: sourced curiosity -> original C -> search -> cited
choice -> separate original C -> bounded actual HTTP loopback -> World/Concern.
Synthetic cognition and platform are explicitly not real semantic qualification.
"""

import json
from types import SimpleNamespace

from nana_core.clock import Clock
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.continuity.world_loop.cognition import CognitionSession, StructuredProposal, InterestProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.life.bilibili import BilibiliLoopbackOpener, BilibiliPublicTransport
from nana_core.life.bilibili_life import BilibiliLife, BilibiliLifeConfig
from tests.living_release_v4.bilibili_loopback import counterpart
from tests.living_release_v4.test_bilibili_reads import grant
from tests.world_loop.helpers import fresh, policy, capture


def model(r, request):
    candidates = []
    for block in json.loads(request.context_json)["blocks"]:
        if block["kind"] != "MEMORY":
            continue
        item = json.loads(block["data_json"])
        if item["memory_id"] not in request.primary_source_refs:
            continue
        try:
            row = json.loads(item["text"])
        except ValueError:
            continue
        if row.get("kind") == "VIDEO_METADATA" and row["data"]["bvid"] == "BV2t55v6DE2v":
            candidates.append(item["memory_id"])
    sources = (candidates[-1],) if candidates else request.primary_source_refs
    return StructuredProposal(
        interpretation="Synthetic public source comparison, not real viewing",
        source_refs=request.primary_source_refs,
        interests=(
            InterestProposal(
                topic="selected-astronomy" if candidates else "astronomy",
                motivation_source="CURIOSITY",
                source_memory_ids=sources,
                expected_value="HIGH",
                possible_behaviors=("EXPLORE",),
                interpretation="Explore the cited source",
            ),
        ),
    )


def app_for(r, session):
    return SimpleNamespace(
        runtime=r,
        policy=policy(),
        router=None,
        config=SimpleNamespace(
            provider_context_tokens=8192,
            provider_output_tokens=1024,
            provider_timeout_ms=3000,
            provider_cost_ceiling_micro=0,
        ),
        _session=lambda privacy: session,
    )


def initial(r, session, life):
    source = capture(r, "independent-interest", {"public_question": "Astronomy source reliability"})
    result = session.execute(session.prepare("own-interest", "INTERPRET", (source,)))
    life.concerns.offer(result["record_id"])
    return source


def judge_queued(r, qid):
    for _ in range(30):
        r.step()
        if r.store.one("runtime_queue", qid)["state"] == "DONE":
            return
    raise AssertionError("Original runtime did not finish its queued judgment")


def test_interest_selection_and_restart_job_cursor_never_pick_first_or_repeat_http(tmp_path):
    with (
        counterpart() as (opener, platform),
        fresh(tmp_path / "self.db", Clock()) as r,
        provider_harness(proposer=lambda req: model(r, req)) as (transport, _),
    ):
        platform["search_results"] = [
            {"bvid": "BV1t55v6DE2v", "aid": 7, "cid": 8, "title": "First unselected result"},
            {"bvid": "BV2t55v6DE2v", "aid": 9, "cid": 10, "title": "Independently cited second result"},
        ]
        session = CognitionSession(r, transport, policy())
        app = app_for(r, session)
        public = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE", request_limit=16)
        public.opener = BilibiliLoopbackOpener(opener.endpoint)
        cfg = BilibiliLifeConfig(
            enabled=True,
            read_authorized=True,
            interpret_materials=True,
            review_interval_seconds=30,
            max_reads_per_day=2,
        )
        life = BilibiliLife(app, None, cfg, transport=public)
        GovernanceController(r.store, r.authority).initialize(r.authority)
        grant(r, life.read, limit=16)
        initial(r, session, life)
        offered = life.opportunity()
        assert offered["not_dispatched"] and platform["requests"] == []
        judge_queued(r, offered["queue_id"])
        first = life.maintenance_slice()
        assert first["phase"] == "MATERIALS" and len(platform["requests"]) == 1
        # Reconstruct the adapter from original Store cursor; no second Runtime.
        recovered = BilibiliLife(app, None, cfg, transport=public)
        assert recovered.maintenance_slice()["result"] == "SOURCED_INTERPRETATION_REQUIRES_NEXT_C"
        offered = recovered.opportunity()
        assert offered["not_dispatched"] and len(platform["requests"]) == 1
        judge_queued(r, offered["queue_id"])
        assert recovered.maintenance_slice()["phase"] == "MATERIALS"
        assert len(platform["requests"]) == 6 and platform["posts"] == 0
        assert "bvid=BV2t55v6DE2v" in platform["requests"][1][1]
        # An effect already verified before cursor commit is reused locally.
        assert recovered.maintenance_slice()["state"] == "DONE"
        assert recovered.opportunity() is None and len(platform["requests"]) == 6
        assert len(r.store.all("actions")) == 2


def test_no_interest_or_missing_original_grant_never_requests_platform(tmp_path):
    with (
        counterpart() as (opener, platform),
        fresh(tmp_path / "self.db", Clock()) as r,
        provider_harness(proposer=lambda req: model(r, req)) as (transport, _),
    ):
        session = CognitionSession(r, transport, policy())
        app = app_for(r, session)
        public = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE")
        public.opener = BilibiliLoopbackOpener(opener.endpoint)
        cfg = BilibiliLifeConfig(enabled=True, read_authorized=True, review_interval_seconds=30)
        life = BilibiliLife(app, None, cfg, transport=public)
        GovernanceController(r.store, r.authority).initialize(r.authority)
        assert life.opportunity() is None and platform["requests"] == []
        initial(r, session, life)
        life.next_at = 0
        offered = life.opportunity()
        judge_queued(r, offered["queue_id"])
        blocked = life.maintenance_slice()
        assert blocked["state"] == "BLOCKED" and platform["requests"] == []


def test_declining_interest_does_not_schedule_tasks_or_force_activity(tmp_path):
    with (
        fresh(tmp_path / "self.db", Clock()) as r,
        provider_harness(
            proposer=lambda req: StructuredProposal(
                interpretation="No useful next step", source_refs=req.primary_source_refs
            )
        ) as (transport, _),
    ):
        session = CognitionSession(r, transport, policy())
        app = app_for(r, session)
        life = BilibiliLife(app, None, BilibiliLifeConfig())
        source = capture(r, "quiet-source", {"notice": "Public low-value source"})
        result = session.execute(session.prepare("no-interest", "INTERPRET", (source,)))
        assert life.concerns.offer(result["record_id"]) == ()
        assert life.opportunity() is None and not r.store.all("jobs")


def test_unknown_read_is_parked_across_adapter_recovery_without_another_request(tmp_path):
    with (
        counterpart() as (opener, platform),
        fresh(tmp_path / "self.db", Clock()) as r,
        provider_harness(proposer=lambda req: model(r, req)) as (transport, _),
    ):
        session = CognitionSession(r, transport, policy())
        app = app_for(r, session)
        public = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE")
        public.opener = BilibiliLoopbackOpener(opener.endpoint)
        cfg = BilibiliLifeConfig(enabled=True, read_authorized=True, review_interval_seconds=30)
        life = BilibiliLife(app, None, cfg, transport=public)
        GovernanceController(r.store, r.authority).initialize(r.authority)
        grant(r, life.read, limit=16)
        initial(r, session, life)
        offered = life.opportunity()
        judge_queued(r, offered["queue_id"])
        platform["read_unavailable"] = True
        assert life.maintenance_slice()["state"] == "UNKNOWN"
        assert len(platform["requests"]) == 1
        restarted = BilibiliLife(app, None, cfg, transport=public)
        assert restarted.maintenance_slice() is None and restarted.opportunity() is None
        assert len(platform["requests"]) == 1
