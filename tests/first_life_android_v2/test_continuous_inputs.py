"""Real private IPC, original owner/C and loopback model; no account or paid call."""
from contextlib import contextmanager
import json
import socket
import sqlite3
import threading
import time
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.control import ControlServer, request
from nana_core.life.config import load_config, update_config
from tests.first_life_android_v2.test_supervisor import owned
from tests.independent_life.test_dialogue import relay


@contextmanager
def running_owner(home, router):
    ready=threading.Event();stop=threading.Event();state={};errors=[]
    def run():
        try:
            with LifeApplication(home,router=router) as app, ControlServer(app) as control:
                app.pause();state.update(control=control,identity=app.runtime.identity_id);ready.set()
                while not stop.is_set() and not app.runtime.stop_requested:
                    control.poll();app.runtime.step();stop.wait(.005)
                state['actions']=len(app.runtime.store.all('actions'))
                state['surface_events']=app.runtime.store.db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'local.surface.%'").fetchone()[0]
                state['unknown']=[r['request_id'] for r in app.runtime.store.all('cognitive_requests') if r['state']=='UNKNOWN']
        except Exception as exc:
            errors.append(repr(exc));ready.set()
    thread=threading.Thread(target=run,daemon=True);thread.start()
    try:
        assert ready.wait(5) and not errors
        yield state
    finally:
        stop.set();thread.join(5)
        assert not thread.is_alive() and not errors,errors


def setup(home):
    cfg=load_config(home)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,
        'provider_calls_per_day':8,'provider_calls_per_hour':8,'per_provider_calls_per_day':8,
        'provider_total_calls_limit':8}),expected_revision=cfg.revision)


def message(event,text='SYNTHETIC continuation',**changes):
    return {'operation':'surface-stream','observation':{'binding_id':'nana.space','event_id':event,
        'text':text,'privacy_class':'PROJECT',**changes}}


def launch(home,command,progress=None):
    result={};done=threading.Event()
    def call():
        try:result['response']=request(home,command,timeout=8,progress=progress or (lambda _:None))
        except Exception as exc:result['error']=repr(exc)
        finally:done.set()
    thread=threading.Thread(target=call,daemon=True);thread.start()
    return result,done,thread


def wait_pending(control,count):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        if len(control.pending_inputs)==count:return
        time.sleep(.01)
    assert len(control.pending_inputs)==count


@pytest.mark.parametrize("retained",[False,True])
def test_followup_waits_without_recursive_subject_or_lost_input(tmp_path,retained):
    home,binding,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event()
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router) as state:
        def see(value):
            if value.get('text'):prefix.set()
        first,first_done,t1=launch(home,message('first','SYNTHETIC first thought'),see)
        second={};t2=None
        try:
            assert prefix.wait(3)
            second,second_done,t2=launch(home,message('second','SYNTHETIC added thought',retain_shared_life=retained))
            assert not second_done.wait(.2),'followup must wait, not be refused or recursively dispatched'
            assert len(calls)==2 and not first_done.is_set()
            status=request(home,{'operation':'view','view':'status'},timeout=2)
            assert status['ok'] and status['result']['identity_id']==binding.subject_id
            released_at_us=time.time_ns()//1000
            release.set()
            assert first_done.wait(5) and second_done.wait(5)
            assert first['response']['ok'] and second['response']['ok']
            assert len(calls)==4 and state['identity']==binding.subject_id
            first_mid=first['response']['result']['message_memory_id']
            second_render=calls[-1]['role_input']['dialogue']
            assert any(t['message_memory_id']==first_mid for t in second_render['recent_turns'])
            duplicate=request(home,message('second'),timeout=3,progress=lambda _:None)
            assert duplicate['ok'] and duplicate['result']['state']=='ALREADY_REVIEWED_NO_REPLAY'
            assert len(calls)==4
        finally:
            release.set();t1.join(5)
            if t2:t2.join(5)
    assert state['actions']==0 and not state['unknown'] and state['surface_events']==2
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        mid=second['response']['result']['message_memory_id']
        observed,recorded=db.execute('SELECT e.observed_time_us,m.created_at_us FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE m.memory_id=?',(mid,)).fetchone()
        assert observed < released_at_us <= recorded
        source=second['response']['result']['source_key']
        assert db.execute('SELECT observed_at_us FROM subject_events WHERE source_key=?',(source,)).fetchone()[0]==observed


def test_queue_bounds_privacy_stop_and_disconnected_inputs_before_dispatch(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event();clients=[]
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router) as state:
        first,done,thread=launch(home,message('active'),lambda v:prefix.set() if v.get('text') else None)
        try:
            assert prefix.wait(3)
            denied=request(home,message('not-bound',privacy_class='PERSONAL'),timeout=2,progress=lambda _:None)
            assert denied=={'ok':False,'code':'SURFACE_PRIVACY_NOT_BOUND'}
            for index in range(4):
                clients.append(launch(home,message('pending-'+str(index))))
                wait_pending(state['control'],index+1)
            overflow=request(home,message('overflow'),timeout=2,progress=lambda _:None)
            assert overflow=={'ok':False,'code':'CLOUD_INPUT_QUEUE_FULL_PRE_DISPATCH'}
            assert len(calls)==2
            stopped=request(home,{'operation':'control','command':'stop'},timeout=2)
            assert stopped['ok']
            release.set();assert done.wait(5)
            for result,finished,worker in clients:
                assert finished.wait(5)
                assert result['response']=={'ok':False,'code':'CLOUD_QUEUED_PRE_DISPATCH_CANCELLED'}
            assert len(calls)==2
        finally:
            release.set();thread.join(5)
            for _,_,worker in clients:worker.join(5)
    assert state['actions']==0 and state['surface_events']==1


def test_closed_waiting_client_never_enters_original_core(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event()
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router) as state:
        first,done,thread=launch(home,message('active'),lambda v:prefix.set() if v.get('text') else None)
        try:
            assert prefix.wait(3)
            client=socket.socket(socket.AF_UNIX);client.connect(str(home/'control.sock'))
            client.sendall((json.dumps(message('disconnected'))+'\n').encode())
            wait_pending(state['control'],1);client.close();release.set()
            assert done.wait(5)
            wait_pending(state['control'],0)
            probe=request(home,{'operation':'view','view':'status'},timeout=2)
            assert probe['ok'] and first['response']['ok'] and len(calls)==2
        finally:release.set();thread.join(5)
    assert state['actions']==0 and not state['unknown'] and state['surface_events']==1


def test_expired_waiting_input_does_not_start_cognition(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import nana_core.life.control as control_module
    offset=[0.]
    # Advance only the bounded IPC queue's monotonic clock; Runtime/transport
    # deadlines and the original Subject clock keep running normally.
    monkeypatch.setattr(control_module,'time',SimpleNamespace(monotonic=lambda:time.monotonic()+offset[0]))
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event();queued=None
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router) as state:
        first,done,thread=launch(home,message('active'),lambda v:prefix.set() if v.get('text') else None)
        try:
            assert prefix.wait(3)
            queued,finished,waiting=launch(home,message('too-late'))
            wait_pending(state['control'],1)
            offset[0]=1000.;release.set()
            assert done.wait(5) and finished.wait(5)
            assert first['response']['ok']
            assert queued['response']=={'ok':False,'code':'CLOUD_QUEUED_PRE_DISPATCH_EXPIRED'}
            assert len(calls)==2
        finally:
            release.set();thread.join(5)
            if queued is not None:waiting.join(5)
    assert state['actions']==0 and not state['unknown'] and state['surface_events']==1
