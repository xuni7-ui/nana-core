"""Original G's bounded practice-selection lesson; never replace its grader."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService

class LearningStrategyLesson(DTO):
    kind:Literal['LEARNING_STRATEGY']='LEARNING_STRATEGY'
    scope:Literal['learning.hypothesis-selection']='learning.hypothesis-selection'
    domain:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    approach:Literal['PRACTICE_FILTER_BEFORE_COMMIT']='PRACTICE_FILTER_BEFORE_COMMIT'
    trial_record_id:str=Field(min_length=1,max_length=128)
    experiment_memory_id:str|None=None
    changes_evaluator:Literal[False]=False
    grants_authority:Literal[False]=False

def checks(records,rule):
    trial=records.read(rule.trial_record_id);b=trial['payload'];results=b.get('results',{})
    import json
    experiment=records.memory.read(rule.experiment_memory_id) if rule.experiment_memory_id else None
    data=json.loads(experiment['text']).get('data',{}) if experiment else {}
    return {'current_trial':trial['record_kind']=='LEARNING_TRIAL' and records.current_support(rule.trial_record_id),
        'same_domain':b.get('domain')==rule.domain,
        'improved':results.get('EVALUATE',{}).get('passed',0)>results.get('BASELINE',{}).get('passed',0),
        'practice_heldout_transfer':all(results.get(k,{}).get('all_passed') and results[k].get('checked',0)>0 for k in ('PRACTICE','EVALUATE','TRANSFER')),
        'independent_selection_experiment':bool(experiment and experiment['authority']=='DIRECT' and experiment['source_provenance']['source_kind']=='SYSTEM_VERIFICATION' and data.get('criterion_met') is True and data.get('filtered_passed',0)>data.get('baseline_passed',0)),
        'not_verifier_replacement':not rule.changes_evaluator,'no_authority':not rule.grants_authority}

def propose(store,method_lesson_id,*,authority):
    records=RecordService(store);lesson=store.one('lessons',method_lesson_id)
    if not lesson or lesson['state']!='ACTIVE':raise CoreError('META_VERIFIED_METHOD_LESSON_REQUIRED')
    head=records.read(lesson['record_id']);rule=head['payload']['rule']
    if rule.get('kind')!='METHOD_SELECTION' or not records.current_support(head['record_id']):raise CoreError('META_VERIFIED_METHOD_LESSON_REQUIRED')
    candidate=LearningStrategyLesson(domain=lesson['task_class'],trial_record_id=rule['trial_record_id'])
    if not all(v for k,v in checks(records,candidate).items() if k!='independent_selection_experiment'):raise CoreError('META_TRIAL_NOT_QUALIFIED')
    key='meta-learning:'+digest([method_lesson_id,candidate.model_dump(mode='json')])
    old=store.db.execute("SELECT lesson_id FROM lessons l JOIN continuity_records r ON l.record_id=r.record_id WHERE r.target_id=?",(key,)).fetchone()
    if old:return old[0]
    # One Experience has one Lesson. Run a separate, explicitly attributed
    # selection experiment through the original Experience gate; never duplicate
    # or rewrite the method-learning Experience just to attach another rule.
    from ..learning import ExperienceService,ExperienceInput
    from ..open_agency.learning import LearningSpec,IndependentEvaluator
    trial=records.read(candidate.trial_record_id)['payload']
    job=store.one('jobs',trial['work_id'])
    spec=LearningSpec.model_validate_json(canonical(records.read(job['record_id'])['payload']['spec']))
    evaluator=IndependentEvaluator()
    chosen=next((m for m in spec.hypotheses if evaluator.evaluate(m,spec.practice)['all_passed']),None)
    if not chosen:raise CoreError('META_NO_PRACTICE_CANDIDATE')
    baseline=evaluator.evaluate(spec.baseline_method,spec.evaluation)
    checked=evaluator.evaluate(chosen,spec.evaluation)
    from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    data={'baseline_passed':baseline['passed'],'filtered_passed':checked['passed'],'practice_only_selection':True,'fixed_independent_evaluator':True,'criterion_met':checked['passed']>baseline['passed']}
    text=canonical({'data':data,'origin':'INDEPENDENT_EXECUTED_META_TRIAL_NOT_NEW_WORLD_FACT'})
    project=head['privacy_class']=='PROJECT'
    eid=records.memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT' if project else 'SYNTHETIC_ONLY',source_namespace='recorded.project.learning-transfer' if project else 'synthetic.learning-strategy',source_reference=key,source_kind='SYSTEM_VERIFICATION'),text=text,privacy_class=head['privacy_class'],observed_time_us=head['created_at_us']))
    previous=store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(eid,)).fetchone()
    mid=previous[0] if previous else records.memory.add(MemoryCandidate(entity_id=store.identity['identity_id'],scope=head['scope'],memory_type=MemoryType.PROCEDURAL,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,derived_from=records.support(head['record_id'])))
    service=ExperienceService(store,authority)
    prior=store.db.execute('SELECT experience_id FROM experiences WHERE result_memory_id=?',(mid,)).fetchone()
    if prior:experience_id=prior[0]
    else:
        verification=service.verify_structured_result(mid,digest({**data,'criterion_met':True}),authority)
        experience_id=service.record(ExperienceInput(context_memory_ids=records.support(head['record_id'])[:32],scope=head['scope'],task_class='learning.strategy',decision='Evaluate practice-filter selection with the unchanged independent heldout checker',result_memory_id=mid,verification_memory_id=verification))
    candidate=candidate.model_copy(update={'experiment_memory_id':mid});lid=uid()
    with store.transaction('learning.strategy_candidate',{'lesson_id':lid}) as tx:
        rid=records.create(tx,kind='LESSON',scope=head['scope'],payload={'rule':candidate.model_dump(mode='json')},records=(head['record_id'],candidate.trial_record_id,store.one('experiences',experience_id)['record_id']),target_id=key)
        tx.put('lessons',{'lesson_id':lid,'experience_id':experience_id,'record_id':rid,'task_class':'learning.strategy','revision':1,'state':'CANDIDATE','tested_rule_hash':None,'test_event_id':None})
    return lid

def select(store,problem,*,scope,privacy):
    records=RecordService(store)
    for row in store.db.execute("SELECT * FROM lessons WHERE task_class='learning.strategy' AND state='ACTIVE' ORDER BY rowid DESC LIMIT 8"):
        head=store.one('continuity_records',row['record_id'])
        if not head or head['scope']!=scope or head['privacy_class'] not in privacy or head['lifecycle']!='ACTIVE' or not records.current_support(head['record_id']):continue
        rule=LearningStrategyLesson.model_validate_json(canonical(records.read(head['record_id'])['payload']['rule']))
        if rule.domain!=problem.domain:continue
        from ..open_agency.learning import IndependentEvaluator
        for method in problem.hypotheses:
            if IndependentEvaluator().evaluate(method,problem.practice)['all_passed']:return method,head['record_id']
        return problem.baseline_method,head['record_id']
    return None,None
