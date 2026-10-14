"""Same Store, writer lock, artifact store, transactions and identity authority."""
from ..storage.development_schema import LATEST
from ..storage.sqlite_store import Store
from ..contracts import CoreError
from pathlib import Path


class ContinuityStore(Store):
    def __init__(self, path, clock=None):
        new_database = not Path(path).exists()
        # An identity-only v1 upgrade has no private payloads or old privacy state.
        if not new_database:
            import sqlite3
            db = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
            try:
                new_database = db.execute("PRAGMA user_version").fetchone()[0] == 1
            finally:
                db.close()
        super().__init__(path, clock, schema_target=LATEST)
        try:
            self.db.execute("PRAGMA secure_delete=ON")
            from .privacy import PrivacyJournal
            self.privacy = PrivacyJournal(self, new_database=new_database)
        except BaseException:
            self.close()
            raise

    def ensure_privacy_current(self):
        self.privacy.ensure_current()

    def backup(self, destination):
        self.ensure_privacy_current()
        if Path(destination).exists():
            raise CoreError("DESTINATION_EXISTS")
        self.privacy.register_copy(destination)
        super().backup(destination)

    def replay(self, destination):
        self.ensure_privacy_current()
        if Path(destination).exists():
            raise CoreError("DESTINATION_EXISTS")
        self.privacy.register_copy(destination)
        super().replay(destination)
        with ContinuityStore(destination, self.clock) as replay:
            from .memory import MemoryService
            MemoryService(replay).rebuild_index()

