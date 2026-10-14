"""Typed memory with explicit claim families and evidence-backed correction.

Raw observation, claim and derived summary have independent identities. Only
trusted application controllers call these commit methods; LLMs propose DTOs.
"""
import json
import re

from ..contracts import CoreError
from ..storage import canonical, digest, uid
from .contracts import EvidenceInput, MemoryCandidate

PRIVACY_RANK = {"PUBLIC": 0, "PROJECT": 1, "PERSONAL": 2, "SECRET": 3}


class MemoryService:
    def __init__(self, store):
        self.store = store

    def entity(self, entity_id, kind):
        if type(entity_id) is not str or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", entity_id):
            raise CoreError("INVALID_ENTITY_ID")
        if kind not in {"PERSON", "SELF", "PROJECT", "OBJECT"}:
            raise CoreError("INVALID_ENTITY_KIND")
        existing = self.store.one("entities", entity_id)
        if existing:
            if existing["entity_type"] != kind:
                raise CoreError("ENTITY_BINDING_CONFLICT")
            return entity_id
        with self.store.transaction("memory.entity_registered") as tx:
            tx.put("entities", {"entity_id": entity_id, "entity_type": kind,
                                "created_at_us": self.store.clock.utc_now_us()})
        return entity_id

    def capture(self, candidate: EvidenceInput):
        if not isinstance(candidate, EvidenceInput):
            raise CoreError("INVALID_EVIDENCE_CONTRACT")
        p = candidate.provenance
        previous = self.store.db.execute("SELECT * FROM continuity_evidence WHERE "
            "source_namespace=? AND source_reference=? AND source_revision=?",
            (p.source_namespace, p.source_reference, p.source_revision)).fetchone()
        # Stable keys stay tombstoned; never create a new payload for deleted input.
        if previous:
            if previous["state"] == "DELETED":
                raise CoreError("SOURCE_DELETED")
            payload = json.loads(self.store.artifact(previous["payload_artifact_id"]))
            if payload != candidate.model_dump(mode="json"):
                raise CoreError("SOURCE_KEY_COLLISION")
            return previous["evidence_id"]
        # Revision changes are not a backdoor around erasure of a source object.
        if self.store.db.execute("SELECT 1 FROM continuity_evidence WHERE "
                "source_namespace=? AND source_reference=? AND state='DELETED'",
                (p.source_namespace, p.source_reference)).fetchone():
            raise CoreError("SOURCE_DELETED")
        now = self.store.clock.utc_now_us()
        if candidate.observed_time_us > now:
            raise CoreError("OBSERVATION_FROM_FUTURE")
        evidence_id = uid()
        with self.store.transaction("memory.evidence_captured", occurred_at_us=candidate.event_time_us) as tx:
            artifact_id = tx.artifact(candidate.model_dump_json().encode())
            tx.put("continuity_evidence", {"evidence_id": evidence_id,
                "source_namespace": p.source_namespace, "source_reference": p.source_reference,
                "source_revision": p.source_revision, "source_kind": p.source_kind,
                "provenance_json": p.model_dump_json(), "privacy_class": candidate.privacy_class,
                "payload_artifact_id": artifact_id, "event_time_us": candidate.event_time_us,
                "observed_time_us": candidate.observed_time_us, "ingested_time_us": now,
                "state": "AVAILABLE", "event_id": tx.event_id})
        return evidence_id

    def evidence(self, evidence_id):
        row = self.store.one("continuity_evidence", evidence_id)
        if not row or row["state"] != "AVAILABLE":
            raise CoreError("EVIDENCE_UNAVAILABLE")
        return row

    def read(self, memory_id, *, include_inactive=False):
        row = self.store.one("memories", memory_id)
        if not row or row["lifecycle"] == "DELETED":
            raise CoreError("MEMORY_UNAVAILABLE")
        if not include_inactive and (row["lifecycle"] != "ACTIVE" or
                row["assessment"] not in {"CURRENT", "UNASSESSED"}):
            raise CoreError("MEMORY_NOT_CURRENT")
        return {**row, "text": self.store.artifact(row["payload_artifact_id"]).decode(),
                "source_provenance": json.loads(self.evidence(row["source_evidence_id"])["provenance_json"])}

    def add(self, candidate: MemoryCandidate):
        if not isinstance(candidate, MemoryCandidate):
            raise CoreError("INVALID_MEMORY_CONTRACT")
        if not self.store.one("entities", candidate.entity_id):
            raise CoreError("ENTITY_BINDING_REQUIRED")
        source = self.evidence(candidate.source_evidence_id)
        authority = "DIRECT" if source["source_kind"] in {
            "USER_STATEMENT", "DIRECT_OBSERVATION", "SYSTEM_VERIFICATION"} else "INFERRED"
        if candidate.epistemic_kind in {"SUMMARY", "INFERENCE", "LESSON"}:
            authority = "INFERRED"
        parents = [self.read(x) for x in candidate.derived_from]
        if any(p["scope"] != candidate.scope for p in parents):
            raise CoreError("CROSS_SCOPE_DERIVATION")
        privacy = max([source["privacy_class"], *(p["privacy_class"] for p in parents)], key=PRIVACY_RANK.get)
        if candidate.epistemic_kind in {"OBSERVATION", "STATEMENT"}:
            raw = json.loads(self.store.artifact(source["payload_artifact_id"]))
            if candidate.text != raw["text"] or source["source_kind"] == "MODEL_DERIVATION":
                raise CoreError("DERIVATION_CANNOT_BECOME_OBSERVATION")
        family = self.family(candidate.entity_id, candidate.scope, candidate.predicate_key)
        old = None
        if candidate.correction_of:
            old = self.read(candidate.correction_of, include_inactive=True)
            if old not in family or authority != "DIRECT":
                raise CoreError("INVALID_CORRECTION_AUTHORITY_OR_FAMILY")
            if (source["event_time_us"] is None or old["event_time_us"] is None or
                    source["event_time_us"] < old["event_time_us"]):
                raise CoreError("CORRECTION_TIME_UNPROVEN")
        now = self.store.clock.utc_now_us()
        memory_id = uid()
        assessment = "CURRENT" if not candidate.predicate_key or not family else "DISPUTED"
        if authority != "DIRECT" and candidate.predicate_key:
            assessment = "UNASSESSED"
        if old:
            assessment = "CURRENT"
        with self.store.transaction("memory.committed") as tx:
            tx.put("memories", {"memory_id": memory_id, "entity_id": candidate.entity_id,
                "scope": candidate.scope, "memory_type": candidate.memory_type.value,
                "epistemic_kind": candidate.epistemic_kind, "source_evidence_id": candidate.source_evidence_id,
                "payload_artifact_id": tx.artifact(candidate.text.encode()),
                "predicate_key": candidate.predicate_key, "event_time_us": source["event_time_us"],
                "observed_time_us": source["observed_time_us"], "ingested_time_us": now,
                "confidence": candidate.confidence, "authority": authority,
                "importance": candidate.importance, "significance": candidate.significance,
                "privacy_class": privacy, "lifecycle": "ACTIVE", "assessment": assessment,
                "correction_of": candidate.correction_of, "superseded_by": None,
                "created_at_us": now, "updated_at_us": now, "event_id": tx.event_id})
            for kind, parent in [("EVIDENCE", candidate.source_evidence_id),
                                 *(("MEMORY", p) for p in candidate.derived_from)]:
                tx.put("memory_dependencies", {"link_id": uid(), "memory_id": memory_id,
                                              "parent_kind": kind, "parent_id": parent})
            # An unresolved family stays visibly disputed, not two true facts.
            if candidate.predicate_key and authority == "DIRECT":
                for item in family:
                    if old and item["memory_id"] == old["memory_id"]:
                        tx.update("memories", item["memory_id"], assessment="SUPERSEDED",
                                  superseded_by=memory_id, updated_at_us=now)
                    elif item["assessment"] in {"CURRENT", "DISPUTED"}:
                        # Duplicate corroboration doesn't erase conflict provenance.
                        if item["text"] == candidate.text and not old:
                            tx.update("memories", memory_id, assessment=item["assessment"])
                        else:
                            tx.update("memories", item["memory_id"], assessment="DISPUTED", updated_at_us=now)
                            tx.update("memories", memory_id, assessment="DISPUTED")
            self._index(memory_id, candidate.text)
        return memory_id

    def family(self, entity_id, scope, predicate_key):
        if predicate_key is None:
            return []
        rows = self.store.db.execute("SELECT memory_id FROM memories WHERE entity_id=? AND scope=? "
            "AND predicate_key=? AND lifecycle='ACTIVE' AND assessment NOT IN ('SUPERSEDED','WITHDRAWN')",
            (entity_id, scope, predicate_key)).fetchall()
        return [self.read(r[0], include_inactive=True) for r in rows]

    def query(self, *, entity_ids=(), scopes=(), privacy_classes=("PUBLIC",), include_conflicts=False):
        if not scopes or not privacy_classes:
            return []
        rows = self.store.db.execute("SELECT memory_id FROM memories WHERE lifecycle='ACTIVE' "
            "AND assessment IN ('CURRENT','UNASSESSED'" + (",'DISPUTED'" if include_conflicts else "") + ")").fetchall()
        result = []
        for r in rows:
            row = self.store.one("memories", r[0])
            # Privacy filtering BEFORE loading any payload.
            if (row["scope"] in scopes and row["privacy_class"] in privacy_classes
                    and (not entity_ids or row["entity_id"] in entity_ids)):
                result.append(self.read(r[0], include_inactive=include_conflicts))
        return result

    def _index(self, memory_id, text):
        terms = set(re.findall(r"\w{2,64}", text.casefold()))
        self.store.db.executemany("INSERT OR IGNORE INTO memory_terms VALUES(?,?)",
                                 ((memory_id, t) for t in terms))

    def rebuild_index(self):
        self.store.db.execute("DELETE FROM memory_terms")
        for row in self.store.all("memories"):
            if row["lifecycle"] == "ACTIVE":
                self._index(row["memory_id"], self.store.artifact(row["payload_artifact_id"]).decode())
