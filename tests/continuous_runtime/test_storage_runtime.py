import pytest
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore
from nana_core.continuity.subject import SubjectInput,SubjectLoop
from nana_core.presence.contracts import RuntimeEvent,Cause,ScheduleSpec,SECOND
from nana_core.presence.queue import EventQueue
from nana_core.presence.scheduler import Scheduler


def event(store,key,**updates):
    now=store.clock.utc_now_us()
    data=dict(event_type='USER_EVENT',trigger='INCOMING_EVENT',
        input=SubjectInput(source_key='synthetic.runtime.'+key,kind='INTERACTION',origin='USER',
            entity_id='synthetic-person',scope='life',text='A synthetic significant experience',
            observed_at_us=now,occurred_at_us=now,significance='RELEVANT'),
        causes=(Cause(kind='CANONICAL_SELF',reference_id=store.identity['identity_id']),),due_at_us=now)
    data.update(updates)
    return RuntimeEvent(**data)


def test_queue_cycle_commit_recovery_dedup_privacy(active):
    store,config,lease,clock=active
    queue=EventQueue(store,config,lease)
    e=event(store,'one')
    qid=queue.enqueue(e)
    assert queue.enqueue(e)==qid
    claimed=queue.claim()
    result=SubjectLoop(store,scopes=('life',)).run(queue.input(claimed))
    queue.recover()  # actual process cuts are covered in process qualification
    assert store.one('runtime_queue',qid)['cycle_id']==result.cycle_id
    assert store.one('runtime_queue',qid)['state']=='DONE' and not queue.claim()
    before=len(store.all('events'))
    for _ in range(20):assert queue.claim() is None
    assert len(store.all('events'))==before  # idle polling is not event history
    private=e.input.model_copy(update={'source_key':'synthetic.runtime.nonretention','text':'DO-NOT-SAVE-RUNTIME-BODY','retention':'DO_NOT_REMEMBER'})
    p=queue.enqueue(event(store,'unused',input=private))
    assert queue.input(store.one('runtime_queue',p)).text is None
    assert 'DO-NOT-SAVE-RUNTIME-BODY' not in str(store.snapshot())
    assert not any(store.all(t) for t in ('actions','attempts','grants','budgets'))


def test_lease_expiry_transaction_fence_and_no_double_writer(active):
    store,config,lease,clock=active
    with pytest.raises(CoreError,match='RUNTIME_ALREADY_ACTIVE'):
        ContinuityStore(store.path,clock,schema_target=8)
    with pytest.raises(CoreError,match='RUNTIME_LEASE_LOST'):
        with store.transaction('must.rollback') as tx:
            tx.put('core_meta',{'key':'should_not_commit','value_json':'true'})
            clock.advance(config.lease_us+1)
    assert store.one('core_meta','should_not_commit') is None
    with pytest.raises(CoreError,match='RUNTIME_LEASE_LOST'):lease.heartbeat()
    with pytest.raises(CoreError,match='RUNTIME_LEASE_LOST'):SubjectLoop(store,scopes=('life',)).run(event(store,'late').input)


def test_scheduler_coalesces_and_resumes_same_occurrence(active):
    store,config,lease,clock=active
    queue=EventQueue(store,config,lease);scheduler=Scheduler(store,config,queue)
    now=store.clock.utc_now_us()
    wake=SubjectInput(source_key='synthetic.runtime.template',kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-person',scope='life',observed_at_us=now)
    template=event(store,'unused',event_type='TIME_EVENT',trigger='TIME_TRIGGER',input=wake,due_at_us=now)
    sid=scheduler.add(ScheduleSpec(dedupe_key='periodic',kind='PERIODIC',due_at_us=now+SECOND,interval_us=SECOND,event=template))
    clock.advance(10*SECOND);lease.heartbeat(force=True);scheduler.due()
    assert len(store.all('runtime_queue'))==1
    assert store.one('runtime_schedules',sid)['occurrence']==1
    assert store.all('runtime_queue')[0]['due_at_us']==now+SECOND
    assert scheduler.store.one('runtime_schedules',sid)['due_at_us']==now+11*SECOND
    scheduler.due();assert len(store.all('runtime_queue'))==1
    backup=store.path.parent/'backup'/'self.db';store.backup(backup)
    from nana_core.presence.authority import RuntimeLease
    with ContinuityStore(backup,clock,schema_target=8) as copy:
        with pytest.raises(CoreError,match='RUNTIME_RESTORE_QUARANTINED'):RuntimeLease(copy,config).acquire()
