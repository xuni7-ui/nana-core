"""Read-only, operator-pinned synthetic source files; no model-selected paths.

Source files are never modified. Durable receipts reuse the existing separate
FakeWorld journal schema; the journal is intentionally writable development data.
This is a trusted-process adapter, not an OS sandbox for arbitrary Python code.
"""
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Literal
from pydantic import Field, model_validator
from ..contracts import CoreError, DTO, Receipt, SourceArgs, Verification
from ..storage import canonical, digest, uid

READ_CAPABILITIES = {"reading.source.read", "reading.source.locate"}
MAX_SOURCE_BYTES = 65_536


class SourceDocument(DTO):
    schema_version: Literal[1] = 1
    synthetic_only: Literal[True]
    text: str = Field(min_length=1, max_length=48_000)
    locator: str = Field(min_length=1, max_length=512)


class SourceBinding(DTO):
    synthetic_only: Literal[True]
    relative_path: str = Field(min_length=1, max_length=256)
    blob_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def relative_file(self):
        path = PurePosixPath(self.relative_path)
        if (not path.parts or path.is_absolute() or self.relative_path != path.as_posix()
            or any(p in {".", ".."} for p in path.parts) or "\\" in self.relative_path
            or "\x00" in self.relative_path):
            raise ValueError("canonical relative file path required")
        return self


class FileSourcePort:
    def __init__(self, root, bindings: dict[str, SourceBinding], journal):
        root = Path(root).absolute()
        # Refuse symlinked roots/ancestors, then retain the directory fd. Nested
        # source paths are also opened one component at a time with O_NOFOLLOW.
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise CoreError("SOURCE_ROOT_SYMLINK_REJECTED")
        if not bindings or any(not key.startswith("source://synthetic/") for key in bindings):
            raise CoreError("SYNTHETIC_SOURCE_BINDINGS_REQUIRED")
        self._bindings = {key: SourceBinding.model_validate(value.model_dump()) for key, value in bindings.items()}
        self._root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.journal, self.path = journal, journal.path
        self.counts = {"execute_reads": 0, "verify_reads": 0}

    def close(self):
        os.close(self._root_fd)

    def _document(self, resource, kind):
        binding = self._bindings.get(resource)
        if not binding:
            raise CoreError("SOURCE_NOT_BOUND")
        parent_fd = os.dup(self._root_fd)
        try:
            parts = PurePosixPath(binding.relative_path).parts
            for part in parts[:-1]:
                child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = child_fd
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
                    raise CoreError("SOURCE_TYPE_OR_SIZE_REJECTED")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    raw = stream.read(MAX_SOURCE_BYTES + 1)
                if len(raw) > MAX_SOURCE_BYTES:
                    raise CoreError("SOURCE_TYPE_OR_SIZE_REJECTED")
            finally:
                os.close(fd)
        except OSError:
            raise CoreError("SOURCE_READ_DENIED") from None
        finally:
            os.close(parent_fd)
        if digest(raw) != binding.blob_sha256:
            raise CoreError("SOURCE_PIN_MISMATCH")
        try:
            document = SourceDocument.model_validate_json(raw)
        except Exception:
            raise CoreError("SOURCE_DOCUMENT_REJECTED") from None
        self.counts[kind + "_reads"] += 1
        return document, binding.blob_sha256

    def _validate(self, invocation):
        args = SourceArgs.model_validate(invocation.args)
        if (invocation.capability not in READ_CAPABILITIES or args.source_id != invocation.resource
            or invocation.args_hash != digest(invocation.args)):
            raise CoreError("INVALID_READ_ONLY_INVOCATION")

    @staticmethod
    def _result(invocation, document, blob_hash):
        result = {"source_id": invocation.resource, "source_digest": digest(document.text.encode()),
                  "source_blob_sha256": blob_hash, "source_adapter": "pinned_synthetic_file"}
        result["text" if invocation.capability == "reading.source.read" else "locator"] = (
            document.text if invocation.capability == "reading.source.read" else document.locator)
        return result

    def execute(self, invocation):
        self._validate(invocation)
        document, blob_hash = self._document(invocation.resource, "execute")
        body = self._result(invocation, document, blob_hash)
        db = self.journal.db
        db.execute("BEGIN IMMEDIATE")
        try:
            old = db.execute("SELECT * FROM operations WHERE operation_key=?", (invocation.idempotency_key,)).fetchone()
            if old:
                if ((old["capability"], old["resource"], old["args_hash"]) !=
                    (invocation.capability, invocation.resource, invocation.args_hash)
                    or json.loads(old["result_json"]) != body):
                    raise CoreError("IDEMPOTENCY_COLLISION")
                external_id = old["external_id"]
            else:
                external_id = uid()
                db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)", (invocation.idempotency_key,
                    invocation.capability, invocation.resource, invocation.args_hash, canonical(body), external_id))
            db.execute("INSERT INTO calls(operation_key,capability,resource,kind) VALUES(?,?,?,'EXECUTE')",
                       (invocation.idempotency_key, invocation.capability, invocation.resource))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return Receipt(external_id=external_id, result=body)

    def verify(self, invocation):
        self._validate(invocation)
        db = self.journal.db
        db.execute("INSERT INTO calls(operation_key,capability,resource,kind) VALUES(?,?,?,'VERIFY')",
                   (invocation.idempotency_key, "reading.action.verify", invocation.resource))
        operation = db.execute("SELECT * FROM operations WHERE operation_key=?", (invocation.idempotency_key,)).fetchone()
        if not operation:
            # Missing receipt does not prove that a filesystem read never happened.
            return Verification(verdict="INCONCLUSIVE", evidence={"reason": "NO_DURABLE_READ_RECEIPT"})
        try:
            document, blob_hash = self._document(invocation.resource, "verify")
        except CoreError as exc:
            return Verification(verdict="INCONCLUSIVE", evidence={"reason": exc.code})
        body = self._result(invocation, document, blob_hash)
        matches = ((operation["capability"], operation["resource"], operation["args_hash"]) ==
                   (invocation.capability, invocation.resource, invocation.args_hash)
                   and json.loads(operation["result_json"]) == body)
        return Verification(verdict="MATCH" if matches else "EFFECT_MISMATCH", evidence={
            "operation_key": invocation.idempotency_key, "external_id": operation["external_id"],
            "source_blob_sha256": blob_hash, "result": body, "independent_readback": True,
            "external_world": "development_synthetic_file"})
