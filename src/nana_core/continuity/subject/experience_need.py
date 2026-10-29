"""Qualitative, rebuildable competence needs from independently checked life.

No preference is assigned, no affect score is stored, and learning is optional.
This phase modulates a matching C concern; runtime merely offers opportunities.
"""
from typing import Literal
from ...contracts import DTO
from ..records import RecordService
from .growth_life import project


class ExperienceNeed(DTO):
    derived: Literal[True] = True
    domain: str
    state: Literal['OPEN', 'SETTLED', 'UNKNOWN']
    source_record_ids: tuple[str, ...] = ()
    reason: str


def project_need(store, domain, *, scope, privacy_classes, source_memory_ids=None):
    records=RecordService(store)
    def visible(rid):
        head=store.one('continuity_records',rid)
        return bool(head and head['scope']==scope and head['privacy_class'] in privacy_classes and head['lifecycle']=='ACTIVE' and records.current_support(rid))
    # Bound the relevant, permitted history, not unrelated platforms/scopes or
    # successful outcomes. Otherwise ordinary long-lived activity can drown out
    # the very verified gap this C cycle is reconsidering.
    allowed = tuple(privacy_classes)
    if not allowed:
        return ExperienceNeed(domain=domain,state='UNKNOWN',reason='No readable experience privacy class')
    slots = ','.join('?' for _ in allowed)
    rows=store.db.execute(
        "SELECT e.* FROM experiences e JOIN continuity_records r ON r.record_id=e.record_id "
        f"WHERE e.task_class=? AND e.outcome='FAILURE' AND r.scope=? AND r.privacy_class IN ({slots}) "
        "AND r.lifecycle='ACTIVE' ORDER BY e.created_at_us DESC,e.rowid DESC LIMIT 33",
        (domain,scope,*allowed)).fetchall()
    if len(rows)>32:return ExperienceNeed(domain=domain,state='UNKNOWN',reason='Experience horizon requires review')
    failures=[r for r in rows if r['outcome']=='FAILURE' and visible(r['record_id'])]
    if not failures:return ExperienceNeed(domain=domain,state='UNKNOWN',reason='No current verified gap experience')
    if source_memory_ids is not None:
        # Bind modulation to the gap's actual ancestry, not merely a domain name.
        seen=set();pending=list(source_memory_ids)
        while pending and len(seen)<128:
            mid=pending.pop()
            if mid in seen:continue
            head=store.one('memories',mid)
            if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes:continue
            seen.add(mid)
            pending.extend(r[0] for r in store.db.execute('SELECT parent_id FROM memory_dependencies WHERE memory_id=?',(mid,)))
        if pending:return ExperienceNeed(domain=domain,state='UNKNOWN',reason='Gap ancestry requires bounded review')
        failures=[r for r in failures if r['result_memory_id'] in seen]
        if not failures:return ExperienceNeed(domain=domain,state='UNKNOWN',reason='This concern does not descend from a checked gap')
    latest=failures[0]
    checks=store.db.execute(
        "SELECT a.* FROM strategy_assessments a JOIN lessons l ON l.lesson_id=a.lesson_id "
        "JOIN continuity_records r ON r.record_id=a.record_id "
        f"WHERE l.task_class=? AND r.scope=? AND r.privacy_class IN ({slots}) AND r.lifecycle='ACTIVE' "
        "ORDER BY a.created_at_us DESC,a.rowid DESC LIMIT 33", (domain,scope,*allowed)).fetchall()
    if len(checks)>32:return ExperienceNeed(domain=domain,state='UNKNOWN',reason='Assessment horizon requires review')
    refs=(latest['record_id'],)
    for check in checks:
        if not visible(check['record_id']):continue
        if check['verdict']!='SUCCESS':
            refs=(*refs,check['record_id']);break  # counterexample is not erased by older success
        view=project(store,check['assessment_id'],scope=scope,privacy_classes=privacy_classes)
        if view and check['created_at_us']>=latest['created_at_us']:
            return ExperienceNeed(domain=domain,state='SETTLED',source_record_ids=tuple(dict.fromkeys((*refs,*view.source_record_ids))),reason='Independent later transfer/reuse settled this known capability gap; repeated learning is unnecessary')
    return ExperienceNeed(domain=domain,state='OPEN',source_record_ids=refs,reason='A verified failure still matters; rest, learning or another approach remain subject choices')
