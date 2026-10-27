"""The old standalone inventory must never turn local metadata into host proof."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from nana_core.execution_context.contracts import ExecutionContext
from tools.nana_first_life_android_v2 import host_probe


def arguments(**changes):
    values = dict(subject=None, backups=None, container=None, python=None, container_runtime="/opt/nana-core")
    values.update(changes)
    return argparse.Namespace(**values)


def current_context():
    return ExecutionContext(
        target_id="local-process", binding_id="operator-local-probe", scope="UNKNOWN",
        context_id="a" * 64, observed_at_us=123,
        uid=0, gid=0, euid=0, egid=0,
        user_namespace="user:[101]", mount_namespace="mnt:[102]", pid_namespace="pid:[103]",
        root_device=10, root_inode=11, container_signals=("DOCKER_MARKER",),
    )


def local_process(monkeypatch, *, systemd=False):
    monkeypatch.setattr(host_probe, "local_probe", lambda: SimpleNamespace(capture=current_context))
    original_read = Path.read_text
    original_is_dir = Path.is_dir

    def read(path, *args, **kwargs):
        if str(path) == "/proc/1/comm":
            return "systemd\n" if systemd else "container-init\n"
        return original_read(path, *args, **kwargs)

    def is_dir(path):
        return systemd if str(path) == "/run/systemd/system" else original_is_dir(path)

    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(Path, "is_dir", is_dir)


def test_container_root_and_pid1_are_not_host_authority(monkeypatch):
    local_process(monkeypatch)

    def denied(*args, **kwargs):
        raise AssertionError("No external command expected")

    monkeypatch.setattr(host_probe.subprocess, "run", denied)
    result = host_probe.probe(arguments())
    assert result["process_euid_is_zero"] is True
    assert result["root_identity_scope"] == "CURRENT_USER_NAMESPACE_ONLY"
    assert result["running_as_root_deprecated"] is True
    assert result["host_verification"] == result["host_root_authority"] == "UNKNOWN"
    assert result["execution_context"]["scope"] == "UNKNOWN"
    assert result["execution_context"]["context_id"] == "a" * 64
    assert result["systemd_state"] == "NOT_OBSERVED_IN_EXECUTION_CONTEXT"


def test_systemd_presence_is_current_namespace_observation(monkeypatch):
    local_process(monkeypatch, systemd=True)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(stdout="running\n", returncode=0)

    monkeypatch.setattr(host_probe.subprocess, "run", run)
    result = host_probe.probe(arguments())
    assert calls == [["systemctl", "is-system-running", "--no-pager"]]
    assert result["systemd_state"] == "running"
    assert result["systemd_observation_scope"] == "CURRENT_EXECUTION_CONTEXT_ONLY"
    assert result["host_verification"] == "UNKNOWN"


def test_directory_metadata_and_missing_path_remain_context_bound(tmp_path):
    real = tmp_path / "present"
    real.mkdir()
    result = host_probe.directory(real)
    metadata = result["path_observation"]
    assert result["directory"] is True
    assert result["host_verification"] == "UNKNOWN"
    assert metadata["context"]["target_id"] == "local-process"
    assert metadata["context"]["scope"] == "UNKNOWN"
    assert metadata["actual_path"] == str(real)
    assert (metadata["device"], metadata["inode"]) == (real.stat().st_dev, real.stat().st_ino)
    missing = host_probe.directory(tmp_path / "absent")
    assert missing["state"] == "NOT_PRESENT_IN_EXECUTION_CONTEXT"
    assert missing["path_observation"]["status"] == "MISSING"
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    assert host_probe.directory(link)["state"] == "SYMLINK_REVIEW_REQUIRED"


def test_docker_mount_source_does_not_prove_local_host_path(monkeypatch):
    local_process(monkeypatch)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        rows = [{"Type": "bind", "Source": "/srv/nana-core", "Destination": "/opt/nana-core", "RW": False}]
        return SimpleNamespace(stdout=json.dumps(rows), returncode=0)

    monkeypatch.setattr(host_probe.subprocess, "run", run)
    result = host_probe.probe(arguments(container="synthetic-core"))["runtime_persistence"]
    assert calls == [["docker", "inspect", "--format", "{{json .Mounts}}", "synthetic-core"]]
    assert result["persistent"] is True
    assert result["host_verification"] == result["docker_endpoint_scope"] == "UNKNOWN"
    assert result["source_path_scope"] == "DOCKER_DAEMON_METADATA_NOT_LOCAL_FILESYSTEM_PROOF"
    assert result["observation_context_id"] == "a" * 64
