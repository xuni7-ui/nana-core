from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import HOUR
from .test_storage_runtime import event


def prepared(path,clock):
    with ContinuityStore(path,clock,schema_target=8) as store:
        IdentityService(store,OperatorAuthority());MemoryService(store).entity('synthetic-person','PERSON')


def test_clock_only_presence_and_bounded_cognition_swap(tmp_path):
    path=tmp_path/'self.db';clock=VirtualClock();prepared(path,clock)
    config=RuntimeConfig(scopes=('life',),entity_id='synthetic-person',lease_us=3*HOUR,heartbeat_us=HOUR,
        review_interval_us=HOUR,model='analytical',cognition_cooldown_us=0,max_calls_per_day=1)
    with NanaRuntime(path,config,clock=clock) as runtime:
        identity=runtime.store.identity.copy()
        first=runtime.health()
        clock.advance(HOUR);runtime.drain()
        assert runtime.health().clock_us>first.clock_us
        assert not runtime.store.all('runtime_cognition_calls')
        sample=event(runtime.store,'uncertain')
        sample=sample.model_copy(update={'input':sample.input.model_copy(update={'significance':'HIGH','uncertainty':'HIGH'})})
        runtime.submit(sample);result=runtime.step()
        assert result['mode']=='FULL_COGNITION' and result['cycle'].deliberation
        runtime.cognition.set_model('cautious')
        runtime.submit(event(runtime.store,'second',input=sample.input.model_copy(update={'source_key':'synthetic.runtime.second'})))
        result=runtime.step()
        assert result['mode']=='LIGHT_COGNITION'
        assert len(runtime.store.all('runtime_cognition_calls'))==1
        assert runtime.store.identity==identity
        assert not any(runtime.store.all(t) for t in ('actions','attempts','grants','budgets'))


def test_model_timeout_reaped_and_restart_continues(tmp_path):
    path=tmp_path/'self.db';clock=VirtualClock();prepared(path,clock)
    config=RuntimeConfig(scopes=('life',),entity_id='synthetic-person',model='timeout',model_timeout_seconds=.2)
    with NanaRuntime(path,config,clock=clock) as runtime:
        e=event(runtime.store,'timeout');e=e.model_copy(update={'input':e.input.model_copy(update={'significance':'HIGH','uncertainty':'HIGH'})})
        runtime.submit(e);out=runtime.step()
        assert out['reason']=='MODEL_TIMEOUT_LIGHT_FALLBACK'
        assert runtime.store.all('runtime_cognition_calls')[0]['state']=='TIMED_OUT'
        old_identity=runtime.store.identity['identity_id'];epoch=runtime.lease.epoch
    with NanaRuntime(path,config,clock=clock) as restored:
        assert restored.store.identity['identity_id']==old_identity and restored.lease.epoch==epoch+1
        assert restored.cognition.availability=='DEGRADED'
        backoff=restored.cognition.backoff_until
        restored.cognition.set_model('cautious');restored.cognition.set_model('timeout')
        assert restored.cognition.availability=='DEGRADED' and restored.cognition.backoff_until==backoff
        assert restored.step() is None
        assert len(restored.store.all('subject_cycles'))==1


def test_restart_clock_floor_includes_committed_subject_history(tmp_path):
    path=tmp_path/'self.db';clock=VirtualClock();prepared(path,clock)
    cfg=RuntimeConfig(scopes=('life',),entity_id='synthetic-person',lease_us=3*HOUR,heartbeat_us=HOUR)
    old=NanaRuntime(path,cfg,clock=clock)
    identity=old.store.identity['identity_id'];clock.advance(HOUR)
    old.submit(event(old.store,'future-history'));floor=old.clock.utc_now_us()
    # Crash analogue for clock-floor unit boundary; process SIGKILL is qualified
    # independently. Leave old lease ACTIVE but release its dead Store handle.
    old.store.close();old.stopped=True
    clock.now_us-=2*HOUR
    with NanaRuntime(path,cfg,clock=clock) as restored:
        assert restored.clock.utc_now_us()>=floor and restored.store.identity['identity_id']==identity
        assert restored.lease.epoch==2
        restored.drain()
