import json

import pytest

from nana_core.continuity.context import ContextAssembler, ContextPolicy, ContextRequest
from nana_core.continuity.subject import SubjectLoop
from nana_core.continuity.subject.projections import project_self
from nana_core.contracts import CoreError
from .test_subject_loop import event


def test_relationship_style_context_filter_and_identity(cognitive):
    store, memory, authority = cognitive
    loop = SubjectLoop(store, scopes=('life',), privacy_classes=('PUBLIC','PROJECT','PERSONAL','SECRET'))
    identity = store.identity.copy()
    for i, kind in enumerate(('SHARED_HISTORY', 'SHARED_PROJECT', 'SHARED_JOKE')):
        loop.run(event(store, f'social-{i}', relationship_kind=kind))
    memory.entity('synthetic-stranger', 'PERSON')
    familiar, personality, relation = project_self(store, entity_id='synthetic-sister', scope='life', privacy_classes=('PERSONAL',))
    _, other, _ = project_self(store, entity_id='synthetic-stranger', scope='life', privacy_classes=('PERSONAL',))
    assert relation['interaction_style'] == 'WARM_PLAYFUL'
    assert personality.interaction_style != other.interaction_style
    loop.run(event(store, 'disagreement', relationship_kind='CONFLICT'))
    _, after, _ = project_self(store, entity_id='synthetic-sister', scope='life', privacy_classes=('PERSONAL',))
    assert after.interaction_style == 'REPAIR_FIRST'
    loop.run(event(store, 'repair', relationship_kind='REPAIR'))
    # Explicit times order events, not random UUID tie breaking. Advance clock
    # below before further relationship changes in real source adapters.
    loop.run(event(store, 'secret', text='SYNTHETIC-HIDDEN-PERSONA', privacy_class='SECRET', relationship_kind='BOUNDARY'))
    assembler = ContextAssembler(store, authority)
    request = ContextRequest(entity_id='synthetic-sister', scopes=('life',), task_class='discussion',
        task='Discuss a synthetic project', max_input_tokens=40000)
    policy = ContextPolicy(policy_id='local', allowed_scopes=('life',), readable_privacy=('PUBLIC','PROJECT','PERSONAL'))
    context = assembler.assemble(request, policy)
    assert any(b.kind == 'PERSISTENT_SELF' for b in context.blocks)
    assert 'SYNTHETIC-HIDDEN-PERSONA' not in context.model_dump_json()
    assert store.identity == identity
    assert familiar.derived and familiar.snapshot_policy == 'AUDIT_ONLY_REBUILD_FROM_SOURCES'


def test_project_constraint_and_reflection_not_invented(cognitive):
    store, memory, authority = cognitive
    from nana_core.continuity.contracts import MemoryCandidate, MemoryType
    from .conftest import evidence
    text = json.dumps({'allowed_methods':['verify_first']})
    mid = memory.add(MemoryCandidate(entity_id='synthetic-sister', scope='life',
        memory_type=MemoryType.PROJECT, epistemic_kind='STATEMENT', source_evidence_id=evidence(memory,'constraint',text), text=text))
    loop = SubjectLoop(store, scopes=('life',))
    result = loop.run(event(store, 'bad-method', proposed_method='skip_validation', constraint_memory_ids=(mid,)))
    assert result.judgment.stance == 'ALTERNATIVE' and result.judgment.selected_method == 'verify_first'
    assert result.intention.kind == 'DISAGREE' and result.barrier == 'SHADOW_BLOCKED'
    with pytest.raises(CoreError, match='EXPERIENCE_MISSING'):
        loop.reflect('invented-experience', authority=authority, apply=True)
    assert not store.all('subject_reflections') and not store.all('experiences')
    assert not any(store.all(t) for t in ('actions','attempts','grants','budgets'))


def test_preference_supersession_is_terminal(cognitive):
    from nana_core.continuity.subject import PreferenceSignal
    from nana_core.continuity.subject.growth import Growth
    store, memory, authority = cognitive
    loop = SubjectLoop(store, scopes=('life',))
    for topic in ('exploration', 'methodical_work'):
        for i in range(2):
            loop.run(event(store, f'{topic}-{i}', kind='OUTCOME', origin='ENVIRONMENT',
                preference_signal=PreferenceSignal(topic=topic,direction='SUPPORT',interpretation='Observed outcome supports this inclination')))
    growth = Growth(store)
    old, new = growth.assertions('life')
    growth.supersede(old['assertion_id'], new['assertion_id'], expected_revision=old['revision'])
    assert growth.assertions('life')[0]['state'] == 'SUPERSEDED'
    with pytest.raises(CoreError, match='SUPERSEDED_ASSERTION_CANNOT_SELF_REVIVE'):
        loop.run(event(store, 'revival', kind='OUTCOME', origin='ENVIRONMENT',
            preference_signal=PreferenceSignal(topic=old['topic'],direction='SUPPORT',interpretation='Cannot silently revive')))
    assert not store.all('actions')
