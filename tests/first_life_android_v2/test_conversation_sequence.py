"""Original owner/C, bounded already-received inputs; synthetic language only."""
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.control import dispatch
from tests.first_life_android_v2.test_supervisor import owned
from tests.first_life_android_v2.test_continuous_inputs import setup
from tests.first_life_android_v2.test_continuous_inputs import running_owner
from tests.independent_life.test_dialogue import relay


def sequence(*,retained=False):
    return {'operation':'surface-sequence','observations':[
        {'binding_id':'nana.space','event_id':'sequence-'+str(i),'thread_id':'same-recipient',
         'topic':'daily','privacy_class':'PROJECT','retain_shared_life':retained,
         'text':'SYNTHETIC part '+str(i)} for i in range(3)]}


@pytest.mark.parametrize('long_input',[False,True])
def test_unanswered_sequence_has_individual_c_and_one_source_bound_reply(tmp_path,long_input):
    home,binding,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        request=sequence()
        if long_input:
            tail='SYNTHETIC_QUEUE_TAIL'
            request['observations'][0]['text']='SYNTHETIC '+('x'*(2048-len('SYNTHETIC ')-len(tail)))+tail
        app.pause();result=dispatch(app,request)
        assert result['state']=='SHADOW_SEQUENCE_REVIEWED' and result['coalesced'] is True
        inputs=result['results'];assert len(inputs)==3
        mids=[r['message_memory_id'] for r in inputs]
        assert len(set(mids))==3
        assert [r['render_state'] for r in inputs[:2]]==['DEFERRED_TO_CONTINUATION']*2
        assert all(r['text'] is None and not r['delivered'] for r in inputs[:2])
        assert inputs[-1]['render_state']=='UNVERIFIED_MODEL_WORDING'
        assert [c['cognitive_role'] for c in calls]==['INTERPRET']*3+['SOCIAL']
        dialogue=calls[-1]['role_input']['dialogue']
        assert dialogue['communication_purpose']['respond_to_memory_ids']==mids
        assert dialogue['communication_purpose']['cycle_id']==inputs[-1]['cycle_id']
        assert [t['text'] for t in dialogue['recent_turns']]==[o['text'] for o in request['observations'][:2]]
        assert not any(t.get('text_truncated',False) for t in dialogue['recent_turns'])
        assert all(t['speaker']=='USER' for t in dialogue['recent_turns'])
        assert all(set(mids[:i+1])<=set(calls[i]['source_context_refs']) for i in range(3))
        assert app.runtime.store.db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'local.surface.%'").fetchone()[0]==3
        assert len(set(r['cycle_id'] for r in inputs))==3
        assert app.runtime.identity_id==binding.subject_id
        if long_input:
            assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC_QUEUE_TAIL')>0").fetchone()
        again=dispatch(app,request);assert not again['coalesced']
        assert all(r['state']=='ALREADY_REVIEWED_NO_REPLAY' for r in again['results'])
        assert len(calls)==4
        later=dispatch(app,{'operation':'surface','observation':{
            'binding_id':'nana.space','event_id':'after-sequence','thread_id':'same-recipient',
            'text':'SYNTHETIC separate later question','privacy_class':'PROJECT'}})
        assert calls[-1]['role_input']['dialogue']['communication_purpose']['respond_to_memory_ids']==[later['message_memory_id']]
        assert len(calls)==6
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC part')>0").fetchone()


@pytest.mark.parametrize('field,value',[('thread_id','other'),('privacy_class','PUBLIC'),('topic','other')])
def test_sequence_cannot_mix_recipient_or_source_scope(tmp_path,field,value):
    home,_,_=owned(tmp_path)
    with LifeApplication(home) as app:
        request=sequence();request['observations'][1][field]=value
        with pytest.raises(CoreError,match='SURFACE_SEQUENCE_SCOPE_REQUIRED'):dispatch(app,request)
        assert not app.runtime.store.all('subject_events')
        assert not app.runtime.store.all('cognitive_requests')


def test_partially_seen_sequence_never_replays_or_silently_dispatches_its_tail(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();request=sequence()
        dispatch(app,{'operation':'surface','observation':request['observations'][0]})
        with pytest.raises(CoreError,match='SURFACE_SEQUENCE_PARTIAL_NO_REPLAY'):dispatch(app,request)
        assert len(calls)==2
        assert app.runtime.store.db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'local.surface.%'").fetchone()[0]==1


def test_retention_keeps_individual_exchange_and_feedback_semantics(tmp_path):
    from nana_core.life.conversation import history
    home,_,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();result=dispatch(app,sequence(retained=True))
        assert result['coalesced'] is False and len(calls)==6
        rows=result['results'];assert len({r['exchange_record_id'] for r in rows})==3
        assert all(r['raw_body_persisted'] and r['render_state']=='UNVERIFIED_MODEL_WORDING' for r in rows)
        for response,call in zip(rows,calls[1::2]):
            assert call['role_input']['dialogue']['communication_purpose']['respond_to_memory_ids']==[response['message_memory_id']]
        assert len(history(app,privacy=('PROJECT',))['items'])==3


def test_explicit_boundary_is_not_delayed_or_turned_into_a_group_draft(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();request=sequence();request['observations'][0]['text']='这个话题不要深入了'
        result=dispatch(app,request)
        assert not result['coalesced'] and not calls
        assert all(r['mode']=='RESPECT_BOUNDARY' for r in result['results'])
        assert all(r['render_state']!='DEFERRED_TO_CONTINUATION' for r in result['results'])


def test_sequence_runs_through_original_private_ipc_owner(tmp_path):
    from nana_core.life.control import request
    home,binding,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),running_owner(home,router) as owner:
        response=request(home,sequence())
        assert response['ok'] and response['result']['coalesced']
        assert len(calls)==4 and owner['identity']==binding.subject_id
    assert owner['surface_events']==3 and owner['actions']==0 and not owner['unknown']


def test_unknown_stops_only_this_sequence_and_does_not_replay_its_draft(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
    home,_,_=owned(tmp_path);setup(home)
    original=OpenAIJSONTransport.exchange;attempts=[]
    def exchange(self,request):
        attempts.append(request.request_id)
        if len(attempts)==2:raise TimeoutError()
        return original(self,request)
    monkeypatch.setattr(OpenAIJSONTransport,'exchange',exchange)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause()
        with pytest.raises(CoreError,match='SURFACE_SEQUENCE_INCOMPLETE_NO_REPLAY'):dispatch(app,sequence())
        assert len(attempts)==2 and len(calls)==1 and not app._recent
        pending=[r for r in app.runtime.store.all('cognitive_requests') if r['state']=='UNKNOWN']
        assert len(pending)==1;unknown=pending[0]
        with pytest.raises(CoreError,match='SURFACE_SEQUENCE_PARTIAL_NO_REPLAY'):dispatch(app,sequence())
        assert len(attempts)==2
        independent=dispatch(app,{'operation':'surface','observation':{
            'binding_id':'nana.space','event_id':'independent','thread_id':'same-recipient',
            'text':'SYNTHETIC new independent input','privacy_class':'PROJECT'}})
        assert independent['render_state']=='UNVERIFIED_MODEL_WORDING' and len(attempts)==4
        assert calls[-2]['role_input']['dialogue']['recent_turns']==[]
        after=app.runtime.store.one('cognitive_requests',unknown['request_id'])
        assert (after['state'],after['reserved_cost_micro'])==('UNKNOWN',unknown['reserved_cost_micro'])


def test_interrupted_sequence_survives_restart_as_partial_without_replay(tmp_path,monkeypatch):
    home,binding,_=owned(tmp_path);setup(home)
    original=LifeApplication._reviewed_chat
    def stop_after_first(self,key):
        original(self,key);self.runtime.stop_requested=True
    with relay(home,'CHAT') as (router,calls):
        with LifeApplication(home,router=router) as app:
            app.pause();monkeypatch.setattr(LifeApplication,'_reviewed_chat',stop_after_first)
            with pytest.raises(CoreError,match='SURFACE_SEQUENCE_INTERRUPTED_NO_REPLAY'):dispatch(app,sequence())
            assert len(calls)==1 and not app._recent
        monkeypatch.setattr(LifeApplication,'_reviewed_chat',original)
        with LifeApplication(home,router=router) as app:
            assert app.runtime.identity_id==binding.subject_id
            with pytest.raises(CoreError,match='SURFACE_SEQUENCE_PARTIAL_NO_REPLAY'):dispatch(app,sequence())
            assert len(calls)==1 and not app._recent


def test_withdrawn_unanswered_source_stops_before_another_model_call(tmp_path,monkeypatch):
    home,_,_=owned(tmp_path);setup(home)
    original=LifeApplication._reviewed_chat
    def withdraw(self,key):
        original(self,key);self.forget(self._recent[-1].message_memory_id)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();monkeypatch.setattr(LifeApplication,'_reviewed_chat',withdraw)
        with pytest.raises(CoreError):dispatch(app,sequence())
        assert len(calls)==1 and not app._recent
        assert len(app.runtime.store.all('cognitive_requests'))==1
        assert app.runtime.store.db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'local.surface.%'").fetchone()[0]==1


def test_same_budget_nonretained_serial_control_keeps_three_c_and_six_calls(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();results=[dispatch(app,{'operation':'surface','observation':o}) for o in sequence()['observations']]
        assert len({r['cycle_id'] for r in results})==3
        assert [c['cognitive_role'] for c in calls]==['INTERPRET','SOCIAL']*3
        assert all(r['render_state']=='UNVERIFIED_MODEL_WORDING' and not r['raw_body_persisted'] for r in results)
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_sequence_does_not_replace_original_c_wait_with_social_reply(tmp_path):
    home,_,_=owned(tmp_path);setup(home)
    with relay(home,'UNCLEAR') as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();result=dispatch(app,sequence())
        assert not result['coalesced'] and len(calls)==6
        assert all(r['judgment']=='ASK' and r['intention']=='WAIT' for r in result['results'])
        assert all(r['render_state']!='DEFERRED_TO_CONTINUATION' for r in result['results'])
