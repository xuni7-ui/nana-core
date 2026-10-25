"""Durable infrastructure receipts, not dialogue history or Subject decisions.

Reserve before dispatch. On crash incomplete records become UNKNOWN. Persist only
hashes/state/sanitized scalar references; response wording is volatile. Capacity
fails closed rather than forgetting keys and accidentally replaying an effect.
"""

import hashlib
import json
import time
from .contracts import ApiError, Completion, Receipt
from .state import AtomicDocument


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class OperationLedger:
    def __init__(self, path):
        self.document = AtomicDocument(path, {"schema_version": 1, "revision": 0, "receipts": {}})
        self.volatile = {}
        data = self.document.read()
        if set(data) != {"schema_version", "revision", "receipts"} or not isinstance(data["receipts"], dict):
            raise ApiError("RECEIPT_METADATA_INVALID", 503)
        for key, row in data["receipts"].items():
            try:
                Receipt.model_validate_json(json.dumps(row["receipt"]))
                if set(row) != {"principal", "digest", "receipt", "created_at_us"}:
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise ApiError("RECEIPT_METADATA_INVALID", 503) from None
        if any(r["receipt"]["state"] in {"REQUESTED", "RUNNING", "ADMITTED"} for r in data["receipts"].values()):

            def recover(data):
                for row in data["receipts"].values():
                    r = row["receipt"]
                    if r["state"] in {"REQUESTED", "RUNNING", "ADMITTED"}:
                        r["state"] = "UNKNOWN"
                        r["error"] = "UNKNOWN_NEEDS_RECONCILIATION"

            self.document.update(recover)

    @property
    def revision(self):
        return self.document.read()["revision"]

    def prior(self, key, principal, payload):
        row = self.document.read()["receipts"].get(key)
        if row is None:
            return None
        if row["principal"] != principal:
            raise ApiError("RECEIPT_NOT_FOUND", 404)
        if row["digest"] != fingerprint(payload):
            raise ApiError("IDEMPOTENCY_COLLISION", 409)
        return self.read(key, principal)

    def reserve(self, key, principal, payload, operation, expected_revision, client_request_id):
        def create(data):
            if data["revision"] != expected_revision:
                raise ApiError("REVISION_CONFLICT", 409)
            if key in data["receipts"]:
                raise ApiError("IDEMPOTENCY_COLLISION", 409)
            if len(data["receipts"]) >= 256:
                raise ApiError("RECEIPT_CAPACITY_REQUIRES_OPERATOR_ARCHIVE", 429)
            receipt = Receipt(
                receipt_id=key,
                client_request_id=client_request_id,
                operation=operation,
                state=Completion.REQUESTED,
                dispatch_happened=False,
            )
            data["receipts"][key] = {
                "principal": principal,
                "digest": fingerprint(payload),
                "receipt": receipt.model_dump(mode="json"),
                "created_at_us": time.time_ns() // 1000,
            }

        self.document.update(create)

    def transition(self, key, state, *, result=None, error=None, dispatched=False):
        # Arbitrary response dicts must not become durable host memory. Result
        # wording is returned only to the authenticated caller in this process.
        def apply(data):
            r = data["receipts"][key]["receipt"]
            if r["state"] in {"VERIFIED", "REJECTED", "FAILED", "REVOKED"}:
                raise ApiError("RECEIPT_TERMINAL", 409)
            r["state"] = state.value
            r["dispatch_happened"] = r["dispatch_happened"] or dispatched
            r["error"] = error
            r["result"] = {}

        self.document.update(apply)
        if result is not None:
            self.volatile[key] = result

    def read(self, key, principal):
        row = self.document.read()["receipts"].get(key)
        if row is None or row["principal"] != principal:
            raise ApiError("RECEIPT_NOT_FOUND", 404)
        result = dict(row["receipt"])
        result["result"] = self.volatile.get(key, {})
        return Receipt.model_validate_json(json.dumps(result))
