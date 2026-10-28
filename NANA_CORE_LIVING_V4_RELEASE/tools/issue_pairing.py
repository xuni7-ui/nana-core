"""Issue through the running original BFF; never generate an unregistered code.

HTTPS/cookie/CSRF/Subject binding and HOST_ADMIN remain server enforced.
No Subject/Genesis access or credential discovery. Only a trusted unrecorded
terminal may display the response; credentials and code are memory-only.
"""

import argparse
import getpass
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PREFIX = "/api/nana-space/v2/"


def issue(call, subject, name):
    result = call(
        "devices/offers", "POST", {"device_name": name, "roles": ["READER", "CONVERSATION"], "lifetime_seconds": 120}
    )
    if result.get("subject_id") != subject:
        raise ValueError("SUBJECT_BINDING_MISMATCH")
    data = result.get("data", {})
    value = data.get("pairing_code")
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", value) or data.get("one_time") is not True:
        raise ValueError("BFF_GENERATOR_PROTOCOL_MISMATCH")
    return value


class Portal:
    def __init__(self, base, *, timeout=15):
        if not 1 <= timeout <= 45:
            raise ValueError("BOUNDED_REQUEST_TIMEOUT_REQUIRED")
        self.timeout = timeout
        url = urllib.parse.urlsplit(base)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
            or "\\" in base
            or any(ord(x) < 33 for x in base)
        ):
            raise ValueError("HTTPS_ORIGIN_REQUIRED")
        self.base = base.rstrip("/")
        self.csrf = None

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise ValueError("CREDENTIAL_REDIRECT_DENIED")

        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(self.jar))

    def verify_endpoint(self):
        # Identify the protected original API before asking for any password.
        request = urllib.request.Request(self.base + PREFIX + "bootstrap", headers={"Origin": self.base})
        try:
            with self.opener.open(request, timeout=15):
                raise ValueError("BFF_ENDPOINT_UNVERIFIED")
        except urllib.error.HTTPError as response:
            if response.code != 401:
                raise ValueError("BFF_ENDPOINT_UNVERIFIED") from None
            data = json.loads(response.read(4097))
            if data != {"contract": "nana-space-live/v2", "code": "SESSION_REQUIRED"}:
                raise ValueError("BFF_ENDPOINT_UNVERIFIED")

    def call(self, path, method, body=None):
        headers = {"Origin": self.base, "Content-Type": "application/json"}
        if self.csrf:
            headers["X-Nana-CSRF"] = self.csrf
        request = urllib.request.Request(
            self.base + PREFIX + path,
            method=method,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        # Each operation sent once. An ambiguous offer completion is never replayed.
        with self.opener.open(request, timeout=self.timeout) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("RESPONSE_BOUND")
        return json.loads(raw)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True)
    p.add_argument("--subject-id", required=True)
    p.add_argument("--device-name", required=True)
    p.add_argument("--password-fd", type=int)
    p.add_argument("--display-fd", type=int, default=1)
    a = p.parse_args()
    if not os.isatty(a.display_fd):
        raise ValueError("PRIVATE_TERMINAL_DISPLAY_REQUIRED_NO_REDIRECTION")
    if not 1 <= len(a.subject_id) <= 96 or not 1 <= len(a.device_name) <= 64:
        raise ValueError("PAIRING_METADATA_INVALID")
    portal = Portal(a.base)
    portal.verify_endpoint()
    password = (
        getpass.getpass("Host web-session password (not Provider key): ")
        if a.password_fd is None
        else os.read(a.password_fd, 513).decode().rstrip("\r\n")
    )
    if not 12 <= len(password) <= 128:
        raise ValueError("SESSION_PASSWORD_BOUND")
    login = portal.call("session", "POST", {"subject_id": a.subject_id, "password": password})
    password = None
    if login.get("subject_id") != a.subject_id:
        raise ValueError("SUBJECT_BINDING_MISMATCH")
    portal.csrf = login["data"]["csrf"]
    try:
        code = issue(portal.call, a.subject_id, a.device_name)
        os.write(a.display_fd, ("One-time device pairing code (120s; keep private):\n" + code + "\n").encode())
        code = None
    finally:
        # Logout does not revoke the pending pairing offer. Never repeat issuance.
        try:
            portal.call("session", "DELETE")
        except Exception:
            pass
        portal.jar.clear()
        portal.csrf = None


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Only predefined codes, never remote messages or credential bodies.
        allowed = {
            "PRIVATE_TERMINAL_DISPLAY_REQUIRED_NO_REDIRECTION",
            "HTTPS_ORIGIN_REQUIRED",
            "PAIRING_METADATA_INVALID",
            "SESSION_PASSWORD_BOUND",
            "SUBJECT_BINDING_MISMATCH",
            "BFF_GENERATOR_PROTOCOL_MISMATCH",
            "CREDENTIAL_REDIRECT_DENIED",
            "RESPONSE_BOUND",
            "BFF_ENDPOINT_UNVERIFIED",
        }
        code = (
            str(error) if type(error) is ValueError and str(error) in allowed else "NETWORK_OR_HTTP_RESULT_UNCONFIRMED"
        )
        print(code, file=sys.stderr)
        # No response/credential/code bodies in diagnostics or tracebacks.
        print(
            "ISSUE_NOT_CONFIRMED_NO_RETRY: check HTTPS, web HOST_ADMIN session and original BFF protocol; do not reuse an uncertain offer.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
