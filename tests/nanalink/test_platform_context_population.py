"""Retained platform evidence competes within its source family before limits."""
import json

from nana_core.continuity.context import ContextAssembler, ContextPolicy, ContextRequest
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.life.config import load_config, update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.nanalink.bilibili_dynamic import normalize_dynamic
from nana_core.nanalink.contracts import Account
from nana_core.nanalink.private_source import PrivateDynamicBridge
from nana_core.presence.authority import VirtualClock
from tests.person_self.conftest import initialize

NAMESPACE = 'recorded.platform.bilibili.dynamic'


def prepare(home):
    initialize(home)
    cfg = load_config(home)
    binding = SurfaceBinding(binding_id='bili.private', platform='bilibili.account',
        adapter='bilibili.account', surface='chat.direct', mode='PLATFORM_ADAPTER_NO_SEND',
        permitted_privacy=('PERSONAL',), allow_personal_retention=True,
        personal_retention_consent_ref='consent.fixture')
    channel = BilibiliChannelBinding(channel_id='bili', binding_id=binding.binding_id,
        account_id=42, target_id=43, sender_id=43, cookie_ref='test.cookie', csrf_ref='test.csrf',
        enabled=True, read_authorized=True, private_read_authorized=True)
    update_config(home, cfg.model_copy(update={'revision':cfg.revision+1,
        'surface_bindings':(binding,), 'bilibili_channels':(channel,)}), expected_revision=cfg.revision)


def select(app, *, privacy='PERSONAL'):
    request = ContextRequest(entity_id='project-user', scopes=('project-work',),
        task_class='world.social', task='SYNTHETIC ORCHID follow-up',
        query_terms=('ORCHID',), task_privacy_class=privacy,
        max_input_tokens=16384, output_reserve_tokens=2048)
    policy = ContextPolicy(policy_id='synthetic.platform.population', allowed_scopes=('project-work',),
        readable_privacy=('PUBLIC','PROJECT','PERSONAL'))
    assembler = ContextAssembler(app.runtime.store, app.runtime.authority)
    result = assembler.assemble(request, policy, pinned_only=True, conversation_topic='orchid')
    assembler.validate(result, request, policy)
    assert result.manifest.input_tokens <= result.manifest.input_limit
    return result


def refs(package):
    return {mid for block in package.blocks for mid in block.source_memory_ids}


def populate(app, clock):
    account=Account(platform='bilibili', adapter_id='bilibili.account', account_id='42')
    row={'id_str':'123','modules':{'module_author':{'mid':43,'pub_ts':1},
         'module_dynamic':{'desc':{'text':'SYNTHETIC ORCHID retained observation'}}}}
    event=normalize_dynamic(account,row,now_us=clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK')
    source=PrivateDynamicBridge(app,'bili').receive(event)['memory_id']
    memory=MemoryService(app.runtime.store)
    # These are valid, more important observations, but not the requested
    # platform family. Increasing a global window would mask the defect.
    for i in range(65):
        text=f'SYNTHETIC ORCHID other observation {i}'
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.other',
            source_reference=str(i),source_kind='DIRECT_OBSERVATION'), text=text,
            privacy_class='PERSONAL', event_time_us=clock.utc_now_us(), observed_time_us=clock.utc_now_us()))
        memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,
            epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,importance=1.0))
    return source, event


def test_private_platform_context_survives_unrelated_population_restart_and_withdrawal(tmp_path):
    home=tmp_path/'home';prepare(home);clock=VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        app.pause();identity=app.runtime.identity_id
        source,event=populate(app,clock);memory=MemoryService(app.runtime.store)
        eligible=memory.query(entity_ids=('project-user',),scopes=('project-work',),
                              privacy_classes=('PERSONAL',),query_terms=('ORCHID',),limit=64)
        assert source not in {row['memory_id'] for row in eligible}
        result=select(app)
        assert source in refs(result)
        query=dict(entity_ids=('project-user',),scopes=('project-work',),privacy_classes=('PERSONAL',),limit=1)
        assert [r['memory_id'] for r in memory.query(**query,source_namespaces=(NAMESPACE,))]==[source]
        assert not memory.query(**query,source_namespaces=(NAMESPACE+'%',))
        assert not memory.query(**{**query,'privacy_classes':('PROJECT',)},source_namespaces=(NAMESPACE,))
        assert not memory.query(**{**query,'scopes':('different-scope',)},source_namespaces=(NAMESPACE,))
        assert 'PRIVATE_PLATFORM_OBSERVATION_NOT_USER_INSTRUCTION' in result.model_dump_json()
        assert len([b for b in result.blocks if b.kind=='MEMORY']) <= 4
    with LifeApplication(home, clock=clock) as app:
        app.pause();assert app.runtime.identity_id==identity
        assert source in refs(select(app))
        assert source not in refs(select(app,privacy='PROJECT'))
        assert PrivateDynamicBridge(app,'bili').receive(event)['memory_id']==source
        assert app.runtime.store.db.execute("SELECT count(*) FROM continuity_evidence WHERE source_namespace=?",(NAMESPACE,)).fetchone()[0]==1
        app.forget(source)
        assert source not in refs(select(app))
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('cognitive_requests')


def test_bounded_history_restart_keeps_private_choice_and_platform_evidence_separate(tmp_path, monkeypatch):
    from nana_core.presence.contracts import HOUR
    from tests.independent_life.test_dialogue import relay
    from tests.person_self.test_private_tendency import form, meaning, current
    home=tmp_path/'home';prepare(home);clock=VirtualClock();source=None
    private='SYNTHETIC_PRIVATE_CONTINUITY_CANARY'
    def render(request):
        choice=request['role_input']['dialogue']['communication_purpose'].get('choice')
        approach=choice['approach'] if choice else 'CHAT'
        known=source in request['source_context_refs']
        return 'SYNTHETIC '+approach+(' SOURCE_KNOWN' if known else ' SOURCE_UNAVAILABLE')
    with relay(home,'CHAT',recall_query_terms=('ORCHID',),meaning_builder=meaning,
               renderer=render,context_limit=32768) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();source,event=populate(app,clock);identity=app.runtime.identity_id
            form(app,text=private,topic='orchid');private_record=current(app)[0][0]
            before=dict(app.runtime.store.one('continuity_records',private_record))
            # Ordinary user text remains transient, even if a bounded excerpt is kept.
            app.chat('SYNTHETIC_VOLATILE_CANARY '+('temporary ' * 120),topic='orchid',
                     privacy='PERSONAL',message_id='before-restart')
            assert any(turn.text_truncated for turn in app._recent)
        clock.advance(49*HOUR)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity and app._recent==[]
            kept=app.chat('SYNTHETIC ORCHID follow-up',topic='orchid',privacy='PERSONAL',message_id='kept')
            print(json.dumps({'checkpoint':'restart-followup','text':kept['text'],
                              'requests_seen':len(requests),'last_two_request_json_bytes':[len(json.dumps(q).encode()) for q in requests[-2:]],
                              'budgets':[q['budget'] for q in requests[-2:]]}))
            assert kept['text']=='SYNTHETIC LISTEN SOURCE_KNOWN'
            assert dict(app.runtime.store.one('continuity_records',private_record))==before
            with monkeypatch.context() as off:
                off.setattr(app.runtime.subject,'dialogue_private_refs',lambda **kw:())
                ablated=app.chat('SYNTHETIC ORCHID follow-up',topic='orchid',privacy='PERSONAL',message_id='ablated')
            assert ablated['text']=='SYNTHETIC CHAT SOURCE_KNOWN'
            app.forget(source)
            retired=app.chat('SYNTHETIC ORCHID follow-up',topic='orchid',privacy='PERSONAL',message_id='retired')
            assert retired['text']=='SYNTHETIC LISTEN SOURCE_UNAVAILABLE'
            assert current(app)[0][0]==private_record
            assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC_VOLATILE_CANARY')>0").fetchone()
            assert len(requests)==8 and all(q['budget']==requests[0]['budget'] for q in requests)
            assert all(private not in q['context_json'] for q in requests if q['cognitive_role']=='SOCIAL')
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('goals')
            print(json.dumps({'source':'retained_platform','virtual_hours':49,'model_calls':len(requests),
                              'real_model_calls':0,'private_ablation':ablated['text'],
                              'after_withdrawal':retired['text'],'budget':requests[0]['budget'],
                              'request_json_bytes':[len(json.dumps(q).encode()) for q in requests]}))
