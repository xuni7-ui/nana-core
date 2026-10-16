"""One C attention component: sourced check opportunities, no background loop."""
from pydantic import Field
from ...contracts import DTO
from ...storage import digest
from ..records import RecordService
from .opportunities import cues_from
from ..recurrence import RecurrenceSpec


class AttentionOpportunity(DTO):
    key: str
    source_kind: str
    source_id: str
    source_revision: int | None = None
    scope: str
    entity_id: str
    due_at_us: int
    memory_ids: tuple[str,...]
    event_type: str
    wake_trigger: str
    priority: int = 1
    task_class: str | None = None
    reflection_experience_id: str | None = None
    calendar: RecurrenceSpec | None = None
    commitment_check_id: str | None = None


def collect_opportunities(loop,*,entity_id,now_us,quiet_since_us,quiet_window_us):
    store,records=loop.store,RecordService(loop.store)
    result=[]
    for scope in loop.scopes:
        ids=[r['memory_id'] for r in store.db.execute("SELECT memory_id FROM memories WHERE entity_id IN (?,?) AND scope=? AND predicate_key LIKE 'concern.%' AND lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') ORDER BY created_at_us DESC LIMIT 64",
            (entity_id,store.identity['identity_id'],scope))]
        for mid,cue in cues_from(store,ids,scope=scope,privacy_classes=loop.privacy_classes):
            if cue.cue_kind=='CONSTRAINT':continue
            source=store.one('memories',mid)
            result.append(AttentionOpportunity(key='memory-'+mid,source_kind='MEMORY',source_id=mid,
                scope=scope,entity_id=entity_id,due_at_us=max(cue.not_before_us,source['ingested_time_us']+quiet_window_us,quiet_since_us+quiet_window_us),
                memory_ids=(mid,),event_type='SELF_EVENT',wake_trigger='SELF_TRIGGER',
                task_class='interaction.shared_discovery' if cue.cue_kind=='DISCOVERY' else None))
        for row in store.all('commitments'):
            if store.schema_target>=9 and row['state'] in {'ADOPTED','ACTIVE'} and loop.visible(row['record_id'],scope):
                body=records.read(row['record_id'])['payload']
                if body.get('recurrence'):
                    from ...storage import canonical
                    calendar=RecurrenceSpec.model_validate_json(canonical(body['recurrence']))
                    result.append(AttentionOpportunity(key='calendar-'+digest([row['commitment_id'],row['revision']]),source_kind='COMMITMENT',source_id=row['commitment_id'],source_revision=row['revision'],
                        scope=scope,entity_id=entity_id,due_at_us=calendar.next_after(row['updated_at_us']),memory_ids=records.support(row['record_id']),event_type='GOAL_EVENT',wake_trigger='GOAL_TRIGGER',priority=2,
                        task_class='commitment.calendar_check',calendar=calendar,commitment_check_id=row['commitment_id']))
            if row['state'] in {'ADOPTED','ACTIVE'} and row['due_at_us'] is not None and loop.visible(row['record_id'],scope):
                voluntary=store.schema_target>=10 and bool(records.read(row['record_id'])['payload'].get('voluntary'))
                result.append(AttentionOpportunity(key='commitment-'+digest([row['commitment_id'],row['revision']]),
                    source_kind='COMMITMENT',source_id=row['commitment_id'],source_revision=row['revision'],scope=scope,entity_id=row['entity_id'] if voluntary else entity_id,
                    task_class='relational.accommodation.review' if voluntary else None,commitment_check_id=row['commitment_id'] if voluntary else None,
                    due_at_us=row['due_at_us'],memory_ids=records.support(row['record_id']),event_type='GOAL_EVENT',wake_trigger='GOAL_TRIGGER',priority=3))
        for row in store.all('projects'):
            if row['state']!='ACTIVE' or not loop.visible(row['record_id'],scope):continue
            payload=records.read(row['record_id'])['payload']
            if not payload.get('blockers'):continue
            result.append(AttentionOpportunity(key='project-'+digest([row['project_id'],row['revision']]),source_kind='PROJECT',source_id=row['project_id'],source_revision=row['revision'],
                scope=scope,entity_id=entity_id,due_at_us=max(row['updated_at_us']+quiet_window_us,quiet_since_us+quiet_window_us),
                memory_ids=records.support(row['record_id']),event_type='PROJECT_EVENT',wake_trigger='GOAL_TRIGGER',priority=2))
        for row in store.all('experiences'):
            if not loop.visible(row['record_id'],scope):continue
            if store.db.execute('SELECT 1 FROM subject_reflections WHERE experience_id=?',(row['experience_id'],)).fetchone():continue
            result.append(AttentionOpportunity(key='reflection-'+row['experience_id'],source_kind='EXPERIENCE',source_id=row['experience_id'],
                scope=scope,entity_id=entity_id,due_at_us=max(row['created_at_us']+quiet_window_us,quiet_since_us+quiet_window_us),
                memory_ids=records.support(row['record_id']),event_type='REFLECTION_EVENT',wake_trigger='REFLECTION_TRIGGER',
                task_class=row['task_class'],reflection_experience_id=row['experience_id']))
    return tuple(result[:64])
