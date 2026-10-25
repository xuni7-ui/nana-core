"""Trusted application operations over the existing Store and B8 transfer.

Backup is a quarantined review copy, never a runnable clone. Migration retires
the source before publishing; activation revokes every old grant. Host settings
are explicitly supplied on the destination, never copied from the package.
"""

import json
import os
import shutil
import sqlite3
import socket
import struct
from pathlib import Path
from uuid import uuid4

from ..contracts import CoreError
from ..continuity import ContinuityStore
from ..continuity.portable import SubjectPackageService, PortableTransferAuthority
from ..continuity.provider_config import ProviderConfigService, ProviderConfigurationAuthority
from ..presence.cli import status
from .config import load_config, write_config, home_path


def health(home):
    home = Path(home).absolute()
    config = load_config(home)
    runtime = status(home / "subject/self.db")
    from .durability import read_window

    try:
        monitor = read_window(home / "storage-monitor.json")
        storage_status = monitor.status if monitor else "NOT_OBSERVED"
    except CoreError:
        storage_status = "INVALID_FAIL_CLOSED"
    disk = shutil.disk_usage(home)
    control_ready = None
    control = home / "control.sock"
    if control.exists():
        control_ready = False
        try:
            with socket.socket(socket.AF_UNIX) as probe:
                probe.settimeout(0.2)
                probe.connect(str(control))
                pid, uid, _ = struct.unpack("3i", probe.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                control_ready = uid == os.getuid() and pid == runtime.get("lease", {}).get("pid")
        except OSError:
            pass
    return {
        "derived": True,
        "runtime": runtime,
        "control_ready": control_ready,
        "storage_status": storage_status,
        "process_ready": runtime.get("runtime_active", False)
        and storage_status in {"OBSERVING", "NOT_OBSERVED"}
        and control_ready is not False
        and disk.free >= config.min_free_disk_mb * 1024 * 1024,
        "beta_ready": False,
        "real_provider_qualified": "NOT_QUALIFIED",
        "human_review": "NOT_RUN",
        "disk_free_bytes": disk.free,
        "disk_pressure": "LOW_SPACE" if disk.free < config.min_free_disk_mb * 1024 * 1024 else "AVAILABLE",
        "state_directory": str(home / "subject"),
        "timezone": config.timezone,
        "external_social_send": False,
        "execution_authority": False,
    }


def backup(store, destination):
    """SQLite consistent safe-point snapshot incl. privacy sidecar; no authority."""
    destination = Path(destination).absolute()
    store.backup(destination)
    with sqlite3.connect("file:" + str(destination) + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
            raise CoreError("CLOUD_BACKUP_INTEGRITY")
        quarantine = db.execute("SELECT value_json FROM core_meta WHERE key='recovery_quarantine'").fetchone()
        if quarantine is None or quarantine[0] != "true":
            raise CoreError("CLOUD_BACKUP_NOT_QUARANTINED")
    return {
        "backup": str(destination),
        "identity_id": store.identity["identity_id"],
        "state": "QUARANTINED_REVIEW_COPY",
        "bytes": destination.stat().st_size,
        "runnable": False,
    }


def transfer(home, package, *, destination_id, source_commit, pending_effects=False):
    load_config(home)  # exact existing home, never invent config on a typo
    authority = PortableTransferAuthority()
    with ContinuityStore(Path(home) / "subject/self.db", schema_target=13) as store:
        result = SubjectPackageService(store, authority).export(
            package,
            destination_id=destination_id,
            source_commit=source_commit,
            authority=authority,
            pending_effects=pending_effects,
        )
    return {
        "sha256": result["sha256"],
        "bytes": result["bytes"],
        "manifest": result["manifest"].model_dump(mode="json"),
        "source_retired": True,
    }


def receive(package, home, *, sha256, destination_id, config):
    """Caller provides explicit host-local configuration and rebinds no grants."""
    home = Path(home).absolute()
    if home.exists() or home.is_symlink():
        raise CoreError("CLOUD_FRESH_HOME_REQUIRED")
    home = home_path(home)
    root = home / "subject"
    authority = PortableTransferAuthority(destination_id=destination_id, destination_root=root)
    try:
        path = SubjectPackageService.import_quarantined(
            package, root, expected_sha256=sha256, destination_id=destination_id, authority=authority
        )
        # Config creation is host responsibility. Failure leaves quarantine, not
        # a silently running partly configured Subject.
        write_config(home, config)
        provider = ProviderConfigurationAuthority()
        ProviderConfigService(home / "providers.json", provider).initialize(provider)
        with ContinuityStore(path, schema_target=13) as store:
            received = json.loads(store.one("core_meta", "portable.received")["value_json"])
            identity = SubjectPackageService(store, authority).activate(
                transfer_id=received["transfer_id"], destination_id=destination_id, authority=authority
            )
        return {
            "identity_id": identity,
            "state": "ACTIVATED_NO_EXECUTION_GRANTS",
            "provider_config_transferred": False,
            "host_settings": "EXPLICIT_DESTINATION_ONLY",
        }
    except BaseException:
        # Preserve review evidence. Do not delete an import to hide a failure.
        raise


class RotatingJSONLog:
    """Bounded sanitized operations log, never conversation/model payloads."""

    def __init__(self, home, max_bytes=262144):
        self.path = Path(home) / "runtime.log"
        self.max_bytes = max_bytes

    def write(self, *, state, clock_us, queue_depth):
        data = json.dumps({"state": state, "clock_us": clock_us, "queue_depth": queue_depth}) + "\n"
        if self.path.is_symlink():
            raise CoreError("CLOUD_LOG_SYMLINK_DENIED")
        if self.path.exists() and self.path.stat().st_size + len(data) > self.max_bytes:
            os.replace(self.path, self.path.with_suffix(".log.1"))
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(data)
