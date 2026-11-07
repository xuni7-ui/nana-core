"""Sourced retained speech selection, not real-model or cross-day qualification."""
from nana_core.continuity.person_self import retain_input,retain_exchange,project,compact,rows
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.life.application import LifeApplication


def speech(app,key,text,privacy='PROJECT'):
    r=app.runtime
    mid=retain_input(r.store,entity_id='project-user',scope='project-work',text=text,privacy=privacy,message_id=key)
    cycle=r.subject.run(SubjectInput(domain='LOCAL_INTERACTION',source_key='local.soft-window.'+key,
        kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',privacy_class=privacy,
        observed_at_us=r.clock.utc_now_us(),text='Local input reviewed meaning: CHAT',source_memory_ids=(mid,),
        interaction_signal=InteractionSignal(kind='CHAT',topic_key='daily',basis='EXPLICIT')))
    retain_exchange(r.store,entity_id='project-user',scope='project-work',topic='daily',user_memory_id=mid,
        text='SYNTHETIC reported response, not a verified world fact',cycle=cycle)
    if cycle.intention_id:
        old=r.store.one('subject_intentions',cycle.intention_id)
        r.subject.transition_intention(cycle.intention_id,expected_revision=old['revision'],state='DROPPED')
    return mid


def test_relevant_three_day_old_speech_survives_restart_recent_chatter_and_budget_excerpt(app):
    text='SYNTHETIC background. '*24+'虹光约定的原文是周五下午。'
    mid=speech(app,'old',text);identity=app.runtime.identity_id;home=app.home;clock=app.clock
    app.close();clock.advance(72*3_600_000_000)
    with LifeApplication(home,clock=clock) as restored:
        restored.pause()
        for n in range(10):speech(restored,'new.'+str(n),'SYNTHETIC recent unrelated weather '+str(n))
        plain=project(restored.runtime.store,entity_id='project-user',scope='project-work',privacy=('PROJECT',),topic='daily')
        assert mid not in plain['preferred_exchange_memory_ids']
        view=project(restored.runtime.store,entity_id='project-user',scope='project-work',privacy=('PROJECT',),topic='daily',query_terms=('虹光约定',))
        value=compact(view,query_terms=('虹光约定',))
        assert restored.runtime.identity_id==identity and mid in view['source_memory_ids']
        item=next(row for row in value['recent_exchanges'] if row['user_memory_id']==mid)
        assert '周五下午' in item['user_statement'] and item['epistemic_status']=='REPORTED_SPEECH_NOT_WORLD_TRUTH'
        span=item['excerpt_ranges']['user_statement'];assert span['start']>0
        assert text[span['start']:span['end']]==item['user_statement'] and len(item['user_statement'])<=384
        assert view['recent_selection']['window_is_hard_limit'] is False
        times=[row['as_of_us'] for row in view['recent_exchanges']];assert times==sorted(times)
        restored.forget(mid)
        after=project(restored.runtime.store,entity_id='project-user',scope='project-work',privacy=('PROJECT',),topic='daily',query_terms=('虹光约定',))
        assert mid not in after['source_memory_ids']
        assert all('虹光约定' not in row['user_statement'] for row in compact(after,query_terms=('虹光约定',))['recent_exchanges'])


def test_private_burst_cannot_push_public_speech_out_of_header_limit(app):
    public=speech(app,'public','SYNTHETIC public source')
    for n in range(12):speech(app,'private.'+str(n),'SYNTHETIC PRIVATE_BURST_NOT_REAL_PRIVATE_DATA '+str(n),'PERSONAL')
    result=rows(app.runtime.store,'CONVERSATION_EXCHANGE','project-work',('PROJECT',),limit=1,target='daily')
    assert len(result)==1 and result[0]['payload']['user_memory_id']==public
    assert 'PRIVATE_BURST' not in str(result)


def test_older_relevant_speech_reaches_actual_render_and_withdrawal_rechecks(app):
    import json
    from tests.independent_life.test_dialogue import relay
    old=speech(app,'render-old','SYNTHETIC padding. '*32+'虹光约定是周五下午，在北门集合。')
    home=app.home;clock=app.clock;identity=app.runtime.identity_id
    app.close();clock.advance(72*3_600_000_000)
    with relay(home,'CHAT',recall_query_terms=('虹光约定',)) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause()
            for n in range(10):speech(current,'render-new.'+str(n),'SYNTHETIC unrelated recent speech '+str(n))
            reply=current.chat('虹光约定是什么时候？',message_id='query-old',topic='daily')
            assert reply['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
            assert current.runtime.identity_id==identity
            render=requests[-1];context=json.loads(render['context_json'])
            blocks=[b for b in context['blocks'] if b['kind']=='PERSON_SELF']
            assert blocks and any('周五下午' in b['data_json'] and old in b['source_memory_ids'] for b in blocks)
            current.forget(old)
            current.chat('虹光约定是什么时候？',message_id='query-withdrawn',topic='daily')
            assert len(requests)==4
            assert '周五下午' not in requests[-1]['context_json']
            assert not current.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'虹光约定是什么时候？')>0").fetchone()
