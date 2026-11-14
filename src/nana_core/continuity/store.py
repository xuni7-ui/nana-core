"""Same Store, writer lock, artifact store, transactions and identity authority."""

from ..storage.development_schema import LATEST
from ..storage.sqlite_store import Store
from ..contracts import CoreError
from pathlib import Path
import os
import sqlite3


PRIVATE_INTENT_JSON_CONTRACT = "CASE WHEN json_valid(CAST(payload AS TEXT)) THEN json_extract(CAST(payload AS TEXT),'$.contract') END"
PRIVATE_INTENT_JSON_FILTER = PRIVATE_INTENT_JSON_CONTRACT+" IN ('PRIVATE_INTENT_V1','PRIVATE_ACTIVITY_V2','PRIVATE_QUESTION_V3')"
PRIVATE_TENDENCY_JSON_FILTER = PRIVATE_INTENT_JSON_CONTRACT+"='PRIVATE_TENDENCY_V4'"


REBUILDABLE_LOOKUP_INDEXES = {
    "private_intent_tendency_topic_v4": (
        "CREATE INDEX private_intent_tendency_topic_v4 ON artifacts("
        "json_extract(CAST(payload AS TEXT),'$.owner_identity_id'),json_extract(CAST(payload AS TEXT),'$.topic'),artifact_id) WHERE "+PRIVATE_TENDENCY_JSON_FILTER
    ),
    "private_intent_topic_lookup_v1": (
        "CREATE INDEX private_intent_topic_lookup_v1 ON artifacts("
        "json_extract(CAST(payload AS TEXT),'$.owner_identity_id'),json_extract(CAST(payload AS TEXT),'$.topic'),artifact_id) WHERE "+PRIVATE_INTENT_JSON_FILTER
    ),
    "private_intent_payload_lookup": (
        "CREATE INDEX private_intent_payload_lookup ON continuity_records(payload_artifact_id,scope,privacy_class) "
        "WHERE record_kind='INTENTION' AND target_id='private-intent.v1' AND lifecycle='ACTIVE'"
    ),
    "private_intent_live_lookup": (
        "CREATE INDEX private_intent_live_lookup ON continuity_records(scope,privacy_class,created_at_us DESC) "
        "WHERE record_kind='INTENTION' AND target_id='private-intent.v1' AND lifecycle='ACTIVE'"
    ),
    "events_artifact_lookup": "CREATE INDEX events_artifact_lookup ON events(artifact_id)",
    "memories_payload_lookup": "CREATE INDEX memories_payload_lookup ON memories(payload_artifact_id)",
    "evidence_payload_lookup": "CREATE INDEX evidence_payload_lookup ON continuity_evidence(payload_artifact_id)",
    "memory_correction_lookup": "CREATE INDEX memory_correction_lookup ON memories(correction_of)",
    "memory_superseded_lookup": "CREATE INDEX memory_superseded_lookup ON memories(superseded_by)",
    "memory_terms_term_lookup": "CREATE INDEX memory_terms_term_lookup ON memory_terms(term,memory_id)",
    "memory_source_binding": "CREATE INDEX memory_source_binding ON memories(source_evidence_id,entity_id,scope)",
    "memory_user_note_lookup": (
        "CREATE INDEX memory_user_note_lookup ON memories(entity_id,scope,privacy_class,lifecycle,assessment) "
        "WHERE substr(predicate_key,1,10)='user-note.'"
    ),
    "memory_note_gram_coverage": (
        "CREATE INDEX memory_note_gram_coverage ON memories(entity_id,scope,privacy_class,lifecycle,assessment,memory_id) "
        "WHERE substr(predicate_key,1,10)='user-note.' AND memory_type='SEMANTIC' "
        "AND epistemic_kind='STATEMENT' AND authority='DIRECT'"
    ),
    "artifacts_event_lookup": "CREATE INDEX artifacts_event_lookup ON artifacts(created_event_id)",
    "memory_dependency_parent_lookup": "CREATE INDEX memory_dependency_parent_lookup ON memory_dependencies(parent_kind,parent_id,memory_id)",
    "memory_consolidated_lookup": (
        "CREATE INDEX memory_consolidated_lookup ON memories(entity_id,scope,privacy_class,lifecycle,assessment) "
        "WHERE substr(predicate_key,1,17)='consolidation.v1.'"
    ),
    "memories_event_lookup": "CREATE INDEX memories_event_lookup ON memories(event_id)",
    "evidence_event_lookup": "CREATE INDEX evidence_event_lookup ON continuity_evidence(event_id)",
}


class ContinuityStore(Store):
    @staticmethod
    def _private_path(path):
        path = Path(path)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        stat = path.parent.stat()
        if stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
            raise CoreError("PRIVATE_CONTINUITY_DIRECTORY_REQUIRED")
        if any(Path(str(path) + suffix).is_symlink() for suffix in ("", "-wal", "-shm", ".lock", ".privacy.json")):
            raise CoreError("CONTINUITY_SYMLINK_FORBIDDEN")
        return path

    def __init__(self, path, clock=None, *, schema_target=7, identity_bootstrap=None):
        if type(schema_target) is not int or not 7 <= schema_target <= LATEST:
            raise CoreError("CONTINUITY_SCHEMA_UNSUPPORTED")
        Store.check_host()
        path = self._private_path(path)
        new_database = not Path(path).exists()
        # An identity-only v1 upgrade has no private payloads or old privacy state.
        if not new_database:
            db = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
            try:
                new_database = db.execute("PRAGMA user_version").fetchone()[0] == 1
            finally:
                db.close()
        super().__init__(path, clock, schema_target=schema_target, identity_bootstrap=identity_bootstrap)
        try:
            self.db.execute("PRAGMA secure_delete=ON")
            # Physical lookup aid, not new Subject state or a schema transition.
            # Opening the original Store already holds the exclusive writer lock.
            # Source-bound idempotency and deferred foreign-key checks must not
            # scan the entire history on each write.
            try:self.db.execute("SELECT json_valid('{}')").fetchone();has_json=True
            except sqlite3.OperationalError:has_json=False
            for name,sql in REBUILDABLE_LOOKUP_INDEXES.items():
                if name.startswith('private_intent_') and schema_target<13:continue
                if name in {'private_intent_topic_lookup_v1','private_intent_tendency_topic_v4'} and not has_json:continue
                self.db.execute(sql.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1))
            for suffix in ("", "-wal", "-shm", ".lock"):
                owned = Path(str(self.path) + suffix)
                if owned.exists():
                    owned.chmod(0o600)
            from .privacy import PrivacyJournal

            self.privacy = PrivacyJournal(self, new_database=new_database)
            if not self.one("core_meta", "cloud.shadow_runtime"):
                from ..storage import canonical

                with self.transaction("self.offline_execution_fenced") as tx:
                    tx.put(
                        "core_meta",
                        {
                            "key": "cloud.shadow_runtime",
                            "value_json": canonical(
                                {"mode": "CONTINUOUS_SELF_OFFLINE", "external_execute": "DISABLED"}
                            ),
                        },
                    )
        except BaseException:
            self.close()
            raise

    def ensure_privacy_current(self):
        self.privacy.ensure_current()

    def backup(self, destination):
        destination = self._private_path(destination)
        self.ensure_privacy_current()
        if Path(destination).exists():
            raise CoreError("DESTINATION_EXISTS")
        self.privacy.register_copy(destination)
        super().backup(destination)
        Path(destination).chmod(0o600)

    def replay(self, destination):
        destination = self._private_path(destination)
        self.ensure_privacy_current()
        if Path(destination).exists():
            raise CoreError("DESTINATION_EXISTS")
        self.privacy.register_copy(destination)
        super().replay(destination)
        with ContinuityStore(destination, self.clock, schema_target=self.schema_target) as replay:
            from .memory import MemoryService

            MemoryService(replay).rebuild_index()
