"""Preserve source domains for managed C attention, including legacy keys.

This is provenance/queue identity only. It grants no authority and never turns
a provider interpretation into direct observation. Existing event keys remain
valid across upgrades; a changed namespace must not create a second C cycle.
"""

from ...storage import digest
from ...contracts import CoreError
from ..records import RecordService


def binding(store, concern):
    suffix = digest([concern['concern_id'], concern['revision']])
    legacy = 'synthetic.world.concern.' + suffix
    if store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?', (legacy,)).fetchone():
        return legacy, 'SYNTHETIC_ONLY', 'synthetic.world-concern', 'SYNTHETIC_ONLY'
    records = RecordService(store)
    records.read(concern['record_id'])
    # A revision keeps earlier encounters and proposal/context dependencies.
    # Include memory ancestry too: a derived source cannot hide an unretained
    # receipt or reclassify a synthetic ancestor as a public observation.
    domains, seen, pending = set(), set(), list(records.support(concern['record_id']))
    while pending:
        mid = pending.pop()
        if mid in seen:
            continue
        seen.add(mid)
        domains.add(records.memory.read(mid)['source_provenance']['domain'])
        for edge in store.db.execute('SELECT parent_kind,parent_id FROM memory_dependencies WHERE memory_id=?', (mid,)):
            if edge['parent_kind'] == 'MEMORY':
                pending.append(edge['parent_id'])
            else:
                pending.extend(records.support(edge['parent_id']))
    if 'LOCAL_INTERACTION_METADATA' in domains:
        # No fresh semantic body may be persisted from a transient receipt,
        # even when another ancestor is synthetic or development material.
        raise CoreError('CONCERN_EXPLICIT_RETENTION_REQUIRED')
    if not domains or 'SYNTHETIC_ONLY' in domains:
        return legacy, 'SYNTHETIC_ONLY', 'synthetic.world-concern', 'SYNTHETIC_ONLY'
    if 'DEVELOPMENT_PROJECT' in domains:
        return 'development.world.concern.' + suffix, 'DEVELOPMENT_PROJECT', 'recorded.project.world-concern', 'DEVELOPMENT_MATERIAL'
    if 'CONSENTED_INTERACTION' in domains:
        return 'local.world.concern.' + suffix, 'CONSENTED_INTERACTION', 'recorded.conversation.concern', 'SOURCED_LIFE'
    if domains == {'REAL_PROVIDER'}:
        return 'local.world.concern.' + suffix, 'REAL_PROVIDER', 'provider.world-concern', 'SOURCED_LIFE'
    return 'local.world.concern.' + suffix, 'RECORDED_PUBLIC', 'recorded.world-concern', 'SOURCED_LIFE'
