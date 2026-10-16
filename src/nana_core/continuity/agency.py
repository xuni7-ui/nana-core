"""Adoption and progress transitions, not a second decision loop or executor.

A trusted finite offline program policy can adopt an endorsed C candidate. Every
step is reconsidered by C, then existing Manager/Kernel/Grant/Budget/Verify gates.
"""
import json
from ..contracts import CoreError
from ..storage import canonical,digest,uid
from ..actions import OperatorAuthority
from ..planning import PlanCompiler
from .records import RecordService
from .memory import MemoryService
from .contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from .agency_contracts import OfflineProgram,GoalStepRef,PlanStepView
from .autonomy.contracts import RealizationTarget
from .autonomy.realization import GovernedRealization
from .learning import ExperienceService,ExperienceInput


def step_view(store,reference,*,scope,privacy_classes):
    if store.schema_target<11:raise CoreError('LIVING_SCHEMA_REQUIRED')
    if store.schema_target>=12:
        row=store.one('jobs',reference.work_id)
        if row and row['record_id']:
            payload=RecordService(store).read(row['record_id'])['payload']
            if payload.get('format')=='OPEN_PLAN_V1':
                from .open_agency.service import open_step_view
                return open_step_view(store,reference,scope=scope,privacy_classes=privacy_classes)
    work=store.one('jobs',reference.work_id);records=RecordService(store)
    if not work or work['work_kind']!='GOAL' or work['revision']!=reference.revision or work['cursor']!=reference.cursor or work['state'] not in {'WAITING','RUNNING','PAUSED','UNKNOWN'}:
        raise CoreError('STALE_GOAL_STEP')
    head=store.one('continuity_records',work['record_id'])
    if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes or not records.current_support(head['record_id']):
        raise CoreError('GOAL_SOURCE_UNAVAILABLE')
    plan=records.read(head['record_id'])['payload']
    goal=store.one('goals',plan['goal_id'])
    if not goal or goal['state'] not in {'ACTIVE','BLOCKED'}:raise CoreError('GOAL_NOT_ACTIVE')
    step=plan['steps'][reference.cursor]
    return PlanStepView(reference=reference,goal_id=plan['goal_id'],plan_id=plan['plan_id'],
        target=RealizationTarget(capability=step['capability'],resource=step['resource'],operation='WRITE' if step['capability']=='reading.card.create' else 'READ',resource_class='ORDINARY'),
        record_id=head['record_id'],source_memory_ids=records.support(head['record_id']),task_class=plan['task_class'])

class OfflineGoalPolicy:
    """Application construction, immutable finite procedure data; no Grant field."""
    def __init__(self,programs):
        if not 1<=len(programs)<=16 or len({p.program_id for p in programs})!=len(programs):raise CoreError('FINITE_PROGRAM_POLICY_REQUIRED')
        self._programs={p.program_id:OfflineProgram.model_validate_json(p.model_dump_json()) for p in programs}
        self._review_sources={}
    def install_reviewed(self,program,proposal_id):
        if program.program_id in self._programs:
            if self._programs[program.program_id]!=program or self._review_sources.get(program.program_id)!=proposal_id:raise CoreError('PROGRAM_REGISTRY_COLLISION')
            return
        if len(self._programs)>=16:raise CoreError('PROGRAM_REGISTRY_CAPACITY')
        self._programs[program.program_id]=program;self._review_sources[program.program_id]=proposal_id
    def get(self,program_id):
        if program_id not in self._programs:raise CoreError('OFFLINE_PROGRAM_NOT_REVIEWED')
        return self._programs[program_id]

class AgencyService:
    def __init__(self,store,subject,authority,policy,port,*,step_interval_us=1_000_000):
        if store.schema_target<11 or type(policy) is not OfflineGoalPolicy or not isinstance(authority,OperatorAuthority):raise CoreError('OFFLINE_GOAL_POLICY_REQUIRED')
        if subject.store is not store:raise CoreError('AGENCY_STORE_MISMATCH')
        self.store,self.subject,self._authority,self.policy=store,subject,authority,policy
        self.records=RecordService(store);self.realization=GovernedRealization(store,port,authority)
        self.interval=step_interval_us

    def adopt(self,cycle):
        if not cycle.goal_candidate_id or not cycle.proposed_program_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED':return None
        existing=self.store.db.execute('SELECT goal_id FROM goals WHERE goal_key=?',(cycle.goal_candidate_id,)).fetchone()
        if existing:return existing[0]
        if self.store.db.execute("SELECT 1 FROM goals WHERE state IN ('PROPOSED','ACTIVE','BLOCKED')").fetchone():return None
        p=self.policy.get(cycle.proposed_program_id)
        review=self.policy._review_sources.get(p.program_id)
        if review and not self.records.current_support(review):raise CoreError('SKILL_SOURCE_RETIRED')
        candidate=self.store.one('subject_goal_candidates',cycle.goal_candidate_id)
        event=self.store.one('subject_events',cycle.event_id)
        if not candidate or candidate['state']!='PROPOSED' or event['scope']!=p.scope or p.motivation_source not in {m.source for m in cycle.motivations}:
            raise CoreError('GOAL_ADOPTION_SOURCE_MISMATCH')
        if not self.records.current_support(candidate['record_id']):raise CoreError('GOAL_SOURCE_UNAVAILABLE')
        from .subject.opportunities import cues_from
        cues=cues_from(self.store,self.records.support(candidate['record_id']),scope=p.scope,privacy_classes=self.subject.privacy_classes)
        if not any(c.program_id==p.program_id for _,c in cues):raise CoreError('GOAL_PROGRAM_SOURCE_REQUIRED')
        for _,cue in cues:
            if cue.program_id==p.program_id and cue.resource_ref and (cue.resource_ref!=p.source_resource or cue.resource_class!='ORDINARY'):
                raise CoreError('GOAL_SOURCE_HARD_DENY')
        base=[{'capability':'reading.source.read','resource':p.source_resource},{'capability':'reading.card.create','resource':p.output_resource}]
        strategies=[];lesson_records=[]
        for lesson in self.store.db.execute("SELECT * FROM lessons WHERE task_class='reading_card' AND state='ACTIVE' ORDER BY rowid DESC LIMIT 16"):
            head=self.store.one('continuity_records',lesson['record_id'])
            if head['scope']!=p.scope or head['privacy_class'] not in self.subject.privacy_classes or not self.records.current_support(head['record_id']):continue
            rule=self.records.read(head['record_id'])['payload']['rule'];lesson_records.append(head['record_id'])
            strategies.append({'strategy_id':lesson['lesson_id'],'revision':lesson['revision'],'status':'ACTIVE','body_json':canonical({'rule_json':canonical(rule)})})
        compiled=PlanCompiler().apply(base,strategies)
        gid,pid,wid=uid(),uid(),uid();now=self.store.clock.utc_now_us()
        with self.store.transaction('living.goal_adopted',{'goal_id':gid,'candidate_id':cycle.goal_candidate_id}) as tx:
            goal_record=self.records.create(tx,kind='ADOPTED_GOAL',scope=p.scope,payload={'purpose':cycle.intention.purpose,'candidate_id':cycle.goal_candidate_id,'program_id':p.program_id},records=(candidate['record_id'],))
            plan_record=self.records.create(tx,kind='AUTONOMOUS_PLAN',scope=p.scope,payload={'goal_id':gid,'plan_id':pid,'program':p.model_dump(mode='json'),'program_digest':digest(p.model_dump(mode='json')),'steps':compiled['steps'],'applied_strategies':compiled['applied_strategies'],'task_class':p.template},records=(goal_record,*lesson_records))
            tx.put('goals',{'goal_id':gid,'goal_key':cycle.goal_candidate_id,'event_id':self.store.one('continuity_records',cycle.record_id)['event_id'],'template':p.template,'state':'ACTIVE','version':1,'body_json':canonical({'record_id':goal_record,'plan_record_id':plan_record,'work_id':wid})})
            tx.put('plans',{'plan_id':pid,'goal_id':gid,'body_json':canonical({'record_id':plan_record})})
            tx.put('jobs',{'job_id':wid,'occurrence_key':'goal:'+gid,'due_at_us':now,'state':'WAITING','body_json':canonical({'goal_id':gid,'plan_id':pid}),
                'work_kind':'GOAL','record_id':plan_record,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
            tx.update('subject_goal_candidates',cycle.goal_candidate_id,state='ADOPTED')
            intention=self.store.one('subject_intentions',cycle.intention_id)
            if intention['state']=='PENDING':tx.update('subject_intentions',cycle.intention_id,state='COMPLETED',revision=intention['revision']+1)
        return gid

    def next_reference(self):
        row=self.store.db.execute("SELECT * FROM jobs WHERE work_kind='GOAL' AND state IN ('WAITING','RUNNING','UNKNOWN') AND due_at_us<=? ORDER BY due_at_us LIMIT 1",(self.store.clock.utc_now_us(),)).fetchone()
        return GoalStepRef(work_id=row['job_id'],revision=row['revision'],cursor=row['cursor']) if row else None

    def advance(self,reference,cycle):
        work=self.store.one('jobs',reference.work_id)
        # ACK-after-commit recovery may call this again, but never repeats a step.
        if not work or work['revision']!=reference.revision:return None
        head=self.store.one('continuity_records',work['record_id'])
        view=step_view(self.store,reference,scope=head['scope'],privacy_classes=self.subject.privacy_classes)
        plan=self.records.read(work['record_id'])['payload'];p=self.policy.get(plan['program']['program_id'])
        if digest(p.model_dump(mode='json'))!=plan['program_digest']:raise CoreError('OFFLINE_PROGRAM_DRIFT')
        source=self.store.one('subject_events',cycle.event_id)
        source_body=self.records.read(source['record_id'])['payload']['input']
        if source_body.get('goal_step')!=reference.model_dump(mode='json'):raise CoreError('GOAL_STEP_CYCLE_MISMATCH')
        if not cycle.intention_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED' or cycle.intention.kind!='ACTION_PROPOSAL':
            return self._park(work,view,'SUBJECT_DEFERRED')
        target=view.target
        if cycle.realization_target!=target:raise CoreError('GOAL_STEP_TARGET_MISMATCH')
        if target.capability.startswith('reading.source.'):
            args={'source_id':target.resource}
        else:
            # Reuse only independently verified preceding step outputs.
            outputs=self._outputs(view.goal_id)
            read=next((o for o in outputs if o['capability']=='reading.source.read'),None)
            if not read:raise CoreError('GOAL_REQUIRES_VERIFIED_READ')
            text=json.loads(self.records.memory.read(read['memory_id'])['text'])
            located=next((o for o in outputs if o['capability']=='reading.source.locate'),None)
            locator=json.loads(self.records.memory.read(located['memory_id'])['text']).get('locator') if located else None
            args={'source_id':p.source_resource,'source_digest':digest(text),'content':text.get('text','Verified synthetic source'),'locator':locator}
        old=self.store.db.execute('SELECT action_id FROM actions WHERE effect_slot=?',('subject:'+cycle.intention_id,)).fetchone()
        try:
            if old:action_id=old[0]
            else:
                outcome,action_id=self.realization.propose(cycle.intention_id,expected_revision=1,args=args)
                if not action_id:return self._park(work,view,'MANAGER_'+outcome.result)
                with self.store.transaction('living.action_bound',{'goal_id':view.goal_id,'work_id':work['job_id']}) as tx:
                    tx.update('actions',action_id,goal_id=view.goal_id,plan_id=view.plan_id)
            state=self.realization.dispatch(cycle.intention_id,action_id,expected_revision=1)
        except CoreError as exc:
            return self._park(work,view,'REALIZATION_'+exc.code)
        if state!='SUCCEEDED':return self._park(work,view,'EFFECT_'+state,unknown=state=='UNKNOWN')
        action=self.store.one('actions',action_id)
        verification=self.store.event(json.loads(action['body_json'])['verification_event_id'])
        memory=MemoryService(self.store);text=self.realization.kernel.payload(action,'result_json');when=verification['recorded_at_us']
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.verified-action',source_reference=action_id,source_kind='SYSTEM_VERIFICATION'),text=text,privacy_class=head['privacy_class'],event_time_us=when,observed_time_us=when))
        mid=memory.add(MemoryCandidate(entity_id=source['entity_id'],scope=head['scope'],memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,derived_from=view.source_memory_ids,confidence=1.0))
        final=reference.cursor+1==len(plan['steps'])
        experience=None
        if final:
            learning=ExperienceService(self.store,self._authority)
            old_exp=self.store.db.execute('SELECT experience_id FROM experiences WHERE result_memory_id=? AND task_class=?',(mid,p.template)).fetchone()
            if old_exp:experience=old_exp[0]
            else:
                check=learning.verify_reading_result(mid,self._authority)
                experience=learning.record(ExperienceInput(context_memory_ids=view.source_memory_ids[:32],scope=head['scope'],task_class=p.template,decision=cycle.judgment.reason,result_memory_id=mid,verification_memory_id=check))
        data={'goal_id':view.goal_id,'work_id':work['job_id'],'cursor':reference.cursor,'action_id':action_id,'capability':target.capability,'memory_id':mid,'experience_id':experience}
        with self.store.transaction('living.goal_step_completed',data,source_namespace='living.goal-step',source_key=work['job_id']+':'+str(reference.cursor)) as tx:
            fresh=self.store.one('jobs',work['job_id'])
            if fresh['revision']!=reference.revision:raise CoreError('STALE_GOAL_STEP')
            tx.update('jobs',work['job_id'],cursor=reference.cursor+1,revision=reference.revision+1,state='DONE' if final else 'WAITING',owner_epoch=None,due_at_us=self.store.clock.utc_now_us()+self.interval,updated_at_us=self.store.clock.utc_now_us())
            if final:
                outcome=self.store.one('experiences',experience)['outcome']
                goal=self.store.one('goals',view.goal_id)
                tx.update('goals',view.goal_id,state='COMPLETED' if outcome=='SUCCESS' else 'FAILED',version=goal['version']+1)
            i=self.store.one('subject_intentions',cycle.intention_id)
            if i['state']=='PENDING':tx.update('subject_intentions',cycle.intention_id,state='COMPLETED',revision=i['revision']+1)
        return data

    def _outputs(self,goal_id):
        return [json.loads(r[0])['data'] for r in self.store.db.execute("SELECT data_json FROM events WHERE kind='living.goal_step_completed' AND json_extract(data_json,'$.data.goal_id')=? ORDER BY seq",(goal_id,))]

    def reconsider(self,goal_id,*,cause_memory_id,expected_version,authority):
        """Fresh supported opportunity, never revocation -> replay of an old will."""
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        goal=self.store.one('goals',goal_id)
        if not goal or goal['version']!=expected_version or goal['state']!='BLOCKED':raise CoreError('STALE_OR_NONBLOCKED_GOAL')
        if self.store.db.execute("SELECT 1 FROM actions WHERE goal_id=? AND state IN ('READY','DISPATCHING','UNKNOWN','PENDING_VERIFY')",(goal_id,)).fetchone():raise CoreError('VERIFY_UNKNOWN_EFFECT_FIRST')
        meta=json.loads(goal['body_json']);work=self.store.one('jobs',meta['work_id'])
        plan=self.records.read(work['record_id']);cause=self.records.memory.read(cause_memory_id)
        if cause['scope']!=plan['scope'] or cause['authority']!='DIRECT' or cause['observed_time_us']<work['updated_at_us']:raise CoreError('FRESH_RECONSIDERATION_SOURCE_REQUIRED')
        with self.store.transaction('living.goal_reconsidered',{'goal_id':goal_id,'cause_memory_id':cause_memory_id}) as tx:
            rid=self.records.create(tx,kind='AUTONOMOUS_PLAN',scope=plan['scope'],payload=plan['payload'],records=(work['record_id'],),memories=(cause_memory_id,))
            tx.update('jobs',work['job_id'],record_id=rid,state='WAITING',revision=work['revision']+1,due_at_us=self.store.clock.utc_now_us(),updated_at_us=self.store.clock.utc_now_us())
            tx.update('plans',json.loads(work['body_json'])['plan_id'],body_json=canonical({'record_id':rid}))
            tx.update('goals',goal_id,state='ACTIVE',version=goal['version']+1,body_json=canonical({**meta,'plan_record_id':rid}))
        return goal_id

    def _park(self,work,view,reason,unknown=False):
        body=json.loads(work['body_json']);tries=body.get('verify_checks',0)+(1 if unknown else 0)
        unknown=unknown and tries<=3
        if tries:body['verify_checks']=tries
        with self.store.transaction('living.goal_parked',{'goal_id':view.goal_id,'work_id':work['job_id'],'reason':reason}) as tx:
            tx.update('jobs',work['job_id'],state='UNKNOWN' if unknown else 'BLOCKED',revision=work['revision'] if unknown else work['revision']+1,owner_epoch=None,
                body_json=canonical(body),due_at_us=self.store.clock.utc_now_us()+self.interval*max(1,tries),updated_at_us=self.store.clock.utc_now_us())
            g=self.store.one('goals',view.goal_id);tx.update('goals',view.goal_id,state='BLOCKED',version=g['version']+1)
        return {'reason':reason,'goal_id':view.goal_id}
