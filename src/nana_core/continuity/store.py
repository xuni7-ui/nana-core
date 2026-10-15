"""Same Store, writer lock, artifact store, transactions and identity authority."""
from ..storage.development_schema import LATEST
from ..storage.sqlite_store import Store
from ..contracts import CoreError
from pathlib import Path
import os


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

    def __init__(self, path, clock=None, *, schema_target=7):
        if type(schema_target) is not int or not 7 <= schema_target <= LATEST:
            raise CoreError("CONTINUITY_SCHEMA_UNSUPPORTED")
        path = self._private_path(path)
        new_database = not Path(path).exists()
        # An identity-only v1 upgrade has no private payloads or old privacy state.
        if not new_database:
            import sqlite3
            db = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
            try:
                new_database = db.execute("PRAGMA user_version").fetchone()[0] == 1
            finally:
                db.close()
        super().__init__(path, clock, schema_target=schema_target)
        try:
            self.db.execute("PRAGMA secure_delete=ON")
            for suffix in ("", "-wal", "-shm", ".lock"):
                owned = Path(str(self.path) + suffix)
                if owned.exists():
                    owned.chmod(0o600)
            from .privacy import PrivacyJournal
            self.privacy = PrivacyJournal(self, new_database=new_database)
            if not self.one("core_meta", "cloud.shadow_runtime"):
                from ..storage import canonical
                with self.transaction("self.offline_execution_fenced") as tx:
                    tx.put("core_meta", {"key": "cloud.shadow_runtime", "value_json": canonical({
                        "mode": "CONTINUOUS_SELF_OFFLINE", "external_execute": "DISABLED"})})
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

