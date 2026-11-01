"""Finite signed platform metadata -> existing Core UDS, never another brain.

The separately bound adapter credential authenticates a source, not a user,
Manager or host admin. Raw OneBot message text/roles are ignored. The original
owner independently fetches account/message identity and decides any reply.
202 means volatile queue admission, never dispatch/delivery. No automatic retry.
"""

import hashlib
import hmac
import json
import queue
import re
import threading
import time

from ...contracts import CoreError
from ...continuity.privacy import _json_object
from ..control import request
from .contracts import ApiError


class PlatformEvents:
    def __init__(self, service, references):
        if (
            type(references) is not dict
            or len(references) > 16
            or any(
                not re.fullmatch(r"[a-z][a-z0-9._-]{0,63}", k)
                or type(v) is not str
                or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", v)
                for k, v in references.items()
            )
        ):
            raise ApiError("PLATFORM_EVENT_BINDINGS_INVALID")
        self.service, self.references = service, dict(references)
        self.queue = queue.Queue(maxsize=16)
        self.lock = threading.RLock()
        self.pending = set()
        self.hour, self.accepted = 0, 0
        self.last = {"state": "NOT_OBSERVED", "external_delivery": False}
        self.stopped = threading.Event()
        self.worker = None

    def _authenticate(self, channel, raw, signature, platform):
        full = platform + "." + channel
        if (
            platform not in {"qq", "bilibili"}
            or full not in self.references
            or self.service.credential_resolver is None
        ):
            raise ApiError("PLATFORM_EVENT_CHANNEL_UNAVAILABLE", 403)
        if (
            type(raw) is not bytes
            or not 1 <= len(raw) <= 16384
            or not re.fullmatch(r"sha256=[a-f0-9]{64}", signature or "")
        ):
            raise ApiError("PLATFORM_EVENT_AUTH_REQUIRED", 403)
        resolver = self.service.credential_resolver
        reference = self.references[full]
        if not resolver.available(reference):
            raise ApiError("PLATFORM_EVENT_AUTH_REQUIRED", 403)
        try:
            credential = resolver.resolve(reference)
        except Exception:
            raise ApiError("PLATFORM_EVENT_AUTH_REQUIRED", 403) from None
        try:
            key = credential.reveal_for_header()
            if len(key) < 24:
                raise ApiError("PLATFORM_EVENT_AUTH_REQUIRED", 403)
            expected = "sha256=" + hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ApiError("PLATFORM_EVENT_AUTH_REQUIRED", 403)
        finally:
            credential.clear()

    @staticmethod
    def _metadata(raw, platform):
        try:
            body = json.loads(raw, object_pairs_hook=_json_object)
            message = str(body["message_id"])
            valid = (
                re.fullmatch(r"[0-9]{1,20}", message)
                if platform == "qq"
                else re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", message)
            )
            if body.get("post_type") != "message" or not valid:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ApiError("PLATFORM_EVENT_METADATA_INVALID") from None
        return message

    def offer(self, channel, raw, signature, *, platform="qq"):
        self._authenticate(channel, raw, signature, platform)
        message = self._metadata(raw, platform)
        with self.lock:
            now = int(time.monotonic() // 3600)
            if self.hour != now:
                self.hour, self.accepted = now, 0
            if (platform, channel, message) in self.pending:
                return {"state": "ALREADY_QUEUED_NOT_DELIVERED", "external_delivery": False}
            if self.accepted >= 128:
                raise ApiError("PLATFORM_EVENT_RATE_CEILING", 429)
            try:
                self.queue.put_nowait((platform, channel, message))
            except queue.Full:
                raise ApiError("PLATFORM_EVENT_BACKPRESSURE", 429) from None
            self.pending.add((platform, channel, message))
            self.accepted += 1
        return {"state": "QUEUED_NOT_JUDGED", "external_delivery": False, "authority_granted": False}

    def drain_once(self):
        try:
            platform, channel, message = self.queue.get_nowait()
        except queue.Empty:
            return None
        try:
            result = request(
                self.service.supervisor.home,
                {"operation": platform + "-message", "channel_id": channel, "message_id": message},
                timeout=None,  # Derive the bounded two-phase allowance from host config.
            )
            if result.get("ok") is not True:
                state = result.get("error", "CORE_PLATFORM_UNAVAILABLE")
            else:
                state = result["result"].get("delivery", "SOURCE_OBSERVED")
            # Only an allowlisted status, never message/reply/account/credential.
            self.last = {
                "state": state if type(state) is str and re.fullmatch(r"[A-Z_]{1,96}", state) else "UNKNOWN",
                "external_delivery": bool(result.get("ok") and result["result"].get("external_delivery")),
                "no_retry": True,
            }
        except (CoreError, OSError, ValueError, KeyError, TypeError):
            self.last = {"state": "UNKNOWN_CORE_RECEIPT_NOT_CONFIRMED", "external_delivery": False, "no_retry": True}
        finally:
            with self.lock:
                self.pending.discard((platform, channel, message))
            self.queue.task_done()
        return self.last

    def start(self):
        if self.worker is not None:
            raise ApiError("PLATFORM_EVENT_FORWARDER_ALREADY_STARTED")

        def forward():
            while not self.stopped.wait(0.25):
                self.drain_once()

        self.worker = threading.Thread(target=forward, name="nana-platform-metadata", daemon=True)
        self.worker.start()

    def close(self):
        self.stopped.set()
        if self.worker:
            self.worker.join(timeout=2)

    def view(self):
        return {
            "channels": sorted(self.references),
            "pending": self.queue.qsize(),
            "last": dict(self.last),
            "volatile_admission": True,
            "semantic_authority": False,
            "new_store": False,
        }
