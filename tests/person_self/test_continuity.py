import json
import pytest
from nana_core.continuity.person_self import ConversationProposal,retain_input,adopted,project
from nana_core.continuity.subject.contracts import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication

PRIVACY=('PUBLIC','PROJECT','PERSONAL')

def propose(app,value='sibling',operation='PROPOSE',key='one',replaces=None,kind='RELATIONSHIP_ROLE'):
    r=app.runtime
    mid=retain_input(r.store,entity_id='project-user',scope='project-work',text='Please use '+value,privacy='PROJECT',message_id=key)
    event=SubjectInput(domain='LOCAL_INTERACTION',source_key='local.test.'+key,kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',text='Local input reviewed meaning: CHAT',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),interaction_signal=InteractionSignal(kind='CHAT',topic_key='daily',basis='EXPLICIT'),conversation_proposal=ConversationProposal(kind=kind,operation=operation,value=value,quote=value,replaces_record_id=replaces))
    return r.subject.run(event),mid,event


def test_adoption_is_c_decision_not_biological_fact_or_grant(app):
    c,mid,event=propose(app)
    assert c.judgment.stance=='AGREE' and c.conversation_decision.choice=='ADOPT'
    assert not app.runtime.store.all('grants') and not app.runtime.store.all('goals')
    view=project(app.runtime.store,entity_id='project-user',scope='project-work',privacy=PRIVACY)
    assert view['adopted_conventions'][0]['biological_claim'] is False
    before=app.runtime.store.db.execute("SELECT count(*) FROM continuity_records WHERE record_kind='ASSERTION'").fetchone()[0]
    assert app.runtime.subject.run(event).replayed
    assert app.runtime.store.db.execute("SELECT count(*) FROM continuity_records WHERE record_kind='ASSERTION'").fetchone()[0]==before


def test_conflict_play_correction_withdrawal_and_no_old_role_revival(app):
    propose(app)
    old=adopted(app.runtime.store,'project-work','project-user',PRIVACY)[0]['record_id']
    assert propose(app,'captain',key='conflict')[0].conversation_decision.choice=='KEEP_EXISTING'
    assert propose(app,'dragon','PLAY','play')[0].conversation_decision.choice=='PLAY_ONLY'
    assert propose(app,'friend','CORRECT','bad',replaces='unknown')[0].conversation_decision.choice=='ASK'
    c,mid,_=propose(app,'friend','CORRECT','good',replaces=old)
    assert c.conversation_decision.choice=='ADOPT'
    app.forget(mid)
    assert not adopted(app.runtime.store,'project-work','project-user',PRIVACY)


def test_projection_privacy_and_restart_preserve_identity(app):
    propose(app)
    identity=app.runtime.identity_id;home=app.home;clock=app.clock
    assert not adopted(app.runtime.store,'project-work','project-user',('PUBLIC',))
    app.close()
    with LifeApplication(home,clock=clock) as restored:
        clock.advance(3600_000_000)
        assert restored.runtime.identity_id==identity
        assert adopted(restored.runtime.store,'project-work','project-user',PRIVACY)
        clock.advance(86400_000_000)
        assert adopted(restored.runtime.store,'project-work','project-user',PRIVACY)


def test_unretained_receipt_or_model_quote_cannot_create_relationship(app):
    from nana_core.continuity.project_work.service import capture
    mid=capture(app.runtime,'receipt','not the quote')
    _,_,e=propose(app,key='good')
    e=e.model_copy(update={'source_key':'local.test.attack','source_memory_ids':(mid,)})
    with pytest.raises(CoreError,match='CONVERSATION_ADOPTION_SOURCE_REQUIRED'):
        app.runtime.subject.run(e)


def test_model_cannot_turn_explicit_roleplay_or_negative_role_into_adoption(app):
    from nana_core.continuity.person_self import retain_input
    r=app.runtime
    _,_,template=propose(app,key='initial')
    for i,(text,choice) in enumerate([('Please pretend sibling','PLAY_ONLY'),('Please do not call sibling','ASK')]):
        mid=retain_input(r.store,entity_id='project-user',scope='project-work',text=text,privacy='PROJECT',message_id='guard-'+str(i))
        event=template.model_copy(update={'source_key':'local.guard.'+str(i),'source_memory_ids':(mid,)})
        result=r.subject.run(event)
        assert result.conversation_decision.choice==choice
    assert adopted(r.store,'project-work','project-user',PRIVACY)[0]['payload']['decision']['proposal']['value']=='sibling'
