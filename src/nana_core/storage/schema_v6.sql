-- Bound retrieval before payload loading as long-lived memory grows.
CREATE INDEX memory_scope_visibility ON memories(scope,lifecycle,assessment,privacy_class,entity_id);
PRAGMA user_version=6;
