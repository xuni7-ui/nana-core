"""Durable, finite attention queue. Only the original SubjectLoop chooses WHAT.

Jobs are delivery to C, never execution permission. Completion is reconstructed
from the committed original cycle, including across a crash before job ack.
"""
import json
from typing import Literal
from pydantic import Field
from ...contracts import DTO, CoreError
from ...storage import digest, uid
from ..records import RecordService
from ..subject.opportunities import ConcernCue,OpportunityAssessment
from ..subject.contracts import SubjectInput
from ...presence.contracts import RuntimeEvent, Cause, DAY


class ActivityCost(DTO):
    """Sourced host estimate, never billing truth or budget/Grant authority."""
    basis:Literal['HOST_STRUCTURAL_ESTIMATE']='HOST_STRUCTURAL_ESTIMATE'
    compute:Literal['LIGHT','HEAVY']='LIGHT'
    time:Literal['SHORT','LONG']='SHORT'
    external:Literal['NONE','REQUIRES_RESERVATION','UNKNOWN']='NONE'
    storage:Literal['SMALL','LARGE']='SMALL'
    interruption:Literal['LIGHT','HEAVY']='LIGHT'

    @property
    def pressure(self):
        return sum((self.compute=='HEAVY',self.time=='LONG',self.external!='NONE',self.storage=='LARGE',self.interruption=='HEAVY'))


class LifeOpportunity(DTO):
    kind: Literal['CONCERN','EXPERIENCE','CURIOSITY','RELATIONSHIP','GOAL',
                  'CAPABILITY_GAP','WORLD_CHANGE','MAINTENANCE','REST']
    topic: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    source_memory_ids: tuple[str,...] = Field(min_length=1,max_length=16)
    cue: ConcernCue
    value: Literal['LOW','RELEVANT','HIGH'] = 'RELEVANT'
    novelty: Literal['REPEATED','NEW'] = 'NEW'
    cost: Literal['LIGHT','HEAVY'] = 'LIGHT'
    resource_estimate:ActivityCost|None=None
    expires_at_us: int = Field(ge=0)
    reflection_experience_id:str|None=None


class OpportunityQueue:
    def __init__(self,runtime,*,capacity=16,daily_limit=8):
        if not 1<=capacity<=32 or not 1<=daily_limit<=24:raise CoreError('LIFE_QUEUE_POLICY_BOUND')
        self.runtime=runtime;self.store=runtime.store;self.records=RecordService(self.store)
        self.capacity,self.daily_limit=capacity,daily_limit

    def offer(self,candidate):
        c=LifeOpportunity.model_validate_json(candidate.model_dump_json())
        r=self.runtime;s=self.store
        if c.topic!=c.cue.topic_key:raise CoreError('LIFE_TOPIC_MISMATCH')
        if c.reflection_experience_id:
            exp=s.one('experiences',c.reflection_experience_id)
            if c.kind!='EXPERIENCE' or not exp or not self.records.current_support(exp['record_id']) or not set((exp['result_memory_id'],exp['verification_memory_id']))<=set(c.source_memory_ids):raise CoreError('LIFE_EXPERIENCE_CORRELATION_REQUIRED')
        sources=[self.records.memory.read(m) for m in c.source_memory_ids]
        if any(m['scope'] not in r.config.scopes or m['privacy_class'] not in r.config.privacy_classes or m['privacy_class'] not in {'PUBLIC','PROJECT'} for m in sources):raise CoreError('LIFE_SOURCE_DENIED')
        if len({m['scope'] for m in sources})!=1:raise CoreError('CROSS_SCOPE_DERIVATION')
        # Same supported event cannot make a new wish every wake/restart/day.
        key='life-opportunity:'+digest([c.kind,c.topic,sorted(c.source_memory_ids)])
        old=s.db.execute('SELECT job_id FROM jobs WHERE occurrence_key=?',(key,)).fetchone()
        if old:return old[0]
        pending=s.db.execute("SELECT count(*) FROM jobs j JOIN continuity_records r ON j.record_id=r.record_id WHERE j.work_kind='LIFE_OPPORTUNITY' AND j.state='WAITING' AND r.lifecycle='ACTIVE'").fetchone()[0]
        if pending>=self.capacity:raise CoreError('LIFE_QUEUE_BACKPRESSURE')
        now=r.clock.utc_now_us()
        reason='EXPIRED' if c.expires_at_us<=now else None
        jid=uid()
        with s.transaction('life.opportunity_offered',{'job_id':jid,'suppression':reason}) as tx:
            rid=self.records.create(tx,kind='RUNTIME_WORK',scope=sources[0]['scope'],
                payload={'kind':'LIFE_OPPORTUNITY','candidate':c.model_dump(mode='json'),'state':'SUPPRESSED' if reason else 'AVAILABLE','reason':reason},
                memories=c.source_memory_ids,target_id=key)
            tx.put('jobs',{'job_id':jid,'occurrence_key':key,'due_at_us':now,'state':'CANCELLED' if reason else 'WAITING','body_json':'{}',
                'work_kind':'LIFE_OPPORTUNITY','record_id':rid,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
        return jid

    def _finish(self,row,state,reason,cycle=None):
        head=self.records.read(row['record_id']);body={**head['payload'],'state':reason,'cycle_id':cycle['cycle_id'] if cycle else None}
        if cycle:
            result=self.runtime.subject.result(dict(cycle))
            body.update(behavior=result.intention.behavior,normative=result.evaluation.normative if result.evaluation else 'UNDECIDED')
        with self.store.transaction('life.opportunity_reviewed',{'job_id':row['job_id'],'state':reason}) as tx:
            rid=self.records.create(tx,kind='RUNTIME_WORK',scope=head['scope'],payload=body,records=(row['record_id'],*((cycle['record_id'],) if cycle else ())),supersedes=row['record_id'],target_id=head['target_id'])
            tx.update('jobs',row['job_id'],record_id=rid,state=state,revision=row['revision']+1,updated_at_us=self.runtime.clock.utc_now_us())
        return {'opportunity_id':row['job_id'],'state':reason,'not_execution':True}

    def opportunity(self):
        r=self.runtime;s=self.store;now=r.clock.utc_now_us()
        if r.work.paused:return None
        retired=s.db.execute("SELECT j.job_id,j.revision FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id WHERE j.work_kind='LIFE_OPPORTUNITY' AND j.state='WAITING' AND c.lifecycle!='ACTIVE' LIMIT 32").fetchall()
        if retired:
            with s.transaction('life.retired_opportunity_closed',{'count':len(retired)}) as tx:
                for item in retired:tx.update('jobs',item['job_id'],state='CANCELLED',revision=item['revision']+1,updated_at_us=now)
        rows=s.db.execute("SELECT j.* FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id WHERE j.work_kind='LIFE_OPPORTUNITY' AND j.state='WAITING' AND c.lifecycle='ACTIVE' ORDER BY j.due_at_us,j.rowid LIMIT 32").fetchall()
        viable=[]
        for row in rows:
            key='development.life.'+digest(row['occurrence_key'])
            cycle=s.db.execute('SELECT c.* FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id WHERE e.source_key=?',(key,)).fetchone()
            if cycle:return self._finish(row,'DONE','C_JUDGED',cycle)
            if not self.records.current_support(row['record_id']):return self._finish(row,'CANCELLED','SOURCE_RETIRED')
            head=self.records.read(row['record_id']);c=LifeOpportunity.model_validate_json(json.dumps(head['payload']['candidate']))
            if c.expires_at_us<=now:return self._finish(row,'CANCELLED','EXPIRED')
            viable.append((row,head,c))
        if not viable:return None
        day=now//DAY*DAY
        if s.db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'development.life.%' AND observed_at_us>=?",(day,)).fetchone()[0]>=self.daily_limit:return None
        # Attention ordering is finite; these are options, not pre-adopted goals.
        row,head,c=max(viable,key=lambda x:({'LOW':0,'RELEVANT':1,'HIGH':2}[x[2].value],x[2].kind=='REST',-(x[2].resource_estimate.pressure if x[2].resource_estimate else int(x[2].cost=='HEAVY')),-x[0]['due_at_us']))
        cue=c.cue.model_copy(update={'opportunity_assessment':OpportunityAssessment(value=c.value,novelty=c.novelty)})
        load=s.db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING'").fetchone()[0]
        if load>=4:cue=cue.model_copy(update={'cognitive_load':'HIGH'})
        # Compute/time/interruption estimates can inform attention demand.
        # External reservation and storage size concern later execution/capacity,
        # not evidence that the Subject is tired or cannot want the activity.
        # Keep every estimate for ordering/projection; this candidate grants no
        # resource allocation or execution authority.
        estimate=c.resource_estimate
        attention_pressure=bool(estimate and (estimate.compute=='HEAVY' or estimate.time=='LONG'
            or estimate.interruption=='HEAVY'))
        if c.cost=='HEAVY' or attention_pressure:cue=cue.model_copy(update={'cognitive_load':'HIGH'})
        from .sources import remember
        prior=s.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.material' AND e.source_reference=?",('open-life:cue:'+row['job_id'],)).fetchone()
        if prior:
            self.records.memory.read(prior[0]);mid=prior[0]
        else:mid=remember(r,'cue:'+row['job_id'],cue.model_dump(mode='json'),scope=head['scope'],privacy=head['privacy_class'],kind='MODEL_DERIVATION',parents=c.source_memory_ids,predicate='concern.'+c.topic)
        inp=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.life.'+digest(row['occurrence_key']),kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=head['scope'],privacy_class=head['privacy_class'],observed_at_us=row['due_at_us'],source_memory_ids=(mid,),novelty='RELEVANT',reflection_experience_id=c.reflection_experience_id)
        qid=r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=now,priority=0))
        return {'opportunity_id':row['job_id'],'queue_id':qid,'not_execution':True}

    def view(self):
        return projection(self.store,self.runtime.config.scopes,self.runtime.config.privacy_classes)


def projection(store,scopes,privacy):
    records=RecordService(store);out=[]
    for row in store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_OPPORTUNITY' ORDER BY rowid DESC LIMIT 32"):
        head=store.one('continuity_records',row['record_id'])
        if not head or head['lifecycle']!='ACTIVE' or head['scope'] not in scopes or head['privacy_class'] not in privacy:continue
        if not records.current_support(head['record_id']):continue
        b=records.read(head['record_id'])['payload'];c=b['candidate']
        out.append({'job_id':row['job_id'],'kind':c['kind'],'value':c['value'],'novelty':c['novelty'],'resource_estimate':c.get('resource_estimate'),'state':b['state'],'behavior':b.get('behavior'),'cycle_id':b.get('cycle_id'),'record_id':head['record_id']})
    return tuple(out)
