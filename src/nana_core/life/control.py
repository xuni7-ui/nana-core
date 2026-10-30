"""Bounded private local IPC handled at the original Runtime's safe point.

No worker/second decision loop, TCP listener, credentials, arbitrary command or
Grant installation API. A local trusted application is the controller, never a
model. QQ/Bili submissions remain explicitly development shadow observations.
"""

import json
import os
import re
import socket
import stat
import struct
import time
import shutil
from pathlib import Path
from ..contracts import CoreError
from ..host_requirements import unix_socket_path
from ..continuity.privacy import _json_object
from .surfaces import SurfaceObservation

LIMIT = 16384


def dispatch(app, request):
    if type(request) is not dict:
        raise CoreError("CLOUD_TYPED_REQUEST_REQUIRED")
    op = request.get("operation")
    legacy = getattr(app, 'legacy_imports', None)
    if legacy is not None and op != 'control':
        legacy.reconcile()
    if op=='qq-message' and set(request)=={'operation','channel_id','message_id'}:
        if (type(request['channel_id']) is not str or not re.fullmatch(r'[a-z][a-z0-9._-]{0,63}',request['channel_id'])
                or type(request['message_id']) is not str or not re.fullmatch(r'[0-9]{1,20}',request['message_id'])):
            raise CoreError('QQ_TYPED_MESSAGE_REFERENCE_REQUIRED')
        if shutil.disk_usage(app.home).free < app.config.min_free_disk_mb * 1024 * 1024:
            raise CoreError('CLOUD_DISK_GUARD')
        return app.platforms.qq(request['channel_id'],request['message_id'])
    if op=='bilibili-message' and set(request)=={'operation','channel_id','message_id'}:
        if (type(request['channel_id']) is not str or not re.fullmatch(r'[a-z][a-z0-9._-]{0,63}',request['channel_id'])
                or type(request['message_id']) is not str or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}',request['message_id'])):
            raise CoreError('BILIBILI_TYPED_MESSAGE_REFERENCE_REQUIRED')
        if shutil.disk_usage(app.home).free < app.config.min_free_disk_mb * 1024 * 1024:raise CoreError('CLOUD_DISK_GUARD')
        return app.platforms.bilibili(request['channel_id'],request['message_id'])
    projection_keys = ({"operation", "privacy"}, {"operation", "privacy", "scope", "entity_id"})
    if op in {"bilibili-history", "shared-candidates", "conversation-history", "notification-inbox"} and set(request) in projection_keys:
        if type(request["privacy"]) is not list or any(p not in {"PUBLIC", "PROJECT"} for p in request["privacy"]):
            raise CoreError("PRIVACY_DENIED")
        coordinates = {k: request[k] for k in ("scope", "entity_id") if k in request}
        if any(type(v) is not str or not 1 <= len(v) <= 128 for v in coordinates.values()):
            raise CoreError("INVALID_PROJECTION_BINDING")
        if op == "bilibili-history":
            from .bilibili import BilibiliSourceAdapter
            return BilibiliSourceAdapter(app).history(privacy=request["privacy"], **coordinates)
        if op == "shared-candidates":
            return app.shared.inbox(privacy=request["privacy"], **coordinates)
        if op == 'notification-inbox':
            return app.shared.notification_inbox(privacy=request['privacy'], **coordinates)
        from .conversation import history
        return history(app, privacy=request["privacy"], **coordinates)
    if op == "provider-readiness" and set(request) == {"operation", "privacy"}:
        if request["privacy"] not in {"PUBLIC", "PROJECT"}:
            raise CoreError("PRIVACY_DENIED")
        return app.provider_readiness(privacy=request["privacy"])
    mutating = op in {"surface", "backup", "self-profile", "language-feedback", "review-expression-learning", "bilibili-ingest", "bilibili-interpret", "legacy-import-batch", "legacy-withdraw"} or (
        op == "control" and request.get("command") == "resume"
    )
    if mutating and shutil.disk_usage(app.home).free < app.config.min_free_disk_mb * 1024 * 1024:
        raise CoreError("CLOUD_DISK_GUARD")
    if op=='platform-status' and set(request)=={'operation'}:return app.platforms.view()
    if op=='platform-refresh' and set(request)=={'operation'}:return app.platforms.refresh()
    if op in {"legacy-import-batch", "legacy-withdraw"}:
        from ..migration.archive_ingress import ArchiveImportService, private_document
        common = {'operation', 'archive', 'approval_file'}
        expected = common | ({'plan_file', 'batch_id'} if op == 'legacy-import-batch' else {'source_id'})
        if set(request) != expected or any(type(v) is not str or not 1 <= len(v) <= 4096 for v in request.values()):
            raise CoreError('LEGACY_IMPORT_TYPED_REQUEST_REQUIRED')
        service = ArchiveImportService(app)
        if op == 'legacy-withdraw':
            return service.withdraw(request['archive'], request['approval_file'], request['source_id'])
        return service.import_batch(request['archive'], private_document(request['plan_file']),
            request['approval_file'], request['batch_id'])
    if op == "bilibili-ingest" and set(request) == {"operation", "reading"}:
        from .bilibili import BilibiliSourceAdapter, PublicReading
        value = request["reading"]
        if type(value) is not dict or set(value) != {"reference", "kind", "observed_at_us", "payload", "origin"}:
            raise CoreError("BILIBILI_TYPED_RECEIPT_REQUIRED")
        if type(value["observed_at_us"]) is not int or value["observed_at_us"] < 0:
            raise CoreError("BILIBILI_SOURCE_TIME_REQUIRED")
        return {"source_memory_id": BilibiliSourceAdapter(app).ingest(PublicReading(**value)), "social_delivery": False}
    if op == "bilibili-interpret" and set(request) == {"operation", "source_memory_id"}:
        from .bilibili import BilibiliSourceAdapter
        return BilibiliSourceAdapter(app).interpret(request["source_memory_id"])
    if op == "surface" and set(request) == {"operation", "observation"}:
        return app.surfaces.receive(SurfaceObservation.model_validate_json(json.dumps(request["observation"])))
    if op == "view" and set(request) == {"operation", "view"}:
        if request["view"] == "bilibili-history":
            from .bilibili import BilibiliSourceAdapter
            return BilibiliSourceAdapter(app).history()
        if request["view"] == "provider-settings":
            from .readiness import provider_settings
            return provider_settings(app)
        if request["view"] == "provider-readiness":
            return app.provider_readiness()
        if request["view"] == "life":
            return app.board()
        if request["view"] == "status":
            return app.status()
        if request["view"] == "storage":
            from .durability import profile

            return profile(app.runtime.store)
        if request["view"] == "self":
            from ..continuity.person_self import project

            return project(
                app.runtime.store,
                entity_id=app.runtime.config.entity_id,
                scope=app.runtime.config.scopes[0],
                privacy=("PUBLIC", "PROJECT"),
                topic="daily",
            )
    if op == "self-profile" and set(request) == {"operation", "name", "aliases", "expected_revision", "reason"}:
        from ..continuity.identity import IdentityService

        if type(request["aliases"]) is not list:
            raise CoreError("INVALID_IDENTITY_PROFILE")
        service = IdentityService(app.runtime.store, app.runtime.authority)
        return service.revise_profile(
            expected_revision=request["expected_revision"],
            name=request["name"],
            aliases=tuple(request["aliases"]),
            reason=request["reason"],
            authority=app.runtime.authority,
        ).model_dump(mode="json")
    if op == "language-feedback" and set(request) == {"operation", "sample", "exchange_record_id"}:
        from ..continuity.lived_language import LanguageService, LanguageSample
        from ..continuity.learning import ExperienceService

        sample = LanguageSample.model_validate_json(json.dumps(request["sample"]))
        if sample.provenance != "USER_PROVIDED_REVIEW":
            raise CoreError("HUMAN_REVIEW_PROVENANCE_REQUIRED")
        service = LanguageService(app.runtime.store, app.runtime.authority)
        head = service.records.read(request["exchange_record_id"])
        rid = service.record(
            sample,
            scope=app.runtime.config.scopes[0],
            entity_id=app.runtime.config.entity_id,
            privacy=head["privacy_class"],
            authority=app.runtime.authority,
            exchange_record_id=request["exchange_record_id"],
        )
        eid = service.experience(rid, app.runtime.authority)
        lesson = None
        try:
            lesson = ExperienceService(app.runtime.store, app.runtime.authority).derive_lesson(eid)
        except CoreError as exc:
            if exc.code != "NO_SUPPORTED_LESSON":
                raise
        return {
            "sample_record_id": rid,
            "experience_id": eid,
            "candidate_lesson_id": lesson,
            "human_naturalness_qualified": False,
            "personality_overwritten": False,
        }
    if op == "review-expression-learning" and set(request) == {"operation", "lesson_id"}:
        from ..continuity.learning import ExperienceService

        service = ExperienceService(app.runtime.store, app.runtime.authority)
        row = app.runtime.store.one("lessons", request["lesson_id"])
        if not row or row["task_class"] != "interaction.expression":
            raise CoreError("EXPRESSION_LESSON_REQUIRED")
        checks = service.test_lesson(request["lesson_id"])
        if all(checks.values()):
            service.activate(request["lesson_id"], app.runtime.authority)
        return {
            "checks": checks,
            "state": app.runtime.store.one("lessons", request["lesson_id"])["state"],
            "human_naturalness_qualified": False,
        }
    if op == "continuity" and set(request) == {"operation", "binding_id", "tier"}:
        return app.surfaces.view(request["binding_id"], tier=request["tier"]).model_dump(mode="json")
    if op == "control" and set(request) == {"operation", "command"}:
        name = request["command"]
        if name in {"pause", "resume"}:
            return app.pause(name == "pause")
        if name in {"busy", "available"}:
            return app.presence(name.upper())
        if name == "revoke":
            return app.revoke()
        if name == "stop":
            app.runtime.request_stop()
            return {"state": "STOP_REQUESTED"}
    if op == "forget" and set(request) == {"operation", "memory_id"}:
        return app.forget(request["memory_id"])
    if op == "surface-enabled" and set(request) == {"operation", "binding_id", "enabled", "expected_revision"}:
        from .config import update_config
        from .surfaces import SurfaceSession

        if type(request["enabled"]) is not bool or type(request["expected_revision"]) is not int:
            raise CoreError("CLOUD_SETTING_TYPE_INVALID")
        if request["binding_id"] not in {b.binding_id for b in app.config.surface_bindings}:
            raise CoreError("SURFACE_DISABLED_OR_UNBOUND")
        bindings = tuple(
            b.model_copy(update={"enabled": request["enabled"]}) if b.binding_id == request["binding_id"] else b
            for b in app.config.surface_bindings
        )
        app.config = update_config(
            app.home,
            app.config.model_copy(update={"surface_bindings": bindings, "revision": request["expected_revision"] + 1}),
            expected_revision=request["expected_revision"],
        )
        app.surfaces = SurfaceSession(app, app.config.surface_bindings)
        return {"host_config_revision": app.config.revision, "subject_state_changed": False}
    if op == "backup" and set(request) == {"operation", "name"}:
        if type(request["name"]) is not str or not re.fullmatch("[a-z][a-z0-9_-]{0,63}", request["name"]):
            raise CoreError("CLOUD_BACKUP_NAME_INVALID")
        from .cloud import backup

        return backup(app.runtime.store, app.home / "backups" / (request["name"] + ".db"))
    if op == "review-share" and set(request) == {"operation", "cycle_id", "binding_id"}:
        return app.shared.review(request["cycle_id"], request["binding_id"])
    raise CoreError("CLOUD_OPERATION_DENIED")


class ControlServer:
    def __init__(self, app):
        try:
            path = unix_socket_path(app.home / "control.sock")
        except ValueError as exc:
            raise CoreError(str(exc)) from None
        self.app = app
        self.path = path
        if self.path.exists() or self.path.is_symlink():
            s = self.path.lstat()
            if not stat.S_ISSOCK(s.st_mode) or s.st_uid != os.getuid():
                raise CoreError("CLOUD_CONTROL_PATH_DENIED")
            # Runtime lease and exclusive Store lock have already been acquired;
            # only now is an old owned socket known to belong to a stopped owner.
            self.path.unlink()
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(str(self.path))
        self.path.chmod(0o600)
        self.socket.listen(4)
        self.socket.setblocking(False)
        self.inode = self.path.lstat().st_ino

    def poll(self):
        try:
            conn, _ = self.socket.accept()
        except BlockingIOError:
            return False
        with conn:
            conn.settimeout(0.2)
            try:
                _, uid, _ = struct.unpack("3i", conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid != os.getuid():
                    raise CoreError("CLOUD_CONTROL_OWNER_REQUIRED")
                raw = b""
                deadline = time.monotonic() + 0.5
                while b"\n" not in raw and len(raw) <= LIMIT:
                    if time.monotonic() >= deadline:
                        raise CoreError("CLOUD_REQUEST_TIMEOUT")
                    part = conn.recv(4096)
                    if not part:
                        break
                    raw += part
                if len(raw) > LIMIT or not raw.endswith(b"\n"):
                    raise CoreError("CLOUD_REQUEST_BOUND")
                req = json.loads(raw, object_pairs_hook=_json_object)
                result = dispatch(self.app, req)
                response = {"ok": True, "result": result}
            except (CoreError, ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
                response = {"ok": False, "code": exc.code if isinstance(exc, CoreError) else "CLOUD_REQUEST_REJECTED"}
            try:
                conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode())
            except OSError:
                pass  # lost response never authorizes replay
        return True

    def close(self):
        self.socket.close()
        try:
            if self.path.lstat().st_ino == self.inode:
                self.path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


def request(home, data, timeout=None):
    path = Path(home).absolute() / "control.sock"
    root = path.parent
    if root != root.resolve() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise CoreError("CLOUD_PRIVATE_HOME_REQUIRED")
    row = path.lstat()
    if not stat.S_ISSOCK(row.st_mode) or row.st_uid != os.getuid() or row.st_mode & 0o077:
        raise CoreError("CLOUD_CONTROL_PATH_DENIED")
    raw = (json.dumps(data) + "\n").encode()
    if len(raw) > LIMIT:
        raise CoreError("CLOUD_REQUEST_BOUND")
    if timeout is None:
        from .config import load_config

        timeout = max(5, 2 * load_config(root).provider_timeout_ms / 1000 + 2)
    from ..presence.cli import status

    current = status(root / "subject/self.db")
    if not current.get("runtime_active"):
        raise CoreError("CLOUD_RUNTIME_NOT_CURRENT")
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(str(path))
        except OSError:
            raise CoreError("CLOUD_CONTROL_PRE_DISPATCH_UNAVAILABLE") from None
        pid, uid, _ = struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.getuid() or pid != current["lease"]["pid"] or path.lstat().st_ino != row.st_ino:
            raise CoreError("CLOUD_CONTROL_OWNER_REQUIRED")
        try:
            sock.sendall(raw)
            reply = b""
            while b"\n" not in reply and len(reply) <= 262144:
                part = sock.recv(4096)
                if not part:
                    break
                reply += part
        except OSError:
            raise CoreError("CLOUD_COMPLETION_UNKNOWN_NO_RETRY") from None
    if len(reply) > 262144:
        raise CoreError("CLOUD_RESPONSE_BOUND")
    try:
        return json.loads(reply, object_pairs_hook=_json_object)
    except (ValueError, RecursionError):
        raise CoreError("CLOUD_RESPONSE_UNKNOWN_NO_RETRY") from None
