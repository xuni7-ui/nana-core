import json
from dataclasses import replace

import pytest

from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError, GrantSpec, Invocation
from nana_core.life.bilibili_account import (
    BilibiliAccountPolicy, BilibiliAccountTransport, BilibiliActionPort, BilibiliActionRegistry, BilibiliAccountRealization,
)
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.storage import Store
from tests.living_release_v4.test_bilibili_material import Response


class Platform:
    """An independent recorded-shape account counterpart, not a real account."""
    def __init__(self):
        self.posts = 0
        self.rows = []
        self.lose_response = False
        self.read_unavailable = False
        self.requests = []
        self.account_id = 42
        self.logged_in = True

    def open(self, request, timeout):
        self.requests.append((request.method, request.full_url))
        if request.method == "POST":
            self.posts += 1
            from urllib.parse import parse_qs
            body = parse_qs(request.data.decode())
            assert body["csrf"] == ["TESTONLYNOTSECRET0123456789"]
            self.rows.append({"rpid": self.posts, "root": 0, "member": {"mid": 42},
                              "content": {"message": body["message"][0]}})
            if self.lose_response:
                raise TimeoutError()
            data = {"rpid": self.posts}
        else:
            if self.read_unavailable:
                raise TimeoutError()
            data = ({"isLogin": self.logged_in, "mid": self.account_id}
                    if "/web-interface/nav" in request.full_url else {"replies": self.rows})
        return Response(json.dumps({"code": 0, "data": data}).encode())


def setup(tmp_path, *, limit=10):
    resolver = MemorySecretResolver()
    resolver.bind("bili.cookie", "TEST_ONLY_NOT_SECRET_COOKIE")
    resolver.bind("bili.csrf", "TESTONLYNOTSECRET0123456789")
    policy = BilibiliAccountPolicy(42, True, True, True, (43,), 32)
    transport = BilibiliAccountTransport(resolver, cookie_ref="bili.cookie", csrf_ref="bili.csrf", policy=policy)
    platform = Platform()
    transport.opener = platform
    clock = ManualClock()
    store = Store(tmp_path / "original.db", clock)
    authority = OperatorAuthority()
    port = BilibiliActionPort(store, transport)
    kernel = ActionKernel(store, port, authority, registry=BilibiliActionRegistry())
    kernel.set_budgets({"write_attempts": limit, "external_requests": limit, "cost_micro_units": limit}, authority)
    kernel.grant(GrantSpec(capabilities=("bilibili.comment.send", "bilibili.action.verify"),
                          resources=("project://bilibili/comment/7",), not_before_us=clock.utc_now_us(),
                          expires_at_us=clock.utc_now_us() + 100_000_000), authority)
    return store, kernel, port, transport, platform, authority, clock


def test_original_kernel_reserves_precheck_and_single_send_then_independent_verify(tmp_path):
    store, kernel, _, transport, platform, _, _ = setup(tmp_path)
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Recorded comment"})
        assert kernel.run(action) == "SUCCEEDED"
        assert platform.posts == 1 and transport.calls == 4
        assert store.one("budgets", "external_requests")["spent"] == 4
        assert "/web-interface/nav" in platform.requests[0][1]
        assert kernel.run(action) == "SUCCEEDED" and platform.posts == 1


@pytest.mark.parametrize("limit", [1, 2])
def test_insufficient_original_budget_blocks_all_network_before_precheck(tmp_path, limit):
    store, kernel, _, transport, platform, _, _ = setup(tmp_path, limit=limit)
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Denied"})
        with pytest.raises(CoreError, match="BUDGET_EXHAUSTED"):
            kernel.prepare(action)
        assert transport.calls == platform.posts == 0


def test_unknown_after_send_never_repeats_and_restart_verifies_platform_effect(tmp_path):
    store, kernel, _, transport, platform, authority, clock = setup(tmp_path)
    platform.lose_response = True
    original_open = platform.open
    def lose_then_block_read(request, timeout):
        if platform.posts:
            platform.read_unavailable = True
        return original_open(request, timeout)
    transport.opener.open = lose_then_block_read
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Sent once"})
        assert kernel.run(action) == "UNKNOWN" and platform.posts == 1
        assert kernel.run(action) == "UNKNOWN" and platform.posts == 1
    transport.opener.open = original_open
    platform.read_unavailable = False
    with Store(tmp_path / "original.db", clock) as restarted:
        port = BilibiliActionPort(restarted, transport)
        recovered = ActionKernel(restarted, port, authority, registry=BilibiliActionRegistry())
        assert recovered.recover()[action] == "SUCCEEDED"
        assert platform.posts == 1


def test_forged_invocation_and_missing_account_writer_never_dispatch(tmp_path):
    store, _, port, transport, platform, _, _ = setup(tmp_path)
    with store:
        fake = Invocation(action_id="made-up", attempt_id="made-up", capability="bilibili.comment.send",
            resource="project://bilibili/comment/7", args={}, args_hash="made-up", idempotency_key="made-up")
        with pytest.raises(CoreError, match="BILIBILI_KERNEL_ACTION_UNBOUND"):
            port.execute(fake)
        transport.policy = replace(transport.policy, exclusive_writer_confirmed=False)
        with pytest.raises(CoreError, match="BILIBILI_ACCOUNT_WRITER_NOT_AUTHORIZED"):
            transport.send_comment(7, "No")
        assert platform.posts == transport.calls == 0


def test_public_comment_cannot_export_private_source():
    with pytest.raises(CoreError, match="BILIBILI_PUBLIC_PRIVACY_DENIED"):
        BilibiliActionRegistry().validate("bilibili.comment.send", "project://bilibili/comment/7",
                                        {"target_id": 7, "text": "Private", "data_privacy": "PERSONAL"})


@pytest.mark.parametrize("updates,operation,code", [
    ({"read_authorized": False}, "read", "BILIBILI_ACCOUNT_READ_NOT_AUTHORIZED"),
    ({"send_authorized": False}, "send", "BILIBILI_ACCOUNT_WRITER_NOT_AUTHORIZED"),
    ({"exclusive_writer_confirmed": False}, "send", "BILIBILI_ACCOUNT_WRITER_NOT_AUTHORIZED"),
    ({"permitted_recipients": ()}, "dm", "BILIBILI_CONTACT_NOT_AUTHORIZED"),
    ({"request_limit": 0}, "send", "BILIBILI_ACCOUNT_BUDGET"),
])
def test_explicit_account_policy_blocks_before_secret_or_http(tmp_path, updates, operation, code):
    _, _, _, transport, platform, _, _ = setup(tmp_path)
    transport.policy = replace(transport.policy, **updates)
    with pytest.raises(CoreError, match=code):
        if operation == "read":
            transport.sessions()
        elif operation == "dm":
            transport.send_message(43, "No", "key")
        else:
            transport.send_comment(7, "No")
    assert transport.calls == platform.posts == 0


def test_write_revocation_still_allows_original_independent_readback(tmp_path):
    store, kernel, _, transport, platform, _, _ = setup(tmp_path)
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Once"})
        kernel.prepare(action)
        assert kernel.dispatch(action) == "PENDING_VERIFY"
        transport.policy = replace(transport.policy, send_authorized=False, exclusive_writer_confirmed=False)
        assert kernel.verify(action) == "SUCCEEDED" and platform.posts == 1


def account_cycle(store, authority):
    from nana_core.continuity import IdentityService
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
    from nana_core.continuity.subject import SubjectLoop, SubjectInput
    from nana_core.continuity.subject.opportunities import ConcernCue
    from nana_core.continuity.autonomy.contracts import RealizationTarget
    IdentityService(store, authority)
    memory = MemoryService(store)
    memory.entity("observer", "PERSON")
    cue = ConcernCue(cue_kind="OPPORTUNITY", motivation_source="RELATIONSHIP", topic_key="bili-comment",
        possible_behaviors=("SOCIALIZE",), availability="AVAILABLE")
    evidence = memory.capture(EvidenceInput(provenance=Provenance(source_namespace="synthetic.bilibili-account",
        source_reference="opportunity", source_kind="DIRECT_OBSERVATION"), text=cue.model_dump_json(),
        privacy_class="PUBLIC", observed_time_us=store.clock.utc_now_us()))
    source = memory.add(MemoryCandidate(entity_id="observer", scope="world", memory_type=MemoryType.EPISODIC,
        epistemic_kind="OBSERVATION", source_evidence_id=evidence, text=cue.model_dump_json(), predicate_key="concern.open.bili-comment"))
    target = RealizationTarget(capability="bilibili.comment.send", operation="WRITE", resource="project://bilibili/comment/7", resource_class="ORDINARY")
    result = SubjectLoop(store, scopes=("world",), privacy_classes=("PUBLIC",)).run(SubjectInput(source_key="synthetic.bili-comment",
        kind="INTERACTION", origin="USER", entity_id="observer", scope="world", observed_at_us=store.clock.utc_now_us(),
        text="Synthetic account reply opportunity", privacy_class="PUBLIC", source_memory_ids=(source,), realization_target=target))
    assert result.intention.kind == "SOCIAL_INTERACTION" and result.evaluation.normative == "ENDORSED"
    return result


def governed(store, authority, endpoint, *, grant=True):
    from nana_core.continuity.autonomy.governance import GovernanceController
    resolver = MemorySecretResolver()
    resolver.bind("bili.cookie", "TEST_ONLY_NOT_SECRET_COOKIE")
    resolver.bind("bili.csrf", "TESTONLYNOTSECRET0123456789")
    transport = BilibiliAccountTransport(resolver, cookie_ref="bili.cookie", csrf_ref="bili.csrf",
        policy=BilibiliAccountPolicy(42, True, True, True, (43,), 32), realm="SYNTHETIC_LOOPBACK", loopback_endpoint=endpoint)
    GovernanceController(store, authority).initialize(authority)
    read = BilibiliAccountRealization(store, transport, authority)
    read.kernel.set_budgets({"write_attempts": 4, "external_requests": 12, "cost_micro_units": 12}, authority)
    if grant:
        read.kernel.grant(GrantSpec(capabilities=("bilibili.comment.send", "bilibili.action.verify"), resources=("project://bilibili/comment/7",),
            not_before_us=store.clock.utc_now_us(), expires_at_us=store.clock.utc_now_us()+100_000_000), authority)
    return read, transport


@pytest.mark.parametrize("lose_response", [False, True])
def test_actual_synthetic_http_original_c_manager_grant_kernel_verify_and_restart(tmp_path, lose_response):
    from nana_core.continuity import ContinuityStore
    from tests.living_release_v4.bilibili_loopback import counterpart
    path, clock, authority = tmp_path / "self.db", ManualClock(), OperatorAuthority()
    with counterpart() as (opener, platform):
        platform["lose_response"] = lose_response
        with ContinuityStore(path, clock, schema_target=13) as store:
            cycle = account_cycle(store, authority)
            read, transport = governed(store, authority, opener.endpoint)
            outcome, action = read.propose(cycle.intention_id, expected_revision=1, args={"target_id": 7, "text": "Sent once"})
            assert outcome.result == "PASS"
            expected = "UNKNOWN" if lose_response else "SUCCEEDED"
            assert read.dispatch(cycle.intention_id, action, expected_revision=1) == expected
            assert platform["posts"] == 1 and transport.calls == 4
            assert [method for method, _ in platform["requests"]] == ["GET", "GET", "POST", "GET"]
            assert "/web-interface/nav" in platform["requests"][0][1]
            assert read.dispatch(cycle.intention_id, action, expected_revision=1) == expected
            assert platform["posts"] == 1
            assert store.one("core_meta", "cloud.shadow_runtime")
        platform["read_unavailable"] = False
        with ContinuityStore(path, clock, schema_target=13) as store:
            read, _ = governed(store, authority, opener.endpoint, grant=False)
            if lose_response:
                assert read.kernel.recover()[action] == "SUCCEEDED"
            assert store.one("actions", action)["state"] == "SUCCEEDED"
            assert platform["posts"] == 1


def test_preexisting_platform_comment_has_no_second_send(tmp_path):
    store, kernel, _, transport, platform, _, _ = setup(tmp_path)
    platform.rows.append({"rpid": 99, "root": 0, "member": {"mid": 42}, "content": {"message": "Existing"}})
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Existing"})
        assert kernel.run(action) == "SUCCEEDED"
        assert platform.posts == 0 and transport.calls == 3


@pytest.mark.parametrize("account_id,logged_in", [(77, True), (42, False), ("42", True), (True, True)])
def test_self_account_mismatch_or_logged_out_never_reaches_duplicate_read_or_send(tmp_path, account_id, logged_in):
    store, kernel, _, transport, platform, _, _ = setup(tmp_path)
    platform.account_id, platform.logged_in = account_id, logged_in
    # A historical matching PUBLIC comment must not hide the failed self-account
    # preflight by letting independent verification claim success.
    platform.rows.append({"rpid": 99, "root": 0, "member": {"mid": 42}, "content": {"message": "Existing"}})
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Existing"})
        assert kernel.run(action) == "UNKNOWN"
        assert kernel.run(action) == "UNKNOWN"
        assert platform.posts == 0 and transport.calls == 1
        assert len(platform.requests) == 1 and "/web-interface/nav" in platform.requests[0][1]


def test_actual_loopback_cookie_account_b_cannot_write_under_account_a_grant(tmp_path):
    from nana_core.continuity import ContinuityStore
    from tests.living_release_v4.bilibili_loopback import counterpart
    path, clock, authority = tmp_path / "self.db", ManualClock(), OperatorAuthority()
    with counterpart() as (opener, platform):
        platform["account_id"] = 77
        platform["comments"].append({"rpid": 99, "root": 0, "member": {"mid": 42}, "content": {"message": "Existing"}})
        with ContinuityStore(path, clock, schema_target=13) as store:
            cycle = account_cycle(store, authority)
            read, transport = governed(store, authority, opener.endpoint)
            _, action = read.propose(cycle.intention_id, expected_revision=1, args={"target_id": 7, "text": "Existing"})
            assert read.dispatch(cycle.intention_id, action, expected_revision=1) == "UNKNOWN"
            assert platform["posts"] == 0 and transport.calls == 1
            assert len(platform["requests"]) == 1 and "/web-interface/nav" in platform["requests"][0][1]
        with ContinuityStore(path, clock, schema_target=13) as store:
            read, transport = governed(store, authority, opener.endpoint, grant=False)
            assert read.kernel.recover()[action] == "UNKNOWN"
            assert transport.calls == platform["posts"] == 0
            assert len(platform["requests"]) == 1


def test_credential_rotation_after_preflight_cannot_send_from_another_cookie():
    resolver = MemorySecretResolver()
    resolver.bind("bili.cookie", "TEST_ONLY_ACCOUNT_A_COOKIE")
    resolver.bind("bili.csrf", "TESTONLYNOTSECRET0123456789")
    transport = BilibiliAccountTransport(resolver, cookie_ref="bili.cookie", csrf_ref="bili.csrf",
        policy=BilibiliAccountPolicy(42, True, True, True, (43,), 12))
    platform = Platform()
    transport.opener = platform
    assert transport.account()["account_id"] == 42
    resolver.bind("bili.cookie", "TEST_ONLY_ACCOUNT_B_COOKIE")
    with pytest.raises(CoreError, match="BILIBILI_ACCOUNT_BINDING_MISMATCH"):
        transport.send_comment(7, "No")
    assert transport.calls == 1 and platform.posts == 0


@pytest.mark.parametrize("invalid", [True, 0, 17, 2.0])
def test_registry_cannot_reserve_invalid_or_unbounded_request_cost(tmp_path, invalid):
    store, kernel, _, transport, platform, _, _ = setup(tmp_path)
    class InvalidRegistry(BilibiliActionRegistry):
        def request_count(self, capability):
            return invalid
    kernel.registry = InvalidRegistry()
    with store:
        action = kernel.propose("bilibili.comment.send", "project://bilibili/comment/7", {"target_id": 7, "text": "Denied"})
        with pytest.raises(CoreError, match="CAPABILITY_REQUEST_COST_INVALID"):
            kernel.prepare(action)
        assert transport.calls == platform.posts == 0
        assert store.one("budgets", "external_requests")["held"] == 0
