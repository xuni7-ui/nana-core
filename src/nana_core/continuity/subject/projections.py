"""Rebuild living/personality views. Never save these as an authority snapshot."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO
from ..revision import state_token
from ..records import RecordService
from .contracts import DAY_US, MAX_PENDING
from .growth import Growth
from .state import pending as pending_intentions, visible, revision


class Environment(DTO):
    capabilities: tuple[str, ...] = Field(default=(), max_length=32)
    devices: tuple[str, ...] = Field(default=(), max_length=32)
    platforms: tuple[str, ...] = Field(default=(), max_length=16)
    known_environment: tuple[str, ...] = Field(default=(), max_length=32)
    authority: Literal['NONE_IN_C'] = 'NONE_IN_C'


class PersonalityProfile(DTO):
    derived: Literal[True] = True
    initial_temperament: Literal['warm and precise'] = 'warm and precise'
    stable_preferences: tuple[str, ...]
    self_beliefs: tuple[str, ...]
    expression_tendencies: dict[str, str]
    interaction_style: str
    support_record_ids: tuple[str, ...]
    explanation: tuple[str, ...]


class LivingSelfState(DTO):
    schema_version: Literal[1] = 1
    derived: Literal[True] = True
    identity_id: str
    subject_revision: int
    state_token: str
    as_of_us: int
    presence: Literal['ACTIVE','FOCUSED','WATCHING','IDLE','RESTING','DEGRADED']
    current_activity: str
    attention_focus: str | None
    secondary_attention: tuple[str, ...]
    open_loops: tuple[str, ...]
    internal: dict[str, str]
    intentions: tuple[str, ...]
    goal_candidates: tuple[str, ...]
    commitments: tuple[str, ...]
    projects: tuple[str, ...]
    pending_reflections: tuple[str, ...]
    unresolved_topics: tuple[str, ...]
    environment: Environment
    confidence: Literal['SOURCE_BACKED','PARTIAL','UNKNOWN']
    source_record_ids: tuple[str, ...]
    source_memory_ids: tuple[str, ...]
    snapshot_policy: Literal['AUDIT_ONLY_REBUILD_FROM_SOURCES'] = 'AUDIT_ONLY_REBUILD_FROM_SOURCES'


def project_self(store, *, entity_id, scope, privacy_classes, environment=None):
    store.ensure_privacy_current()
    growth, records = Growth(store), RecordService(store)
    def is_visible(record_id):
        return visible(store,record_id,scope,privacy_classes)
    now, token = store.clock.utc_now_us(), state_token(store)
    pending = pending_intentions(store,scope,privacy_classes)
    concerns = pending[:MAX_PENDING]
    active_ids = tuple(r['intention_id'] for r in concerns)
    candidates = tuple(r['candidate_id'] for r in store.all('subject_goal_candidates')
        if r['state'] in {'PROPOSED','DEFERRED'} and r['intention_id'] in active_ids
        and is_visible(r['record_id']))
    commitments = tuple(r for r in store.all('commitments') if r['state'] in {'ADOPTED','ACTIVE'} and is_visible(r['record_id']))
    projects = tuple(r for r in store.all('projects') if r['state'] == 'ACTIVE' and is_visible(r['record_id']))
    reflections = tuple(r for r in store.all('subject_reflections') if r['state'] == 'CANDIDATE' and is_visible(r['record_id']))
    assertions = tuple(a for a in growth.assertions(scope, privacy_classes=privacy_classes) if a['topic'])[:32]
    adopted = [a for a in assertions if a['state'] == 'ADOPTED']
    relation = growth.relationship(entity_id, scope, privacy_classes=privacy_classes)
    support = [r['record_id'] for r in (*concerns, *commitments, *projects, *reflections)]
    for a in assertions:
        support.extend(a['source_record_ids'])
    support.extend(relation['source_record_ids'])
    memories = tuple(sorted({m for r in support for m in records.support(r)}))
    last = store.db.execute('SELECT c.* FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id '
        'WHERE e.scope=? ORDER BY c.revision DESC LIMIT 1', (scope,)).fetchone()
    stale = last is not None and now - last['created_at_us'] > DAY_US
    unavailable = last is not None and last['record_id'] is not None and not is_visible(last['record_id'])
    presence = 'DEGRADED' if unavailable else 'FOCUSED' if concerns and not stale else 'WATCHING' if concerns else 'IDLE'
    preferences = tuple(a['topic'] for a in adopted if a['kind'] == 'PREFERENCE')
    beliefs = tuple(a['topic'] for a in adopted if a['kind'] == 'SELF_BELIEF')
    internal = {'curiosity': 'ENGAGED' if preferences and concerns else 'AVAILABLE' if preferences else 'QUIET',
        'boredom': 'LOW_STIMULATION' if stale or not last else 'QUIET',
        'social_drive': 'AVAILABLE' if relation['familiarity'] == 'FAMILIAR' else 'QUIET',
        'mental_load': 'SATURATED' if len(concerns) == MAX_PENDING else 'OCCUPIED' if concerns else 'LOW',
        'confidence': 'SOURCE_BACKED' if support else 'UNKNOWN', 'uncertainty': 'MIXED' if unavailable else 'KNOWN_LIMITS',
        'playfulness_activation': relation['playfulness_permission'],
        'exploration_drive': 'INHIBITED_BY_DUTY' if any(r['due_at_us'] and r['due_at_us'] <= now for r in commitments)
            else 'AVAILABLE' if preferences else 'QUIET'}
    personality = PersonalityProfile(stable_preferences=preferences, self_beliefs=beliefs,
        expression_tendencies={'curiosity': 'EVIDENCE_SUPPORTED' if 'exploration' in preferences else 'UNESTABLISHED',
            'playfulness': relation['playfulness_permission'], 'directness': relation['challenge_comfort'],
            'patience': 'UNESTABLISHED', 'boldness': 'UNESTABLISHED', 'social_energy': 'CONTEXT_DEPENDENT',
            'humor_style': 'SHARED_CONTEXT' if relation['interaction_style'] == 'WARM_PLAYFUL' else 'UNESTABLISHED',
            'exploration_tendency': 'SUPPORTED' if 'exploration' in preferences else 'UNESTABLISHED',
            'risk_tendency': 'NO_AUTHORITY_INFERENCE', 'affection_expression': 'RELATIONSHIP_CONTEXTUAL'},
        interaction_style=relation['interaction_style'], support_record_ids=tuple(dict.fromkeys(support)),
        explanation=('Defaults are light; established tendencies require current independent sources.',
            'State activation, relationship stance and canonical identity are different layers.'))
    state = LivingSelfState(identity_id=store.identity['identity_id'], subject_revision=revision(store),
        state_token=token, as_of_us=now, presence=presence,
        current_activity=concerns[0]['kind'] if concerns else 'PRESENT_WITHOUT_ACTION',
        attention_focus=active_ids[0] if active_ids else None, secondary_attention=active_ids[1:],
        open_loops=active_ids, internal=internal, intentions=active_ids, goal_candidates=candidates,
        commitments=tuple(r['commitment_id'] for r in commitments)[:32], projects=tuple(r['project_id'] for r in projects)[:32],
        pending_reflections=tuple(r['reflection_id'] for r in reflections)[:8],
        unresolved_topics=tuple(a['topic'] for a in assertions if a['state'] in {'CANDIDATE','DISPUTED'})[:16],
        environment=environment or Environment(), confidence='PARTIAL' if unavailable else 'SOURCE_BACKED' if support else 'UNKNOWN',
        source_record_ids=tuple(dict.fromkeys(support)), source_memory_ids=memories)
    if state_token(store) != token:
        from ...contracts import CoreError
        raise CoreError('STATE_CHANGED_DURING_PROJECTION')
    return state, personality, relation
