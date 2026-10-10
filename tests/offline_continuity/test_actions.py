import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import pytest
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.fake_world import FakeWorld
from nana_core.storage import Store
from conftest import CARD, SOURCE, authorize, card_args

pytestmark = pytest.mark.s2


def test_E05_no_grant_means_no_execution(environment):
    store, world, kernel, _, _ = environment
    action = kernel.propose("reading.card.create", CARD, card_args())
    with pytest.raises(CoreError, match="AUTH_REQUIRED"):
        kernel.run(action)
    assert world.counts()["execute_calls"] == 0
    assert store.one("actions", action)["state"] == "BLOCKED"
    assert not store.all("attempts")


@pytest.mark.parametrize("invalidate", ["expire", "revoke"])
def test_E06_recheck_after_reservation(environment, invalidate):
    store, world, kernel, authority, clock = environment
    grant = authorize(kernel, authority, clock)
    action = kernel.propose("reading.card.create", CARD, card_args())
    kernel.prepare(action)
    if invalidate == "expire":
        clock.advance(11_000_000)
    else:
        kernel.revoke(grant, authority)
    with pytest.raises(CoreError, match="AUTH_EXPIRED|AUTH_REVOKED"):
        kernel.dispatch(action)
    assert world.counts()["execute_calls"] == 0
    assert all(b["spent"] == b["held"] == 0 for b in store.all("budgets"))


def test_E07_attempt_budget_atomic_reservation(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock, resources=(SOURCE, CARD, "notebook://synthetic/card-2"))
    kernel.set_budgets({"write_attempts": 1, "external_requests": 100, "cost_micro_units": 100}, authority)
    first = kernel.propose("reading.card.create", CARD, card_args())
    second = kernel.propose("reading.card.create", "notebook://synthetic/card-2", card_args())
    kernel.prepare(first)
    before = store.all("budgets")
    with pytest.raises(CoreError, match="BUDGET_EXHAUSTED"):
        kernel.prepare(second)
    assert store.all("budgets") == before
    assert len(store.all("attempts")) == 1
    kernel.dispatch(first)
    assert store.one("budgets", "write_attempts")["spent"] == 1
    assert store.one("actions", first)["state"] == "PENDING_VERIFY"


def test_E08_unknown_does_not_refund_or_blind_retry(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    world.control("lose_receipt", True)
    world.control("verify_unavailable", True)
    action = kernel.propose("reading.card.create", CARD, card_args())
    assert kernel.run(action) == "UNKNOWN"
    assert store.one("budgets", "write_attempts")["spent"] == 1
    assert store.one("budgets", "cost_micro_units")["held"] == 2
    assert kernel.run(action) == "UNKNOWN"
    assert world.counts()["effects"] == world.counts()["execute_calls"] == 1
    with pytest.raises(CoreError, match="ILLEGAL_ACTION_TRANSITION"):
        kernel.prepare(action)
    world.control("verify_unavailable", False)
    assert kernel.recover()[action] == "SUCCEEDED"
    assert world.counts()["effects"] == world.counts()["execute_calls"] == 1


def test_receipt_is_not_success_and_readback_detects_wrong_effect(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    action = kernel.propose("reading.card.create", CARD, card_args())
    kernel.prepare(action)
    assert kernel.dispatch(action) == "PENDING_VERIFY"
    world.db.execute("UPDATE cards SET content_json='{}' WHERE resource=?", (CARD,))
    assert kernel.verify(action) == "FAILED_EFFECT"


def test_operator_boundary_and_resource_scope(environment):
    store, world, kernel, authority, clock = environment
    with pytest.raises(CoreError, match="UNAUTHENTICATED_OPERATOR"):
        kernel.set_budgets({"write_attempts": 999}, OperatorAuthority())
    authorize(kernel, authority, clock, resources=(SOURCE,))
    action = kernel.propose("reading.card.create", CARD, card_args())
    with pytest.raises(CoreError, match="AUTH_REQUIRED"):
        kernel.run(action)
    assert not world.counts()["effects"]


def test_effect_slot_and_immutable_arguments(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    action = kernel.propose("reading.card.create", CARD, card_args(), effect_slot="synthetic-slot")
    assert kernel.propose("reading.card.create", CARD, card_args(), effect_slot="synthetic-slot") == action
    with pytest.raises(CoreError, match="EFFECT_SLOT_COLLISION"):
        kernel.propose("reading.card.create", CARD, card_args("different"), effect_slot="synthetic-slot")
    kernel.prepare(action)
    store.db.execute("UPDATE actions SET args_json='{}' WHERE action_id=?", (action,))
    with pytest.raises(CoreError, match="ACTION_ARGS_CORRUPT"):
        kernel.dispatch(action)
    assert not world.counts()["execute_calls"]


def test_expired_write_can_be_verified_with_separate_read_grant(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock, capabilities={"reading.card.create"}, ttl=2_000_000)
    authorize(kernel, authority, clock, capabilities={"reading.action.verify"}, ttl=100_000_000)
    action = kernel.propose("reading.card.create", CARD, card_args())
    kernel.prepare(action)
    kernel.dispatch(action)
    clock.advance(3_000_000)
    assert kernel.verify(action) == "SUCCEEDED"


@pytest.mark.parametrize("point", ["before_call", "after_effect"])
def test_E03_E04_real_SIGKILL_recovery(tmp_path, point):
    from nana_core.clock import ManualClock
    from conftest import PARAGRAPHS
    store_path, world_path = tmp_path / "nana.db", tmp_path / "fake_world.db"
    clock = ManualClock()
    authority = OperatorAuthority()
    with Store(store_path, clock) as store:
        world = FakeWorld(world_path)
        world.seed_source(SOURCE, PARAGRAPHS)
        kernel = ActionKernel(store, world, authority)
        kernel.set_budgets({"write_attempts": 1, "external_requests": 10, "cost_micro_units": 10}, authority)
        authorize(kernel, authority, clock)
        identity_id = store.identity["identity_id"]
        action = kernel.propose("reading.card.create", CARD, card_args())
        kernel.prepare(action)
        world.close()
    script = '''
import os, signal, sys
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.fake_world import FakeWorld
from nana_core.storage import Store
with Store(sys.argv[1], ManualClock()) as store:
    world = FakeWorld(sys.argv[2])
    kernel = ActionKernel(store, world, OperatorAuthority())
    def fault(point):
        if point == sys.argv[4]:
            print("fault=" + point, flush=True)
            os.kill(os.getpid(), signal.SIGKILL)
    kernel.dispatch(sys.argv[3], fault=fault)
'''
    child = subprocess.run([sys.executable, "-c", script, str(store_path), str(world_path), action, point],
        env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path("src").resolve())},
        capture_output=True, text=True, timeout=10)
    assert child.returncode == -signal.SIGKILL
    assert child.stdout.strip() == "fault=" + point
    with Store(store_path, clock) as store:
        world = FakeWorld(world_path)
        assert store.one("actions", action)["state"] == "DISPATCHING"
        assert store.identity["identity_id"] == identity_id
        kernel = ActionKernel(store, world, OperatorAuthority())
        expected = "SUCCEEDED" if point == "after_effect" else "NOT_APPLIED"
        assert kernel.recover()[action] == expected
        counts = world.counts()
        assert counts["effects"] == counts["execute_calls"] == (point == "after_effect")
        assert counts["verify_calls"] == 1
        assert store.one("budgets", "write_attempts")["spent"] == 1
        proof = {"signal": child.returncode, "fault_point": point, "action_id": action,
                 "identity_id": identity_id, "recovered_state": expected, "world_counts": counts}
        (tmp_path / "crash-proof.json").write_text(json.dumps(proof, indent=2))
        world.close()


def test_E18_backup_quarantine_prevents_old_state_redispatch(environment, tmp_path):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    action = kernel.propose("reading.card.create", CARD, card_args())
    kernel.prepare(action)
    backup = tmp_path / "old-backup.db"
    store.backup(backup)
    assert kernel.run(action) == "SUCCEEDED"
    with Store(backup, clock) as restored:
        recovered = ActionKernel(restored, world, authority)
        with pytest.raises(CoreError, match="RESTORE_QUARANTINE"):
            recovered.run(action)
    assert world.counts()["effects"] == world.counts()["execute_calls"] == 1
