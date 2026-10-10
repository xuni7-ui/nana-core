-- Only tables used by S0-S4. Evidence and event log are authoritative;
-- the remaining tables are deterministic projections of recorded changes.
CREATE TABLE core_meta (key TEXT PRIMARY KEY, value_json TEXT NOT NULL CHECK(json_valid(value_json)));
CREATE TABLE events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT,
 event_id TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL,
 schema_version INTEGER NOT NULL CHECK(schema_version=1),
 identity_id TEXT,
 source_namespace TEXT,
 source_key TEXT,
 occurred_at_us INTEGER,
 observed_at_us INTEGER NOT NULL,
 recorded_at_us INTEGER NOT NULL,
 data_json TEXT NOT NULL CHECK(json_valid(data_json)),
 artifact_id TEXT REFERENCES artifacts(artifact_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(source_namespace,source_key)
);
CREATE TABLE artifacts (
 artifact_id TEXT PRIMARY KEY,
 sha256 TEXT NOT NULL,
 payload BLOB,
 completeness TEXT NOT NULL CHECK(completeness IN ('COMPLETE','UNAVAILABLE')),
 created_event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE identities (
 identity_id TEXT PRIMARY KEY,
 revision INTEGER NOT NULL CHECK(revision>=1),
 body_json TEXT NOT NULL CHECK(json_valid(body_json)),
 created_event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE memory_items (
 memory_id TEXT PRIMARY KEY,
 kind TEXT NOT NULL CHECK(kind IN ('CLAIM','EPISODE')),
 status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETRACTED','UNAVAILABLE')),
 body_json TEXT NOT NULL CHECK(json_valid(body_json)),
 created_event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE goals (
 goal_id TEXT PRIMARY KEY,
 goal_key TEXT NOT NULL UNIQUE,
 event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id),
 template TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PROPOSED','ACTIVE','BLOCKED','COMPLETED','FAILED','ABANDONED','REJECTED')),
 version INTEGER NOT NULL,
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE UNIQUE INDEX one_live_goal ON goals((1)) WHERE state IN ('PROPOSED','ACTIVE','BLOCKED');
CREATE TABLE plans (
 plan_id TEXT PRIMARY KEY,
 goal_id TEXT NOT NULL UNIQUE REFERENCES goals(goal_id),
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE TABLE decisions (
 decision_id TEXT PRIMARY KEY,
 goal_id TEXT NOT NULL REFERENCES goals(goal_id),
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE TABLE grants (
 grant_id TEXT PRIMARY KEY,
 issuer TEXT NOT NULL,
 identity_id TEXT NOT NULL REFERENCES identities(identity_id),
 not_before_us INTEGER NOT NULL,
 expires_at_us INTEGER NOT NULL CHECK(expires_at_us>not_before_us),
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE TABLE budgets (
 dimension TEXT PRIMARY KEY CHECK(dimension IN ('write_attempts','external_requests','cost_micro_units')),
 limit_value INTEGER NOT NULL CHECK(limit_value>=0),
 held INTEGER NOT NULL CHECK(held>=0),
 spent INTEGER NOT NULL CHECK(spent>=0),
 CHECK(held+spent<=limit_value)
);
CREATE TABLE actions (
 action_id TEXT PRIMARY KEY,
 goal_id TEXT REFERENCES goals(goal_id),
 plan_id TEXT REFERENCES plans(plan_id),
 effect_slot TEXT,
 idempotency_key TEXT NOT NULL UNIQUE,
 capability TEXT NOT NULL,
 resource TEXT NOT NULL,
 args_json TEXT NOT NULL CHECK(json_valid(args_json)),
 args_hash TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PROPOSED','BLOCKED','READY','DISPATCHING','PENDING_VERIFY','UNKNOWN','SUCCEEDED','NOT_APPLIED','FAILED_EFFECT','CANCELLED')),
 version INTEGER NOT NULL,
 attempt_id TEXT,
 result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)),
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE UNIQUE INDEX one_possible_effect ON actions(effect_slot) WHERE effect_slot IS NOT NULL AND state NOT IN ('CANCELLED','NOT_APPLIED');
CREATE TABLE attempts (
 attempt_id TEXT PRIMARY KEY,
 action_id TEXT NOT NULL REFERENCES actions(action_id),
 grant_id TEXT NOT NULL REFERENCES grants(grant_id),
 kind TEXT NOT NULL CHECK(kind IN ('EXECUTE','VERIFY')),
 attempt_no INTEGER NOT NULL,
 started_at_us INTEGER,
 outcome TEXT,
 receipt_event_id TEXT REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED,
 verification_event_id TEXT REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(action_id,attempt_no)
);
CREATE TABLE budget_holds (
 hold_id TEXT PRIMARY KEY,
 owner_id TEXT NOT NULL REFERENCES attempts(attempt_id),
 dimension TEXT NOT NULL REFERENCES budgets(dimension),
 amount INTEGER NOT NULL CHECK(amount>=0),
 status TEXT NOT NULL CHECK(status IN ('HELD','SPENT','RELEASED')),
 UNIQUE(owner_id,dimension)
);
CREATE TABLE strategies (
 strategy_id TEXT PRIMARY KEY,
 revision INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('CANDIDATE','TESTED','ACTIVE','REJECTED','SUSPENDED','RETIRED')),
 feedback_event_id TEXT NOT NULL REFERENCES events(event_id),
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE TABLE jobs (
 job_id TEXT PRIMARY KEY,
 occurrence_key TEXT NOT NULL UNIQUE,
 due_at_us INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('WAITING','DONE')),
 body_json TEXT NOT NULL CHECK(json_valid(body_json))
);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only events'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only events'); END;
PRAGMA user_version=1;
