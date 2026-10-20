import json,os,signal,subprocess,sys,time
from pathlib import Path
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject.experience_need import project_need
from nana_core.continuity.subject.growth_life import opportunities
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.world_loop.learning import EpisodeLearning
from tests.controlled_hands.conftest import initialize,until


def need_cycle(app,key,mid):
    r=app.runtime
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.need.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',source_memory_ids=(mid,),task_class='owned-document')
    return r.subject.run(event)


def test_actual_failure_changes_need_reuse_settles_restart_counterexample_reopens(tmp_path,record_property):
    tasks=(ApplicationTask(task_id='base',kind='DOCUMENT',initial='old ',wanted='new',context='notes'),ApplicationTask(task_id='later',kind='DOCUMENT',initial='draft ',wanted='different',context='research'))
    with OwnedApplication(tmp_path/'target',tasks=tasks) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime;identity=r.identity_id
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE' AND task_class='owned-document'").fetchone()))
            app.pause();failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE' AND task_class='owned-document' LIMIT 1").fetchone()
            # The opportunity is derived from the observed gap. No PreferenceSignal.
            cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='document-competence',motivation_source='CAPABILITY_GAP',program_id='learn.owned-document',possible_behaviors=('LEARN','WATCH'))
            mid=capture(r,'reconsider-known-gap',cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(failure['result_memory_id'],),predicate='concern.document-competence')
            before=need_cycle(app,'before',mid)
            assert before.experience_need.state=='OPEN' and before.intention.behavior=='LEARN'
            if before.intention_id:r.subject.transition_intention(before.intention_id,expected_revision=1,state='DROPPED')
            app.pause(False)
            until(app,lambda:bool(opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)))
            app.pause();view=opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)[0]
            after=need_cycle(app,'after',mid)
            assert after.experience_need.state=='SETTLED' and after.intention.behavior=='WATCH'
            assert not r.store.all('self_assertions') and not r.store.all('assertion_signals')
            effects=len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])
        marker=tmp_path/'committed-self-wake.json'
        child=subprocess.Popen([sys.executable,'-m','tools.nana_foundation_closure.restart_worker','--home',str(home),'--mid',mid,'--marker',str(marker)])
        try:
            deadline=time.monotonic()+10
            while not marker.exists():
                assert child.poll() is None and time.monotonic()<deadline
                time.sleep(.02)
            committed=json.loads(marker.read_text());assert committed['state']=='SETTLED' and committed['behavior']=='WATCH'
            os.kill(child.pid,signal.SIGKILL);child.wait(timeout=4)
            assert child.returncode==-signal.SIGKILL
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=4)
        with LifeApplication(home,bootstrap_grant=False) as app:
            r=app.runtime;app.pause()
            replay=r.subject.run(SubjectInput.model_validate_json(json.dumps(committed['event'])))
            assert replay.replayed and replay.cycle_id==committed['cycle_id'] and len(r.store.all('actions'))==committed['actions']
            restarted=need_cycle(app,'restarted',mid)
            assert r.identity_id==identity and restarted.experience_need.state=='SETTLED' and restarted.intention.behavior=='WATCH'
            assert effects==len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])
            # Independent evaluator checks a contrary expectation and suspends the lesson.
            case=LearningCase(case_id='counterexample',context='changed-expectation',data={'task':tasks[1].model_dump(mode='json'),'revision':1},expected={'different_required_workflow':True})
            counter=capture(r,'counter-observation',{'strategy_episode':{'episode_key':'contrary-expectation','lesson_id':view.lesson_id,'case':case.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
            EpisodeLearning(r.store,r.authority,scopes=r.config.scopes,privacy_classes=r.config.privacy_classes).assess(view.lesson_id,counter,authority=r.authority)
            reopened=need_cycle(app,'counter',mid)
            assert reopened.experience_need.state=='OPEN' and reopened.intention.behavior=='LEARN'
            assert not r.store.all('cognitive_requests')
            app.forget(failure['result_memory_id'])
            assert project_need(r.store,'owned-document',scope='project-work',privacy_classes=r.config.privacy_classes).state=='UNKNOWN'
            record_property('causal_chain',json.dumps({'before':before.experience_need.state,'after_verified_reuse':after.experience_need.state,'restart':restarted.experience_need.state,'counterexample':reopened.experience_need.state,'withdrawal':'UNKNOWN','identity':identity,'actual_owned_effects':effects,'provider_calls':0,'actual_sigkill':True,'replay_same_cycle':True}))


def test_deleted_training_root_remains_tombstoned_on_host_rebind(tmp_path):
    task=ApplicationTask(task_id='task',kind='DOCUMENT',wanted='note')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home) as app:
            app.pause();r=app.runtime;mid=app.work.training_sources[0]
            source=r.subject.records.memory.read(mid)['source_evidence_id']
            app.forget(mid)
            count=r.store.db.execute("SELECT count(*) FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference LIKE 'owned-learning-input:%'").fetchone()[0]
            identity=r.identity_id
        with LifeApplication(home) as app:
            assert app.runtime.identity_id==identity and app.work.training_sources==()
            assert app.runtime.store.one('continuity_evidence',source)['state']=='DELETED'
            assert not app.runtime.work.open_learning.specs
            assert count==app.runtime.store.db.execute("SELECT count(*) FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference LIKE 'owned-learning-input:%'").fetchone()[0]
