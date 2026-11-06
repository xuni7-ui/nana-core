"""Independent host lifecycle controller over one existing original Core home.

No init, SQL writes, arbitrary executable/PID/command, systemctl or Subject will.
Only fixed operator-registered releases can launch. Original Runtime still owns
Store lock/lease and safe points. A stop latch survives controller restarts.
"""

import fcntl
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import threading
import time
from pathlib import Path
from ...contracts import DTO, CoreError
from pydantic import Field
from ...host_requirements import unix_socket_path
from ...presence.authority import process_identity
from ..cloud import health
from ..control import request
from .contracts import ApiError, Binding, Realm
from .state import AtomicDocument


def existing_identity(home):
    path = Path(home).absolute() / "subject/self.db"
    if path.resolve() != path or not path.is_file() or path.stat().st_uid != os.getuid():
        raise ApiError("EXISTING_SUBJECT_REQUIRED", 503)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.5) as db:
        rows = db.execute("SELECT identity_id,created_event_id FROM identities LIMIT 2").fetchall()
        if len(rows) != 1:
            raise ApiError("INVALID_IDENTITY", 409)
        lineage = hashlib.sha256(
            json.dumps({"identity_id": rows[0][0], "created_event_id": rows[0][1]}, sort_keys=True).encode()
        ).hexdigest()
        unknown = db.execute("SELECT count(*) FROM cognitive_requests WHERE state IN ('CALLING','UNKNOWN')").fetchone()[
            0
        ]
    return rows[0][0], lineage, unknown


class Release(DTO):
    release_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    source_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    root: str
    python: str
    schema_version: int = Field(default=13, ge=13, le=13)
    plan_contract: str = "PRECISION_V2"
    integrity_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    def validate_local(self, *, qualified=False):
        root, python = Path(self.root), Path(self.python)
        if not root.is_absolute() or root.resolve() != root or not python.is_absolute() or not python.is_file():
            raise ApiError("RELEASE_PATH_DENIED")
        if self.plan_contract != "PRECISION_V2":
            raise ApiError("INCOMPATIBLE_PLAN_CONTRACT", 409)
        if not (root / "src/nana_core/life/__main__.py").is_file():
            raise ApiError("RELEASE_UNAVAILABLE", 503)
        if (root / ".git").exists():
            observed = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            if qualified and subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root
            ):
                raise ApiError("QUALIFIED_RELEASE_DIRTY", 409)
        elif (root / "runtime.json").is_file():
            observed = json.loads((root / "runtime.json").read_text())["source_commit"]
        else:
            raise ApiError("PINNED_RELEASE_MANIFEST_REQUIRED", 503)
        if qualified and (root / "runtime.json").is_file():
            sums = root / "SHA256SUMS"
            if (
                not self.integrity_digest
                or not sums.is_file()
                or hashlib.sha256(sums.read_bytes()).hexdigest() != self.integrity_digest
            ):
                raise ApiError("QUALIFIED_INTEGRITY_MANIFEST_REQUIRED", 409)
            for line in sums.read_text().splitlines():
                value, name = line.split("  ", 1)
                path = root / name
                if (
                    path.resolve() != path
                    or not path.is_relative_to(root)
                    or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != value
                ):
                    raise ApiError("RELEASE_INTEGRITY_MISMATCH", 409)
        if observed != self.source_commit:
            raise ApiError("RELEASE_SOURCE_MISMATCH", 409)


class Supervisor:
    def __init__(
        self,
        home,
        state_root,
        binding: Binding,
        releases,
        *,
        active_release,
        activation=None,
        readiness_seconds=15,
        provider_binding=None,
        provider_live_authorized=True,
    ):
        self.home = Path(home).absolute()
        self.binding = binding
        self.releases = {r.release_id: r for r in releases}
        if len(self.releases) != len(releases) or active_release not in self.releases:
            raise ApiError("RELEASE_REGISTRY_INVALID")
        if not 1 <= readiness_seconds <= 30:
            raise ApiError("READINESS_BOUND_REQUIRED")
        self.readiness_seconds = readiness_seconds
        self.lock = threading.RLock()
        self.child = None
        self.provider_binding = provider_binding
        if type(provider_live_authorized) is not bool:raise ApiError('EXPLICIT_PROVIDER_AUTHORIZATION_REQUIRED')
        self.provider_live_authorized=provider_live_authorized
        self.state = AtomicDocument(
            Path(state_root) / "supervisor.json",
            {
                "schema_version": 1,
                "revision": 0,
                "stop_latch": True,
                "active_release": active_release,
                "owner": None,
                "restart_times": [],
                "last_state": "STOP_LATCHED",
            },
        )
        self.lock_fd = os.open(
            Path(state_root) / "supervisor.owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.lock_fd)
            raise ApiError("SUPERVISOR_ALREADY_OWNED", 409) from None
        try:
            unix_socket_path(self.home / "control.sock")
            self.verify_binding()
            if binding.realm == Realm.PRODUCTION:
                self._production_gate(activation)
            self.releases[self.state.read()["active_release"]].validate_local(
                qualified=self.binding.realm == Realm.PRODUCTION
            )
        except BaseException:
            os.close(self.lock_fd)
            raise

    def _production_gate(self, activation):
        # Supplied by a separate trusted operator workflow, never HTTP input.
        if not activation or set(activation) != {
            "subject_id",
            "lineage_binding",
            "old_writer_fence_digest",
            "approval_digest",
            "genesis_receipt_digest",
            "realm",
        }:
            raise ApiError("PRODUCTION_ACTIVATION_REQUIRED", 403)
        if (
            activation["subject_id"] != self.binding.subject_id
            or activation["lineage_binding"] != self.binding.lineage_binding
            or activation["realm"] != Realm.PRODUCTION.value
        ):
            raise ApiError("INVALID_IDENTITY", 409)
        import re

        if not all(
            re.fullmatch("[a-f0-9]{64}", activation[k])
            for k in ("old_writer_fence_digest", "approval_digest", "genesis_receipt_digest")
        ):
            raise ApiError("PRODUCTION_ACTIVATION_UNVERIFIED", 403)
        # Actual files/receipts and operator scope are qualified by the canonical
        # activation tool; digest strings alone are not sufficient here.
        from .canonical import verify_activation

        verify_activation(self.home, activation)

    def verify_binding(self):
        identity, lineage, unknown = existing_identity(self.home)
        if identity != self.binding.subject_id or lineage != self.binding.lineage_binding:
            raise ApiError("INVALID_IDENTITY", 409)
        return unknown

    def status(self):
        self.verify_binding()
        try:
            raw = health(self.home)
        except (OSError, ValueError, CoreError):
            raise ApiError("CORE_HEALTH_UNVERIFIED", 503) from None
        state = self.state.read()
        lease = raw["runtime"].get("lease") or {}
        owner = state["owner"]
        known = bool(
            owner
            and lease.get("pid") == owner["pid"]
            and lease.get("process_start") == owner["process_start"]
            and lease.get("boot_id") == owner["boot_id"]
        )
        return {
            # A lease can become ACTIVE before ControlServer binds its socket.
            # This supervisor always starts --control: do not report readiness
            # until the peer belongs to that lease, even if headless CLI health
            # legitimately permits a runtime without a control endpoint.
            "process_ready": raw["process_ready"] and raw["control_ready"] is True,
            "runtime_active": raw["runtime"].get("runtime_active", False),
            "owner_epoch": lease.get("epoch", 0),
            "stop_latch": state["stop_latch"],
            "owner_managed": known,
            "supervisor_state": state["last_state"],
            "release_id": state["active_release"],
            "source_commit": self.releases[state["active_release"]].source_commit,
            "storage_status": raw["storage_status"],
            "last_exit_code": state.get("last_exit_code"),
            "disk_pressure": raw["disk_pressure"],
            "unknown_requests": self.verify_binding(),
            "subject_id": self.binding.subject_id,
            "lineage_binding": self.binding.lineage_binding,
        }

    def _record(self, **changes):
        self.state.update(lambda data: data.update(changes))

    def _require_secret_binding_contract(self, release, *, supplied=False, has_fd=False):
        """Reject incompatible inherited credentials without stopping an owner.

        Public resolver metadata may prove an empty binding before a switch.
        The actual export is checked again before launch; no envelope downgrade
        or credential export is used to probe compatibility.
        """
        if self.provider_binding is None or (supplied and not has_fd):
            return
        try:
            resolver = getattr(self.provider_binding, "__self__", None)
            required = getattr(resolver, "binding_contract_version", 1)
            if type(required) is not int or required < 1:
                raise ValueError()
            if not supplied and required > 1 and callable(getattr(resolver, "metadata", None)):
                bindings = resolver.metadata()["bindings"]
                if type(bindings) is not int or not 0 <= bindings <= 12:
                    raise ValueError()
                if bindings == 0:
                    return
            manifest = Path(release.root) / "runtime.json"
            supported = 1
            if manifest.exists() or manifest.is_symlink():
                if manifest.resolve() != manifest:
                    raise ValueError()
                fd = os.open(manifest, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                        raise ValueError()
                    raw = stream.read(65537)
                if len(raw) > 65536:
                    raise ValueError()
                from ...continuity.privacy import _json_object

                metadata = json.loads(raw, object_pairs_hook=_json_object)
                supported = metadata.get("secret_binding_contract", 1)
            elif self.binding.realm == Realm.DEVELOPMENT:
                from .. import secret_binding

                decoder = Path(release.root) / "src/nana_core/life/secret_binding.py"
                if (decoder.is_file() and decoder.resolve() == decoder
                        and decoder == Path(secret_binding.__file__).resolve()):
                    supported = secret_binding.SUPPORTED_FD_CONTRACT_VERSION
            if type(supported) is not int or supported < 1 or required > supported:
                raise ValueError()
        except Exception:
            raise ApiError("INCOMPATIBLE_SECRET_BINDING_CONTRACT", 409) from None

    def _require_memory_ingress_contract(self, release):
        """Reject an old decoder BEFORE stopping a healthy owner; no DB rollback."""
        from ..config import load_config
        path = self.home / 'subject/self.db'
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
            legacy = db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='recorded.legacy.archive' LIMIT 1").fetchone()
            direct_reply = db.execute("SELECT 1 FROM events WHERE kind='open.direct_reply_assessed' LIMIT 1").fetchone()
            bilibili_work=db.execute("SELECT 1 FROM jobs WHERE work_kind='BILIBILI_LIFE' LIMIT 1").fetchone()
        required = {}
        if 'PERSONAL' in self.binding.privacy:
            required['private_context_contract'] = 'INCOMPATIBLE_PRIVATE_CONTEXT_CONTRACT'
        if legacy is not None:
            required['archive_ingress_contract'] = 'INCOMPATIBLE_ARCHIVE_MEMORY_CONTRACT'
        config = load_config(self.home)
        if config.bilibili_life is not None or bilibili_work is not None:
            required['bilibili_life_contract'] = 'INCOMPATIBLE_BILIBILI_LIFE_CONTRACT'
        if (config.qq_channels or config.bilibili_channels or direct_reply is not None
                or self.provider_binding is not None and not self.provider_live_authorized):
            required['platform_runtime_contract'] = 'INCOMPATIBLE_PLATFORM_RUNTIME_CONTRACT'
        if not required:
            return
        try:
            manifest = Path(release.root) / 'runtime.json'
            if manifest.is_file():
                from ...continuity.privacy import _json_object
                if manifest.resolve() != manifest or manifest.stat().st_size > 65536:
                    raise ValueError()
                metadata = json.loads(manifest.read_bytes(), object_pairs_hook=_json_object)
            elif self.binding.realm == Realm.DEVELOPMENT and Path(release.root).resolve() == Path(__file__).resolve().parents[4]:
                # Only this exact working-tree decoder, never another directory
                # or an imported module from a newer interpreter on sys.path.
                metadata = {'archive_ingress_contract': 1, 'bilibili_life_contract': 1, 'platform_runtime_contract': 1, 'private_context_contract': 1}
            else:
                metadata = {}
        except (OSError, ValueError, TypeError):
            raise ApiError('INCOMPATIBLE_HOST_DATA_CONTRACT', 409) from None
        for key, code in required.items():
            value = metadata.get(key, 0)
            if type(value) is not int or value < 1:
                raise ApiError(code, 409)

    def start(self, *, automatic=False):
        with self.lock:
            unknown = self.verify_binding()
            current = self.status()
            if current["runtime_active"]:
                raise ApiError("CORE_ALREADY_OWNED", 409)
            state = self.state.read()
            if state["owner"]:
                old = state["owner"]
                try:
                    alive = process_identity(old["pid"]) == (old["process_start"], old["boot_id"])
                except (OSError, ValueError):
                    alive = False
                if alive:
                    raise ApiError("CORE_OWNER_PENDING_NO_RETRY", 409)
            if automatic and (state["stop_latch"] or unknown):
                raise ApiError("AUTORESTART_INHIBITED", 409)
            self._prestart()
            release = self.releases[state["active_release"]]
            release.validate_local(qualified=self.binding.realm == Realm.PRODUCTION)
            self._require_secret_binding_contract(release)
            self._require_memory_ingress_contract(release)
            # Core already writes its original bounded sanitized runtime.log.
            # Do not retain an unbounded stdout/stderr stream or error payloads.
            # Original entry point with explicit finite residency, not a second
            # daemon/loop. Its current single-writer lock/epoch fence remains final.
            argv = [
                release.python,
                "-B",
                "-m",
                "nana_core.life",
                "run",
                "--home",
                str(self.home),
                "--seconds",
                str(7 * 86400),
                "--headless",
                "--control",
            ]
            env = {
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "TZ": "UTC",
                "PYTHONPATH": str(Path(release.root) / "src"),
            }
            fd = None
            try:
                if self.provider_binding is not None:
                    # Explicit host resolver only. FD number is not a credential;
                    # plaintext travels solely over an inherited private pipe.
                    supplied = self.provider_binding()
                    if supplied is not None:
                        fd, reference = supplied
                        from ..config import load_config
                        config=load_config(self.home)
                        if config.qq_channels or config.bilibili_channels or not self.provider_live_authorized:
                            argv += ['--platform-bindings-authorized']
                        if self.provider_live_authorized:
                            argv += ["--live-provider-authorized"]
                        argv += ["--secret-bundle-fd", str(fd)] if reference is None else ["--secret-fd", str(fd), "--secret-ref", reference]
                self._require_secret_binding_contract(release, supplied=True, has_fd=fd is not None)
                self._record(stop_latch=False, last_state="START_REQUESTED")
                self.child = subprocess.Popen(
                    argv,
                    cwd=release.root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    pass_fds=() if fd is None else (fd,),
                )
            finally:
                if fd is not None:
                    os.close(fd)
            start, boot = process_identity(self.child.pid)
            self._record(owner={"pid": self.child.pid, "process_start": start, "boot_id": boot}, last_state="STARTING")
            deadline = time.monotonic() + self.readiness_seconds
            while time.monotonic() < deadline:
                if self.child.poll() is not None:
                    self._record(last_state="START_EXITED", stop_latch=True, last_exit_code=self.child.returncode)
                    raise ApiError("CORE_START_EXITED", 503)
                if self.status()["process_ready"]:
                    self._record(last_state="RUNNING")
                    return self.status()
                time.sleep(0.08)
            self._record(last_state="START_TIMEOUT_UNKNOWN", stop_latch=True)
            # Do not launch another process. The owned attempt may still be
            # starting; subsequent status reconciles it without replay.
            raise ApiError("CORE_START_TIMEOUT_UNKNOWN", 504)

    def _prestart(self):
        """Original privacy closure and schema in a query-only transaction."""
        from ..inspector import _ReadView

        path = self.home / "subject/self.db"
        try:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                _ReadView(db, path, self.binding.scope, self.binding.privacy)
                if (
                    db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
                    or db.execute("PRAGMA foreign_key_check").fetchone()
                ):
                    raise ApiError("CORE_INTEGRITY_UNVERIFIED", 503)
                if db.execute(
                    "SELECT 1 FROM core_meta WHERE key IN ('portable.retired','recovery_quarantine') AND value_json!='false'"
                ).fetchone():
                    raise ApiError("CORE_RETIRED_OR_QUARANTINED", 409)
        except CoreError:
            raise ApiError("CORE_PRIVACY_RECONCILIATION_REQUIRED", 503) from None

    def stop(self):
        with self.lock:
            self._record(stop_latch=True, last_state="STOP_REQUESTED")
            current = self.status()
            if not current["runtime_active"]:
                self._wait_owned_exit()
                self._record(last_state="STOP_LATCHED")
                return self.status()
            if not current["owner_managed"]:
                raise ApiError("FOREIGN_OWNER_REQUIRES_OPERATOR", 409)
            try:
                result = request(self.home, {"operation": "control", "command": "stop"}, timeout=3)
                if result.get("ok") is not True:
                    raise ApiError("CORE_STOP_UNVERIFIED", 503)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if self.child is not None:
                        self.child.poll()
                    current = self.status()
                    if not current["runtime_active"]:
                        self._wait_owned_exit()
                        self._record(last_state="STOP_LATCHED")
                        return self.status()
                    time.sleep(0.08)
            except (OSError, CoreError):
                raise ApiError("UNKNOWN_NEEDS_RECONCILIATION", 503) from None
            raise ApiError("UNKNOWN_NEEDS_RECONCILIATION", 504)

    def _wait_owned_exit(self):
        # A released lease can precede final process cleanup. Do not report
        # VERIFIED stop/start until the actual known child is reaped or gone.
        if self.child is not None:
            try:
                self.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise ApiError("CORE_STOP_CLEANUP_UNKNOWN", 504) from None
            return
        owner = self.state.read()["owner"]
        if owner:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    if process_identity(owner["pid"]) != (owner["process_start"], owner["boot_id"]):
                        return
                except (OSError, ValueError):
                    return
                time.sleep(0.08)
            raise ApiError("CORE_STOP_CLEANUP_UNKNOWN", 504)

    def restart(self):
        with self.lock:
            release = self.releases[self.state.read()["active_release"]]
            self._require_secret_binding_contract(release)
            self._require_memory_ingress_contract(release)
            self.stop()
            return self.start()

    def change_release(self, release_id, *, rollback=False):
        """Offline stop/check/replace/start only, never active-plan hot downgrade.

        The trusted host registry must prequalify both releases with the same
        schema and planner contract. A failed start stays stopped/UNKNOWN; there
        is no automatic binary rollback or replay of actions.
        """
        with self.lock:
            if release_id not in self.releases:
                raise ApiError("QUALIFIED_RELEASE_REQUIRED", 409)
            previous = self.releases[self.state.read()["active_release"]]
            target = self.releases[release_id]
            target.validate_local(qualified=self.binding.realm == Realm.PRODUCTION)
            if (previous.schema_version, previous.plan_contract) != (target.schema_version, target.plan_contract):
                raise ApiError("INCOMPATIBLE_RELEASE_STOP_REQUIRED", 409)
            self._require_secret_binding_contract(target)
            self._require_memory_ingress_contract(target)
            if self.verify_binding():
                raise ApiError("PENDING_UNKNOWN_REQUIRES_REVIEW", 409)
            self.stop()
            self._prestart()
            self._record(
                active_release=release_id,
                stop_latch=True,
                last_state="ROLLBACK_SELECTED" if rollback else "UPGRADE_SELECTED",
            )
            return self.start()

    def monitor_once(self):
        """Infrastructure cadence only; cannot choose goals or replay effects."""
        with self.lock:
            state = self.state.read()
            if self.child is not None and self.child.poll() is None:
                return self.status()
            if self.child is None:
                owner = state["owner"]
                if not owner:
                    return self.status()
                try:
                    if process_identity(owner["pid"]) == (owner["process_start"], owner["boot_id"]):
                        return self.status()
                except (OSError, ValueError):
                    pass
            if state["stop_latch"] or (self.child is not None and self.child.returncode == 0):
                return self.status()
            now = time.time()
            attempts = [x for x in state["restart_times"] if now - x < 3600]
            if len(attempts) >= 3 or self.verify_binding():
                self._record(last_state="RECOVERY_REVIEW_REQUIRED", stop_latch=True)
                return self.status()
            self._record(restart_times=attempts + [now], last_state="RECOVERING")
            return self.start(automatic=True)

    def close(self):
        # Closing gateway/Supervisor never silently stops the independently living
        # Core or resets identity. A later controller revalidates the owner receipt.
        os.close(self.lock_fd)
