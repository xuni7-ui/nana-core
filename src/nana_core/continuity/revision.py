"""Shared read-only state stamp; projections never depend on their coordinator."""
from ..storage import digest


def state_token(store):
    store.ensure_privacy_current()
    # Governance definitions do not change normative input. Their own snapshot
    # fences realization; actual constraint outcomes still change subject state.
    cutoff=store.db.execute("SELECT coalesce(max(seq),0) FROM events WHERE kind NOT IN ('governance.initialized','governance.constraint_revision')").fetchone()[0] if store.schema_target>=9 else store.db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]
    return digest({'identity_revision': store.identity['revision'],
        'event_cutoff': cutoff,
        'privacy': digest(store.privacy.read()['intents'])})
