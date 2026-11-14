"""Independently checked G reuse can matter privately, without forced sharing."""
import json,time
from pathlib import Path
from contextlib import contextmanager
import pytest
from nana_core.storage import digest
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.autonomy import private_intent
from nana_core.continuity.cognition import CognitiveProposal,AnalyticalFixturePort
from nana_core.continuity.context import ContextAssembler,ContextRequest
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject import growth_life
from nana_core.continuity.world_loop.reference import open_runtime,context_policy
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import objective,configure,offer,advance,source,cue,post,presence
from nana_core.continuity.subject.opportunities import ConcernCue
from .test_private_method_continuation import bind


@contextmanager
def grown(root,clock):
    """Reuse original G trial/held-out and actual later Kernel/Verify path."""
    objs=(objective('inner-before',[3.25,1.5]),objective('inner-later',[8.25,2.5]))
    with open_runtime(root/'subject/self.db',clock,wall=True) as r:
        world=configure(r,root,objs,grant=True)
        for obj,data in zip(objs,([3.25,1.5],[8.25,2.5])):world.seed_observation(obj.operators[0].resource,data)
        offer(r,objs[0],'before');advance(r,clock,6)
        assert r.store.all('goals')[0]['state']=='FAILED'
        origin=r.store.db.execute("SELECT result_memory_id FROM experiences WHERE outcome='FAILURE' ORDER BY rowid LIMIT 1").fetchone()[0]
        mid=cue(r,'gap',ConcernCue(cue_kind='OPEN_LOOP',topic_key='inner-gap',motivation_source='CAPABILITY_GAP',program_id='learn.numbers',possible_behaviors=('LEARN',)),parents=(origin,))
        post(r,'learn',(mid,),task_class='numbers');advance(r,clock,30)
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();assert job['state']=='DONE'
        lesson=RecordService(r.store).read(job['record_id'])['payload']['lesson_id']
        offer(r,objs[1],'later');advance(r,clock,8)
        action=next(a for a in r.store.all('actions') if a['resource']==objs[1].operators[1].resource and a['state']=='SUCCEEDED')
        result=world._load()['resources'][objs[1].operators[1].resource]
        assert result['data']==10.75 and result['method']=='NUMERIC_SUM'
        case=LearningCase(case_id='inner-novel-use',context='different-future-measurement',data=[8.25,2.5],expected=10.75)
        episode={'episode_key':'inner-actual-later-use','lesson_id':lesson,'case':case.model_dump(mode='json'),'action_id':action['action_id'],'actual_result_digest':digest(result['data'])}
        am=r.store.db.execute("SELECT memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_reference=? AND e.source_namespace='synthetic.open-action'",(action['action_id'],)).fetchone()[0]
        reuse=source(r,'inner-verified-reuse',{'strategy_episode':episode},kind='SYSTEM_VERIFICATION',parents=(am,))
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        assessment=review.assess(lesson,reuse,authority=r.authority)
        view=growth_life.project(r.store,assessment,scope='world',privacy_classes=('PUBLIC',));assert view
        yield r,view,origin,reuse,lesson


@pytest.mark.parametrize('condition',['active','rest','available-rest','ablated','no-provider'])
def test_original_g_success_can_inform_own_interest_without_mandatory_sharing(tmp_path,monkeypatch,condition):
    clock=VirtualClock();seen=[]
    def propose(request):
        package=json.loads(request.context_json);blocks=[json.loads(b['data_json']) for b in package['blocks'] if b['kind']=='GROWTH_CHANGE']
        frame=next(json.loads(b['data_json']) for b in package['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert 'PRIVATE_GROWTH_INTEREST_CANARY' not in request.context_json
        seen.append((request,blocks,frame))
        use=bool(blocks) and condition not in {'rest','available-rest'}
        return StructuredProposal(interpretation='SYNTHETIC choose privately after actual checked growth',subject_cognition=CognitiveProposal(
            identity_id=package['manifest']['identity_id'],identity_revision=package['manifest']['identity_revision'],
            interpretation='SYNTHETIC current skill may inspire play; no external emotion or benefit is inferred',
            preferred_behavior='REFLECT' if use else 'REST' if condition in {'rest','available-rest'} else 'WATCH',
            proposed_operations=('DRAFT',) if use else ('WAIT',),
            private_tendency={'topic':'own-growth-play','tendency':'PRIVATE_GROWTH_INTEREST_CANARY: I would like to try playful measurement in my own creative time.'} if use else None))
    with grown(tmp_path/condition,clock) as (r,view,origin,reuse,lesson),provider_harness(proposer=propose) as (transport,state):
        from tests.world_loop.test_model_framing import bind as bind_counter
        bind_counter(transport)
        if condition=='available-rest':presence(r,'growth-recipient-available','AVAILABLE')
        if condition=='ablated':monkeypatch.setattr(growth_life,'context_projection',lambda *args,**kwargs:None,raising=False)
        if condition!='no-provider':bind(r,transport,context_policy())
        before={table:len(r.store.all(table)) for table in ('goals','actions','grants')}
        waiting_before=r.store.db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING' AND kind='WAIT'").fetchone()[0]
        def allocated():
            return sum(p.stat().st_blocks*512 for p in (Path(str(r.store.path)+suffix) for suffix in ('','-wal','-shm')) if p.exists())
        disk_before=allocated();cpu_before=time.process_time()
        clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
        for _ in range(12):r.step()
        for _ in range(3):r.refresh_attention();r.step()
        values=private_intent.candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL'))
        own=[(rid,v) for rid,v in values if v.category=='PRIVATE_TENDENCY' and v.topic=='own-growth-play']
        measure=r.store.one('cognitive_requests',seen[0][0].request_id) if seen else None
        print(json.dumps({'measurement':'synthetic_independent_growth_to_private_choice','condition':condition,'self_calls':state['calls'],'private_tendencies':len(own),'input_bytes':measure['input_bytes'] if measure else None,'reserved_bytes':measure['reserved_bytes'] if measure else None,'latency_us':measure['latency_us'] if measure else None,'sqlite_family_allocated_before':disk_before,'sqlite_family_allocated_after':allocated(),'runtime_cpu_seconds':time.process_time()-cpu_before},sort_keys=True))
        assert state['calls']==(0 if condition=='no-provider' else 1)
        assert bool(own)==(condition=='active')
        assert before=={table:len(r.store.all(table)) for table in before}
        assert waiting_before==r.store.db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING' AND kind='WAIT'").fetchone()[0]
        if seen:
            assert {'REFLECT','REST'}<=set(seen[0][2]['behavior_options'])
            if condition!='ablated':assert seen[0][1][0]['lesson_id']==lesson and seen[0][1][0]['method']=='NUMERIC_SUM'
        if condition=='active':
            rid,item=own[0];identity=r.identity_id
            assert item.activity_state=='ACTIVE' and item.disclosure_policy=='PRIVATE_FOR_NOW'
            assert RecordService(r.store).current_support(rid)
            kwargs=dict(scope='world',entity_id='observer',privacy_classes=('PUBLIC','PROJECT','PERSONAL'),selected_record_ids=seen[0][2]['source_record_ids'])
            snap=r.store.snapshot();writes=r.store.db.total_changes
            assert growth_life.context_projection(r.store,seen[0][2]['subject_event_id'],**kwargs).lesson_id==lesson
            for key,value in [('scope','other-scope'),('entity_id','friend'),('selected_record_ids',()),('privacy_classes',())]:
                assert growth_life.context_projection(r.store,seen[0][2]['subject_event_id'],**{**kwargs,key:value}) is None
            assert r.store.snapshot()==snap and r.store.db.total_changes==writes
            ordinary=ContextAssembler(r.store,r.authority).assemble(ContextRequest(entity_id='observer',scopes=('world',),task_class='ordinary',task='A separate permitted context',task_privacy_class='PERSONAL',max_input_tokens=65536),context_policy())
            assert not any(b.kind=='GROWTH_CHANGE' for b in ordinary.blocks)
            assert 'PRIVATE_GROWTH_INTEREST_CANARY' not in ordinary.model_dump_json()
        if condition in {'active','ablated'}:
            class Later:
                descriptor='synthetic-independent-next-context-choice'
                def propose(self,request):
                    own_now=[json.loads(b['data_json']) for b in json.loads(request.context_json)['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
                    value=json.loads(AnalyticalFixturePort().propose(request));value.update(preferred_behavior='REFLECT' if own_now else 'WATCH',proposed_operations=['DRAFT'] if own_now else ['READ_SOURCE'])
                    if own_now:value['private_question']={'topic':'own-growth-play','question':'SYNTHETIC could playful measurement support a new creative experiment?'}
                    return json.dumps(value)
            mid=cue(r,'later-own-opportunity',ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='own-growth-play',possible_behaviors=('WATCH','REFLECT')))
            decision=r.subject.cognize(SubjectInput(source_key='synthetic.inner-later-choice',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,)),model=Later(),authority=r.authority,policy=context_policy())
            assert decision.intention.behavior==('REFLECT' if condition=='active' else 'WATCH')
            assert not decision.goal_candidate_id and state['calls']==1
            assert before=={table:len(r.store.all(table)) for table in before}
            print(json.dumps({'measurement':'synthetic_growth_later_choice','condition':condition,'chosen_behavior':decision.intention.behavior,'later_fixture_calls':1,'extra_provider_calls':0},sort_keys=True))
    if condition=='active':
        with open_runtime(tmp_path/condition/'subject/self.db',clock,wall=True) as r:
            assert r.identity_id==identity
            assert any(v.intent_id==item.intent_id and v.content_summary==item.content_summary for _,v in private_intent.candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')))
            # A direct independent counterexample suspends G and removes all of
            # this method's qualification, rather than imposing a trait edit.
            bad=LearningCase(case_id='inner-precision-counterexample',context='decimal-exactness',data=[.1,.2],expected=.3)
            counter=source(r,'inner-counterexample',{'strategy_episode':{'episode_key':'inner-precision-counterexample','lesson_id':lesson,'case':bad.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
            EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',)).assess(lesson,counter,authority=r.authority)
            assert growth_life.project(r.store,view.assessment_id,scope='world',privacy_classes=('PUBLIC',)) is None
            assert growth_life.context_projection(r.store,seen[0][2]['subject_event_id'],**kwargs) is None
            # Counterevidence retires the lesson; source deletion still governs
            # erasure of an own idea whose original occurrence remains factual.
            MemoryService(r.store,r.authority).forget(origin,r.authority)
            assert not any(v.intent_id==item.intent_id for _,v in private_intent.candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')))
            assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PRIVATE_GROWTH_INTEREST_CANARY')>0").fetchone()
            assert r.identity_id==identity
