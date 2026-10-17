"""Single-slice C components integrated into the existing LivingWork hooks.

There is no loop here. No provider callback adopts a goal; a proposal creates a
source-backed concern, then the next ordinary SubjectLoop owns its judgment.
"""
import json
from ...contracts import CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from .cognition import CognitionSession,CognitionBudget
from .attention import ConcernService
from .world import WorldModel

class WorldLoopWork:
    def __init__(self,runtime,transport,policy,*,resources,skill_development=None):
        self.runtime,self.store=runtime,runtime.store;self.records=RecordService(self.store)
        if not runtime.work.agency or not runtime.work.agency.policy.dynamic_resources:raise CoreError('DYNAMIC_GOAL_REALM_REQUIRED')
        self.cognition=CognitionSession(runtime,transport,policy);self.cognition.recover()
        self.concerns=ConcernService(runtime,resources=resources);self.concerns.restore_descriptions()
        self.world=WorldModel(self.store,scopes=runtime.config.scopes,privacy_classes=runtime.config.privacy_classes)
        self.budget=CognitionBudget()
        self.skills=skill_development
        if self.skills:self.skills.cognition=self.cognition
    def observe(self,memory_id,*,role='GOALS'):
        row=self.records.memory.read(memory_id)
        if row['scope'] not in self.runtime.config.scopes or row['privacy_class'] not in self.runtime.config.privacy_classes:raise CoreError('WORLD_OBSERVATION_DENIED')
        import json
        try:body=json.loads(row['text'])
        except ValueError:body={}
        if isinstance(body,dict) and 'world_claim' in body:
            self.world.ingest(memory_id)
            from .world import SourcedClaim
            claim=SourcedClaim.model_validate_json(canonical(body['world_claim']))
            if claim.related_resources and self.world.view(claim.entity_id,claim.predicate).state=='SUPPORTED_BELIEF' and row['authority']=='DIRECT':self._review_related_goals(memory_id,claim.related_resources)
        key='world-cognition:'+digest([memory_id,role])
        old=self.store.db.execute('SELECT job_id FROM jobs WHERE occurrence_key=?',(key,)).fetchone()
        if old:return old[0]
        if self.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='WORLD_COGNITION' AND state='WAITING'").fetchone()[0]>=8:raise CoreError('WORLD_OBSERVATION_BACKPRESSURE')
        now=self.store.clock.utc_now_us();wid=uid()
        with self.store.transaction('world.interpretation_queued',{'work_id':wid}) as tx:
            rid=self.records.create(tx,kind='RUNTIME_WORK',scope=row['scope'],payload={'memory_id':memory_id,'role':role},memories=(memory_id,))
            tx.put('jobs',{'job_id':wid,'occurrence_key':key,'due_at_us':now,'state':'WAITING','body_json':'{}','work_kind':'WORLD_COGNITION','record_id':rid,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
        return wid
    def _review_related_goals(self,memory_id,resources):
        from ..subject.contracts import SubjectInput
        from ..agency_contracts import GoalReviewRef
        from ...presence.contracts import RuntimeEvent,Cause
        memory=self.records.memory.read(memory_id)
        for goal in self.store.db.execute("SELECT * FROM goals WHERE state IN ('ACTIVE','BLOCKED','SUSPENDED') LIMIT 16"):
            meta=json.loads(goal['body_json']);head=self.records.read(meta['plan_record_id'])
            if head['scope']!=memory['scope'] or not self.records.current_support(head['record_id']):continue
            if not any(op['resource'] in resources for op in head['payload']['steps']):continue
            if self.store.db.execute("SELECT 1 FROM actions WHERE goal_id=? AND state IN ('READY','DISPATCHING','UNKNOWN','PENDING_VERIFY')",(goal['goal_id'],)).fetchone():continue
            key='synthetic.world.replan.'+digest([goal['goal_id'],goal['version'],memory_id])
            ref=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=memory_id)
            inp=SubjectInput(source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=self.runtime.config.entity_id,scope=memory['scope'],observed_at_us=memory['observed_time_us'],source_memory_ids=(memory_id,),goal_review=ref,privacy_class=memory['privacy_class'])
            self.runtime.submit(RuntimeEvent(event_type='GOAL_EVENT',trigger='GOAL_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=memory_id),),due_at_us=self.store.clock.utc_now_us(),priority=3))
    def opportunity(self):return self.concerns.opportunity()
    def maintenance_slice(self):
        row=self.store.db.execute("SELECT * FROM jobs WHERE work_kind='WORLD_COGNITION' AND state='WAITING' ORDER BY due_at_us LIMIT 1").fetchone()
        if not row:
            result=self.skills.slice() if self.skills else None
            if result and result.get('observation_memory_id'):self.observe(result['observation_memory_id'])
            return result
        if not self.records.current_support(row['record_id']):return self._finish(row,'CANCELLED','SOURCE_RETIRED')
        body=self.records.read(row['record_id'])['payload']
        try:
            request_id=self.cognition.prepare(row['occurrence_key'],body['role'],(body['memory_id'],),budget=self.budget,capabilities=tuple(self.runtime.work.agency.registry.definitions))
            outcome=self.cognition.execute(request_id)
            if outcome['state']=='PROPOSED':
                rid=outcome.get('record_id')
                if not rid:
                    result=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(request_id,)).fetchone();rid=result[0] if result else None
                if rid:
                    self.cognition.proposal(rid)
                    self.concerns.offer(rid)
                return self._finish(row,'DONE','PROPOSAL_RECORDED')
            return self._finish(row,'UNKNOWN' if outcome['state']=='UNKNOWN' else 'BLOCKED',outcome.get('error_code',outcome['state']))
        except (CoreError,ValueError) as exc:
            if isinstance(exc,CoreError) and exc.code in {'RUNTIME_LEASE_LOST','PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE'}:raise
            return self._finish(row,'BLOCKED',exc.code if isinstance(exc,CoreError) else 'INVALID_WORLD_PROPOSAL')
    def _finish(self,row,state,reason):
        with self.store.transaction('world.interpretation_finished',{'work_id':row['job_id'],'reason':reason}) as tx:tx.update('jobs',row['job_id'],state=state,revision=row['revision']+1)
        return {'work_id':row['job_id'],'state':state,'reason':reason}
    def after_cycle(self,cycle,event,result):
        if cycle.intention_id and cycle.intention.kind=='REFLECTION' and event.reflection_experience_id:
            reflected=self.store.db.execute('SELECT 1 FROM subject_reflections WHERE experience_id=?',(event.reflection_experience_id,)).fetchone()
            intention=self.store.one('subject_intentions',cycle.intention_id)
            if reflected and intention and intention['state']=='PENDING':self.runtime.subject.transition_intention(cycle.intention_id,expected_revision=intention['revision'],state='COMPLETED')
        self.concerns.after_cycle(cycle,event,result)
        if self.skills and event.world_concern_id:
            concern=self.store.one('open_concerns',event.world_concern_id)
            if concern:
                b=self.records.read(concern['record_id'])['payload']
                if b['skill_task'] and cycle.evaluation and cycle.evaluation.normative=='ENDORSED':self.skills.select(cycle,b['skill_task'])
    def view(self,*,scopes=None,privacy_classes=None):
        scopes=tuple(scopes or self.runtime.config.scopes);privacy=tuple(privacy_classes or self.runtime.config.privacy_classes)
        world=WorldModel(self.store,scopes=scopes,privacy_classes=privacy)
        return {'beliefs':[x.model_dump(mode='json') for x in world.snapshot()], 'concerns':self.concerns.view(scopes=scopes,privacy_classes=privacy),'cognition':self.cognition.journal(scopes=scopes,privacy_classes=privacy),'live_provider':'NOT_RUN_UNLESS_EXPLICITLY_CONFIGURED','execution_authority':'NONE_FROM_VIEW'}
