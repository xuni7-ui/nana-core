"""Significance gate and independent non-execution verification, not learning by fiat."""
import json
from typing import Literal
from pydantic import Field
from ...actions import OperatorAuthority
from ...contracts import DTO,CoreError
from ...storage import canonical,digest
from ..records import RecordService
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType

class ConsequenceObservation(DTO):
    disposition_record_id: str
    kind: Literal['MEANINGFUL_DOWNSTREAM','VALIDATES_REASONING','DISPROVES_REASONING','RELATIONSHIP_EFFECT','PROJECT_OUTCOME']
    assessment: Literal['UNASSESSED','HELPFUL','HARMFUL'] = 'UNASSESSED'
    description: str = Field(min_length=1,max_length=512)

class DispositionQualityCheck(DTO):
    schema_version: Literal[1] = 1
    check: Literal['DISPOSITION_OUTCOME'] = 'DISPOSITION_OUTCOME'
    result_memory_id: str
    result_artifact_digest: str
    candidate_record_id: str
    disposition_record_id: str
    factual_code: str
    reasoning_assessment: Literal['UNASSESSED','HELPFUL','HARMFUL']

class DispositionRule(DTO):
    kind: Literal['CONSIDER_VERIFIED_CONSEQUENCE'] = 'CONSIDER_VERIFIED_CONSEQUENCE'
    scope: Literal['disposition.review'] = 'disposition.review'
    assessment: Literal['HELPFUL','HARMFUL']
    grants_authority: Literal[False] = False

def lesson_method(rule=None):
    return 'ask_for_review_without_bypass' if rule and rule.assessment=='HARMFUL' else 'review_context_before_repeating' if rule else 'no_learned_consequence'

def disposition_fact(store,record_id):
    records=RecordService(store);row=store.one('continuity_records',record_id)
    if not row or row['record_kind']!='INTENTION_DISPOSITION' or not records.current_support(record_id):raise CoreError('DISPOSITION_SOURCE_UNAVAILABLE')
    body=records.read(record_id)['payload'];cycle=store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(body['cycle_id'],)).fetchone()
    if not cycle:raise CoreError('DISPOSITION_CYCLE_MISSING')
    raw=records.read(cycle['record_id'])['payload']
    if raw.get('evaluation',{}).get('normative')!=body['normative']:raise CoreError('DISPOSITION_FACT_MISMATCH')
    event=store.event(row['event_id'])
    if event['kind'] not in {'subject.cycle_accepted','governance.outcome'}:raise CoreError('DISPOSITION_SOURCE_UNTRUSTED')
    actual='NONE'
    if body['stage']=='MANAGER':
        gate=next((records.read(e['parent_id'])['payload'] for e in store.db.execute("SELECT * FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD'",(record_id,)) if store.one('continuity_records',e['parent_id'])['record_kind']=='CONSTRAINT_OUTCOME'),None)
        if not gate or gate['intention_id']!=body['intention_id']:raise CoreError('DISPOSITION_GATE_MISMATCH')
        expected='REALIZATION_ELIGIBLE' if gate['result']=='PASS' else 'MANAGER_BLOCKED' if gate['result']=='BLOCK' else 'MANAGER_UNKNOWN'
        if body['code']!=expected:raise CoreError('DISPOSITION_GATE_MISMATCH')
        actual=gate['actual_effect']
    elif body['stage']!='SUBJECT' or raw['evaluation']['disposition']!=body['code']:raise CoreError('DISPOSITION_FACT_MISMATCH')
    return {'disposition_record_id':record_id,'cycle_id':body['cycle_id'],'intention_id':body['intention_id'],
        'normative':body['normative'],'code':body['code'],'stage':body['stage'],'actual_effect_at_decision':actual,
        'reasoning_correctness':'NOT_ESTABLISHED_BY_DISPOSITION'}

class ExperienceCandidateService:
    def __init__(self,store,authority):
        if store.schema_target<9 or not isinstance(authority,OperatorAuthority):raise CoreError('CANDIDATE_CONTROLLER_REQUIRED')
        self.store,self._authority,self.records=store,authority,RecordService(store)

    def consider(self,disposition_record_id,*,consequence_memory_id=None,selection_cycle_id=None):
        fact=disposition_fact(self.store,disposition_record_id)
        parent=self.store.one('continuity_records',disposition_record_id);reason=None;memories=[];parents=[disposition_record_id]
        if consequence_memory_id:
            head=self.store.one('memories',consequence_memory_id)
            if not head or head['scope']!=parent['scope']:raise CoreError('CONSEQUENCE_SCOPE_MISMATCH')
            memory=self.records.memory.read(consequence_memory_id);source=self.records.memory.evidence(memory['source_evidence_id'])
            if memory['observed_time_us']<parent['created_at_us']:raise CoreError('CONSEQUENCE_PRECEDES_DISPOSITION')
            if source['source_kind'] not in {'DIRECT_OBSERVATION','SYSTEM_VERIFICATION'} or memory['epistemic_kind']!='OBSERVATION':raise CoreError('CONSEQUENCE_INDEPENDENT_SOURCE_REQUIRED')
            obs=ConsequenceObservation.model_validate_json(memory['text'])
            if obs.disposition_record_id!=disposition_record_id:raise CoreError('CONSEQUENCE_TARGET_MISMATCH')
            reason=obs.kind;memories.append(consequence_memory_id)
        if selection_cycle_id:
            cycle=self.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(selection_cycle_id,)).fetchone()
            if not cycle or cycle['judgment']!='REFLECT':raise CoreError('REFLECTION_SELECTION_REQUIRED')
            payload=self.records.read(cycle['record_id'])['payload']
            source=self.store.one('subject_events',payload['event_id'])
            if source['scope']!=parent['scope']:raise CoreError('REFLECTION_SELECTION_SCOPE_MISMATCH')
            if payload.get('selected_disposition_id')!=disposition_record_id:raise CoreError('REFLECTION_SELECTION_TARGET_MISMATCH')
            reason=reason or 'REFLECTION_SELECTED';parents.append(cycle['record_id'])
        if reason is None:
            seen=set();pattern=[]
            for r in self.store.db.execute("SELECT * FROM continuity_records WHERE record_kind='INTENTION_DISPOSITION' AND scope=? AND lifecycle='ACTIVE' ORDER BY created_at_us DESC,rowid DESC LIMIT 64",(parent['scope'],)):
                if not self.records.current_support(r['record_id']):continue
                other=self.records.read(r['record_id'])['payload']
                if other['code']==fact['code'] and other['intention_id'] and other['intention_id'] not in seen:
                    seen.add(other['intention_id']);pattern.append(r['record_id'])
            if len(seen)>=3:reason='REPEATED_PATTERN';parents.extend(pattern[:8])
        if reason is None:return None
        old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='autonomy.experience_candidate' AND source_key=?",(disposition_record_id,)).fetchone()
        if old:
            rid=json.loads(old[0])['data']['record_id'];self.records.read(rid);return rid
        data={'target_id':disposition_record_id}
        with self.store.transaction('autonomy.experience_candidate',data,source_namespace='autonomy.experience_candidate',source_key=disposition_record_id) as tx:
            rid=self.records.create(tx,kind='EXPERIENCE_CANDIDATE',scope=parent['scope'],target_id=disposition_record_id,
                payload={'fact':fact,'reason':reason,'consequence_memory_id':consequence_memory_id,'selection_cycle_id':selection_cycle_id},records=tuple(dict.fromkeys(parents)),memories=tuple(memories))
            data['record_id']=rid
        return rid

    def verify(self,candidate_record_id,authority):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        candidate=self.records.read(candidate_record_id)
        if candidate['record_kind']!='EXPERIENCE_CANDIDATE' or not self.records.current_support(candidate_record_id):raise CoreError('EXPERIENCE_CANDIDATE_UNAVAILABLE')
        body=candidate['payload'];fact=disposition_fact(self.store,body['fact']['disposition_record_id'])
        if fact!=body['fact']:raise CoreError('DISPOSITION_FACT_MISMATCH')
        assessment='UNASSESSED'
        if body['consequence_memory_id']:
            item=self.records.memory.read(body['consequence_memory_id']);obs=ConsequenceObservation.model_validate_json(item['text']);assessment=obs.assessment
        def capture(namespace,text,parents):
            time=candidate['created_at_us']
            eid=self.records.memory.capture(EvidenceInput(provenance=Provenance(source_namespace=namespace,source_reference=candidate_record_id,source_kind='SYSTEM_VERIFICATION'),
                text=text,privacy_class=candidate['privacy_class'],event_time_us=time,observed_time_us=time))
            source=self.store.one('subject_events',self.store.db.execute('SELECT subject_event_id FROM subject_cycles WHERE cycle_id=?',(fact['cycle_id'],)).fetchone()[0])
            return self.records.memory.add(MemoryCandidate(entity_id=source['entity_id'],scope=candidate['scope'],memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,confidence=1.0,derived_from=tuple(parents)))
        support=self.records.support(candidate_record_id)
        if len(support)>64:raise CoreError('EXPERIENCE_SUPPORT_CAPACITY')
        result=capture('synthetic.disposition-result',canonical({'candidate_record_id':candidate_record_id,'fact':fact,'reasoning_assessment':assessment}),support)
        row=self.records.memory.read(result)
        proof=DispositionQualityCheck(result_memory_id=result,result_artifact_digest=digest(self.store.artifact(row['payload_artifact_id'])),
            candidate_record_id=candidate_record_id,disposition_record_id=fact['disposition_record_id'],factual_code=fact['code'],reasoning_assessment=assessment)
        verification=capture('synthetic.disposition-check',proof.model_dump_json(),(result,))
        return result,verification
