import threading,time
from nana_core.presence.cadence import Cadence
from .helpers import fresh,event

def test_interruptible_wait_durable_ingress_and_clean_shutdown(tmp_path):
    with fresh(tmp_path/'self.db') as r:
        receipt=[]
        incoming=event(r,'incoming',text='A synthetic timely input',significance='RELEVANT')
        def producer():
            time.sleep(.02);receipt.append(r.post(incoming))
        t=threading.Thread(target=producer);t.start()
        stamp=r.cadence.stamp();start=time.monotonic();r.cadence.wait(2,stamp)
        assert time.monotonic()-start<.5
        r.step();t.join();assert receipt[0].wait(.2)
        assert r.store.all('subject_cycles')
        assert r.cadence.idle_rounds==0

def test_background_cognition_preempted_without_duplicate_subject_commit(tmp_path):
    with fresh(tmp_path/'self.db',model='timeout',model_timeout_seconds=.5) as r:
        background=event(r,'background',background=True,novelty='HIGH',uncertainty='HIGH',significance='HIGH')
        qid=r.submit(background)
        incoming=event(r,'foreground',text='A synthetic urgent input',significance='RELEVANT')
        def producer():
            time.sleep(.05);r.post(incoming)
        t=threading.Thread(target=producer);t.start();result=r.step();t.join()
        assert result['reason']=='PREEMPTED'
        assert not r.store.all('subject_cycles')
        assert r.store.one('runtime_queue',qid)['state']=='DEFERRED'
        assert r.store.all('runtime_cognition_calls')[0]['state']=='CANCELLED'
        foreground=r.step();assert foreground['queue_id']!=qid
        resumed=r.step();assert resumed['queue_id']==qid
        assert len(r.store.all('subject_cycles'))==2
