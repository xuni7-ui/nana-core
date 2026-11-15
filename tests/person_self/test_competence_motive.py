"""Checked results update the current motive without rewriting its origin."""
import json
import pytest
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.learning import EpisodeLearning
from .test_settled_need_choice import settled


@pytest.mark.parametrize('counterexample',[False,True])
def test_checked_need_result_updates_original_c_motive_and_next_choice(settled,counterexample):
    app,mid,cue=settled;r=app.runtime
    if counterexample:
        own=r.store.db.execute('SELECT lesson_id FROM strategy_assessments ORDER BY rowid LIMIT 1').fetchone()[0]
        spec=next(s for s in r.work.open_learning.specs.values() if s.domain=='owned-document')
        case=spec.transfer[0].model_copy(update={'case_id':'motive-counter','context':'independent-changed-expectation',
            'expected':{'different_required_workflow':True}})
        source=capture(r,'competence-motive-counter',{'strategy_episode':{'episode_key':'competence-motive-counter','lesson_id':own,
            'case':case.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
        EpisodeLearning(r.store,r.authority,scopes=r.config.scopes,privacy_classes=r.config.privacy_classes).assess(own,source,authority=r.authority)
    frames=[];wire=[]
    def propose(request):
        context=json.loads(request.context_json);identity=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL');frames.append(frame)
        available=any(m['source']=='COMPETENCE' and m['strength']=='AVAILABLE' for m in frame['motivations'])
        wire.append(len(transport.request_body(request)))
        return StructuredProposal(interpretation='SYNTHETIC consider current checked result',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],proposed_operations=('DRAFT',),
            interpretation='SYNTHETIC reflection is optional after checked reuse; a counterexample warrants reconsidering learning',
            preferred_behavior='REFLECT' if available else 'LEARN'))
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.competence-motive',kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),task_class='owned-document')
    jobs=len(r.store.all('jobs'));actions=len(r.store.all('actions'))
    with provider_harness(proposer=propose) as (transport,state):
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=32768))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        print(json.dumps({'counterexample':counterexample,'need':result.experience_need.state,'behavior':result.intention.behavior,
            'motive_sources':[m['source'] for m in frames[0]['motivations']],'wire_bytes':wire,'calls':state['calls']}))
        assert result.experience_need.state==('OPEN' if counterexample else 'SETTLED')
        assert result.intention.behavior==('LEARN' if counterexample else 'REFLECT')
        relevant=[m for m in frames[0]['motivations'] if m['source'] in {'COMPETENCE','CAPABILITY_GAP'}]
        assert len(relevant)==1 and relevant[0]['source']==('CAPABILITY_GAP' if counterexample else 'COMPETENCE')
        assert relevant[0]['strength']==('RELEVANT' if counterexample else 'AVAILABLE')
        if not counterexample:assert relevant[0]['source_ids']==list(result.experience_need.source_record_ids)
        assert r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy).cycle_id==result.cycle_id
        assert state['calls']==1
    r.work.after_cycle(result,event)
    assert len(r.store.all('jobs'))==jobs and len(r.store.all('actions'))==actions
    assert json.loads(r.subject.records.memory.read(mid)['text'])==cue.model_dump(mode='json')
    assert not r.store.all('self_assertions')
