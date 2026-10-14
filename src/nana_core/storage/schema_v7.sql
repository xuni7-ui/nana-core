-- Explicit development-only parent rebuild; install() controls the FK fence.
CREATE TABLE entities_new (
 entity_id TEXT PRIMARY KEY,
 entity_type TEXT NOT NULL CHECK(entity_type IN ('SELF','PERSON','PROJECT','OBJECT','GROUP','COMMUNITY','AGENT')),
 created_at_us INTEGER NOT NULL
);
INSERT INTO entities_new SELECT * FROM entities;
DROP TABLE entities;
ALTER TABLE entities_new RENAME TO entities;
CREATE TABLE continuity_records_new (
 record_id TEXT PRIMARY KEY,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON','SUBJECT_EVENT','SUBJECT_CYCLE','ASSERTION','ASSERTION_SIGNAL','RELATIONSHIP_EVENT','INTENTION','GOAL_CANDIDATE','REFLECTION')),
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
CREATE TABLE subject_events (
 subject_event_id TEXT PRIMARY KEY,
 source_key TEXT NOT NULL UNIQUE,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 scope TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('INTERACTION','PROJECT','PLAY','OUTCOME','WAKE','RELATIONSHIP','REFLECTION')),
 origin TEXT NOT NULL CHECK(origin IN ('USER','ENVIRONMENT','SELF_WAKE')),
 record_id TEXT REFERENCES continuity_records(record_id),
 memory_id TEXT REFERENCES memories(memory_id),
 occurred_at_us INTEGER,
 observed_at_us INTEGER NOT NULL,
 ingested_at_us INTEGER NOT NULL,
 admission TEXT NOT NULL CHECK(admission IN ('KEEP','MERGE','TEMPORARY','IGNORE','FORGET_LATER'))
);
CREATE TABLE subject_cycles (
 cycle_id TEXT PRIMARY KEY,
 subject_event_id TEXT NOT NULL UNIQUE REFERENCES subject_events(subject_event_id),
 revision INTEGER NOT NULL UNIQUE CHECK(revision>0),
 record_id TEXT REFERENCES continuity_records(record_id),
 judgment TEXT NOT NULL CHECK(judgment IN ('AGREE','PARTIAL_AGREE','DISAGREE','ALTERNATIVE','IGNORE','WATCH','REMEMBER','ASK','THINK_MORE','DEFER','REFLECT')),
 attention TEXT NOT NULL CHECK(attention IN ('FOCUS_NOW','BACKGROUND_WATCH','DEFER','IGNORE','RECALL_LATER')),
 barrier TEXT NOT NULL CHECK(barrier IN ('NO_ACTION','SHADOW_BLOCKED')),
 created_at_us INTEGER NOT NULL
);
CREATE TABLE self_assertions (
 assertion_id TEXT PRIMARY KEY,
 assertion_kind TEXT NOT NULL CHECK(assertion_kind IN ('PREFERENCE','SELF_BELIEF')),
 topic_key TEXT NOT NULL,
 scope TEXT NOT NULL,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 revision INTEGER NOT NULL CHECK(revision>0),
 state TEXT NOT NULL CHECK(state IN ('CANDIDATE','ADOPTED','DISPUTED','SUPERSEDED')),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 updated_at_us INTEGER NOT NULL,
 UNIQUE(assertion_kind,topic_key,scope,entity_id)
);
CREATE TABLE assertion_signals (
 signal_id TEXT PRIMARY KEY,
 assertion_id TEXT NOT NULL REFERENCES self_assertions(assertion_id),
 subject_event_id TEXT NOT NULL REFERENCES subject_events(subject_event_id),
 direction TEXT NOT NULL CHECK(direction IN ('SUPPORT','COUNTER')),
 root_evidence_id TEXT NOT NULL REFERENCES continuity_evidence(evidence_id),
 independent INTEGER NOT NULL CHECK(independent IN (0,1)),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 created_at_us INTEGER NOT NULL,
 UNIQUE(assertion_id,subject_event_id)
);
CREATE TABLE relationship_events (
 relationship_event_id TEXT PRIMARY KEY,
 subject_event_id TEXT NOT NULL UNIQUE REFERENCES subject_events(subject_event_id),
 from_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 to_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
 relation_kind TEXT NOT NULL CHECK(relation_kind IN ('SHARED_HISTORY','SHARED_PROJECT','SHARED_JOKE','NORM','BOUNDARY','CONFLICT','REPAIR','TRUST','COMMITMENT')),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 occurred_at_us INTEGER NOT NULL
);
CREATE TABLE subject_intentions (
 intention_id TEXT PRIMARY KEY,
 subject_event_id TEXT NOT NULL REFERENCES subject_events(subject_event_id),
 scope TEXT NOT NULL,
 slot_key TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('NO_ACTION','SOCIAL_INTERACTION','MEMORY_CANDIDATE','REFLECTION','GOAL_CANDIDATE','ACTION_PROPOSAL','WAIT','EXPLORE','DISAGREE')),
 state TEXT NOT NULL CHECK(state IN ('PENDING','COMPLETED','DEFERRED','DROPPED','EXPIRED')),
 revision INTEGER NOT NULL CHECK(revision>0),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 created_at_us INTEGER NOT NULL,
 expires_at_us INTEGER NOT NULL
);
CREATE UNIQUE INDEX subject_intention_live_slot ON subject_intentions(scope,slot_key) WHERE state='PENDING';
CREATE TABLE subject_goal_candidates (
 candidate_id TEXT PRIMARY KEY,
 intention_id TEXT NOT NULL UNIQUE REFERENCES subject_intentions(intention_id),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 state TEXT NOT NULL CHECK(state IN ('PROPOSED','DEFERRED','WITHDRAWN','EXPIRED'))
);
CREATE TABLE subject_reflections (
 reflection_id TEXT PRIMARY KEY,
 experience_id TEXT NOT NULL UNIQUE REFERENCES experiences(experience_id),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 state TEXT NOT NULL CHECK(state IN ('CANDIDATE','APPLIED','REJECTED')),
 revision INTEGER NOT NULL CHECK(revision>0),
 lesson_id TEXT REFERENCES lessons(lesson_id),
 created_at_us INTEGER NOT NULL
);
CREATE INDEX subject_current_intentions ON subject_intentions(scope,state,expires_at_us);
CREATE INDEX subject_assertion_roots ON assertion_signals(assertion_id,root_evidence_id);
PRAGMA user_version=7;
