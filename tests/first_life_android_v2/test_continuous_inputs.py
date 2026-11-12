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
def running_owner(home, router, *, coalesce_continuations=False):
    ready=threading.Event();stop=threading.Event();state={};errors=[]
    def run():
        try:
            with LifeApplication(home,router=router) as app, ControlServer(app,coalesce_continuations=coalesce_continuations) as control:
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


@pytest.mark.parametrize('enabled',[False,True])
def test_input_already_at_socket_is_checked_at_render_completion_without_an_extra_model_tick(tmp_path,enabled):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event()
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router,coalesce_continuations=enabled) as state:
        # Deterministic boundary: the transport's last progress tick happened
        # before the new bytes. No subsequent model-wait tick is promised.
        state['control'].app.runtime.control_progress=lambda:None
        first,done,thread=launch(home,message('completion-root'),lambda v:prefix.set() if v.get('text') else None)
        child=socket.socket(socket.AF_UNIX);child.settimeout(6)
        try:
            assert prefix.wait(3)
            child.connect(str(home/'control.sock'))
            child.sendall((json.dumps({**message('completion-child'),'operation':'surface'})+'\n').encode())
            assert not state['control'].pending_inputs
            release.set();assert done.wait(5)
            second=json.loads(child.makefile('rb').readline())
            assert first['response']['ok'] and second['ok'] and len(calls)==4
            parent=first['response']['result'];reply=second['result']
            if enabled:
                assert parent['text'] is None and parent['render_state']=='DEFERRED_TO_CONTINUATION'
                assert reply['respond_to_memory_ids']==[parent['message_memory_id'],reply['message_memory_id']]
            else:
                assert parent['text'] and reply['respond_to_memory_ids']==[reply['message_memory_id']]
        finally:
            release.set();child.close();thread.join(5)


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


@pytest.mark.parametrize('enabled',[False,True])
def test_queue_bounds_privacy_stop_and_disconnected_inputs_before_dispatch(tmp_path,enabled):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event();clients=[]
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router,coalesce_continuations=enabled) as state:
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


@pytest.mark.parametrize('enabled',[False,True])
def test_closed_waiting_client_never_enters_original_core(tmp_path,enabled):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event()
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router,coalesce_continuations=enabled) as state:
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


@pytest.mark.parametrize('enabled',[False,True])
def test_expired_waiting_input_does_not_start_cognition(tmp_path,monkeypatch,enabled):
    from types import SimpleNamespace
    import nana_core.life.control as control_module
    offset=[0.]
    # Advance only the bounded IPC queue's monotonic clock; Runtime/transport
    # deadlines and the original Subject clock keep running normally.
    monkeypatch.setattr(control_module,'time',SimpleNamespace(monotonic=lambda:time.monotonic()+offset[0]))
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event();queued=None
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router,coalesce_continuations=enabled) as state:
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


@pytest.mark.parametrize('enabled',[False,True])
@pytest.mark.parametrize('arrival_phase',['INTERPRET','RENDER'])
@pytest.mark.parametrize('unicode_input',[False,True])
def test_isolated_same_owner_continuation_reorganizes_only_unsent_draft(tmp_path,enabled,arrival_phase,unicode_input):
    home,binding,_=owned(tmp_path);setup(home)
    release=threading.Event();blocked=threading.Event();waiting=[]
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls):
        original_create=router.factory.create
        def create(*args):
            port=original_create(*args);exchange=port.exchange
            def exchange_once(request):
                if arrival_phase=='INTERPRET' and request.cognitive_role=='INTERPRET' and not blocked.is_set():
                    blocked.set();assert release.wait(4)
                return exchange(request)
            port.exchange=exchange_once
            return port
        router.factory.create=create
        with running_owner(home,router,coalesce_continuations=enabled) as state:
            def see(value):
                if arrival_phase=='RENDER' and value.get('text'):blocked.set()
            # The relay echoes interpretation in ensure_ascii JSON. Keep its
            # response inside the unchanged output-byte bound while checking
            # full2048-character input and a separate >1024 Han-character input.
            filler='细'*1100 if unicode_input else 'x'*(2048-len('SYNTHETIC ')-len('SYNTHETIC_UNANSWERED_TAIL'))
            original_text='SYNTHETIC '+filler+'SYNTHETIC_UNANSWERED_TAIL'
            assert 1024<len(original_text)<=2048
            first,done,t1=launch(home,message('draft-parent',original_text),see)
            try:
                assert blocked.wait(3),first
                second,done2,t2=launch(home,message('draft-next','SYNTHETIC another thought before reply'))
                waiting.append(t2);wait_pending(state['control'],1)
                assert not done.is_set() and not done2.is_set()
                release.set();assert done.wait(5) and done2.wait(5)
                a=first['response']['result'];b=second['response']['result']
                assert first['response']['ok'] and second['response']['ok']
                assert state['identity']==binding.subject_id
                if enabled:
                    assert a['text'] is None and a['render_state']=='DEFERRED_TO_CONTINUATION'
                    assert b['text']=='A deliberately synthetic language response'
                    render=calls[-1]['role_input']['dialogue']
                    assert render['communication_purpose']['respond_to_memory_ids']==[a['message_memory_id'],b['message_memory_id']]
                    assert not any(t['speaker']=='ASSISTANT' and t['message_memory_id']==a['message_memory_id'] for t in render['recent_turns'])
                    assert any(t['speaker']=='USER' and t['message_memory_id']==a['message_memory_id'] for t in render['recent_turns'])
                    original_turn=next(t for t in render['recent_turns'] if t['speaker']=='USER' and t['message_memory_id']==a['message_memory_id'])
                    assert original_turn['text']==original_text and not original_turn.get('text_truncated',False)
                    assert len(calls)==(3 if arrival_phase=='INTERPRET' else 4)
                else:
                    assert a['text']==b['text']=='A deliberately synthetic language response'
                    assert len(calls)==4
                assert not a['raw_body_persisted'] and not b['raw_body_persisted']
                previous=next(t for t in state['control'].app._recent if t.speaker=='USER' and t.message_memory_id==a['message_memory_id'])
                assert previous.text==original_text[:1024] and previous.text_truncated
            finally:
                release.set();t1.join(5)
                for thread in waiting:thread.join(5)
        assert state['actions']==0 and state['surface_events']==2 and not state['unknown']
        with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
            assert not db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0",
                                  ('SYNTHETIC_UNANSWERED_TAIL',)).fetchone()


@pytest.mark.parametrize('boundary',['retained','different-thread','literal-rest'])
def test_isolated_draft_keeps_contexts_separate_and_honors_new_rest(tmp_path,boundary):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();prefix=threading.Event();threads=[]
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router,coalesce_continuations=True) as state:
        first,done,t1=launch(home,message('separate-parent'),lambda value:prefix.set() if value.get('text') else None)
        try:
            assert prefix.wait(3)
            changes={'retain_shared_life':True} if boundary=='retained' else {'thread_id':'other-thread'} if boundary=='different-thread' else {}
            second,done2,t2=launch(home,message('separate-next','我先休息了' if boundary=='literal-rest' else 'SYNTHETIC separate input',**changes))
            threads.append(t2);wait_pending(state['control'],1);release.set()
            assert done.wait(5) and done2.wait(5)
            a=first['response']['result'];b=second['response']['result']
            if boundary=='literal-rest':
                assert a['render_state']=='DEFERRED_TO_CONTINUATION' and a['text'] is None
                assert b['mode']=='RESPECT_BOUNDARY' and len(calls)==2
            else:
                assert a['render_state']=='UNVERIFIED_MODEL_WORDING' and a['text']=='A deliberately synthetic language response'
                assert len(calls)==4 and calls[-1]['role_input']['dialogue']['communication_purpose']['respond_to_memory_ids']==[b['message_memory_id']]
            assert b['raw_body_persisted']==(boundary=='retained')
        finally:
            release.set();t1.join(5)
            for thread in threads:thread.join(5)
    assert state['actions']==0 and not state['unknown']


def test_isolated_draft_is_not_discarded_for_an_already_reviewed_input(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    release=threading.Event();release.set();prefix=threading.Event();threads=[]
    with relay(home,'CHAT',stream_fixture={'release':release}) as (router,calls),running_owner(home,router,coalesce_continuations=True) as state:
        prior,done,t0=launch(home,message('old-source'));threads.append(t0)
        assert done.wait(5) and prior['response']['ok'];release.clear()
        first,done1,t1=launch(home,message('new-source'),lambda value:prefix.set() if value.get('text') else None);threads.append(t1)
        try:
            assert prefix.wait(3)
            duplicate,done2,t2=launch(home,message('old-source'));threads.append(t2)
            wait_pending(state['control'],1);release.set()
            assert done1.wait(5) and done2.wait(5)
            assert first['response']['result']['render_state']=='UNVERIFIED_MODEL_WORDING'
            assert first['response']['result']['text']=='A deliberately synthetic language response'
            assert duplicate['response']['result']['state']=='ALREADY_REVIEWED_NO_REPLAY'
            assert len(calls)==4
        finally:
            release.set()
            for thread in threads:thread.join(5)
    assert state['surface_events']==2 and not state['unknown'] and state['actions']==0
