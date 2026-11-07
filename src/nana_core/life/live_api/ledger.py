"""Durable infrastructure receipts, not dialogue history or Subject decisions.

Reserve before dispatch. On crash incomplete records become UNKNOWN. Persist only
hashes/state/sanitized scalar references; response wording is volatile. Completed/uncertain metadata can leave the bounded
hot set without forgetting
its idempotency key. Archive files contain only the same host receipt metadata,
never Subject facts or response wording. No expiry permits redispatch.
"""

import hashlib
import json
import os
import re
import stat
from pathlib import Path
import time
from .contracts import ApiError, Completion, Receipt
from .state import AtomicDocument


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


HOT_LIMIT = 256
ARCHIVE_FORMAT = "HASHED_RECEIPT_METADATA_V1"
ARCHIVABLE = {"VERIFIED", "REJECTED", "FAILED", "REVOKED", "UNKNOWN"}
TERMINAL = {"VERIFIED", "REJECTED", "FAILED", "REVOKED"}


class OperationLedger:
    def __init__(self, path):
        self.document = AtomicDocument(path, {"schema_version": 1, "revision": 0, "receipts": {}})
        self.volatile = {}
        self.archive_root = Path(str(self.document.path) + ".archive")
        data = self.document.read()
        if (
            set(data)
            not in (
                {"schema_version", "revision", "receipts"},
                {"schema_version", "revision", "receipts", "archive_format"},
            )
            or not isinstance(data["receipts"], dict)
            or ("archive_format" in data and data["archive_format"] != ARCHIVE_FORMAT)
        ):
            raise ApiError("RECEIPT_METADATA_INVALID", 503)
        for key, row in data["receipts"].items():
            self._validate_row(key, row)
        if any(r["receipt"]["state"] in {"REQUESTED", "RUNNING", "ADMITTED"} for r in data["receipts"].values()):

            def recover(data):
                for row in data["receipts"].values():
                    r = row["receipt"]
                    if r["state"] in {"REQUESTED", "RUNNING", "ADMITTED"}:
                        r["state"] = "UNKNOWN"
                        r["error"] = "UNKNOWN_NEEDS_RECONCILIATION"

            self.document.update(recover)

    @staticmethod
    def _validate_row(key, row):
        try:
            if (
                type(key) is not str
                or not re.fullmatch(r"[A-Za-z0-9._:-]{1,96}", key)
                or set(row) != {"principal", "digest", "receipt", "created_at_us"}
                or type(row["principal"]) is not str
                or not 1 <= len(row["principal"]) <= 256
                or not re.fullmatch(r"[a-f0-9]{64}", row["digest"])
                or type(row["created_at_us"]) is not int
                or row["created_at_us"] < 0
            ):
                raise ValueError()
            receipt = Receipt.model_validate_json(json.dumps(row["receipt"]))
            if receipt.receipt_id != key or receipt.result:
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise ApiError("RECEIPT_METADATA_INVALID", 503) from None

    def _archive_path(self, key, *, create=False):
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9._:-]{1,96}", key):
            raise ApiError("RECEIPT_NOT_FOUND", 404)
        hashed = hashlib.sha256(key.encode()).hexdigest()
        bucket = self.archive_root / hashed[:2]
        for directory in (self.archive_root, bucket):
            if create:
                directory.mkdir(mode=0o700, exist_ok=True)
            try:
                info = directory.lstat()
            except FileNotFoundError:
                continue
            if (
                directory.resolve() != directory
                or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
            ):
                raise ApiError("RECEIPT_ARCHIVE_PATH_DENIED", 503)
        return bucket / (hashed[2:] + ".json")

    def _archived(self, key):
        path = self._archive_path(key)
        try:
            path.lstat()
        except FileNotFoundError:
            return None
        value = AtomicDocument.read_existing(path)
        if set(value) != {"schema_version", "revision", "receipt_key", "row"} or value["receipt_key"] != key:
            raise ApiError("RECEIPT_ARCHIVE_INVALID", 503)
        self._validate_row(key, value["row"])
        if value["row"]["receipt"]["state"] not in ARCHIVABLE:
            raise ApiError("RECEIPT_ARCHIVE_INVALID", 503)
        return value["row"]

    def _archive(self, key, row):
        self._validate_row(key, row)
        previous = self._archived(key)
        if previous:
            fixed = ("principal", "digest", "created_at_us")
            if (
                any(previous[k] != row[k] for k in fixed)
                or any(
                    previous["receipt"][k] != row["receipt"][k]
                    for k in ("receipt_id", "client_request_id", "operation")
                )
                or (previous["receipt"]["state"] in TERMINAL and previous != row)
            ):
                raise ApiError("RECEIPT_ARCHIVE_COLLISION", 503)
        path = self._archive_path(key, create=True)
        document = AtomicDocument(path, {"schema_version": 1, "revision": 0, "receipt_key": key, "row": row})
        if previous and previous != row:
            document.update(lambda data: data.update(row=row))
        # Independent readback BEFORE hot eviction. On a crash, a duplicate
        # hot/cold copy is safe: the hot copy is authoritative until removed.
        if self._archived(key) != row:
            raise ApiError("RECEIPT_ARCHIVE_UNVERIFIED", 503)

    def _make_room(self, data, *, protected=None):
        if len(data["receipts"]) < HOT_LIMIT:
            return []
        candidates = sorted(
            (
                (key, row)
                for key, row in data["receipts"].items()
                if key != protected and row["receipt"]["state"] in ARCHIVABLE
            ),
            key=lambda pair: pair[1]["created_at_us"],
        )
        needed = max(32, len(data["receipts"]) - HOT_LIMIT + 1)
        selected = candidates[:needed]
        if len(data["receipts"]) - len(selected) >= HOT_LIMIT:
            raise ApiError("RECEIPT_ACTIVE_CAPACITY", 429)
        for key, row in selected:
            self._archive(key, row)
        for key, _ in selected:
            del data["receipts"][key]
        # Older binaries reject the extended root instead of forgetting the
        # cold keys. Compatibility/downgrade must preserve the whole directory.
        data["archive_format"] = ARCHIVE_FORMAT
        return [key for key, _ in selected]

    @property
    def revision(self):
        return self.document.read()["revision"]

    def entry(self, key):
        """Trusted infrastructure metadata lookup, never a public authorization."""
        with self.document.locked():
            return self.document.read()["receipts"].get(key) or self._archived(key)

    def prior(self, key, principal, payload):
        row = self.entry(key)
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
            if key in data["receipts"] or self._archived(key) is not None:
                raise ApiError("IDEMPOTENCY_COLLISION", 409)
            retired = self._make_room(data)
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

            return retired

        retired = self.document.update(create)
        for old in retired:
            self.volatile.pop(old, None)

    def transition(self, key, state, *, result=None, error=None, dispatched=False):
        # Arbitrary response dicts must not become durable host memory. Result
        # wording is returned only to the authenticated caller in this process.
        def apply(data):
            row = data["receipts"].get(key) or self._archived(key)
            if row is None:
                raise ApiError("RECEIPT_NOT_FOUND", 404)
            r = row["receipt"]
            if r["state"] in TERMINAL:
                raise ApiError("RECEIPT_TERMINAL", 409)
            retired = self._make_room(data, protected=key) if key not in data["receipts"] else []
            data["receipts"][key] = row
            r["state"] = state.value
            r["dispatch_happened"] = r["dispatch_happened"] or dispatched
            r["error"] = error
            r["result"] = {}

            return retired

        retired = self.document.update(apply)
        for old in retired:
            self.volatile.pop(old, None)
        if result is not None:
            self.volatile[key] = result

    def read(self, key, principal):
        row = self.entry(key)
        if row is None or row["principal"] != principal:
            raise ApiError("RECEIPT_NOT_FOUND", 404)
        result = dict(row["receipt"])
        result["result"] = self.volatile.get(key, {})
        return Receipt.model_validate_json(json.dumps(result))
