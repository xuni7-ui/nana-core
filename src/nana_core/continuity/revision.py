"""Shared read-only state stamp; projections never depend on their coordinator."""
from ..storage import digest


def state_token(store):
    store.ensure_privacy_current()
    return digest({'identity_revision': store.identity['revision'],
        'event_cutoff': store.db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0],
        'privacy': digest(store.privacy.read()['intents'])})
