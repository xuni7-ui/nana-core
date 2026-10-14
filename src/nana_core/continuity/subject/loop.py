"""The sole C-stage next-intention coordinator; no executor/network/model secrets."""
import json
from ...contracts import CoreError
from ...storage import canonical, digest, uid
from ..memory import PRIVACY_RANK
from ..records import RecordService
from .contracts import CycleResult, DAY_US, INTENTION_TTL_US, MAX_PENDING, SubjectInput
from .growth import Growth, live_record
from .ingress import SubjectIngress
from .policy import Situation, appraise, decide, motivate
from . import state


class SubjectLoop:
    def __init__(self, store, *, scopes, privacy_classes=('PUBLIC','PROJECT','PERSONAL')):
        self.store, self.scopes, self.privacy_classes = store, tuple(scopes), tuple(privacy_classes)
        if not self.scopes or any(x not in PRIVACY_RANK for x in self.privacy_classes):
            raise CoreError('SUBJECT_SCOPE_POLICY_REQUIRED')
        self.records, self.ingress, self.growth = RecordService(store), SubjectIngress(store), Growth(store)

    @property
    def revision(self):
        return state.revision(self.store)

    def visible(self, record_id, scope):
        return state.visible(self.store,record_id,scope,self.privacy_classes)

    def situation(self, event, source):
        now = self.store.clock.utc_now_us()
        records, memories, projects, commitments, due, methods = [], [], [], [], [], []
        if source['record_id']:
            if not self.visible(source['record_id'], event.scope):
                raise CoreError('SUBJECT_SOURCE_UNAVAILABLE')
            records.append(source['record_id'])
            memories.extend(self.records.support(source['record_id']))
        for mid in (*event.source_memory_ids, *event.constraint_memory_ids):
            item = self.records.memory.read(mid)
            if item['scope'] != event.scope or item['privacy_class'] not in self.privacy_classes:
                raise CoreError('SUBJECT_CONTEXT_POLICY_BLOCKED')
            memories.append(mid)
        for r in self.store.all('projects'):
            if r['state'] == 'ACTIVE' and self.visible(r['record_id'], event.scope):
                projects.append(r['project_id']); records.append(r['record_id'])
        for r in self.store.all('commitments'):
            if r['state'] in {'ADOPTED','ACTIVE'} and self.visible(r['record_id'], event.scope):
                commitments.append(r['commitment_id']); records.append(r['record_id'])
                if r['due_at_us'] is not None and r['due_at_us'] <= now:
                    due.append(r['commitment_id'])
        for mid in event.constraint_memory_ids:
            try:
                value = json.loads(self.records.memory.read(mid)['text'])
            except ValueError:
                continue
            if type(value) is dict and type(value.get('allowed_methods')) is list:
                methods.extend(x for x in value['allowed_methods'] if type(x) is str and len(x) <= 128)
        assertions = [a for a in self.growth.assertions(event.scope, privacy_classes=self.privacy_classes) if a['state'] == 'ADOPTED'
            and all(self.visible(r, event.scope) for r in a['source_record_ids'])]
        interests = tuple(a['topic'] for a in assertions if a['kind'] == 'PREFERENCE' and a['topic'])
        for a in assertions:
            records.extend(a['source_record_ids'])
        for r in records:
            memories.extend(self.records.support(r))
        pending = self.pending(event.scope)
        relation = self.growth.relationship(event.entity_id, event.scope, privacy_classes=self.privacy_classes)
        if not all(self.visible(r, event.scope) for r in relation['source_record_ids']):
            relation = {'familiarity': 'UNKNOWN', 'source_record_ids': ()}
        records.extend(relation['source_record_ids'])
        lesson_rows = [r for r in self.store.all('lessons') if r['task_class'] == event.task_class
            and r['state'] == 'ACTIVE' and self.visible(r['record_id'], event.scope)]
        records.extend(r['record_id'] for r in lesson_rows)
        for r in lesson_rows:
            memories.extend(self.records.support(r['record_id']))
        # An already pending interest is an open loop, not another reason to spawn.
        unresolved = next((x for x in interests if not any(p['slot_key'] == 'explore-' + x for p in pending)), None)
        return Situation(scope=event.scope, memory_ids=tuple(sorted(set(memories))),
            project_ids=tuple(projects), commitment_ids=tuple(commitments), due_commitment_ids=tuple(due),
            adopted_interests=interests, unresolved_interest=unresolved,
            familiar=relation['familiarity'] == 'FAMILIAR', allowed_methods=tuple(sorted(set(methods))),
            lesson_ids=tuple(r['lesson_id'] for r in lesson_rows), lesson_record_ids=tuple(r['record_id'] for r in lesson_rows),
            support_record_ids=tuple(dict.fromkeys(records)), pending_count=len(pending),
            idle=event.kind == 'WAKE')

    def pending(self, scope):
        return state.pending(self.store,scope,self.privacy_classes)

    def _expire(self, tx):
        now = self.store.clock.utc_now_us()
        for row in self.store.all('subject_intentions'):
            if row['scope'] not in self.scopes:
                continue
            supported_interests = {a['topic'] for a in self.growth.assertions(row['scope'], privacy_classes=self.privacy_classes) if a['state']=='ADOPTED'}
            lost_motivation = row['kind']=='EXPLORE' and row['slot_key'].removeprefix('explore-') not in supported_interests
            if row['state'] == 'PENDING' and (row['expires_at_us'] <= now or not live_record(self.store, row['record_id']) or lost_motivation):
                state = 'EXPIRED' if row['expires_at_us'] <= now else 'DROPPED'
                tx.update('subject_intentions', row['intention_id'], state=state, revision=row['revision'] + 1)
                for goal in self.store.all('subject_goal_candidates'):
                    if goal['intention_id'] == row['intention_id']:
                        tx.update('subject_goal_candidates', goal['candidate_id'], state='EXPIRED' if state == 'EXPIRED' else 'WITHDRAWN')

    def run(self, event: SubjectInput, *, expected_revision=None, _deliberation=None):
        if event.scope not in self.scopes or event.privacy_class not in self.privacy_classes:
            raise CoreError('SUBJECT_CONTEXT_POLICY_BLOCKED')
        if expected_revision is not None and type(expected_revision) is not int:
            raise CoreError('INVALID_SUBJECT_REVISION')
        self.store.ensure_privacy_current()
        high_water = self.store.db.execute('SELECT coalesce(max(created_at_us),0) FROM subject_cycles').fetchone()[0]
        if self.store.clock.utc_now_us() < high_water:
            raise CoreError('SUBJECT_CLOCK_ROLLBACK')
        source = self.ingress.ingest(event)
        old = self.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?', (source['subject_event_id'],)).fetchone()
        if old:
            return self.result(dict(old), replayed=True)
        expected_revision = self.revision if expected_revision is None else expected_revision
        with self.store.transaction('subject.cycle_accepted') as tx:
            if self.revision != expected_revision:
                raise CoreError('STALE_SUBJECT_REVISION')
            self._expire(tx)
            self.growth.apply(tx, event, source)
            self._expire(tx)  # counter-evidence may inhibit an earlier optional intention
            situation = self.situation(event, source)
            appraisal = appraise(event, situation)
            motives = motivate(event, situation, appraisal)
            attention, judgment, intention = decide(event, situation, appraisal, motives)
            if _deliberation is not None:
                # Model uncertainty may inhibit ordinary interaction; it cannot
                # overrule a sourced conflict, obligation or tested lesson.
                operations = _deliberation.proposal.proposed_operations
                if judgment.stance in {'WATCH','REMEMBER','THINK_MORE'} and not judgment.lesson_ids and any(x in operations for x in ('ASK','WAIT')):
                    from .contracts import Intention, Judgment
                    judgment = Judgment(stance='ASK' if 'ASK' in operations else 'DEFER',
                        reason='Cognitive proposal requests clarification or waiting; no unsupported truth is adopted',
                        source_ids=situation.memory_ids)
                    intention = Intention(kind='WAIT', purpose='Hold the concern pending clarification',
                        slot_key='clarify', source_ids=situation.memory_ids, self_generated=event.origin == 'SELF_WAKE')
            pending = self.pending(event.scope)
            duplicate_slot = any(r['slot_key'] == intention.slot_key for r in pending)
            global_pending = self.store.db.execute(
                "SELECT count(*) FROM subject_intentions i JOIN continuity_records r ON r.record_id=i.record_id "
                "WHERE i.state='PENDING' AND i.expires_at_us>? AND r.lifecycle='ACTIVE'",
                (self.store.clock.utc_now_us(),)).fetchone()[0]
            if global_pending >= MAX_PENDING or duplicate_slot:
                from .contracts import Intention, Judgment
                attention = 'DEFER'
                judgment = Judgment(stance='DEFER', reason='A matching concern is already pending or attention is full', source_ids=situation.memory_ids)
                intention = Intention(kind='NO_ACTION', purpose='Keep existing concern without duplicate initiative',
                    slot_key='quiet', source_ids=situation.memory_ids, self_generated=event.origin == 'SELF_WAKE')
            cycle_id, intention_id, candidate_id = uid(), None, None
            parents = situation.support_record_ids
            supports = situation.memory_ids
            # Non-retention also blocks derived retention, regardless of context.
            if event.retention == 'DO_NOT_REMEMBER':
                parents, supports = (), ()
            if intention.kind != 'NO_ACTION' and (parents or supports):
                intention_id = uid()
                record = self.records.create(tx, kind='INTENTION', scope=event.scope,
                    payload=intention.model_dump(mode='json'), records=parents, memories=supports)
                tx.put('subject_intentions', {'intention_id': intention_id, 'subject_event_id': source['subject_event_id'],
                    'scope': event.scope, 'slot_key': intention.slot_key, 'kind': intention.kind, 'state': 'PENDING',
                    'revision': 1, 'record_id': record, 'created_at_us': self.store.clock.utc_now_us(),
                    'expires_at_us': self.store.clock.utc_now_us() + INTENTION_TTL_US})
                if intention.kind in {'EXPLORE','GOAL_CANDIDATE'}:
                    candidate_id = uid()
                    candidate_record = self.records.create(tx, kind='GOAL_CANDIDATE', scope=event.scope,
                        payload={'purpose': intention.purpose, 'source_intention_id': intention_id,
                            'adopted': False, 'execution_authority': False}, records=(record,))
                    tx.put('subject_goal_candidates', {'candidate_id': candidate_id,
                        'intention_id': intention_id, 'record_id': candidate_record, 'state': 'PROPOSED'})
            result = CycleResult(cycle_id=cycle_id, event_id=source['subject_event_id'], revision=expected_revision + 1,
                admission=source['admission'], appraisal=appraisal, motivations=motives, attention=attention,
                judgment=judgment, intention=intention, intention_id=intention_id, goal_candidate_id=candidate_id,
                barrier='NO_ACTION' if intention.kind == 'NO_ACTION' else 'SHADOW_BLOCKED', record_id=None,
                deliberation=None if _deliberation is None else {
                    'model_descriptor': _deliberation.model_descriptor,
                    'context_digest': _deliberation.context_digest, 'raw_proposal_json': _deliberation.raw_proposal_json})
            record = None
            if parents or supports:
                record = self.records.create(tx, kind='SUBJECT_CYCLE', scope=event.scope,
                    payload=result.model_dump(mode='json'), records=parents, memories=supports)
            tx.put('subject_cycles', {'cycle_id': cycle_id, 'subject_event_id': source['subject_event_id'],
                'revision': expected_revision + 1, 'record_id': record, 'judgment': judgment.stance,
                'attention': attention, 'barrier': result.barrier, 'created_at_us': self.store.clock.utc_now_us()})
            tx.put('core_meta', {'key': 'self.subject_revision', 'value_json': canonical(expected_revision + 1)})
        return result.model_copy(update={'record_id': record})

    def result(self, row, *, replayed=False):
        if row['record_id'] and live_record(self.store, row['record_id']):
            value = self.records.read(row['record_id'])['payload']
            return CycleResult.model_validate_json(canonical(value)).model_copy(update={'record_id': row['record_id'], 'replayed': replayed})
        # An expired/deleted/never-retained rationale is not reconstructed from
        # guesses. Keep the immutable operational receipt, with no private text.
        raise CoreError('SUBJECT_RATIONALE_NOT_RETAINED' if not row['record_id'] else 'SUBJECT_RATIONALE_RETIRED')

    def transition_intention(self, intention_id, *, expected_revision, state):
        if type(expected_revision) is not int or state not in {'COMPLETED','DEFERRED','DROPPED','EXPIRED'}:
            raise CoreError('INVALID_INTENTION_TRANSITION')
        with self.store.transaction('subject.intention_transition') as tx:
            row = self.store.one('subject_intentions', intention_id)
            if not row or row['state'] != 'PENDING' or row['revision'] != expected_revision:
                raise CoreError('STALE_OR_TERMINAL_INTENTION')
            tx.update('subject_intentions', intention_id, state=state, revision=expected_revision + 1)
            for goal in self.store.all('subject_goal_candidates'):
                if goal['intention_id'] == intention_id:
                    tx.update('subject_goal_candidates', goal['candidate_id'], state='EXPIRED' if state == 'EXPIRED' else 'WITHDRAWN')

    def reflect(self, experience_id, *, authority, expected_revision=None, apply=False):
        """Explicit SubjectLoop transition, not an autonomous reflection engine.

        Application still requires existing reviewed narrow-rule authority.
        No reflection can alter CanonicalIdentity or create an Action.
        """
        from .reflection import ReflectionService
        if expected_revision is not None and expected_revision != self.revision:
            raise CoreError('STALE_SUBJECT_REVISION')
        service = ReflectionService(self.store, authority)
        reflection_id = service.propose(experience_id)
        row = self.store.one('subject_reflections', reflection_id)
        if apply and row['state'] == 'CANDIDATE':
            service.apply(reflection_id, expected_revision=row['revision'], authority=authority)
        return reflection_id

    def cognize(self, event, *, model, authority, policy):
        """Optional bounded D cognition. Never hold SQLite transaction over model.

        Freeze after idempotent ingress, validate before/after inference, then
        accept against the same subject revision. No model receives services.
        """
        from ..context import ContextAssembler, ContextRequest
        from ..cognition import DeliberationSession
        if event.scope not in self.scopes or event.privacy_class not in self.privacy_classes:
            raise CoreError('SUBJECT_CONTEXT_POLICY_BLOCKED')
        source = self.ingress.ingest(event)
        if self.store.db.execute('SELECT 1 FROM subject_cycles WHERE subject_event_id=?', (source['subject_event_id'],)).fetchone():
            return self.run(event)
        revision = self.revision
        # Complete the pre-deliberation stages before invoking a ModelPort.
        # This is a tentative view, not a committed judgment/intention. The
        # transaction re-appraises against current support before acceptance.
        situation = self.situation(event, source)
        appraisal = appraise(event, situation)
        motives = motivate(event, situation, appraisal)
        attention = decide(event, situation, appraisal, motives)[0]
        if attention == 'IGNORE':
            return self.run(event, expected_revision=revision)
        from .contracts import DeliberationFrame
        frame = DeliberationFrame(subject_event_id=source['subject_event_id'], scope=event.scope,
            appraisal=appraisal,motivations=motives,attention=attention,
            source_memory_ids=situation.memory_ids,source_record_ids=situation.support_record_ids)
        assembler = ContextAssembler(self.store, authority)
        request = ContextRequest(entity_id=event.entity_id, scopes=(event.scope,),
            task_class=event.task_class or 'subject_deliberation',
            task=event.text or 'Assess current concerns; silence is allowed', task_privacy_class=event.privacy_class,
            max_input_tokens=65536, output_reserve_tokens=4096)
        context = assembler.assemble(request, policy, subject_frame=frame)
        result = DeliberationSession(assembler).run(model, context, request, policy)
        assembler.validate(context, request, policy)
        return self.run(event, expected_revision=revision, _deliberation=result)
