"""C-selected skill need → bounded existing code lifecycle, one slice at a time."""
from ...contracts import CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from ..open_agency.code_skills import CodeSpec,CodeCandidate,CodeSkillService
from ..open_agency.learning import LearningCase

class TransformCodeProposer:
    """Reference replaceable code proposer, explicitly deterministic not a model."""
    def implement(self,spec,diagnostic=None):
        if spec.task=='TEXT_CLEAN':
            expr='data.strip().casefold()' if diagnostic else 'data.strip()'
        elif spec.task=='TOKEN_ANALYSIS':
            expr="{'tokens': sorted(data.casefold().split()), 'count': len(data.split())}" if diagnostic else "{'tokens': sorted(data.split()), 'count': len(data.split())}"
        else:raise CoreError('REFERENCE_SKILL_TASK_UNAVAILABLE')
        return CodeCandidate(source='def transform(data):\n    return '+expr+'\n')

def default_skill_specs():
    return {
        'TEXT_CLEAN':(CodeSpec(name='text-clean',revision=1,purpose='Normalize surrounding whitespace and case',task='TEXT_CLEAN',skill_kind='BOUNDED_DATA'),(LearningCase(case_id='clean-a',context='captions',data=' Hello ',expected='hello'),LearningCase(case_id='clean-b',context='notes',data='\tWORLD\n',expected='world'))),
        'TOKEN_ANALYSIS':(CodeSpec(name='token-analysis',revision=1,purpose='Compose normalization, ordering and token-count analysis',task='TOKEN_ANALYSIS',skill_kind='BOUNDED_ANALYSIS_WORKFLOW'),(LearningCase(case_id='analysis-a',context='captions',data='Zulu alpha',expected={'tokens':['alpha','zulu'],'count':2}),LearningCase(case_id='analysis-b',context='notes',data='B A A',expected={'tokens':['a','a','b'],'count':3})))
    }

class SelfExtensionWork:
    def __init__(self,runtime,*,specs=None,proposer=None,publish_opportunity=True,test_slice_size=None):
        self.runtime,self.store=runtime,runtime.store;self.records=RecordService(self.store)
        self.codes=CodeSkillService(self.store,runtime.authority);self.specs=specs or default_skill_specs();self.proposer=proposer or TransformCodeProposer();self.cognition=None;self.publish_opportunity=publish_opportunity;self.test_slice_size=test_slice_size
    def select(self,cycle,task):
        if task not in self.specs or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED' or cycle.intention.behavior!='SEEK_CAPABILITY':raise CoreError('SUBJECT_SKILL_NEED_REQUIRED')
        key='world-skill:'+digest([cycle.record_id,task]);old=self.store.db.execute('SELECT job_id FROM jobs WHERE occurrence_key=?',(key,)).fetchone()
        if old:return old[0]
        # Completed source problem must not regenerate on a timer.
        if self.store.db.execute("SELECT 1 FROM jobs j JOIN continuity_records r ON j.record_id=r.record_id WHERE j.work_kind='CODE_DEVELOPMENT' AND r.target_id=?",(task,)).fetchone():return None
        now=self.store.clock.utc_now_us();wid=uid()
        with self.store.transaction('world.skill_need_selected',{'work_id':wid}) as tx:
            rid=self.records.create(tx,kind='SKILL_PROPOSAL',scope=self.records.read(cycle.record_id)['scope'],payload={'cycle_id':cycle.cycle_id,'source_program_id':cycle.proposed_program_id,'task':task,'stage':'GENERATE','candidate_record_id':None,'diagnostic':None},records=(cycle.record_id,),target_id=task)
            i=self.store.one('subject_intentions',cycle.intention_id)
            if i and i['state']=='PENDING':tx.update('subject_intentions',i['intention_id'],state='COMPLETED',revision=i['revision']+1)
            if cycle.goal_candidate_id:tx.update('subject_goal_candidates',cycle.goal_candidate_id,state='ADOPTED')
            tx.put('jobs',{'job_id':wid,'occurrence_key':key,'due_at_us':now,'state':'WAITING','body_json':'{}','work_kind':'CODE_DEVELOPMENT','record_id':rid,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
        return wid
    def slice(self):
        row=self.store.db.execute("SELECT * FROM jobs WHERE work_kind='CODE_DEVELOPMENT' AND state='WAITING' ORDER BY due_at_us LIMIT 1").fetchone()
        if not row:return None
        head=self.records.read(row['record_id']);b=dict(head['payload'])
        if not self.records.current_support(row['record_id']):return self._park(row,'CANCELLED','SOURCE_RETIRED')
        if b['task'] not in self.specs:return self._park(row,'BLOCKED','SKILL_POLICY_CHANGED')
        spec,cases=self.specs[b['task']];cycle_row=self.store.one('subject_cycles',b['cycle_id']);cycle=self.runtime.subject.result(cycle_row)
        stage=b['stage']
        try:
            # A crash between candidate revision and job cursor commit may leave
            # the exact candidate superseded. Resolve only its own current chain.
            if b['candidate_record_id']:
                old=self.store.one('continuity_records',b['candidate_record_id'])
                if old and old['lifecycle']=='SUPERSEDED':
                    current=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='CODE_SKILL' AND target_id=? AND lifecycle='ACTIVE' ORDER BY rowid DESC LIMIT 1",(old['target_id'],)).fetchone()
                    if current:b['candidate_record_id']=current[0]

            if stage in {'GENERATE','REPAIR'}:
                if stage=='REPAIR':spec=spec.model_copy(update={'revision':2})
                proposer=self.proposer
                if self.cognition:
                    from .ports import CognitionCodeProposer,bounded_sources
                    proposer=CognitionCodeProposer(self.cognition,bounded_sources(self.cognition,self.records.support(cycle.record_id)))
                b['candidate_record_id']=self.codes.propose(cycle,spec,proposer,diagnostic=b['diagnostic']);b['stage']='TEST'
            elif stage=='TEST':
                tested=self.codes.test(b['candidate_record_id'],cases,max_cases=self.test_slice_size);body=self.records.read(tested)['payload'];b['candidate_record_id']=tested
                if body['state']=='TESTING':b['stage']='TEST'
                elif body['state']=='REJECTED':
                    if b['diagnostic']:return self._park(row,'BLOCKED','REPAIR_DID_NOT_PASS')
                    b['diagnostic']='Independent cases failed; preserve contract and repair transformation';b['stage']='REPAIR'
                else:b['stage']='REVIEW'
            elif stage=='REVIEW':
                body=self.records.read(b['candidate_record_id'])['payload']
                if body['state']=='ACTIVE':
                    self.codes.revalidate(b['candidate_record_id'],cases,authority=self.runtime.authority);b['stage']='ACTIVE'
                else:
                    if b['candidate_record_id'] not in self.codes._tested:
                        b['candidate_record_id']=self.codes.test(b['candidate_record_id'],cases,max_cases=self.test_slice_size)
                        body=self.records.read(b['candidate_record_id'])['payload']
                    if body['state']=='TESTING':b['stage']='TEST'
                    else:b['candidate_record_id']=self.codes.review(b['candidate_record_id'],authority=self.runtime.authority,expected_digest=body['source_digest']);b['stage']='ACTIVE'
            else:return self._park(row,'BLOCKED','CURRENT_REALM_REVIEW_REQUIRED')
        except CoreError as exc:return self._park(row,'UNKNOWN',exc.code)
        with self.store.transaction('world.skill_development_slice',{'work_id':row['job_id'],'stage':stage}) as tx:
            rid=self.records.create(tx,kind='SKILL_PROPOSAL',scope=head['scope'],payload=b,records=(row['record_id'],b['candidate_record_id']),supersedes=row['record_id'],target_id=b['task'])
            tx.update('jobs',row['job_id'],record_id=rid,state='DONE' if b['stage']=='ACTIVE' else 'WAITING',cursor=row['cursor']+1,revision=row['revision']+1)
        observation=None
        if b['stage']=='ACTIVE' and self.publish_opportunity:
            from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
            case=cases[0];resource='synthetic://skill/data' if spec.skill_kind=='BOUNDED_DATA' else 'synthetic://skill/analysis'
            payload={'opportunities':[{'topic':'try-'+spec.name,'motive':'COMPETENCE','resource':resource,'domain':'skill-use','skill_record_id':b['candidate_record_id'],'data':case.data,'expected':case.expected,'value':'HIGH','scope':head['scope']}], 'fact':'Reviewed pure local skill available; no new capability or Grant'}
            memory=self.records.memory;when=self.store.clock.utc_now_us();text=canonical(payload)
            eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.skill-review',source_reference=b['candidate_record_id'],source_kind='SYSTEM_VERIFICATION'),text=text,privacy_class=head['privacy_class'],observed_time_us=when))
            previous=self.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(eid,)).fetchone()
            observation=previous[0] if previous else memory.add(MemoryCandidate(entity_id=self.runtime.config.entity_id,scope=head['scope'],memory_type=MemoryType.PROCEDURAL,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,derived_from=self.records.support(b['candidate_record_id']),confidence=1.))
        return {'work_id':row['job_id'],'stage':stage,'next_stage':b['stage'],'candidate_record_id':b['candidate_record_id'],'observation_memory_id':observation}
    def _park(self,row,state,reason):
        with self.store.transaction('world.skill_development_parked',{'work_id':row['job_id'],'reason':reason}) as tx:tx.update('jobs',row['job_id'],state=state,revision=row['revision']+1)
        return {'work_id':row['job_id'],'state':state,'reason':reason}
    def active(self):
        results=[]
        for row in self.store.db.execute("SELECT * FROM jobs WHERE work_kind='CODE_DEVELOPMENT' AND state='DONE' LIMIT 16"):
            if not self.records.current_support(row['record_id']):continue
            body=self.records.read(row['record_id'])['payload']
            results.append((body['task'],body['candidate_record_id']))
        return tuple(results)
