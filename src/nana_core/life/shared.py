"""Real experiences can offer attention to C; expression never implies sending.

Every candidate is rebuilt from current original Experience/support. Finite,
idempotent opportunities are not lessons, relationship facts or another will.
"""
import json
from ..contracts import CoreError
from ..storage import canonical,digest
from ..continuity.records import RecordService
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.subject.contracts import SubjectInput
from ..continuity.subject.context_fit import depth_boundary
from ..continuity.subject.growth_life import availability
from ..continuity.project_work.service import capture
from ..continuity.open_agency.delivery import DeliveryAdmission,DeliveryPolicy
from ..presence.contracts import RuntimeEvent,Cause,DAY


class SharedPresence:
    def __init__(self,app):self.app=app;self.next_at=0
    def candidates(self):
        app=self.app;s=app.runtime.store;records=RecordService(s);out=[]
        for row in s.db.execute('SELECT * FROM experiences ORDER BY created_at_us DESC,rowid DESC LIMIT 32'):
            head=s.one('continuity_records',row['record_id'])
            if not head or head['scope'] not in app.policy.allowed_scopes or head['privacy_class'] not in app.policy.readable_privacy or head['lifecycle']!='ACTIVE' or not records.current_support(row['record_id']):continue
            try:
                m=records.memory.read(row['result_memory_id']);records.memory.read(row['verification_memory_id'])
                value=json.loads(m['text'])
            except (CoreError,ValueError):continue
            if m['source_provenance']['source_kind']!='SYSTEM_VERIFICATION' or value.get('origin') not in {'REAL_OS_CONTROLLED_INDEPENDENT_VERIFICATION','LOCAL_PROJECT_ACTION'}:continue
            topic='experience.'+digest(row['experience_id'])[:24]
            if depth_boundary(s,app.runtime.config.entity_id,head['scope'],topic,app.policy.readable_privacy)[0]:continue
            out.append({'experience_id':row['experience_id'],'record_id':row['record_id'],
                'scope':head['scope'],'privacy_class':head['privacy_class'],'outcome':row['outcome'],
                'task_class':row['task_class'],'topic':topic,
                'source_memory_ids':(row['result_memory_id'],row['verification_memory_id']),
                'status':'VERIFIED_EXPERIENCE_NOT_DELIVERED'})
            if len(out)>=16:break
        return out
    def opportunity(self):
        app=self.app;r=app.runtime;s=r.store;now=r.clock.utc_now_us()
        if now<self.next_at:return None
        self.next_at=now+5_000_000
        # Pending reviews are finite, and user events/goals retain priority.
        if s.db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING'").fetchone()[0]>=4:return None
        if s.db.execute("SELECT 1 FROM goals WHERE state='ACTIVE' LIMIT 1").fetchone():return None
        day=now//DAY;prefix='development.shared.'+str(day)+'.'
        if s.db.execute('SELECT count(*) FROM subject_events WHERE source_key LIKE ?',(prefix+'%',)).fetchone()[0]>=8:return None
        state,parents=availability(s,r.config.entity_id,scope=r.config.scopes[0],privacy_classes=r.config.privacy_classes)
        for c in self.candidates():
            if c['privacy_class'] not in {'PUBLIC','PROJECT'}:continue
            ref='shared-experience:'+c['experience_id']
            if s.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference=?",(ref,)).fetchone():continue
            cue=ConcernCue(cue_kind='DISCOVERY',topic_key=c['topic'],motivation_source='SOCIAL_CONNECTION',
                possible_behaviors=('SOCIALIZE','STAY_SILENT'),resource_class='ORDINARY',availability=state,
                behavior_domain='COMPANIONSHIP')
            mid=capture(r,ref,cue.model_dump(mode='json'),kind='MODEL_DERIVATION',
                parents=tuple(dict.fromkeys((*c['source_memory_ids'],*parents))),predicate='concern.'+c['topic'])
            event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key=prefix+digest(c['experience_id']),kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=c['scope'],privacy_class='PROJECT',observed_at_us=now,source_memory_ids=(mid,))
            qid=r.submit(RuntimeEvent(event_type='RELATIONSHIP_EVENT',trigger='RELATIONSHIP_TRIGGER',input=event,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=now))
            return {'shared_experience_opportunity':c['experience_id'],'queue_id':qid,'not_delivery':True}
        return None
    def review(self,cycle_id,binding_id):
        app=self.app;r=app.runtime;s=r.store;b=app.surfaces._binding(binding_id)
        raw=s.one('subject_cycles',cycle_id)
        if not raw:raise CoreError('SHARED_CYCLE_UNAVAILABLE')
        cycle=r.subject.result(raw)
        if cycle.intention.kind!='SOCIAL_INTERACTION':raise CoreError('SUBJECT_DID_NOT_CHOOSE_SHARING')
        resource='synthetic://recipient/'+r.config.entity_id
        admission=DeliveryAdmission(s,DeliveryPolicy(recipients=(resource,),privacy_classes=('PUBLIC','PROJECT'),
            quiet_timezone=app.config.timezone,quiet_start_local_hour=app.config.quiet_start_local_hour,
            quiet_end_local_hour=app.config.quiet_end_local_hour),scopes=r.config.scopes,privacy_classes=app.policy.readable_privacy)
        decision=admission.assess(cycle,resource,payload={'cycle_id':cycle_id,'surface':binding_id},source_memory_ids=cycle.intention.source_ids)
        return {'cycle_id':cycle_id,'surface':binding_id,'decision':decision,'delivered':False,
            'state':'SHADOW_ONLY_NO_SOCIAL_AUTHORIZATION','execution_authority':False}


class LifeOpportunities:
    """One D opportunity source composes services; neither chooses an intention."""
    def __init__(self,work,shared):self.work,self.shared=work,shared
    def opportunity(self):
        result=self.work.opportunity()
        return result if result is not None else self.shared.opportunity()
