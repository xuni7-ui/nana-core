"""Actual original chat/C -> original Kernel -> owned HTTP counterpart.

No prewritten C cycle or real account; synthetic model wording and owned effects
are explicitly independent from real-platform/provider/human qualification.
"""

import pytest

from nana_core.contracts import GrantSpec, CoreError
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.platform_runtime import QQChannelBinding, QQReplyWorkflow
from nana_core.life.surfaces import SurfaceBinding, SurfaceObservation
from nana_core.presence.authority import VirtualClock
from tests.person_self.conftest import initialize
from tests.independent_life.test_dialogue import relay
from tests.living_release_v4.test_platform_bridge import counterpart, transport


def initialize_channel(home, url):
    initialize(home)
    cfg = load_config(home)
    binding = SurfaceBinding(
        binding_id="qq.primary",
        platform="qq.onebot",
        surface="chat.direct",
        adapter="qq.onebot",
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=("PROJECT",),
    )
    update_config(
        home,
        cfg.model_copy(update={"revision": cfg.revision + 1, "surface_bindings": (binding,)}),
        expected_revision=cfg.revision,
    )
    return QQChannelBinding(
        channel_id="primary",
        binding_id=binding.binding_id,
        endpoint=url,
        account_id="42",
        sender_id="43",
        target_id="43",
        enabled=True,
        read_authorized=True,
        send_authorized=True,
    )


def equip(app, channel, url, *, with_grant=True):
    flow = QQReplyWorkflow(app, channel, transport(url))
    GovernanceController(app.runtime.store, app.runtime.authority).initialize(app.runtime.authority)
    flow.realization.kernel.set_budgets(
        {"external_requests": 16, "write_attempts": 4, "cost_micro_units": 16}, app.runtime.authority
    )
    if with_grant:
        flow.realization.kernel.grant(
            GrantSpec(
                capabilities=("world.contact", "world.action.verify"),
                resources=(flow.resource,),
                not_before_us=app.runtime.clock.utc_now_us(),
                expires_at_us=app.runtime.clock.utc_now_us() + 100_000000,
            ),
            app.runtime.authority,
        )
    return flow


def test_original_natural_reply_completes_actual_owned_send_and_duplicate_is_receipt_only(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        with (
            relay(home, "CHAT") as (router, requests),
            LifeApplication(home, clock=VirtualClock(), router=router) as app,
        ):
            app.pause()
            flow = equip(app, channel, url)
            result = flow.receive("1")
            assert result["delivery"] == "SUCCEEDED" and result["external_delivery"]
            assert len(requests) == 2 and len(platform["sent"]) == 1
            assert platform["sent"][0]["message"] == [
                {"type": "text", "data": {"text": "A deliberately synthetic language response"}}
            ]
            calls = len(platform["calls"])
            assert flow.receive("1")["delivery"] == "SUCCEEDED"
            assert len(platform["calls"]) == calls and len(requests) == 2


def test_unknown_restart_does_not_refetch_reinterpret_or_resend(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        clock = VirtualClock()
        with relay(home, "CHAT") as (router, requests):
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = equip(app, channel, url)
                platform["lose_ack"] = True
                result = flow.receive("1")
                assert result["delivery"] == "UNKNOWN" and not result["external_delivery"]
                calls = len(platform["calls"])
                identity = app.runtime.identity_id
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = QQReplyWorkflow(app, channel, transport(url))
                later = flow.receive("1")
                assert later["delivery"] == "UNKNOWN"
                assert len(platform["calls"]) == calls and len(platform["sent"]) == 1 and len(requests) == 2
                assert app.runtime.identity_id == identity


def test_direct_reply_window_is_not_a_grant_or_proactive_permission(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        with relay(home, "CHAT") as (router, _), LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            flow = equip(app, channel, url, with_grant=False)
            with pytest.raises(CoreError, match="AUTH_REQUIRED"):
                flow.receive("1")
            assert platform["sent"] == []
            assert not app.runtime.store.all("grants")


def test_reply_source_window_and_peer_cannot_authorize_other_or_later_delivery(tmp_path):
    from nana_core.continuity.open_agency.delivery import DeliveryAdmission, DeliveryPolicy, ReplyWindowBinding

    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        clock = VirtualClock()
        with relay(home, "CHAT") as (router, _), LifeApplication(home, clock=clock, router=router) as app:
            app.pause()
            flow = equip(app, channel, url)
            result = app.surfaces.receive(
                SurfaceObservation(
                    binding_id=channel.binding_id,
                    event_id="test:window",
                    thread_id="qq.private.43",
                    text="PROJECT reply window",
                    privacy_class="PROJECT",
                    origin="SYNTHETIC_LOOPBACK",
                ),
                reply_target=flow.target,
            )
            row = app.runtime.store.db.execute(
                "SELECT * FROM subject_cycles WHERE cycle_id=?", (result["cycle_id"],)
            ).fetchone()
            cycle = app.runtime.subject.result(dict(row))
            admission = flow.port.delivery
            assert admission.assess(cycle, flow.resource)["result"] == "UNKNOWN_AVAILABILITY"
            wrong = DeliveryAdmission(
                app.runtime.store,
                DeliveryPolicy(
                    recipients=(flow.resource,),
                    privacy_classes=("PROJECT",),
                    direct_reply_bindings=(
                        ReplyWindowBinding(
                            resource=flow.resource,
                            binding_id=channel.binding_id,
                            platform="qq.onebot",
                            thread_id="qq.private.44",
                        ),
                    ),
                ),
                scopes=app.runtime.config.scopes,
                privacy_classes=("PROJECT",),
            )
            with pytest.raises(CoreError, match="DIRECT_REPLY_PEER_UNBOUND"):
                wrong.assess_reply(cycle, flow.resource)
            clock.advance(61_000000)
            with pytest.raises(CoreError, match="DIRECT_REPLY_WINDOW_EXPIRED"):
                admission.assess_reply(cycle, flow.resource)
            assert not platform["sent"]


def test_source_read_uses_original_budget_and_cannot_dispatch_when_exhausted(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        with LifeApplication(home, clock=VirtualClock()) as app:
            app.pause()
            flow = equip(app, channel, url)
            flow.realization.kernel.set_budgets(
                {"external_requests": 1, "cost_micro_units": 1, "write_attempts": 4}, app.runtime.authority
            )
            with pytest.raises(CoreError, match="BUDGET_EXHAUSTED"):
                flow.receive("1")
            assert platform["calls"] == [] and not platform["sent"]
            assert not app.runtime.store.db.execute("SELECT 1 FROM events WHERE kind='platform.qq.ingress_reserved'").fetchone()


def test_channel_bound_is_given_before_rendering_not_mechanical_post_split(tmp_path):
    with counterpart() as (url, platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        def render(request):
            limit=request['role_input']['dialogue'].get('reply_character_limit',16384)
            return 'SYNTHETIC bounded channel reply' if limit==2048 else 'SYNTHETIC long channel wording '*100
        with relay(home,'CHAT',renderer=render) as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            result=flow.receive('1')
            assert result['delivery']=='SUCCEEDED' and len(platform['sent'])==1
            assert requests[-1]['role_input']['dialogue']['reply_character_limit']==2048
            assert requests[-1]['expected_schema']['$defs']['DialogueDraft']['properties']['text']['anyOf'][0]['maxLength']==2048
            assert platform['sent'][0]['message']==[{'type':'text','data':{'text':'SYNTHETIC bounded channel reply'}}]
            assert len(requests)==2


def test_oversized_channel_reply_is_rejected_before_sending_without_split_or_retry(tmp_path):
    with counterpart() as (url, platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        with relay(home,'CHAT',renderer=lambda request:'SYNTHETIC oversized channel reply '*100) as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            result=flow.receive('1')
            assert result['render_state']=='DIALOGUE_REPLY_BOUND'
            assert result['delivery']=='NOT_AUTHORIZED_OR_NO_MODEL_WORDING'
            assert not platform['sent'] and len(requests)==2
            assert not app.runtime.store.all('actions')
            flow.receive('1')
            assert not platform['sent'] and len(requests)==2


def test_retained_reply_feedback_uses_independent_readback_not_generated_wording(tmp_path):
    from nana_core.life.conversation import history
    from nana_core.life.memory_notes import save
    from nana_core.continuity.lived_language import LanguageService, LanguageSample, MemoryUseFeedback
    with counterpart() as (url, platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        with relay(home,'CHAT',recall_query_terms=('ORCHID',)) as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            mid=save(app,text='SYNTHETIC ORCHID meeting Friday',privacy='PROJECT',request_id='delivery-note')['memory_id']
            turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                thread_id='qq.private.43',text='SYNTHETIC ORCHID question',privacy_class='PROJECT',
                origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
            row=history(app,privacy=('PROJECT',))['items'][-1]
            assert row.get('reply_delivery') is None
            delivered=flow._reply(turn,'1')
            assert delivered['delivery']=='SUCCEEDED' and len(platform['sent'])==1
            io=len(platform['calls'])
            row=history(app,privacy=('PROJECT',))['items'][-1]
            proof=row.get('reply_delivery')
            assert proof and proof['state']=='INDEPENDENT_PLATFORM_READBACK'
            assert proof['origin']=='SYNTHETIC_LOOPBACK' and proof['human_read_proven'] is False
            assert proof['entity_id']=='project-user' and proof['scope']=='project-work'
            assert proof['action_id']==delivered['action_id']
            assert row['memory_use_delivery_proven'] is False
            language=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='delivered-memory-review',review_target=turn['exchange_record_id'],
                mode='CASUAL',context='SYNTHETIC explicit review after fixture readback',candidate_response=turn['text'],
                human_judgment='PARTIAL',provenance='USER_PROVIDED_REVIEW',observed_at_us=app.runtime.clock.utc_now_us(),
                memory_use=MemoryUseFeedback(memory_id=mid,mode='NATURAL_REFERENCE'))
            rid=language.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            payload=language.records.read(rid)['payload']
            assert payload['delivery_attribution']['action_id']==delivered['action_id']
            assert payload['delivery_attribution']['origin']=='SYNTHETIC_LOOPBACK'
            assert payload['delivery_attribution']['human_read_proven'] is False
            assert len(platform['calls'])==io and len(requests)==2
            source=language.records.support(rid)
            assert mid in source
            app.forget(mid)
            assert not language.records.current_support(rid)
            assert not history(app,privacy=('PROJECT',))['items']


@pytest.mark.parametrize('lost_ack',[False,True],ids=['readback','unknown'])
def test_method_opinion_keeps_exact_recipient_and_delivery_evidence_separate(tmp_path,lost_ack):
    from nana_core.continuity.lived_language import LanguageService,LanguageSample,communication_feedback
    def meaning(request):
        return {'communication_proposal':{'approach':'LISTEN','detail':'BRIEF','follow_up':'NONE','strategy_duration_seconds':600}}
    with counterpart() as (url,platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        with relay(home,'CHAT',meaning_builder=meaning,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                thread_id='qq.private.43',text='SYNTHETIC retained method reply',privacy_class='PROJECT',
                origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
            platform['lose_ack']=lost_ack
            result=flow._reply(turn,'1')
            assert result['delivery']==('UNKNOWN' if lost_ack else 'SUCCEEDED')
            io=len(platform['calls']);service=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='method-delivery-opinion',review_target=turn['exchange_record_id'],mode='CASUAL',
                context='SYNTHETIC explicit opinion, not a claim of recovery',candidate_response=turn['text'],
                human_judgment='PARTIAL',reason_tags=('TOO_FORMAL',),provenance='USER_PROVIDED_REVIEW',observed_at_us=app.clock.utc_now_us())
            rid=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,
                exchange_record_id=turn['exchange_record_id'])
            binding=service.records.read(rid)['payload']['communication_attribution']
            recipient={'platform':'qq.onebot','binding_id':'qq.primary','conversation_id':'qq.private.43'}
            assert binding['recipient_context']==recipient and binding['reviewed_choice']['approach']=='LISTEN'
            args=dict(scope='project-work',entity_id='project-user',topic=binding['topic'],recipient_context=recipient,privacy=('PROJECT',))
            projected=communication_feedback(app.runtime.store,**args)
            assert projected['delivery_state']==('NOT_PROVEN' if lost_ack else 'INDEPENDENT_PLATFORM_READBACK')
            assert projected['delivery_origin']==(None if lost_ack else 'SYNTHETIC_LOOPBACK')
            assert projected['human_read_proven'] is False and projected['effect_status']=='NOT_EVALUATED_NO_EFFECT_INFERRED'
            assert communication_feedback(app.runtime.store,**(args|{'recipient_context':None})) is None
            assert communication_feedback(app.runtime.store,**(args|{'recipient_context':recipient|{'conversation_id':'qq.private.44'}})) is None
            assert len(platform['calls'])==io and len(requests)==2  # No verification retry or new cognition for an opinion.


@pytest.mark.parametrize('failure', ['lost_ack', 'wrong_peer'])
def test_unconfirmed_retained_reply_does_not_gain_delivery_attribution(tmp_path, failure):
    from nana_core.life.conversation import history
    from nana_core.continuity.lived_language import LanguageService, LanguageSample
    with counterpart() as (url,platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        with relay(home,'CHAT') as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                thread_id='qq.private.43',text='SYNTHETIC retained pending reply',privacy_class='PROJECT',
                origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
            if failure=='lost_ack':platform['lose_ack']=True
            else:platform['read_peer']='44'
            result=flow._reply(turn,'1')
            assert result['delivery']==('UNKNOWN' if failure=='lost_ack' else 'FAILED_EFFECT')
            io=len(platform['calls'])
            assert history(app,privacy=('PROJECT',))['items'][-1].get('reply_delivery') is None
            language=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='local-review',review_target=turn['exchange_record_id'],mode='CASUAL',
                context='SYNTHETIC opinion about generated wording only',candidate_response=turn['text'],
                human_judgment='PARTIAL',provenance='USER_PROVIDED_REVIEW',observed_at_us=app.runtime.clock.utc_now_us())
            rid=language.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            assert 'delivery_attribution' not in language.records.read(rid)['payload']
            assert len(platform['calls'])==io and len(platform['sent'])==1 and len(requests)==2


def test_reply_readback_is_not_retroactively_attributed_to_an_earlier_review(tmp_path):
    from nana_core.continuity.lived_language import LanguageService, LanguageSample
    with counterpart() as (url,platform):
        home=tmp_path/'home';channel=initialize_channel(home,url);clock=VirtualClock()
        with relay(home,'CHAT') as (router,_), LifeApplication(home,clock=clock,router=router) as app:
            app.pause();flow=equip(app,channel,url)
            turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                thread_id='qq.private.43',text='SYNTHETIC review before actual fixture send',privacy_class='PROJECT',
                origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
            before=clock.utc_now_us();clock.advance(10)
            assert flow._reply(turn,'1')['delivery']=='SUCCEEDED'
            language=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='earlier-review',review_target=turn['exchange_record_id'],mode='CASUAL',
                context='SYNTHETIC earlier local opinion',candidate_response=turn['text'],human_judgment='PARTIAL',
                provenance='USER_PROVIDED_REVIEW',observed_at_us=before)
            rid=language.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            assert 'delivery_attribution' not in language.records.read(rid)['payload']


def test_reply_readback_provenance_survives_restart_without_network_or_human_read_claim(tmp_path):
    from nana_core.life.conversation import history
    with counterpart() as (url,platform):
        home=tmp_path/'home';channel=initialize_channel(home,url);clock=VirtualClock()
        with relay(home,'CHAT') as (router,requests):
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();flow=equip(app,channel,url)
                turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                    thread_id='qq.private.43',text='SYNTHETIC retained reply',privacy_class='PROJECT',
                    origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
                assert flow._reply(turn,'1')['delivery']=='SUCCEEDED'
                proof=history(app,privacy=('PROJECT',))['items'][-1]['reply_delivery']
                assert proof['recipient_context']=={'platform':'qq.onebot','binding_id':'qq.primary','conversation_id':'qq.private.43'}
                identity=app.runtime.identity_id;io=len(platform['calls'])
            with LifeApplication(home,clock=clock) as app:
                app.pause()
                assert app.runtime.identity_id==identity
                restored=history(app,privacy=('PROJECT',))['items'][-1]['reply_delivery']
                assert restored==proof and restored['human_read_proven'] is False
                assert restored['origin']=='SYNTHETIC_LOOPBACK' and restored['memory_use_verified'] is False
                assert len(platform['calls'])==io and len(requests)==2


@pytest.mark.parametrize('preexisting_retained_turns', [0, 1])
def test_delivered_memory_feedback_changes_later_render_only_in_its_recipient_context(tmp_path,preexisting_retained_turns):
    import json
    from nana_core.life.memory_notes import save
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.lived_language import LanguageService, LanguageSample, MemoryUseFeedback
    def render(request):
        blocks=json.loads(request['context_json'])['blocks']
        guidance=next((json.loads(b['data_json'])['memory_use_guidance'] for b in blocks
            if b['kind']=='MEMORY_USE_GUIDANCE'),())
        return 'SYNTHETIC '+(guidance[0]['requested_mode'] if guidance else 'BASELINE')
    with counterpart() as (url,platform):
        home=tmp_path/'home';channel=initialize_channel(home,url);clock=VirtualClock()
        with relay(home,'CHAT',recall_query_terms=('ORCHID',),renderer=render) as (router,requests):
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();flow=equip(app,channel,url)
                for index in range(preexisting_retained_turns):
                    app.chat('SYNTHETIC earlier unrelated conversation '+str(index),privacy='PROJECT',
                        retain_shared_life=True,message_id='earlier-'+str(index))
                mid=save(app,text='SYNTHETIC ORCHID Friday',privacy='PROJECT',request_id='recipient-note')['memory_id']
                fact=MemoryService(app.runtime.store).read(mid)
                turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                    thread_id='qq.private.43',text='SYNTHETIC ORCHID first question',privacy_class='PROJECT',
                    origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
                assert turn['text']=='SYNTHETIC BASELINE'
                assert flow._reply(turn,'1')['delivery']=='SUCCEEDED'
                service=LanguageService(app.runtime.store,app.runtime.authority)
                sample=LanguageSample(sample_id='recipient-review',review_target=turn['exchange_record_id'],mode='CASUAL',
                    context='SYNTHETIC explicit fixture review',candidate_response=turn['text'],human_judgment='PARTIAL',
                    provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us(),
                    memory_use=MemoryUseFeedback(memory_id=mid,mode='NATURAL_REFERENCE'))
                review_id=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                    authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
                io=len(platform['calls']);identity=app.runtime.identity_id
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();assert app.runtime.identity_id==identity
                for sequence,thread,expected in ((2,'qq.private.43','NATURAL_REFERENCE'),(3,'qq.private.44','BASELINE')):
                    later=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:'+str(sequence),
                        thread_id=thread,text='SYNTHETIC ORCHID later question',privacy_class='PROJECT',
                        origin='SYNTHETIC_LOOPBACK',retain_shared_life=True))
                    assert later['text']=='SYNTHETIC '+expected,later
                    assert mid in requests[-1]['source_context_refs']
                    assert requests[-1]['role_input']['dialogue']['recipient_context']['conversation_id']==thread
                assert len(requests)==6+2*preexisting_retained_turns and len(platform['calls'])==io and len(platform['sent'])==1
                assert MemoryService(app.runtime.store).read(mid)==fact
                app.forget(mid)
                assert not LanguageService(app.runtime.store,app.runtime.authority).records.current_support(review_id)
