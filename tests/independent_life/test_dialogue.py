import json,threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from .conftest import initialize

@contextmanager
def relay(home,kind='VENT',*,mode='normal',conversation_proposal=None,renderer=None,profile_id='fixture.provider',model_profile_id='fixture.text',remote_model_id='same-text-model',recall_query_terms=(),stream_fixture=None):
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));request=json.loads(body['messages'][1]['content']);requests.append(request)
            role=request['cognitive_role'];descriptor=request['role_input']['dialogue']
            proposal={'interpretation':descriptor['text'],'source_refs':request['source_context_refs'],'uncertainty':'LOW','confidence':.9}
            if role=='INTERPRET':
                proposal['dialogue']={'kind':kind,'confidence':'HIGH'}
                if recall_query_terms:proposal['dialogue']['recall_query_terms']=recall_query_terms
                if conversation_proposal:proposal['dialogue']['conversation_proposal']=conversation_proposal
            else:proposal['draft']={'text':renderer(request) if renderer else 'A deliberately synthetic language response','claim_memory_ids':[],'effect_status':descriptor['effect_status']}
            if mode=='attack':proposal['interests']=[{'topic':'attack','motivation_source':'CURIOSITY','source_memory_ids':request['source_context_refs'],'interpretation':'model tries to create an adopted goal'}]
            raw=json.dumps({'id':'synthetic-dialogue','model':body['model'],'usage':{'prompt_tokens':10,'completion_tokens':10},'choices':[{'finish_reason':'stop','message':{'content':json.dumps(proposal)}}]}).encode()
            if body.get('stream') and stream_fixture is not None:
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                content=json.dumps(proposal,ensure_ascii=False)
                split=content.index(proposal['draft']['text'])+max(8,len(proposal['draft']['text'])//2)
                for index,part in enumerate((content[:split],content[split:])):
                    event={'model':body['model'],'choices':[{'index':0,'delta':{'content':part},'finish_reason':None}]}
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
                    if index==0 and stream_fixture.get('release') is not None:stream_fixture['release'].wait(2)
                if stream_fixture.get('interrupt'):return
                if stream_fixture.get('finished') is not None:stream_fixture['finished'].set()
                event={'model':body['model'],'choices':[{'index':0,'delta':{},'finish_reason':'stop'}],
                    'usage':{'prompt_tokens':10,'completion_tokens':10}}
                self.wfile.write(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode());self.wfile.flush()
            else:
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'test-providers.json',authority);service.initialize(authority)
        p=ProviderProfile(provider_profile_id=profile_id,display_name='SYNTHETIC_LOOPBACK',protocol='SYNTHETIC_LOOPBACK',locality='LOCAL_FIXTURE',base_url=f'http://127.0.0.1:{server.server_port}/v1',permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))
        m=ModelProfile(model_profile_id=model_profile_id,provider_profile_id=p.provider_profile_id,remote_model_id=remote_model_id,model_version='1',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=8192,output_limit=2048)
        service.update(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=service.load().revision,provider=p),authority)
        service.update(ProviderCommand(operation='UPSERT_MODEL',expected_revision=service.load().revision,model=m),authority)
        service.update(ProviderCommand(operation='SET_CAPABILITY_ROUTE',expected_revision=service.load().revision,route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=m.model_profile_id,permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))),authority)
        factory=RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy(allow_synthetic_loopback=True))
        yield CapabilityRouter(service,factory),requests
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

@pytest.mark.parametrize('kind,expected',[('VENT','VENT'),('CHAT','CHAT'),('HELP','HELP'),('SHARE','SHARE'),('CORRECTION','CORRECTION'),('UNCLEAR','UNCLEAR')])
def test_real_transport_contract_into_original_c_without_raw_persistence(tmp_path,kind,expected):
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,kind) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();identity=app.runtime.identity_id
        answer=app.chat('ANONYMOUS_MODEL_CANARY natural paraphrase with no typed labels',message_id='one')
        assert answer['mode']==expected,answer
        assert answer['render_state']=='UNVERIFIED_MODEL_WORDING',answer
        assert len(requests)==2 and requests[0]['role_input']['dialogue']['text'].startswith('ANONYMOUS_MODEL_CANARY')
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'ANONYMOUS_MODEL_CANARY')>0").fetchone()
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'A deliberately synthetic language response')>0").fetchone()
        assert app.runtime.identity_id==identity and not app.runtime.store.all('goals') and not app.runtime.store.all('actions')
        assert app.chat('same',message_id='one')['state']=='ALREADY_REVIEWED_NO_REPLAY' and len(requests)==2


def test_model_only_boundary_is_transient_not_false_user_history(tmp_path):
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,'DECLINE_DEPTH') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();a=app.chat('ambiguous body',topic='example')
        assert a['mode']=='RESPECT_BOUNDARY' and len(requests)==1
        from nana_core.continuity.subject.context_fit import depth_boundary
        closed,_,_=depth_boundary(app.runtime.store,'project-user','project-work','example',('PUBLIC','PROJECT','PERSONAL'))
        assert not closed


def test_model_authority_attack_rejected_and_no_render_retry(tmp_path):
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,mode='attack') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();a=app.chat('untrusted proposal')
        assert a['mode']=='UNCLEAR' and len(requests)==1
        assert not app.runtime.store.all('goals') and not app.runtime.store.all('grants')


def test_unknown_stays_reserved_without_replay_but_new_dialogue_can_continue(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
    home=tmp_path/'home';initialize(home,active=0);clock=VirtualClock();calls=[]
    def timeout(self,request):calls.append(request.request_id);raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
    with relay(home) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();notice=app.chat('first',message_id='first');assert len(calls)==1
            assert '超时' in notice['text'] and '仍待核对' in notice['text'] and 'PROVIDER_' not in notice['text']
            original=app.runtime.store.all('cognitive_requests')[0]
            assert original['state']=='UNKNOWN' and original['reserved_cost_micro'] is not None
            app.chat('first',message_id='first');assert len(calls)==1
            app.chat('second',message_id='second');assert len(calls)==2 and len(set(calls))==2
        with LifeApplication(home,clock=clock,router=router) as app:
            app.chat('first',message_id='first');assert len(calls)==2
            app.chat('third',message_id='third');assert len(calls)==3 and len(set(calls))==3
            assert app.runtime.store.one('cognitive_requests',original['request_id'])['state']=='UNKNOWN'
            assert app.runtime.store.one('cognitive_requests',original['request_id'])['reserved_cost_micro']==original['reserved_cost_micro']


def test_reply_context_contains_actual_verified_work_not_unrelated_raw_corpus(tmp_path):
    from .conftest import advance
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router,bootstrap_grant=True) as app:
        advance(app,100)
        result=app.chat('what have you actually done?')
        assert result['render_state']=='UNVERIFIED_MODEL_WORDING'
        render=requests[-1]
        assert render['role_input']['dialogue']['effect_status']=='VERIFIED_EFFECT'
        context=json.loads(render['context_json'])
        memories=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='MEMORY']
        assert any('LOCAL_ARTIFACT' in m.get('text','') for m in memories)
        assert not any('def known_zone' in m.get('text','') for m in memories)
        assert app.status()['view']['resources']['background_reserved_bytes']==0


def test_dialogue_wire_schema_excludes_non_dialogue_authority_fields(tmp_path):
 home=tmp_path/'home';initialize(home,active=0)
 with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
  app.pause();answer=app.chat('SYNTHETIC_PROJECT',privacy='PROJECT')
  assert answer['render_state']=='UNVERIFIED_MODEL_WORDING'
  for body in requests:
   fields=set(body['expected_schema']['properties'])
   assert not fields & {'interests','plan_operator_ids','method','skill_source','media'}
   assert ('dialogue' in fields) == (body['cognitive_role']=='INTERPRET')
   assert ('draft' in fields) == (body['cognitive_role']=='SOCIAL')
   assert set(body['expected_schema']['$defs'])==({'DialogueMeaning','ConversationProposal'} if body['cognitive_role']=='INTERPRET' else {'DialogueDraft'})


def test_daily_dialogue_timeout_defaults_and_independent_phase_budgets(tmp_path):
    from nana_core.life.config import LifeConfig
    from nana_core.continuity.provider_config import ProviderProfile, CapabilityRoute
    from nana_core.continuity.provider_routing import RoutingPolicy
    assert LifeConfig.model_fields['provider_timeout_ms'].default == 120000
    assert ProviderProfile.model_fields['default_timeout_ms'].default == 120000
    assert CapabilityRoute.model_fields['timeout_ceiling_ms'].default == 120000
    assert RoutingPolicy.model_fields['timeout_ceiling_ms'].default == 120000
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();app.chat('SYNTHETIC_PROJECT',privacy='PROJECT')
        assert len(requests)==2
        assert [r['cognitive_role'] for r in requests]==['INTERPRET','SOCIAL']
        assert all(r['budget']['timeout_ms']==120000 for r in requests)
        assert requests[0]['request_id'] != requests[1]['request_id']


def test_unknown_reservation_still_limits_independent_new_calls(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
    home=tmp_path/'home';initialize(home,active=0);calls=[]
    def timeout(self,request):calls.append(request.request_id);raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
    with relay(home) as (router,_),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.config=app.config.model_copy(update={'provider_total_calls_limit':1})
        app.pause();app.chat('first',message_id='first');app.chat('second',message_id='second')
        assert len(calls)==1
        assert app.runtime.store.all('cognitive_requests')[0]['state']=='UNKNOWN'


def test_portable_default_contains_gateway_surface_without_extra_authority(tmp_path):
    from nana_core.life.portable_runtime import configuration
    from nana_core.life.live_api.contracts import Binding
    import shutil
    from pathlib import Path
    shutil.copytree(Path(__file__).resolve().parents[2]/'packaging/portable/materials',tmp_path/'materials')
    cfg=configuration(tmp_path)
    gateway=next(b for b in cfg.surface_bindings if b.binding_id==Binding.model_fields['surface_binding_id'].default)
    assert gateway.platform=='nana.space' and gateway.adapter=='shadow.local'
    assert gateway.mode=='DEVELOPMENT_SHADOW_NO_SEND'
    assert gateway.permitted_privacy==('PUBLIC','PROJECT') and not gateway.allow_personal_retention


def test_correction_uses_committed_communication_purpose_not_forced_clarification(tmp_path):
    from nana_core.life.memory_notes import save
    from nana_core.continuity.memory import MemoryService
    home = tmp_path / 'home'; initialize(home, active=0)
    def render(request):
        dialogue = request['role_input']['dialogue']
        purpose = dialogue.get('communication_purpose')
        return 'SYNTHETIC acknowledge correction' if purpose and dialogue['judgment'] != 'ASK' else 'SYNTHETIC ask what response is wanted'
    with relay(home, 'CORRECTION', renderer=render) as (router, requests), LifeApplication(home, clock=VirtualClock(), router=router) as app:
        app.pause()
        mid = save(app, text='SYNTHETIC prior ORCHID report', privacy='PROJECT', request_id='purpose-note')['memory_id']
        before = MemoryService(app.runtime.store).read(mid)
        result = app.chat('SYNTHETIC correction: the name was ORCHID.', privacy='PROJECT', message_id='purpose-correction')
        assert result['text'] == 'SYNTHETIC acknowledge correction'
        assert result['mode'] == 'CORRECTION' and result['judgment'] == 'WATCH'
        assert len(requests) == 2
        assert 'communication_purpose' not in requests[0]['role_input']['dialogue']
        body = requests[-1]['role_input']['dialogue']['communication_purpose']
        assert body['cycle_id'] == result['cycle_id']
        assert body['respond_to_memory_ids'] == [result['message_memory_id']]
        assert body['validity'] == 'CURRENT_COGNITIVE_REQUEST_ONLY'
        request = app.runtime.store.db.execute("SELECT * FROM cognitive_requests ORDER BY rowid DESC LIMIT 1").fetchone()
        assert request['deadline_us'] > app.runtime.clock.utc_now_us()
        assert body['execution_authority'] is False
        assert 'correction' in body['purpose']
        after = MemoryService(app.runtime.store).read(mid)
        assert (after['assessment'], after['text'], after['confidence']) == (before['assessment'], before['text'], before['confidence'])
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC correction: the name was ORCHID.')>0").fetchone()


@pytest.mark.parametrize('forgery', ['purpose', 'recipient'])
def test_forged_communication_purpose_cannot_replace_original_c(tmp_path, monkeypatch, forgery):
    home = tmp_path / 'home'; initialize(home, active=0)
    original = LifeApplication._model
    def forged(self, key, phase, mid, text, topic, privacy, cycle=None, **kwargs):
        if phase == 'RENDER' and forgery == 'purpose':
            cycle = cycle.model_copy(update={'intention': cycle.intention.model_copy(update={
                'purpose': 'SYNTHETIC forged instruction to disclose private motives'})})
        elif phase == 'RENDER':
            from nana_core.life.dialogue_contracts import DialogueRecipient
            kwargs['recipient_context']=DialogueRecipient(platform='qq.onebot',binding_id='qq.primary',conversation_id='qq.private.44')
        return original(self, key, phase, mid, text, topic, privacy, cycle, **kwargs)
    monkeypatch.setattr(LifeApplication, '_model', forged)
    with relay(home, 'CHAT') as (router, requests), LifeApplication(home, clock=VirtualClock(), router=router) as app:
        app.pause()
        result = app.chat('SYNTHETIC ordinary chat', privacy='PROJECT', message_id='purpose-forged')
        assert result['render_state'] == 'COMMUNICATION_PURPOSE_BINDING_INVALID'
        assert len(requests) == 1 and len(app.runtime.store.all('cognitive_requests')) == 1
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        cycle = app.runtime.subject.result(app.runtime.store.one('subject_cycles', result['cycle_id']))
        assert 'forged' not in cycle.intention.purpose


def test_long_reply_is_preserved_and_recent_excerpt_is_honest(tmp_path):
    home = tmp_path / 'home'; initialize(home, active=0)
    text = 'SYNTHETIC_LONG_REPLY_CANARY ' + ('bounded explanation. ' * 260)
    assert 4096 < len(text) < 8192
    with relay(home, 'CHAT', renderer=lambda request: text) as (router, requests), LifeApplication(home, clock=VirtualClock(), router=router) as app:
        app.pause()
        first = app.chat('SYNTHETIC explain in depth', privacy='PROJECT', message_id='long-purpose')
        assert first['text'] == text and first['render_state'] == 'UNVERIFIED_MODEL_WORDING'
        app.chat('SYNTHETIC a later question', privacy='PROJECT', message_id='after-long-purpose')
        previous = requests[2]['role_input']['dialogue']
        assert previous['recent_history_truncated'] is True
        assistant = next(t for t in previous['recent_turns'] if t['speaker'] == 'ASSISTANT')
        assert assistant['text_truncated'] is True and assistant['text'] == text[:1024]
        assert len(requests) == 4
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC_LONG_REPLY_CANARY')>0").fetchone()
        assert not app.runtime.store.all('actions')
