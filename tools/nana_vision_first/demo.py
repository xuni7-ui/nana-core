"""Finite public controlled-local growth experiment; no real dialogue/provider.

Environment/operator inputs are synthetic. Computation, SQLite, Kernel/Verify,
learning stages, independent held-out comparisons and subsequent use really run.
"""
import argparse,json,math,time
from pathlib import Path
from nana_core.contracts import GrantSpec,CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.world_loop.reference import open_runtime,context_policy
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject.growth_life import project,opportunities
from nana_core.continuity.open_agency.contracts import Objective,Operator
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.open_agency.delivery import RecipientState
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.continuity.open_agency.service import OpenGoalPolicy
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.records import RecordService
from nana_core.continuity.cognition import AnalyticalFixturePort,CautiousFixturePort
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeEvent,Cause,SECOND,HOUR


def source(r,key,text,*,kind='DIRECT_OBSERVATION',parents=(),predicate=None):
    text=text if isinstance(text,str) else canonical(text);m=MemoryService(r.store)
    eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.vision-first',source_reference=key,source_kind=kind),text=text,privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()))
    return m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE if predicate else MemoryType.EPISODIC,epistemic_kind='INFERENCE' if kind=='MODEL_DERIVATION' else 'OBSERVATION',source_evidence_id=eid,text=text,derived_from=parents,predicate_key=predicate))

def cue(r,key,c,parents=()):return source(r,key,c.model_dump_json(),kind='MODEL_DERIVATION' if parents else 'DIRECT_OBSERVATION',parents=parents,predicate='concern.'+c.topic_key)

def post(r,key,mids,**kw):
    event=SubjectInput(source_key='synthetic.vf2.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=mids,observed_at_us=r.clock.utc_now_us(),privacy_class='PUBLIC',**kw)
    r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=event,causes=(Cause(kind='MEMORY',reference_id=mids[0]),),due_at_us=r.clock.utc_now_us()))

def advance(r,clock,n):
    results=[]
    for _ in range(n):clock.advance(SECOND);v=r.step();results.append(v)
    return results

def objective(key,data):
    expected=math.fsum(data)
    return Objective(objective_id='sample.'+key,scope='world',motivation_source='CREATIVE_INTEREST',task_domain='numbers',desired=('measured',),operators=(
        Operator(operator_id='inspect',capability='world.observe',resource='synthetic://vf2/'+key+'/source',produces=('seen',),args={}),
        Operator(operator_id='measure',capability='world.compute',resource='synthetic://vf2/'+key+'/result',requires=('seen',),produces=('measured',),args={'method':'NAIVE_SUM','input_from':'inspect'},expected_digest=digest(expected),strategy_selectable=True)))

def configure(r,root,objectives,*,grant):
    world=OfflineEffectPort(r.identity_id,root/'environment/state.fixture.json');GovernanceController(r.store,r.authority).initialize(r.authority)
    r.work.configure_open_agency(OpenGoalPolicy(objectives),world);r.work.configure_open_learning((numeric_learning(),))
    if grant:
        k=r.work.agency.realization.kernel
        k.grant(GrantSpec(capabilities=tuple(k.capabilities)+(k.verify_capability,),resources=tuple(op.resource for obj in objectives for op in obj.operators),not_before_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+48*HOUR),r.authority)
        k.set_budgets({'write_attempts':64,'external_requests':128,'cost_micro_units':128},r.authority)
    return world

def offer(r,obj,key):
    mid=cue(r,key,ConcernCue(cue_kind='OPEN_LOOP',topic_key=obj.objective_id,motivation_source=obj.motivation_source,program_id=obj.objective_id))
    post(r,key,(mid,),task_class='numbers');return mid

def presence(r,key,state):
    resource='synthetic://recipient/observer';p=RecipientState(resource=resource,entity_id='observer',availability=state,observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+24*HOUR)
    return source(r,key,p.model_dump_json(),kind='SYSTEM_VERIFICATION',predicate='recipient.'+digest(resource)[:32])

def life_cycle(r,key,view):
    event=SubjectInput(source_key='synthetic.vf2.life.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=view.source_memory_ids,observed_at_us=r.clock.utc_now_us(),privacy_class='PUBLIC',growth_assessment_id=view.assessment_id)
    return r.subject.run(event)

def run(root,*,withdraw=False):
    started=time.monotonic();cpu=time.process_time();clock=VirtualClock();db=root/'subject/self.db'
    data_before=[3.25,1.5];data_after=[8.25,2.5]
    objs=(objective('baseline',data_before),objective('later-science',data_after))
    with open_runtime(db,clock) as r:
        identity=r.identity_id;world=configure(r,root,objs,grant=True)
        for obj,data in zip(objs,(data_before,data_after)):world.seed_observation(obj.operators[0].resource,data)
        offer(r,objs[0],'baseline');advance(r,clock,6)
        baseline_goal=r.store.all('goals')[0];assert baseline_goal['state']=='FAILED'
        failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE' ORDER BY rowid LIMIT 1").fetchone();assert failure
        origin=failure['result_memory_id']
        # A sourced failure makes a capability gap available; ordinary chatter is
        # not fabricated as the Subject's interest. Same concern may instead rest.
        need=cue(r,'gap',ConcernCue(cue_kind='OPEN_LOOP',topic_key='measurement',motivation_source='CAPABILITY_GAP',program_id='learn.numbers',possible_behaviors=('LEARN',)),parents=(origin,))
        resting=cue(r,'rest',ConcernCue(cue_kind='LOAD_STATE',topic_key='measurement-rest',motivation_source='CAPABILITY_GAP',program_id='learn.numbers',possible_behaviors=('LEARN','REST'),cognitive_load='HIGH'),parents=(origin,))
        rest=r.subject.run(SubjectInput(source_key='synthetic.vf2.rest',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(resting,),observed_at_us=clock.utc_now_us(),privacy_class='PUBLIC'))
        assert rest.intention.behavior=='REST' and not rest.goal_candidate_id
        post(r,'choose-learning',(need,),task_class='numbers');advance(r,clock,30)
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();assert job and job['state']=='DONE'
        body=RecordService(r.store).read(job['record_id'])['payload'];lesson_id=body['lesson_id'];assert r.work.open_learning.strategy('numbers','world')[1]=='NUMERIC_SUM'
        # Actual different-context future plan: same declared baseline, changed
        # selected operator due to current independently tested lesson.
        offer(r,objs[1],'later-science');advance(r,clock,8)
        goal=next(g for g in r.store.all('goals') if json.loads(g['body_json']).get('record_id') and RecordService(r.store).read(json.loads(g['body_json'])['record_id'])['payload']['objective']['objective_id']==objs[1].objective_id)
        assert goal['state']=='COMPLETED'
        result=world._load()['resources'][objs[1].operators[1].resource];assert result['data']==math.fsum(data_after) and result['method']=='NUMERIC_SUM'
        plan=RecordService(r.store).read(json.loads(goal['body_json'])['plan_record_id'])['payload'];assert plan['strategy_ids']
        # Record only an outcome actually observed/verified in this local realm.
        action=next(a for a in r.store.all('actions') if a['goal_id']==goal['goal_id'] and a['resource']==objs[1].operators[1].resource)
        assert action['state']=='SUCCEEDED'
        case=LearningCase(case_id='novel-later-use',context='independent-science',data=data_after,expected=math.fsum(data_after))
        episode={'episode_key':'actual-later-use','lesson_id':lesson_id,'case':case.model_dump(mode='json'),'action_id':action['action_id'],'actual_result_digest':digest(result['data'])}
        am=r.store.db.execute("SELECT memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_reference=? AND e.source_namespace='synthetic.open-action'",(action['action_id'],)).fetchone()[0]
        reuse=source(r,'verified-reuse',{'strategy_episode':episode},kind='SYSTEM_VERIFICATION',parents=(am,))
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',));assessment=review.assess(lesson_id,reuse,authority=r.authority)
        view=project(r.store,assessment,scope='world',privacy_classes=('PUBLIC',));assert view
        claim=SourcedClaim(entity_id='device',predicate='measurement.later-local-result',kind='VERIFIED_RESULT',value={'data':result['data'],'method':result['method'],'action_id':action['action_id']},valid_from_us=clock.utc_now_us(),confidence=1.)
        wm=source(r,'world-result',{'world_claim':claim.model_dump(mode='json')},kind='SYSTEM_VERIFICATION',parents=(reuse,))
        world_model=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',));world_model.ingest(wm);assert world_model.view('device',claim.predicate).state=='SUPPORTED_BELIEF'
        # Original D collector now sees a legitimate later-life opportunity.
        presence(r,'available','AVAILABLE')
        collected=r.subject.background_opportunities(entity_id='observer',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
        assert any(x.growth_assessment_id==assessment for x in collected)
        before_withdraw={'method':r.work.open_learning.strategy('numbers','world')[1],'opportunities':len(opportunities(r.store,scope='world',privacy_classes=('PUBLIC',)))}
        if withdraw:
            MemoryService(r.store,r.authority).forget(origin,r.authority)
            assert not project(r.store,assessment,scope='world',privacy_classes=('PUBLIC',)) and not r.work.open_learning.strategy('numbers','world')
            # Same later wake has no growth-derived cue when original source gone.
            c=r.subject.run(SubjectInput(source_key='synthetic.vf2.without-source',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',observed_at_us=clock.utc_now_us(),privacy_class='PUBLIC'))
            return {'arm':'SOURCE_WITHDRAWN','pre_intervention':before_withdraw,'source_withdrawn':True,'capability_after_withdrawal':None,'life_opportunities':len(opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))),'judgment':c.judgment.stance,'intention':c.intention.kind,'social_proposal':None if not c.social_proposal else c.social_proposal.act,'identity_stable':r.identity_id==identity,'intervention':'actual MemoryService.forget original failure result; closure not a policy flag'}
        social=life_cycle(r,'available',view);assert social.social_proposal and social.social_proposal.act=='REPORT_DISCOVERY'
        if social.intention_id:r.subject.transition_intention(social.intention_id,expected_revision=1,state='DROPPED') # candidate not delivered
        presence(r,'busy','BUSY');busy=life_cycle(r,'busy',view);assert busy.intention.behavior=='WATCH' and not busy.social_proposal
        refuse=SubjectInput(source_key='synthetic.vf2.no-interest',kind='INTERACTION',origin='USER',entity_id='observer',scope='world',observed_at_us=clock.utc_now_us(),privacy_class='PUBLIC',text='Synthetic recipient explicitly declines this discussion',interaction_signal=InteractionSignal(kind='DECLINE_DEPTH',topic_key=view.topic))
        r.subject.run(refuse);presence(r,'available-again','AVAILABLE');no_interest=life_cycle(r,'no-interest',view)
        assert no_interest.context_fit.mode=='RESPECT_BOUNDARY' and no_interest.intention.kind=='NO_ACTION'
        result_summary={'baseline_actual':sum(int(x) for x in data_before),'baseline_expected':math.fsum(data_before),'baseline_original_failure_experience_retained':r.store.one('experiences',failure['experience_id'])['outcome']=='FAILURE','training':body['results'],'later_data':data_after,'later_actual':result['data'],'later_expected':math.fsum(data_after),'later_method':result['method'],'later_goal_state':goal['state'],'actual_later_action_verified':True,'lesson_id':lesson_id,'assessment_id':assessment,'reuse_memory_id':reuse,'source_memory_id':origin,'social_available':social.social_proposal.act,'busy_intention':busy.intention.kind,'no_interest_intention':no_interest.intention.kind,'pre_intervention':before_withdraw,'rest_was_valid':True,'identity_id':identity,'world_model_result':'SUPPORTED_BELIEF','local_actions':len(r.store.all('actions')),'real_external_actions':0,'real_provider_calls':0,'actual_model_cost':0,'cost_precision':'local CPU/time measured; external billing not applicable','model_input_tokens':0,'model_output_tokens':0}
    with open_runtime(db,clock) as r:
        configure(r,root,objs,grant=False);assert r.identity_id==identity and r.work.open_learning.strategy('numbers','world')[1]=='NUMERIC_SUM'
        before=(len(r.store.all('actions')),len(r.store.all('grants')))
        for key,model in [('a',AnalyticalFixturePort()),('b',CautiousFixturePort())]:
            e=SubjectInput(source_key='synthetic.vf2.model.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(reuse,),observed_at_us=clock.utc_now_us(),task_class='numbers',privacy_class='PUBLIC')
            r.subject.cognize(e,model=model,authority=r.authority,policy=context_policy())
        assert before==(len(r.store.all('actions')),len(r.store.all('grants')))
        # Genuine independent changed expectation exposes float precision limits.
        counter=LearningCase(case_id='precision-limit',context='decimal-exactness',data=[.1,.2],expected=.3)
        cm=source(r,'counterexample',{'strategy_episode':{'episode_key':'precision-limit','lesson_id':lesson_id,'case':counter.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
        rev=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',));rev.assess(lesson_id,cm,authority=r.authority)
        assert not r.work.open_learning.strategy('numbers','world') and not project(r.store,assessment,scope='world',privacy_classes=('PUBLIC',))
        result_summary.update(restart_identity_stable=True,model_port_swap_identity_stable=True,new_authorization_on_restart=False,counterexample_suspended_strategy=True,counterexample_removed_life_support=True)
    result_summary.update(elapsed_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,execution='CONTROLLED_LOCAL_FIXTURE_KERNEL_AND_COMPUTATION_NOT_REAL_EXTERNAL_WORLD',capability_claim='bounded strategy-selection improvement, not algorithm invention',real_dialogue='NOT_RUN')
    return result_summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.root.exists():p.error('use a fresh dedicated development root')
    normal=run(args.root/'normal');ablation=run(args.root/'ablation',withdraw=True)
    assert normal['pre_intervention']==ablation['pre_intervention']
    result={'normal':normal,'ablation':ablation,'counterfactual_matching':'independently initialized synthetic stores, same inputs/spec/clock/role; opaque allocated IDs differ, no policy arm flag','CAPABILITY_CHANGE':'PASS_CONTROLLED_LOCAL','LIFE_CAUSAL_CHANGE':'PASS_OFFLINE_CANDIDATE','REAL_DIALOGUE':'NOT_RUN','PRODUCTION_CORE_ADOPTION':'NOT_RUN','GENERAL_DEEP_SELF_MODIFICATION':'NOT_RUN'}
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'CAPABILITY_CHANGE':result['CAPABILITY_CHANGE'],'LIFE_CAUSAL_CHANGE':result['LIFE_CAUSAL_CHANGE'],'output':str(args.output)}))
if __name__=='__main__':main()
