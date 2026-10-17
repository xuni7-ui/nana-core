import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.subject import SubjectInput
from nana_core.presence.contracts import RuntimeEvent,Cause,SECOND
from tests.world_loop.helpers import fresh
from .helpers import *

def periodic(c,a,*,ms=1000):
    p=c.configuration.load().sources[0].model_copy(update={'capture_mode':'PERIODIC','base_interval_ms':ms})
    c.configuration.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=c.configuration.load().revision,profile=p),a);return c.configuration.load().sources[0]
def user_event(r,key='user'):
    now=r.clock.utc_now_us();return RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=SubjectInput(source_key='synthetic.h2-user.'+key,kind='INTERACTION',origin='USER',entity_id='observer',scope='world',observed_at_us=now,text='public synthetic hello'),causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=now,priority=3)

def test_periodic_coalescing_disable_remove_preserves_history(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);periodic(c,a);c.attach();r.step();r.clock.source.advance(5*SECOND)
        result=r.step();assert result['perception']['state']=='GROUNDED' and adapter.captures==1
        mid=result['perception']['memory_id'];assert c.records.memory.read(mid)
        assert len([x for x in r.store.all('runtime_schedules') if x['state']=='ACTIVE' and x['dedupe_key'].startswith('h2.')])==1
        c.configuration.update(SourceCommand(operation='DISABLE_PERCEPTION_SOURCE',expected_revision=2,target_id='screen.a'),a)
        r.clock.source.advance(10*SECOND);r.step();assert adapter.captures==1 and c.records.memory.read(mid)
        c.configuration.update(SourceCommand(operation='REMOVE_PERCEPTION_SOURCE',expected_revision=3,target_id='screen.a'),a)
        r.step();assert c.records.memory.read(mid)
        with pytest.raises(CoreError,match='SOURCE_UNAVAILABLE'):c.request('screen.a',request_id='removed')

def test_user_preempts_at_capture_safe_point_one_owner(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);c.attach()
        def cut(stage):
            if stage=='AFTER_CAPTURE_BEFORE_INGEST':r.post(user_event(r))
        c._checkpoint=cut;c.enqueue(c.request('screen.a',request_id='background'))
        result=r.step();assert result['perception']['reason']=='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED' and m.calls==0
        user=r.step();assert r.store.one('runtime_queue',user['queue_id'])['event_type']=='USER_EVENT'
        assert r.queue.depth()==0 and len(r.store.all('subject_cycles'))<=1
        # A later opportunity is a new observation, not revival of the lost bytes.
        c._checkpoint=lambda stage:None;r.clock.source.advance(SECOND)
        c.enqueue(c.request('screen.a',request_id='later'));assert r.step()['perception']['state']=='GROUNDED'

def test_background_queue_bounded_and_foreground_permission(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);c.attach()
        c.configuration.update(SourceCommand(operation='SET_CAPTURE_POLICY',expected_revision=1,policy=CapturePolicy(pending_capacity=2)),a)
        for i in range(2):c.enqueue(c.request('screen.a',request_id='q'+str(i)))
        with pytest.raises(CoreError,match='BACKPRESSURE'):c.enqueue(c.request('screen.a',request_id='q3'))
        assert len(c.state['pending'])==2 and adapter.bytes_read==0
        r.submit(user_event(r));one=r.step();assert r.store.one('runtime_queue',one['queue_id'])['event_type']=='USER_EVENT'


def test_event_driven_sample_expiry_no_fabricated_restore(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);c.attach()
        adapter.publish('frame.pending',png(),event_time=r.clock.utc_now_us(),sequence=7)
        req=c.request('screen.a',request_id='event-one',sample_key='frame.pending');value=c.observe(req);assert value['state']=='GROUNDED'
        r.clock.source.advance(SECOND)
        missing=c.observe(c.request('screen.a',request_id='event-two',sample_key='not-retained'))
        assert missing['reason']=='SOURCE_SAMPLE_EXPIRED' and m.calls==1

def test_event_metadata_producer_uses_original_runtime_pull_no_bytes_in_queue(tmp_path):
    import threading
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);c.attach();p=c.configuration.load().sources[0].model_copy(update={'capture_mode':'EVENT_DRIVEN'})
        c.configuration.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=1,profile=p),a)
        now=r.clock.utc_now_us();adapter.publish('sample1',png(),event_time=now,sequence=1);receipts=[]
        producer=threading.Thread(target=lambda:receipts.append(c.notify_sample('screen.a','sample1',observed_at_us=now)));producer.start();producer.join(2)
        assert receipts and adapter.bytes_read==0
        result=r.step();assert receipts[0].wait(.1) and result['perception']['state']=='GROUNDED' and m.calls==1
        assert all('data_b64' not in row['metadata_json'] for row in r.store.all('runtime_queue'))
        r.clock.source.advance(SECOND)
        receipts.append(c.notify_sample('screen.a','lost-sample',observed_at_us=r.clock.utc_now_us()))
        result=r.step();assert result['perception']['reason']=='SOURCE_SAMPLE_EXPIRED' and m.calls==1

def test_repeated_tick_while_user_pressure_has_one_pending_per_source(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,adapter,m,a=setup(r,tmp_path);periodic(c,a,ms=1000);c.attach();r.step()
        for n in range(3):
            r.clock.source.advance(2*SECOND);r.submit(user_event(r,'pressure'+str(n)));result=r.step()
            assert r.store.one('runtime_queue',result['queue_id'])['event_type']=='USER_EVENT'
        pending=r.store.db.execute("SELECT count(*) FROM runtime_queue WHERE event_type='DEVICE_EVENT' AND state IN ('READY','DEFERRED')").fetchone()[0]
        assert pending==1 and adapter.captures==0 and c.state['coalesced']>=1
        assert r.step()['perception']['state']=='GROUNDED' and adapter.captures==1
