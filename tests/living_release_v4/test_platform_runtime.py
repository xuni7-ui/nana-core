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


@pytest.mark.parametrize('confirmed', [True, False], ids=['readback', 'unknown'])
def test_delivered_method_opinion_changes_later_c_choice_after_restart(tmp_path, confirmed):
    import json
    from nana_core.continuity.lived_language import LanguageSample, LanguageService
    from nana_core.presence.contracts import SECOND

    later_opinions = []

    def meaning(request):
        context = json.loads(request['context_json'])
        opinions = [json.loads(block['data_json']) for block in context['blocks']
                    if block['kind'] == 'COMMUNICATION_FEEDBACK']
        later_opinions.append(opinions)
        use = any(opinion['delivery_state'] == 'INDEPENDENT_PLATFORM_READBACK'
                  and opinion['human_judgment'] == 'REJECTED' for opinion in opinions)
        proposal = {'approach':'CHAT' if use else 'LISTEN', 'detail':'BRIEF', 'follow_up':'NONE'}
        if len(later_opinions) == 1:
            proposal['strategy_duration_seconds'] = 600
        return {'communication_proposal': proposal}

    def wording(request):
        choice = request['role_input']['dialogue']['communication_purpose'].get('choice')
        if choice is None:
            return 'SYNTHETIC no current C method'
        return 'SYNTHETIC short chat' if choice['approach'] == 'CHAT' else 'SYNTHETIC listening'

    with counterpart() as (url, platform):
        home = tmp_path/'home'
        channel = initialize_channel(home, url)
        clock = VirtualClock()
        with relay(home,'CHAT',meaning_builder=meaning,renderer=wording,context_limit=32768) as (router,requests):
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause()
                flow = equip(app,channel,url)
                turn = app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                    thread_id='qq.private.43',text='SYNTHETIC first message',privacy_class='PROJECT',
                    origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
                platform['lose_ack'] = not confirmed
                assert turn['text'] == 'SYNTHETIC listening'
                first_action = flow._reply(turn,'1')
                assert first_action['delivery'] == ('SUCCEEDED' if confirmed else 'UNKNOWN')
                service = LanguageService(app.runtime.store,app.runtime.authority)
                sample = LanguageSample(sample_id='explicit-delivered-method-review',review_target=turn['exchange_record_id'],
                    mode='CASUAL',context='SYNTHETIC review of the actual method',candidate_response=turn['text'],
                    human_judgment='REJECTED',reason_tags=('TOO_FORMAL',),provenance='USER_PROVIDED_REVIEW',
                    observed_at_us=clock.utc_now_us())
                review_id = service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                    authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
                assert bool(service.records.read(review_id)['payload'].get('delivery_attribution')) is confirmed
                identity = app.runtime.identity_id
                platform_calls = len(platform['calls'])
            clock.advance(10*SECOND)
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause()
                assert app.runtime.identity_id == identity
                flow = QQReplyWorkflow(app,channel,transport(url))
                next_turn = app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:2',
                    thread_id='qq.private.43',text='SYNTHETIC later message',privacy_class='PROJECT',
                    origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
                assert next_turn['text'] == ('SYNTHETIC short chat' if confirmed else 'SYNTHETIC listening')
                assert len(later_opinions) == 2 and not later_opinions[0]
                assert len(later_opinions[1]) == 1
                opinion = later_opinions[1][0]
                assert opinion['delivery_state'] == ('INDEPENDENT_PLATFORM_READBACK' if confirmed else 'NOT_PROVEN')
                assert opinion['effect_status'] == 'NOT_EVALUATED_NO_EFFECT_INFERRED'
                assert opinion['human_read_proven'] is False
                store = app.runtime.store
                first = store.one('actions', first_action['action_id'])
                assert first['state'] == first_action['delivery']
                cycle = store.db.execute('SELECT * FROM subject_cycles WHERE record_id=?',
                    (next_turn['cycle_record_id'],)).fetchone()
                current = app.runtime.subject.result(dict(cycle))
                assert current.evaluation.normative == 'ENDORSED'
                assert current.communication_choice.approach == ('CHAT' if confirmed else 'LISTEN')
                assert first['effect_slot'] != 'subject:' + current.intention_id
                assert len(platform['calls']) == platform_calls and len(platform['sent']) == 1 and len(requests) == 4
                if confirmed:
                    service = LanguageService(store, app.runtime.authority)
                    feedback = next(mid for mid in service.records.support(review_id)
                        if service.records.memory.read(mid)['source_provenance']['source_namespace'] == 'recorded.conversation.feedback')
                    app.forget(feedback)
                    assert not service.records.current_support(next_turn['cycle_record_id'])
                    fresh = app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:3',
                        thread_id='qq.private.43',text='SYNTHETIC after feedback withdrawal',privacy_class='PROJECT',
                        origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
                    assert fresh['text'] == 'SYNTHETIC listening' and not later_opinions[-1]
                    assert len(platform['calls']) == platform_calls and len(platform['sent']) == 1
                else:
                    platform['lose_ack'] = False
                    second = flow._reply(next_turn, '2')
                    assert second['delivery'] == 'SUCCEEDED' and len(platform['sent']) == 2
                    assert second['action_id'] != first_action['action_id']
                    assert store.one('actions', first_action['action_id'])['state'] == 'UNKNOWN'
                    calls = len(platform['calls'])
                    assert flow._reply(next_turn, '2')['delivery'] == 'SUCCEEDED'
                    assert len(platform['calls']) == calls and len(platform['sent']) == 2 and len(requests) == 4


@pytest.mark.parametrize('first_offer', ['local-opinion', 'confirmed-opinion'])
def test_new_delivery_evidence_reopens_feedback_once_without_rescheduling_aliases(tmp_path, first_offer):
    from nana_core.continuity.autonomy.private_intent import feedback_continuation
    from nana_core.continuity.lived_language import LanguageSample, LanguageService
    from nana_core.continuity.subject import SubjectInput
    from nana_core.presence.contracts import Cause, RuntimeEvent, ScheduleSpec, SECOND

    def meaning(_):
        return {'communication_proposal': {'approach':'LISTEN','detail':'BRIEF','follow_up':'NONE',
                                           'strategy_duration_seconds':600}}

    with counterpart() as (url, platform):
        home = tmp_path/'home'
        channel = initialize_channel(home, url)
        clock = VirtualClock()
        with relay(home,'CHAT',meaning_builder=meaning,context_limit=32768) as (router,requests), \
                LifeApplication(home,clock=clock,router=router) as app:
            app.pause()
            flow = equip(app,channel,url)
            turn = app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                thread_id='qq.private.43',text='SYNTHETIC contact before method review',privacy_class='PROJECT',
                origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
            runtime = app.runtime
            service = LanguageService(runtime.store,runtime.authority)
            scope = {'scope':'project-work','entity_id':'project-user'}

            def opinion(label):
                sample = LanguageSample(sample_id=label,review_target=turn['exchange_record_id'],mode='CASUAL',
                    context='SYNTHETIC same opinion as the earlier report',candidate_response=turn['text'],
                    human_judgment='REJECTED',reason_tags=('TOO_FORMAL',),exact_feedback='SYNTHETIC use ordinary chat',
                    provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us())
                rid = service.record(sample,**scope,privacy='PROJECT',authority=runtime.authority,
                    exchange_record_id=turn['exchange_record_id'])
                return rid, service.experience(rid,runtime.authority)

            project = {'privacy_classes':('PROJECT',), **scope}

            def schedule(view, experience):
                now = clock.utc_now_us()
                inp = SubjectInput(source_key='synthetic.feedback-schedule',kind='WAKE',origin='SELF_WAKE',
                    **scope,observed_at_us=now,task_class='private.feedback.review',reflection_experience_id=experience,
                    source_memory_ids=view['memory_ids'])
                runtime.scheduler.add(ScheduleSpec(dedupe_key=view['key'],kind='CONDITION',due_at_us=now,
                    event=RuntimeEvent(event_type='REFLECTION_EVENT',trigger='REFLECTION_TRIGGER',input=inp,
                        causes=(Cause(kind='EXPERIENCE',reference_id=experience),),due_at_us=now)))

            before, original_experience = opinion('before-delivery')
            original = feedback_continuation(runtime.store,original_experience,**project)
            assert original and 'delivery_attribution' not in service.records.read(before)['payload']
            if first_offer == 'local-opinion':
                schedule(original, original_experience)
            clock.advance(SECOND)
            assert flow._reply(turn,'1')['delivery']=='SUCCEEDED'
            verified, subsequent = opinion('after-delivery')
            actual = feedback_continuation(runtime.store,subsequent,**project)
            assert actual and service.records.read(verified)['payload']['delivery_attribution']['human_read_proven'] is False
            assert (actual['key'] != original['key']) is (first_offer == 'local-opinion')
            assert feedback_continuation(runtime.store,original_experience,**project) is None
            if first_offer == 'confirmed-opinion':
                schedule(actual, subsequent)
            clock.advance(SECOND)
            _, same_experience = opinion('alias-after-delivery')
            duplicate = feedback_continuation(runtime.store,same_experience,**project)
            assert duplicate and duplicate['key']==actual['key']
            opportunities = runtime.subject.background_opportunities(entity_id=scope['entity_id'],
                now_us=clock.utc_now_us(),quiet_since_us=clock.utc_now_us()-2*SECOND,quiet_window_us=SECOND)
            expected_keys = {actual['key']} if first_offer == 'local-opinion' else set()
            assert {item.key for item in opportunities if item.task_class == 'private.feedback.review'} == expected_keys
            assert len(platform['sent'])==1 and len(requests)==2


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


@pytest.mark.parametrize('foreign_review_count', [0, 256], ids=['recipient', 'crowded-recipient'])
def test_memory_use_opinion_on_unconfirmed_platform_reply_stays_with_its_recipient(tmp_path, foreign_review_count):
    import json
    from nana_core.continuity.lived_language import LanguageSample, LanguageService, MemoryUseFeedback
    from nana_core.life.memory_notes import save
    from nana_core.presence.contracts import SECOND

    def wording(request):
        blocks = json.loads(request['context_json'])['blocks']
        items = [item for block in blocks if block['kind']=='MEMORY_USE_GUIDANCE'
                 for item in json.loads(block['data_json'])['memory_use_guidance']]
        return 'SYNTHETIC silent reference' if any(item['requested_mode']=='IMPLICIT_REFERENCE' for item in items) else 'SYNTHETIC baseline'

    with counterpart() as (url,platform):
        home=tmp_path/'home';channel=initialize_channel(home,url);clock=VirtualClock()
        with relay(home,'CHAT',renderer=wording,recall_query_terms=('ORCHID',),context_limit=32768) as (router,requests):
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();flow=equip(app,channel,url)
                mid=save(app,text='SYNTHETIC ORCHID meeting Friday',privacy='PROJECT',request_id='recipient-note')['memory_id']
                turn=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:1',
                    thread_id='qq.private.43',text='SYNTHETIC ORCHID question',privacy_class='PROJECT',
                    origin='SYNTHETIC_LOOPBACK',retain_shared_life=True),reply_target=flow.target)
                platform['lose_ack']=True
                assert flow._reply(turn,'1')['delivery']=='UNKNOWN'
                language=LanguageService(app.runtime.store,app.runtime.authority)
                sample=LanguageSample(sample_id='unconfirmed-recipient-opinion',review_target=turn['exchange_record_id'],
                    mode='CASUAL',context='SYNTHETIC own platform context',candidate_response=turn['text'],
                    human_judgment='PARTIAL',provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us(),
                    memory_use=MemoryUseFeedback(memory_id=mid,mode='IMPLICIT_REFERENCE'))
                review=language.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                    authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
                assert 'delivery_attribution' not in language.records.read(review)['payload']
                if foreign_review_count:
                    other=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:99',
                        thread_id='qq.private.44',text='SYNTHETIC ORCHID question for another recipient',privacy_class='PROJECT',
                        origin='SYNTHETIC_LOOPBACK',retain_shared_life=True))
                    for index in range(foreign_review_count):
                        wrong_receiver=sample.model_copy(update={'sample_id':f'foreign-use-{index}',
                            'review_target':other['exchange_record_id'],'candidate_response':other['text'],
                            'memory_use':MemoryUseFeedback(memory_id=mid,mode='EXPLICIT_RECALL')})
                        language.record(wrong_receiver,scope='project-work',entity_id='project-user',privacy='PROJECT',
                            authority=app.runtime.authority,exchange_record_id=other['exchange_record_id'])
                identity=app.runtime.identity_id
            clock.advance(2*SECOND)
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();assert app.runtime.identity_id==identity
                foreign=app.chat('SYNTHETIC ORCHID question on a different surface',topic='later',
                    privacy='PROJECT',message_id='local-other-audience')
                assert foreign['text']=='SYNTHETIC baseline'
                matching=app.surfaces.receive(SurfaceObservation(binding_id=channel.binding_id,event_id='qq:2',
                    thread_id='qq.private.43',topic='later',text='SYNTHETIC ORCHID later question',
                    privacy_class='PROJECT',origin='SYNTHETIC_LOOPBACK',retain_shared_life=True))
                assert matching['text']=='SYNTHETIC silent reference'
                assert len(platform['sent'])==1 and len(requests)==(8 if foreign_review_count else 6)


@pytest.mark.parametrize('same_recipient', [True, False], ids=['transfer','split-evidence'])
def test_expression_reviews_qualify_and_transfer_only_for_their_recipient(tmp_path, same_recipient):
    import json
    from nana_core.continuity.learning import ExperienceService
    from nana_core.continuity.lived_language import LanguageSample, LanguageService
    from nana_core.presence.contracts import SECOND

    def wording(request):
        blocks=json.loads(request['context_json'])['blocks']
        if any(block['kind']=='LIVED_LANGUAGE' for block in blocks):return 'SYNTHETIC concise'
        return 'SYNTHETIC baseline'

    def receive(app, identifier, peer, topic, *, retain=False):
        return app.surfaces.receive(SurfaceObservation(binding_id='qq.primary',event_id=f'qq:{identifier}',
            thread_id=f'qq.private.{peer}',topic=topic,text=f'SYNTHETIC topic {topic}',privacy_class='PROJECT',
            origin='SYNTHETIC_LOOPBACK',retain_shared_life=retain))

    with counterpart() as (url,platform):
        home=tmp_path/'home';initialize_channel(home,url);clock=VirtualClock()
        with relay(home,'CHAT',renderer=wording,context_limit=32768) as (router,requests):
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();r=app.runtime;identity=r.identity_id
                service=LanguageService(r.store,r.authority)
                supporting_reviews=[]
                for i,peer in enumerate(('43','43' if same_recipient else '44'),1):
                    turn=receive(app,i,peer,f'independent-{i}',retain=True)
                    sample=LanguageSample(sample_id=f'expression-bound-{i}',review_target=turn['exchange_record_id'],
                        mode='CASUAL',context='SYNTHETIC a recipient-specific preference',candidate_response=turn['text'],
                        human_judgment='REJECTED',reason_tags=('TOO_VERBOSE',),exact_feedback='SYNTHETIC_AUDIENCE_CANARY',
                        provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us())
                    rid=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                        authority=r.authority,exchange_record_id=turn['exchange_record_id'])
                    eid=service.experience(rid,r.authority)
                    supporting_reviews.append(rid)
                experience=ExperienceService(r.store,r.authority)
                lesson=experience.derive_lesson(eid)
                checks=experience.test_lesson(lesson)
                assert all(checks.values()) is same_recipient
                if not same_recipient:
                    assert r.store.one('lessons',lesson)['state']=='REJECTED'
                    return
                experience.activate(lesson,r.authority)
            clock.advance(2*SECOND)
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();assert app.runtime.identity_id==identity
                local=app.chat('SYNTHETIC local independent topic',topic='unseen-local',privacy='PROJECT',message_id='unseen-local')
                assert local['text']=='SYNTHETIC baseline'
                assert all('SYNTHETIC_AUDIENCE_CANARY' not in req['context_json'] for req in requests[-2:])
                foreign=receive(app,3,'44','unseen-other')
                assert foreign['text']=='SYNTHETIC baseline'
                assert all('SYNTHETIC_AUDIENCE_CANARY' not in req['context_json'] for req in requests[-2:])
                matched=receive(app,4,'43','unseen-match',retain=True)
                assert matched['text']=='SYNTHETIC concise'
                r=app.runtime;service=LanguageService(r.store,r.authority)
                counter=LanguageSample(sample_id='expression-bound-counter',review_target=matched['exchange_record_id'],
                    mode='CASUAL',context='SYNTHETIC an independent counterexample',candidate_response=matched['text'],
                    human_judgment='REJECTED',reason_tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW',
                    observed_at_us=clock.utc_now_us())
                counter_id=service.record(counter,scope='project-work',entity_id='project-user',privacy='PROJECT',
                    authority=r.authority,exchange_record_id=matched['exchange_record_id'])
                assert receive(app,5,'43','unseen-counter')['text']=='SYNTHETIC baseline'

                def withdraw_review(record_id):
                    sample_id=service.records.read(record_id)['payload']['sample']['sample_id']
                    opinion = next(mid for mid in service.records.support(record_id)
                        if service.records.memory.read(mid)['source_provenance']['source_reference'] == sample_id)
                    app.forget(opinion)
                    assert not service.records.current_support(record_id)

                withdraw_review(counter_id)
                assert receive(app,6,'43','after-counter-withdrawal')['text']=='SYNTHETIC concise'
                withdraw_review(supporting_reviews[0])
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();assert app.runtime.identity_id==identity
                assert receive(app,7,'43','after-support-withdrawal')['text']=='SYNTHETIC baseline'
                assert len(requests)==16 and not platform['sent']


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


def test_owner_media_cache_binding_is_volatile_and_account_isolated(tmp_path, monkeypatch):
    from nana_core.nanalink.media import MediaCache
    from nana_core.life import platform_runtime
    with counterpart() as (url, _):
        home = tmp_path / 'home'
        channel = initialize_channel(home, url)
        with LifeApplication(home, clock=VirtualClock()) as app:
            app.pause()
            app.config = app.config.model_copy(update={'qq_channels': (channel,)})
            cache = MediaCache(tmp_path / 'cache', source_current=lambda _: True)
            seen = []
            class Flow:
                def __init__(self, app, channel, transport, *, media_cache=None):
                    seen.append(media_cache)
                def receive(self, message_id):
                    return {'delivery': 'NOT_SENT'}
            monkeypatch.setattr(platform_runtime, 'QQReplyWorkflow', Flow)
            app.platforms.qq('primary', '1')
            app.platforms.bind_qq_media_cache('primary', cache)
            app.platforms.qq('primary', '1')
            other = channel.model_copy(update={'channel_id': 'secondary', 'account_id': '44'})
            app.config = app.config.model_copy(update={'qq_channels': (channel, other)})
            with pytest.raises(CoreError, match='QQ_MEDIA_ACCOUNT_ISOLATION_REQUIRED'):
                app.platforms.bind_qq_media_cache('secondary', cache)
            changed = channel.model_copy(update={'account_id': '99'})
            app.config = app.config.model_copy(update={'qq_channels': (changed,)})
            app.platforms.qq('primary', '1')
            assert seen == [None, cache, None]
            with pytest.raises(CoreError, match='QQ_MEDIA_ACCOUNT_ISOLATION_REQUIRED'):
                app.platforms.bind_qq_media_cache('primary', cache)
            with pytest.raises(CoreError, match='QQ_CHANNEL_UNBOUND'):
                app.platforms.bind_qq_media_cache('unknown', cache)
            cache.close()


def test_owner_caches_only_exact_current_original_image(tmp_path):
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.world_loop.perception import PerceptionService, PublicMediaSource
    from nana_core.nanalink.media import MediaCache
    from nana_core.nanalink.media_candidates import candidate, resolve_image
    from tests.person_self.test_nanalink_media_choice import picture
    from tests.world_loop.helpers import providers
    with counterpart() as (url, _):
        home = tmp_path / 'home'
        channel = initialize_channel(home, url)
        with LifeApplication(home, clock=VirtualClock()) as app:
            app.pause()
            app.config = app.config.model_copy(update={'qq_channels': (channel,)})
            r = app.runtime
            now = r.clock.utc_now_us()
            source = PublicMediaSource(source_id='owned-original', modality='IMAGE', origin='SYNTHETIC',
                                       event_time_us=now, observed_time_us=now)
            data = picture()
            mid, _ = PerceptionService(r.store, providers(), app.policy).ingest(
                data, source, entity_id='project-user', scope='project-work')
            cache = MediaCache(tmp_path/'image-cache', source_current=lambda _: True)
            with pytest.raises(CoreError, match='QQ_MEDIA_CACHE_UNBOUND'):
                app.platforms.cache_qq_observed_image('primary', mid, data)
            app.platforms.bind_qq_media_cache('primary', cache)
            MemoryService(r.store).entity('other-person', 'PERSON')
            other_source = source.model_copy(update={'source_id': 'other-person-picture'})
            other_mid, _ = PerceptionService(r.store, providers(), app.policy).ingest(
                data, other_source, entity_id='other-person', scope='project-work')
            with pytest.raises(CoreError, match='QQ_MEDIA_ORIGINAL_SOURCE_REQUIRED'):
                app.platforms.cache_qq_observed_image('primary', other_mid, data)
            with pytest.raises(CoreError, match='QQ_MEDIA_SOURCE_BYTES_MISMATCH'):
                app.platforms.cache_qq_observed_image('primary', mid, b'wrong')
            result = app.platforms.cache_qq_observed_image('primary', mid, data)
            assert result['execution_authority'] is False and result['bytes_cached'] == len(data)
            selected = candidate(MemoryService(r.store).read(mid))
            assert resolve_image(r.store, cache, selected) == data
            MemoryService(r.store, r.authority).forget(mid, r.authority)
            with pytest.raises(CoreError):
                app.platforms.cache_qq_observed_image('primary', mid, data)
            assert not r.store.all('actions') and not r.store.all('grants')
            cache.close()


def test_actual_qq_ingress_can_use_light_cognition_without_selecting_image(tmp_path):
    import json
    from nana_core.continuity.world_loop.perception import PerceptionService, PublicMediaSource
    from nana_core.nanalink.media import MediaCache
    from tests.person_self.test_nanalink_media_choice import picture
    from tests.world_loop.helpers import providers

    def choose(request):
        context = json.loads(request['context_json'])
        identity = context['manifest']
        candidates = [json.loads(b['data_json'])['candidates'][0] for b in context['blocks'] if b['kind'] == 'MEDIA_CANDIDATES']
        assert candidates
        item = candidates[0]
        return {'interpretation': 'SYNTHETIC optional picture', 'subject_cognition': {
            'identity_id': identity['identity_id'], 'identity_revision': identity['identity_revision'],
            'interpretation': 'SYNTHETIC consider sharing', 'proposed_operations': ['DRAFT'],
            'memory_refs': [item['source_memory_id']], 'selected_media': item}}

    with counterpart() as (url, platform):
        home = tmp_path/'home'
        channel = initialize_channel(home, url)
        with relay(home, 'CHAT', context_limit=32768, subject_builder=choose) as (router, requests), \
                LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            app.config = app.config.model_copy(update={'qq_channels': (channel,)})
            r = app.runtime
            now = r.clock.utc_now_us()
            source = PublicMediaSource(source_id='prior-picture', modality='IMAGE', origin='SYNTHETIC',
                                       event_time_us=now, observed_time_us=now)
            data = picture()
            mid, _ = PerceptionService(r.store, providers(), app.policy).ingest(
                data, source, entity_id='project-user', scope='project-work')
            cache = MediaCache(tmp_path/'prior-cache', source_current=lambda _: True)
            app.platforms.bind_qq_media_cache('primary', cache)
            app.platforms.cache_qq_observed_image('primary', mid, data)
            app.bind_provider_cognition()
            flow = equip(app, channel, url)
            flow.port.media_cache = cache
            result = flow.receive('1')
            assert result['delivery'] == 'SUCCEEDED' and result['external_delivery']
            assert len(platform['sent']) == 1 and len(platform['sent'][0]['message']) == 1
            assert [request['cognitive_role'] for request in requests] == ['INTERPRET', 'SOCIAL']
            assert flow.receive('1')['delivery'] == 'SUCCEEDED' and len(platform['sent']) == 1
            cache.close()


def test_owner_managed_media_cache_closes_with_application(tmp_path):
    from pathlib import Path
    with counterpart() as (url, _):
        home = tmp_path/'home'
        channel = initialize_channel(home, url)
        with LifeApplication(home, clock=VirtualClock()) as app:
            app.pause()
            app.config = app.config.model_copy(update={'qq_channels': (channel,)})
            assert app.platforms.open_qq_media_cache('primary') == {'state':'CACHE_BOUND_NO_AUTHORITY','persistent':False}
            cache, directory = app.platforms._owned_qq_media_caches['primary']
            path = Path(directory.name)
            assert path.is_dir() and cache.total == 0
            with pytest.raises(CoreError, match='QQ_MEDIA_CACHE_ALREADY_BOUND'):
                app.platforms.open_qq_media_cache('primary')
            app.platforms.bind_qq_media_cache('primary', None)
            assert not path.exists()
            app.platforms.open_qq_media_cache('primary')
            _, directory = app.platforms._owned_qq_media_caches['primary']
            path = Path(directory.name)
            assert path.is_dir()
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert not path.exists()
