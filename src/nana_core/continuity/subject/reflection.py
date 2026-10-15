"""Reflection explains independently checked experiences; it cannot invent one."""
from ...contracts import CoreError
from ...storage import uid
from ..learning import ExperienceService
from ..records import RecordService


class ReflectionService:
    def __init__(self, store, authority):
        self.store, self.authority = store, authority
        self.learning, self.records = ExperienceService(store, authority), RecordService(store)

    def propose(self, experience_id):
        experience = self.learning.get(experience_id)  # unknown or reflection IDs rejected
        old = self.store.db.execute('SELECT reflection_id FROM subject_reflections WHERE experience_id=?', (experience_id,)).fetchone()
        if old:
            return old[0]
        parent = self.store.one('experiences', experience_id)
        scope = self.records.read(parent['record_id'])['scope']
        with self.store.transaction('subject.reflection_proposed') as tx:
            reflection_id = uid()
            record = self.records.create(tx, kind='REFLECTION', scope=scope,
                payload={'experience_id': experience_id, 'outcome': experience.outcome,
                    'verification_memory_id': parent['verification_memory_id'],
                    'interpretation': 'Distinguish the recorded non-execution fact from later evidence about its consequences; do not infer obedience or hostility' if experience.task_class=='disposition.review' else 'Keep contextual variety and reception constraints' if experience.task_class=='interaction.shared_discovery' else 'Inspect a missing verified output field before repeating this procedure',
                    'candidate_kind': 'LessonCandidate', 'changes_identity': False, 'grants_authority': False},
                records=(parent['record_id'],))
            tx.put('subject_reflections', {'reflection_id': reflection_id, 'experience_id': experience_id,
                'record_id': record, 'state': 'CANDIDATE', 'revision': 1, 'lesson_id': None,
                'created_at_us': self.store.clock.utc_now_us()})
        return reflection_id

    def apply(self, reflection_id, *, expected_revision, authority):
        if authority is not self.authority:
            raise CoreError('UNAUTHENTICATED_OPERATOR')
        row = self.store.one('subject_reflections', reflection_id)
        if not row or row['revision'] != expected_revision or row['state'] != 'CANDIDATE':
            raise CoreError('STALE_OR_TERMINAL_REFLECTION')
        self.records.read(row['record_id'])
        if not self.records.current_support(row['record_id']):
            raise CoreError('REFLECTION_SOURCE_REQUIRES_REVIEW')
        # Reuse the checked narrow rule lifecycle, including idempotent recovery
        # after a crash between proposal/test/activation and reflection commit.
        lesson = self.learning.derive_lesson(row['experience_id'])
        state = self.store.one('lessons', lesson)['state']
        if state == 'CANDIDATE':
            self.learning.test_lesson(lesson)
            state = self.store.one('lessons', lesson)['state']
        if state == 'TESTED':
            self.learning.activate(lesson, authority)
            state = 'ACTIVE'
        if state != 'ACTIVE':
            raise CoreError('REFLECTION_LESSON_NOT_APPLICABLE')
        with self.store.transaction('subject.reflection_applied') as tx:
            fresh = self.store.one('subject_reflections', reflection_id)
            if fresh['revision'] != expected_revision:
                raise CoreError('STALE_OR_TERMINAL_REFLECTION')
            tx.update('subject_reflections', reflection_id, state='APPLIED', revision=expected_revision + 1, lesson_id=lesson)
        return lesson
