"""Read-only subject queries below loop, projections and context assembly."""
import json
from ..records import RecordService


def revision(store):
    row = store.one('core_meta', 'self.subject_revision')
    return json.loads(row['value_json']) if row else 0


def visible(store, record_id, scope, privacy_classes):
    row = store.one('continuity_records', record_id)
    # Inspect classification before reading any supporting private payload.
    return bool(row and row['scope'] == scope and row['privacy_class'] in privacy_classes
        and row['lifecycle'] == 'ACTIVE' and RecordService(store).current_support(record_id))


def pending(store, scope, privacy_classes):
    rows = store.db.execute("SELECT i.* FROM subject_intentions i JOIN subject_cycles c ON c.subject_event_id=i.subject_event_id WHERE i.scope=? AND i.state='PENDING' "
        "AND i.expires_at_us>? ORDER BY i.created_at_us,c.revision", (scope,store.clock.utc_now_us()))
    return tuple(dict(r) for r in rows if visible(store,r['record_id'],scope,privacy_classes))
