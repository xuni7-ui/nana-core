-- Operational runtime state shares the authoritative Store, not another DB.
CREATE TABLE runtime_lease (
 identity_id TEXT PRIMARY KEY REFERENCES identities(identity_id),
 instance_id TEXT NOT NULL,
 epoch INTEGER NOT NULL CHECK(epoch>=1),
 state TEXT NOT NULL CHECK(state IN ('ACTIVE','STOPPED','LOST')),
 pid INTEGER NOT NULL,
 process_start TEXT NOT NULL,
 boot_id TEXT NOT NULL,
 acquired_at_us INTEGER NOT NULL,
 heartbeat_at_us INTEGER NOT NULL,
 expires_at_us INTEGER NOT NULL,
 clock_high_water_us INTEGER NOT NULL
);
CREATE TABLE runtime_queue (
 queue_id TEXT PRIMARY KEY,
 source_key TEXT NOT NULL UNIQUE,
 sequence_no INTEGER NOT NULL UNIQUE,
 event_type TEXT NOT NULL CHECK(event_type IN ('USER_EVENT','TIME_EVENT','WORLD_EVENT','DEVICE_EVENT','PLATFORM_EVENT','PROJECT_EVENT','RELATIONSHIP_EVENT','GOAL_EVENT','SELF_EVENT','REFLECTION_EVENT','CAPABILITY_EVENT')),
 wake_trigger TEXT NOT NULL CHECK(wake_trigger IN ('INCOMING_EVENT','TIME_TRIGGER','GOAL_TRIGGER','ANOMALY','RELATIONSHIP_TRIGGER','SELF_TRIGGER','REFLECTION_TRIGGER','DEVICE_TRIGGER','ENVIRONMENT_CHANGE')),
 subject_event_id TEXT REFERENCES subject_events(subject_event_id),
 record_id TEXT REFERENCES continuity_records(record_id),
 metadata_json TEXT NOT NULL,
 cause_json TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('READY','DEFERRED','PROCESSING','DONE','IGNORED','EXPIRED')),
 priority INTEGER NOT NULL CHECK(priority BETWEEN 0 AND 3),
 due_at_us INTEGER NOT NULL,
 expires_at_us INTEGER,
 owner_epoch INTEGER,
 cycle_id TEXT REFERENCES subject_cycles(cycle_id),
 outcome_code TEXT,
 stream_key TEXT,
 source_sequence INTEGER,
 attempts INTEGER NOT NULL CHECK(attempts>=0),
 created_at_us INTEGER NOT NULL,
 updated_at_us INTEGER NOT NULL,
 UNIQUE(stream_key,source_sequence)
);
CREATE INDEX runtime_ready ON runtime_queue(state,due_at_us,priority,sequence_no);
CREATE TABLE runtime_schedules (
 schedule_id TEXT PRIMARY KEY,
 dedupe_key TEXT NOT NULL UNIQUE,
 state TEXT NOT NULL CHECK(state IN ('ACTIVE','FIRED','CANCELLED')),
 schedule_kind TEXT NOT NULL CHECK(schedule_kind IN ('ONE_SHOT','DEADLINE','PERIODIC','CONDITION')),
 due_at_us INTEGER NOT NULL,
 interval_us INTEGER,
 template_json TEXT NOT NULL,
 last_queue_id TEXT REFERENCES runtime_queue(queue_id),
 occurrence INTEGER NOT NULL CHECK(occurrence>=0),
 created_at_us INTEGER NOT NULL
);
CREATE INDEX runtime_due ON runtime_schedules(state,due_at_us);
CREATE TABLE runtime_cognition_calls (
 call_id TEXT PRIMARY KEY,
 queue_id TEXT NOT NULL UNIQUE REFERENCES runtime_queue(queue_id),
 provider TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('RESERVED','SUCCEEDED','FAILED','UNKNOWN','TIMED_OUT')),
 owner_epoch INTEGER NOT NULL,
 reserved_units INTEGER NOT NULL CHECK(reserved_units=1),
 input_bytes INTEGER,
 output_bytes INTEGER,
 actual_tokens INTEGER,
 actual_cost_micro INTEGER,
 started_at_us INTEGER NOT NULL,
 finished_at_us INTEGER
);
PRAGMA user_version=8;
