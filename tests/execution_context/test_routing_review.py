"""Independent negative checks for identity-label, freshness and path binding."""

from copy import deepcopy
import time

import pytest

from nana_core.contracts import CoreError
from nana_core.execution_context.contracts import ContextBinding
from nana_core.execution_context.probe import LocalContextProbe
from nana_core.execution_context.routing import (
    ExecutionChannel, ExecutionContextRouter, ResourceBinding, TargetBinding, require_fresh,
)


RESOURCE = "project://review/bound-path"


class View:
    """Synthetic label/view over the same physical development process."""

    def __init__(self, target, scope, *, age_us=0, omit_mount_digest=False):
        self.local = LocalContextProbe(ContextBinding(target_id=target, scope=scope, binding_id="review-only"))
        self.target = target
        self.scope = scope
        self.age_us = age_us
        self.omit_mount_digest = omit_mount_digest

    def capture(self):
        value = self.local.capture()
        return value.model_copy(update={
            "observed_kind": "UNKNOWN", "container_signals": (),
            "observed_at_us": time.time_ns() // 1000 - self.age_us,
            "mount_table_digest": None if self.omit_mount_digest else value.mount_table_digest,
        })

    def observe(self, path):
        return self.local.observe(path).model_copy(update={"context": self.capture()})


def build(source, peer, path="/", kind="LOCAL"):
    return ExecutionContextRouter(
        source,
        targets=(TargetBinding(target_id=peer.target, context_id=peer.capture().context_id,
                               scope=peer.scope, channel_ids=("review",)),),
        channels=(ExecutionChannel("review", kind, peer, object()),),
        resources=(ResourceBinding(resource=RESOURCE, target_id=peer.target, path=path,
                                   capabilities=("world.publish",)),),
    )


@pytest.mark.parametrize("kind,code", [
    ("LOCAL", "EXECUTION_LOCAL_TARGET_MISMATCH"),
    ("HOST_OPERATOR", "EXECUTION_SCOPE_IDENTITY_CONFLICT"),
])
def test_relabeling_same_process_container_as_host_is_rejected_without_markers(kind, code):
    core = View("core-container", "CONTAINER")
    mislabeled = View("host", "HOST")
    assert core.capture().context_id == mislabeled.capture().context_id
    with pytest.raises(CoreError, match=code):
        build(core, mislabeled, kind=kind).select(RESOURCE, "world.publish")


@pytest.mark.parametrize("source_age,peer_age", [(0, 6_000_000), (6_000_000, 0), (0, -6_000_000)])
def test_action_selection_refuses_stale_or_future_capture_before_dispatch(source_age, peer_age):
    source = View("core-container", "CONTAINER", age_us=source_age)
    peer = View("core-container", "CONTAINER", age_us=peer_age)
    with pytest.raises(CoreError, match="EXECUTION_CONTEXT_STALE"):
        build(source, peer).select(RESOURCE, "world.publish")


def test_missing_mount_table_identity_fails_closed_even_without_unknown_list():
    peer = View("core-container", "CONTAINER", omit_mount_digest=True)
    assert peer.capture().unknown_fields == ()
    with pytest.raises(CoreError, match="EXECUTION_CONTEXT_UNKNOWN"):
        build(peer, peer).select(RESOURCE, "world.publish")


def test_fresh_evidence_rejects_wrong_requested_actual_and_expected_path(tmp_path):
    path = tmp_path / "bound-file"
    path.write_text("PUBLIC synthetic")
    peer = View("core-container", "CONTAINER")
    evidence = build(peer, peer, path=str(path)).diagnose("core-container", str(path))
    options = dict(expected_target="core-container", expected_path=str(path), max_age_us=5_000_000)
    assert require_fresh(evidence, **options).status == "PRESENT"
    for field in ("requested_path", "observation.requested_path", "observation.actual_path", "observation.inode"):
        changed = deepcopy(evidence)
        if field.startswith("observation."):
            changed["observation"][field.split(".")[1]] = None if field.endswith(".inode") else "/different-file"
        else:
            changed[field] = "/different-file"
        with pytest.raises(CoreError, match="EXECUTION_EVIDENCE_STALE_OR_MISMATCHED"):
            require_fresh(changed, **options)
    with pytest.raises(CoreError, match="EXECUTION_EVIDENCE_STALE_OR_MISMATCHED"):
        require_fresh(evidence, **{**options, "expected_path": "/different-file"})


def test_predispatch_selection_skips_diagnostic_only_channel_without_port(tmp_path):
    path = tmp_path / "bound-file"
    path.write_text("PUBLIC synthetic")
    peer = View("core-container", "CONTAINER")
    routes = ExecutionContextRouter(
        peer,
        targets=(TargetBinding(target_id=peer.target, context_id=peer.capture().context_id,
                               scope=peer.scope, channel_ids=("operator", "ssh")),),
        channels=(ExecutionChannel("operator", "HOST_OPERATOR", peer),
                  ExecutionChannel("ssh", "SSH", peer, object())),
        resources=(ResourceBinding(resource=RESOURCE, target_id=peer.target, path=str(path),
                                   capabilities=("world.publish",)),),
    )
    assert routes.diagnose(peer.target, str(path))["channel_id"] == "operator"
    selected = routes.select(RESOURCE, "world.publish")
    assert selected.channel_id == "ssh" and selected.transport == "SSH"
    assert selected.grants_authority is False


def test_source_probe_failure_is_sanitized_and_not_a_target_missing_file():
    class UnavailableSource:
        def capture(self):
            raise PermissionError("PRIVATE_SYNTHETIC_DIAGNOSTIC_NOT_TO_EXPOSE")

    peer = View("core-container", "CONTAINER")
    with pytest.raises(CoreError, match="EXECUTION_SOURCE_CONTEXT_UNAVAILABLE") as error:
        build(UnavailableSource(), peer).select(RESOURCE, "world.publish")
    assert "PRIVATE_SYNTHETIC_DIAGNOSTIC_NOT_TO_EXPOSE" not in str(error.value)
