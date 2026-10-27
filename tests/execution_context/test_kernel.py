"""Real local owned files; synthetic namespace routing is tested separately.

Original Kernel/Store/Grant/Budget own dispatch; this is not cloud deployment.
"""

import json

import pytest

from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError, GrantSpec, Receipt, Verification
from nana_core.execution_context.contracts import ContextBinding
from nana_core.execution_context.port import ContextBoundPort, PREFIX
from nana_core.execution_context.probe import LocalContextProbe
from nana_core.execution_context.routing import ExecutionChannel, ExecutionContextRouter, ResourceBinding, TargetBinding
from nana_core.storage import Store, digest


RESOURCE = "notebook://synthetic/context-repair"
ARGS = {
    "source_id": "source://synthetic/source",
    "source_digest": digest(b"synthetic"),
    "content": "finite owned repair",
    "locator": None,
}


class OwnedFilePort:
    """Test-only fixed effect, not a production file writer or shell adapter."""

    def __init__(self, path):
        self.output = path
        self.calls = 0
        self.verifies = 0
        self.lose_receipt = False
        self.verify_unavailable = False

    def execute(self, inv):
        assert inv.capability == "reading.card.create" and inv.resource == RESOURCE and inv.args == ARGS
        self.calls += 1
        self.output.write_text(inv.args["content"])
        if self.lose_receipt:
            raise TimeoutError("TEST_ONLY_COMPLETION_AMBIGUOUS")
        return Receipt(external_id=inv.idempotency_key, result={"written": True})

    def verify(self, inv):
        self.verifies += 1
        if self.verify_unavailable:
            return Verification(verdict="INCONCLUSIVE", evidence={"reason": "TEST_ONLY_UNAVAILABLE"})
        return Verification(
            verdict="MATCH" if self.output.read_text() == inv.args["content"] else "EFFECT_MISMATCH",
            evidence={"independent_readback": True},
        )


def construct(store, authority, directory, backend=None):
    probe = LocalContextProbe(ContextBinding(target_id="core-container", binding_id="owned-test"))
    context = probe.capture()
    backend = backend or OwnedFilePort(directory / "output.txt")
    router = ExecutionContextRouter(
        probe,
        targets=(
            TargetBinding(
                target_id=context.target_id,
                context_id=context.context_id,
                scope=context.scope,
                channel_ids=("local-owned",),
            ),
        ),
        channels=(ExecutionChannel("local-owned", "LOCAL", probe, backend),),
        resources=(
            ResourceBinding(
                resource=RESOURCE,
                target_id=context.target_id,
                path=str(directory),
                capabilities=("reading.card.create",),
            ),
        ),
    )
    wrapper = ContextBoundPort(store, router, authority)
    return ActionKernel(store, wrapper, authority), wrapper, backend


def grant(kernel, authority, clock):
    kernel.set_budgets({"external_requests": 30, "write_attempts": 10, "cost_micro_units": 30}, authority)
    return kernel.grant(
        GrantSpec(
            capabilities=("reading.card.create", "reading.action.verify"),
            resources=(RESOURCE,),
            not_before_us=clock.utc_now_us(),
            expires_at_us=clock.utc_now_us() + 100_000_000,
        ),
        authority,
    )


def test_actual_authorized_local_repair_independent_verify_and_bound_receipts(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, wrapper, backend = construct(store, authority, directory)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        with pytest.raises(CoreError, match="AUTH_REQUIRED"):
            kernel.run(action)
        assert backend.calls == 0 and not (directory / "output.txt").exists()
        grant(kernel, authority, clock)
        assert kernel.run(action) == "SUCCEEDED"
        assert backend.calls == backend.verifies == 1
        pin = json.loads(store.one("core_meta", PREFIX + action)["value_json"])
        assert pin["target_id"] == "core-container" and pin["transport"] == "LOCAL"
        assert pin["path_observation"]["device"] == directory.stat().st_dev
        claim = json.loads(store.one("core_meta", "execution.context.dispatch:" + action)["value_json"])
        assert claim["metadata"]["observation"]["actual_path"] == str(directory)
        assert claim["metadata"]["execution_authority"] is False
        assert kernel.run(action) == "SUCCEEDED" and backend.calls == 1


def test_unknown_restart_no_resend_no_fallback_and_later_independent_reconcile(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    path = tmp_path / "subject.db"
    store = Store(path, clock)
    identity = store.identity["identity_id"]
    kernel, wrapper, backend = construct(store, authority, directory)
    grant(kernel, authority, clock)
    backend.lose_receipt = backend.verify_unavailable = True
    action = kernel.propose("reading.card.create", RESOURCE, ARGS)
    assert kernel.run(action) == "UNKNOWN"
    assert backend.calls == 1
    store.close()
    with Store(path, clock) as restored:
        kernel, _, _ = construct(restored, authority, directory, backend)
        assert restored.identity["identity_id"] == identity
        assert kernel.run(action) == "UNKNOWN" and backend.calls == 1
        backend.verify_unavailable = False
        assert kernel.recover()[action] == "SUCCEEDED" and backend.calls == 1


def test_context_change_or_revoked_grant_never_reaches_backend(tmp_path, monkeypatch):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, wrapper, backend = construct(store, authority, directory)
        gid = grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        kernel.prepare(action)
        original = wrapper.router.source_probe.capture
        monkeypatch.setattr(
            wrapper.router.source_probe, "capture", lambda: original().model_copy(update={"context_id": "f" * 64})
        )
        assert kernel.dispatch(action) == "UNKNOWN" and backend.calls == 0
        assert kernel.verify(action) == "UNKNOWN" and backend.calls == 0
        monkeypatch.setattr(wrapper.router.source_probe, "capture", original)
        second = kernel.propose("reading.card.create", RESOURCE, ARGS, effect_slot="second")
        kernel.prepare(second)
        kernel.revoke(gid, authority)
        with pytest.raises(CoreError, match="AUTH_REVOKED"):
            kernel.dispatch(second)
        assert backend.calls == 0


def test_bound_directory_substitution_is_not_an_environment_repair(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, _, backend = construct(store, authority, directory)
        grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        kernel.prepare(action)
        directory.rename(tmp_path / "old")
        directory.mkdir()
        assert kernel.dispatch(action) == "UNKNOWN" and backend.calls == 0
        assert not (directory / "output.txt").exists()


def test_direct_port_call_requires_kernel_dispatch_and_atomic_binding(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, wrapper, backend = construct(store, authority, directory)
        grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        kernel.prepare(action)
        inv = kernel._invocation(store.one("actions", action))
        with pytest.raises(CoreError, match="KERNEL_INVOCATION_REQUIRED"):
            wrapper.execute(inv)
        assert backend.calls == 0


def test_write_requires_existing_filesystem_anchor_before_reservation(tmp_path):
    directory = tmp_path / "missing-owned-directory"
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, _, backend = construct(store, authority, directory)
        grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        with pytest.raises(CoreError, match="EXECUTION_WRITE_ANCHOR_REQUIRED"):
            kernel.prepare(action)
        assert backend.calls == 0 and not directory.exists()
        assert not store.all("attempts")
        assert store.one("actions", action)["state"] == "BLOCKED"


def test_stored_context_for_another_resource_cannot_route_this_action(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, _, backend = construct(store, authority, directory)
        grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        kernel.prepare(action)
        key = PREFIX + action
        pin = json.loads(store.one("core_meta", key)["value_json"])
        pin["resource"] = "notebook://synthetic/another-resource"
        with store.transaction("synthetic.context_corruption", {}) as tx:
            tx.update("core_meta", key, value_json=json.dumps(pin))
        assert kernel.dispatch(action) == "UNKNOWN"
        assert backend.calls == 0
        assert not (directory / "output.txt").exists()


def test_atomic_file_replacement_uses_original_independent_verifier(tmp_path):
    class AtomicFilePort(OwnedFilePort):
        def execute(self, inv):
            assert inv.resource == RESOURCE and inv.args == ARGS
            self.calls += 1
            temporary = self.output.with_suffix(".next")
            temporary.write_text(inv.args["content"])
            temporary.replace(self.output)
            return Receipt(external_id=inv.idempotency_key, result={"written": True})

    directory = tmp_path / "owned"
    directory.mkdir()
    output = directory / "output.txt"
    output.write_text("before")
    before_inode = output.stat().st_ino
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        _, original, _ = construct(store, authority, directory)
        old_router = original.router
        backend = AtomicFilePort(output)
        old_channel = old_router.channels["local-owned"]
        router = ExecutionContextRouter(
            old_router.source_probe,
            targets=tuple(old_router.targets.values()),
            channels=(ExecutionChannel("local-owned", "LOCAL", old_channel.probe, backend),),
            resources=(
                ResourceBinding(
                    resource=RESOURCE,
                    target_id="core-container",
                    path=str(output),
                    capabilities=("reading.card.create",),
                ),
            ),
        )
        wrapper = ContextBoundPort(store, router, authority)
        kernel = ActionKernel(store, wrapper, authority)
        grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        assert kernel.run(action) == "SUCCEEDED"
        assert output.stat().st_ino != before_inode
        assert output.read_text() == ARGS["content"]
        assert backend.calls == backend.verifies == 1


def test_successful_effect_can_be_reobserved_without_dispatch(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(tmp_path / "subject.db", clock) as store:
        kernel, _, backend = construct(store, authority, directory)
        grant(kernel, authority, clock)
        action = kernel.propose("reading.card.create", RESOURCE, ARGS)
        assert kernel.run(action) == "SUCCEEDED"
        observation = kernel.reobserve(action, authority)
        assert observation["verdict"] == "MATCH"
        assert backend.calls == 1 and backend.verifies == 2
        assert store.one("actions", action)["state"] == "SUCCEEDED"
