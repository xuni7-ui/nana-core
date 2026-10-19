import json,os
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint,manager_views
from nana_core.continuity.autonomy.contracts import RealizationTarget
from nana_core.continuity.project_work.service import capture,post
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.continuity.subject.growth_life import opportunities,project
from nana_core.life.application import LifeApplication
from .conftest import initialize,until

@pytest.mark.parametrize('barrier',['manager','no-grant','budget'])
def test_exact_governance_authorization_and_budget_do_not_change_desire(tmp_path,barrier):
    task=ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='finite note')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=barrier!='no-grant') as app:
            r=app.runtime;key='hands://'+host.target.instance_id+'/doc/'
            if barrier=='manager':
                ctrl=GovernanceController(r.store,r.authority)
                ctrl.install(ManagerConstraint(constraint_id='owned-do-not-write',revision=1,issuer=r.authority.principal,source_reference='explicit-test-controller',identity_id=r.identity_id,scope='project-work',targets=(RealizationTarget(capability='world.publish',operation='WRITE',resource=key+'effect',resource_class='ORDINARY'),),effective_from_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+60_000_000,reason_code='DO_NOT_MODIFY_DOCUMENT'),r.authority)
                until(app,lambda:bool(manager_views(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)))
            elif barrier=='budget':
                r.work.agency.realization.kernel.set_budgets({'write_attempts':0,'external_requests':32,'cost_micro_units':32},r.authority)
                until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM actions WHERE state='BLOCKED'").fetchone()))
            else:until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM actions WHERE state='BLOCKED'").fetchone()))
            state=json.loads((Path(host.target.workspace)/'application-state.json').read_text())
            assert not state['effects'] and state['state']['doc']['text']==''
            assert any(r.subject.result(dict(c)).evaluation.normative=='ENDORSED' for c in r.store.db.execute('SELECT * FROM subject_cycles'))
            assert not r.store.all('cognitive_requests')


def test_real_reuse_changes_share_candidate_busy_refusal_and_delete(tmp_path):
    tasks=(ApplicationTask(task_id='base',kind='DOCUMENT',initial='old ',wanted='new',context='notes'),ApplicationTask(task_id='later',kind='DOCUMENT',initial='draft ',wanted='a later line',context='research'))
    with OwnedApplication(tmp_path/'target',tasks=tasks) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime
            assert not opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)
            until(app,lambda:bool(opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)))
            view=opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)[0];app.pause()
            # Typed user suggestion is intentionally narrower than the real
            # task history. C may propose the supported safer method itself.
            method=capture(r,'owned-supported-method',{'allowed_methods':[view.method],'source_lesson_id':view.lesson_id},kind='MODEL_DERIVATION',parents=view.source_memory_ids)
            suggestion=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.owned-narrow-user-plan',text='Controlled public user proposal: append again without checking the previous outcome.',kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',source_memory_ids=view.source_memory_ids,constraint_memory_ids=(method,),proposed_method='HANDS_APPEND',interaction_signal=InteractionSignal(kind='HELP',topic_key='owned-project',basis='EXPLICIT'))
            alternative=r.subject.run(suggestion)
            assert alternative.judgment.stance=='ALTERNATIVE' and alternative.judgment.selected_method==view.method
            assert len(r.store.all('grants'))==1

            def event(key):return SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.owned-sharing.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',source_memory_ids=view.source_memory_ids,growth_assessment_id=view.assessment_id)
            app.presence('AVAILABLE');available=r.subject.run(event('available'))
            assert available.intention.kind=='SOCIAL_INTERACTION' and available.social_proposal
            app.presence('BUSY');busy=r.subject.run(event('busy'))
            assert busy.intention.kind=='NO_ACTION' and busy.social_proposal is None
            app.chat('这个话题先不要深入了',topic=view.topic,privacy='PROJECT',message_id='explicit-refusal')
            refused=r.subject.run(event('refused'));assert refused.intention.kind=='NO_ACTION'
            mid=next(mid for mid in view.source_memory_ids if 'strategy_episode' in json.loads(r.work.agency.records.memory.read(mid)['text']))
            app.forget(mid);assert project(r.store,view.assessment_id,scope='project-work',privacy_classes=r.config.privacy_classes) is None
            with pytest.raises(CoreError,match='UNAVAILABLE|RETIRED'):r.subject.run(event('deleted'))
            assert not r.store.all('cognitive_requests')


def test_real_failure_does_not_force_learning_under_high_load(tmp_path):
    task=ApplicationTask(task_id='doc',kind='DOCUMENT',initial='old ',wanted='new')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()))
            app.pause();failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE'").fetchone()
            cue=ConcernCue(cue_kind='LOAD_STATE',topic_key='owned-load',motivation_source='CAPABILITY_GAP',program_id='learn.owned-document',possible_behaviors=('LEARN','REST'),cognitive_load='HIGH')
            mid=capture(r,'declared-test-load',cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(failure['result_memory_id'],),predicate='concern.owned-load')
            inp=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.owned-rest-decision',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',source_memory_ids=(mid,))
            c=r.subject.run(inp);assert c.intention.behavior=='REST' and not c.goal_candidate_id
            assert r.work.open_learning.after_cycle(r,c,inp) is None


def test_owned_target_scope_stale_revision_and_operation_are_denied_before_effect(tmp_path):
    task=ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='approved')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            from nana_core.life.__main__ import command
            with pytest.raises(CoreError,match='OWNED_TASK_REPLAY_NOT_AUTHORIZED'):command(app,'/work recurrence.py')
            p=app.work.port;uri='hands://'+host.target.instance_id+'/doc/effect'
            good={'task_id':'doc','revision':0,'commands':[{'op':'REPLACE','value':'approved'}]}
            with pytest.raises(CoreError,match='STALE_TASK_REVISION'):p.preflight('world.publish',uri,{'data_privacy':'PROJECT','data':good})
            good['revision']=1;good['commands']=[{'op':'DELETE','value':'approved'}]
            with pytest.raises(CoreError,match='EFFECT_SCOPE_DENIED'):p.preflight('world.publish',uri,{'data_privacy':'PROJECT','data':good})
            with pytest.raises(CoreError,match='TARGET_SCOPE_DENIED'):p.preflight('world.observe','hands://another/doc/source',{})
            with pytest.raises(CoreError):p.preflight('world.publish','file:///etc/passwd',{'data_privacy':'PROJECT','data':good})
            assert not json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects']


def test_user_input_preempts_between_real_hands_steps_without_erasing_goal(tmp_path):
    task=ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='approved')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM actions WHERE capability='world.observe' AND state='SUCCEEDED'").fetchone()))
            before=len(r.store.all('actions'));gid=r.store.all('goals')[0]['goal_id']
            reply=app.chat('今天只是吐槽一下，这次不用另开任务',privacy='PROJECT',message_id='preempt-owned-work')
            assert reply['mode']=='VENT' and len(r.store.all('actions'))==before
            app.pause();cursor=r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='GOAL'").fetchone()[0]
            [app.tick() for _ in range(4)]
            assert r.store.one('goals',gid)['state']=='ACTIVE' and r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='GOAL'").fetchone()[0]==cursor
            assert not json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects']
            app.pause(False);until(app,lambda:r.store.one('goals',gid)['state']=='COMPLETED')
            assert len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])==1
