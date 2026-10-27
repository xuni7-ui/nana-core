"""Kernel metadata and filesystem differences, never live host control."""

import errno
import os

import pytest

from nana_core.contracts import CoreError
from nana_core.execution_context.contracts import ContextBinding
from nana_core.execution_context import probe


def local_probe(target="core-container", scope="CONTAINER"):
    return probe.LocalContextProbe(
        ContextBinding(target_id=target, scope=scope, binding_id="explicit-test-binding")
    )


def test_actual_process_identity_is_scoped_and_labels_do_not_change_physical_identity(tmp_path):
    first = local_probe().capture()
    other = local_probe("host", "HOST").capture()
    assert first.context_id == other.context_id
    assert first.uid == os.getuid() and first.euid == os.geteuid()
    assert first.supplementary_gids == tuple(sorted(set(os.getgroups())))
    assert first.mount_table_digest
    assert first.mount_namespace and first.user_namespace and first.root_inode
    assert first.grants_authority is False
    # Scope is supplied metadata, never proof that this process is the host.
    assert other.observed_kind in {"CONTAINER_HINTS", "UNKNOWN"}
    assert "HOST" not in first.observed_kind
    path = tmp_path / "only-in-this-filesystem.txt"
    path.write_text("PUBLIC_SYNTHETIC_CONTENT_NOT_RETURNED")
    observed = local_probe().observe(str(path))
    assert observed.status == "PRESENT" and observed.actual_path == str(path)
    info = path.stat()
    assert (observed.device, observed.inode, observed.uid, observed.gid) == (
        info.st_dev, info.st_ino, info.st_uid, info.st_gid
    )
    assert observed.mount and observed.mount.fs_type
    assert "PUBLIC_SYNTHETIC_CONTENT_NOT_RETURNED" not in observed.model_dump_json()


def test_path_change_and_different_inode_remain_distinguishable(tmp_path):
    path = tmp_path / "item"
    other = tmp_path / "same-name-elsewhere"
    path.write_text("v1")
    other.write_text("v2-longer")
    p = local_probe()
    first, second = p.observe(str(path)), p.observe(str(other))
    assert first.context.context_id == second.context.context_id
    assert first.inode != second.inode
    path.write_text("version-changed")
    changed = p.observe(str(path))
    assert changed.inode == first.inode and changed.size != first.size
    assert changed.observed_at_us >= first.observed_at_us
    path.unlink()
    missing = p.observe(str(path))
    assert missing.status == "MISSING" and missing.actual_path is None
    assert missing.context.target_id == "core-container"
    assert missing.code == "EXECUTION_PATH_MISSING_IN_THIS_CONTEXT"


def test_all_symlink_components_are_refused_without_reading_targets(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "file").write_text("DO_NOT_READ")
    (tmp_path / "indirect").symlink_to(actual, target_is_directory=True)
    (tmp_path / "file-link").symlink_to(actual / "file")
    p = local_probe()
    for path in (tmp_path / "indirect" / "file", tmp_path / "file-link"):
        observation = p.observe(str(path))
        assert observation.status == "SYMLINK"
        assert observation.actual_path is None and observation.inode is None
    for path in ("relative", str(tmp_path) + "/../private", "/nul\x00", "/bad\npath"):
        with pytest.raises(CoreError):
            p.observe(path)


def test_permission_and_unknown_errors_are_distinct(tmp_path, monkeypatch):
    path = tmp_path / "denied-parent"
    path.mkdir()
    original_open = probe.os.open

    def denied(name, *args, **kwargs):
        if name == "denied-parent":
            raise PermissionError(errno.EACCES, "synthetic error text must not appear")
        return original_open(name, *args, **kwargs)

    monkeypatch.setattr(probe.os, "open", denied)
    observation = local_probe().observe(str(path / "file"))
    assert observation.status == "DENIED"
    assert "synthetic error" not in observation.model_dump_json()

    def io_error(name, *args, **kwargs):
        if name == "denied-parent":
            raise OSError(errno.EIO, "synthetic")
        return original_open(name, *args, **kwargs)

    monkeypatch.setattr(probe.os, "open", io_error)
    assert local_probe().observe(str(path / "file")).status == "UNKNOWN"


def test_uid_map_is_parent_numeric_mapping_not_display_name_or_host_identity():
    ranges = probe.parse_id_map("0 100000 1000\n1000 200000 1000\n")
    assert probe.parent_namespace_id(999, ranges) == 100999
    assert probe.parent_namespace_id(1000, ranges) == 200000
    assert probe.parent_namespace_id(3000, ranges) is None
    for raw in ("", "0 1 0", "0 100000 1000\n999 200000 1000", "0 100 10\n100 105 10", "0 name 5"):
        with pytest.raises(ValueError):
            probe.parse_id_map(raw)


def test_mountinfo_overlay_bind_subtree_escape_and_component_boundary():
    raw = "\n".join((
        "30 1 0:27 / / rw,relatime - overlay overlay rw,lowerdir=/private/omitted,upperdir=/private/omitted",
        "31 30 8:1 /srv/project /opt/project rw,relatime shared:1 - ext4 /dev/sda1 rw",
        "32 30 8:2 / /opt/project-long ro - ext4 /dev/sdb1 ro",
        r"33 30 8:3 /share\040name /shared\040path ro - ext4 /dev/sdc1 ro",
    ))
    mounts = probe.parse_mountinfo(raw)
    assert mounts[0].backing_kind == "OVERLAY"
    assert mounts[1].backing_kind == "SUBTREE"
    assert mounts[1].filesystem_root == "/srv/project"
    assert mounts[3].mount_point == "/shared path"
    assert mounts[3].filesystem_root == "/share name"
    assert mounts[2].read_only
    assert probe.mount_for_path("/opt/project/file", mounts).mount_id == 31
    assert probe.mount_for_path("/opt/project-longer/file", mounts).mount_id == 30
    assert "/private/omitted" not in mounts[0].model_dump_json()
    assert "/dev/sda1" not in mounts[1].model_dump_json()
    for bad in ("", "30 1 0:27 / / rw overlay", raw + "\n" + raw.splitlines()[0]):
        with pytest.raises(ValueError):
            probe.parse_mountinfo(bad)


def test_unavailable_kernel_fields_and_absent_markers_are_unknown(monkeypatch):
    original_read = probe._read_kernel
    original_lstat = probe.os.lstat

    def read(path, limit=probe.MAX_KERNEL_BYTES):
        if path in {"/proc/self/uid_map", "/proc/self/gid_map"}:
            raise PermissionError("not available")
        if path == "/proc/self/cgroup":
            return "0::/\n"
        return original_read(path, limit)

    def lstat(path, *args, **kwargs):
        if path in {"/.dockerenv", "/run/.containerenv"}:
            raise FileNotFoundError
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(probe, "_read_kernel", read)
    monkeypatch.setattr(probe.os, "lstat", lstat)
    monkeypatch.setattr(probe, "_namespace", lambda name: (_ for _ in ()).throw(PermissionError()))
    context = local_probe(scope="UNKNOWN").capture()
    assert context.observed_kind == "UNKNOWN" and context.scope == "UNKNOWN"
    assert context.uid_map == () and context.user_namespace is None
    assert {"uid_map", "gid_map", "user_namespace", "mount_namespace", "pid_namespace"} <= set(context.unknown_fields)


def test_mount_table_update_changes_context_fingerprint_without_namespace_change(monkeypatch):
    p = local_probe()
    first = p.capture()
    original_read = probe._read_kernel

    def read(path, limit=probe.MAX_KERNEL_BYTES):
        raw = original_read(path, limit)
        if path == "/proc/self/mountinfo":
            return raw.replace(" - ", " shared:999999 - ", 1)
        return raw

    monkeypatch.setattr(probe, "_read_kernel", read)
    changed = p.capture()
    assert first.mount_namespace == changed.mount_namespace
    assert first.mount_table_digest != changed.mount_table_digest
    assert first.context_id != changed.context_id
