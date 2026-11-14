"""An own retained method can start a private concern without a feedback seed."""
import json
from pathlib import Path
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import current
from .test_private_feedback_continuation import wording


@pytest.mark.parametrize('condition',['form','pending-restart','rest','transient','private-ask','no-method','no-retention','disabled','withdrawn','source-race'])
def test_original_method_and_actual_statement_can_offer_first_c_thought_without_feedback(tmp_path,condition):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    statement='SYNTHETIC user reports a difficult day; this is a statement, not an independently verified mood.'
    private='PRIVATE_INITIAL_CARE: I feel tentative concern and would like a calm ordinary conversation; I do not know whether the person needs comfort.'
    passing='PRIVATE_PASSING_CARE: perhaps a quieter rhythm would suit this moment; no lasting plan is necessary.'
    def meaning(request):
        own=[json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
        proposal={'approach':'CHAT' if own else 'LISTEN','detail':'BRIEF','follow_up':'NONE','basis_private_record_ids':[v['record_id'] for v in own]}
        if condition!='no-method' and not own:proposal['strategy_duration_seconds']=3600
        return {'communication_proposal':proposal}
    def inner(request):
        seen.append(request);context=json.loads(request['context_json']);manifest=context['manifest']
        methods=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='COMMUNICATION_STRATEGY']
        assert len(methods)==1 and methods[0]['choice']['approach']=='LISTEN' and methods[0]['effect_status']=='NOT_EVALUATED_NO_EFFECT_INFERRED'
        assert not any(b['kind']=='COMMUNICATION_FEEDBACK' for b in context['blocks'])
        assert any(statement in json.loads(b['data_json']).get('text','') for b in context['blocks'] if b['kind']=='MEMORY')
        proposal={'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC an own possible concern, not a mood fact or an instruction',
            'preferred_behavior':'REST' if condition=='rest' else 'REFLECT','proposed_operations':['DRAFT'] if condition in {'form','pending-restart'} else ['ASK'] if condition=='private-ask' else ['WAIT']}
        if condition in {'form','pending-restart'}:proposal['private_tendency']={'topic':'initial-care','tendency':private}
        if condition in {'transient','private-ask'}:proposal['passing_thought']=passing
        return {'interpretation':'SYNTHETIC original C considers the meaning of its own current method','subject_cognition':proposal}
    with relay(home,'VENT',meaning_builder=meaning,renderer=wording,subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            turn=app.chat(statement,topic='initial-care',privacy='PERSONAL',retain_shared_life=condition!='no-retention',message_id='initial')
            assert turn['text']=='SYNTHETIC listening method' and len(requests)==2 and not current(app)
            assert not app.runtime.store.all('experiences')
            if condition=='withdrawn':app.forget(turn['message_memory_id'])
        clock.advance(601*SECOND);config=load_config(home)
        update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_background_cognition':condition!='disabled','provider_context_tokens':32768}),expected_revision=config.revision)
        if condition=='pending-restart':
            with LifeApplication(home,clock=clock,router=router) as staging:
                staging.pause(False);staging.runtime.refresh_attention();staging.runtime._watch_sources()
                assert len(requests)==2
                assert any('communication_method_record_id' in row['template_json'] for row in staging.runtime.store.all('runtime_schedules'))
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            app.pause(False);app.runtime.refresh_attention()
            if condition=='source-race':
                factory=app.runtime.cognition.provider_factory
                def withdraw(event):
                    if getattr(event,'communication_method_record_id',None):app.forget(turn['message_memory_id'])
                    return factory(event)
                app.runtime.cognition.provider_factory=withdraw
            for _ in range(8):app.tick()
            clock.advance(2*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            measure=app.runtime.store.one('cognitive_requests',seen[0]['request_id']) if seen else None
            print(json.dumps({'measurement':'synthetic_initial_method','condition':condition,'self_http_calls':len(seen),
                'configured_input_tokens':load_config(home).provider_context_tokens,'input_bytes':measure['input_bytes'] if measure else None,
                'reserved_bytes':measure['reserved_bytes'] if measure else None,'latency_us':measure['latency_us'] if measure else None,
                'budget':seen[0]['budget'] if seen else None,'record_count':len(app.runtime.store.all('continuity_records')),
                'sqlite_family_allocated_bytes':sum(Path(str(app.runtime.store.path)+suffix).stat().st_size for suffix in ('','-wal','-shm') if Path(str(app.runtime.store.path)+suffix).exists())},sort_keys=True))
            assert len(seen)==(1 if condition in {'form','pending-restart','rest','transient','private-ask'} else 0)
            if condition in {'transient','private-ask'}:
                assert not app.runtime.store.db.execute("SELECT 1 FROM subject_intentions WHERE state='PENDING' AND kind='WAIT'").fetchone()
            formed=current(app);assert bool(formed)==(condition in {'form','pending-restart'})
            if formed:
                assert formed[0][1].content_summary==private and turn['message_memory_id'] in formed[0][1].source_memory_ids
                assert formed[0][1].epistemic_status=='OWN_TENDENCY_NOT_WORLD_FACT'
            calls=len(requests);clock.advance(3*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            assert len(requests)==calls
            assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants') and not app.runtime.store.all('world_beliefs')
            assert not app.runtime.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0 OR instr(data_json,?)>0',(private,passing)).fetchone()
            app.pause()
            if condition in {'form','pending-restart','rest','transient','private-ask'}:
                later=app.chat('SYNTHETIC a different later conversation',topic='initial-care',privacy='PERSONAL',message_id='later')
                assert later['text']==('SYNTHETIC ordinary-chat method' if condition in {'form','pending-restart'} else 'SYNTHETIC listening method')
                assert private not in requests[-1]['context_json'] and passing not in requests[-1]['context_json']
                app.forget(turn['message_memory_id']);assert not current(app)


@pytest.mark.parametrize('operation',['ASK','WAIT'])
def test_ordinary_user_clarification_keeps_original_wait_intention(tmp_path,operation):
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.cognition import AnalyticalFixturePort
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    class Ordinary:
        descriptor='synthetic-ordinary-clarification-control'
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request));value['proposed_operations']=[operation]
            return json.dumps(value)
    with LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime
        result=r.subject.cognize(SubjectInput(source_key='synthetic.ordinary-clarification',kind='INTERACTION',origin='USER',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',text='SYNTHETIC ordinary ambiguous request',
            significance='RELEVANT',observed_at_us=clock.utc_now_us()),model=Ordinary(),authority=r.authority,policy=app.policy)
        assert result.intention.kind=='WAIT' and result.judgment.stance==('ASK' if operation=='ASK' else 'DEFER')
        assert r.store.one('subject_intentions',result.intention_id)['state']=='PENDING'
        assert not r.store.all('goals') and not r.store.all('actions')


def test_initial_method_selection_is_read_only_scoped_indexed_and_rejects_replaced_method_before_model(tmp_path):
    from nana_core.contracts import CoreError
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.subject.context_fit import method_consideration
    home=tmp_path/'home';initialize(home);clock=VirtualClock();style=['LISTEN']
    config=load_config(home);update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_calls_per_day':128,'provider_calls_per_hour':128,'per_provider_calls_per_day':128}),expected_revision=config.revision)
    def meaning(request):return {'communication_proposal':{'approach':style[0],'detail':'BRIEF','follow_up':'NONE','strategy_duration_seconds':3600}}
    with relay(home,'CHAT',meaning_builder=meaning,renderer=wording,context_limit=65536) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
        app.pause();turn=app.chat('SYNTHETIC first retained source',topic='initial-care',privacy='PERSONAL',retain_shared_life=True,message_id='one')
        store=app.runtime.store;rid=store.db.execute("SELECT record_id FROM continuity_records WHERE target_id GLOB 'communication-strategy.*' AND lifecycle='ACTIVE' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
        args=dict(scope='project-work',entity_id='project-user',privacy_classes=('PERSONAL',))
        for index in range(40):
            app.chat('SYNTHETIC a transient unrelated interaction',topic='transient-'+str(index),privacy='PERSONAL',message_id='transient-'+str(index))
        # More than one header page of real methods lacks retained input. They
        # cannot displace the older, still current and consented occurrence.
        opportunities=app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=clock.utc_now_us(),quiet_window_us=SECOND)
        assert any(v.communication_method_record_id==rid for v in opportunities)
        snapshot=store.snapshot();writes=store.db.total_changes
        selected=method_consideration(store,rid,**args);assert selected['input_memory_id']==turn['message_memory_id']
        for key,value in [('scope','another-scope'),('entity_id','another-person'),('privacy_classes',('PUBLIC',))]:assert method_consideration(store,rid,**{**args,key:value}) is None
        query="SELECT record_id FROM continuity_records WHERE scope=? AND record_kind='INTENTION' AND target_id GLOB 'communication-strategy.*' AND lifecycle='ACTIVE' AND created_at_us>? ORDER BY created_at_us DESC,record_id"
        assert any('communication_method_live_lookup' in str(tuple(row)) for row in store.db.execute('EXPLAIN QUERY PLAN '+query,('project-work',clock.utc_now_us()-86400*SECOND)))
        assert store.snapshot()==snapshot and store.db.total_changes==writes
        event=SubjectInput(source_key='synthetic.initial-method-view',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=selected['memory_ids'],task_class='interaction.method.consider',communication_method_record_id=rid)
        with pytest.raises(ValueError):SubjectInput.model_validate({**event.model_dump(),'origin':'USER'})
        style[0]='EXPLAIN';app.chat('SYNTHETIC a changed situation',topic='initial-care',privacy='PERSONAL',retain_shared_life=True,message_id='two')
        assert method_consideration(store,rid,**args) is None
        snapshot=store.snapshot();writes=store.db.total_changes;calls=len(requests)
        with pytest.raises(CoreError,match='COMMUNICATION_METHOD_CONSIDERATION_UNAVAILABLE'):app.runtime.cognition.preview_private(event,app.runtime.subject)
        assert len(requests)==calls==84 and store.snapshot()==snapshot and store.db.total_changes==writes
