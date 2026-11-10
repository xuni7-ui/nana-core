"""Frozen original controlled QQ test against the exact installed bundle only.
Original fixtures copied from00898e0; external qualification, never packaged.
"""
import argparse,ast,json,socket,subprocess,sys,threading,time,sqlite3
from pathlib import Path
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
p=argparse.ArgumentParser();p.add_argument('--expected-source',required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
bundle=a.bundle.resolve();work=a.work.resolve()
if a.output.exists() or work.exists() or Path(sys.prefix).resolve()!=bundle/'.venv':raise ValueError('FRESH_INSTALLED_OWNED_QUALIFICATION_REQUIRED')
manifest=json.loads((bundle/'runtime.json').read_text())
if manifest['source_commit']!=a.expected_source:raise ValueError('SOURCE_REQUIRED')
prior=work.parent/(work.name+'-gateway-result.json')
subprocess.run([sys.executable,'-I','-B',str(Path(__file__).with_name('verify-dev.py')),'--bundle',str(bundle),'--work',str(work),'--output',str(prior),'--check-memory-notes'],check=True,timeout=90)
sys.path.insert(0,str(bundle/'src'));sys.dont_write_bytecode=True
from nana_core.contracts import CoreError,GrantSpec
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.life.platform_runtime import QQChannelBinding,QQReplyWorkflow
from nana_core.life.platform_bridge import OneBotHTTPTransport
from nana_core.life.surfaces import SurfaceBinding,SurfaceObservation
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.life.live_api.supervisor import existing_identity
report=json.loads(prior.read_text());identity,lineage,_=existing_identity(work/'life')
if report['execution']!='ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD' or identity!=report['subject_id'] or lineage!=report['lineage_binding']:raise ValueError('SAME_DEV_SUBJECT_REQUIRED')
def register_channel(home,url):
    cfg=load_config(home)
    binding=SurfaceBinding(binding_id='qq.primary',platform='qq.onebot',surface='chat.direct',adapter='qq.onebot',mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PROJECT',))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(*cfg.surface_bindings,binding),'provider_context_tokens':16384,'provider_output_tokens':2048,'provider_total_calls_limit':6,'provider_calls_per_day':6,'provider_calls_per_hour':6,'per_provider_calls_per_day':6}),expected_revision=cfg.revision)
    return QQChannelBinding(channel_id='primary',binding_id=binding.binding_id,endpoint=url,account_id='42',sender_id='43',target_id='43',enabled=True,read_authorized=True,send_authorized=True)
def clock_start(home):
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
    return max(high,time.time_ns()//1000)

@contextmanager
def counterpart():
    """Independent server retains its effect even when its HTTP ACK is lost."""
    state = {'calls': [], 'sent': [], 'lose_ack': False, 'read_peer': '43', 'incoming_sender': '43', 'incoming_kind': 'private', 'incoming_group': '77', 'account': '42', 'redirect': False}

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['calls'].append((self.path, body))
            if state['redirect']:
                self.send_response(307)
                self.send_header('Location', '/send_private_msg')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if self.path == '/get_login_info':
                data = {'user_id': state['account']}
            elif self.path in {'/send_private_msg', '/send_group_msg'}:
                state['sent'].append(body)
                if state['lose_ack']:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                data = {'message_id': 100 + len(state['sent'])}
            elif self.path == '/get_msg' and body['message_id'] == 1:
                data = {'message_id': 1, 'message_type': state['incoming_kind'], 'group_id': state['incoming_group'], 'time': 1, 'sender': {'user_id': state['incoming_sender']}, 'message': [{'type': 'text', 'data': {'text': '你好，今天只随便聊聊。'}}]}
            elif self.path == '/get_msg':
                sent = state['sent'][body['message_id'] - 101]
                data = {'message_id': body['message_id'], 'message_type': 'private', 'time': 1, 'sender': {'user_id': '42'}, 'target_id': state['read_peer'], 'message': sent['message']}
            else:
                self.send_error(404)
                return
            raw = json.dumps({'status': 'ok', 'retcode': 0, 'data': data}).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield ('http://127.0.0.1:' + str(server.server_port), state)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

def transport(endpoint, **updates):
    return OneBotHTTPTransport(endpoint, '42', authorized=True, realm='SYNTHETIC_LOOPBACK', **updates)

@contextmanager
def relay(home, kind='VENT', *, mode='normal', conversation_proposal=None, renderer=None, profile_id='fixture.provider', model_profile_id='fixture.text', remote_model_id='same-text-model', recall_query_terms=(), stream_fixture=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            request = json.loads(body['messages'][1]['content'])
            requests.append(request)
            role = request['cognitive_role']
            descriptor = request['role_input']['dialogue']
            proposal = {'interpretation': descriptor['text'], 'source_refs': request['source_context_refs'], 'uncertainty': 'LOW', 'confidence': 0.9}
            if role == 'INTERPRET':
                proposal['dialogue'] = {'kind': kind, 'confidence': 'HIGH'}
                if recall_query_terms:
                    proposal['dialogue']['recall_query_terms'] = recall_query_terms
                if conversation_proposal:
                    proposal['dialogue']['conversation_proposal'] = conversation_proposal
            else:
                proposal['draft'] = {'text': renderer(request) if renderer else 'A deliberately synthetic language response', 'claim_memory_ids': [], 'effect_status': descriptor['effect_status']}
            if mode == 'attack':
                proposal['interests'] = [{'topic': 'attack', 'motivation_source': 'CURIOSITY', 'source_memory_ids': request['source_context_refs'], 'interpretation': 'model tries to create an adopted goal'}]
            raw = json.dumps({'id': 'synthetic-dialogue', 'model': body['model'], 'usage': {'prompt_tokens': 10, 'completion_tokens': 10}, 'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(proposal)}}]}).encode()
            if body.get('stream') and stream_fixture is not None:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                content = json.dumps(proposal, ensure_ascii=False)
                split = content.index(proposal['draft']['text']) + max(8, len(proposal['draft']['text']) // 2)
                for index, part in enumerate((content[:split], content[split:])):
                    event = {'model': body['model'], 'choices': [{'index': 0, 'delta': {'content': part}, 'finish_reason': None}]}
                    self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
                    self.wfile.flush()
                    if index == 0 and stream_fixture.get('release') is not None:
                        stream_fixture['release'].wait(2)
                if stream_fixture.get('interrupt'):
                    return
                if stream_fixture.get('finished') is not None:
                    stream_fixture['finished'].set()
                event = {'model': body['model'], 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}
                self.wfile.write(('data: ' + json.dumps(event) + '\n\ndata: [DONE]\n\n').encode())
                self.wfile.flush()
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        authority = ProviderConfigurationAuthority()
        service = ProviderConfigService(home / 'test-providers.json', authority)
        service.initialize(authority)
        p = ProviderProfile(provider_profile_id=profile_id, display_name='SYNTHETIC_LOOPBACK', protocol='SYNTHETIC_LOOPBACK', locality='LOCAL_FIXTURE', base_url=f'http://127.0.0.1:{server.server_port}/v1', permitted_privacy=('PUBLIC', 'PROJECT', 'PERSONAL'))
        m = ModelProfile(model_profile_id=model_profile_id, provider_profile_id=p.provider_profile_id, remote_model_id=remote_model_id, model_version='1', operations=('COGNITION',), input_modalities=('TEXT',), output_modalities=('TEXT',), context_limit=8192, output_limit=2048)
        service.update(ProviderCommand(operation='UPSERT_PROVIDER', expected_revision=service.load().revision, provider=p), authority)
        service.update(ProviderCommand(operation='UPSERT_MODEL', expected_revision=service.load().revision, model=m), authority)
        service.update(ProviderCommand(operation='SET_CAPABILITY_ROUTE', expected_revision=service.load().revision, route=CapabilityRoute(operation='COGNITION', primary_model_profile_id=m.model_profile_id, permitted_privacy=('PUBLIC', 'PROJECT', 'PERSONAL'))), authority)
        factory = RuntimeProviderFactory(ProviderRegistry(), None, RoutingPolicy(allow_synthetic_loopback=True))
        yield (CapabilityRouter(service, factory), requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def equip(app, channel, url, *, with_grant=True):
    flow = QQReplyWorkflow(app, channel, transport(url))
    GovernanceController(app.runtime.store, app.runtime.authority).initialize(app.runtime.authority)
    flow.realization.kernel.set_budgets({'external_requests': 16, 'write_attempts': 4, 'cost_micro_units': 16}, app.runtime.authority)
    if with_grant:
        flow.realization.kernel.grant(GrantSpec(capabilities=('world.contact', 'world.action.verify'), resources=(flow.resource,), not_before_us=app.runtime.clock.utc_now_us(), expires_at_us=app.runtime.clock.utc_now_us() + 100000000), app.runtime.authority)
    return flow

def qualify(work):
    import json
    from nana_core.life.memory_notes import save
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.lived_language import LanguageService, LanguageSample, MemoryUseFeedback

    def render(request):
        blocks = json.loads(request['context_json'])['blocks']
        guidance = next((json.loads(b['data_json'])['memory_use_guidance'] for b in blocks if b['kind'] == 'MEMORY_USE_GUIDANCE'), ())
        return 'SYNTHETIC ' + (guidance[0]['requested_mode'] if guidance else 'BASELINE')
    with counterpart() as (url, platform):
        home = work / 'life'
        channel = register_channel(home, url)
        clock = VirtualClock(clock_start(home))
        with relay(home, 'CHAT', recall_query_terms=('ORCHID',), renderer=render) as (router, requests):
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = equip(app, channel, url)
                mid = save(app, text='SYNTHETIC ORCHID Friday', privacy='PROJECT', request_id='recipient-note')['memory_id']
                fact = MemoryService(app.runtime.store).read(mid)
                turn = app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id, event_id='qq:1', thread_id='qq.private.43', text='SYNTHETIC ORCHID first question', privacy_class='PROJECT', origin='SYNTHETIC_LOOPBACK', retain_shared_life=True), reply_target=flow.target)
                assert turn['text'] == 'SYNTHETIC BASELINE'
                assert flow._reply(turn, '1')['delivery'] == 'SUCCEEDED'
                service = LanguageService(app.runtime.store, app.runtime.authority)
                sample = LanguageSample(sample_id='recipient-review', review_target=turn['exchange_record_id'], mode='CASUAL', context='SYNTHETIC explicit fixture review', candidate_response=turn['text'], human_judgment='PARTIAL', provenance='USER_PROVIDED_REVIEW', observed_at_us=clock.utc_now_us(), memory_use=MemoryUseFeedback(memory_id=mid, mode='NATURAL_REFERENCE'))
                review_id = service.record(sample, scope='project-work', entity_id='project-user', privacy='PROJECT', authority=app.runtime.authority, exchange_record_id=turn['exchange_record_id'])
                io = len(platform['calls'])
                identity = app.runtime.identity_id
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                assert app.runtime.identity_id == identity
                for sequence, thread, expected in ((2, 'qq.private.43', 'NATURAL_REFERENCE'), (3, 'qq.private.44', 'BASELINE')):
                    later = app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id, event_id='qq:' + str(sequence), thread_id=thread, text='SYNTHETIC ORCHID later question', privacy_class='PROJECT', origin='SYNTHETIC_LOOPBACK', retain_shared_life=True))
                    assert later['text'] == 'SYNTHETIC ' + expected, later
                    assert mid in requests[-1]['source_context_refs']
                    assert requests[-1]['role_input']['dialogue']['recipient_context']['conversation_id'] == thread
                assert len(requests) == 6 and len(platform['calls']) == io and (len(platform['sent']) == 1)
                assert MemoryService(app.runtime.store).read(mid) == fact
                app.forget(mid)
                assert not LanguageService(app.runtime.store, app.runtime.authority).records.current_support(review_id)
    return {"subject_id":identity,"local_fixture_calls":len(requests),"platform_fixture_sends":len(platform["sent"]),"actual_independent_readback":True,"same_subject_restart":True,"recipient_scoped_later_render":True,"source_withdrawal":True,"human_read_proven":False,"real_provider_calls":0,"real_account_sends":0}

result=qualify(work)
assert result['subject_id']==report['subject_id']
result.update(execution='ACTUAL_INSTALLED_OWNED_QQ_LOOPBACK_NOT_REAL_ACCOUNT_OR_HUMAN',source_commit=manifest['source_commit'],lineage_binding=lineage,no_repository_pythonpath=True,production_changed=False,private_data_used=False)
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
