"""Synthetic endpoint identity tests; these do not contact SSH or a real host.

The process-local kernel probe supplies real metadata. Synthetic endpoint peers
then deliberately represent different namespace-qualified machines, including
the misleading case of the same absolute path and numeric UID.
"""

import time

import pytest

from nana_core.contracts import CoreError
from nana_core.execution_context.contracts import ContextBinding, IDMap
from nana_core.execution_context.probe import LocalContextProbe
from nana_core.execution_context.routing import (
    ExecutionChannel,
    ExecutionContextRouter,
    ResourceBinding,
    TargetBinding,
    require_fresh,
)
from nana_core.storage import digest


class SyntheticProbe:
    """Trusted test peer carrying a distinct synthetic namespace identity."""

    def __init__(self, target_id, scope, *, namespace=None, paths=None):
        self.local = LocalContextProbe(ContextBinding(target_id=target_id, scope=scope, binding_id="synthetic-peer"))
        self.target_id = target_id
        self.scope = scope
        self.namespace = namespace or target_id
        self.paths = paths or {}
        self.available = True
        self.capture_calls = 0
        self.observe_calls = []

    def capture(self):
        self.capture_calls += 1
        if not self.available:
            raise OSError("synthetic endpoint unavailable")
        original = self.local.capture()
        return original.model_copy(
            update={
                "context_id": digest(["SYNTHETIC", self.namespace]),
                "user_namespace": "user:[" + str(abs(hash(self.namespace)) % 10**9) + "]",
                "mount_namespace": "mnt:[" + str(abs(hash(self.namespace)) % 10**9) + "]",
                "uid": 999,
                "gid": 999,
                "euid": 999,
                "egid": 999,
                "uid_map": (IDMap(inside_id=0, outside_id=100000, count=65536),),
                "gid_map": (IDMap(inside_id=0, outside_id=100000, count=65536),),
                "observed_kind": "UNKNOWN" if self.scope == "HOST" else original.observed_kind,
                "container_signals": () if self.scope == "HOST" else original.container_signals,
            }
        )

    def observe(self, path):
        self.observe_calls.append(path)
        physical = self.paths.get(path, path)
        value = self.local.observe(physical)
        return value.model_copy(
            update={
                "context": self.capture(),
                "requested_path": path,
                "actual_path": path if value.status == "PRESENT" else None,
                "observed_at_us": time.time_ns() // 1000,
            }
        )


RESOURCE = "project://execution-context/document"


def target(probe, *channels):
    return TargetBinding(
        target_id=probe.target_id,
        context_id=probe.capture().context_id,
        scope=probe.scope,
        channel_ids=channels,
    )


def router(source, targets, channels, *, target_id="host", path="/workspace/document"):
    return ExecutionContextRouter(
        source,
        targets=targets,
        channels=channels,
        resources=(
            ResourceBinding(
                resource=RESOURCE,
                target_id=target_id,
                path=path,
                capabilities=("world.observe", "world.publish"),
            ),
        ),
    )


def test_same_absolute_path_has_distinct_context_file_and_uid_identity(tmp_path):
    core_file = tmp_path / "core-version"
    host_file = tmp_path / "host-version"
    core_file.write_text("core")
    host_file.write_text("host file has another version")
    path = "/srv/nana-core/runtime/version"
    core = SyntheticProbe("core-container", "CONTAINER", paths={path: str(core_file)})
    host = SyntheticProbe("host", "HOST", paths={path: str(host_file)})
    routes = router(
        core,
        (target(core, "core-local"), target(host, "host-operator")),
        (
            ExecutionChannel("core-local", "LOCAL", core, object()),
            ExecutionChannel("host-operator", "HOST_OPERATOR", host, object()),
        ),
        path=path,
    )

    core_evidence = routes.diagnose("core-container", path)
    host_evidence = routes.diagnose("host", path)
    core_observation = require_fresh(core_evidence, expected_target="core-container", max_age_us=5_000_000)
    host_observation = require_fresh(host_evidence, expected_target="host", max_age_us=5_000_000)
    assert core_observation.size != host_observation.size
    assert core_observation.context.euid == host_observation.context.euid == 999
    assert core_observation.context.user_namespace != host_observation.context.user_namespace
    assert core_observation.context.context_id != host_observation.context.context_id
    assert (core_observation.device, core_observation.inode) != (host_observation.device, host_observation.inode)
    assert host_evidence["source_context"]["target_id"] == "core-container"
    assert host_evidence["transport"] == "HOST_OPERATOR"
    assert host_evidence["host_path_equivalence"] == "UNKNOWN"
    assert host_evidence["execution_authority"] is False


def test_host_missing_file_does_not_become_container_missing_file(tmp_path):
    core_file = tmp_path / "only-in-container"
    core_file.write_text("exists")
    path = "/opt/nana-core/runtime/python"
    core = SyntheticProbe("core-container", "CONTAINER", paths={path: str(core_file)})
    host = SyntheticProbe("host", "HOST", paths={path: str(tmp_path / "missing-on-host")})
    routes = router(
        core,
        (target(core, "core-local"), target(host, "host-operator")),
        (
            ExecutionChannel("core-local", "LOCAL", core, object()),
            ExecutionChannel("host-operator", "HOST_OPERATOR", host, object()),
        ),
        path=path,
    )
    evidence = routes.diagnose("host", path)
    assert evidence["observation"]["status"] == "MISSING"
    assert evidence["observation"]["context"]["target_id"] == "host"
    assert core.observe_calls == []
    assert routes.diagnose("core-container", path)["observation"]["status"] == "PRESENT"


def test_local_channel_cannot_represent_a_different_host_context():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    routes = router(core, (target(host, "pretend-host"),), (ExecutionChannel("pretend-host", "LOCAL", host, object()),))
    with pytest.raises(CoreError, match="EXECUTION_LOCAL_TARGET_MISMATCH"):
        routes.select(RESOURCE, "world.publish")
    assert host.observe_calls == []


def test_unavailable_host_channel_never_falls_back_to_container_root():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    routes = router(core, (target(host, "not-installed"),), (ExecutionChannel("core-local", "LOCAL", core, object()),))
    with pytest.raises(CoreError, match="EXECUTION_CHANNEL_UNAVAILABLE"):
        routes.diagnose("host", "/")
    assert core.observe_calls == []


def test_host_operator_preferred_to_ssh_independent_of_declaration_order():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    routes = router(
        core,
        (target(host, "ssh-peer", "host-operator"),),
        (
            ExecutionChannel("ssh-peer", "SSH", host, object()),
            ExecutionChannel("host-operator", "HOST_OPERATOR", host, object()),
        ),
    )
    snapshot = routes.select(RESOURCE, "world.observe")
    assert snapshot.channel_id == "host-operator"
    assert snapshot.transport == "HOST_OPERATOR"
    assert snapshot.grants_authority is False


def test_only_predispatch_unavailability_may_choose_second_channel():
    core = SyntheticProbe("core-container", "CONTAINER")
    operator = SyntheticProbe("host", "HOST")
    ssh = SyntheticProbe("host", "HOST")
    routes = router(
        core,
        (target(operator, "host-operator", "ssh-peer"),),
        (
            ExecutionChannel("host-operator", "HOST_OPERATOR", operator, object()),
            ExecutionChannel("ssh-peer", "SSH", ssh, object()),
        ),
    )
    operator.available = False
    snapshot = routes.select(RESOURCE, "world.observe")
    assert snapshot.channel_id == "ssh-peer"
    assert snapshot.target_id == "host"


def test_pinned_channel_failure_does_not_switch_to_available_channel():
    core = SyntheticProbe("core-container", "CONTAINER")
    operator = SyntheticProbe("host", "HOST")
    ssh = SyntheticProbe("host", "HOST")
    routes = router(
        core,
        (target(operator, "host-operator", "ssh-peer"),),
        (
            ExecutionChannel("host-operator", "HOST_OPERATOR", operator, object()),
            ExecutionChannel("ssh-peer", "SSH", ssh, object()),
        ),
    )
    snapshot = routes.select(RESOURCE, "world.publish")
    operator.available = False
    before = ssh.capture_calls
    with pytest.raises(CoreError, match="EXECUTION_CHANNEL_UNAVAILABLE"):
        routes.channel_for(snapshot)
    assert ssh.capture_calls == before


def test_namespace_change_invalidates_selected_target_even_with_uid999():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    routes = router(core, (target(host, "operator"),), (ExecutionChannel("operator", "HOST_OPERATOR", host, object()),))
    snapshot = routes.select(RESOURCE, "world.publish")
    host.namespace = "host-new-user-namespace"
    assert host.capture().euid == snapshot.target_context.euid == 999
    with pytest.raises(CoreError, match="EXECUTION_TARGET_CONTEXT_MISMATCH"):
        routes.channel_for(snapshot)


def test_target_context_unknown_fails_closed():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    routes = router(core, (target(host, "operator"),), (ExecutionChannel("operator", "HOST_OPERATOR", host, object()),))
    previous = host.capture
    host.capture = lambda: previous().model_copy(update={"user_namespace": None, "unknown_fields": ("user_namespace",)})
    with pytest.raises(CoreError, match="EXECUTION_CONTEXT_UNKNOWN"):
        routes.select(RESOURCE, "world.publish")


def test_host_label_cannot_override_detected_container_hint():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    routes = router(core, (target(host, "operator"),), (ExecutionChannel("operator", "HOST_OPERATOR", host, object()),))
    previous = host.capture
    host.capture = lambda: previous().model_copy(
        update={"observed_kind": "CONTAINER_HINTS", "container_signals": ("DOCKER_MARKER",)}
    )
    with pytest.raises(CoreError, match="EXECUTION_HOST_CONTAINER_CONTRADICTION"):
        routes.select(RESOURCE, "world.publish")


@pytest.mark.parametrize("bad_age", [-1, 10_000_001])
def test_stale_and_future_evidence_never_count_as_current(tmp_path, bad_age):
    path = str(tmp_path / "observed")
    (tmp_path / "observed").write_text("metadata")
    core = SyntheticProbe("core-container", "CONTAINER")
    routes = router(
        core,
        (target(core, "local"),),
        (ExecutionChannel("local", "LOCAL", core, object()),),
        target_id=core.target_id,
        path=path,
    )
    evidence = routes.diagnose(core.target_id, path)
    now_us = time.time_ns() // 1000
    evidence["observed_at_us"] = now_us - bad_age
    with pytest.raises(CoreError, match="EXECUTION_EVIDENCE_STALE_OR_MISMATCHED"):
        require_fresh(evidence, expected_target=core.target_id, max_age_us=5_000_000, now_us=now_us)


def test_changed_resource_binding_does_not_reinterpret_old_snapshot():
    core = SyntheticProbe("core-container", "CONTAINER")
    host = SyntheticProbe("host", "HOST")
    targets = (target(host, "operator"),)
    channels = (ExecutionChannel("operator", "HOST_OPERATOR", host, object()),)
    first = router(core, targets, channels, path="/srv/nana-core/data/a")
    snapshot = first.select(RESOURCE, "world.publish")
    second = router(core, targets, channels, path="/srv/nana-core/data/b")
    with pytest.raises(CoreError, match="EXECUTION_ROUTE_CHANGED"):
        second.channel_for(snapshot)


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_id", "another-host"),
        ("target_context_id", "0" * 64),
        ("requested_path", "/srv/different-file"),
    ],
)
def test_repackaged_evidence_cannot_claim_another_target_or_path(tmp_path, field, value):
    path = str(tmp_path / "observed")
    (tmp_path / "observed").write_text("metadata")
    core = SyntheticProbe("core-container", "CONTAINER")
    routes = router(
        core,
        (target(core, "local"),),
        (ExecutionChannel("local", "LOCAL", core, object()),),
        target_id=core.target_id,
        path=path,
    )
    evidence = routes.diagnose(core.target_id, path)
    evidence[field] = value
    with pytest.raises(CoreError, match="EXECUTION_EVIDENCE_STALE_OR_MISMATCHED"):
        require_fresh(evidence, expected_target=core.target_id, max_age_us=5_000_000)


def test_unbound_resources_and_unsafe_paths_have_no_inferred_target():
    core = SyntheticProbe("core-container", "CONTAINER")
    routes = router(
        core, (target(core, "local"),), (ExecutionChannel("local", "LOCAL", core, object()),), target_id=core.target_id
    )
    with pytest.raises(CoreError, match="EXECUTION_RESOURCE_UNBOUND"):
        routes.select("file:///srv/nana-core/data", "world.publish")
    with pytest.raises(CoreError, match="EXECUTION_RESOURCE_UNBOUND"):
        routes.select(RESOURCE, "shell.exec")
    with pytest.raises(CoreError, match="EXECUTION_PATH_INVALID"):
        routes.diagnose(core.target_id, "/srv/nana-core/../private")
