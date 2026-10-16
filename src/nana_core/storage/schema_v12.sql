-- Explicit living-runtime development opt-in; no new table.
CREATE TABLE continuity_records_new (
 record_id TEXT PRIMARY KEY,
 target_id TEXT,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('COMMITMENT','PROJECT','EXPERIENCE','LESSON','SUBJECT_EVENT','SUBJECT_CYCLE','ASSERTION','ASSERTION_SIGNAL','RELATIONSHIP_EVENT','INTENTION','GOAL_CANDIDATE','REFLECTION','INTENTION_DISPOSITION','CONSTRAINT_OUTCOME','EXPERIENCE_CANDIDATE','SUBJECT_BOOTSTRAP','RUNTIME_WORK','ADOPTED_GOAL','AUTONOMOUS_PLAN','MAINTENANCE_CANDIDATE','MEMORY_VALIDITY','SKILL_PROPOSAL','ACTION_PAYLOAD','OPEN_LEARNING','LEARNING_TRIAL','CODE_SKILL','DELIVERY_DECISION','WORLD_OBSERVATION','OPEN_STRATEGY')),
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
-- Multiple bounded goals are an explicit opt-in; legacy schemas retain their index.
DROP INDEX one_live_goal;
CREATE TABLE goals_new (
 goal_id TEXT PRIMARY KEY, goal_key TEXT NOT NULL UNIQUE,
 event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id), template TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PROPOSED','ACTIVE','SUSPENDED','BLOCKED','COMPLETED','FAILED','ABANDONED','REJECTED')),
 version INTEGER NOT NULL, body_json TEXT NOT NULL CHECK(json_valid(body_json)),
 priority INTEGER NOT NULL DEFAULT 1 CHECK(priority BETWEEN 0 AND 3),
 deadline_us INTEGER, parent_id TEXT REFERENCES goals(goal_id),
 depends_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(depends_json)),
 last_served_us INTEGER NOT NULL DEFAULT 0
);
INSERT INTO goals_new(goal_id,goal_key,event_id,template,state,version,body_json)
 SELECT goal_id,goal_key,event_id,template,state,version,body_json FROM goals;
DROP TABLE goals;
ALTER TABLE goals_new RENAME TO goals;
CREATE INDEX open_goal_attention ON goals(state,priority,deadline_us,last_served_us);
PRAGMA user_version=12;
