"""Source-backed media choices use original C; they confer no action grant."""
import json

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.world_loop.cognition import CognitionBudget, CognitionSession, StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.perception import PerceptionService, PublicMediaSource
from tests.world_loop.helpers import providers


def picture():
    from io import BytesIO
    from PIL import Image
    output = BytesIO()
    Image.new('RGB', (4, 4), (20, 80, 160)).save(output, format='PNG')
    return output.getvalue()


def test_original_c_can_leave_retrieved_image_unselected(app):
    r = app.runtime
    now = r.clock.utc_now_us()
    source = PublicMediaSource(source_id='synthetic-picture', modality='IMAGE', origin='SYNTHETIC',
                               event_time_us=now, observed_time_us=now)
    mid, _ = PerceptionService(r.store, providers(), app.policy).ingest(
        picture(), source, entity_id='project-user', scope='project-work')
    seen = []
    def propose(request):
        context = json.loads(request.context_json)
        block = next(b for b in context['blocks'] if b['kind'] == 'MEDIA_CANDIDATES')
        offered = json.loads(block['data_json'])['candidates']
        seen.extend(offered)
        identity = context['manifest']
        return StructuredProposal(interpretation='synthetic choice', subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'], identity_revision=identity['identity_revision'],
            interpretation='wait without selecting an image', proposed_operations=('WAIT',)))
    event = SubjectInput(domain='DEVELOPMENT_MATERIAL', source_key='development.media-choice',
        kind='WAKE', origin='SELF_WAKE', entity_id='project-user', scope='project-work',
        privacy_class='PUBLIC', observed_at_us=now)
    with provider_harness(proposer=propose) as (transport, state):
        session = CognitionSession(r, transport, app.policy)
        result = r.subject.cognize(event, model=session.subject_port(privacy_class='PUBLIC',
            budget=CognitionBudget(input_tokens=32768)), authority=r.authority, policy=app.policy)
    assert len(seen) == 1 and seen[0]['source_memory_id'] == mid
    assert result.realization_target is None
    assert state['calls'] == 1 and not r.store.all('actions') and not r.store.all('grants')
    MemoryService(r.store, r.authority).forget(mid, r.authority)
    with pytest.raises(CoreError):
        MemoryService(r.store).read(mid)


def test_proposal_rejects_unadvertised_or_uncited_media():
    from types import SimpleNamespace
    from nana_core.continuity.cognition import validate_cognitive_proposal
    media = dict(kind='image', source_memory_id='m1', content_sha256='a'*64, reference='image')
    block = SimpleNamespace(kind='MEDIA_CANDIDATES', source_memory_ids=('m1',),
                            data_json=json.dumps({'candidates': [dict(schema_version=1, **media)]}))
    context = SimpleNamespace(manifest=SimpleNamespace(identity_id='nana', identity_revision=1), blocks=(block,))
    base = dict(identity_id='nana', identity_revision=1, interpretation='consider', proposed_operations=('WAIT',))
    valid = CognitiveProposal(**base, memory_refs=('m1',), selected_media=media)
    validate_cognitive_proposal(valid, context)
    assert 'selected_media' not in CognitiveProposal(**base).model_dump(mode='json')
    with pytest.raises(CoreError, match='UNSUPPORTED_COGNITIVE_MEDIA_SELECTION'):
        validate_cognitive_proposal(CognitiveProposal(**base, selected_media=media), context)
    forged = dict(media, content_sha256='b'*64)
    with pytest.raises(CoreError, match='UNSUPPORTED_COGNITIVE_MEDIA_SELECTION'):
        validate_cognitive_proposal(CognitiveProposal(**base, memory_refs=('m1',), selected_media=forged), context)


@pytest.mark.parametrize('scenario', ['ack', 'verified', 'lost-ack', 'revoked', 'no-grant', 'during-login', 'superseded', 'superseded-during-login'])
def test_selected_image_binds_original_endorsed_contact_and_withdraws(app, scenario):
    from nana_core.continuity.autonomy.contracts import RealizationTarget
    from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.subject.opportunities import ConcernCue

    r = app.runtime
    now = r.clock.utc_now_us()
    source = PublicMediaSource(source_id='choice-picture', modality='IMAGE', origin='SYNTHETIC',
                               event_time_us=now, observed_time_us=now)
    mid, observation_id = PerceptionService(r.store, providers(), app.policy).ingest(
        picture(), source, entity_id='project-user', scope='project-work')
    memory = MemoryService(r.store)
    cue = ConcernCue(cue_kind='OPPORTUNITY', motivation_source='RELATIONSHIP', topic_key='qq-image-choice',
                     possible_behaviors=('SOCIALIZE',), availability='AVAILABLE')
    evidence = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.qq',
        source_reference='media-choice', source_kind='USER_STATEMENT'), text=cue.model_dump_json(),
        privacy_class='PROJECT', observed_time_us=now))
    cue_id = memory.add(MemoryCandidate(entity_id='project-user', scope='project-work', memory_type=MemoryType.SEMANTIC,
        epistemic_kind='STATEMENT', source_evidence_id=evidence, text=cue.model_dump_json(),
        predicate_key='concern.open.qq-image-choice'))
    def propose(request):
        context = json.loads(request.context_json)
        block = next(b for b in context['blocks'] if b['kind'] == 'MEDIA_CANDIDATES')
        media = json.loads(block['data_json'])['candidates'][0]
        identity = context['manifest']
        return StructuredProposal(interpretation='synthetic contact', subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'], identity_revision=identity['identity_revision'],
            interpretation='consider sharing', proposed_operations=('DRAFT',), preferred_behavior='SOCIALIZE',
            memory_refs=(mid,), selected_media=media))
    target = RealizationTarget(capability='world.contact', operation='CONTACT',
                               resource='project://qq/private/43', resource_class='ORDINARY')
    event = SubjectInput(source_key='synthetic.qq.image-choice', kind='INTERACTION', origin='USER',
        entity_id='project-user', scope='project-work', observed_at_us=now, text='Synthetic contact opportunity',
        privacy_class='PROJECT', source_memory_ids=(cue_id,), realization_target=target)
    with provider_harness(proposer=propose) as (transport, state):
        session = CognitionSession(r, transport, app.policy)
        cycle = r.subject.cognize(event, model=session.subject_port(privacy_class='PROJECT',
            budget=CognitionBudget(input_tokens=32768)), authority=r.authority, policy=app.policy)
    assert state['calls'] == 1 and cycle.evaluation.normative == 'ENDORSED'
    assert cycle.realization_target.resource == target.resource
    assert cycle.realization_target.media.source_memory_id == mid
    assert not r.store.all('actions') and not r.store.all('grants')
    from nana_core.nanalink.media import MediaCache
    from tests.living_release_v4.test_platform_bridge import equipped, propose
    from tests.nanalink.test_onebot_network import network
    from nana_core.life.platform_bridge import OneBotHTTPTransport
    from nana_core.life.platform_runtime import SecretReference
    import tempfile
    with tempfile.TemporaryDirectory() as directory, network() as (net, platform, resolver, loop):
        cache = MediaCache(directory, source_current=lambda _: True)
        cache.put([picture()], source_ref=mid)
        connection = OneBotHTTPTransport(net["endpoint"], "42", credential=SecretReference(resolver, "core.test"),
                                         authorized=True, realm="SYNTHETIC_LOOPBACK")
        service, port = equipped(r.store, r.authority, connection, grant=scenario != 'no-grant')
        port.media_cache = cache
        action = propose(service, port, cycle)
        if scenario == 'during-login':
            login = connection.account
            def revoke_during_login():
                value = login()
                MemoryService(r.store, r.authority).forget(mid, r.authority)
                return value
            connection.account = revoke_during_login
            try:
                service.dispatch(cycle.intention_id, action, expected_revision=1)
            except CoreError:
                pass
            assert not platform['sent']
        elif scenario in {'superseded', 'superseded-during-login'}:
            records=RecordService(r.store);original=records.read(observation_id);support=records.support(observation_id)
            def supersede():
                with r.store.transaction('synthetic.image_observation_revised') as tx:
                    records.create(tx,kind='MEDIA_OBSERVATION',scope='project-work',payload=original['payload'],
                                   memories=support,supersedes=observation_id,target_id=mid)
                assert records.current_support(observation_id)
            if scenario=='superseded':
                supersede()
            else:
                login=connection.account
                def supersede_during_login():
                    value=login();supersede();return value
                connection.account=supersede_during_login
            result=service.dispatch(cycle.intention_id, action, expected_revision=1)
            assert result=='UNKNOWN'
            assert service.dispatch(cycle.intention_id, action, expected_revision=1)=='UNKNOWN'
            assert not platform['sent']
        elif scenario == 'revoked':
            MemoryService(r.store, r.authority).forget(mid, r.authority)
            with pytest.raises(CoreError):
                service.dispatch(cycle.intention_id, action, expected_revision=1)
            assert not platform['sent']
        elif scenario == 'no-grant':
            with pytest.raises(CoreError, match='AUTH_REQUIRED'):
                service.dispatch(cycle.intention_id, action, expected_revision=1)
            assert not platform['sent']
        else:
            platform['lose_ack'] = scenario == 'lost-ack'
            platform['image_readback'] = scenario == 'verified'
            expected = 'SUCCEEDED' if scenario == 'verified' else 'UNKNOWN'
            assert service.dispatch(cycle.intention_id, action, expected_revision=1) == expected
            assert len(platform['sent']) == 1
            assert platform['sent'][0]['message'][1]['type'] == 'image'
            assert service.dispatch(cycle.intention_id, action, expected_revision=1) == expected
            assert len(platform['sent']) == 1
            if scenario == 'lost-ack':
                from nana_core.life.platform_bridge import QQCapabilityPort, QQGovernedDelivery
                fresh_connection = OneBotHTTPTransport(net['endpoint'], '42',
                    credential=SecretReference(resolver, 'core.test'), authorized=True, realm='SYNTHETIC_LOOPBACK')
                fresh_port = QQCapabilityPort(r.store, fresh_connection, {target.resource: ('private', '43')},
                    host_enabled=True, delivery=port.delivery, media_cache=cache)
                recovered = QQGovernedDelivery(fresh_port, r.authority, host_enabled=True)
                assert recovered.kernel.recover()[action] == 'UNKNOWN'
                assert recovered.kernel.run(action) == 'UNKNOWN'
                assert fresh_connection.calls == 0 and len(platform['sent']) == 1
        cache.close()
    if scenario not in {'revoked', 'during-login'}:
        MemoryService(r.store, r.authority).forget(mid, r.authority)
    assert not RecordService(r.store).current_support(cycle.record_id)


def test_unverified_media_descriptor_cannot_be_offered(app):
    from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
    r = app.runtime
    now = r.clock.utc_now_us()
    memory = MemoryService(r.store)
    text = json.dumps({'source': {'source_id': 'fake', 'modality': 'IMAGE'},
        'source_byte_digest': 'a' * 64, 'decoded': {'modality': 'IMAGE', 'decoded': True}})
    eid = memory.capture(EvidenceInput(provenance=Provenance(domain='SYNTHETIC_ONLY',
        source_namespace='synthetic.public-media', source_reference='fake', source_kind='DIRECT_OBSERVATION'),
        text=text, privacy_class='PUBLIC', observed_time_us=now))
    mid = memory.add(MemoryCandidate(entity_id='project-user', scope='project-work', memory_type=MemoryType.EPISODIC,
        epistemic_kind='OBSERVATION', source_evidence_id=eid, text=text))
    def propose(request):
        context = json.loads(request.context_json)
        assert not any(b['kind'] == 'MEDIA_CANDIDATES' for b in context['blocks'])
        identity = context['manifest']
        return StructuredProposal(interpretation='synthetic wait', subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'], identity_revision=identity['identity_revision'],
            interpretation='wait', proposed_operations=('WAIT',)))
    event = SubjectInput(source_key='synthetic.fake-image', kind='WAKE', origin='SELF_WAKE',
        entity_id='project-user', scope='project-work', observed_at_us=now, privacy_class='PUBLIC', source_memory_ids=(mid,))
    with provider_harness(proposer=propose) as (transport, state):
        session = CognitionSession(r, transport, app.policy)
        r.subject.cognize(event, model=session.subject_port(privacy_class='PUBLIC'), authority=r.authority, policy=app.policy)
    assert state['calls'] == 1 and not r.store.all('actions')


def test_host_cannot_impose_attachment_without_original_c(tmp_path):
    from nana_core.continuity.autonomy.contracts import MediaSelection
    from tests.living_release_v4.test_platform_bridge import TARGET, candidate
    from nana_core.continuity import ContinuityStore
    from nana_core.actions import OperatorAuthority
    from nana_core.presence.authority import VirtualClock
    media = MediaSelection(kind='image', source_memory_id='forged', content_sha256='a' * 64, reference='forged')
    with ContinuityStore(tmp_path/'state.db', VirtualClock(), schema_target=13) as store:
        with pytest.raises(CoreError, match='SUBJECT_MEDIA_SELECTION_BINDING_REQUIRED'):
            candidate(store, OperatorAuthority(), target=TARGET.model_copy(update={'media': media}))


def test_cached_image_must_match_current_original_observation(app, tmp_path):
    from nana_core.nanalink.media import MediaCache
    from nana_core.nanalink.media_candidates import candidate, resolve_image
    r = app.runtime
    now = r.clock.utc_now_us()
    source = PublicMediaSource(source_id='cached-picture', modality='IMAGE', origin='SYNTHETIC',
                               event_time_us=now, observed_time_us=now)
    data = picture()
    mid, _ = PerceptionService(r.store, providers(), app.policy).ingest(
        data, source, entity_id='project-user', scope='project-work')
    source_row = MemoryService(r.store).read(mid)
    selection = candidate(source_row)
    assert candidate({**source_row, 'privacy_class': 'PERSONAL'}) is None
    cache = MediaCache(tmp_path/'cache', source_current=lambda _: True)
    with pytest.raises(CoreError, match='MEDIA_CACHE_MISS'):
        resolve_image(r.store, cache, selection)
    cache.put([data], source_ref=mid)
    assert resolve_image(r.store, cache, selection) == data
    path, _ = cache.items[selection.content_sha256]
    path.write_bytes(b'x' * len(data))
    with pytest.raises(CoreError, match='MEDIA_CACHE_CONTENT_MISMATCH'):
        resolve_image(r.store, cache, selection)
    path.write_bytes(data)
    with pytest.raises(CoreError, match='MEDIA_SEND_BYTE_BOUND'):
        resolve_image(r.store, cache, selection, max_bytes=1)
    MemoryService(r.store, r.authority).forget(mid, r.authority)
    with pytest.raises(CoreError):
        resolve_image(r.store, cache, selection)
    cache.close()


@pytest.mark.parametrize('explicit_source', [False, True])
def test_retrieved_image_does_not_cross_entity_boundary(app, explicit_source):
    r = app.runtime
    now = r.clock.utc_now_us()
    MemoryService(r.store).entity('another-person', 'PERSON')
    source = PublicMediaSource(source_id='other-picture', modality='IMAGE', origin='SYNTHETIC',
                               event_time_us=now, observed_time_us=now)
    mid, _ = PerceptionService(r.store, providers(), app.policy).ingest(
        picture(), source, entity_id='another-person', scope='project-work')
    def propose(request):
        context = json.loads(request.context_json)
        assert not any(b['kind'] == 'MEDIA_CANDIDATES' for b in context['blocks'])
        identity = context['manifest']
        return StructuredProposal(interpretation='synthetic wait', subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'], identity_revision=identity['identity_revision'],
            interpretation='wait', proposed_operations=('WAIT',)))
    event = SubjectInput(source_key='synthetic.no-cross-entity-image', kind='WAKE', origin='SELF_WAKE',
        entity_id='project-user', scope='project-work', observed_at_us=now, privacy_class='PUBLIC',
        source_memory_ids=(mid,) if explicit_source else ())
    with provider_harness(proposer=propose) as (transport, state):
        session = CognitionSession(r, transport, app.policy)
        if explicit_source:
            with pytest.raises(CoreError, match='CONTEXT_REQUIRED_SOURCE_DENIED'):
                r.subject.cognize(event, model=session.subject_port(privacy_class='PUBLIC'), authority=r.authority, policy=app.policy)
        else:
            r.subject.cognize(event, model=session.subject_port(privacy_class='PUBLIC'), authority=r.authority, policy=app.policy)
    assert state['calls'] == (0 if explicit_source else 1) and not r.store.all('actions')
