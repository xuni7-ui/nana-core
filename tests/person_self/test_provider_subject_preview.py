"""Read-only existing request admission for D; a preview creates no entitlement."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.subject.contracts import DeliberationFrame
from nana_core.continuity.subject.policy import appraise,motivate,decide
from nana_core.continuity.subject.opportunities import directions
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
from nana_core.continuity.world_loop.harness import provider_harness
from .test_provider_subject_cognition import initialize,event_for,candidate


def inputs(app):
    r=app.runtime;mid,event=event_for(app)
    source=r.subject.ingress.ingest(event);s=r.subject.situation(event,source);appraisal=appraise(event,s);motives=motivate(event,s,appraisal)
    frame=DeliberationFrame(subject_event_id=source['subject_event_id'],scope=event.scope,appraisal=appraisal,motivations=motives,
        attention=decide(event,s,appraisal,motives)[0],source_memory_ids=s.memory_ids,source_record_ids=s.support_record_ids,
        behavior_options=tuple(directions(s.cue)))
    return mid,dict(subject_frame=frame,role_input={'subject_cognition':{'subject_event_id':frame.subject_event_id,'privacy_class':'PROJECT'}},
        budget=CognitionBudget(input_tokens=32768))


def test_preview_is_read_only_matches_actual_reservation_and_exposes_no_context(tmp_path):
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,options=inputs(app);session=CognitionSession(r,transport,app.policy)
        before=r.store.db.total_changes;snapshot=r.store.snapshot()
        first=session.preview('eventual-self','SELF',(mid,),**options)
        assert session.preview('eventual-self','SELF',(mid,),**options)==first
        assert r.store.db.total_changes==before and r.store.snapshot()==snapshot and state['calls']==0
        assert first['state']=='WOULD_PREPARE' and first['reservation_created'] is False and first['execution_authority'] is False
        assert 'context_json' not in json.dumps(first) and 'subject_event_id' not in json.dumps(first)
        rid=session.prepare('eventual-self','SELF',(mid,),**options)
        assert r.store.one('cognitive_requests',rid)['reserved_bytes']==first['reserved_bytes']
        before=r.store.db.total_changes
        existing=session.preview('eventual-self','SELF',(mid,),**options)
        assert existing['existing_request'] and existing['request_id']==rid and existing['state']=='PREPARED'
        assert r.store.db.total_changes==before and state['calls']==0


@pytest.mark.parametrize('reason',['cost','framing'])
def test_blocked_preview_changes_no_original_store_or_model_counter(tmp_path,reason):
    from tests.world_loop.test_model_framing import bind
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,options=inputs(app);session=CognitionSession(r,transport,app.policy)
        if reason=='framing':bind(transport,lambda body:70000)
        else:options['budget']=CognitionBudget(cost_ceiling_micro=17)
        before=r.store.db.total_changes;snapshot=r.store.snapshot()
        with pytest.raises(CoreError,match='INSUFFICIENT_CONTEXT_BUDGET' if reason=='framing' else 'COGNITION_COST_BUDGET'):
            session.preview('blocked-self','SELF',(mid,),**options)
        assert r.store.db.total_changes==before and r.store.snapshot()==snapshot and state['calls']==0
        assert not r.store.all('cognitive_requests') and not r.store.all('runtime_cognition_calls')


def test_positive_preview_does_not_reserve_a_slot_or_bypass_changed_daily_budget(tmp_path):
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,options=inputs(app);session=CognitionSession(r,transport,app.policy,max_calls_per_day=1)
        assert session.preview('previewed','SELF',(mid,),**options)['state']=='WOULD_PREPARE'
        session.prepare('independent-admission','INTERPRET',(mid,))
        with pytest.raises(CoreError,match='COGNITION_DAILY_BUDGET'):session.prepare('previewed','SELF',(mid,),**options)
        assert len(r.store.all('cognitive_requests'))==1 and state['calls']==0
