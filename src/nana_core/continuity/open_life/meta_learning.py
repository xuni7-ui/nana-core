"""Original G's bounded practice-selection lesson; never replace its grader."""
import json
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService

TRANSFER_COUNTEREXAMPLE_NAMESPACE = 'learning.strategy.transfer-counterexample'


def transfer_counterexample_key(problem, method, scope):
    baseline, hypotheses, examples = problem.experiment_material()
    return digest([scope, problem.domain, baseline, sorted(hypotheses), sorted(examples), method])


def recent_transfer_counterexample(store, problem, method, *, scope, privacy):
    if not privacy:
        return None
    key = transfer_counterexample_key(problem, method, scope)
    marks = ','.join('?' for _ in privacy)
    rows = store.db.execute(
        "SELECT r.record_id FROM events e JOIN jobs j ON j.job_id=json_extract(e.data_json,'$.data.work_id') "
        "JOIN continuity_records r ON r.record_id=j.record_id "
        "WHERE e.source_namespace=? AND e.source_key>=? AND e.source_key<? "
        "AND j.work_kind='LEARNING' AND j.state='BLOCKED' AND r.lifecycle='ACTIVE' AND r.scope=? "
        f"AND r.privacy_class IN ({marks}) ORDER BY e.seq DESC LIMIT 8",
        (TRANSFER_COUNTEREXAMPLE_NAMESPACE, key + ':', key + ';', scope, *privacy),
    )
    records = RecordService(store)
    return next((row['record_id'] for row in rows if records.current_support(row['record_id'])), None)


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
    experiment=records.memory.read(rule.experiment_memory_id) if rule.experiment_memory_id else None
    data=json.loads(experiment['text']).get('data',{}) if experiment else {}
    return {'current_trial':trial['record_kind']=='LEARNING_TRIAL' and records.current_support(rule.trial_record_id),
        'same_domain':b.get('domain')==rule.domain,
        'improved':results.get('EVALUATE',{}).get('passed',0)>results.get('BASELINE',{}).get('passed',0),
        'practice_heldout_transfer':all(results.get(k,{}).get('all_passed') and results[k].get('checked',0)>0 for k in ('PRACTICE','EVALUATE','TRANSFER')),
        'independent_selection_experiment':bool(experiment and experiment['authority']=='DIRECT'
            and experiment['source_provenance']['source_kind']=='SYSTEM_VERIFICATION'
            and data.get('criterion_met') is True and data.get('filtered_passed',0)>data.get('baseline_passed',0)
            and _selection_transferred(records,b,data)),
        'not_verifier_replacement':not rule.changes_evaluator,'no_authority':not rule.grants_authority}

def _first_passing_hypothesis(problem, evaluator, *, candidate_allowed=None):
    for method in problem.hypotheses:
        try:
            passed = evaluator.evaluate(method, problem.practice)['all_passed']
        except (CoreError, ValueError, TypeError):
            # These are sealed local methods. An inapplicable method may reject
            # practice inputs, while another current candidate can still fit.
            continue
        if passed and (candidate_allowed is None or candidate_allowed(method)):
            return method
    return None


def _original_spec(records,trial):
    from ..open_agency.learning import LearningSpec
    job=records.store.one('jobs',trial['work_id'])
    return LearningSpec.model_validate_json(canonical(records.read(job['record_id'])['payload']['spec']))


def _transfer_result(spec,evaluator,chosen):
    try:return evaluator.evaluate(chosen,spec.transfer)
    except (CoreError,ValueError,TypeError):return None


def _selection_transferred(records,trial,data):
    if 'transfer_checked' in data:
        return type(data['transfer_checked']) is int and data['transfer_checked']>0 and data.get('transfer_all_passed') is True
    # Recheck an older receipt in place using its original, separate cases.
    # Never replace the original selected candidate using these answers.
    from ..open_agency.learning import IndependentEvaluator
    try:
        spec=_original_spec(records,trial);evaluator=IndependentEvaluator()
        chosen=_first_passing_hypothesis(spec,evaluator)
        if not chosen or not evaluator.evaluate(chosen,spec.evaluation)['all_passed']:return False
        result=_transfer_result(spec,evaluator,chosen)
        return bool(result and result['all_passed'])
    except (CoreError,KeyError,TypeError,ValueError):return False


def propose(store,method_lesson_id,*,authority,consideration_records=()):
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
    from ..open_agency.learning import IndependentEvaluator
    trial=records.read(candidate.trial_record_id)['payload']
    spec=_original_spec(records,trial)
    evaluator=IndependentEvaluator()
    chosen=_first_passing_hypothesis(spec,evaluator)
    if not chosen:raise CoreError('META_NO_PRACTICE_CANDIDATE')
    baseline=evaluator.evaluate(spec.baseline_method,spec.evaluation)
    checked=evaluator.evaluate(chosen,spec.evaluation)
    transfer=_transfer_result(spec,evaluator,chosen)
    if not checked['all_passed'] or checked['passed']<=baseline['passed'] or not transfer or not transfer['all_passed']:
        raise CoreError('META_SELECTION_NOT_TRANSFERRED')
    from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    data={'baseline_passed':baseline['passed'],'filtered_passed':checked['passed'],'practice_only_selection':True,
        'fixed_independent_evaluator':True,'criterion_met':True,'transfer_checked':transfer['checked'],'transfer_all_passed':True}
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
        rid=records.create(tx,kind='LESSON',scope=head['scope'],payload={'rule':candidate.model_dump(mode='json')},
            records=(head['record_id'],candidate.trial_record_id,store.one('experiences',experience_id)['record_id'],*consideration_records),target_id=key)
        tx.put('lessons',{'lesson_id':lid,'experience_id':experience_id,'record_id':rid,'task_class':'learning.strategy','revision':1,'state':'CANDIDATE','tested_rule_hash':None,'test_event_id':None})
    return lid

def select(store,problem,*,scope,privacy,candidate_allowed=None):
    records=RecordService(store)
    if not privacy:return None,None
    allowed=tuple(dict.fromkeys(privacy));marks=','.join('?' for _ in allowed)
    # Eight relevant strategy candidates, not eight global rows. A newer
    # method for another domain/scope must not hide this problem's policy.
    rows=store.db.execute(
        "SELECT l.* FROM lessons l JOIN continuity_records h ON h.record_id=l.record_id "
        "JOIN artifacts a ON a.artifact_id=h.payload_artifact_id "
        "WHERE l.task_class='learning.strategy' AND l.state='ACTIVE' AND h.lifecycle='ACTIVE' "
        f"AND h.scope=? AND h.privacy_class IN ({marks}) "
        "AND CASE WHEN json_valid(CAST(a.payload AS TEXT)) "
        "THEN json_extract(CAST(a.payload AS TEXT),'$.rule.domain') END=? "
        "ORDER BY l.rowid DESC LIMIT 8",(scope,*allowed,problem.domain))
    for row in rows:
        head=store.one('continuity_records',row['record_id'])
        if not head or head['scope']!=scope or head['privacy_class'] not in privacy or head['lifecycle']!='ACTIVE' or not records.current_support(head['record_id']):continue
        rule=LearningStrategyLesson.model_validate_json(canonical(records.read(head['record_id'])['payload']['rule']))
        if rule.domain!=problem.domain or not all(checks(records,rule).values()):continue
        from ..open_agency.learning import IndependentEvaluator
        method=_first_passing_hypothesis(problem,IndependentEvaluator(),candidate_allowed=candidate_allowed)
        # The baseline is a comparison, and may not be a valid nomination.
        # Leave the current proposer in charge when this strategy finds no fit.
        return (method,head['record_id']) if method is not None else (None,None)
    return None,None
