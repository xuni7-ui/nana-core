from types import SimpleNamespace

import pytest

from nana_core.contracts import CoreError, GrantSpec
from nana_core.clock import Clock
from nana_core.continuity.autonomy.governance import GovernanceController, ManagerConstraint
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionSession, InterestProposal, StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.life.bilibili import BilibiliPublicTransport, BilibiliReadRealization, PublicReading, BilibiliLoopbackOpener
from tests.world_loop.helpers import fresh, policy
from tests.living_release_v4.bilibili_loopback import counterpart


def proposal(request):
    return StructuredProposal(interpretation="Synthetic source suggests a bounded public question",
        source_refs=request.primary_source_refs, interests=(InterestProposal(topic="source-reliability", motivation_source="CURIOSITY",
            source_memory_ids=request.primary_source_refs, expected_value="HIGH", interpretation="Compare sources",
            possible_behaviors=("EXPLORE",)),))


def setup(r, opener, transport):
    transport.opener = BilibiliLoopbackOpener(opener.endpoint)
    app = SimpleNamespace(runtime=r, policy=policy())
    read = BilibiliReadRealization(app, transport)
    GovernanceController(r.store, r.authority).initialize(r.authority)
    source = read.port.sources.ingest(PublicReading("BV1t55v6DE2v", "VIDEO_METADATA", r.clock.utc_now_us(),
        {"bvid": "BV1t55v6DE2v", "title": "Synthetic source", "coverage": "METADATA_ONLY_NOT_WATCHED"}, "SYNTHETIC_FIXTURE"))
    return read, source


def cycle(r, read, source, cognition, *, discover=True):
    session = CognitionSession(r, cognition, policy())
    concerns = ConcernService(r, resources=(read.port.registry.resource,))
    result = session.execute(session.prepare("question-" + str(discover), "INTERPRET", (source,)))
    concerns.offer(result["record_id"])
    event = read.port.bind_event(concerns.opportunity().input, source, discover=discover)
    return r.subject.run(event)


def grant(r, read, *, limit=12):
    now = r.clock.utc_now_us()
    read.kernel.set_budgets({"write_attempts": 0, "external_requests": limit, "cost_micro_units": limit}, r.authority)
    return read.kernel.grant(GrantSpec(capabilities=tuple(read.port.registry.definitions) + (read.port.registry.verify_capability,),
        resources=(read.port.registry.resource,), not_before_us=now, expires_at_us=now + 100_000_000), r.authority)


@pytest.mark.parametrize("discover,expected_calls", [(True, 1), (False, 5)])
def test_original_c_manager_kernel_real_loopback_reads_record_sources_only(tmp_path, discover, expected_calls):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (cognition, _), fresh(tmp_path / "self.db", Clock()) as r:
        transport = BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE")
        read, source = setup(r, opener, transport)
        judged = cycle(r, read, source, cognition, discover=discover)
        assert judged.evaluation.normative == "ENDORSED"
        grant(r, read)
        args = read.port.args_for_cycle(judged.cycle_id, source)
        assert args["query"] == "source reliability" if discover else args["bvid"] == "BV1t55v6DE2v"
        outcome, action = read.propose(judged.intention_id, expected_revision=1, args=args, input_memory_ids=(source,))
        assert outcome.result == "PASS"
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "SUCCEEDED"
        assert transport.calls == expected_calls == len(platform["requests"])
        assert platform["posts"] == 0 and r.store.one("budgets", "write_attempts")["spent"] == 0
        receipt = __import__("json").loads(read.kernel.payload(r.store.one("actions", action), "result_json"))
        memory = read.port._source(receipt["source_memory_id"])[1]
        assert memory["origin"] == "SYNTHETIC_FIXTURE" and memory["watched"] is False
        assert memory["kind"] == ("DISCOVERY" if discover else "VIDEO_READING")
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "SUCCEEDED"
        assert transport.calls == expected_calls


def test_manager_veto_and_grant_absence_prevent_all_public_http(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (cognition, _), fresh(tmp_path / "self.db", Clock()) as r:
        read, source = setup(r, opener, BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE"))
        judged = cycle(r, read, source, cognition)
        args = read.port.args_for_cycle(judged.cycle_id, source)
        _, action = read.propose(judged.intention_id, expected_revision=1, args=args)
        with pytest.raises(CoreError, match="AUTH_REQUIRED"):
            read.dispatch(judged.intention_id, action, expected_revision=1)
        controller = GovernanceController(r.store, r.authority)
        controller.install(ManagerConstraint(constraint_id="read-veto", revision=1, issuer=r.authority.principal,
            source_reference="synthetic-veto", identity_id=r.identity_id, scope="world", targets=(judged.realization_target,),
            effective_from_us=r.clock.utc_now_us(), expires_at_us=r.clock.utc_now_us()+100_000_000, reason_code="HOST_READ_DENIED"), r.authority)
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "INTENTION_BLOCKED_MANAGER"
        assert platform["requests"] == []


def test_forged_source_or_query_and_budget_cannot_bypass_original_read(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (cognition, _), fresh(tmp_path / "self.db", Clock()) as r:
        read, source = setup(r, opener, BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE"))
        judged = cycle(r, read, source, cognition, discover=False)
        grant(r, read, limit=1)
        args = read.port.args_for_cycle(judged.cycle_id, source)
        _, action = read.propose(judged.intention_id, expected_revision=1, args=args)
        with pytest.raises(CoreError, match="BUDGET_EXHAUSTED"):
            read.dispatch(judged.intention_id, action, expected_revision=1)
        assert platform["requests"] == []
        with pytest.raises(CoreError, match="BILIBILI_C_SOURCE_MISMATCH"):
            read.port.args_for_cycle(judged.cycle_id, "forged-source")


def test_substituted_query_is_parked_without_http_or_blind_retry(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (cognition, _), fresh(tmp_path / "self.db", Clock()) as r:
        read, source = setup(r, opener, BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE"))
        judged = cycle(r, read, source, cognition)
        grant(r, read)
        args = read.port.args_for_cycle(judged.cycle_id, source)
        args["query"] = "Substituted query outside the source concern"
        _, action = read.propose(judged.intention_id, expected_revision=1, args=args)
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "UNKNOWN"
        assert read.dispatch(judged.intention_id, action, expected_revision=1) == "UNKNOWN"
        assert platform["requests"] == []


def test_source_withdrawal_blocks_pending_read_at_original_manager_gate(tmp_path):
    from nana_core.continuity.memory import MemoryService
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (cognition, _), fresh(tmp_path / "self.db", Clock()) as r:
        read, source = setup(r, opener, BilibiliPublicTransport(authorized=True, origin="SYNTHETIC_FIXTURE"))
        judged = cycle(r, read, source, cognition)
        grant(r, read)
        _, action = read.propose(judged.intention_id, expected_revision=1, args=read.port.args_for_cycle(judged.cycle_id, source))
        MemoryService(r.store, r.authority).forget(source, r.authority)
        with pytest.raises(CoreError):
            read.dispatch(judged.intention_id, action, expected_revision=1)
        assert platform["requests"] == []
