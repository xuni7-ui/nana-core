"""Same Store, writer lock, artifact store, transactions and identity authority."""
from ..storage.development_schema import LATEST
from ..storage.sqlite_store import Store


class ContinuityStore(Store):
    def __init__(self, path, clock=None):
        super().__init__(path, clock, schema_target=LATEST)
        self.db.execute("PRAGMA secure_delete=ON")

