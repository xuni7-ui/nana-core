from nana_core.continuity.person_self import project,retain_input,retain_exchange
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal
from .test_continuity import propose


def test_eighty_retained_turns_do_not_exhaust_source_horizon_or_lose_role(app):
    # No provider needed: report synthetic speech with the full selected source
    # ancestry, exercising the same retained exchange closure as real rendering.
    propose(app)
    for old in app.runtime.subject.pending('project-work'):
        app.runtime.subject.transition_intention(old['intention_id'],expected_revision=old['revision'],state='DROPPED')
    r=app.runtime
    for i in range(80):
        mid=retain_input(r.store,entity_id='project-user',scope='project-work',text='Synthetic turn '+str(i),privacy='PROJECT',message_id='bounded-'+str(i))
        c=r.subject.run(SubjectInput(domain='LOCAL_INTERACTION',source_key='local.bounded.'+str(i),kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=app.clock.utc_now_us(),text='Local input reviewed meaning: CHAT',source_memory_ids=(mid,),interaction_signal=InteractionSignal(kind='CHAT',topic_key='daily',basis='EXPLICIT')))
        before=project(r.store,entity_id='project-user',scope='project-work',privacy=('PROJECT',),topic='daily')
        retain_exchange(r.store,entity_id='project-user',scope='project-work',topic='daily',user_memory_id=mid,text='SYNTHETIC reported speech',cycle=c,source_memory_ids=before['source_memory_ids'])
        if c.intention_id:
            row=r.store.one('subject_intentions',c.intention_id)
            r.subject.transition_intention(c.intention_id,expected_revision=row['revision'],state='DROPPED')
        after=project(r.store,entity_id='project-user',scope='project-work',privacy=('PROJECT',),topic='daily')
        assert len(after['source_memory_ids'])<=32
        assert after['adopted_conventions'][0]['decision']['proposal']['value']=='sibling'
