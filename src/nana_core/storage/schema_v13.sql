-- Explicit living-runtime development opt-in; no new table.
CREATE TABLE continuity_records_new (
 record_id TEXT PRIMARY KEY,
 target_id TEXT,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON','SUBJECT_EVENT','SUBJECT_CYCLE','ASSERTION','ASSERTION_SIGNAL','RELATIONSHIP_EVENT','INTENTION','GOAL_CANDIDATE','REFLECTION','INTENTION_DISPOSITION','CONSTRAINT_OUTCOME','EXPERIENCE_CANDIDATE','SUBJECT_BOOTSTRAP','RUNTIME_WORK','ADOPTED_GOAL','AUTONOMOUS_PLAN','MAINTENANCE_CANDIDATE','MEMORY_VALIDITY','SKILL_PROPOSAL','ACTION_PAYLOAD','OPEN_LEARNING','LEARNING_TRIAL','CODE_SKILL','DELIVERY_DECISION','WORLD_OBSERVATION','COGNITION_REQUEST','COGNITION_PROPOSAL','WORLD_BELIEF','OPEN_CONCERN','MEDIA_OBSERVATION','STRATEGY_REVIEW')),
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
CREATE INDEX autonomy_record_lookup ON continuity_records(record_kind,scope,created_at_us DESC);
CREATE INDEX autonomy_record_target ON continuity_records(record_kind,target_id,created_at_us DESC);
CREATE UNIQUE INDEX relational_request_identity ON continuity_records(target_id) WHERE record_kind='SUBJECT_EVENT' AND target_id LIKE 'relational-request:%';

-- Indexed operational headers only; erasable content lives in continuity_records.
CREATE TABLE cognitive_requests (
 request_id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 subject_revision INTEGER NOT NULL, owner_epoch INTEGER NOT NULL,
 goal_id TEXT REFERENCES goals(goal_id), goal_version INTEGER,
 state TEXT NOT NULL CHECK(state IN ('PREPARED','CALLING','PROPOSED','FAILED','UNKNOWN','STALE','REJECTED')),
 deadline_us INTEGER NOT NULL, request_digest TEXT NOT NULL,
 response_digest TEXT, error_code TEXT, created_at_us INTEGER NOT NULL
);
CREATE INDEX cognition_pending ON cognitive_requests(state,deadline_us);
CREATE TABLE world_beliefs (
 belief_id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 scope TEXT NOT NULL,
 entity_id TEXT NOT NULL REFERENCES entities(entity_id), predicate_key TEXT NOT NULL,
 revision INTEGER NOT NULL, epistemic_kind TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('CURRENT','CONFLICT','UNKNOWN','SUPERSEDED')),
 valid_from_us INTEGER NOT NULL, valid_until_us INTEGER,
 known_at_us INTEGER NOT NULL, replaces TEXT REFERENCES world_beliefs(belief_id),
 UNIQUE(scope,entity_id,predicate_key,revision)
);
CREATE INDEX world_current ON world_beliefs(scope,entity_id,predicate_key,known_at_us DESC);
CREATE TABLE open_concerns (
 concern_id TEXT PRIMARY KEY, concern_key TEXT NOT NULL UNIQUE,
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 state TEXT NOT NULL CHECK(state IN ('TRANSIENT','INTEREST','PROPOSED','ADOPTED','DEFERRED','ABANDONED','EXPIRED')),
 revision INTEGER NOT NULL, encounters INTEGER NOT NULL,
 next_review_us INTEGER NOT NULL, updated_at_us INTEGER NOT NULL,
 goal_id TEXT REFERENCES goals(goal_id)
);
CREATE INDEX concern_attention ON open_concerns(state,next_review_us,updated_at_us);
CREATE TABLE strategy_assessments (
 assessment_id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 episode_key TEXT NOT NULL, verdict TEXT NOT NULL CHECK(verdict IN ('SUCCESS','COUNTEREXAMPLE','UNKNOWN')),
 context_digest TEXT NOT NULL, created_at_us INTEGER NOT NULL,
 UNIQUE(lesson_id,episode_key)
);
CREATE INDEX strategy_history ON strategy_assessments(lesson_id,created_at_us DESC);
PRAGMA user_version=13;
