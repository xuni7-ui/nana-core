import json,signal,subprocess,sys,time
import pytest
from tests.open_autonomy.helpers import fresh,configure,advance
from tests.open_autonomy.test_learning import number_learning
from tools.nana_precision.recovery_worker import described
from tests.open_autonomy.helpers import capture,cue,send
from nana_core.contracts import CoreError


@pytest.mark.parametrize('cut',('BEFORE_PLAN_COMMIT','AFTER_PLAN_COMMIT'))
def test_actual_sigkill_checkpoint_commit_replays_without_duplicate_prefix(tmp_path,cut):
    with (tmp_path/'worker.txt').open('w') as log:
        process=subprocess.Popen([sys.executable,'-m','tools.nana_precision.recovery_worker',str(tmp_path),cut],stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+20
            while not (tmp_path/'cut.json').exists():
                assert process.poll() is None,(tmp_path/'worker.txt').read_text()
                assert time.monotonic()<deadline,'exact cut absent'
                time.sleep(.025)
            process.kill();process.wait(4);assert process.returncode==-signal.SIGKILL
        finally:
            if process.poll() is None:process.kill();process.wait(4)
    snapshot=json.loads((tmp_path/'cut.json').read_text());obj=described()
    with fresh(tmp_path/'state'/'self.db') as r:
        port=configure(r,tmp_path/'world'/'effect.fixture.json',(obj,),grant=False)
        r.work.configure_open_learning((number_learning(),))
        assert r.identity_id==snapshot['identity_id']
        advance(r,20)
        assert r.store.one('goals',snapshot['goal_id'])['state']=='COMPLETED'
        prefix=[a for a in r.store.all('actions') if a['resource']=='synthetic://output/precision.prefix']
        assert len(prefix)==1 and prefix[0]['state']=='SUCCEEDED'
        # Three prefix steps + failed read/compute (no bad write) + three repair
        # steps. The independently rejected compute must never publish.
        assert len(r.store.all('actions'))==8
        assert len(port._load()['effects'])==8
        assert r.store.db.execute("SELECT count(*) FROM events WHERE kind='open.goal_replanned'").fetchone()[0]==1
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_changed_checkpoint_is_not_reused_and_old_success_is_not_rewritten(tmp_path):
    obj=described()
    with fresh(tmp_path/'state'/'self.db') as r:
        port=configure(r,tmp_path/'world'/'changed.fixture.json',(obj,))
        for op in obj.operators:
            if op.capability=='world.observe':port.seed_observation(op.resource,[1.2,2.3])
        send(r,'initial',(cue(r,obj),));r.step();advance(r,8)
        goal=r.store.all('goals')[0];assert goal['state']=='FAILED'
        prefix=next(a for a in r.store.all('actions') if a['resource']=='synthetic://output/precision.prefix')
        body=port._load();body['resources'][prefix['resource']]={'data':'externally changed'};port._save(body)
        cause=capture(r,'change','A current independent source reports changed environment.')
        before=len(r.store.all('actions'))
        with pytest.raises(CoreError,match='CHECKPOINT_CURRENT_EFFECT_UNCERTAIN'):
            r.work.agency.revise(goal['goal_id'],expected_version=goal['version'],cause_memory_id=cause,authority=r.authority)
        assert r.store.one('actions',prefix['action_id'])['state']=='SUCCEEDED'
        assert len(r.store.all('actions'))==before
        with pytest.raises(CoreError,match='UNAUTHENTICATED_OPERATOR'):
            r.work.agency.realization.kernel.reobserve(prefix['action_id'],object())
