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
from collections import deque
from pathlib import Path
from ..contracts import CoreError
from ..host_requirements import unix_socket_path
from ..continuity.privacy import _json_object
from .surfaces import SurfaceObservation

LIMIT = 16384
MAX_PENDING_INPUTS = 4


def dispatch(app, request, *, observed_at_us=None, respond_to=()):
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
        if type(request["privacy"]) is not list or any(p not in {"PUBLIC", "PROJECT", "PERSONAL"} for p in request["privacy"]):
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
        if request["privacy"] not in {"PUBLIC", "PROJECT", "PERSONAL"}:
            raise CoreError("PRIVACY_DENIED")
        return app.provider_readiness(privacy=request["privacy"])
    mutating = op in {"surface", "surface-sequence", "backup", "self-profile", "language-feedback", "review-expression-learning", "bilibili-ingest", "bilibili-interpret", "legacy-import-batch", "legacy-withdraw", "memory-note"} or (
        op == "control" and request.get("command") == "resume"
    )
    if mutating and shutil.disk_usage(app.home).free < app.config.min_free_disk_mb * 1024 * 1024:
        raise CoreError("CLOUD_DISK_GUARD")
    if op=='platform-status' and set(request)=={'operation'}:return app.platforms.view()
    if op=='memory-note' and set(request)=={'operation','text','privacy','request_id','target_id','surface_binding_id','request_digest'}:
        from .memory_notes import save
        return save(app,text=request['text'],privacy=request['privacy'],request_id=request['request_id'],target_id=request['target_id'],surface_binding_id=request['surface_binding_id'],request_digest=request['request_digest'])
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
        return app.surfaces.receive(SurfaceObservation.model_validate_json(json.dumps(request["observation"])), observed_at_us=observed_at_us, _respond_to=respond_to)
    if op=='surface-sequence' and set(request)=={'operation','observations'}:
        if type(request['observations']) is not list or not 2<=len(request['observations'])<=4:raise CoreError('SURFACE_SEQUENCE_BOUND')
        return app.surfaces.receive_sequence(tuple(SurfaceObservation.model_validate_json(json.dumps(o)) for o in request['observations']))
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
    if op == "language-feedback" and set(request) in ({"operation", "sample", "exchange_record_id"}, {"operation", "sample", "exchange_record_id", "request_digest"}, {"operation", "sample", "exchange_record_id", "response_sha256"}, {"operation", "sample", "exchange_record_id", "request_digest", "response_sha256"}):
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
            request_digest=request.get("request_digest"),
            response_sha256=request.get("response_sha256"),
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
    def __init__(self, app, *, coalesce_continuations=False):
        # Explicit isolated prototype until BFF/client individual deferred-receipt
        # handling is integrated. Ordinary runtime behavior remains unchanged.
        if type(coalesce_continuations) is not bool:raise CoreError('CLOUD_CONTINUATION_OPTION_INVALID')
        self.coalesce_continuations=coalesce_continuations
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
        self.pending_inputs = deque()  # private volatile bodies, never a second Store
        self.previous_progress = getattr(app.runtime, "control_progress", None)
        self.progress_callback = lambda: self.poll(urgent_only=True)
        app.runtime.control_progress = self.progress_callback
        self.active_observation=None
        self.unanswered=()
        self.unanswered_context=None
        self.unanswered_target=None
        self.continuation_target=None
        self.previous_continuation=getattr(app,'dialogue_continuation_pending',None)
        self.continuation_callback=self._continuation_pending
        if coalesce_continuations:app.dialogue_continuation_pending=self.continuation_callback

    @staticmethod
    def _conversation_context(observation):
        return (observation.binding_id,observation.thread_id,observation.topic,
                observation.privacy_class,observation.origin)

    def _continuation_pending(self,surface,topic,privacy,retained):
        """Admit bytes already at the socket before committing an unsent draft.

        The model may finish between transport progress ticks. Use the existing
        urgent lane once at this safe point; messages only queue, never reenter C.
        Only the original restrictive controls may execute, as during model wait.
        """
        if retained or surface is None or self.active_observation is None:
            return False
        for _ in range(MAX_PENDING_INPUTS+1):
            if not self.poll(urgent_only=True):break
        if not self.pending_inputs:return False
        active=self.active_observation
        if (surface.session_id!=active.binding_id or surface.conversation_id!=active.thread_id
                or topic!=active.topic or privacy!=active.privacy_class):return False
        conn,request,deadline,_=self.pending_inputs[0]
        if time.monotonic()>=deadline or self.app.runtime.stop_requested:return False
        import select
        if select.select([conn],[],[],0)[0]:return False  # disconnected/extra bytes: do not defer for it
        try:
            following,binding=self.app.surfaces.validate_observation(
                SurfaceObservation.model_validate_json(json.dumps(request['observation'])))
        except (CoreError,ValueError):return False
        # The new input still enters original C. A literal rest/stop can then
        # withhold the previous unsent draft; it must not force that draft out.
        compatible=(binding.mode=='DEVELOPMENT_SHADOW_NO_SEND'
            and self._conversation_context(active)==self._conversation_context(following)
            and not active.retain_shared_life and not following.retain_shared_life
            and active.approved_summary is None and following.approved_summary is None)
        if compatible:
            from ..storage import digest
            from ..continuity.surfaces import source_key
            candidate=surface.model_copy(update={'source_event_key':digest([following.binding_id,following.event_id])})
            if self.app.runtime.store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',
                    (source_key(candidate),)).fetchone():return False
            self.continuation_target=(following.binding_id,following.event_id)
        return compatible

    def poll(self, *, urgent_only=False):
        queued = False
        req = None
        deadline = None
        observed_at_us = None
        if not urgent_only and self.pending_inputs:
            conn, req, deadline, observed_at_us = self.pending_inputs.popleft()
        else:
            try:
                conn, _ = self.socket.accept()
            except BlockingIOError:
                return False
        try:
            conn.settimeout(0.2)
            try:
                if req is None:
                    _, uid, _ = struct.unpack("3i", conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != os.getuid():
                        raise CoreError("CLOUD_CONTROL_OWNER_REQUIRED")
                    raw = b""
                    read_deadline = time.monotonic() + 0.5
                    while b"\n" not in raw and len(raw) <= LIMIT:
                        if time.monotonic() >= read_deadline:
                            raise CoreError("CLOUD_REQUEST_TIMEOUT")
                        part = conn.recv(4096)
                        if not part:
                            break
                        raw += part
                    if len(raw) > LIMIT or not raw.endswith(b"\n"):
                        raise CoreError("CLOUD_REQUEST_BOUND")
                    req = json.loads(raw, object_pairs_hook=_json_object)
                else:
                    if self.app.runtime.stop_requested:
                        raise CoreError('CLOUD_QUEUED_PRE_DISPATCH_CANCELLED')
                    if time.monotonic() >= deadline:
                        raise CoreError('CLOUD_QUEUED_PRE_DISPATCH_EXPIRED')
                    # A closed waiting client has not authorized detached work.
                    # Never consume extra bytes or enter Core for that request.
                    import select
                    if select.select([conn], [], [], 0)[0]:
                        if not conn.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT):
                            return True
                        raise CoreError('CLOUD_TYPED_REQUEST_REQUIRED')
                if urgent_only:
                    # Input can wait, but cannot recursively enter C/Store while
                    # another cognition request owns the original safe point.
                    if type(req) is dict and req.get('operation') in {'surface','surface-stream'}:
                        if set(req) != {'operation','observation'}:
                            raise CoreError('CLOUD_TYPED_REQUEST_REQUIRED')
                        self.app.surfaces.validate_observation(SurfaceObservation.model_validate_json(json.dumps(req['observation'])))
                        if self.app.runtime.stop_requested:
                            raise CoreError('CLOUD_QUEUED_PRE_DISPATCH_CANCELLED')
                        if len(self.pending_inputs) >= MAX_PENDING_INPUTS:
                            raise CoreError('CLOUD_INPUT_QUEUE_FULL_PRE_DISPATCH')
                        self.pending_inputs.append((conn, req, time.monotonic()+2*self.app.config.provider_timeout_ms/1000, self.app.runtime.clock.utc_now_us()))
                        queued = True
                        return True
                    # Only original interruption controls run at transport wait.
                    allowed = type(req) is dict and (
                        (set(req) == {"operation", "command"} and req["operation"] == "control"
                         and req["command"] in {"pause", "busy", "available", "revoke", "stop"})
                        or req == {"operation": "view", "view": "status"})
                    if not allowed:
                        raise CoreError("CLOUD_BUSY_PRE_DISPATCH")
                old_sink=getattr(self.app,'response_sink',None)
                old_active=self.active_observation
                try:
                    if type(req) is dict and req.get('operation')=='surface-stream':
                        if set(req)!={'operation','observation'}:raise CoreError('CLOUD_TYPED_REQUEST_REQUIRED')
                        live=[True]
                        def progress(value):
                            if not live[0]:return
                            if value.get('state') not in {'INTERPRETING','RENDERING','PROVISIONAL_MODEL_DRAFT'}:return
                            try:conn.sendall((json.dumps({'progress':value},ensure_ascii=False)+'\n').encode())
                            except OSError:live[0]=False
                        self.app.response_sink=progress
                        req={**req,'operation':'surface'}
                    respond_to=()
                    if self.coalesce_continuations and type(req) is dict and req.get('operation')=='surface':
                        self.active_observation=SurfaceObservation.model_validate_json(json.dumps(req['observation']))
                        context=self._conversation_context(self.active_observation)
                        target=(self.active_observation.binding_id,self.active_observation.event_id)
                        if context==self.unanswered_context and target==self.unanswered_target:respond_to=self.unanswered
                        else:self.unanswered=();self.unanswered_context=None;self.unanswered_target=None
                        self.continuation_target=None
                    result = dispatch(self.app, req, observed_at_us=observed_at_us,respond_to=respond_to)
                    if self.coalesce_continuations and type(req) is dict and req.get('operation')=='surface':
                        if result.get('render_state')=='DEFERRED_TO_CONTINUATION':
                            self.unanswered=(*respond_to,result['message_memory_id'])
                            self.unanswered_context=self._conversation_context(self.active_observation)
                            self.unanswered_target=self.continuation_target
                        else:self.unanswered=();self.unanswered_context=None;self.unanswered_target=None
                    response = {"ok": True, "result": result}
                finally:
                    self.active_observation=old_active
                    self.app.response_sink=old_sink
                    if getattr(self.app,'session',None):self.app.session.draft_sink=old_sink
            except (CoreError, ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
                if self.coalesce_continuations and type(req) is dict and req.get('operation') in {'surface','surface-stream'}:
                    self.unanswered=();self.unanswered_context=None;self.unanswered_target=None
                response = {"ok": False, "code": exc.code if isinstance(exc, CoreError) else "CLOUD_REQUEST_REJECTED"}
            try:
                conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode())
            except OSError:
                pass  # lost response never authorizes replay
        finally:
            if not queued:
                conn.close()
        return True

    def close(self):
        if getattr(self.app,'dialogue_continuation_pending',None) is self.continuation_callback:
            self.app.dialogue_continuation_pending=self.previous_continuation
        self.unanswered=();self.unanswered_context=None;self.unanswered_target=None
        if getattr(self.app.runtime, "control_progress", None) is self.progress_callback:
            self.app.runtime.control_progress = self.previous_progress
        while self.pending_inputs:
            conn, _, _, _ = self.pending_inputs.popleft()
            try:
                conn.sendall(b'{"ok":false,"code":"CLOUD_QUEUED_PRE_DISPATCH_CANCELLED"}\n')
            except OSError:
                pass
            finally:
                conn.close()
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


def request(home, data, timeout=None, *, progress=None):
    path = Path(home).absolute() / "control.sock"
    root = path.parent
    if root != root.resolve() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise CoreError("CLOUD_PRIVATE_HOME_REQUIRED")
    row = path.lstat()
    if not stat.S_ISSOCK(row.st_mode) or row.st_uid != os.getuid() or row.st_mode & 0o077:
        raise CoreError("CLOUD_CONTROL_PATH_DENIED")
    if data.get('operation')=='surface-stream' and progress is None:raise CoreError('CLOUD_STREAM_LISTENER_REQUIRED')
    raw = (json.dumps(data) + "\n").encode()
    if len(raw) > LIMIT:
        raise CoreError("CLOUD_REQUEST_BOUND")
    if timeout is None:
        from .config import load_config

        # Separate queue wait (up to two calls) from this input's own two calls.
        calls = 4 if data.get('operation') in {'surface','surface-stream'} else 2
        if data.get('operation')=='surface-sequence':
            observations=data.get('observations')
            if type(observations) is not list or not 2<=len(observations)<=4:raise CoreError('SURFACE_SEQUENCE_BOUND')
            calls=2*len(observations)  # retained/boundary fallback retains independent phase budgets
        timeout = max(5, calls * load_config(root).provider_timeout_ms / 1000 + 30)
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
            reply=b'';buffer=b'';total=0;frames=0;display=True
            while True:
                while b'\n' not in buffer:
                    part=sock.recv(4096)
                    if not part:raise CoreError('CLOUD_COMPLETION_UNKNOWN_NO_RETRY')
                    buffer+=part;total+=len(part)
                    if len(buffer)>262144 or total>(8388608 if progress else 262144):raise CoreError('CLOUD_RESPONSE_BOUND')
                line,buffer=buffer.split(b'\n',1)
                value=json.loads(line,object_pairs_hook=_json_object)
                if type(value) is dict and set(value)=={'progress'}:
                    frames+=1
                    if progress is None or frames>1024:raise CoreError('CLOUD_PROGRESS_BOUND')
                    body=value['progress']
                    if (type(body) is not dict or body.get('state') not in {'INTERPRETING','RENDERING','PROVISIONAL_MODEL_DRAFT'}
                            or set(body)-{'state','text'} or ('text' in body and (type(body['text']) is not str or len(body['text'])>4096))):
                        raise CoreError('CLOUD_PROGRESS_INVALID')
                    if display:
                        try:progress(body)
                        except Exception:display=False  # keep reading original final result, never redispatch
                    continue
                reply=line
                break
        except OSError:
            raise CoreError("CLOUD_COMPLETION_UNKNOWN_NO_RETRY") from None
        except (ValueError,RecursionError):
            raise CoreError("CLOUD_RESPONSE_UNKNOWN_NO_RETRY") from None
    if len(reply) > 262144:
        raise CoreError("CLOUD_RESPONSE_BOUND")
    try:
        return json.loads(reply, object_pairs_hook=_json_object)
    except (ValueError, RecursionError):
        raise CoreError("CLOUD_RESPONSE_UNKNOWN_NO_RETRY") from None
