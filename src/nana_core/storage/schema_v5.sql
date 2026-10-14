CREATE TABLE experiences (
 experience_id TEXT PRIMARY KEY,
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 task_class TEXT NOT NULL,
 result_memory_id TEXT NOT NULL REFERENCES memories(memory_id),
 verification_memory_id TEXT NOT NULL REFERENCES memories(memory_id),
 outcome TEXT NOT NULL CHECK(outcome IN ('SUCCESS','FAILURE')),
 created_at_us INTEGER NOT NULL
);
CREATE TABLE lessons (
 lesson_id TEXT PRIMARY KEY,
 experience_id TEXT NOT NULL REFERENCES experiences(experience_id),
 record_id TEXT NOT NULL REFERENCES continuity_records(record_id),
 task_class TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision>=1),
 state TEXT NOT NULL CHECK(state IN ('CANDIDATE','TESTED','ACTIVE','SUSPENDED','RETIRED','REJECTED')),
 tested_rule_hash TEXT,
 test_event_id TEXT REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(experience_id)
);
PRAGMA user_version=5;
