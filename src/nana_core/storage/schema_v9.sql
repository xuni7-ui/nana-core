-- Explicit opt-in; existing tables only. Parent rebuild preserves IDs/FKs.
CREATE TABLE continuity_records_new (
 record_id TEXT PRIMARY KEY,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON','SUBJECT_EVENT','SUBJECT_CYCLE','ASSERTION','ASSERTION_SIGNAL','RELATIONSHIP_EVENT','INTENTION','GOAL_CANDIDATE','REFLECTION','INTENTION_DISPOSITION','CONSTRAINT_OUTCOME','EXPERIENCE_CANDIDATE')),
 scope TEXT NOT NULL,
 privacy_class TEXT NOT NULL CHECK(privacy_class IN ('PUBLIC','PROJECT','PERSONAL','SECRET')),
 payload_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('ACTIVE','SUPERSEDED','DELETED')),
 created_at_us INTEGER NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO continuity_records_new SELECT * FROM continuity_records;
DROP TABLE continuity_records;
ALTER TABLE continuity_records_new RENAME TO continuity_records;
CREATE TABLE subject_intentions_new (
 intention_id TEXT PRIMARY KEY,
 subject_event_id TEXT NOT NULL REFERENCES subject_events(subject_event_id),
 scope TEXT NOT NULL,
 slot_key TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('NO_ACTION','SOCIAL_INTERACTION','MEMORY_CANDIDATE','REFLECTION','GOAL_CANDIDATE','ACTION_PROPOSAL','WAIT','EXPLORE','DISAGREE')),
 state TEXT NOT NULL CHECK(state IN ('PENDING','COMPLETED','DEFERRED','DROPPED','EXPIRED','MANAGER_BLOCKED','MANAGER_UNKNOWN')),
 revision INTEGER NOT NULL CHECK(revision>0),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 created_at_us INTEGER NOT NULL,
 expires_at_us INTEGER NOT NULL
);
INSERT INTO subject_intentions_new SELECT * FROM subject_intentions;
DROP TABLE subject_intentions;
ALTER TABLE subject_intentions_new RENAME TO subject_intentions;
CREATE UNIQUE INDEX subject_intention_live_slot ON subject_intentions(scope,slot_key) WHERE state='PENDING';
CREATE INDEX subject_current_intentions ON subject_intentions(scope,state,expires_at_us);

CREATE INDEX autonomy_event_lookup ON events(kind,json_extract(data_json,'$.data.target_id'),seq DESC);
CREATE INDEX autonomy_record_lookup ON continuity_records(record_kind,scope,created_at_us DESC);
CREATE INDEX autonomy_relationship_lookup ON relationship_events(to_entity_id,occurred_at_us DESC);
ALTER TABLE relationship_events ADD COLUMN related_event_id TEXT REFERENCES relationship_events(relationship_event_id);
ALTER TABLE relationship_events ADD COLUMN relation_domain TEXT;
ALTER TABLE relationship_events ADD COLUMN relation_effect TEXT;
PRAGMA user_version=9;
