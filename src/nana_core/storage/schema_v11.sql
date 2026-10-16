-- Explicit living-runtime development opt-in; no new table.
CREATE TABLE continuity_records_new (
 record_id TEXT PRIMARY KEY,
 target_id TEXT,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON','SUBJECT_EVENT','SUBJECT_CYCLE','ASSERTION','ASSERTION_SIGNAL','RELATIONSHIP_EVENT','INTENTION','GOAL_CANDIDATE','REFLECTION','INTENTION_DISPOSITION','CONSTRAINT_OUTCOME','EXPERIENCE_CANDIDATE','SUBJECT_BOOTSTRAP','RUNTIME_WORK','ADOPTED_GOAL','AUTONOMOUS_PLAN','MAINTENANCE_CANDIDATE','MEMORY_VALIDITY','SKILL_PROPOSAL','ACTION_PAYLOAD')),
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
CREATE TABLE jobs_new (
 job_id TEXT PRIMARY KEY, occurrence_key TEXT NOT NULL UNIQUE, due_at_us INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('WAITING','RUNNING','PAUSED','DONE','BLOCKED','UNKNOWN','CANCELLED')),
 body_json TEXT NOT NULL CHECK(json_valid(body_json)),
 work_kind TEXT NOT NULL DEFAULT 'LEGACY', record_id TEXT REFERENCES continuity_records(record_id),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0), cursor INTEGER NOT NULL DEFAULT 0 CHECK(cursor>=0),
 owner_epoch INTEGER, updated_at_us INTEGER NOT NULL DEFAULT 0
);
INSERT INTO jobs_new(job_id,occurrence_key,due_at_us,state,body_json) SELECT * FROM jobs;
DROP TABLE jobs;
ALTER TABLE jobs_new RENAME TO jobs;
CREATE INDEX living_work_ready ON jobs(state,due_at_us,work_kind);
CREATE TABLE runtime_cognition_calls_new (
 call_id TEXT PRIMARY KEY, queue_id TEXT NOT NULL UNIQUE REFERENCES runtime_queue(queue_id),
 provider TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('RESERVED','SUCCEEDED','FAILED','UNKNOWN','TIMED_OUT','CANCELLED')),
 owner_epoch INTEGER NOT NULL, reserved_units INTEGER NOT NULL CHECK(reserved_units=1),
 input_bytes INTEGER, output_bytes INTEGER, actual_tokens INTEGER, actual_cost_micro INTEGER,
 started_at_us INTEGER NOT NULL, finished_at_us INTEGER,
 lane TEXT NOT NULL DEFAULT 'FOREGROUND' CHECK(lane IN ('FOREGROUND','BACKGROUND')),
 reserved_bytes INTEGER NOT NULL DEFAULT 0 CHECK(reserved_bytes>=0),
 reserved_cost_micro INTEGER NOT NULL DEFAULT 0 CHECK(reserved_cost_micro>=0),
 accounting TEXT NOT NULL DEFAULT 'ESTIMATED_UPPER_BOUND', wall_latency_us INTEGER
);
INSERT INTO runtime_cognition_calls_new(call_id,queue_id,provider,state,owner_epoch,reserved_units,input_bytes,output_bytes,actual_tokens,actual_cost_micro,started_at_us,finished_at_us)
SELECT * FROM runtime_cognition_calls;
DROP TABLE runtime_cognition_calls;
ALTER TABLE runtime_cognition_calls_new RENAME TO runtime_cognition_calls;
CREATE TABLE subject_goal_candidates_new (
 candidate_id TEXT PRIMARY KEY,
 intention_id TEXT NOT NULL UNIQUE REFERENCES subject_intentions(intention_id),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 state TEXT NOT NULL CHECK(state IN ('PROPOSED','DEFERRED','WITHDRAWN','EXPIRED','ADOPTED'))
);
INSERT INTO subject_goal_candidates_new SELECT * FROM subject_goal_candidates;
DROP TABLE subject_goal_candidates;
ALTER TABLE subject_goal_candidates_new RENAME TO subject_goal_candidates;
PRAGMA user_version=11;
