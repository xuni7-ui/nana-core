import json
import pytest
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.framing import ProblemFrame,FactCondition
from nana_core.continuity.subject.context_fit import InteractionSignal
from tests.controlled_hands.conftest import initialize,until

@pytest.mark.parametrize('initial,expected,grant',[('stale prefix ','REFRAME',True),('','PREMISE_SUPPORTED',True),('stale prefix ','REFRAME',False)])
def test_same_question_different_observation_reframes_problem_not_method(tmp_path,initial,expected,grant,record_property):
    task=ApplicationTask(task_id='note',kind='DOCUMENT',initial=initial,wanted='clean note')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=grant) as app:
            r=app.runtime
            observed=app.work.port.peek('note')
            assert observed['state']['text']==initial  # actual IPC, not model assertion
            mid=capture(r,'problem-observation',{'current_text':observed['state']['text'],'wanted':observed['task']['wanted']})
            original=app.work.objects['note']
            obj=original.model_copy(update={'objective_id':'reframe.clean','motivation_source':'UNRESOLVED_QUESTION','operators':tuple(op.model_copy(update={'args':{**op.args,'method':'HANDS_REPLACE'}}) if op.operator_id=='prepare' else op for op in original.operators)})
            app.work.policy.offer(obj)
            frame=ProblemFrame(requested_problem='Append the supposedly missing note',assumed=(FactCondition(memory_id=mid,field='current_text',expected=''),),alternative_problem='Replace stale contents to obtain the requested exact document',required=(FactCondition(memory_id=mid,field='wanted',expected='clean note'),),program_id=obj.objective_id)
            event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.problem-question',kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',text='Controlled project question: append the missing note',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),problem_frame=frame,topic='note',interaction_signal=InteractionSignal(kind='HELP',topic_key='note'),significance='RELEVANT')
            c=r.subject.run(event)
            assert c.problem_frame.state==expected
            assert not r.store.all('actions')
            if expected=='REFRAME':
                assert c.judgment.stance=='ALTERNATIVE' and c.judgment.selected_method is None
                assert c.intention.purpose==frame.alternative_problem
                gid=r.work.open_goals.adopt(c) if hasattr(r.work,'open_goals') else r.work.agency.adopt(c)
                assert gid and r.store.one('goals',gid)['state']=='ACTIVE'
                if grant:
                    until(app,lambda:r.store.one('goals',gid)['state']=='COMPLETED')
                    actual=app.work.port.peek('note')['state']['text']
                    assert actual=='clean note' and len(r.store.all('grants'))==1
                else:
                    until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM actions WHERE state='BLOCKED'").fetchone()))
                    assert app.work.port.peek('note')['state']['text']==initial and not r.store.all('grants')
                record_property('framing_chain',json.dumps({'same_question':frame.requested_problem,'observation':initial,'state':c.problem_frame.state,'new_problem':c.intention.purpose,'method_substitution':False,'goal':gid,'grant':grant,'goal_state':r.store.one('goals',gid)['state']}))
            else:
                assert c.judgment.stance!='ALTERNATIVE' and c.intention.purpose!=frame.alternative_problem


def test_model_interpretation_cannot_refute_fact_or_force_new_goal(tmp_path):
    from nana_core.continuity.world_loop.reference import open_runtime,capture as source
    from nana_core.presence.authority import VirtualClock
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        mid=source(r,'guess',{'current':False},kind='MODEL_DERIVATION')
        frame=ProblemFrame(requested_problem='A',assumed=(FactCondition(memory_id=mid,field='current',expected=True),),alternative_problem='B',required=(FactCondition(memory_id=mid,field='current',expected=False),),program_id='project.unapproved')
        c=r.subject.run(SubjectInput(source_key='synthetic.frame.guess',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',observed_at_us=r.clock.utc_now_us(),privacy_class='PUBLIC',source_memory_ids=(mid,),problem_frame=frame))
        assert c.problem_frame.state=='INSUFFICIENT_EVIDENCE' and c.judgment.stance=='ASK' and not c.goal_candidate_id
        assert not r.store.all('grants') and not r.store.all('goals')
