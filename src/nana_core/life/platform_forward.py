"""One signed metadata handoff for an explicitly bound legacy adapter.

No platform message body, model or account send. The original owner fetches the
actual event independently and applies C/Manager/Grant/Kernel/Verify. A missing
HTTP acknowledgement is UNKNOWN and is never retried here. Credentials come
only from an explicit FD or the explicitly selected host vault.
"""

import argparse
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from ..contracts import CoreError
from ..continuity.privacy import _json_object
from .provider import ExplicitFDResolver


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def forward(base, platform, channel, message_id, resolver, reference):
    try:
        url = urllib.parse.urlsplit(base)
        local = url.scheme == "http" and url.hostname in {"127.0.0.1", "::1"}
        if (
            url.scheme != "https"
            and not local
            or not url.hostname
            or url.path not in {"", "/"}
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or any(c in base for c in "\r\n\\")
            or url.port is not None
            and not 1 <= url.port <= 65535
        ):
            raise ValueError()
    except ValueError:
        raise CoreError("PLATFORM_FORWARD_ENDPOINT_INVALID") from None
    if (
        platform not in {"qq", "bilibili"}
        or not re.fullmatch(r"[a-z][a-z0-9._-]{0,63}", channel)
        or not re.fullmatch(r"-?[0-9]{1,20}" if platform == "qq" else r"[A-Za-z0-9._:-]{1,128}", message_id)
    ):
        raise CoreError("PLATFORM_FORWARD_METADATA_INVALID")
    raw = json.dumps({"post_type": "message", "message_id": message_id}, separators=(",", ":")).encode()
    credential = resolver.resolve(reference)
    try:
        key = credential.reveal_for_header()
        if len(key) < 24:
            raise CoreError("PLATFORM_FORWARD_CREDENTIAL_INVALID")
        signature = "sha256=" + hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
    finally:
        credential.clear()
    target = base.rstrip("/") + "/api/nana-space/v2/platform/" + platform + "/events/" + channel
    req = urllib.request.Request(
        target, data=raw, headers={"Content-Type": "application/json", "X-Nana-Signature": signature}, method="POST"
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=3) as response:
            body = response.read(4097)
            if response.status != 202 or len(body) > 4096:
                raise ValueError()
            result = json.loads(body, object_pairs_hook=_json_object)
            state = result.get("state")
            if state not in {"QUEUED_NOT_JUDGED", "ALREADY_QUEUED_NOT_DELIVERED"}:
                raise ValueError()
            return {"state": state, "delivery_confirmed": False, "no_retry": True}
    except urllib.error.HTTPError as exc:
        return {"state": "REJECTED_HTTP_" + str(exc.code), "delivery_confirmed": False, "no_retry": True}
    except (OSError, ValueError):
        return {"state": "UNKNOWN_INGRESS_ACK_NO_RETRY", "delivery_confirmed": False, "no_retry": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--platform", choices=("qq", "bilibili"), required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--secret-ref", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--secret-fd", type=int)
    group.add_argument("--host-vault")
    args = parser.parse_args()
    resolver = None
    try:
        import sys

        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise CoreError("PLATFORM_FORWARD_INPUT_BOUND")
        event = json.loads(raw, object_pairs_hook=_json_object)
        if type(event) is not dict or "message_id" not in event:
            raise CoreError("PLATFORM_FORWARD_METADATA_INVALID")
        if args.secret_fd is not None:
            resolver = ExplicitFDResolver(args.secret_fd, args.secret_ref)
        else:
            from .provider_vault import DurableSecretResolver

            resolver = DurableSecretResolver(args.host_vault, initialize=False)
        result = forward(
            args.base_url, args.platform, args.channel, str(event["message_id"]), resolver, args.secret_ref
        )
        print(json.dumps(result), flush=True)
    except (CoreError, OSError, ValueError, TypeError):
        print(
            json.dumps({"state": "PLATFORM_FORWARD_BLOCKED", "no_retry": True, "delivery_confirmed": False}), flush=True
        )
        raise SystemExit(2) from None
    finally:
        if resolver:
            resolver.clear()
        if args.secret_fd is not None:
            os.close(args.secret_fd)


if __name__ == "__main__":
    main()
