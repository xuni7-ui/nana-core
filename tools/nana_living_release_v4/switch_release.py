"""Invoke the existing Host Admin confirmation protocol, never edit state/DB.

No credential defaults/discovery/retry. One explicitly requested transition;
UNKNOWN is returned for reconciliation, never repeated after a timeout.
"""

import os
import http.client
import re
from uuid import uuid4
if __package__:
    from tools.nana_first_life_unified_release.issue_pairing import Portal
else:
    from issue_pairing import Portal


def one_operation(portal, subject, body):
    """A missing/invalid post-dispatch response is UNKNOWN, never safe to resend."""
    try:
        response = portal.call("host/operations", "POST", body)
        data = response["data"]
        if (type(data) is not dict or response["subject_id"] != subject or type(data.get("state")) is not str
                or type(data.get("receipt_id")) is not str):
            raise ValueError("OPERATION_RECEIPT_UNVERIFIED")
        if data["state"] not in {"VERIFIED", "REJECTED", "UNKNOWN"}:
            data = {**data, "state": "UNKNOWN"}
        return data
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        return {"state": "UNKNOWN", "receipt_id": None,
                "client_request_id": body["client_request_id"], "operation": body["operation"],
                "no_retry": True}


def switch(base, subject, release, password_fd, *, operation):
    if operation not in {"UPGRADE", "ROLLBACK"}:
        raise ValueError("VERSION_OPERATION_DENIED")
    portal = Portal(base, timeout=45)
    portal.verify_endpoint()
    raw = os.read(password_fd, 513)
    if len(raw) > 512:
        raise ValueError("PASSWORD_BOUND")
    try:
        login = portal.call("session", "POST", {"subject_id": subject, "password": raw.decode().rstrip("\r\n")})
        if login["subject_id"] != subject:
            raise ValueError("HOST_ADMIN_BINDING_REQUIRED")
        portal.csrf = login["data"]["csrf"]
        bootstrap = portal.call("bootstrap", "GET", None)
        if bootstrap["subject_id"] != subject or "HOST_ADMIN" not in bootstrap["data"]["roles"]:
            raise ValueError("HOST_ADMIN_BINDING_REQUIRED")
        backup_confirmation = portal.call("host/confirmations", "POST", {
            "operation": "BACKUP", "expected_revision": bootstrap["revision"],
        })
        backup_key = "release-backup." + uuid4().hex
        backup = one_operation(portal, subject, {
            "client_request_id": backup_key, "idempotency_key": backup_key, "expected_revision": bootstrap["revision"],
            "run_generation": bootstrap["run_generation"], "owner_epoch": bootstrap["owner_epoch"],
            "operation": "BACKUP", "confirmation_id": backup_confirmation["data"]["confirmation_id"],
        })
        if backup["state"] != "VERIFIED":
            return {"state": "BACKUP_NOT_VERIFIED_NO_SWITCH", "backup_state": backup["state"],
                    "receipt_id": backup["receipt_id"], "client_request_id": backup_key,
                    "services_changed": False, "no_retry": True}
        bootstrap = portal.call("bootstrap", "GET", None)
        confirm = portal.call("host/confirmations", "POST", {
            "operation": operation, "expected_revision": bootstrap["revision"], "release_id": release,
        })
        key = "release." + uuid4().hex
        result = one_operation(portal, subject, {
            "client_request_id": key, "idempotency_key": key, "expected_revision": bootstrap["revision"],
            "run_generation": bootstrap["run_generation"], "owner_epoch": bootstrap["owner_epoch"],
            "operation": operation, "release_id": release, "confirmation_id": confirm["data"]["confirmation_id"],
        })
        error = result.get("error")
        if error is not None and (type(error) is not str or not re.fullmatch(r"[A-Z0-9_]{1,96}", error)):
            error = "REMOTE_OPERATION_ERROR"
        return {"state": result["state"], "receipt_id": result["receipt_id"],
                "error": error, "no_retry": True, "client_request_id": key,
                "services_changed": "UNKNOWN" if result["state"] == "UNKNOWN" else result["state"] == "VERIFIED",
                "subject_id": subject, "database_restored_or_overwritten": False}
    finally:
        raw = None
        try:
            portal.call("session", "DELETE", None)
        except Exception:
            pass  # Session expires; never repeat the version operation.
        portal.jar.clear()
