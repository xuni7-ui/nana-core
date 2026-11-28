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
                    'interpretation': 'Distinguish the recorded non-execution fact from later evidence about its consequences; do not infer obedience or hostility' if experience.task_class=='disposition.review' else 'Keep contextual variety and reception constraints' if experience.task_class=='interaction.shared_discovery' else 'Compare independent outcomes, hypotheses and held-out transfer before changing a strategy' if self.store.schema_target>=12 and experience.verification.check=='STRUCTURED_EXPECTATION' else 'Inspect a missing verified output field before repeating this procedure',
                    'candidate_kind': 'LessonCandidate', 'changes_identity': False, 'grants_authority': False},
                records=(parent['record_id'],))
            tx.put('subject_reflections', {'reflection_id': reflection_id, 'experience_id': experience_id,
                'record_id': record, 'state': 'CANDIDATE', 'revision': 1, 'lesson_id': None,
                'created_at_us': self.store.clock.utc_now_us()})
        return reflection_id

    def consider_learning_strategy(self, row, *, scope, privacy_classes, intention_record_id):
        from .state import visible
        from ..open_life.meta_learning import propose, strategy_source_withdrawn

        if row['lesson_id']:
            strategy = self.store.one('lessons', row['lesson_id'])
            if not strategy_source_withdrawn(self.store, strategy):
                # Recovery can reach an already committed renewal before the
                # original reflection follow-up reopened independent review.
                if (row['state'] == 'APPLIED' and strategy['task_class'] == 'learning.strategy'
                        and strategy['state'] == 'CANDIDATE'
                        and visible(self.store, strategy['record_id'], scope, privacy_classes)
                        and self.store.db.execute(
                            "SELECT 1 FROM record_dependencies WHERE record_id=? AND parent_id=? "
                            "AND parent_kind='RECORD' AND relation_kind='SUPPORT'",
                            (strategy['record_id'], intention_record_id),
                        ).fetchone()):
                    return strategy['lesson_id']
                return None
        method = self.store.db.execute(
            "SELECT * FROM lessons WHERE experience_id=? AND state='ACTIVE'", (row['experience_id'],)
        ).fetchone()
        if not method or not visible(self.store, method['record_id'], scope, privacy_classes):
            return None
        if getattr(self.learning._rule(method), 'kind', None) != 'METHOD_SELECTION':
            return None
        try:
            return propose(self.store, method['lesson_id'], authority=self.authority,
                consideration_records=(row['record_id'], intention_record_id))
        except CoreError as exc:
            if exc.code not in {'META_TRIAL_NOT_QUALIFIED', 'META_NO_PRACTICE_CANDIDATE', 'META_SELECTION_NOT_TRANSFERRED'}:
                raise
            return None

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
        lesson = row['lesson_id'] or self.learning.derive_lesson(row['experience_id'])
        lesson_row = self.store.one('lessons', lesson)
        if not self.records.current_support(lesson_row['record_id']):
            raise CoreError('REFLECTION_LESSON_NOT_APPLICABLE')
        state = lesson_row['state']
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
