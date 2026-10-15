"""Explicit, forward-only development migrations. Default v1 Store stays frozen.

These schemas are not an authorization to upgrade any deployed Store. A rollback
uses a pre-upgrade snapshot in quarantine; it never down-converts new history.
"""
from pathlib import Path

from ..contracts import CoreError

LATEST = 9
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
    # Earlier checkpoints of this unreleased development v9 had no normalized
    # relationship links. Complete their additive finalization without touching
    # v7/v8 or reinterpreting old history; official replay fills NULL defaults.
    if current==target==9:
        columns={r[1] for r in db.execute('PRAGMA table_info(relationship_events)')}
        additions={'related_event_id':'TEXT REFERENCES relationship_events(relationship_event_id)',
            'relation_domain':'TEXT','relation_effect':'TEXT'}
        missing={k:v for k,v in additions.items() if k not in columns}
        if missing:
            db.execute('BEGIN IMMEDIATE')
            try:
                for name,definition in missing.items():db.execute('ALTER TABLE relationship_events ADD COLUMN '+name+' '+definition)
                db.execute('COMMIT')
            except BaseException:db.execute('ROLLBACK');raise
    if current == 1 and target > 1:
        # v1 replicated plaintext into immutable events. Adding nullable columns
        # cannot make those records deletable. Require a separate audited import.
        if db.execute("SELECT 1 FROM events WHERE kind!='identity.created' LIMIT 1").fetchone():
            raise CoreError("LEGACY_PAYLOAD_MIGRATION_REQUIRED")
        if db.execute("SELECT 1 FROM artifacts LIMIT 1").fetchone():
            raise CoreError("LEGACY_PAYLOAD_MIGRATION_REQUIRED")
    for version in range(current + 1, target + 1):
        sql = Path(__file__).with_name(f"schema_v{version}.sql").read_text()
        if version in {7, 9}:
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

