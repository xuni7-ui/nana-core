"""Shared deletable payload/lineage discipline, not a second state store."""
import json

from ..contracts import CoreError
from ..storage import canonical, uid
from .memory import MemoryService, PRIVACY_RANK


class RecordService:
    def __init__(self, store):
        self.store, self.memory = store, MemoryService(store)

    def create(self, tx, *, kind, scope, payload, memories=(), records=(), supersedes=None, target_id=None):
        if not memories and not records:
            raise CoreError("RECORD_SUPPORT_REQUIRED")
        parents = [self.memory.read(x) for x in memories]
        record_parents = [self.read(x) for x in records]
        if any(x["scope"] != scope for x in [*parents, *record_parents]):
            raise CoreError("CROSS_SCOPE_DERIVATION")
        record_id = uid()
        privacy = max((x["privacy_class"] for x in [*parents, *record_parents]), key=PRIVACY_RANK.get)
        tx.put("continuity_records", {"record_id": record_id, "record_kind": kind,
            "scope": scope, "privacy_class": privacy, "payload_artifact_id": tx.artifact(canonical(payload).encode()),
            "lifecycle": "ACTIVE", "created_at_us": self.store.clock.utc_now_us(), "event_id": tx.event_id,
            **({'target_id':target_id} if self.store.schema_target>=9 else {})})
        for parent_kind, values in (("MEMORY", memories), ("RECORD", records)):
            for parent in set(values):
                tx.put("record_dependencies", {"link_id": uid(), "record_id": record_id,
                                               "parent_kind": parent_kind, "parent_id": parent,
                                               "relation_kind": "SUPPORT"})
        if supersedes:
            # Link revisions for erasure even if a future revision omits an old source.
            if supersedes not in records:
                tx.put("record_dependencies", {"link_id": uid(), "record_id": record_id,
                                               "parent_kind": "RECORD", "parent_id": supersedes,
                                               "relation_kind": "REVISION"})
            tx.update("continuity_records", supersedes, lifecycle="SUPERSEDED")
        return record_id

    def read(self, record_id, *, include_history=False):
        self.store.ensure_privacy_current()
        row = self.store.one("continuity_records", record_id)
        allowed = {"ACTIVE", "SUPERSEDED"} if include_history else {"ACTIVE"}
        if not row or row["lifecycle"] not in allowed:
            raise CoreError("RECORD_UNAVAILABLE")
        # A corrected/withdrawn parent is not a current fact merely because the
        # dependent project/commitment still exists. Callers see STALE_SUPPORT.
        return {**row, "payload": json.loads(self.store.artifact(row["payload_artifact_id"]))}

    def support(self, record_id):
        seen, pending, memories = set(), [record_id], set()
        while pending:
            record = pending.pop()
            if record in seen:
                continue
            seen.add(record)
            for edge in self.store.db.execute("SELECT * FROM record_dependencies WHERE record_id=? "
                                             "AND relation_kind='SUPPORT'", (record,)):
                if edge["parent_kind"] == "MEMORY":
                    memories.add(edge["parent_id"])
                else:
                    pending.append(edge["parent_id"])
        return tuple(sorted(memories))

    def current_support(self, record_id):
        for memory_id in self.support(record_id):
            try:
                self.memory.read(memory_id)
            except CoreError:
                return False
        return True
