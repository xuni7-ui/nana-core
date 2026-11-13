"""Shared read-only state stamp; projections never depend on their coordinator."""
from ..storage import digest


def state_token(store):
    store.ensure_privacy_current()
    # Governance definitions do not change normative input. Their own snapshot
    # fences realization; actual constraint outcomes still change subject state.
    # Request preparation/usage/terminal metadata does not change what C knows
    # or wants. Counting its own model audit as a new experience would always
    # invalidate a provider-backed original C deliberation. Actual admissions,
    # sources, decisions, permissions and privacy changes are not excluded.
    cutoff=store.db.execute("SELECT coalesce(max(seq),0) FROM events WHERE kind NOT IN ('governance.initialized','governance.constraint_revision','world.cognition_prepared','world.cognition_calling','world.cognition_proposed','world.cognition_terminal')").fetchone()[0] if store.schema_target>=9 else store.db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]
    return digest({'identity_revision': store.identity['revision'],
        'event_cutoff': cutoff,
        'privacy': digest(store.privacy.read()['intents'])})
