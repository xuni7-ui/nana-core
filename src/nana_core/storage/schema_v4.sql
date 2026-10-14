-- Revision payloads are typed by the owning service, referenced and deletable.
CREATE TABLE continuity_records (
 record_id TEXT PRIMARY KEY,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON')),
 scope TEXT NOT NULL,
 privacy_class TEXT NOT NULL CHECK(privacy_class IN ('PUBLIC','PROJECT','PERSONAL','SECRET')),
 payload_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('ACTIVE','SUPERSEDED','DELETED')),
 created_at_us INTEGER NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE record_dependencies (
 link_id TEXT PRIMARY KEY,
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 parent_kind TEXT NOT NULL CHECK(parent_kind IN ('MEMORY','RECORD')),
 parent_id TEXT NOT NULL,
 relation_kind TEXT NOT NULL CHECK(relation_kind IN ('SUPPORT','REVISION')),
 UNIQUE(record_id,parent_kind,parent_id)
);
CREATE TABLE commitments (
 commitment_id TEXT PRIMARY KEY,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 scope TEXT NOT NULL,
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 revision INTEGER NOT NULL CHECK(revision>=1),
 state TEXT NOT NULL CHECK(state IN ('PROPOSED','ADOPTED','ACTIVE','FULFILLED','CANCELLED','FAILED','SUPERSEDED')),
 due_at_us INTEGER,
 adoption_event_id TEXT REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED,
 fulfillment_memory_id TEXT REFERENCES memories(memory_id),
 superseded_by TEXT REFERENCES commitments(commitment_id) DEFERRABLE INITIALLY DEFERRED,
 created_at_us INTEGER NOT NULL,
 updated_at_us INTEGER NOT NULL
);
CREATE TABLE projects (
 project_id TEXT PRIMARY KEY,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 scope TEXT NOT NULL,
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 revision INTEGER NOT NULL CHECK(revision>=1),
 state TEXT NOT NULL CHECK(state IN ('ACTIVE','PAUSED','COMPLETED','ARCHIVED')),
 created_at_us INTEGER NOT NULL,
 updated_at_us INTEGER NOT NULL
);
PRAGMA user_version=4;
