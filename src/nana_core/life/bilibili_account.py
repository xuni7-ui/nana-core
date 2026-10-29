"""Explicit account adapter, never another Bilibili brain or authority ledger.

The HTTP paths mirror the existing C.2 reader/sender semantics. Credentials are
resolved only from the host-supplied resolver; no legacy file/env discovery.
Writes are usable only as an original ActionKernel CapabilityPort, after its
Grant/Manager/budget gate. Verification is a fresh platform read, never HTTP200.
"""

import json
import http.client
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from types import MappingProxyType

from pydantic import Field

from ..contracts import DTO, CoreError, Invocation, Receipt, Verification
from ..storage import digest
from .bilibili import NoRedirect, plain, BilibiliLoopbackOpener


@dataclass(frozen=True)
class BilibiliAccountPolicy:
    account_id: int
    read_authorized: bool = False
    send_authorized: bool = False
    exclusive_writer_confirmed: bool = False
    permitted_recipients: tuple[int, ...] = ()
    request_limit: int = 12


class BilibiliAccountTransport:
    """Bounded real API implementation. Construction grants no Core authority."""
    def __init__(self, resolver, *, cookie_ref, csrf_ref, policy, realm="ACCOUNT_API_UNATTESTED", loopback_endpoint=None):
        if realm not in {"ACCOUNT_API_UNATTESTED", "SYNTHETIC_LOOPBACK", "AUTHENTICATED_PLATFORM"}:
            raise CoreError("BILIBILI_ACCOUNT_REALM_INVALID")
        if loopback_endpoint is not None and realm != "SYNTHETIC_LOOPBACK":
            raise CoreError("BILIBILI_LOOPBACK_ORIGIN_REQUIRED")
        self.__resolver = resolver
        self.__cookie_ref, self.__csrf_ref = cookie_ref, csrf_ref
        self.policy = policy
        self.realm = realm
        self.calls = 0
        self.__nav_cookie_digest = None
        self.__attested_cookie = None
        self.opener = BilibiliLoopbackOpener(loopback_endpoint) if loopback_endpoint is not None else urllib.request.build_opener(NoRedirect())

    def __repr__(self):
        return "<BilibiliAccountTransport explicit credentials REDACTED>"

    def _admit(self, host, path, write):
        allowed = {
            ("api.vc.bilibili.com", "/session_svr/v1/session_svr/get_sessions", False),
            ("api.vc.bilibili.com", "/svr_sync/v1/svr_sync/fetch_session_msgs", False),
            ("api.vc.bilibili.com", "/web_im/v1/web_im/send_msg", True),
            ("api.bilibili.com", "/x/v2/reply", False),
            ("api.bilibili.com", "/x/v2/reply/add", True),
            ("api.bilibili.com", "/x/web-interface/nav", False),
        }
        if (host, path, write) not in allowed:
            raise CoreError("BILIBILI_ACCOUNT_ENDPOINT_DENIED")
        p = self.policy
        if p.read_authorized is not True or type(p.account_id) is not int or p.account_id < 1:
            raise CoreError("BILIBILI_ACCOUNT_READ_NOT_AUTHORIZED")
        if write and (p.send_authorized is not True or p.exclusive_writer_confirmed is not True):
            raise CoreError("BILIBILI_ACCOUNT_WRITER_NOT_AUTHORIZED")
        if self.calls >= min(max(p.request_limit, 0), 32):
            raise CoreError("BILIBILI_ACCOUNT_BUDGET")

    def _json(self, host, path, values, *, write=False):
        self._admit(host, path, write)
        credential = self.__resolver.resolve(self.__cookie_ref)
        try:
            cookie = credential.reveal_for_header()
            if not cookie or len(cookie) > 4096 or any(ord(c) < 32 or ord(c) > 126 for c in cookie):
                raise CoreError("BILIBILI_ACCOUNT_CREDENTIAL_INVALID")
            if write:
                if self.__attested_cookie != (self.policy.account_id, digest(cookie)):
                    raise CoreError("BILIBILI_ACCOUNT_BINDING_MISMATCH")
                self.__attested_cookie = None  # One POST at most per self-account preflight.
            headers = {"Cookie": cookie, "Referer": "https://www.bilibili.com/", "User-Agent": "NanaCore/4"}
            values = dict(values)
            if write:
                csrf = self.__resolver.resolve(self.__csrf_ref)
                try:
                    value = csrf.reveal_for_header()
                    if not re.fullmatch(r"[A-Za-z0-9]{16,64}", value):
                        raise CoreError("BILIBILI_CSRF_REFERENCE_INVALID")
                    values.update(csrf=value, csrf_token=value)
                finally:
                    csrf.clear()
            encoded = urllib.parse.urlencode(values).encode()
            url = "https://" + host + path + ("" if write else "?" + encoded.decode())
            request = urllib.request.Request(url, data=encoded if write else None, headers=headers,
                                             method="POST" if write else "GET")
            self.calls += 1
            try:
                with self.opener.open(request, timeout=5) as response:
                    raw = response.read(262145)
            except (OSError, http.client.HTTPException):
                raise CoreError("BILIBILI_SEND_UNKNOWN_NO_RETRY" if write else "BILIBILI_ACCOUNT_READ_UNAVAILABLE") from None
            if len(raw) > 262144:
                raise CoreError("BILIBILI_ACCOUNT_RESPONSE_BOUND")
            try:
                from ..continuity.privacy import _json_object
                result = json.loads(raw, object_pairs_hook=_json_object)
                if type(result) is not dict or result.get("code") != 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise CoreError("BILIBILI_SEND_UNKNOWN_NO_RETRY" if write else "BILIBILI_ACCOUNT_API_UNAVAILABLE") from None
            if (host, path) == ("api.bilibili.com", "/x/web-interface/nav"):
                self.__nav_cookie_digest = digest(cookie)
            return result.get("data")
        finally:
            credential.clear()

    def account(self):
        """Attest the Cookie's actual logged-in MID before any write precheck."""
        self.__attested_cookie = self.__nav_cookie_digest = None
        try:
            data = self._json("api.bilibili.com", "/x/web-interface/nav", {})
            if (type(data) is not dict or data.get("isLogin") is not True
                    or type(data.get("mid")) is not int or data["mid"] != self.policy.account_id):
                raise CoreError("BILIBILI_ACCOUNT_BINDING_MISMATCH")
            # RAM-only correlation also blocks a host credential rotation between
            # account preflight and POST. No cookie or cookie digest is persisted.
            self.__attested_cookie = (data["mid"], self.__nav_cookie_digest)
            return {"account_id": data["mid"], "authenticated_self_read": True}
        finally:
            self.__nav_cookie_digest = None

    def sessions(self):
        data = self._json("api.vc.bilibili.com", "/session_svr/v1/session_svr/get_sessions",
                          {"session_type": 1, "group_fold": 1, "unfollow_fold": 0, "sort_rule": 2})
        if type(data) is not dict or type(data.get("session_list", [])) is not list:
            raise CoreError("BILIBILI_SESSION_RESPONSE_INVALID")
        out = []
        for row in data.get("session_list", [])[:16]:
            if type(row) is dict and row.get("session_type") == 1:
                out.append({"talker_id": row.get("talker_id"), "unread_count": row.get("unread_count", 0),
                            "last_seqno": row.get("max_seqno", 0), "session_timestamp": row.get("session_ts"),
                            "privacy_class": "PERSONAL", "source": "BILIBILI_ACCOUNT_SESSION"})
        return {"sessions": out, "pagination": "FIRST_PAGE_ONLY", "second_store": False}

    def messages(self, recipient, *, after_seqno=0):
        if type(recipient) is not int or recipient < 1 or type(after_seqno) is not int or after_seqno < 0:
            raise CoreError("BILIBILI_RECIPIENT_INVALID")
        if recipient not in self.policy.permitted_recipients:
            raise CoreError("BILIBILI_CONTACT_NOT_AUTHORIZED")
        data = self._json("api.vc.bilibili.com", "/svr_sync/v1/svr_sync/fetch_session_msgs",
                          {"talker_id": recipient, "session_type": 1, "size": 20})
        if type(data) is not dict or type(data.get("messages", [])) is not list:
            raise CoreError("BILIBILI_MESSAGE_RESPONSE_INVALID")
        out = []
        for row in data.get("messages", [])[:20]:
            if type(row) is not dict:
                continue
            try:
                content = json.loads(row.get("content", "{}"))
                sequence = int(row.get("msg_seqno", 0))
                sender = int(row.get("sender_uid", 0))
                target = int(row.get("receiver_id", 0))
            except (ValueError, TypeError):
                continue
            if type(content) is not dict:
                continue
            if {sender, target} != {self.policy.account_id, recipient} or sequence <= after_seqno:
                continue
            out.append({"message_key": str(row.get("msg_key", "")), "sequence": sequence,
                        "sender_id": sender, "receiver_id": target, "text": plain(content.get("content"), 2048),
                        "timestamp": row.get("timestamp"), "privacy_class": "PERSONAL"})
        return out

    def comment_rows(self, aid):
        if type(aid) is not int or aid < 1:
            raise CoreError("BILIBILI_MATERIAL_IDENTITY_REQUIRED")
        data = self._json("api.bilibili.com", "/x/v2/reply", {"type": 1, "oid": aid, "pn": 1, "ps": 20, "sort": 0})
        if type(data) is not dict or type(data.get("replies") or []) is not list:
            raise CoreError("BILIBILI_COMMENT_RESPONSE_INVALID")
        return [row for row in (data.get("replies") or [])[:20] if type(row) is dict]

    def send_comment(self, aid, text, root=0):
        return self._json("api.bilibili.com", "/x/v2/reply/add",
                          {"type": 1, "oid": aid, "message": text, "root": root, "parent": root}, write=True)

    def send_message(self, recipient, text, key):
        if type(recipient) is not int or recipient < 1 or recipient not in self.policy.permitted_recipients:
            raise CoreError("BILIBILI_CONTACT_NOT_AUTHORIZED")
        from uuid import UUID
        return self._json("api.vc.bilibili.com", "/web_im/v1/web_im/send_msg", {
            "msg[sender_uid]": self.policy.account_id, "msg[receiver_id]": recipient,
            "msg[receiver_type]": 1, "msg[msg_type]": 1, "msg[msg_status]": 0,
            "msg[content]": json.dumps({"content": text}, ensure_ascii=False),
            "msg[timestamp]": int(time.time()), "msg[dev_id]": str(UUID(digest(key)[:32])),
        }, write=True)


class BilibiliSendArgs(DTO):
    target_id: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=1024)
    after_seqno: int = Field(default=0, ge=0)
    root_reply_id: int = Field(default=0, ge=0)
    data_privacy: str = "PUBLIC"


class BilibiliActionRegistry:
    """Finite descriptive catalogue, not a Grant or model-selectable backend."""
    definitions = MappingProxyType({"bilibili.comment.send": BilibiliSendArgs, "bilibili.dm.send": BilibiliSendArgs})
    verify_capability = "bilibili.action.verify"

    @staticmethod
    def is_write(capability):
        return capability in BilibiliActionRegistry.definitions

    @staticmethod
    def request_count(capability):
        if capability not in BilibiliActionRegistry.definitions:
            raise CoreError("BILIBILI_ACTION_UNSUPPORTED")
        return 3  # Authenticated self-account + duplicate precheck + at most one POST.

    @staticmethod
    def payload_privacy(payload):
        return payload.get("data_privacy", "PUBLIC") if type(payload) is dict else "PUBLIC"

    def validate(self, capability, resource, args):
        if capability not in self.definitions:
            raise CoreError("BILIBILI_ACTION_UNSUPPORTED")
        body = BilibiliSendArgs.model_validate(args).model_dump()
        kind = "comment" if capability == "bilibili.comment.send" else "dm"
        if resource != "project://bilibili/" + kind + "/" + str(body["target_id"]):
            raise CoreError("BILIBILI_ACTION_TARGET_MISMATCH")
        if body["data_privacy"] not in ({"PUBLIC"} if kind == "comment" else {"PUBLIC", "PROJECT", "PERSONAL"}):
            raise CoreError("BILIBILI_PUBLIC_PRIVACY_DENIED")
        return body


class BilibiliActionPort:
    """C.2 precheck→one send→independent verify, persisted by original Kernel.

    A host composes this port with the original Kernel/registry. It must not be
    exposed as a raw frontend POST or model tool bypassing that Kernel. UNKNOWN
    cannot execute again; restart verification derives entirely from original
    action args/attempts and a fresh account read, with no second ledger.
    """
    def __init__(self, store, transport, *, app=None, activation=None):
        self.store, self.transport = store, transport
        self.app, self.activation = app, activation
        self.identity_id = store.identity["identity_id"]

    def assert_owned(self):
        if self.transport.realm == "SYNTHETIC_LOOPBACK" and type(self.transport.opener) is BilibiliLoopbackOpener:
            BilibiliLoopbackOpener(self.transport.opener.endpoint)
            return
        if self.app is not None and self.activation is not None and self.transport.realm == "AUTHENTICATED_PLATFORM":
            from .platform_authority import require_platform_authority
            if self.app.runtime.store is not self.store:
                raise CoreError("PLATFORM_CANONICAL_STORE_MISMATCH")
            require_platform_authority(self.app, self.activation, channel="bilibili", exclusive_writer=True,
                                       account_id=self.transport.policy.account_id)
            return
        raise CoreError("BILIBILI_CANONICAL_ACTIVATION_REQUIRED")

    def _bound(self, invocation, *, verifying=False):
        if type(invocation) is not Invocation:
            raise CoreError("BILIBILI_KERNEL_INVOCATION_REQUIRED")
        row = self.store.one("actions", invocation.action_id)
        states = {"PENDING_VERIFY", "UNKNOWN", "SUCCEEDED"} if verifying else {"DISPATCHING"}
        if not row or row["state"] not in states or any(row[name] != getattr(invocation, name)
                for name in ("attempt_id", "capability", "resource", "args_hash", "idempotency_key")):
            raise CoreError("BILIBILI_KERNEL_ACTION_UNBOUND")
        if digest(invocation.args) != invocation.args_hash:
            raise CoreError("BILIBILI_KERNEL_ARGS_MISMATCH")
        policy = self.transport.policy
        if not verifying and (policy.send_authorized is not True or policy.exclusive_writer_confirmed is not True):
            raise CoreError("BILIBILI_ACCOUNT_WRITER_NOT_AUTHORIZED")
        return BilibiliActionRegistry().validate(invocation.capability, invocation.resource, invocation.args)

    def _matches(self, invocation, body):
        if invocation.capability == "bilibili.dm.send":
            rows = self.transport.messages(body["target_id"], after_seqno=body["after_seqno"])
            return [r for r in rows if r["sender_id"] == self.transport.policy.account_id and r["text"] == body["text"]]
        rows = self.transport.comment_rows(body["target_id"])
        return [r for r in rows if type(r.get("member")) is dict and type(r.get("content")) is dict
                and str(r["member"].get("mid")) == str(self.transport.policy.account_id)
                and plain(r["content"].get("message"), 2048) == body["text"]
                and str(r.get("root", 0)) == str(body["root_reply_id"])]

    def execute(self, invocation):
        body = self._bound(invocation)
        account = self.transport.account()
        # Persist only the checked account/action correlation in the ORIGINAL
        # journal. A failed identity preflight must never later verify a matching
        # historical public comment as this action's accepted account result.
        with self.store.transaction("bilibili.account_bound", {"action_id": invocation.action_id,
                "attempt_id": invocation.attempt_id, "args_hash": invocation.args_hash,
                "account_id": account["account_id"]}):
            pass
        prior = self._matches(invocation, body)
        if prior:
            return Receipt(external_id=str(prior[0].get("message_key", prior[0].get("rpid", "existing"))),
                           result={"state": "PRE_EXIST", "send_count": 0, "independent_verify_required": True})
        if invocation.capability == "bilibili.dm.send":
            result = self.transport.send_message(body["target_id"], body["text"], invocation.idempotency_key)
        else:
            result = self.transport.send_comment(body["target_id"], body["text"], body["root_reply_id"])
        return Receipt(external_id=str((result or {}).get("msg_key", (result or {}).get("rpid", invocation.action_id))),
                       result={"state": "ACCEPTED_NEEDS_VERIFY", "send_count": 1, "independent_verify_required": True})

    def verify(self, invocation):
        body = self._bound(invocation, verifying=True)
        bound = self.store.db.execute("SELECT 1 FROM events WHERE kind='bilibili.account_bound' "
            "AND json_extract(data_json,'$.data.action_id')=? AND json_extract(data_json,'$.data.attempt_id')=? "
            "AND json_extract(data_json,'$.data.args_hash')=? AND json_extract(data_json,'$.data.account_id')=? LIMIT 1",
            (invocation.action_id, invocation.attempt_id, invocation.args_hash, self.transport.policy.account_id)).fetchone()
        if not bound:
            return Verification(verdict="INCONCLUSIVE", evidence={"platform": "bilibili", "no_blind_retry": True,
                "authenticated_account_preflight": "NOT_BOUND", "network_calls": 0})
        try:
            matches = self._matches(invocation, body)
        except CoreError:
            matches = []
        if not matches:
            return Verification(verdict="INCONCLUSIVE", evidence={"platform": "bilibili", "no_blind_retry": True})
        item = matches[0]
        return Verification(verdict="MATCH", evidence={"platform": "bilibili", "read_only_platform_confirmation": True,
            "result": {"message_key": item.get("message_key"), "reply_id": item.get("rpid"), "send_repeated": False}})


from ..continuity.autonomy.realization import GovernedRealization


class BilibiliAccountRealization(GovernedRealization):
    """Exact account port bound to the existing C/Manager/Grant/Kernel chain."""
    def __init__(self, store, transport, authority, *, app=None, activation=None):
        from ..actions import ActionKernel
        from ..continuity.autonomy.governance import ManagerConstraintGate
        if store.schema_target < 13 or type(transport) is not BilibiliAccountTransport:
            raise CoreError("BILIBILI_ORIGINAL_RUNTIME_REQUIRED")
        self.store, self.gate = store, ManagerConstraintGate(store)
        self.port = BilibiliActionPort(store, transport, app=app, activation=activation)
        self.kernel = ActionKernel(store, self.port, authority, registry=BilibiliActionRegistry())
