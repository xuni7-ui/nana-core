import pytest
from nana_core.actions import ActionKernel,OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CAPABILITIES,CoreError,GrantSpec,Observation,VERIFY_CAPABILITY
from nana_core.fake_world import FakeWorld
from nana_core.initiative import GoalCandidate,Initiative
from nana_core.phase3.initiative_cases import run_cases
from nana_core.planning import FixtureModel
from nana_core.storage import Store


def test_value_conflict_candidates_no_actions_and_restart_pending(tmp_path):
    world=FakeWorld(tmp_path/'world.db');clock=ManualClock();authority=OperatorAuthority()
    try:
        with Store(tmp_path/'core.db',clock) as store:
            kernel=ActionKernel(store,world,authority);report=run_cases(store,kernel)
            assert report['passed'] and report['actions']==report['grants']==report['goals']==0
            identity=store.identity;cid=report['cases'][0]['candidate_id'];before=Initiative(store,kernel).candidate(cid)
            assert before['state']=='DEFERRED' and before['job_id']
            assert world.counts()['effects']==0
        with Store(tmp_path/'core.db',clock) as store:
            assert store.identity==identity
            kernel=ActionKernel(store,world,authority)
            assert Initiative(store,kernel).candidate(cid)==before
            assert Initiative(store,kernel).evaluate(cid)==before
    finally:world.close()


def test_acceptance_does_not_dispatch_and_activation_never_bypasses_grants(tmp_path):
    world=FakeWorld(tmp_path/'world.db');authority=OperatorAuthority();clock=ManualClock()
    source='source://synthetic/initiative';card='notebook://synthetic/initiative'
    try:
        with Store(tmp_path/'core.db',clock) as store:
            world.seed_source(source,[{'text':'Synthetic paper garden.','locator':'synthetic paragraph 1'}])
            kernel=ActionKernel(store,world,authority);initiative=Initiative(store,kernel)
            obs=Observation(source_namespace='synthetic.initiative',object_id='reading',raw_text='A synthetic request.',
                source_id=source,card_resource=card,occurred_at='2026-09-01T00:00:00Z')
            eid=store.ingest(obs)
            proposal=GoalCandidate(purpose='Help a synthetic reader',intent='reading_card',evidence_event_ids=(eid,),
                need=.9,importance=.9,urgency=.8,confidence=.9,disturbance=.1,required_capability='reading.source.read',resource=source)
            cid=initiative.propose(proposal)
            assert initiative.evaluate(cid)['state']=='BLOCKED'
            assert store.all('actions')==[]
            with pytest.raises(CoreError):initiative.activate_reading(cid,obs,FixtureModel())
            # Only source-read grant: acceptance permitted, actual card remains blocked.
            kernel.set_budgets({'write_attempts':2,'external_requests':20,'cost_micro_units':20},authority)
            kernel.grant(GrantSpec(capabilities=('reading.source.read',VERIFY_CAPABILITY),resources=(source,card),
                not_before_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+10_000_000),authority)
            assert initiative.evaluate(cid)['state']=='ACCEPTED' and store.all('actions')==[]
            goal=initiative.activate_reading(cid,obs,FixtureModel())
            assert store.one('goals',goal)['state']=='BLOCKED' and world.counts()['effects']==0
            assert world.counts()['execute_calls']==1
    finally:world.close()


def test_candidate_evidence_and_duplicate_collision_are_strict(tmp_path):
    world=FakeWorld(tmp_path/'world.db');authority=OperatorAuthority()
    try:
        with Store(tmp_path/'core.db') as store:
            i=Initiative(store,ActionKernel(store,world,authority))
            p=GoalCandidate(purpose='Synthetic',intent='dialogue',evidence_event_ids=('missing',),need=.5,importance=.5,urgency=.5,confidence=.5,disturbance=.5)
            with pytest.raises(CoreError,match='EVIDENCE_MISSING'):i.propose(p)
            eid=store.ingest(Observation(source_namespace='synthetic.i',object_id='a',kind='unrelated',raw_text='Synthetic evidence.'))
            p=p.model_copy(update={'evidence_event_ids':(eid,)})
            cid=i.propose(p);assert i.propose(p)==cid
            with pytest.raises(CoreError,match='CANDIDATE_KEY_COLLISION'):i.propose(p.model_copy(update={'need':.9}))
    finally:world.close()


def test_real_crash_after_scheduler_commit_resumes_one_occurrence(tmp_path):
    import json,os,signal,subprocess,sys
    from pathlib import Path
    script='''import os,sys,signal
from nana_core.storage import Store
from nana_core.clock import ManualClock
from nana_core.fake_world import FakeWorld
from nana_core.actions import ActionKernel,OperatorAuthority
from nana_core.contracts import Observation
from nana_core.initiative import Initiative,GoalCandidate
with Store(sys.argv[1],ManualClock()) as store:
 world=FakeWorld(sys.argv[2]);i=Initiative(store,ActionKernel(store,world,OperatorAuthority()))
 eid=store.ingest(Observation(source_namespace="synthetic.i.crash",object_id="wake",kind="unrelated",raw_text="Synthetic pending need."))
 cid=i.propose(GoalCandidate(purpose="Synthetic discussion",intent="dialogue",evidence_event_ids=(eid,),need=.8,importance=.8,urgency=.8,confidence=.8,disturbance=.1))
 print(cid,flush=True)
 def stop(point):os.kill(os.getpid(),signal.SIGKILL)
 i.evaluate(cid,fault=stop)
'''
    proc=subprocess.run([sys.executable,'-c',script,str(tmp_path/'core.db'),str(tmp_path/'world.db')],
        env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':str(Path('src').absolute())},capture_output=True,text=True,timeout=10)
    assert proc.returncode==-signal.SIGKILL
    clock=ManualClock();clock.advance(50_000_000)
    world=FakeWorld(tmp_path/'world.db')
    try:
        with Store(tmp_path/'core.db',clock) as store:
            i=Initiative(store,ActionKernel(store,world,OperatorAuthority()));cid=proc.stdout.strip()
            assert i.candidate(cid)['state']=='PROPOSED' and len(store.all('jobs'))==1
            assert i.evaluate(cid)['state']=='ACCEPTED' and len(store.all('jobs'))==1
            assert store.all('actions')==[] and world.counts()['effects']==0
    finally:world.close()
