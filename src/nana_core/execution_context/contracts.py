"""Kernel-observed execution metadata, never a Grant or a Subject identity.

Target labels are explicit application bindings. Numeric identities are scoped by
user namespace; an ``outside_id`` refers to the parent namespace, not necessarily
the physical host. File identity also includes its execution context.
"""

from typing import Literal

from pydantic import Field, model_validator

from ..contracts import DTO


class ContextBinding(DTO):
    """Application-owned endpoint label; its text grants no execution authority."""

    target_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    scope: Literal["HOST", "CONTAINER", "EXTERNAL_DEVICE", "UNKNOWN"] = "UNKNOWN"
    binding_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


class IDMap(DTO):
    """A Linux user-namespace range, with no account-name authority."""

    inside_id: int = Field(ge=0, le=4294967295)
    outside_id: int = Field(ge=0, le=4294967295)
    count: int = Field(gt=0, le=4294967295)

    @model_validator(mode="after")
    def bounded(self):
        if max(self.inside_id, self.outside_id) + self.count > 4294967296:
            raise ValueError("ID_MAP_RANGE_INVALID")
        return self


class MountMetadata(DTO):
    """Bounded mount relation; overlay options and host source paths are omitted."""

    mount_id: int = Field(gt=0)
    parent_id: int = Field(ge=0)
    device: str = Field(pattern=r"^\d{1,10}:\d{1,10}$")
    mount_point: str = Field(min_length=1, max_length=4096)
    filesystem_root: str = Field(min_length=1, max_length=4096)
    filesystem_root_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    fs_type: str = Field(pattern=r"^[a-zA-Z0-9._-]{1,64}$")
    source_kind: Literal["PATH", "NAMED", "UNKNOWN"]
    source_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    backing_kind: Literal["OVERLAY", "SUBTREE", "FILESYSTEM"]
    read_only: bool


class ExecutionContext(DTO):
    """A point-in-time local process observation; UNKNOWN is not host proof."""

    target_id: str
    binding_id: str
    scope: Literal["HOST", "CONTAINER", "EXTERNAL_DEVICE", "UNKNOWN"]
    context_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    observed_at_us: int = Field(ge=0)
    uid: int = Field(ge=0)
    gid: int = Field(ge=0)
    euid: int = Field(ge=0)
    egid: int = Field(ge=0)
    supplementary_gids: tuple[int, ...] = Field(default=(), max_length=1024)
    user_namespace: str | None = None
    mount_namespace: str | None = None
    pid_namespace: str | None = None
    root_device: int | None = None
    root_inode: int | None = None
    mount_table_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    uid_map: tuple[IDMap, ...] = Field(default=(), max_length=128)
    gid_map: tuple[IDMap, ...] = Field(default=(), max_length=128)
    container_signals: tuple[str, ...] = Field(default=(), max_length=8)
    cap_effective: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{1,32}$")
    no_new_privs: bool | None = None
    seccomp_mode: Literal[0, 1, 2] | None = None
    observed_kind: Literal["CONTAINER_HINTS", "UNKNOWN"] = "UNKNOWN"
    unknown_fields: tuple[str, ...] = Field(default=(), max_length=16)
    grants_authority: Literal[False] = False


class PathObservation(DTO):
    """Metadata only, with filesystem identity qualified by context and time."""

    context: ExecutionContext
    requested_path: str = Field(min_length=1, max_length=4096)
    actual_path: str | None = Field(default=None, max_length=4096)
    observed_at_us: int = Field(ge=0)
    status: Literal["PRESENT", "MISSING", "DENIED", "SYMLINK", "UNKNOWN"]
    device: int | None = Field(default=None, ge=0)
    inode: int | None = Field(default=None, gt=0)
    uid: int | None = Field(default=None, ge=0)
    gid: int | None = Field(default=None, ge=0)
    mode: int | None = Field(default=None, ge=0, le=0o7777)
    mtime_ns: int | None = None
    size: int | None = Field(default=None, ge=0)
    file_kind: Literal["FILE", "DIRECTORY", "OTHER"] | None = None
    mount: MountMetadata | None = None
    code: str
    grants_authority: Literal[False] = False

    @model_validator(mode="after")
    def complete_presence(self):
        if self.status != "PRESENT":
            if self.actual_path is not None:
                raise ValueError("NONPRESENT_ACTUAL_PATH_INVALID")
            return self
        metadata = (self.actual_path, self.device, self.inode, self.uid, self.gid,
                    self.mode, self.mtime_ns, self.size, self.file_kind)
        if any(value is None for value in metadata):
            raise ValueError("PRESENT_PATH_METADATA_REQUIRED")
        path = self.actual_path
        parts = path.split("/")[1:]
        if (not path.startswith("/") or path != "/" + "/".join(p for p in parts if p)
            or any(p in {".", ".."} for p in parts) or any(ord(c) < 32 for c in path)):
            raise ValueError("PRESENT_CANONICAL_PATH_REQUIRED")
        return self
