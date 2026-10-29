"""Actual HTTP against an owned synthetic OneBot counterpart; no QQ account."""

import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError, GrantSpec, Invocation
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.autonomy.contracts import RealizationTarget
from nana_core.continuity.autonomy.governance import GovernanceController, ManagerConstraint
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.open_agency.delivery import DeliveryAdmission, DeliveryPolicy, RecipientState
from nana_core.continuity.subject import SubjectInput, SubjectLoop
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.life.application import LifeApplication
from nana_core.life.platform_bridge import OneBotHTTPTransport, QQCapabilityPort, QQGovernedDelivery, QQIngress
from nana_core.life.surfaces import SurfaceBinding, SurfaceObservation, recent_sources
from tests.cloud_life.conftest import initialize


RESOURCE = "project://qq/private/43"
TARGET = RealizationTarget(capability="world.contact", operation="CONTACT", resource=RESOURCE,
                           resource_class="ORDINARY")


@contextmanager
def counterpart():
    """Independent server retains its effect even when its HTTP ACK is lost."""
    state = {"calls": [], "sent": [], "lose_ack": False, "read_peer": "43", "incoming_sender": "43",
             "incoming_kind": "private", "incoming_group": "77", "account": "42", "redirect": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["calls"].append((self.path, body))
            if state["redirect"]:
                self.send_response(307)
                self.send_header("Location", "/send_private_msg")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if self.path == "/get_login_info":
                data = {"user_id": state["account"]}
            elif self.path in {"/send_private_msg", "/send_group_msg"}:
                state["sent"].append(body)
                if state["lose_ack"]:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                data = {"message_id": 100 + len(state["sent"])}
            elif self.path == "/get_msg" and body["message_id"] == 1:
                data = {"message_id": 1, "message_type": state["incoming_kind"],
                        "group_id": state["incoming_group"], "time": 1,
                        "sender": {"user_id": state["incoming_sender"]},
                        "message": [{"type": "text", "data": {"text": "你好，今天只随便聊聊。"}}]}
            elif self.path == "/get_msg":
                sent = state["sent"][body["message_id"] - 101]
                data = {"message_id": body["message_id"], "message_type": "private", "time": 1,
                        "sender": {"user_id": "42"}, "target_id": state["read_peer"],
                        "message": sent["message"]}
            else:
                self.send_error(404)
                return
            raw = json.dumps({"status": "ok", "retcode": 0, "data": data}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def transport(endpoint, **updates):
    return OneBotHTTPTransport(endpoint, "42", authorized=True, realm="SYNTHETIC_LOOPBACK", **updates)


def candidate(store, authority, *, key="first", target=TARGET):
    IdentityService(store, authority)
    memory = MemoryService(store)
    memory.entity("project-user", "PERSON")
    cue = ConcernCue(cue_kind="OPPORTUNITY", motivation_source="RELATIONSHIP", topic_key="qq-" + key,
                     possible_behaviors=("SOCIALIZE",), availability="AVAILABLE")
    evidence = memory.capture(EvidenceInput(provenance=Provenance(source_namespace="synthetic.qq",
        source_reference=key, source_kind="USER_STATEMENT"), text=cue.model_dump_json(), privacy_class="PROJECT",
        observed_time_us=store.clock.utc_now_us()))
    mid = memory.add(MemoryCandidate(entity_id="project-user", scope="project-work", memory_type=MemoryType.SEMANTIC,
        epistemic_kind="STATEMENT", source_evidence_id=evidence, text=cue.model_dump_json(),
        predicate_key="concern.open.qq-" + key))
    cycle = SubjectLoop(store, scopes=("project-work",), privacy_classes=("PUBLIC", "PROJECT", "PERSONAL")).run(
        SubjectInput(source_key="synthetic.qq." + key, kind="INTERACTION", origin="USER", entity_id="project-user",
            scope="project-work", observed_at_us=store.clock.utc_now_us(), text="Source-backed contact opportunity",
            privacy_class="PROJECT", source_memory_ids=(mid,), realization_target=target))
    assert cycle.intention.kind == "SOCIAL_INTERACTION" and cycle.intention_id
    return cycle, mid


def original_delivery(store):
    return DeliveryAdmission(store, DeliveryPolicy(recipients=(RESOURCE,), privacy_classes=("PROJECT",),
        quiet_start_utc_hour=0, quiet_end_utc_hour=0), scopes=("project-work",), privacy_classes=("PROJECT",))


def equipped(store, authority, connection, *, grant=True, limit=16):
    GovernanceController(store, authority).initialize(authority)
    recipient = RecipientState(resource=RESOURCE, entity_id="project-user", availability="AVAILABLE",
        observed_at_us=store.clock.utc_now_us(), expires_at_us=store.clock.utc_now_us() + 60_000_000,
        permitted_privacy=("PROJECT",))
    memory = MemoryService(store)
    evidence = memory.capture(EvidenceInput(provenance=Provenance(source_namespace="synthetic.qq-presence",
        source_reference="recipient", source_kind="USER_STATEMENT"), text=recipient.model_dump_json(),
        privacy_class="PROJECT", observed_time_us=store.clock.utc_now_us()))
    from nana_core.storage import digest
    memory.add(MemoryCandidate(entity_id="project-user", scope="project-work", memory_type=MemoryType.EPISODIC,
        epistemic_kind="STATEMENT", source_evidence_id=evidence, text=recipient.model_dump_json(),
        predicate_key="recipient." + digest(RESOURCE)[:32]))
    port = QQCapabilityPort(store, connection, {RESOURCE: ("private", "43")}, host_enabled=True,
                            delivery=original_delivery(store))
    service = QQGovernedDelivery(port, authority, host_enabled=True)
    service.kernel.set_budgets({"write_attempts": limit, "external_requests": limit, "cost_micro_units": limit}, authority)
    if grant:
        service.kernel.grant(GrantSpec(capabilities=("world.contact", "world.action.verify"), resources=(RESOURCE,),
            not_before_us=store.clock.utc_now_us(), expires_at_us=store.clock.utc_now_us() + 100_000_000), authority)
    return service, port


def propose(service, port, cycle):
    data = port.bind_candidate("Original C chose this local test reply", cycle.record_id, privacy="PROJECT")
    admission = port.delivery.assess(cycle, RESOURCE, payload=data)
    assert admission["result"] == "ELIGIBLE"
    outcome, action = service.propose(cycle.intention_id, expected_revision=1,
                                   args={"data_privacy": "PROJECT", "data": data, "admission_id": admission["record_id"]})
    assert outcome.result == "PASS" and action
    return action


def test_real_loopback_http_original_c_manager_grant_budget_kernel_and_verify(tmp_path):
    authority = OperatorAuthority()
    with counterpart() as (url, platform), ContinuityStore(tmp_path / "subject/self.db", ManualClock(), schema_target=13) as store:
        cycle, _ = candidate(store, authority)
        connection = transport(url)
        service, port = equipped(store, authority, connection)
        action = propose(service, port, cycle)
        assert service.dispatch(cycle.intention_id, action, expected_revision=1) == "SUCCEEDED"
        assert len(platform["sent"]) == 1 and connection.calls == 3
        assert [x[0] for x in platform["calls"]] == ["/get_login_info", "/send_private_msg", "/get_msg"]
        assert store.one("budgets", "external_requests")["spent"] == 3
        assert service.dispatch(cycle.intention_id, action, expected_revision=1) == "SUCCEEDED"
        assert len(platform["sent"]) == 1
        assert store.one("core_meta", "cloud.shadow_runtime")  # fence was preserved
        assert not store.db.execute("PRAGMA foreign_key_check").fetchall()


def test_lost_ack_restart_remains_unknown_with_zero_resends_or_regeneration(tmp_path):
    path, clock, authority = tmp_path / "subject/self.db", ManualClock(), OperatorAuthority()
    with counterpart() as (url, platform):
        platform["lose_ack"] = True
        with ContinuityStore(path, clock, schema_target=13) as store:
            cycle, _ = candidate(store, authority)
            service, port = equipped(store, authority, transport(url))
            action = propose(service, port, cycle)
            assert service.dispatch(cycle.intention_id, action, expected_revision=1) == "UNKNOWN"
            assert len(platform["sent"]) == 1
            assert not port.candidates
        with ContinuityStore(path, clock, schema_target=13) as store:
            restarted = transport(url)
            port = QQCapabilityPort(store, restarted, {RESOURCE: ("private", "43")}, host_enabled=True,
                                    delivery=original_delivery(store))
            service = QQGovernedDelivery(port, authority, host_enabled=True)
            assert service.kernel.recover()[action] == "UNKNOWN"
            assert service.kernel.run(action) == "UNKNOWN"
            assert restarted.calls == 0 and len(platform["sent"]) == 1


@pytest.mark.parametrize("denial", ["grant", "budget", "manager"])
def test_missing_original_authority_budget_or_late_veto_makes_zero_requests(tmp_path, denial):
    authority = OperatorAuthority()
    with counterpart() as (url, platform), ContinuityStore(tmp_path / "subject/self.db", ManualClock(), schema_target=13) as store:
        cycle, _ = candidate(store, authority)
        service, port = equipped(store, authority, transport(url), grant=denial != "grant", limit=1 if denial == "budget" else 16)
        action = propose(service, port, cycle)
        if denial == "manager":
            GovernanceController(store, authority).install(ManagerConstraint(constraint_id="late-veto", revision=1,
                issuer=authority.principal, source_reference="synthetic-review", identity_id=store.identity["identity_id"],
                scope="project-work", targets=(TARGET,), effective_from_us=store.clock.utc_now_us(),
                expires_at_us=store.clock.utc_now_us() + 10_000_000, reason_code="DO_NOT_CONTACT"), authority)
            assert service.dispatch(cycle.intention_id, action, expected_revision=1) == "INTENTION_BLOCKED_MANAGER"
        else:
            with pytest.raises(CoreError, match="AUTH_REQUIRED" if denial == "grant" else "BUDGET_EXHAUSTED"):
                service.dispatch(cycle.intention_id, action, expected_revision=1)
        assert not platform["calls"] and not platform["sent"]


def test_independent_receipt_peer_mismatch_is_failed_effect_never_success(tmp_path):
    authority = OperatorAuthority()
    with counterpart() as (url, platform), ContinuityStore(tmp_path / "subject/self.db", ManualClock(), schema_target=13) as store:
        cycle, _ = candidate(store, authority)
        platform["read_peer"] = "99"
        service, port = equipped(store, authority, transport(url))
        action = propose(service, port, cycle)
        assert service.dispatch(cycle.intention_id, action, expected_revision=1) == "FAILED_EFFECT"
        assert len(platform["sent"]) == 1


def test_original_delivery_admission_expiry_blocks_send_before_network(tmp_path):
    authority = OperatorAuthority()
    clock = ManualClock()
    with counterpart() as (url, platform), ContinuityStore(tmp_path / "subject/self.db", clock, schema_target=13) as store:
        cycle, _ = candidate(store, authority)
        service, port = equipped(store, authority, transport(url))
        action = propose(service, port, cycle)
        clock.advance(31_000_000)
        assert service.dispatch(cycle.intention_id, action, expected_revision=1) == "UNKNOWN"
        assert not platform["calls"] and not platform["sent"]


def test_transport_never_follows_redirect_or_changed_account_to_send():
    with counterpart() as (url, platform):
        connection = transport(url)
        platform["redirect"] = True
        with pytest.raises(CoreError, match="HTTP_REJECTED_NO_RETRY"):
            connection.account()
        assert len(platform["calls"]) == 1 and not platform["sent"]
        platform["redirect"], platform["account"] = False, "99"
        with pytest.raises(CoreError, match="ACCOUNT_BINDING_CHANGED"):
            connection.send("private", "43", "No inherited account authority", "echo")
        assert len(platform["calls"]) == 2 and not platform["sent"]


def test_source_erasure_and_forged_invocation_cannot_dispatch(tmp_path):
    authority = OperatorAuthority()
    with counterpart() as (url, platform), ContinuityStore(tmp_path / "subject/self.db", ManualClock(), schema_target=13) as store:
        cycle, mid = candidate(store, authority)
        service, port = equipped(store, authority, transport(url))
        with pytest.raises(CoreError, match="PRIVACY_DOWNGRADE"):
            port.bind_candidate("No downgrade", cycle.record_id, privacy="PUBLIC")
        fake = Invocation(action_id="fake", attempt_id="fake", capability="world.contact", resource=RESOURCE,
                          args={}, args_hash="fake", idempotency_key="fake")
        with pytest.raises(CoreError, match="KERNEL_ACTION_REQUIRED"):
            port.execute(fake)
        action = propose(service, port, cycle)
        MemoryService(store, authority).forget(mid, authority)
        with pytest.raises(CoreError, match="RECORD|SUPPORT"):
            service.dispatch(cycle.intention_id, action, expected_revision=1)
        assert not platform["calls"]


def binding(**updates):
    return SurfaceBinding(binding_id="qq.platform", platform="qq.onebot", surface="chat.direct", adapter="onebot.http",
                          mode="PLATFORM_ADAPTER_NO_SEND", **updates)


def test_trusted_onebot_ingress_reaches_same_original_c_no_send_and_deduplicates(tmp_path):
    home = tmp_path / "life"
    initialize(home, max_autonomous_materials=0, surface_bindings=(binding(),))
    with counterpart() as (url, platform), LifeApplication(home) as app:
        app.pause()
        ingress = QQIngress(app, transport(url), "qq.platform", "43")
        result = ingress.receive(1)
        assert result["state"] == "CORE_REPLY_CANDIDATE" and result["cycle_record_id"]
        assert result["platform_origin"] == "SYNTHETIC_LOOPBACK" and result["external_delivery"] is False
        assert len(app.runtime.store.all("subject_cycles")) == 1
        assert ingress.receive(1)["state"] == "ALREADY_REVIEWED_NO_REPLAY"
        assert len(app.runtime.store.all("subject_cycles")) == 1
        assert not app.runtime.store.all("grants") and not app.runtime.store.all("actions") and not platform["sent"]
        platform["incoming_sender"] = "99"
        with pytest.raises(CoreError, match="SENDER_UNBOUND"):
            ingress.receive(1)
        platform["incoming_sender"], platform["incoming_kind"] = "43", "group"
        with pytest.raises(CoreError, match="PEER_UNBOUND"):
            ingress.receive(1)


def test_personal_ingress_read_and_retention_are_separate_explicit_bindings(tmp_path):
    home = tmp_path / "life"
    initialize(home, max_autonomous_materials=0, surface_bindings=(binding(permitted_privacy=("PERSONAL",)),))
    with counterpart() as (url, _), LifeApplication(home) as app:
        app.pause()
        with pytest.raises(CoreError, match="PRIVATE_INGRESS_NOT_AUTHORIZED"):
            QQIngress(app, transport(url), "qq.platform", "43", privacy="PERSONAL")
        ingress = QQIngress(app, transport(url), "qq.platform", "43", privacy="PERSONAL", private_read_authorized=True)
        assert ingress.receive(1)["raw_body_persisted"] is False
        with pytest.raises(CoreError, match="RETENTION_NOT_AUTHORIZED"):
            app.surfaces.receive(SurfaceObservation(binding_id="qq.platform", event_id="retain", text="private text",
                privacy_class="PERSONAL", approved_summary="Explicit summary", summary_authorization="EXPLICIT_PERSONAL_SUMMARY"))

    allowed = tmp_path / "allowed"
    initialize(allowed, max_autonomous_materials=0, surface_bindings=(binding(permitted_privacy=("PERSONAL",),
        allow_personal_retention=True, personal_retention_consent_ref="operator.summary-consent.1"),))
    with LifeApplication(allowed) as app:
        app.pause()
        result = app.surfaces.receive(SurfaceObservation(binding_id="qq.platform", event_id="retain", topic="qq-private",
            text="private text", privacy_class="PERSONAL", approved_summary="Explicit summary",
            summary_authorization="EXPLICIT_PERSONAL_SUMMARY"))
        mid = result["summary_memory_ids"][0]
        source = MemoryService(app.runtime.store).read(mid)["source_provenance"]
        assert source["domain"] == "CONSENTED_INTERACTION" and source["source_namespace"] == "recorded.conversation.input"
        assert recent_sources(app, "qq-private", "PERSONAL") == (mid,)
        assert not recent_sources(app, "qq-private", "PROJECT")
        app.forget(mid)
        assert not recent_sources(app, "qq-private", "PERSONAL")


def test_real_ingress_requires_original_canonical_channel_binding_before_network(tmp_path):
    home = tmp_path / "life"
    initialize(home, max_autonomous_materials=0, surface_bindings=(binding(),))
    with LifeApplication(home) as app:
        connection = OneBotHTTPTransport("https://example.invalid", "42", authorized=True)
        with pytest.raises(CoreError, match="CANONICAL_ACTIVATION_REQUIRED"):
            QQIngress(app, connection, "qq.platform", "43")
        assert connection.calls == 0


def test_queued_surface_privacy_rejection_keeps_original_owner_running(tmp_path):
    home = tmp_path / "life"
    initialize(home, max_autonomous_materials=0, surface_bindings=(binding(),))
    with LifeApplication(home) as app:
        app.pause()
        app.ingress.offer(SurfaceObservation(binding_id="qq.platform", event_id="forbidden", text="Private input",
            privacy_class="PERSONAL", origin="SYNTHETIC_LOOPBACK"))
        result = app.tick()["surface_ingress"]["result"]
        assert result["error"] == "SURFACE_PRIVACY_NOT_BOUND" and result["judged"] is False
        assert not app.runtime.store.all("subject_cycles")
        app.ingress.offer(SurfaceObservation(binding_id="qq.platform", event_id="allowed", text="Project input",
            privacy_class="PROJECT", origin="SYNTHETIC_LOOPBACK"))
        assert app.tick()["surface_ingress"]["result"]["state"] == "CORE_REPLY_CANDIDATE"
        assert len(app.runtime.store.all("subject_cycles")) == 1


def test_transport_endpoint_and_real_account_shadow_fence(tmp_path):
    for endpoint in ("http://example.com", "https://u:p@example.com", "https://example.com/path", "https://example.com?token=x"):
        with pytest.raises(CoreError, match="SAFE_ENDPOINT_REQUIRED"):
            OneBotHTTPTransport(endpoint, "42", authorized=True)
    authority = OperatorAuthority()
    with ContinuityStore(tmp_path / "subject/self.db", ManualClock(), schema_target=13) as store:
        candidate(store, authority)
        connection = OneBotHTTPTransport("https://example.invalid", "42", authorized=True, realm="AUTHENTICATED_PLATFORM")
        port = QQCapabilityPort(store, connection, {RESOURCE: ("private", "43")}, host_enabled=True)
        service = QQGovernedDelivery(port, authority, host_enabled=True)
        with pytest.raises(CoreError, match="CANONICAL_ACTIVATION_REQUIRED|SHADOW_BLOCKED"):
            service.kernel.set_budgets({"write_attempts": 1, "external_requests": 2, "cost_micro_units": 2}, authority)
        assert connection.calls == 0
