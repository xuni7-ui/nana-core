-- Explicit opt-in; existing tables only. Parent rebuild preserves IDs/FKs.
CREATE TABLE continuity_records_new (
 record_id TEXT PRIMARY KEY,
 target_id TEXT,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON','SUBJECT_EVENT','SUBJECT_CYCLE','ASSERTION','ASSERTION_SIGNAL','RELATIONSHIP_EVENT','INTENTION','GOAL_CANDIDATE','REFLECTION','INTENTION_DISPOSITION','CONSTRAINT_OUTCOME','EXPERIENCE_CANDIDATE','SUBJECT_BOOTSTRAP')),
 scope TEXT NOT NULL,
 privacy_class TEXT NOT NULL CHECK(privacy_class IN ('PUBLIC','PROJECT','PERSONAL','SECRET')),
 payload_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('ACTIVE','SUPERSEDED','DELETED')),
 created_at_us INTEGER NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO continuity_records_new(record_id,target_id,record_kind,scope,privacy_class,payload_artifact_id,lifecycle,created_at_us,event_id) SELECT record_id,target_id,record_kind,scope,privacy_class,payload_artifact_id,lifecycle,created_at_us,event_id FROM continuity_records;
DROP TABLE continuity_records;
ALTER TABLE continuity_records_new RENAME TO continuity_records;
CREATE TABLE self_assertions_new (
 assertion_id TEXT PRIMARY KEY,
 assertion_kind TEXT NOT NULL CHECK(assertion_kind IN ('PREFERENCE','SELF_BELIEF','PERSONALITY_TENDENCY')),
 topic_key TEXT NOT NULL,
 scope TEXT NOT NULL,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 revision INTEGER NOT NULL CHECK(revision>0),
 state TEXT NOT NULL CHECK(state IN ('CANDIDATE','ADOPTED','DISPUTED','SUPERSEDED')),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 updated_at_us INTEGER NOT NULL,
 UNIQUE(assertion_kind,topic_key,scope,entity_id)
);
INSERT INTO self_assertions_new SELECT * FROM self_assertions;
DROP TABLE self_assertions;
ALTER TABLE self_assertions_new RENAME TO self_assertions;
CREATE INDEX autonomy_record_lookup ON continuity_records(record_kind,scope,created_at_us DESC);
CREATE INDEX autonomy_record_target ON continuity_records(record_kind,target_id,created_at_us DESC);
CREATE UNIQUE INDEX relational_request_identity ON continuity_records(target_id) WHERE record_kind='SUBJECT_EVENT' AND target_id LIKE 'relational-request:%';
PRAGMA user_version=10;
