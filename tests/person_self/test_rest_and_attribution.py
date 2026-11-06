"""Synthetic dialogue/clock/transport; not a human naturalness qualification."""
import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
from nana_core.continuity.open_agency.delivery import DeliveryAdmission, DeliveryPolicy
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import REST_DELIVERY_TOPIC, depth_boundary
from nana_core.continuity.subject.growth_life import availability
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.life.application import LifeApplication

from .conftest import initialize
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay


@pytest.mark.parametrize('text', [
    '他说先不聊这个了', '小明说他不想聊', '她转述：不要研究这个',
    '别人说不要处理，不是我的要求', '「先不聊」是别人说的',
    '朋友引用『不要研究』', '他说晚安', '她说我回来了',
])
def test_reported_speech_never_installs_a_literal_user_boundary(text):
    meaning=LiteralSpanInterpreter().interpret(text)
    assert meaning.kind=='UNCLEAR' and meaning.basis=='UNREVIEWED_PROPOSAL'


@pytest.mark.parametrize('text,expected', [
    ('我先不聊这个了','DECLINE_DELIVERY'), ('不要研究这个数据','DECLINE_DEPTH'),
    ('晚安！','DECLINE_DELIVERY'), ('我先休息了','DECLINE_DELIVERY'),
    ('我回来了','REOPEN_DELIVERY'), ('我醒了','REOPEN_DELIVERY'),
])
def test_first_person_boundaries_remain_explicit(text,expected):
    meaning=LiteralSpanInterpreter().interpret(text)
    assert meaning.kind==expected and meaning.basis=='LITERAL_SPAN'


def social_cycle(app,key):
    r=app.runtime
    cue=ConcernCue(cue_kind='DISCOVERY',topic_key='independent-interest',
        motivation_source='RELATIONSHIP',possible_behaviors=('SOCIALIZE',),availability='AVAILABLE')
    mid=capture(r,key,cue.model_dump_json(),predicate='concern.independent-interest')
    return r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.rest.'+key,
        kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=r.config.scopes[0],
        privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,)))


def test_rest_is_delivery_only_survives_restart_and_rechecks_old_admission(tmp_path):
    home=tmp_path/'life'; initialize(home); clock=VirtualClock()
    resource='synthetic://recipient/project-user'
    def gate(app):
        return DeliveryAdmission(app.runtime.store,DeliveryPolicy(recipients=(resource,),
            privacy_classes=('PUBLIC','PROJECT'),quiet_start_utc_hour=0,quiet_end_utc_hour=0),
            scopes=('project-work',),privacy_classes=('PUBLIC','PROJECT'))
    with LifeApplication(home,clock=clock) as app:
        app.pause(); identity=app.runtime.identity_id
        app.presence('AVAILABLE',privacy_classes=('PUBLIC','PROJECT'))
        before=social_cycle(app,'before-rest')
        assert before.intention.kind=='SOCIAL_INTERACTION'
        desire=app.runtime.store.one('subject_intentions',before.intention_id)
        allowed=gate(app).assess(before,resource)
        assert allowed['result']=='ELIGIBLE'
        app.chat('晚安',privacy='PROJECT',message_id='sleep')
        assert depth_boundary(app.runtime.store,'project-user','project-work',REST_DELIVERY_TOPIC,('PROJECT',))[0]
        assert not depth_boundary(app.runtime.store,'project-user','project-work',REST_DELIVERY_TOPIC,('PROJECT',),purpose='COGNITION')[0]
        with pytest.raises(CoreError,match='DELIVERY_ADMISSION_STALE'):
            gate(app).require(allowed['record_id'],resource)
        app.presence('AVAILABLE',privacy_classes=('PUBLIC','PROJECT'))  # does not override rest declaration
        assert app.runtime.store.one('subject_intentions',before.intention_id)==desire
        assert gate(app).assess(before,resource)['result']=='DEFER_RECIPIENT_REST'
        assert app.shared.notification_inbox(privacy=('PROJECT',))['state']=='SILENT_RECIPIENT_REST'
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
    clock.advance(60_000_000)
    with LifeApplication(home,clock=clock) as app:
        app.pause(); assert app.runtime.identity_id==identity
        assert app.shared.notification_inbox(privacy=('PROJECT',))['state']=='SILENT_RECIPIENT_REST'
        app.chat('我回来了',privacy='PROJECT',message_id='returned')
        assert not depth_boundary(app.runtime.store,'project-user','project-work',REST_DELIVERY_TOPIC,('PROJECT',))[0]
        app.presence('AVAILABLE',privacy_classes=('PUBLIC','PROJECT'))
        previous=app.runtime.subject.result(app.runtime.store.one('subject_cycles',before.cycle_id))
        assert previous.intention.kind=='SOCIAL_INTERACTION'
        assert gate(app).assess(previous,resource)['result']=='ELIGIBLE'
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_model_cannot_close_global_rest_and_new_direct_dialogue_still_works(tmp_path):
    home=tmp_path/'life'; initialize(home)
    with relay(home,'DECLINE_DELIVERY') as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause(); app.chat('小明说他不想聊',privacy='PROJECT',message_id='reported')
        assert len(requests)==1
        assert not depth_boundary(app.runtime.store,'project-user','project-work','daily',('PROJECT',))[0]
        assert not depth_boundary(app.runtime.store,'project-user','project-work',REST_DELIVERY_TOPIC,('PROJECT',))[0]
    home=tmp_path/'second-life'; initialize(home)
    with relay(home,'CHAT') as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause(); app.chat('我先睡了',privacy='PROJECT',message_id='sleep')
        assert requests==[]
        answer=app.chat('SYNTHETIC 还有一个项目问题',privacy='PROJECT',message_id='independent-new-turn')
        assert answer['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
        assert depth_boundary(app.runtime.store,'project-user','project-work',REST_DELIVERY_TOPIC,('PROJECT',))[0]
        assert not app.runtime.store.all('relationship_events')


def test_repeated_presence_is_temporal_correction_not_conflict_or_growing_attention(app):
    r=app.runtime; first=None
    for n in range(35):
        result=app.presence('BUSY' if n%2==0 else 'AVAILABLE',privacy_classes=('PUBLIC','PROJECT'))
        if first is None:first=result['source_memory_id']
    result=app.presence('AVAILABLE',privacy_classes=('PUBLIC','PROJECT'))
    state,parents=availability(r.store,'project-user',scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
    assert state=='AVAILABLE' and parents==(result['source_memory_id'],)
    assert r.store.one('memories',first)['assessment']=='SUPERSEDED'
    assert r.store.db.execute("SELECT count(*) FROM memories WHERE predicate_key LIKE 'recipient.%' AND assessment='CURRENT'").fetchone()[0]==1
    app.forget(result['source_memory_id'])
    assert availability(r.store,'project-user',scope='project-work',privacy_classes=('PUBLIC','PROJECT'))[0]=='UNKNOWN'
    assert not r.store.all('actions') and not r.store.all('grants')
