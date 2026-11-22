"""Original C can reconsider accommodation instead of decorating a fixed answer."""
import json
import pytest
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput,PreferenceSignal
from nana_core.continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority
from nana_core.continuity.relational.contracts import SubjectPersonalitySeed,RelationalAnchorSpec,RelationalRequest,DAY
from nana_core.continuity.relational.projections import social_appetite
from nana_core.presence.runtime import NanaRuntime
from tests.world_loop.helpers import fresh,policy


def prepare(r):
    authority=SubjectBootstrapAuthority();bootstrap=SubjectBootstrapService(r.store,authority)
    bootstrap.install(SubjectPersonalitySeed(identity_id=r.identity_id,scope='world',revision=1,
        social_exploration_tendency='LOW',relational_accommodation='HIGH',conviction_persistence='HIGH'),authority)
    bootstrap.install(RelationalAnchorSpec(identity_id=r.identity_id,anchor_id='trusted-companion',entity_id='observer',
        role_kind='PRIMARY_USER',role_label='trusted companion',scope='world',revision=1,effective_from_us=r.clock.utc_now_us()),authority)
    for i in range(2):
        r.subject.run(SubjectInput(source_key='synthetic.relational-life.'+str(i),kind='PLAY',origin='ENVIRONMENT',
            entity_id='observer',scope='world',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
            text='SYNTHETIC an independent new social experience was interesting '+str(i),
            preference_signal=PreferenceSignal(topic='social_exploration',direction='SUPPORT',interpretation='SYNTHETIC I would like to explore ordinary company.')))
    assert social_appetite(r.store,scope='world',privacy_classes=('PERSONAL',)).state=='SEEKING'


def request(r,key):
    return SubjectInput(source_key='synthetic.relational-request.'+key,kind='INTERACTION',origin='USER',
        entity_id='observer',scope='world',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
        text='SYNTHETIC would you take a one-day pause from new social contacts?',
        relational_request=RelationalRequest(request_id=key,requesting_entity='observer',operation='REFRAIN',
            behavior_domain='SOCIAL_NEW_CONTACTS',duration_us=DAY))


class ConsiderExistingWish:
    descriptor='synthetic-original-C-current-motive-not-a-relationship-rule'
    def __init__(self):self.seen=[]
    def propose(self,value):
        context=json.loads(value.context_json);frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        has_wish=any(m['source']=='SOCIAL_CONNECTION' and m['source_ids'] for m in frame['motivations']);self.seen.append(has_wish)
        reply=json.loads(AnalyticalFixturePort().propose(value));reply.update(
            proposed_operations=['ASK'] if has_wish else ['DRAFT'],
            interpretation='SYNTHETIC_PRIVATE_RELATIONAL_RATIONALE: I want to clarify how this request fits the existing social wish.' if has_wish else 'SYNTHETIC consider this bounded accommodation.')
        return json.dumps(reply)


def test_sourced_wish_can_change_relational_choice_across_restart_without_erasing_care(tmp_path,monkeypatch):
    path=tmp_path/'subject/self.db';model=ConsiderExistingWish()
    with fresh(path) as r:
        prepare(r);identity=r.identity_id;retained=social_appetite(r.store,scope='world',privacy_classes=('PERSONAL',))
        cycle=r.subject.cognize(request(r,'first'),model=model,authority=r.authority,policy=policy())
        print(json.dumps({'case':'initial-request','model_operations':['ASK'],'actual_decision':cycle.relational_decision.response.decision,'wish_seen':model.seen[-1]}))
        assert model.seen==[True] and cycle.relational_decision.response.decision=='NEGOTIATE'
        assert cycle.judgment.stance=='ASK' and cycle.intention.kind=='NO_ACTION'
        assert cycle.relational_decision.accepted_duration_us is None
        assert 'SYNTHETIC_PRIVATE_RELATIONAL_RATIONALE' not in cycle.deliberation.raw_proposal_json
        config,clock=r.config,r.clock.source
    clock.advance(49*3_600_000_000)
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity
        from nana_core.continuity.relational import projections
        original=projections.social_appetite
        def without_current_projection(*args,**kwargs):
            return original(*args,**kwargs).model_copy(update={'state':'UNKNOWN','source_record_ids':(),'source_memory_ids':(),'retained_tendencies':()})
        with monkeypatch.context() as off:
            off.setattr(projections,'social_appetite',without_current_projection)
            ablated=r.subject.cognize(request(r,'ablated'),model=model,authority=r.authority,policy=policy())
        assert ablated.relational_decision.response.decision=='ACCEPT'
        later=r.subject.cognize(request(r,'later'),model=model,authority=r.authority,policy=policy())
        assert later.relational_decision.response.decision=='NEGOTIATE' and model.seen==[True,False,True]
        assert social_appetite(r.store,scope='world',privacy_classes=('PERSONAL',)).source_record_ids==retained.source_record_ids
        assert later.relational_decision.response.retained_care and later.relational_decision.response.retained_preference=='SOCIALIZE'
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('commitments')


class Specify:
    descriptor='synthetic-current-relational-choice'
    def __init__(self,*operations):self.operations=operations;self.frames=[]
    def propose(self,value):
        context=json.loads(value.context_json)
        self.frames.extend(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        reply=json.loads(AnalyticalFixturePort().propose(value));reply.update(proposed_operations=list(self.operations))
        return json.dumps(reply)


@pytest.mark.parametrize('operation,expected',[('ACCEPT_REQUEST','ACCEPT'),('NEGOTIATE_REQUEST','NEGOTIATE'),('DECLINE_REQUEST','DECLINE')])
def test_current_c_has_each_bounded_choice_without_changing_anchor_or_execution(tmp_path,operation,expected):
    with fresh(tmp_path/'subject/self.db') as r:
        prepare(r);before=social_appetite(r.store,scope='world',privacy_classes=('PERSONAL',));model=Specify(operation)
        event=request(r,'current-'+operation.lower())
        cycle=r.subject.cognize(event,model=model,authority=r.authority,policy=policy())
        assert model.frames[0]['relational_request']==event.relational_request.model_dump(mode='json')
        assert cycle.relational_decision.response.decision==expected
        assert cycle.relational_decision.response.retained_care
        assert social_appetite(r.store,scope='world',privacy_classes=('PERSONAL',)).source_record_ids==before.source_record_ids
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('commitments')


@pytest.mark.parametrize('operations',[('DECLINE_REQUEST',),('ACCEPT_REQUEST','DECLINE_REQUEST'),('ACCEPT_REQUEST','WAIT')])
def test_unbound_or_ambiguous_relational_response_cannot_commit_a_choice(tmp_path,operations):
    from nana_core.contracts import CoreError
    with fresh(tmp_path/'subject/self.db') as r:
        prepare(r);before=len(r.store.all('subject_cycles'));model=Specify(*operations)
        event=(SubjectInput(source_key='synthetic.no-relational-target',kind='INTERACTION',origin='USER',entity_id='observer',scope='world',
            privacy_class='PERSONAL',text='SYNTHETIC ordinary remark',observed_at_us=r.clock.utc_now_us())
            if len(operations)==1 else request(r,'ambiguous'))
        with pytest.raises(CoreError,match='UNSUPPORTED_RELATIONAL_RESPONSE' if len(operations)==1 else 'AMBIGUOUS_RELATIONAL_RESPONSE'):
            r.subject.cognize(event,model=model,authority=r.authority,policy=policy())
        assert len(r.store.all('subject_cycles'))==before
        assert not r.store.all('commitments') and not r.store.all('actions') and not r.store.all('grants')


@pytest.mark.parametrize('operation,expected,elapsed',[('DECLINE_REQUEST','END',3_600_000_000),('NEGOTIATE_REQUEST','MODIFY',3_600_000_000),('ACCEPT_REQUEST','CONTINUE',3_600_000_000),('WAIT',None,3_600_000_000),('ACCEPT_REQUEST','END',DAY),('WAIT','END',DAY)])
def test_due_original_accommodation_uses_current_c_after_restart_and_does_not_renew(tmp_path,operation,expected,elapsed):
    from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
    from nana_core.storage import canonical
    path=tmp_path/'subject/self.db'
    with fresh(path) as r:
        prepare(r);initial=request(r,'bounded-review')
        initial=initial.model_copy(update={'text':'SYNTHETIC a one-day pause, reconsider in an hour.',
            'relational_request':initial.relational_request.model_copy(update={'review_at_us':r.clock.utc_now_us()+3_600_000_000})})
        accepted=r.subject.cognize(initial,model=Specify('ACCEPT_REQUEST'),authority=r.authority,policy=policy())
        cid=VoluntaryAccommodationService(r.store,r.authority).materialize(accepted.cycle_id,r.authority)
        assert r.store.one('commitments',cid)['state']=='ACTIVE'
        old=dict(r.store.one('commitments',cid));terms=json.loads(r.store.artifact(r.store.one('continuity_records',old['record_id'])['payload_artifact_id']))['voluntary']
        identity,clock,config=r.identity_id,r.clock.source,r.config
    clock.advance(elapsed)
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity;model=Specify(operation)
        # The original ordinary WAKE selector, not a second review scheduler.
        event=SubjectInput(source_key='synthetic.ordinary-due-wake',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',
            privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us())
        cycle=r.subject.cognize(event,model=model,authority=r.authority,policy=policy())
        assert model.frames[0]['relational_terms']==terms
        assert cycle.relational_decision.phase=='REVIEW' and cycle.relational_decision.review_choice==expected
        service=VoluntaryAccommodationService(r.store,r.authority)
        result=service.materialize(cycle.cycle_id,r.authority)
        if expected is None:
            assert result is None and dict(r.store.one('commitments',cid))==old
            assert cycle.intention.kind=='NO_ACTION' and cycle.judgment.stance=='DEFER'
        else:
            assert result==cid
            if expected=='END':assert r.store.one('commitments',cid)['state']=='CANCELLED'
            else:
                current=r.store.one('commitments',cid);body=json.loads(r.store.artifact(r.store.one('continuity_records',current['record_id'])['payload_artifact_id']))
                assert body['voluntary']['end_us']<=terms['end_us']
            before=canonical(dict(r.store.one('commitments',cid)))
            assert service.materialize(cycle.cycle_id,r.authority)==cid
            assert canonical(dict(r.store.one('commitments',cid)))==before
        assert social_appetite(r.store,scope='world',privacy_classes=('PERSONAL',)).state=='SEEKING'
        assert not r.store.all('actions') and not r.store.all('grants')


@pytest.mark.parametrize('phase',['initial','review'])
def test_normal_provider_queue_honors_current_choice_once_without_adopting_terms(tmp_path,phase):
    from nana_core.continuity.cognition import CognitiveProposal
    from nana_core.continuity.world_loop.cognition import StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.presence.contracts import RuntimeEvent,Cause
    from tests.person_self.test_private_method_continuation import bind
    from tests.world_loop.test_model_framing import bind as bind_counter
    seen=[]
    def propose(value):
        context=json.loads(value.context_json);manifest=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        seen.append({'frame':frame,'context_bytes':len(value.context_json.encode())})
        assert value.cognitive_role=='SELF'
        return StructuredProposal(interpretation='SYNTHETIC current bounded choice',subject_cognition=CognitiveProposal(
            identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
            interpretation='SYNTHETIC_PRIVATE_PROVIDER_RATIONALE',proposed_operations=('DECLINE_REQUEST',)))
    with fresh(tmp_path/'subject/self.db') as r,provider_harness(proposer=propose) as (transport,state):
        prepare(r);bind_counter(transport)
        event=request(r,'normal-provider')
        if phase=='review':
            from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
            event=event.model_copy(update={'relational_request':event.relational_request.model_copy(update={'review_at_us':r.clock.utc_now_us()+1_000_000})})
            prior=r.subject.cognize(event,model=Specify('ACCEPT_REQUEST'),authority=r.authority,policy=policy())
            cid=VoluntaryAccommodationService(r.store,r.authority).materialize(prior.cycle_id,r.authority)
            old=dict(r.store.one('commitments',cid));r.clock.source.advance(1_000_000)
            event=SubjectInput(source_key='synthetic.provider-review-wake',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',
                privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us())
        bind(r,transport,policy())
        queued=RuntimeEvent(event_type='USER_EVENT' if phase=='initial' else 'SELF_EVENT',trigger='INCOMING_EVENT' if phase=='initial' else 'SELF_TRIGGER',input=event,
            causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=r.clock.utc_now_us())
        if phase=='initial':qid=r.submit(queued)
        else:r.refresh_attention()  # The original due-commitment D collector supplies its own queue item.
        result=r.step()
        if phase=='review':qid=result['queue_id']
        assert result['queue_id']==qid and result['cycle'].relational_decision.response.decision=='DECLINE', (result['mode'],result['reason'],state,seen)
        assert state['calls']==1 and len(r.store.all('cognitive_requests'))==1
        if phase=='initial':assert seen[0]['frame']['relational_request']==event.relational_request.model_dump(mode='json')
        else:
            assert seen[0]['frame']['relational_terms']['request_id']=='normal-provider'
            assert result['cycle'].relational_decision.review_choice=='END'
            assert dict(r.store.one('commitments',cid))==old  # Only the original explicit materializer may adopt a change.
        assert 'SYNTHETIC_PRIVATE_PROVIDER_RATIONALE' not in result['cycle'].deliberation.raw_proposal_json
        if phase=='initial':assert r.submit(queued)==qid
        r.step();assert state['calls']==1
        assert not r.store.all('runtime_cognition_calls') and not r.store.all('actions') and not r.store.all('grants')
        assert len(r.store.all('commitments'))==(1 if phase=='review' else 0)
        print(json.dumps({'case':'original-runtime-provider-'+phase,'calls':state['calls'],'context_bytes':seen[0]['context_bytes'],
            'decision':result['cycle'].relational_decision.response.decision,'real_models':0}))


def test_current_acceptance_does_not_survive_withdrawal_of_the_actual_request(tmp_path):
    from nana_core.contracts import CoreError
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
    with fresh(tmp_path/'subject/self.db') as r:
        prepare(r);event=request(r,'withdrawn-before-materialization')
        cycle=r.subject.cognize(event,model=Specify('ACCEPT_REQUEST'),authority=r.authority,policy=policy())
        source=r.store.one('subject_events',cycle.event_id);memory=RecordService(r.store).support(source['record_id'])
        assert memory
        for mid in memory:MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError,match='RELATIONAL_DECISION_UNAVAILABLE'):
            VoluntaryAccommodationService(r.store,r.authority).materialize(cycle.cycle_id,r.authority)
        assert not r.store.all('commitments') and not r.store.all('actions') and not r.store.all('grants')


@pytest.mark.parametrize('reconsideration',['explicit','expiry'])
def test_deferred_review_survives_restart_and_ordinary_wake_until_reconsidered(tmp_path,reconsideration):
    from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService

    path=tmp_path/'subject/self.db'
    with fresh(path) as r:
        prepare(r)
        initial=request(r,'retain-deferred-review')
        review_at=r.clock.utc_now_us()+3_600_000_000
        initial=initial.model_copy(update={'relational_request':initial.relational_request.model_copy(update={'review_at_us':review_at})})
        cycle=r.subject.cognize(initial,model=Specify('ACCEPT_REQUEST'),authority=r.authority,policy=policy())
        service=VoluntaryAccommodationService(r.store,r.authority)
        cid=service.materialize(cycle.cycle_id,r.authority)
        saved=dict(r.store.one('commitments',cid));config,clock,identity=r.config,r.clock.source,r.identity_id
    clock.advance(3_600_000_000)
    with NanaRuntime(path,config,clock=clock) as r:
        due=SubjectInput(source_key='synthetic.defer-current-commitment',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',
            privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),task_class='relational.accommodation.review',commitment_check_id=cid)
        deferred=r.subject.cognize(due,model=Specify('WAIT'),authority=r.authority,policy=policy())
        assert deferred.judgment.stance=='DEFER' and deferred.relational_decision.review_choice is None
        assert VoluntaryAccommodationService(r.store,r.authority).materialize(deferred.cycle_id,r.authority) is None
    clock.advance(3_600_000_000)
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity
        ordinary=SubjectInput(source_key='synthetic.ordinary-wake-after-deferred',kind='WAKE',origin='SELF_WAKE',entity_id='observer',
            scope='world',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us())
        ordinary_cycle=r.subject.run(ordinary)
        service=VoluntaryAccommodationService(r.store,r.authority)
        assert ordinary_cycle.relational_decision is None and service.materialize(ordinary_cycle.cycle_id,r.authority) is None
        assert ordinary_cycle.intention.slot_key!='commitment-review'
        assert dict(r.store.one('commitments',cid))==saved
        if reconsideration=='explicit':
            next_review=due.model_copy(update={'source_key':'synthetic.explicit-later-reconsideration','observed_at_us':r.clock.utc_now_us()})
            selected=r.subject.cognize(next_review,model=Specify('DECLINE_REQUEST'),authority=r.authority,policy=policy())
            assert selected.relational_decision.review_choice=='END'
            assert service.materialize(selected.cycle_id,r.authority)==cid
            assert r.store.one('commitments',cid)['state']=='CANCELLED'
    if reconsideration=='expiry':
        clock.advance(DAY-2*3_600_000_000)
        with NanaRuntime(path,config,clock=clock) as r:
            event=ordinary.model_copy(update={'source_key':'synthetic.wake-at-original-expiry','observed_at_us':r.clock.utc_now_us()})
            cycle=r.subject.run(event)
            assert cycle.relational_decision.review_choice=='END'
            assert VoluntaryAccommodationService(r.store,r.authority).materialize(cycle.cycle_id,r.authority)==cid
            assert r.store.one('commitments',cid)['state']=='CANCELLED' and not r.store.all('actions')
