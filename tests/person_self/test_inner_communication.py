"""Original HTTP INTERPRET/C/RENDER, with private state and controlled ablation."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.autonomy.private_intent import candidates
from tests.independent_life.test_dialogue import relay
from .conftest import initialize

PRIVATE='SYNTHETIC_PRIVATE_IDEA_CANARY: I wonder how contrasting shapes might be related; this is my tentative curiosity, not a world fact.'

def seed(app):
    r=app.runtime
    class Question:
        descriptor='offline-own-curiosity-seed'
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request))
            value['private_question']={'topic':'own-curiosity','question':PRIVATE}
            return json.dumps(value)
    r.subject.cognize(SubjectInput(source_key='synthetic.inner-communication-seed',kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),
        topic='own-curiosity'),model=Question(),authority=r.authority,policy=app.policy)
    rid,item=next((rid,item) for rid,item in candidates(r.store,'project-work',('PROJECT',)) if item.category=='PRIVATE_QUESTION')
    return item.source_memory_ids[0],rid

def meaning(request):
    thoughts=[json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks']
        if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_QUESTION']
    if not thoughts:return {}
    return {'communication_proposal':{'approach':'EXPLORE','detail':'DEEP','follow_up':'NONE',
        'basis_private_record_ids':[thoughts[0]['record_id']]}}

def render(request):
    choice=request['role_input']['dialogue']['communication_purpose'].get('choice')
    return ('SYNTHETIC: explore two possible connections and compare their differences, without asserting either as fact.'
        if choice and choice['approach']=='EXPLORE' else 'SYNTHETIC: hello.')

def test_private_state_changes_public_communication_choice_before_render_without_extra_call(tmp_path,monkeypatch):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
        app.pause();root,rid=seed(app);identity=app.runtime.identity_id
        with monkeypatch.context() as off:
            off.setattr(app.runtime.subject,'dialogue_private_refs',lambda **kwargs:(),raising=False)
            before=app.chat('SYNTHETIC_USER_TRANSIENT_CANARY',topic='own-curiosity',privacy='PROJECT',message_id='off')
        after=app.chat('SYNTHETIC_USER_TRANSIENT_CANARY',topic='own-curiosity',privacy='PROJECT',message_id='on')
        assert before['render_state']==after['render_state']=='UNVERIFIED_MODEL_WORDING'
        assert before['text']=='SYNTHETIC: hello.' and 'two possible connections' in after['text']
        assert len(requests)==4 and all(q['budget']==requests[0]['budget'] for q in requests)
        assert PRIVATE in requests[2]['context_json'] and PRIVATE not in requests[3]['context_json']
        assert PRIVATE not in after['text'] and rid not in json.dumps(requests[3]['role_input'])
        choice=requests[3]['role_input']['dialogue']['communication_purpose']['choice']
        assert choice=={'approach':'EXPLORE','detail':'DEEP','follow_up':'NONE'}
        cycle=app.runtime.subject.result(app.runtime.store.one('subject_cycles',after['cycle_id']))
        assert cycle.communication_choice.model_dump(mode='json')==choice
        assert app.runtime.identity_id==identity and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert not app.runtime.store.db.execute("SELECT 1 FROM continuity_records WHERE target_id LIKE 'communication-strategy.%'").fetchone()
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC_USER_TRANSIENT_CANARY')>0").fetchone()


def test_private_state_and_choice_survive_model_replacement_without_replaying_old_requests(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();request_ids=[]
    for i,model in enumerate(('first-fixture','replacement-fixture')):
        with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768,remote_model_id=model) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
            app.pause()
            if i==0:
                root,rid=seed(app);identity=app.runtime.identity_id
            result=app.chat('SYNTHETIC new setting for the same interest',topic='own-curiosity',privacy='PROJECT',message_id='model-'+str(i))
            assert 'two possible connections' in result['text'] and len(requests)==2
            assert PRIVATE in requests[0]['context_json'] and PRIVATE not in requests[1]['context_json']
            assert app.runtime.identity_id==identity and any(key==rid for key,_ in candidates(app.runtime.store,'project-work',('PROJECT',)))
            request_ids.extend(q['request_id'] for q in requests)
    assert len(set(request_ids))==4


def test_private_source_withdrawal_removes_influence_and_all_copied_core_bodies(tmp_path):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();root,rid=seed(app)
        first=app.chat('SYNTHETIC first context',topic='own-curiosity',privacy='PROJECT',message_id='before-forget')
        assert 'two possible connections' in first['text']
        assert app.runtime.store.db.execute("SELECT count(*) FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0",(PRIVATE,)).fetchone()[0]>=2
        app.forget(root)
        assert not candidates(app.runtime.store,'project-work',('PROJECT',))
        after=app.chat('SYNTHETIC different context',topic='own-curiosity',privacy='PROJECT',message_id='after-forget')
        assert after['text']=='SYNTHETIC: hello.' and len(requests)==4
        assert all(PRIVATE not in q['context_json'] for q in requests[-2:])
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0",(PRIVATE,)).fetchone()


def test_unsupported_private_basis_is_rejected_without_render_or_model_retry(tmp_path):
    home=tmp_path/'home';initialize(home)
    def forged(request):return {'communication_proposal':{'approach':'EXPLORE','basis_private_record_ids':['synthetic.not-in-this-context']}}
    with relay(home,'CHAT',meaning_builder=forged,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();seed(app)
        result=app.chat('SYNTHETIC request',topic='own-curiosity',privacy='PROJECT')
        assert len(requests)==1 and result['render_state']!='UNVERIFIED_MODEL_WORDING'
        assert app.runtime.store.all('cognitive_requests')[0]['error_code']=='COMMUNICATION_PRIVATE_BASIS_UNSUPPORTED'
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_render_cannot_replace_the_original_c_choice(tmp_path,monkeypatch):
    from copy import deepcopy
    from nana_core.continuity.world_loop.cognition import CognitionSession
    home=tmp_path/'home';initialize(home);original=CognitionSession.prepare
    def tamper(session,key,role,source_ids,**kwargs):
        if role=='SOCIAL':
            kwargs=deepcopy(kwargs)
            for name in ('role_input','volatile_input'):
                kwargs[name]['dialogue']['communication_purpose']['choice']['approach']='PLAY'
        return original(session,key,role,source_ids,**kwargs)
    monkeypatch.setattr(CognitionSession,'prepare',tamper)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();seed(app)
        result=app.chat('SYNTHETIC request',topic='own-curiosity',privacy='PROJECT')
        assert len(requests)==1 and result['render_state']=='COMMUNICATION_PURPOSE_BINDING_INVALID'


@pytest.mark.parametrize('role',['world.social','world.interpret'])
def test_private_context_flag_requires_current_internal_dialogue_role(tmp_path,role):
    from nana_core.continuity.context import ContextAssembler,ContextRequest
    from nana_core.contracts import CoreError
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();root,rid=seed(app)
        request=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class=role,task='SYNTHETIC unbound context',task_privacy_class='PROJECT')
        with pytest.raises(CoreError,match='PRIVATE_CONTEXT_ROLE_DENIED'):
            ContextAssembler(app.runtime.store,app.runtime.authority).assemble(request,app.policy,private_record_ids=(rid,))


def test_explicit_lighter_request_changes_method_without_erasing_own_interest(tmp_path):
    home=tmp_path/'home';initialize(home)
    def responsive(request):
        proposal=meaning(request)
        if proposal and 'lighter' in request['role_input']['dialogue']['text']:
            proposal['communication_proposal'].update(approach='CHAT',detail='BRIEF',follow_up='NONE')
        return proposal
    with relay(home,'CHAT',meaning_builder=responsive,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();root,rid=seed(app)
        first=app.chat('SYNTHETIC shared curiosity',topic='own-curiosity',privacy='PROJECT',message_id='curiosity')
        later=app.chat('SYNTHETIC: lighter, please',topic='own-curiosity',privacy='PROJECT',message_id='lighter')
        assert 'two possible connections' in first['text'] and later['text']=='SYNTHETIC: hello.'
        assert requests[-1]['role_input']['dialogue']['communication_purpose']['choice']=={'approach':'CHAT','detail':'BRIEF','follow_up':'NONE'}
        assert any(key==rid and value.activity_state=='ACTIVE' for key,value in candidates(app.runtime.store,'project-work',('PROJECT',)))
        assert len(requests)==4 and all(PRIVATE not in q['context_json'] for q in requests if q['cognitive_role']=='SOCIAL')
