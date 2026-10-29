"""Real experiences can offer attention to C; expression never implies sending.

Every candidate is rebuilt from current original Experience/support. Finite,
idempotent opportunities are not lessons, relationship facts or another will.
"""
import json
from ..contracts import CoreError
from ..storage import canonical,digest
from ..continuity.records import RecordService
from ..continuity.subject.opportunities import ConcernCue,ShareAssessment
from ..continuity.subject.contracts import SubjectInput
from ..continuity.subject.context_fit import depth_boundary
from ..continuity.subject.growth_life import availability
from ..continuity.project_work.service import capture
from ..continuity.open_agency.delivery import DeliveryAdmission,DeliveryPolicy
from ..presence.contracts import RuntimeEvent,Cause,DAY


class SharedPresence:
    def __init__(self,app):self.app=app;self.next_at=0
    def inbox(self, *, privacy, scope=None, entity_id=None):
        """Current original-C candidates, not notifications or delivered speech."""
        app=self.app;s=app.runtime.store;records=RecordService(s);out=[]
        allowed=set(privacy)&set(app.policy.readable_privacy)&{'PUBLIC','PROJECT'}
        scope=app.runtime.config.scopes[0] if scope is None else scope
        entity_id=app.runtime.config.entity_id if entity_id is None else entity_id
        for row in s.db.execute("SELECT * FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id LIKE 'shared-candidate:%' ORDER BY created_at_us DESC,rowid DESC LIMIT 64"):
            if row['scope']!=scope or row['scope'] not in app.policy.allowed_scopes or row['privacy_class'] not in allowed or row['lifecycle']!='ACTIVE':continue
            try:
                current=records.read(row['record_id']);body=current['payload']
                if body.get('kind')!='SHARED_LIFE_CANDIDATE' or not records.current_support(row['record_id']):continue
                raw=s.one('subject_cycles',body['cycle_id'])
                if not raw or app.runtime.subject.result(raw).intention.kind!='SOCIAL_INTERACTION':continue
                event=s.one('subject_events',raw['subject_event_id'])
                if not event or event['entity_id']!=entity_id:continue
                out.append({'candidate_record_id':row['record_id'],'cycle_id':body['cycle_id'],
                    'topic':body.get('topic'),'state':body['state'],'delivery':'NONE',
                    'source_record_ids':[raw['record_id']],
                    'source_memory_ids':list(records.support(row['record_id']))})
            except CoreError:continue
            if len(out)>=16 or len(canonical(out).encode())>8000:
                if len(canonical(out).encode())>8000:out.pop()
                break
        return {'items':out,'coverage':'ORIGINAL_C_APPROVED_CANDIDATES_ONLY','external_delivery':False}
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
    def reconcile(self):
        """Complete internal candidate formation, never claim a delivered message.

        A social intention must not occupy a global cognitive-load slot forever
        merely because a dev surface has no sending authorization. Its original
        desire/judgment persists, and the separate sourced candidate can be saved.
        """
        app=self.app;r=app.runtime;s=r.store;records=RecordService(s)
        for row in s.db.execute("SELECT c.*,i.intention_id FROM subject_cycles c JOIN subject_events e ON c.subject_event_id=e.subject_event_id JOIN subject_intentions i ON i.subject_event_id=e.subject_event_id WHERE e.source_key LIKE 'development.shared.%' AND i.kind='SOCIAL_INTERACTION' AND i.state='PENDING' ORDER BY c.rowid LIMIT 16"):
            head=s.one('continuity_records',row['record_id'])
            if not head or head['scope'] not in r.config.scopes or head['privacy_class'] not in r.config.privacy_classes or not records.current_support(row['record_id']):continue
            cycle=r.subject.result(row);key='shared-candidate:'+cycle.cycle_id
            old=s.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=?",(key,)).fetchone()
            if not old:
                state,parents=availability(s,r.config.entity_id,scope=head['scope'],privacy_classes=r.config.privacy_classes)
                status='SAVE_FOR_LATER_NO_SURFACE'
                if state=='BUSY':status='DEFER_BUSY'
                elif state=='UNKNOWN':status='SAVE_FOR_LATER_UNKNOWN_AVAILABILITY'
                if app.config.surface_bindings:
                    enabled=next((b for b in app.config.surface_bindings if b.enabled),None)
                    if enabled:status=self.review(cycle.cycle_id,enabled.binding_id)['decision']['result']
                topic=cycle.context_fit.topic_key if cycle.context_fit else None
                body={'kind':'SHARED_LIFE_CANDIDATE','cycle_id':cycle.cycle_id,'intention_id':row['intention_id'],'state':status,'topic':topic,'delivery':'NONE','internal_candidate_complete':True,'external_action':False,'authority_granted':False}
                with s.transaction('life.share_candidate_formed',{'cycle_id':cycle.cycle_id,'delivery':'NONE'}) as tx:
                    rid=records.create(tx,kind='RUNTIME_WORK',scope=head['scope'],payload=body,records=(cycle.record_id,),memories=parents,target_id=key)
            else:rid=old[0]
            intention=s.one('subject_intentions',row['intention_id'])
            if intention['state']=='PENDING':r.subject.transition_intention(row['intention_id'],expected_revision=intention['revision'],state='COMPLETED')
            return {'shared_candidate_record_id':rid,'not_delivered':True,'original_judgment_preserved':True}
        return None

    def opportunity(self):
        app=self.app;r=app.runtime;s=r.store;now=r.clock.utc_now_us()
        reconciled=self.reconcile()
        if reconciled:return reconciled
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
            # Relevance is sourced from this outcome/relationship support, not a
            # permanent sentiment score or delivery authority. Quiet/busy remains
            # an independent delivery condition; C may still want to share.
            from ..continuity.autonomy.relationships import relationship_influence
            from ..continuity.memory import PRIVACY_RANK
            visible=tuple(p for p in r.config.privacy_classes if PRIVACY_RANK[p]<=PRIVACY_RANK[c['privacy_class']])
            influence=relationship_influence(s,r.config.entity_id,scope=c['scope'],privacy_classes=visible)
            relationship_sources=tuple(m for rid in influence.source_record_ids for m in RecordService(s).support(rid))
            support=tuple(dict.fromkeys((*c['source_memory_ids'],*parents,*relationship_sources)))
            if len(support)>32:continue
            designated=any(b.enabled and b.entity_id==r.config.entity_id and b.scope==c['scope'] for b in app.config.surface_bindings)
            share=ShareAssessment(relational_relevance='RELEVANT' if influence.source_record_ids or designated else 'LOW',affect_relevance='RELEVANT' if c['outcome']=='FAILURE' else 'LOW',interruption_cost='HEAVY' if state=='BUSY' else 'LIGHT')
            cue=cue.model_copy(update={'share_assessment':share})
            mid=capture(r,ref,cue.model_dump(mode='json'),kind='MODEL_DERIVATION',
                parents=support,predicate='concern.'+c['topic'])
            event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key=prefix+digest(c['experience_id']),kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=c['scope'],privacy_class='PROJECT',observed_at_us=now,source_memory_ids=(mid,))
            qid=r.submit(RuntimeEvent(event_type='RELATIONSHIP_EVENT',trigger='RELATIONSHIP_TRIGGER',input=event,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=now))
            return {'shared_experience_opportunity':c['experience_id'],'queue_id':qid,'not_delivery':True}
        from .conversation_opportunity import opportunity
        return opportunity(app)
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
