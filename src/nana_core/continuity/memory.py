"""Typed memory with explicit claim families and evidence-backed correction.

Raw observation, claim and derived summary have independent identities. Only
trusted application controllers call these commit methods; LLMs propose DTOs.
"""
from contextlib import nullcontext
import json
import re
import sqlite3
import time

from ..contracts import CoreError
from ..storage import uid
from .contracts import EvidenceInput, MemoryCandidate, MemoryType

PRIVACY_RANK = {"PUBLIC": 0, "PROJECT": 1, "PERSONAL": 2, "SECRET": 3}

# Rebuildable lookup terms share the original memory_terms deletion lifecycle.
# Completeness is per immutable payload; old binaries/long notes remain scanned.
NOTE_GRAM_PREFIX = '@note-literal3-v1:'
NOTE_GRAM_COMPLETE = NOTE_GRAM_PREFIX + 'complete'
NOTE_GRAM_MAX_CHARS = 4096
# One derived end key completes two-codepoint prefix lookup. Legacy/long
# payloads without it stay in the exact scan fallback; old readers ignore it.
NOTE_END_PREFIX = '@note-literal2-end-v1:'


def _prefix_upper(prefix):
    for i in range(len(prefix)-1,-1,-1):
        if ord(prefix[i])<0x10ffff:
            code=ord(prefix[i])+1
            if 0xd800<=code<=0xdfff:code=0xe000
            return prefix[:i]+chr(code)
    raise ValueError('literal namespace has no successor')

# Same qualification before ranking/LIMIT for literal lookup and G snapshots.
USER_NOTE_HEADER_QUALIFICATION = (
    " AND substr(m.predicate_key,1,10)='user-note.'"
    " AND m.authority='DIRECT' AND m.epistemic_kind='STATEMENT'"
)
USER_NOTE_SOURCE_QUALIFICATION = (
    " AND e.source_namespace='recorded.conversation.input' AND e.source_kind='USER_STATEMENT'"
    " AND json_extract(e.provenance_json,'$.domain')='CONSENTED_INTERACTION'"
    " AND substr(e.source_reference,1,5)='note:' AND e.state='AVAILABLE'"
)
USER_NOTE_QUALIFICATION = USER_NOTE_HEADER_QUALIFICATION + USER_NOTE_SOURCE_QUALIFICATION


def is_user_note(memory):
    """Explicitly consented user statement, never a lived event or permission."""
    provenance = memory.get("source_provenance", {})
    return (
        (memory.get("predicate_key", "") or "").startswith("user-note.")
        and (provenance.get("domain"), provenance.get("source_namespace"), provenance.get("source_kind"))
        == ("CONSENTED_INTERACTION", "recorded.conversation.input", "USER_STATEMENT")
        and provenance.get("source_reference", "").startswith("note:")
        and memory.get("epistemic_kind") == "STATEMENT"
        and memory.get("memory_type") == "SEMANTIC"
        and memory.get("authority") == "DIRECT"
    )


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
        return self._capture(candidate)

    def _matching_evidence(self, provenance):
        return self.store.db.execute(
            "SELECT * FROM continuity_evidence WHERE source_namespace=? AND source_reference=? AND source_revision=?",
            (provenance.source_namespace, provenance.source_reference, provenance.source_revision),
        ).fetchone()

    def _capture(self, candidate: EvidenceInput, *, tx=None):
        if tx is None:
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
        own=p.domain=='SELF_COGNITION'
        if own:
            from ..actions import OperatorAuthority
            from .contracts import SELF_COGNITION_OCCURRENCE_TEXT,SELF_PROVIDER_CONSIDERATION_TEXT
            expected={'recorded.subject.cognition-occurrence':(SELF_COGNITION_OCCURRENCE_TEXT,r'self\.[a-f0-9]{64}'),
                'recorded.subject.provider-consideration':(SELF_PROVIDER_CONSIDERATION_TEXT,r'self\.request\.[a-f0-9]{64}')}.get(p.source_namespace)
            root=(expected is not None and p.source_kind=='SYSTEM_VERIFICATION'
                and candidate.text==expected[0] and re.fullmatch(expected[1],p.source_reference)
                and type(self._authority) is OperatorAuthority)
            derived=p.source_namespace=='recorded.subject.concern' and p.source_kind=='MODEL_DERIVATION'
            if derived:
                from .subject.opportunities import ConcernCue
                ConcernCue.model_validate_json(candidate.text)
            if self.store.schema_target<13 or not (root or derived) or candidate.retention_consent_ref is not None:
                raise CoreError('SELF_COGNITION_OCCURRENCE_REQUIRED')
        consented=p.domain=='CONSENTED_INTERACTION'
        if consented and (self.store.schema_target<13 or candidate.privacy_class not in {'PUBLIC','PROJECT','PERSONAL'} or candidate.retention_consent_ref!=p.source_reference or (p.source_namespace,p.source_kind) not in {('recorded.conversation.input','USER_STATEMENT'),('recorded.conversation.feedback','USER_STATEMENT'),('recorded.conversation.feedback-check','SYSTEM_VERIFICATION'),('recorded.conversation.concern','MODEL_DERIVATION')}):raise CoreError('EXPLICIT_CONVERSATION_RETENTION_REQUIRED')
        platform=p.domain=='CONSENTED_PLATFORM'
        if platform:
            from ..nanalink.private_source import PlatformObservationAuthority
            if (self.store.schema_target<13 or candidate.privacy_class!='PERSONAL'
                    or p.source_namespace!='recorded.platform.bilibili.dynamic'
                    or p.source_kind!='DIRECT_OBSERVATION'
                    or type(self._authority) is not PlatformObservationAuthority
                    or not self._authority.permits(self.store,candidate)):
                raise CoreError('PLATFORM_OBSERVATION_NOT_AUTHORIZED')
        local=p.domain=='LOCAL_INTERACTION_METADATA'
        if local:
            from .contracts import PENDING_LOCAL_RECEIPT
            legacy=p.source_kind=='USER_STATEMENT' and re.fullmatch(r'Local input reviewed meaning: (?:VENT|CHAT|HELP|SHARE|CORRECTION|DECLINE_DEPTH|DECLINE_DELIVERY|REOPEN|REOPEN_DELIVERY|FOCUS|UNCLEAR|IMPORTANT|PROJECT_STATUS)',candidate.text)
            pending=p.source_kind=='DIRECT_OBSERVATION' and candidate.text==PENDING_LOCAL_RECEIPT
            if self.store.schema_target<13 or candidate.privacy_class not in {'PUBLIC','PROJECT','PERSONAL'} or not (legacy or pending):raise CoreError('LOCAL_METADATA_ONLY')
        project=p.domain=="DEVELOPMENT_PROJECT" and candidate.privacy_class=="PROJECT" and self.store.schema_target>=13
        if p.domain=="DEVELOPMENT_PROJECT" and not project:raise CoreError("PROJECT_DEVELOPMENT_INGRESS_ONLY")
        if p.domain!="SYNTHETIC_ONLY" and not project and not local and not consented and not legacy and not own and not platform and (self.store.schema_target<13 or candidate.privacy_class!="PUBLIC"):
            raise CoreError("PUBLIC_DEVELOPMENT_INGRESS_ONLY")
        previous = self._matching_evidence(p)
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
        transaction = nullcontext(tx) if tx is not None else self.store.transaction(
            "memory.evidence_captured", occurred_at_us=candidate.event_time_us)
        with transaction as tx:
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
        return self._available_evidence(evidence_id)

    def _available_evidence(self, evidence_id):
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
        return self._add(candidate)

    def capture_derived_observation(self, evidence: EvidenceInput, *, parent_memory_id):
        """Commit excerpt evidence with its backlink in one owner transaction."""
        if not isinstance(evidence, EvidenceInput) or evidence.provenance.source_kind != "DIRECT_OBSERVATION":
            raise CoreError("DERIVED_OBSERVATION_EVIDENCE_REQUIRED")
        parent = self.read(parent_memory_id)
        if evidence.privacy_class != parent["privacy_class"]:
            raise CoreError("DERIVED_OBSERVATION_PRIVACY_MISMATCH")

        def observation(evidence_id):
            return MemoryCandidate(
                entity_id=parent["entity_id"], scope=parent["scope"], memory_type=MemoryType.EPISODIC,
                epistemic_kind="OBSERVATION", text=evidence.text, source_evidence_id=evidence_id,
                derived_from=(parent_memory_id,),
            )

        if self._matching_evidence(evidence.provenance) is not None:
            return self.add(observation(self.capture(evidence)))
        with self.store.transaction("memory.derived_observation_committed", occurred_at_us=evidence.event_time_us) as tx:
            evidence_id = self._capture(evidence, tx=tx)
            return self._add(observation(evidence_id), tx=tx, parent=parent)

    def _add(self, candidate: MemoryCandidate, *, tx=None, parent=None):
        if not isinstance(candidate, MemoryCandidate):
            raise CoreError("INVALID_MEMORY_CONTRACT")
        if not self.store.one("entities", candidate.entity_id):
            raise CoreError("ENTITY_BINDING_REQUIRED")
        if candidate.memory_type.value == "SELF" and candidate.entity_id != self.store.identity["identity_id"]:
            raise CoreError("SELF_MEMORY_REQUIRES_CANONICAL_SUBJECT")
        source = (self.evidence if tx is None else self._available_evidence)(candidate.source_evidence_id)
        provenance=json.loads(source['provenance_json'])
        if provenance['domain']=='SELF_COGNITION':
            if provenance['source_namespace'] in {'recorded.subject.cognition-occurrence','recorded.subject.provider-consideration'}:
                if (candidate.entity_id!=self.store.identity['identity_id'] or candidate.memory_type!=MemoryType.EPISODIC
                        or candidate.epistemic_kind!='OBSERVATION' or candidate.predicate_key or candidate.correction_of or candidate.derived_from):
                    raise CoreError('SELF_COGNITION_IS_OCCURRENCE_NOT_WORLD_CLAIM')
            elif candidate.epistemic_kind!='INFERENCE' or candidate.memory_type!=MemoryType.PROSPECTIVE or not candidate.derived_from:
                raise CoreError('SELF_COGNITION_DERIVATION_REQUIRES_INFERENCE')
        legacy = provenance['domain'] == 'LEGACY_ARCHIVE'
        if legacy and (candidate.memory_type != MemoryType.SEMANTIC or candidate.epistemic_kind != 'BELIEF'
                       or candidate.confidence != 0 or candidate.correction_of or not candidate.predicate_key):
            raise CoreError('LEGACY_CLAIM_CANNOT_BECOME_EXPERIENCE_OR_FACT')
        authority = "DIRECT" if source["source_kind"] in {
            "USER_STATEMENT", "DIRECT_OBSERVATION", "SYSTEM_VERIFICATION"} else "INFERRED"
        if legacy:
            authority = 'INFERRED'
        if candidate.epistemic_kind in {"SUMMARY", "INFERENCE", "LESSON"}:
            authority = "INFERRED"
        parents = [parent] if parent is not None else [self.read(x) for x in candidate.derived_from]
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
        transaction = nullcontext(tx) if tx is not None else self.store.transaction("memory.committed")
        with transaction as tx:
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
              limit=128, query_terms=(), memory_types=(), predicate_prefixes=(), source_namespaces=()):
        self._fresh()
        if type(limit) is not int or not 1 <= limit <= 512:
            raise CoreError("INVALID_RETRIEVAL_LIMIT")
        if not scopes or not privacy_classes:
            return []
        where, args = self._query_filter(entity_ids, scopes, privacy_classes, include_conflicts, memory_types)
        # Select sourced claim families before ranking/limits or loading payloads.
        # Literal prefix matching deliberately gives % and _ no wildcard authority.
        if predicate_prefixes:
            if not isinstance(predicate_prefixes, (tuple, list)) or len(predicate_prefixes) > 8 or any(
                type(prefix) is not str or not 1 <= len(prefix) <= 128 for prefix in predicate_prefixes
            ):
                raise CoreError("INVALID_PREDICATE_PREFIX_FILTER")
            where += " AND (" + " OR ".join(
                "substr(m.predicate_key,1,length(?))=?" for _ in predicate_prefixes
            ) + ")"
            args.extend(value for prefix in predicate_prefixes for value in (prefix, prefix))
        # A caller may request one sourced family without unrelated memories
        # consuming its bounded population before provenance qualification.
        # Namespace matching is exact: these values never carry LIKE syntax.
        if source_namespaces:
            if not isinstance(source_namespaces, (tuple, list)) or len(source_namespaces) > 8 or any(
                type(namespace) is not str or not 1 <= len(namespace) <= 128 for namespace in source_namespaces
            ):
                raise CoreError("INVALID_SOURCE_NAMESPACE_FILTER")
            where += (" AND EXISTS (SELECT 1 FROM continuity_evidence e WHERE e.evidence_id=m.source_evidence_id "
                      + f"AND e.source_namespace IN ({','.join('?' for _ in source_namespaces)}))")
            args.extend(source_namespaces)
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

    def literal_notes(self, *, entity_ids, scopes, privacy_classes, terms, limit=4, timeout_ms=100):
        """Bounded original-Store literal lookup, not semantic truth or a cache.

        Materialize authorized headers before inspecting text. Only the existing
        explicitly retained note family participates; arbitrary observations,
        private intentions and archives cannot enter through this shortcut.
        The single owner must call outside a transaction/progress callback.
        """
        self._fresh()
        if (
            type(terms) is not tuple
            or not 1 <= len(terms) <= 8
            or any(type(t) is not str or not 2 <= len(t) <= 64 for t in terms)
            or type(limit) is not int
            or not 1 <= limit <= 4
            or type(timeout_ms) is not int
            or not 1 <= timeout_ms <= 1000
        ):
            raise CoreError("INVALID_NOTE_RECALL_QUERY")
        where, args = self._query_filter(entity_ids, scopes, privacy_classes, False, ("SEMANTIC",))
        match = " OR ".join("instr(lower(CAST(a.payload AS TEXT)),lower(?))>0" for _ in terms)
        deadline = time.monotonic() + timeout_ms / 1000
        db = self.store.db
        if db.in_transaction:
            raise CoreError("NOTE_RECALL_SAFE_POINT_REQUIRED")
        from .store import REBUILDABLE_LOOKUP_INDEXES
        index = db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='memory_user_note_lookup'").fetchone()
        if index and index[0] != REBUILDABLE_LOOKUP_INDEXES['memory_user_note_lookup']:
            raise CoreError('NOTE_RECALL_INDEX_DEFINITION_MISMATCH')
        hint = ' INDEXED BY memory_user_note_lookup' if index else ''
        term_index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='memory_terms_term_lookup'").fetchone()
        if term_index and term_index[0]!=REBUILDABLE_LOOKUP_INDEXES['memory_terms_term_lookup']:
            raise CoreError('NOTE_RECALL_INDEX_DEFINITION_MISMATCH')
        # A substring match must contain its first normalized trigram. This is
        # only a candidate accelerator: final literal/source checks stay exact.
        # Two-codepoint queries reuse prefix grams plus one payload end key.
        # Missing/legacy cache entries retain exact scanning, never false absence.
        grams=tuple(dict.fromkeys(NOTE_GRAM_PREFIX+t.casefold()[:3] for t in terms))
        accelerated=bool(term_index and all(len(t.casefold())>=3 for t in terms))
        short=bool(term_index and any(len(t.casefold())==2 for t in terms) and all(len(t.casefold())>=2 for t in terms))
        coverage=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='memory_note_gram_coverage'").fetchone()
        if coverage and coverage[0]!=REBUILDABLE_LOOKUP_INDEXES['memory_note_gram_coverage']:
            raise CoreError('NOTE_RECALL_INDEX_DEFINITION_MISMATCH')
        coverage_hint=' INDEXED BY memory_note_gram_coverage' if coverage else hint
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        try:
            prefix="WITH "
            memory_from="memories m"+hint
            parameters=[]
            rows=None
            if short:
                prefix,memory_from,parameters,posting=self._short_note_candidates(where,args,coverage_hint,terms)
                rows=self._broad_note_matches(prefix,memory_from,parameters,posting,where,args,match,terms,limit)
            elif accelerated:
                # EXCEPT is index-only: no payload from an unqualified header is
                # opened. Unindexed notes remain in the candidate set, including
                # notes written by old versions and payloads over the gram cap.
                prefix+=("unindexed AS MATERIALIZED (SELECT m.memory_id FROM memories m"+coverage_hint+
                    " WHERE "+where+USER_NOTE_HEADER_QUALIFICATION+" AND m.memory_type='SEMANTIC' EXCEPT "
                    "SELECT memory_id FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE term=?), "
                    "candidate_ids AS MATERIALIZED (SELECT memory_id FROM unindexed UNION "
                    "SELECT memory_id FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE term IN ("+
                    ','.join('?' for _ in grams)+")), ")
                parameters.extend((*args,NOTE_GRAM_COMPLETE,*grams))
                # Candidate-first primary-key probes avoid rejoining every note
                # to evidence before the selective gram set is considered.
                memory_from="candidate_ids c CROSS JOIN memories m ON m.memory_id=c.memory_id"
            if rows is None:
                rows = db.execute(
                    prefix+"visible AS MATERIALIZED (SELECT m.memory_id,m.payload_artifact_id,m.rowid AS ordinal FROM "
                    + memory_from + " CROSS JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE "
                    + where
                    + USER_NOTE_QUALIFICATION + ") "
                    "SELECT v.memory_id FROM visible v JOIN artifacts a ON a.artifact_id=v.payload_artifact_id WHERE ("
                    + match
                    + ") ORDER BY v.ordinal DESC LIMIT ?",
                    (*parameters, *args, *terms, limit),
                ).fetchall()
        except sqlite3.OperationalError as exc:
            if "interrupt" in str(exc).lower():
                raise CoreError("NOTE_RECALL_TIME_BOUND") from None
            raise
        finally:
            db.set_progress_handler(None, 0)
        result = []
        for row in rows:
            try:
                current = self.read(row["memory_id"])
            except CoreError:
                continue
            if is_user_note(current):
                result.append(current)
        return result

    def _short_note_candidates(self,where,args,coverage_hint,terms):
        clauses=[];values=[];exact=[]
        for term in terms:
            normalized=term.casefold()
            if len(normalized)>=3:
                exact.append(NOTE_GRAM_PREFIX+normalized[:3])
            else:
                prefix=NOTE_GRAM_PREFIX+normalized
                upper=_prefix_upper(prefix)
                if prefix<=NOTE_GRAM_COMPLETE<upper:
                    clauses.extend(('(term>=? AND term<?)','(term>? AND term<?)'))
                    values.extend((prefix,NOTE_GRAM_COMPLETE,NOTE_GRAM_COMPLETE,upper))
                else:
                    clauses.append('(term>=? AND term<?)');values.extend((prefix,upper))
                exact.append(NOTE_END_PREFIX+normalized)
        if exact:
            clauses.append('term IN ('+','.join('?' for _ in exact)+')');values.extend(exact)
        # A single end-key row is also per-payload coverage, including one-char
        # notes. No new table/index/version or eager history rebuild is needed.
        prefix=('WITH unindexed AS MATERIALIZED (SELECT m.memory_id FROM memories m'+coverage_hint+
            ' WHERE '+where+USER_NOTE_HEADER_QUALIFICATION+" AND m.memory_type='SEMANTIC' EXCEPT "
            'SELECT memory_id FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE term>=? AND term<?), '
            'candidate_ids AS MATERIALIZED (SELECT memory_id FROM unindexed UNION '
            'SELECT memory_id FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE '+' OR '.join(clauses)+'), ')
        return prefix,'candidate_ids c CROSS JOIN memories m ON m.memory_id=c.memory_id',[
            *args,NOTE_END_PREFIX,_prefix_upper(NOTE_END_PREFIX),*values],(' OR '.join(clauses),values)

    def _broad_note_matches(self,prefix,memory_from,parameters,posting,where,args,match,terms,limit):
        db=self.store.db;qualification=where+USER_NOTE_QUALIFICATION
        # Cardinality chooses a plan; 65 is not a recall/adoption/history limit.
        # Qualify source/role/scope/privacy before the probe, without reading text.
        clause,values=posting
        direct=db.execute('SELECT DISTINCT m.memory_id FROM memory_terms t INDEXED BY memory_terms_term_lookup '
            'CROSS JOIN memories m ON m.memory_id=t.memory_id CROSS JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id '
            'WHERE ('+clause+') AND '+qualification+' LIMIT 65',(*values,*args)).fetchall()
        probe=direct if len(direct)>=65 else db.execute(prefix[:-2]+' SELECT m.memory_id FROM '+memory_from+
            ' CROSS JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE '+qualification+' LIMIT 65',
            (*parameters,*args)).fetchall()
        if len(probe)<65:
            if not probe:return []
            ids=tuple(row['memory_id'] for row in probe)
            # The small qualified set is complete. Recheck sources before text,
            # without recomputing the full coverage/prefix candidate query.
            return db.execute('WITH visible AS MATERIALIZED (SELECT m.memory_id,m.payload_artifact_id,m.rowid AS ordinal FROM memories m '
                'CROSS JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE m.memory_id IN ('+
                ','.join('?' for _ in ids)+') AND '+qualification+') SELECT v.memory_id FROM visible v JOIN artifacts a '
                'ON a.artifact_id=v.payload_artifact_id WHERE ('+match+') ORDER BY v.ordinal DESC LIMIT ?',
                (*ids,*args,*terms,limit)).fetchall()
        # Broad literals should not materialize every payload. CASE is a real
        # short-circuit barrier: even reordered predicates cannot read a body
        # before the complete original authorization/source check. Ordering on
        # original rowid preserves the same newest-first exact result semantics.
        return db.execute('SELECT m.memory_id FROM memories m NOT INDEXED CROSS JOIN continuity_evidence e '
            'ON e.evidence_id=m.source_evidence_id WHERE '+qualification+' AND CASE WHEN ('+qualification+
            ') THEN coalesce((SELECT ('+match+') FROM artifacts a WHERE a.artifact_id=m.payload_artifact_id),0) ELSE 0 END '
            'ORDER BY m.rowid DESC LIMIT ?',(*args,*args,*terms,limit)).fetchall()

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
        row=self.store.one('memories',memory_id)
        if (row and row['memory_type']=='SEMANTIC' and row['epistemic_kind']=='STATEMENT'
                and row['authority']=='DIRECT' and (row['predicate_key'] or '').startswith('user-note.')
                and len(text)<=NOTE_GRAM_MAX_CHARS):
            normalized=text.casefold()
            terms.update(NOTE_GRAM_PREFIX+normalized[i:i+3] for i in range(max(0,len(normalized)-2)))
            terms.add(NOTE_GRAM_COMPLETE)
            terms.add(NOTE_END_PREFIX+normalized[-2:])
        self.store.db.executemany("INSERT OR IGNORE INTO memory_terms VALUES(?,?)",
                                 ((memory_id, t) for t in terms))

    def rebuild_index(self):
        self._fresh()
        db = self.store.db
        db.execute("SAVEPOINT rebuild_memory_terms")
        try:
            db.execute("DELETE FROM memory_terms")
            for memory_id, artifact_id in db.execute(
                "SELECT memory_id,payload_artifact_id FROM memories "
                "WHERE lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') ORDER BY rowid"
            ):
                self._index(memory_id, self.store.artifact(artifact_id).decode())
            db.execute("RELEASE rebuild_memory_terms")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK TO rebuild_memory_terms")
                db.execute("RELEASE rebuild_memory_terms")
            raise
