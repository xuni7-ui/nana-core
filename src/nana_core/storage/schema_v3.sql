-- Payloads only in artifacts, never replicated into immutable event JSON.
CREATE TABLE entities (
 entity_id TEXT PRIMARY KEY,
 entity_type TEXT NOT NULL CHECK(entity_type IN ('PERSON','SELF','PROJECT','OBJECT')),
 created_at_us INTEGER NOT NULL
);
CREATE TABLE continuity_evidence (
 evidence_id TEXT PRIMARY KEY,
 source_namespace TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 source_revision TEXT NOT NULL,
 source_kind TEXT NOT NULL CHECK(source_kind IN
 ('USER_STATEMENT','DIRECT_OBSERVATION','MODEL_DERIVATION','SYSTEM_VERIFICATION')),
 provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json)),
 privacy_class TEXT NOT NULL CHECK(privacy_class IN ('PUBLIC','PROJECT','PERSONAL','SECRET')),
 payload_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
 event_time_us INTEGER,
 observed_time_us INTEGER NOT NULL,
 ingested_time_us INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('AVAILABLE','DELETED')),
 event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(source_namespace,source_reference,source_revision)
);
CREATE TABLE memories (
 memory_id TEXT PRIMARY KEY,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 scope TEXT NOT NULL,
 memory_type TEXT NOT NULL CHECK(memory_type IN
 ('EPISODIC','SEMANTIC','RELATIONAL','SELF','PROCEDURAL','PROSPECTIVE','PROJECT')),
 epistemic_kind TEXT NOT NULL CHECK(epistemic_kind IN
 ('OBSERVATION','STATEMENT','BELIEF','SUMMARY','INFERENCE','LESSON')),
 source_evidence_id TEXT NOT NULL REFERENCES continuity_evidence(evidence_id),
 payload_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
 predicate_key TEXT,
 event_time_us INTEGER,
 observed_time_us INTEGER NOT NULL,
 ingested_time_us INTEGER NOT NULL,
 confidence REAL NOT NULL CHECK(confidence>=0 AND confidence<=1),
 authority TEXT NOT NULL CHECK(authority IN ('DIRECT','INFERRED','UNASSESSED')),
 importance REAL NOT NULL CHECK(importance>=0 AND importance<=1),
 significance REAL NOT NULL CHECK(significance>=0 AND significance<=1),
 privacy_class TEXT NOT NULL CHECK(privacy_class IN ('PUBLIC','PROJECT','PERSONAL','SECRET')),
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('ACTIVE','SUPPRESSED','ARCHIVED','DELETED')),
 assessment TEXT NOT NULL CHECK(assessment IN
 ('UNASSESSED','CURRENT','DISPUTED','SUPERSEDED','WITHDRAWN')),
 correction_of TEXT REFERENCES memories(memory_id) DEFERRABLE INITIALLY DEFERRED,
 superseded_by TEXT REFERENCES memories(memory_id) DEFERRABLE INITIALLY DEFERRED,
 created_at_us INTEGER NOT NULL,
 updated_at_us INTEGER NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX memory_family ON memories(entity_id,scope,predicate_key,assessment,lifecycle);
CREATE TABLE memory_dependencies (
 link_id TEXT PRIMARY KEY,
 memory_id TEXT NOT NULL REFERENCES memories(memory_id),
 parent_kind TEXT NOT NULL CHECK(parent_kind IN ('EVIDENCE','MEMORY')),
 parent_id TEXT NOT NULL,
 UNIQUE(memory_id,parent_kind,parent_id)
);
-- Derived search projection: intentionally not event-sourced (rebuild after purge).
CREATE TABLE memory_terms (
 memory_id TEXT NOT NULL REFERENCES memories(memory_id),
 term TEXT NOT NULL,
 PRIMARY KEY(memory_id,term)
);
PRAGMA user_version=3;
