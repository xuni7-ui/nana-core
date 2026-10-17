"""B10 runtime projections. No model, mutation or delivery authority."""
import json
from ..contracts import CoreError
from ..continuity.context import self_frame
from ..continuity.journal import living_journal
from ..continuity.records import RecordService
from ..continuity.relational.bootstrap import primary_user_view
from ..continuity.relational.projections import social_appetite
from ..continuity.autonomy.governance import manager_views
from .resources import resource_state


def runtime_projection(runtime,kind,policy,*,scopes,entity_id):
    if not runtime.config.living:raise CoreError('LIVING_RUNTIME_NOT_ENABLED')
    if not set(scopes)<=set(policy.allowed_scopes):raise CoreError('RUNTIME_VIEW_SCOPE_DENIED')
    r=runtime;privacy=policy.readable_privacy;records=RecordService(r.store)
    if kind=='WORLD_LOOP':
        if not r.work.world:raise CoreError('WORLD_LOOP_NOT_CONFIGURED')
        return r.work.world.view(scopes=scopes,privacy_classes=privacy)
    if kind=='OPEN_AUTONOMY':
        from ..continuity.open_agency.projections import project_open
        return project_open(r.store,policy,scopes=scopes).model_dump(mode='json')
    if kind=='LIVING_JOURNAL':return living_journal(r.store,scopes=scopes,privacy_classes=privacy).model_dump(mode='json')
    if kind=='RESOURCE_STATE':return resource_state(r.store,r.config).model_dump(mode='json')
    if kind!='LIVING_RUNTIME':raise CoreError('RUNTIME_VIEW_UNKNOWN')
    if len(scopes)!=1:raise CoreError('RUNTIME_VIEW_EXACT_SCOPE_REQUIRED')
    scope=scopes[0]
    from ..continuity.subject.projections import project_self,Environment
    living,personality,relation=project_self(r.store,entity_id=entity_id,scope=scope,privacy_classes=privacy,
        environment=Environment(capabilities=r.config.capability_snapshot.capabilities,cognition_available=r.cognition.availability not in {'DEGRADED','UNAVAILABLE'}))
    goals=[]
    for goal in r.store.db.execute("SELECT * FROM goals ORDER BY rowid DESC LIMIT 16"):
        meta=json.loads(goal['body_json']);rid=meta.get('record_id');head=r.store.one('continuity_records',rid) if rid else None
        if not head or head['scope']!=scope or head['privacy_class'] not in privacy or head['lifecycle']!='ACTIVE' or not records.current_support(rid):continue
        work=r.store.one('jobs',meta['work_id']);goals.append({'goal_id':goal['goal_id'],'state':goal['state'],'version':goal['version'],'work_state':work['state'],'cursor':work['cursor'],'record_id':rid})
    source=r.store.db.execute('SELECT c.* FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id WHERE e.scope=? AND e.entity_id=? ORDER BY c.revision DESC LIMIT 1',(scope,entity_id)).fetchone()
    motives=[]
    if source and source['record_id']:
        head=r.store.one('continuity_records',source['record_id'])
        if head['privacy_class'] in privacy and head['lifecycle']=='ACTIVE' and records.current_support(head['record_id']):
            motives=records.read(head['record_id'])['payload']['motivations']
    primary=primary_user_view(r.store,scope=scope,privacy_classes=privacy)
    return {'derived':True,'living_self':living.model_dump(mode='json'),'motivation_sources':motives,
        'social_appetite':social_appetite(r.store,scope=scope,privacy_classes=privacy).model_dump(mode='json'),
        'primary_user':primary.model_dump(mode='json') if primary else None,'goals':goals,
        'state':'THINKING' if r._processing else 'WAITING' if r.queue.depth() else 'RESTING' if living.presence=='RESTING' else 'WATCHING',
        'runtime_health':r.health().model_dump(mode='json'),'resources':resource_state(r.store,r.config).model_dump(mode='json'),
        'manager_outcomes':manager_views(r.store,scope=scope,privacy_classes=privacy),
        'maintenance_pending':r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='SCAN' AND state='WAITING'").fetchone()[0],
        'execution_authority':'NONE_FROM_VIEW','personality_is_not_runtime_pressure':True}
