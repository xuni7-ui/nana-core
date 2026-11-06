"""Typed memory with explicit claim families and evidence-backed correction.

Raw observation, claim and derived summary have independent identities. Only
trusted application controllers call these commit methods; LLMs propose DTOs.
"""
import json
import re

from ..contracts import CoreError
from ..storage import uid
from .contracts import EvidenceInput, MemoryCandidate, MemoryType

PRIVACY_RANK = {"PUBLIC": 0, "PROJECT": 1, "PERSONAL": 2, "SECRET": 3}


class MemoryService:
    def __init__(self, store, authority=None):
        self.store, self._authority = store, authority

    def _fresh(self):
        self.store.ensure_privacy_current()

    def entity(self, entity_id, kind):
        if type(entity_id) is not str or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", entity_id):
            raise CoreError("INVALID_ENTITY_ID")
        if kind not in {"PERSON", "SELF", "PROJECT", "OBJECT", "GROUP", "COMMUNITY", "AGENT"}:
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
        self._fresh()
        if not isinstance(candidate, EvidenceInput):
            raise CoreError("INVALID_EVIDENCE_CONTRACT")
        p = candidate.provenance
        legacy = p.domain == 'LEGACY_ARCHIVE'
        if legacy:
            # Only the local, manifest/lineage-bound import controller can admit
            # archived claims. A DTO, model output or a boolean is insufficient.
            from ..migration.archive_ingress import ArchiveIngressAuthority
            if type(self._authority) is not ArchiveIngressAuthority or not self._authority.permits(self.store, candidate):
                raise CoreError('LEGACY_ARCHIVE_IMPORT_NOT_AUTHORIZED')
        consented=p.domain=='CONSENTED_INTERACTION'
        if consented and (self.store.schema_target<13 or candidate.privacy_class not in {'PUBLIC','PROJECT','PERSONAL'} or candidate.retention_consent_ref!=p.source_reference or (p.source_namespace,p.source_kind) not in {('recorded.conversation.input','USER_STATEMENT'),('recorded.conversation.feedback','USER_STATEMENT'),('recorded.conversation.feedback-check','SYSTEM_VERIFICATION'),('recorded.conversation.concern','MODEL_DERIVATION')}):raise CoreError('EXPLICIT_CONVERSATION_RETENTION_REQUIRED')
        local=p.domain=='LOCAL_INTERACTION_METADATA'
        if local:
            from .contracts import PENDING_LOCAL_RECEIPT
            legacy=p.source_kind=='USER_STATEMENT' and re.fullmatch(r'Local input reviewed meaning: (?:VENT|CHAT|HELP|SHARE|CORRECTION|DECLINE_DEPTH|DECLINE_DELIVERY|REOPEN|REOPEN_DELIVERY|FOCUS|UNCLEAR|IMPORTANT|PROJECT_STATUS)',candidate.text)
            pending=p.source_kind=='DIRECT_OBSERVATION' and candidate.text==PENDING_LOCAL_RECEIPT
            if self.store.schema_target<13 or candidate.privacy_class not in {'PUBLIC','PROJECT','PERSONAL'} or not (legacy or pending):raise CoreError('LOCAL_METADATA_ONLY')
        project=p.domain=="DEVELOPMENT_PROJECT" and candidate.privacy_class=="PROJECT" and self.store.schema_target>=13
        if p.domain=="DEVELOPMENT_PROJECT" and not project:raise CoreError("PROJECT_DEVELOPMENT_INGRESS_ONLY")
        if p.domain!="SYNTHETIC_ONLY" and not project and not local and not consented and not legacy and (self.store.schema_target<13 or candidate.privacy_class!="PUBLIC"):
            raise CoreError("PUBLIC_DEVELOPMENT_INGRESS_ONLY")
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
        self._fresh()
        row = self.store.one("continuity_evidence", evidence_id)
        if not row or row["state"] != "AVAILABLE":
            raise CoreError("EVIDENCE_UNAVAILABLE")
        return row

    def read(self, memory_id, *, include_inactive=False):
        self._fresh()
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
        if candidate.memory_type.value == "SELF" and candidate.entity_id != self.store.identity["identity_id"]:
            raise CoreError("SELF_MEMORY_REQUIRES_CANONICAL_SUBJECT")
        source = self.evidence(candidate.source_evidence_id)
        legacy = json.loads(source['provenance_json'])['domain'] == 'LEGACY_ARCHIVE'
        if legacy and (candidate.memory_type != MemoryType.SEMANTIC or candidate.epistemic_kind != 'BELIEF'
                       or candidate.confidence != 0 or candidate.correction_of or not candidate.predicate_key):
            raise CoreError('LEGACY_CLAIM_CANNOT_BECOME_EXPERIENCE_OR_FACT')
        authority = "DIRECT" if source["source_kind"] in {
            "USER_STATEMENT", "DIRECT_OBSERVATION", "SYSTEM_VERIFICATION"} else "INFERRED"
        if legacy:
            authority = 'INFERRED'
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
        # Idempotent cognitive commit without retaining a content hash after
        # erasure. Stable source keys plus remaining payload/lineage identify it.
        for raw in self.store.db.execute("SELECT * FROM memories WHERE source_evidence_id=? "
                "AND entity_id=? AND scope=?", (candidate.source_evidence_id, candidate.entity_id, candidate.scope)):
            row = dict(raw)
            if row["lifecycle"] == "DELETED":
                continue
            if (row["memory_type"], row["epistemic_kind"], row["predicate_key"], row["correction_of"]) != (
                    candidate.memory_type.value, candidate.epistemic_kind, candidate.predicate_key, candidate.correction_of):
                continue
            parents = {r[0] for r in self.store.db.execute("SELECT parent_id FROM memory_dependencies "
                "WHERE memory_id=? AND parent_kind='MEMORY'", (row["memory_id"],))}
            if parents == set(candidate.derived_from) and self.store.artifact(row["payload_artifact_id"]).decode() == candidate.text:
                return row["memory_id"]
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
        direct_family = [x for x in family if x["authority"] == "DIRECT"]
        assessment = "CURRENT" if not candidate.predicate_key or not direct_family else "DISPUTED"
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
                        self.store.db.execute("DELETE FROM memory_terms WHERE memory_id=?", (item["memory_id"],))
                        self._invalidate_descendants(tx, item["memory_id"])
                    elif item["assessment"] in {"CURRENT", "DISPUTED"}:
                        # Duplicate corroboration doesn't erase conflict provenance.
                        if item["text"] == candidate.text and not old:
                            tx.update("memories", memory_id, assessment=item["assessment"])
                        else:
                            tx.update("memories", item["memory_id"], assessment="DISPUTED", updated_at_us=now)
                            self.store.db.execute("DELETE FROM memory_terms WHERE memory_id=?", (item["memory_id"],))
                            self._invalidate_descendants(tx, item["memory_id"])
                            tx.update("memories", memory_id, assessment="DISPUTED")
            if self.store.one("memories", memory_id)["assessment"] in {"CURRENT", "UNASSESSED"}:
                self._index(memory_id, candidate.text)
        return memory_id

    def family(self, entity_id, scope, predicate_key):
        if predicate_key is None:
            return []
        rows = self.store.db.execute("SELECT memory_id FROM memories WHERE entity_id=? AND scope=? "
            "AND predicate_key=? AND lifecycle='ACTIVE' AND assessment NOT IN ('SUPERSEDED','WITHDRAWN')",
            (entity_id, scope, predicate_key)).fetchall()
        return [self.read(r[0], include_inactive=True) for r in rows]

    def _query_filter(self, entity_ids, scopes, privacy_classes, include_conflicts, memory_types=()):
        if not scopes or not privacy_classes:
            return "0", []
        states = ("CURRENT", "UNASSESSED", "DISPUTED") if include_conflicts else ("CURRENT", "UNASSESSED")
        clauses, parameters = ["m.lifecycle='ACTIVE'"], []
        for column, values in (("scope", scopes), ("privacy_class", privacy_classes), ("assessment", states)):
            clauses.append(f"m.{column} IN ({','.join('?' for _ in values)})")
            parameters.extend(values)
        if entity_ids:
            clauses.append(f"m.entity_id IN ({','.join('?' for _ in entity_ids)})")
            parameters.extend(entity_ids)
        if memory_types:
            kinds = {kind.value for kind in MemoryType}
            if not isinstance(memory_types, (tuple, list)) or any(
                not isinstance(value, str) or value not in kinds for value in memory_types
            ):
                raise CoreError("INVALID_MEMORY_TYPE_FILTER")
            clauses.append(f"m.memory_type IN ({','.join('?' for _ in memory_types)})")
            parameters.extend(memory_types)
        return " AND ".join(clauses), parameters

    def query_count(self, *, entity_ids=(), scopes=(), privacy_classes=("PUBLIC",), include_conflicts=False, memory_types=()):
        self._fresh()
        where, args = self._query_filter(entity_ids, scopes, privacy_classes, include_conflicts, memory_types)
        return self.store.db.execute("SELECT count(*) FROM memories m WHERE " + where, args).fetchone()[0]

    def query(self, *, entity_ids=(), scopes=(), privacy_classes=("PUBLIC",), include_conflicts=False,
              limit=128, query_terms=(), memory_types=()):
        self._fresh()
        if type(limit) is not int or not 1 <= limit <= 512:
            raise CoreError("INVALID_RETRIEVAL_LIMIT")
        if not scopes or not privacy_classes:
            return []
        where, args = self._query_filter(entity_ids, scopes, privacy_classes, include_conflicts, memory_types)
        if query_terms:
            if len(query_terms) > 32 or any(type(t) is not str or not 1 <= len(t) <= 128 for t in query_terms):
                raise CoreError("INVALID_QUERY_TERMS")
            relevance = "(SELECT count(*) FROM memory_terms t WHERE t.memory_id=m.memory_id "
            relevance += f"AND t.term IN ({','.join('?' for _ in query_terms)}))"
            order_args = [t.casefold() for t in query_terms]
        else:
            relevance, order_args = "0+0", []
        # Rare-term expansion helps large eligible sets. Common terms and small
        # scopes keep the original query plan; no plaintext/result cache is used.
        sparse = False
        has_term_index = bool(query_terms) and self.store.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='memory_terms_term_lookup'"
        ).fetchone() is not None
        if has_term_index:
            placeholders = ','.join('?' for _ in query_terms)
            dense = self.store.db.execute(
                f"SELECT 1 FROM memory_terms WHERE term IN ({placeholders}) LIMIT 1 OFFSET 4096",
                order_args,
            ).fetchone()
            if dense is None:
                visible = self.store.db.execute(
                    "SELECT count(*) FROM memories m WHERE " + where, args
                ).fetchone()[0]
                sparse = visible > 512
        order = "(m.authority='DIRECT') DESC,m.importance DESC,m.significance DESC,m.event_time_us DESC,m.rowid"
        if sparse:
            # CROSS JOIN pins the selective term lookup before memory checks.
            # Both stages retain the same scope/entity/privacy/current filters.
            rows = self.store.db.execute(
                f"WITH hits AS (SELECT t.memory_id,count(*) AS relevance "
                f"FROM memory_terms t INDEXED BY memory_terms_term_lookup CROSS JOIN memories m "
                f"ON m.memory_id=t.memory_id WHERE t.term IN ({placeholders}) AND {where} "
                f"GROUP BY t.memory_id) SELECT m.memory_id FROM memories m "
                f"LEFT JOIN hits h ON h.memory_id=m.memory_id WHERE {where} "
                f"ORDER BY coalesce(h.relevance,0) DESC,{order} LIMIT ?",
                [*order_args, *args, *args, limit],
            ).fetchall()
        else:
            rows = self.store.db.execute(
                "SELECT m.memory_id FROM memories m WHERE " + where +
                " ORDER BY " + relevance + " DESC," + order + " LIMIT ?",
                [*args, *order_args, limit],
            ).fetchall()
        return [self.read(r[0], include_inactive=include_conflicts) for r in rows]

    def conflict_bundle(self, row, privacy_classes):
        headers = self.store.db.execute("SELECT * FROM memories WHERE entity_id=? AND scope=? AND predicate_key=? "
            "AND lifecycle='ACTIVE' AND assessment NOT IN ('SUPERSEDED','WITHDRAWN')",
            (row["entity_id"], row["scope"], row["predicate_key"])).fetchall()
        if len(headers) > 64 or any(h["privacy_class"] not in privacy_classes for h in headers):
            raise CoreError("INSUFFICIENT_CONTRADICTION_CONTEXT")
        return [self.read(h["memory_id"], include_inactive=True) for h in headers]

    def _invalidate_descendants(self, tx, memory_id):
        pending, seen = [memory_id], {memory_id}
        while pending:
            parent = pending.pop()
            children = self.store.db.execute("SELECT memory_id FROM memory_dependencies "
                "WHERE parent_kind='MEMORY' AND parent_id=?", (parent,)).fetchall()
            for child, in children:
                if child in seen:
                    continue
                seen.add(child)
                pending.append(child)
                tx.update("memories", child, assessment="WITHDRAWN",
                          updated_at_us=self.store.clock.utc_now_us())
                self.store.db.execute("DELETE FROM memory_terms WHERE memory_id=?", (child,))

    def set_lifecycle(self, memory_id, state, authority):
        if self._authority is None or authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        if state not in {"SUPPRESSED", "ARCHIVED", "ACTIVE"}:
            raise CoreError("USE_PRIVACY_ERASURE_FOR_DELETE")
        row = self.read(memory_id, include_inactive=True)
        if state == "ACTIVE" and row["assessment"] in {"WITHDRAWN", "SUPERSEDED"}:
            raise CoreError("RETIRED_MEMORY_CANNOT_REVIVE")
        with self.store.transaction("memory.lifecycle_changed") as tx:
            tx.update("memories", memory_id, lifecycle=state, updated_at_us=self.store.clock.utc_now_us())
            if state != "ACTIVE":
                self.store.db.execute("DELETE FROM memory_terms WHERE memory_id=?", (memory_id,))
                self._invalidate_descendants(tx, memory_id)
            else:
                self._index(memory_id, row["text"])

    def assess_confidence(self, memory_id, value, authority):
        if self._authority is None or authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        if type(value) is not float or not 0 <= value <= 1:
            raise CoreError("INVALID_CONFIDENCE")
        self.read(memory_id, include_inactive=True)
        with self.store.transaction("memory.confidence_assessed") as tx:
            tx.update("memories", memory_id, confidence=value, updated_at_us=self.store.clock.utc_now_us())

    def forget(self, memory_id, authority):
        if self._authority is None or authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        return self.store.privacy._erase(memory_id)

    def _index(self, memory_id, text):
        terms = set(re.findall(r"\w{2,64}", text.casefold()))
        self.store.db.executemany("INSERT OR IGNORE INTO memory_terms VALUES(?,?)",
                                 ((memory_id, t) for t in terms))

    def rebuild_index(self):
        self.store.db.execute("DELETE FROM memory_terms")
        for row in self.store.all("memories"):
            if row["lifecycle"] == "ACTIVE" and row["assessment"] in {"CURRENT", "UNASSESSED"}:
                self._index(row["memory_id"], self.store.artifact(row["payload_artifact_id"]).decode())
