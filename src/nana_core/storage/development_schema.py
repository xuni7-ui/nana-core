"""Explicit, forward-only development migrations. Default v1 Store stays frozen.

These schemas are not an authorization to upgrade any deployed Store. A rollback
uses a pre-upgrade snapshot in quarantine; it never down-converts new history.
"""
from pathlib import Path

from ..contracts import CoreError

LATEST = 13
EXTENSION_KEYS = {
    2: {"identity_revisions": "revision_id"},
    3: {"entities": "entity_id", "continuity_evidence": "evidence_id",
        "memories": "memory_id", "memory_dependencies": "link_id"},
    4: {"continuity_records": "record_id", "record_dependencies": "link_id",
        "commitments": "commitment_id", "projects": "project_id"},
    5: {"experiences": "experience_id", "lessons": "lesson_id"},
    7: {"subject_events": "subject_event_id", "subject_cycles": "cycle_id",
        "self_assertions": "assertion_id", "assertion_signals": "signal_id",
        "relationship_events": "relationship_event_id", "subject_intentions": "intention_id",
        "subject_goal_candidates": "candidate_id", "subject_reflections": "reflection_id"},
    13: {"cognitive_requests": "request_id", "world_beliefs": "belief_id",
         "open_concerns": "concern_id", "strategy_assessments": "assessment_id"},
    8: {"runtime_lease": "identity_id", "runtime_queue": "queue_id",
        "runtime_schedules": "schedule_id", "runtime_cognition_calls": "call_id"},
}


def keys_for(version):
    if type(version) is not int or not 1 <= version <= LATEST:
        raise CoreError("SCHEMA_VERSION_UNSUPPORTED")
    return {table: key for number, keys in EXTENSION_KEYS.items()
            if number <= version for table, key in keys.items()}


def install(db, current, target):
    if current > target:
        raise CoreError("SCHEMA_DOWNGRADE_FORBIDDEN")
    # Finalize additive fields of this unreleased development v9 only. Existing
    # released v7/v8 remain explicit migrations, never implicitly upgraded.
    if current==target==9:
        relations={r[1] for r in db.execute('PRAGMA table_info(relationship_events)')}
        record_columns={r[1] for r in db.execute('PRAGMA table_info(continuity_records)')}
        additions={'related_event_id':'TEXT REFERENCES relationship_events(relationship_event_id)',
            'relation_domain':'TEXT','relation_effect':'TEXT'}
        missing={k:v for k,v in additions.items() if k not in relations}
        calendar_missing='CALENDAR' not in db.execute("SELECT sql FROM sqlite_master WHERE name='runtime_schedules'").fetchone()[0]
        outcome_missing='NON_EXECUTION' not in db.execute("SELECT sql FROM sqlite_master WHERE name='experiences'").fetchone()[0]
        if missing or calendar_missing or outcome_missing or 'target_id' not in record_columns:
            db.execute('PRAGMA foreign_keys=OFF')
            db.execute('BEGIN IMMEDIATE')
            try:
                for name,definition in missing.items():db.execute('ALTER TABLE relationship_events ADD COLUMN '+name+' '+definition)
                full=Path(__file__).with_name('schema_v9.sql').read_text()
                if calendar_missing:
                    fragment=full[full.index('CREATE TABLE runtime_schedules_new'):full.index('CREATE INDEX autonomy_record_target')]
                    for statement in fragment.split(';'):
                        if statement.strip():db.execute(statement)
                if 'target_id' not in record_columns:db.execute('ALTER TABLE continuity_records ADD COLUMN target_id TEXT')
                db.execute('CREATE INDEX IF NOT EXISTS autonomy_record_target ON continuity_records(record_kind,target_id,created_at_us DESC)')
                if outcome_missing:
                    fragment=full[full.index('CREATE TABLE experiences_new'):full.index('PRAGMA user_version=9')]
                    for statement in fragment.split(';'):
                        if statement.strip():db.execute(statement)
                # Rebuild opaque lookup metadata, not private factual authority.
                db.execute("UPDATE continuity_records SET target_id=(SELECT json_extract(CAST(payload AS TEXT),'$.intention_id') FROM artifacts WHERE artifact_id=payload_artifact_id) WHERE target_id IS NULL AND record_kind IN ('INTENTION_DISPOSITION','CONSTRAINT_OUTCOME') AND lifecycle='ACTIVE'")
                if db.execute('PRAGMA foreign_key_check').fetchone():raise CoreError('MIGRATION_FOREIGN_KEY_FAILURE')
                db.execute('COMMIT')
            except BaseException:
                if db.in_transaction:db.execute('ROLLBACK')
                raise
            finally:db.execute('PRAGMA foreign_keys=ON')
    if current==target==10:
        # Finalize the index on unreleased v10 checkpoints; never migrate a
        # deployed/default Store implicitly or revive retired request IDs.
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS relational_request_identity ON continuity_records(target_id) WHERE record_kind='SUBJECT_EVENT' AND target_id LIKE 'relational-request:%'")
    if current == 1 and target > 1:
        # v1 replicated plaintext into immutable events. Adding nullable columns
        # cannot make those records deletable. Require a separate audited import.
        if db.execute("SELECT 1 FROM events WHERE kind!='identity.created' LIMIT 1").fetchone():
            raise CoreError("LEGACY_PAYLOAD_MIGRATION_REQUIRED")
        if db.execute("SELECT 1 FROM artifacts LIMIT 1").fetchone():
            raise CoreError("LEGACY_PAYLOAD_MIGRATION_REQUIRED")
    for version in range(current + 1, target + 1):
        sql = Path(__file__).with_name(f"schema_v{version}.sql").read_text()
        if version in {7, 9, 10, 11, 12, 13}:
            # SQLite parent-table rebuild must disable FK outside the transaction.
            # Never rename the old parent: that would rewrite children to *_old.
            db.execute("PRAGMA foreign_keys=OFF")
            try:
                db.executescript("BEGIN IMMEDIATE;\n" + sql)
                if db.execute("PRAGMA foreign_key_check").fetchone():
                    raise CoreError("MIGRATION_FOREIGN_KEY_FAILURE")
                db.execute("COMMIT")
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
            finally:
                db.execute("PRAGMA foreign_keys=ON")
        else:
            db.executescript("BEGIN IMMEDIATE;\n" + sql + "\nCOMMIT;")


    if target>=13:
        # Rebuildable query indexes only. No new table, authority or schema14;
        # both fresh and existing explicitly opened development v13 are covered.
        db.execute("CREATE INDEX IF NOT EXISTS world_valid_candidates ON world_beliefs(scope,entity_id,predicate_key,valid_from_us DESC,valid_until_us,known_at_us)")
        db.execute("CREATE INDEX IF NOT EXISTS world_replaced_lookup ON world_beliefs(replaces,scope,known_at_us) WHERE replaces IS NOT NULL")
