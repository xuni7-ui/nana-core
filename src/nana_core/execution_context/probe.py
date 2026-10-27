"""Trusted, bounded Linux metadata probes without shells or arbitrary reads.

The probe reads only kernel metadata and lstat/open directory handles. It never
reads file contents, credentials, process environments or account databases. A
container marker is evidence of containment; absent markers cannot prove HOST.
Every path is walked with O_NOFOLLOW directory descriptors, preventing an
intermediate symlink from silently redirecting a check to another filesystem.
"""

import errno
import os
import re
import stat
import time

from ..contracts import CoreError
from ..storage import digest
from .contracts import ContextBinding, ExecutionContext, IDMap, MountMetadata, PathObservation


MAX_KERNEL_BYTES = 262144


def _read_kernel(path: str, limit: int = MAX_KERNEL_BYTES) -> str:
    with open(path, "rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("KERNEL_METADATA_BOUND")
    return raw.decode("utf-8", errors="strict")


def parse_id_map(raw: str) -> tuple[IDMap, ...]:
    """Parse parent-namespace mapping, rejecting partial/overlapping ranges."""
    if len(raw) > 16384:
        raise ValueError("ID_MAP_BOUND")
    rows = []
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 3 or not all(re.fullmatch(r"[0-9]{1,10}", item) for item in fields):
            raise ValueError("ID_MAP_INVALID")
        rows.append(IDMap(inside_id=int(fields[0]), outside_id=int(fields[1]), count=int(fields[2])))
    if not rows or len(rows) > 128:
        raise ValueError("ID_MAP_BOUND")
    for attr in ("inside_id", "outside_id"):
        ordered = sorted(rows, key=lambda row: getattr(row, attr))
        if any(getattr(a, attr) + a.count > getattr(b, attr) for a, b in zip(ordered, ordered[1:])):
            raise ValueError("ID_MAP_OVERLAP")
    return tuple(rows)


def parent_namespace_id(value: int, ranges: tuple[IDMap, ...]) -> int | None:
    """Translate only to the direct parent; never call the result a host UID."""
    for row in ranges:
        if row.inside_id <= value < row.inside_id + row.count:
            return row.outside_id + value - row.inside_id
    return None


def _unescape(value: str) -> str:
    if len(value) > 16384:
        raise ValueError("MOUNT_FIELD_BOUND")
    # mountinfo escapes backslash, space, tab and newline with octal encoding.
    return re.sub(r"\\(040|011|012|134)", lambda match: chr(int(match[1], 8)), value)


def parse_mountinfo(raw: str) -> tuple[MountMetadata, ...]:
    """Parse mountinfo without exposing overlay lowerdirs or source file paths.

    SUBTREE is a relation, not proof of a bind mount or host path equivalence.
    A trusted operator mapping is still required to translate paths across peers.
    """
    if len(raw.encode("utf-8")) > MAX_KERNEL_BYTES:
        raise ValueError("MOUNTINFO_BOUND")
    rows = []
    for line in raw.splitlines():
        fields = line.split()
        try:
            separator = fields.index("-")
            if separator < 6 or len(fields) < separator + 4:
                raise ValueError("MOUNTINFO_INVALID")
            root, point = _unescape(fields[3]), _unescape(fields[4])
            if not root.startswith("/") or not point.startswith("/"):
                raise ValueError("MOUNTINFO_PATH_INVALID")
            source = _unescape(fields[separator + 2])
            fs_type = fields[separator + 1]
            options = set(fields[5].split(",")) | set(fields[separator + 3].split(","))
            rows.append(MountMetadata(
                mount_id=int(fields[0]), parent_id=int(fields[1]), device=fields[2],
                mount_point=point, filesystem_root=root, filesystem_root_digest=digest(root), fs_type=fs_type,
                source_kind="PATH" if source.startswith("/") else "NAMED" if source != "none" else "UNKNOWN",
                source_digest=None if source == "none" else digest(source),
                backing_kind="OVERLAY" if fs_type == "overlay" else "SUBTREE" if root != "/" else "FILESYSTEM",
                read_only="ro" in options,
            ))
        except (IndexError, ValueError) as exc:
            raise ValueError("MOUNTINFO_INVALID") from exc
        if len(rows) > 4096:
            raise ValueError("MOUNTINFO_BOUND")
    if not rows or len({row.mount_id for row in rows}) != len(rows):
        raise ValueError("MOUNTINFO_INVALID")
    return tuple(rows)


def mount_for_path(path: str, mounts: tuple[MountMetadata, ...]) -> MountMetadata | None:
    """Select the longest component-boundary mount point in this namespace."""
    matches = [row for row in mounts if path == row.mount_point or path.startswith(row.mount_point.rstrip("/") + "/")]
    return max(matches, key=lambda row: len(row.mount_point), default=None)


def _namespace(name: str) -> str:
    value = os.readlink("/proc/self/ns/" + name)
    if not re.fullmatch(r"[a-z]+:\[[0-9]{1,20}\]", value):
        raise ValueError("NAMESPACE_INVALID")
    return value


def _path_parts(path: str) -> tuple[str, ...]:
    if not isinstance(path, str) or not path.startswith("/") or len(os.fsencode(path)) > 4096 or "\x00" in path:
        raise CoreError("EXECUTION_ABSOLUTE_PATH_REQUIRED")
    parts = path.split("/")[1:]
    if any(part in {".", ".."} for part in parts) or any(ord(c) < 32 for c in path):
        raise CoreError("EXECUTION_PATH_INVALID")
    return tuple(part for part in parts if part)


def _container_signals(unknown: list[str]) -> tuple[str, ...]:
    signals = []
    for filename, label in (("/.dockerenv", "DOCKER_MARKER"), ("/run/.containerenv", "CONTAINERENV_MARKER")):
        try:
            os.lstat(filename)
            signals.append(label)
        except FileNotFoundError:
            pass
        except OSError:
            unknown.append(label)
    try:
        cgroup = _read_kernel("/proc/self/cgroup", 16384).lower()
        if any(marker in cgroup for marker in ("docker", "kubepods", "containerd", "lxc")):
            signals.append("CONTAINER_CGROUP")
    except (OSError, ValueError):
        unknown.append("cgroup_container_signal")
    return tuple(signals)


def _process_flags(unknown: list[str]) -> dict:
    values = dict(cap_effective=None, no_new_privs=None, seccomp_mode=None)
    try:
        status = _read_kernel("/proc/self/status", 65536)
        cap = re.search(r"^CapEff:\s*([a-fA-F0-9]{1,32})$", status, flags=re.MULTILINE)
        no_new = re.search(r"^NoNewPrivs:\s*([01])$", status, flags=re.MULTILINE)
        seccomp = re.search(r"^Seccomp:\s*([012])$", status, flags=re.MULTILINE)
        values["cap_effective"] = cap[1] if cap else None
        values["no_new_privs"] = no_new[1] == "1" if no_new else None
        values["seccomp_mode"] = int(seccomp[1]) if seccomp else None
        if not cap:
            unknown.append("cap_effective")
        if not no_new or not seccomp:
            unknown.append("process_isolation_flags")
    except (OSError, ValueError):
        unknown.extend(("cap_effective", "process_isolation_flags"))
    return values


def _boot_digest(unknown: list[str]) -> str | None:
    try:
        boot = _read_kernel("/proc/sys/kernel/random/boot_id", 128).strip()
        if not re.fullmatch(r"[a-f0-9-]{36}", boot):
            raise ValueError("BOOT_ID_INVALID")
        return digest(boot)
    except (OSError, ValueError):
        unknown.append("boot_identity")
        return None


def _error_result(exc: OSError) -> dict:
    if exc.errno in {errno.ENOENT, errno.ENOTDIR}:
        return dict(status="MISSING", code="EXECUTION_PATH_MISSING_IN_THIS_CONTEXT")
    if exc.errno in {errno.EACCES, errno.EPERM}:
        return dict(status="DENIED", code="EXECUTION_PATH_PERMISSION_DENIED")
    if exc.errno == errno.ELOOP:
        return dict(status="SYMLINK", code="EXECUTION_SYMLINK_DENIED")
    return dict(status="UNKNOWN", code="EXECUTION_METADATA_UNAVAILABLE")


class LocalContextProbe:
    """A process-local observer with an explicit trusted application label."""

    def __init__(self, binding: ContextBinding):
        if type(binding) is not ContextBinding:
            raise CoreError("EXECUTION_CONTEXT_BINDING_REQUIRED")
        self.binding = binding

    def capture(self) -> ExecutionContext:
        now = time.time_ns() // 1000
        unknown = []
        values = {}
        for name, field in (("user", "user_namespace"), ("mnt", "mount_namespace"), ("pid", "pid_namespace")):
            try:
                values[field] = _namespace(name)
            except (OSError, ValueError):
                values[field] = None
                unknown.append(field)
        for name in ("uid_map", "gid_map"):
            try:
                values[name] = parse_id_map(_read_kernel("/proc/self/" + name, 16384))
            except (OSError, ValueError):
                values[name] = ()
                unknown.append(name)
        try:
            root = os.stat("/", follow_symlinks=False)
            values.update(root_device=root.st_dev, root_inode=root.st_ino)
        except OSError:
            values.update(root_device=None, root_inode=None)
            unknown.append("root_identity")
        try:
            mount_table = _read_kernel("/proc/self/mountinfo")
            parse_mountinfo(mount_table)
            values["mount_table_digest"] = digest(mount_table)
        except (OSError, ValueError):
            values["mount_table_digest"] = None
            unknown.append("mount_table_digest")
        boot_digest = _boot_digest(unknown)
        signals = _container_signals(unknown)
        values.update(_process_flags(unknown))
        numeric = dict(uid=os.getuid(), gid=os.getgid(), euid=os.geteuid(), egid=os.getegid())
        try:
            groups = tuple(sorted(set(os.getgroups())))
            if len(groups) > 1024:
                raise ValueError("SUPPLEMENTARY_GROUP_BOUND")
        except (OSError, ValueError):
            groups = ()
            unknown.append("supplementary_gids")
        fingerprint = digest({"boot": boot_digest, **numeric, "supplementary_gids": groups,
                              **{key: value if not isinstance(value, tuple) else [r.model_dump(mode="json") for r in value]
                                 for key, value in values.items()}})
        return ExecutionContext(**self.binding.model_dump(), context_id=fingerprint, observed_at_us=now,
                                **numeric, **values, supplementary_gids=groups,
                                container_signals=tuple(signals), unknown_fields=tuple(unknown),
                                observed_kind="CONTAINER_HINTS" if signals else "UNKNOWN")

    def observe(self, path: str) -> PathObservation:
        parts = _path_parts(path)
        context = self.capture()
        normalized = "/" + "/".join(parts)
        base = dict(context=context, requested_path=path, observed_at_us=time.time_ns() // 1000)
        fd = None
        try:
            fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            for part in parts[:-1]:
                info = os.stat(part, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    return PathObservation(**base, status="SYMLINK", code="EXECUTION_SYMLINK_DENIED")
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            info = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False) if parts else os.fstat(fd)
            if stat.S_ISLNK(info.st_mode):
                return PathObservation(**base, status="SYMLINK", code="EXECUTION_SYMLINK_DENIED")
            try:
                mount = mount_for_path(normalized, parse_mountinfo(_read_kernel("/proc/self/mountinfo")))
            except (OSError, ValueError):
                mount = None
            # Check that the namespace/credential binding did not change mid-probe.
            if self.capture().context_id != context.context_id:
                return PathObservation(**base, status="UNKNOWN", code="EXECUTION_CONTEXT_CHANGED")
            return PathObservation(**base, actual_path=normalized, status="PRESENT", code="EXECUTION_METADATA_OBSERVED",
                                   device=info.st_dev, inode=info.st_ino, uid=info.st_uid, gid=info.st_gid,
                                   mode=stat.S_IMODE(info.st_mode), mtime_ns=info.st_mtime_ns, size=info.st_size,
                                   file_kind="FILE" if stat.S_ISREG(info.st_mode) else "DIRECTORY" if stat.S_ISDIR(info.st_mode) else "OTHER",
                                   mount=mount)
        except OSError as exc:
            return PathObservation(**base, **_error_result(exc))
        finally:
            if fd is not None:
                os.close(fd)
