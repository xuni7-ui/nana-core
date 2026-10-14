-- Canonical identity is the original identities row; revisions are its history.
CREATE TABLE identity_revisions (
 revision_id TEXT PRIMARY KEY,
 identity_id TEXT NOT NULL REFERENCES identities(identity_id),
 revision INTEGER NOT NULL CHECK(revision>=1),
 schema_version INTEGER NOT NULL CHECK(schema_version=1),
 supersedes TEXT REFERENCES identity_revisions(revision_id),
 body_json TEXT NOT NULL CHECK(json_valid(body_json)),
 provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json)),
 authority TEXT NOT NULL CHECK(authority IN ('BOOTSTRAP','OPERATOR_REVIEW')),
 reason_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
 created_at_us INTEGER NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(event_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(identity_id,revision)
);
PRAGMA user_version=2;

