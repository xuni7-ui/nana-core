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
from .opportunities import cues_from,SyntheticActionProposal
from .social import propose_social


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
                elif event.commitment_check_id==r['commitment_id']:due.append(r['commitment_id'])
        if event.commitment_check_id and event.commitment_check_id not in commitments:raise CoreError('COMMITMENT_CHECK_SOURCE_STALE')
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
        for current in pending:
            records.append(current['record_id']);memories.extend(self.records.support(current['record_id']))
        influence=None
        if self.store.schema_target>=9:
            from ..autonomy.relationships import relationship_influence,legacy_style
            influence=relationship_influence(self.store,event.entity_id,scope=event.scope,privacy_classes=self.privacy_classes)
            relation=legacy_style(influence)
        else:relation = self.growth.relationship(event.entity_id, event.scope, privacy_classes=self.privacy_classes)
        if not all(self.visible(r, event.scope) for r in relation['source_record_ids']):
            relation = {'familiarity': 'UNKNOWN', 'source_record_ids': ()}
        records.extend(relation['source_record_ids'])
        for rid in relation['source_record_ids']:memories.extend(self.records.support(rid))
        lesson_rows = [r for r in self.store.all('lessons') if r['task_class'] == event.task_class
            and r['state'] == 'ACTIVE' and self.visible(r['record_id'], event.scope)]
        records.extend(r['record_id'] for r in lesson_rows)
        for r in lesson_rows:
            memories.extend(self.records.support(r['record_id']))
        norm_rows=self.store.db.execute("SELECT memory_id FROM memories WHERE scope=? AND entity_id IN (?,?) AND predicate_key LIKE 'concern.constraint%' AND lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') LIMIT 65",
            (event.scope,event.entity_id,self.store.identity['identity_id'])).fetchall()
        if len(norm_rows)>64:raise CoreError('SUBJECT_NORM_CAPACITY_REQUIRES_REVIEW')
        norm_ids=tuple(r['memory_id'] for r in norm_rows)
        candidates=cues_from(self.store,(*event.source_memory_ids,*norm_ids),scope=event.scope,privacy_classes=self.privacy_classes)
        cue=next((c for _,c in candidates if c.cue_kind!='CONSTRAINT'),None)
        if cue is not None and event.result_for_intention_id and event.novelty=='HIGH':
            from .opportunities import ConcernCue
            cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key=cue.topic_key,
                possible_behaviors=('SOCIALIZE','WATCH') if relation.get('familiarity')=='FAMILIAR' else ('WATCH',),availability=event.observed_availability or 'UNKNOWN')
        if cue is None and event.kind=='WAKE':
            from .opportunities import ConcernCue
            for pid in projects:
                project=self.store.one('projects',pid)
                if self.records.read(project['record_id'])['payload'].get('blockers'):
                    cue=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='PROJECT_COMPLETION',topic_key='project-'+digest(pid)[:16])
                    break
        if cue is not None and cue.required_preference_id and cue.required_preference_id not in {a['assertion_id'] for a in assertions}:
            cue=cue.model_copy(update={'possible_behaviors':('WATCH',)})
        if cue is not None and len(pending)>=6 and not due:
            cue=cue.model_copy(update={'cognitive_load':'HIGH'})
        prohibited=tuple(dict.fromkeys(b for _,c in candidates if c.cue_kind=='CONSTRAINT' and (cue is None or c.topic_key==cue.topic_key) for b in c.prohibited_behaviors))
        memories.extend(mid for mid,_ in candidates)
        last_act=None
        for old in reversed(self.store.all('subject_intentions')):
            if old['kind']=='SOCIAL_INTERACTION' and self.visible(old['record_id'],event.scope):
                parent=self.store.one('subject_events',old['subject_event_id'])
                if parent['entity_id']==event.entity_id:
                    last_act=self.records.read(old['record_id'])['payload'].get('social_proposal')
                    last_act=last_act.get('act') if last_act else None
                    break
        if event.reflection_experience_id:
            experience=self.store.one('experiences',event.reflection_experience_id)
            if not experience or not self.visible(experience['record_id'],event.scope):raise CoreError('EXPERIENCE_MISSING')
            records.append(experience['record_id']);memories.extend(self.records.support(experience['record_id']))
        # An already pending interest is an open loop, not another reason to spawn.
        if event.disposition_reflection_id:
            ref=self.store.one('continuity_records',event.disposition_reflection_id)
            if not ref or ref['record_kind']!='INTENTION_DISPOSITION' or not self.visible(ref['record_id'],event.scope):raise CoreError('DISPOSITION_REFLECTION_SOURCE_UNAVAILABLE')
            records.append(ref['record_id']);memories.extend(self.records.support(ref['record_id']))
        unresolved = next((x for x in interests if not any(p['slot_key'] == 'explore-' + x for p in pending)), None)
        manager_outcomes=()
        if self.store.schema_target>=9:
            from ..autonomy.governance import manager_views
            manager_outcomes=manager_views(self.store,scope=event.scope,privacy_classes=self.privacy_classes)
            # External facts are available, not automatic normative dependencies.
            # Otherwise every new decision accumulates the whole veto history.
            records.extend(x['record_id'] for x in manager_outcomes if x['record_id']==event.governance_review_id)
        privacy=None
        if self.store.schema_target>=9:
            from ..autonomy.relationships import social_privacy
            topic=event.disclosure_request.topic if event.disclosure_request else cue.topic_key if cue else event.topic
            if topic:
                privacy=social_privacy(self.store,event,topic=topic,privacy_classes=self.privacy_classes,resource=cue.resource_ref if cue else None)
                memories.extend(privacy.support_refs)
        return Situation(scope=event.scope, memory_ids=tuple(sorted(set(memories))),
            project_ids=tuple(projects), commitment_ids=tuple(commitments), due_commitment_ids=tuple(due),
            adopted_interests=interests, unresolved_interest=unresolved,
            familiar=relation['familiarity'] == 'FAMILIAR', allowed_methods=tuple(sorted(set(methods))),
            lesson_ids=tuple(r['lesson_id'] for r in lesson_rows), lesson_record_ids=tuple(r['record_id'] for r in lesson_rows),
            support_record_ids=tuple(dict.fromkeys(records)), pending_count=len(pending),
            idle=event.kind == 'WAKE',cue=cue,prohibited_behaviors=prohibited,
            interaction_style=relation.get('interaction_style','RESPECTFUL_EXPLICIT'),last_social_act=last_act,
            reflection_experience_id=event.reflection_experience_id,manager_outcomes=manager_outcomes,
            relationship_influence=influence,social_privacy=privacy,autonomy_semantics=self.store.schema_target>=9)

    def pending(self, scope):
        return state.pending(self.store,scope,self.privacy_classes)

    def _expire(self, tx):
        now = self.store.clock.utc_now_us()
        for row in self.store.all('subject_intentions'):
            if row['scope'] not in self.scopes:
                continue
            supported_interests = {a['topic'] for a in self.growth.assertions(row['scope'], privacy_classes=self.privacy_classes) if a['state']=='ADOPTED'}
            lost_motivation = row['kind']=='EXPLORE' and row['slot_key'].startswith('explore-') and row['slot_key'].removeprefix('explore-') not in supported_interests
            if row['state'] == 'PENDING' and (row['expires_at_us'] <= now or not live_record(self.store, row['record_id']) or lost_motivation):
                state = 'EXPIRED' if row['expires_at_us'] <= now else 'DROPPED'
                tx.update('subject_intentions', row['intention_id'], state=state, revision=row['revision'] + 1)
                for goal in self.store.all('subject_goal_candidates'):
                    if goal['intention_id'] == row['intention_id']:
                        tx.update('subject_goal_candidates', goal['candidate_id'], state='EXPIRED' if state == 'EXPIRED' else 'WITHDRAWN')

    def run(self, event: SubjectInput, *, expected_revision=None, _deliberation=None):
        if any(x is not None for x in (event.disclosure_request,event.realization_target,event.governance_review_id,event.relationship_details,event.positive_request,event.commitment_check_id,event.disposition_reflection_id)) and self.store.schema_target<9:
            raise CoreError('AUTONOMY_SCHEMA_REQUIRED')
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
            if event.result_for_intention_id:
                parent=self.store.one('subject_intentions',event.result_for_intention_id)
                if not parent or parent['kind']!='EXPLORE' or parent['scope']!=event.scope or parent['state']!='PENDING' or not self.visible(parent['record_id'],event.scope):
                    raise CoreError('SYNTHETIC_INTENTION_OUTCOME_MISMATCH')
                if not set(event.source_memory_ids)&set(self.records.support(parent['record_id'])):
                    raise CoreError('SYNTHETIC_INTENTION_OUTCOME_MISMATCH')
                tx.update('subject_intentions',parent['intention_id'],state='COMPLETED',revision=parent['revision']+1)
                for candidate in self.store.all('subject_goal_candidates'):
                    if candidate['intention_id']==parent['intention_id']:tx.update('subject_goal_candidates',candidate['candidate_id'],state='WITHDRAWN')
            self.growth.apply(tx, event, source)
            self._expire(tx)  # counter-evidence may inhibit an earlier optional intention
            situation = self.situation(event, source)
            appraisal = appraise(event, situation)
            motives = motivate(event, situation, appraisal)
            attention, judgment, intention = decide(event, situation, appraisal, motives)
            request_decision=None
            if self.store.schema_target>=9 and event.positive_request and event.retention!='DO_NOT_REMEMBER':
                from ..autonomy.requests import evaluate_request
                from .contracts import Intention,Judgment
                request_decision=evaluate_request(event,situation,self.store.clock.utc_now_us(),source_memory_id=source['memory_id'])
                choice=request_decision.decision
                judgment=Judgment(stance='AGREE' if choice=='ACCEPT' else 'ALTERNATIVE' if choice=='NEGOTIATE' else 'DISAGREE',reason=request_decision.reason,source_ids=situation.memory_ids)
                intention=Intention(kind='GOAL_CANDIDATE' if choice=='ACCEPT' else 'SOCIAL_INTERACTION' if choice=='NEGOTIATE' else 'NO_ACTION',
                    purpose='Propose, discuss or decline a commitment; this is not adoption',slot_key='request-'+digest(event.source_key)[:24],source_ids=situation.memory_ids,self_generated=False)
            if self.store.schema_target>=9 and situation.cue and situation.social_privacy:
                from .contracts import Intention,Judgment
                if situation.social_privacy.assessment in {'EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN'}:
                    attention='DEFER'
                    judgment=Judgment(stance='DEFER',reason='A sourced social boundary makes self-restraint appropriate; this is not a governance veto',source_ids=situation.memory_ids)
                    intention=Intention(kind='NO_ACTION',purpose='Choose to respect the social expectation',slot_key='quiet',source_ids=situation.memory_ids,self_generated=event.origin=='SELF_WAKE',behavior='STAY_SILENT')
                elif situation.social_privacy.assessment=='CONTEXT_SENSITIVE' and not situation.familiar:
                    attention='FOCUS_NOW'
                    judgment=Judgment(stance='ASK',reason='Clarify the social expectation before proceeding in an unfamiliar context',source_ids=situation.memory_ids)
                    intention=Intention(kind='WAIT',purpose='Clarify rather than assume interaction latitude',slot_key='clarify',source_ids=situation.memory_ids,self_generated=event.origin=='SELF_WAKE')
            if event.governance_review_id:
                view=next((v for v in situation.manager_outcomes if v['record_id']==event.governance_review_id),None)
                if not view:raise CoreError('MANAGER_REVIEW_SOURCE_UNAVAILABLE')
                from .contracts import Intention,Judgment
                judgment=Judgment(stance='DISAGREE' if view['result']=='BLOCK' else 'ASK',
                    reason='Request review of an external limitation without changing it or rewriting the prior intention',source_ids=situation.memory_ids)
                intention=Intention(kind='GOAL_CANDIDATE',purpose='Consider a request for governance review',slot_key='review-'+view['record_id'],
                    source_ids=situation.memory_ids,self_generated=event.origin=='SELF_WAKE',behavior='EXPRESS_OPINION')
            if event.disposition_reflection_id:
                from .contracts import Intention,Judgment
                judgment=Judgment(stance='REFLECT',reason='Select a recorded disposition for meaningful experience review; no new history is invented',source_ids=situation.memory_ids)
                intention=Intention(kind='REFLECTION',purpose='Consider the meaning of a recorded decision',slot_key='disposition-'+event.disposition_reflection_id,
                    source_ids=situation.memory_ids,self_generated=event.origin=='SELF_WAKE',behavior='REFLECT')
            if self.store.schema_target>=9 and event.task_class=='disposition.review' and situation.lesson_ids:
                from ..autonomy.experience import DispositionRule,lesson_method
                from .contracts import Intention,Judgment
                rule=DispositionRule.model_validate_json(canonical(self.records.read(self.store.one('lessons',situation.lesson_ids[0])['record_id'])['payload']['rule']))
                judgment=Judgment(stance='ALTERNATIVE',reason='A checked later consequence supports reviewing context before repeating a decision',source_ids=situation.memory_ids,
                    selected_method=lesson_method(rule),lesson_ids=situation.lesson_ids)
                intention=Intention(kind='REFLECTION',purpose='Review the supported consequence without acquiring authority',slot_key='learned-disposition-review',source_ids=situation.memory_ids,self_generated=event.origin=='SELF_WAKE',behavior='REFLECT')
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
            social=None
            if request_decision and request_decision.decision=='NEGOTIATE':
                social=propose_social(topic='commitment.scope',style='RESPECTFUL_EXPLICIT',available=True,source_ids=situation.memory_ids)
            evaluation=disclosure=None
            if self.store.schema_target>=9:
                from ..autonomy.evaluation import evaluate
                from ..autonomy.disclosure import decide_disclosure
                evaluation=evaluate(event,situation,attention,judgment,intention)
                disclosure=decide_disclosure(self.store,event,privacy_classes=self.privacy_classes,relation=situation.relationship_influence)
                if disclosure:
                    # Disclosure sources participate in the same erasure lineage.
                    situation=situation.model_copy(update={
                        'memory_ids':tuple(dict.fromkeys((*situation.memory_ids,*disclosure.source_memory_ids))),
                        'support_record_ids':tuple(dict.fromkeys((*situation.support_record_ids,*disclosure.source_record_ids)))})
            if intention.kind=='SOCIAL_INTERACTION' and situation.cue:
                social=propose_social(topic=situation.cue.topic_key,style=situation.interaction_style,
                    available=situation.cue.availability=='AVAILABLE',source_ids=situation.memory_ids,
                    lesson_ids=situation.lesson_ids,last_act=situation.last_social_act)
            action=None
            if intention.kind=='EXPLORE' and situation.cue and situation.cue.resource_ref:
                action=SyntheticActionProposal(resource_ref=situation.cue.resource_ref,resource_class=situation.cue.resource_class,source_memory_ids=situation.memory_ids)
            target=event.realization_target if evaluation and evaluation.normative=='ENDORSED' else None
            if target and situation.cue and situation.cue.resource_ref:
                if target.resource!=situation.cue.resource_ref:raise CoreError('REALIZATION_SOURCE_TARGET_MISMATCH')
                target=target.model_copy(update={'resource_class':situation.cue.resource_class})
            cycle_id, intention_id, candidate_id = uid(), None, None
            parents = situation.support_record_ids
            supports = situation.memory_ids
            # Non-retention also blocks derived retention, regardless of context.
            if event.retention == 'DO_NOT_REMEMBER':
                parents, supports = (), ()
            if (intention.kind != 'NO_ACTION' or (evaluation and evaluation.considered)) and (parents or supports):
                intention_id = uid()
                record = self.records.create(tx, kind='INTENTION', scope=event.scope,
                    payload={**intention.model_dump(mode='json'),'social_proposal':social.model_dump(mode='json') if social else None}, records=parents, memories=supports)
                tx.put('subject_intentions', {'intention_id': intention_id, 'subject_event_id': source['subject_event_id'],
                    'scope': event.scope, 'slot_key': intention.slot_key, 'kind': intention.kind,
                    'state': 'DROPPED' if evaluation and evaluation.normative=='RESTRAINED' else 'DEFERRED' if intention.kind=='NO_ACTION' else 'PENDING',
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
                barrier='NO_ACTION' if intention.kind == 'NO_ACTION' else 'SHADOW_BLOCKED', record_id=None,social_proposal=social,action_proposal=action,
                evaluation=evaluation,disclosure=disclosure,request_decision=request_decision,selected_disposition_id=event.disposition_reflection_id,
                realization_target=target,
                deliberation=None if _deliberation is None else {
                    'model_descriptor': _deliberation.model_descriptor,
                    'context_digest': _deliberation.context_digest, 'raw_proposal_json': _deliberation.raw_proposal_json})
            record = None
            if parents or supports:
                record = self.records.create(tx, kind='SUBJECT_CYCLE', scope=event.scope,
                    payload=result.model_dump(mode='json'), records=parents, memories=supports)
                if evaluation:
                    from ..autonomy.history import record_disposition
                    record_disposition(self.store,tx,cycle_id=cycle_id,intention_id=intention_id,intention_revision=1,
                        scope=event.scope,parent_record=record,stage='SUBJECT',code=evaluation.disposition,
                        normative=evaluation.normative,wanted=evaluation.wanted,reason_refs=evaluation.reason_refs)
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

    def cognize(self, event, *, model, authority, policy, capabilities=(), limitations=()):
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
        context = assembler.assemble(request, policy, subject_frame=frame,capabilities=capabilities,limitations=limitations)
        result = DeliberationSession(assembler).run(model, context, request, policy)
        assembler.validate(context, request, policy)
        return self.run(event, expected_revision=revision, _deliberation=result)

    def maintain(self):
        """C-owned expiration; D supplies time, never invents a judgment."""
        now=self.store.clock.utc_now_us()
        pending=[r for r in self.store.all('subject_intentions') if r['scope'] in self.scopes and r['state']=='PENDING']
        if any(r['expires_at_us']<=now or not live_record(self.store,r['record_id']) for r in pending):
            with self.store.transaction('subject.time_maintained') as tx:self._expire(tx)

    def background_opportunities(self,**time_context):
        from .watch import collect_opportunities
        return collect_opportunities(self,**time_context)
