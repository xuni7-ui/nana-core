"""Real loopback BFF → original owner → original MemoryService; synthetic notes."""

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.life.live_api.contracts import Role, ApiError
from tests.person_self.conftest import initialize
from tests.living_release_v4.test_private_context import private_host, paired
from .test_http_integration import running, http, login, base


def note(service, key, text, **extra):
    return {**base(service, key), "text": text, "privacy_class": "PROJECT", "consent": True, **extra}


def test_actual_notes_correction_restart_recall_withdrawal_and_same_receipt(running):
    server, service = running
    headers = login(server, service)
    identity = service.binding.subject_id
    request = note(service, "first-note", "SYNTHETIC 我喜欢把项目约定放在周三")
    code, result, _ = http(server, "memories/notes", "POST", request, headers)
    assert code == 200 and result["data"]["state"] == "VERIFIED", result
    saved = result["data"]["result"]
    mid = saved["memory_id"]
    assert saved["provenance"] == "USER_PROVIDED_NOT_VERIFIED_FACT" and saved["nana_lived_experience"] is False
    assert (
        http(server, "memories/notes", "POST", request, headers)[1]["data"]["receipt_id"]
        == result["data"]["receipt_id"]
    )
    rows = http(server, "views/memories", headers=headers)[1]["data"]["memories"]
    original = next(m for m in rows if m["memory_id"] == mid)
    assert original["user_provided_note"] and original["epistemic_kind"] == "STATEMENT"
    corrected = note(service, "correct-note", "SYNTHETIC 更新项目约定为周五", target_id=mid)
    code, new, _ = http(server, "memories/notes", "POST", corrected, headers)
    assert code == 200 and new["data"]["state"] == "VERIFIED", new
    nextmid = new["data"]["result"]["memory_id"]
    stale = http(
        server,
        "memories/notes",
        "POST",
        note(service, "stale-correction", "SYNTHETIC stale edit", target_id=mid),
        headers,
    )[1]["data"]
    assert (
        stale["state"] == "REJECTED" and not stale["dispatch_happened"] and stale["error"] == "MEMORY_NOTE_TARGET_STALE"
    )
    service.supervisor.stop()
    service.supervisor.start()
    found = http(server, "memories/search", "POST", {"query": "项目约定"}, headers)[1]["data"]["memories"]
    assert [m["memory_id"] for m in found] == [nextmid] and found[0]["text"] == corrected["text"]
    assert http(server, "bootstrap", headers=headers)[1]["subject_id"] == identity
    withdrawn = http(
        server,
        "commands",
        "POST",
        {**base(service, "withdraw-note"), "operation": "WITHDRAW", "target_id": nextmid},
        headers,
    )
    assert withdrawn[1]["data"]["state"] == "VERIFIED", withdrawn
    assert http(server, "memories/search", "POST", {"query": "项目约定"}, headers)[1]["data"]["memories"] == []
    assert (
        http(server, "receipts/correct-note", headers=headers)[1]["data"]["result"]["state"]
        == "BODY_WITHHELD_SOURCE_CHANGED"
    )
    service.supervisor.stop()
    service.supervisor.start()
    assert http(server, "memories/search", "POST", {"query": "项目约定"}, headers)[1]["data"]["memories"] == []


def test_note_role_csrf_explicit_consent_and_private_retention_gates(running):
    server, service = running
    headers = login(server, service)
    request = note(service, "unauth", "SYNTHETIC note")
    assert http(server, "memories/notes", "POST", request)[0] in {401, 403}
    assert (
        http(server, "memories/notes", "POST", request, {"Cookie": headers["Cookie"], "Origin": headers["Origin"]})[0]
        == 403
    )
    for consent in (False, 1, "true"):
        assert http(server, "memories/notes", "POST", {**request, "consent": consent}, headers)[0] == 400
    assert http(server, "memories/notes", "POST", {**request, "caller_role": "SYSTEM"}, headers)[0] == 400
    assert (
        http(
            server,
            "memories/notes",
            "POST",
            {**request, "text": '{"api_key":"SYNTHETIC_NOT_A_REAL_CREDENTIAL"}'},
            headers,
        )[0]
        == 400
    )
    reader = paired(server, service, headers, ["READER"])
    assert http(server, "memories/notes", "POST", note(service, "reader", "SYNTHETIC reader note"), reader)[0] == 403
    assert http(server, "memories/notes", "POST", {**request, "privacy_class": "PERSONAL"}, headers)[0] == 403
    private_host(service, retention=False)
    response = http(
        server,
        "memories/notes",
        "POST",
        note(service, "no-consent", "SYNTHETIC private note", privacy_class="PERSONAL"),
        headers,
    )[1]["data"]
    assert response["state"] == "REJECTED" and response["error"] == "SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED"
    private_host(service, retention=True)
    response = http(
        server,
        "memories/notes",
        "POST",
        note(service, "allowed-private", "SYNTHETIC retained private note", privacy_class="PERSONAL"),
        headers,
    )[1]["data"]
    assert response["state"] == "VERIFIED"
    assert any(
        m["memory_id"] == response["result"]["memory_id"]
        for m in http(server, "views/memories", headers=headers)[1]["data"]["memories"]
    )


def test_core_note_fences_unchanged_replay_secret_and_foreign_correction(tmp_path):
    home = tmp_path / "life"
    initialize(home)
    from nana_core.life.config import load_config, update_config
    from nana_core.life.surfaces import SurfaceBinding

    config = load_config(home)
    binding = SurfaceBinding(
        binding_id="private.notes",
        platform="cloud.local",
        surface="chat.direct",
        adapter="shadow.local",
        permitted_privacy=("PUBLIC", "PROJECT", "PERSONAL"),
        allow_personal_retention=True,
        personal_retention_consent_ref="SYNTHETIC_ONLY_RETENTION",
    )
    update_config(
        home,
        config.model_copy(
            update={
                "revision": config.revision + 1,
                "privacy_classes": ("PUBLIC", "PROJECT", "PERSONAL"),
                "surface_bindings": (binding,),
            }
        ),
        expected_revision=config.revision,
    )
    with LifeApplication(home) as app:
        app.pause()
        r = app.runtime
        args = {"privacy": "PERSONAL", "request_id": "first", "surface_binding_id": "private.notes"}
        original = save(app, text="SYNTHETIC private note", **args)
        assert save(app, text="SYNTHETIC private note", **args) == original
        with pytest.raises(CoreError, match="REQUEST_CONFLICT"):
            save(app, text="SYNTHETIC changed", **args)
        with pytest.raises(CoreError, match="DOWNGRADE"):
            save(
                app,
                text="SYNTHETIC public correction",
                privacy="PROJECT",
                request_id="lower",
                target_id=original["memory_id"],
            )
        from nana_core.continuity.project_work.service import capture

        observation = capture(r, "source-observation", {"value": "SYNTHETIC verified source"})
        with pytest.raises(CoreError, match="TARGET_DENIED"):
            save(
                app, text="SYNTHETIC replacement", privacy="PROJECT", request_id="replace-source", target_id=observation
            )
        evidence_before = len(r.store.all("continuity_evidence"))
        for value in ["sk-" + "X" * 32, '{"authorization":"TEST_ONLY_NOT_SECRET_TOKEN"}']:
            with pytest.raises(CoreError, match="CREDENTIAL_DENIED"):
                save(app, text=value, privacy="PROJECT", request_id="credential")
        assert len(r.store.all("continuity_evidence")) == evidence_before
        app.forget(original["memory_id"])
        with pytest.raises(CoreError, match="SOURCE_DELETED"):
            save(app, text="SYNTHETIC private note", **args)
        assert not r.store.all("actions") and not r.store.all("grants") and not r.store.all("cognitive_requests")


def test_dispatch_id_alone_cannot_fake_an_independent_saved_note(running, monkeypatch):
    server, service = running
    headers = login(server, service)
    first = http(
        server, "memories/notes", "POST", note(service, "real-note", "SYNTHETIC actual retained note"), headers
    )[1]["data"]
    assert first["state"] == "VERIFIED"
    mid = first["result"]["memory_id"]
    from nana_core.life.live_api import memory_notes

    monkeypatch.setattr(
        memory_notes,
        "core_request",
        lambda *args, **kwargs: {
            "ok": True,
            "result": {"state": "USER_NOTE_SAVED", "memory_id": mid, "nana_lived_experience": False},
        },
    )
    result = http(
        server, "memories/notes", "POST", note(service, "forged-dispatch", "SYNTHETIC different unsaved note"), headers
    )[1]["data"]
    assert result["state"] == "UNKNOWN" and result["result"] == {}
    assert http(server, "receipts/forged-dispatch", headers=headers)[1]["data"]["state"] == "UNKNOWN"
    assert http(server, "memories/search", "POST", {"query": "different unsaved"}, headers)[1]["data"]["memories"] == []


@pytest.mark.parametrize("withdraw", [False, True])
def test_lost_actual_write_reply_reconciles_from_persisted_proof_without_redispatch(running, monkeypatch, withdraw):
    server, service = running
    headers = login(server, service)
    from nana_core.life.live_api import memory_notes
    from nana_core.life.live_api.ledger import OperationLedger

    actual = memory_notes.core_request
    calls = []

    def lose_reply(*args, **kwargs):
        result = actual(*args, **kwargs)
        assert result["ok"] and result["result"]["state"] == "USER_NOTE_SAVED"
        calls.append(result["result"]["memory_id"])
        raise TimeoutError("SYNTHETIC transport loss after actual Core commit")

    monkeypatch.setattr(memory_notes, "core_request", lose_reply)
    request = note(service, "lost-note", "SYNTHETIC saved before transport loss")
    result = http(server, "memories/notes", "POST", request, headers)[1]["data"]
    assert result["state"] == "UNKNOWN" and len(calls) == 1
    if withdraw:
        reply = http(
            server,
            "commands",
            "POST",
            {**base(service, "forget-lost"), "operation": "WITHDRAW", "target_id": calls[0]},
            headers,
        )[1]["data"]
        assert reply["state"] == "VERIFIED"
    service.supervisor.stop()
    service.supervisor.start()
    # The ordinary host ledger loses volatile results on restart. No raw note
    # body or caller-provided success flag is used to recover its terminal state.
    service.ledger = OperationLedger(service.ledger.document.path)
    service.receipt_privacy.clear()
    service.receipt_scopes.clear()
    recovered = http(server, "receipts/lost-note", headers=headers)[1]["data"]
    if withdraw:
        assert recovered["state"] == "UNKNOWN" and recovered["result"] == {}
    else:
        assert recovered["state"] == "VERIFIED" and recovered["result"]["memory_id"] == calls[0]
        same = http(server, "memories/notes", "POST", request, headers)[1]["data"]
        assert same["state"] == "VERIFIED"
    assert len(calls) == 1  # GET/replay of the receipt never calls the writer again.


def test_archived_lost_reply_reconciles_from_original_core_after_gateway_and_owner_restart(running, monkeypatch):
    """Only one actual saved DEV note; filler rows are explicit host metadata fixtures."""
    from nana_core.life.live_api import memory_notes
    from nana_core.life.live_api.ledger import OperationLedger, HOT_LIMIT
    from nana_core.life.live_api.contracts import Completion

    server, service = running
    headers = login(server, service)
    actual = memory_notes.core_request
    calls = []

    def lost(*args, **kwargs):
        result = actual(*args, **kwargs)
        calls.append(result["result"]["memory_id"])
        raise TimeoutError("SYNTHETIC reply lost after actual commit")

    monkeypatch.setattr(memory_notes, "core_request", lost)
    request = note(service, "archived-lost-note", "SYNTHETIC archived proof remains available")
    assert http(server, "memories/notes", "POST", request, headers)[1]["data"]["state"] == "UNKNOWN"
    for i in range(HOT_LIMIT + 1):
        key = "synthetic-filler." + str(i)
        service.ledger.reserve(key, "synthetic-fixture-owner", {}, "MESSAGE", service.ledger.revision, key)
        service.ledger.transition(key, Completion.VERIFIED)
    assert "archived-lost-note" not in service.ledger.document.read()["receipts"]
    assert service.ledger.entry("archived-lost-note")["receipt"]["state"] == "UNKNOWN"
    service.supervisor.stop()
    service.supervisor.start()
    service.ledger = OperationLedger(service.ledger.document.path)
    service.receipt_privacy.clear()
    service.receipt_scopes.clear()
    result = http(server, "receipts/archived-lost-note", headers=headers)[1]["data"]
    assert result["state"] == "VERIFIED" and result["result"]["memory_id"] == calls[0]
    repeated = http(server, "memories/notes", "POST", request, headers)[1]["data"]
    assert repeated["state"] == "VERIFIED" and len(calls) == 1
