"""Independent scope qualification, not automatic promotion of the old16 skill."""
import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.records import RecordService
from nana_core.continuity.retrieval_growth import qualified_method, case_for
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.memory_notes import save
from nana_core.presence.authority import VirtualClock
from .conftest import initialize
from .test_retrieval_growth import notes, advance, selected
from .test_dialogue import relay
from .test_note_recall import supplied_notes, render_from_supplied_sources


def initialize_expanded(home):
    initialize(home, active=0)
    config = load_config(home)
    # Trusted explicit host setting. Missing/old config remains the16-note scope.
    changed = type(config).model_validate({**config.model_dump(), 'revision': config.revision + 1,
                                          'note_retrieval_notes_limit': 32})
    update_config(home, changed, expected_revision=config.revision)


def fillers(app, count=17):
    return [save(app, text=f'SYNTHETIC unrelated filler item{i:03d}', privacy='PROJECT',
                 request_id=f'filler-{i}')['memory_id'] for i in range(count)]


def test_expanded_original_g_requires_new_qualification_and_later_use_survives_restart(tmp_path):
    home = tmp_path / 'home'
    initialize_expanded(home)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        train = notes(app)
        fillers(app)
        evaluator = app.runtime.work.note_retrieval_growth.evaluator
        with pytest.raises(CoreError, match='NOTE_STRATEGY_SCOPE_BOUND'):
            evaluator.snapshot('project-work')  # Legacy qualification stays bounded.
        assert selected(app) is None
        result = app.runtime.work.note_retrieval_growth.slice('project-work')
        assert result['note_retrieval'] == 'OFFERED_TO_C'
        assert not app.runtime.store.all('lessons')
        identity = app.runtime.identity_id
    with LifeApplication(home, clock=clock) as app:
        advance(app)
        lesson = selected(app)
        assert lesson and lesson[1] == 'UNICODE_WORDS'
        rule = RecordService(app.runtime.store).read(lesson[0])['payload']['rule']
        trial = RecordService(app.runtime.store).read(rule['trial_record_id'])['payload']
        for stage in ('EVALUATE', 'TRANSFER'):
            assert trial['results'][stage]['qualification_scope']['max_notes'] == 32
            assert trial['results'][stage]['evaluator'] == 'CORE_NOTE_RETRIEVAL_V2'
            assert trial['results'][stage]['all_passed']
        job = app.runtime.store.db.execute("SELECT record_id FROM jobs WHERE work_kind='LEARNING'").fetchone()
        body = RecordService(app.runtime.store).read(job[0])['payload']
        assert body['practice_competition']['selection_scope'] == 'PRACTICE_ONLY_NOT_QUALIFICATION'
        later = notes(app, ('ＡＬＴＡＩＲ',), prefix='expanded-unseen')[0]
    with relay(home, 'CHAT', renderer=render_from_supplied_sources,
               remote_model_id='expanded-fixture-resource-b', recall_query_terms=('ALTAIR',)) as (router, requests):
        with LifeApplication(home, clock=clock, router=router) as app:
            app.pause()
            assert app.runtime.identity_id == identity
            reply = app.chat('SYNTHETIC different later recall', privacy='PROJECT', message_id='expanded-later')
            assert [n['memory_id'] for n in supplied_notes(requests[-1])] == [later], reply
            app.forget(train[0])
            assert selected(app) is None
            app.chat('SYNTHETIC recall after source withdrawal', privacy='PROJECT', message_id='expanded-withdrawn')
            assert supplied_notes(requests[-1]) == []
            assert len(requests) == 4


def test_expanded_scope_rejects_33_notes_and_cannot_forge_legacy_qualification(tmp_path):
    home = tmp_path / 'home'
    initialize_expanded(home)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        fillers(app, 30)
        growth = app.runtime.work.note_retrieval_growth
        assert growth.slice('project-work')['reason'] == 'NOTE_STRATEGY_SCOPE_BOUND'
        assert not app.runtime.store.all('experiences') and not app.runtime.store.all('lessons')
        assert not app.runtime.store.all('cognitive_requests')


def test_old_host_scope_stays_16_and_unknown_capacity_is_not_a_false_counterexample(tmp_path):
    home = tmp_path / 'home'
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        growth.slice('project-work')
        advance(app)
        original = selected(app)
        fillers(app)
        assert growth.slice('project-work')['reason'] == 'NOTE_STRATEGY_SCOPE_BOUND'
        assert selected(app) == original
        assert load_config(home).note_retrieval_notes_limit == 16
        assert 'note_retrieval_notes_limit' not in load_config(home).model_dump(mode='json')


def test_original_16_lesson_is_not_promoted_without_new_practice_and_independent_splits(tmp_path):
    from nana_core.continuity.retrieval_growth import qualified_note_limit
    home = tmp_path / 'home'
    initialize(home, active=0)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        notes(app)
        app.runtime.work.note_retrieval_growth.slice('project-work'); advance(app)
        original = selected(app)
        assert qualified_note_limit(app.runtime.store, original) == 16
        fillers(app)
    config = load_config(home)
    update_config(home, type(config).model_validate({**config.model_dump(),
        'revision': config.revision + 1, 'note_retrieval_notes_limit': 32}), expected_revision=config.revision)
    with LifeApplication(home, clock=clock) as app:
        assert selected(app) == original
        assert qualified_note_limit(app.runtime.store, selected(app)) == 16
        assert app.runtime.work.note_retrieval_growth.slice('project-work')['note_retrieval'] == 'OFFERED_TO_C'
        assert selected(app) == original  # Merely offering the candidate does not widen it.
        advance(app)
        assert selected(app) != original and qualified_note_limit(app.runtime.store, selected(app)) == 32
        evaluator = app.runtime.work.note_retrieval_growth.evaluator
        snapshot = evaluator.snapshot('project-work', max_notes=32)
        current = case_for(snapshot, ('ORION',), 'new')
        forged = current.model_copy(update={'data': {**current.data, 'kind': 'CORE_NOTE_RETRIEVAL_V1'}})
        with pytest.raises(CoreError, match='NOTE_STRATEGY_MIXED_EVALUATION'):
            evaluator.evaluate('JOIN', (current, forged))


def test_scope32_qualification_and_future_context_survive_original_b8_transfer(tmp_path):
    from uuid import uuid4
    import subprocess
    from nana_core.actions import OperatorAuthority
    from nana_core.continuity import ContinuityStore
    from nana_core.continuity.context import ContextAssembler, ContextPolicy, ContextRequest
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.portable import SubjectPackageService, PortableTransferAuthority, verify_package
    home = tmp_path / 'home'
    initialize_expanded(home)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        train = notes(app); fillers(app)
        app.runtime.work.note_retrieval_growth.slice('project-work'); advance(app)
        assert selected(app)
        later = notes(app, ('ＡＬＴＡＩＲ',), prefix='portable-later')[0]
        identity = app.runtime.identity_id
    target = str(uuid4()); authority = PortableTransferAuthority()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    with ContinuityStore(home / 'subject/self.db', clock, schema_target=13) as source:
        package = SubjectPackageService(source, authority).export(tmp_path / 'scope32.nana',
            destination_id=target, source_commit=revision, authority=authority)
        with pytest.raises(CoreError, match='SOURCE_RETIRED'):
            MemoryService(source).entity('blocked-old-writer', 'PERSON')
    manifest, _ = verify_package(package['path'], expected_sha256=package['sha256'])
    destination_root = tmp_path / 'destination'
    controller = PortableTransferAuthority(destination_id=target, destination_root=destination_root)
    path = SubjectPackageService.import_quarantined(package['path'], destination_root,
        expected_sha256=package['sha256'], destination_id=target, authority=controller)
    with ContinuityStore(path, clock, schema_target=13) as restored:
        SubjectPackageService(restored, controller).activate(transfer_id=manifest.transfer_id,
            destination_id=target, authority=controller)
        operator = OperatorAuthority()
        assert restored.identity['identity_id'] == identity and not restored.all('grants')
        assert qualified_method(restored, operator, 'project-user', 'project-work', ('PROJECT',))
        assembler = ContextAssembler(restored, operator)
        policy = ContextPolicy(policy_id='scope32.transfer', allowed_scopes=('project-work',), readable_privacy=('PROJECT',))
        request = ContextRequest(entity_id='project-user', scopes=('project-work',), task_class='world.social',
            task='SYNTHETIC independent later lookup after transfer', task_privacy_class='PROJECT',
            query_terms=('ALTAIR',), max_input_tokens=8192, output_reserve_tokens=1024)
        result = assembler.assemble(request, policy, pinned_only=True, conversation_topic='daily')
        assembler.validate(result, request, policy)
        assert any(later in b.source_memory_ids for b in result.blocks if b.kind == 'MEMORY')
        MemoryService(restored, operator).forget(train[0], operator)
        assert qualified_method(restored, operator, 'project-user', 'project-work', ('PROJECT',)) is None
        assert not restored.db.execute('PRAGMA foreign_key_check').fetchall()
