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
from .opportunities import cues_from,directions,SyntheticActionProposal
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

    def dialogue_private_refs(self, *, scope, topic, privacy_classes):
        """C's current own considerations, before its normal dialogue decision.

        This read-only selection is neither disclosure nor adoption. The same
        records compete in the complete INTERPRET request budget.
        """
        if scope not in self.scopes:raise CoreError('SUBJECT_CONTEXT_POLICY_BLOCKED')
        from ..autonomy.private_intent import decision_support
        return decision_support(self.store,scope,tuple(p for p in privacy_classes if p in self.privacy_classes),topic=topic)

    def situation(self, event, source):
        now = self.store.clock.utc_now_us()
        records, memories, projects, commitments, due, methods = [], [], [], [], [], []
        continued=None
        if event.private_thought_ref is not None:
            if self.store.schema_target<13:raise CoreError('PRIVATE_CONTINUATION_SCHEMA_REQUIRED')
            from ..autonomy.private_intent import continuation_target
            continued=continuation_target(self.store,event.private_thought_ref,scope=event.scope,privacy_classes=self.privacy_classes)
            event=event.model_copy(update={'topic':continued[1].topic})
        if source['record_id']:
            if not self.visible(source['record_id'], event.scope):
                raise CoreError('SUBJECT_SOURCE_UNAVAILABLE')
            records.append(source['record_id'])
            memories.extend(self.records.support(source['record_id']))
        if self.store.schema_target>=13 and event.world_concern_id:
            from ..world_loop.concern_source import binding as concern_binding
            concern=self.store.one('open_concerns',event.world_concern_id)
            if not concern or event.source_key!=concern_binding(self.store,concern)[0] or not self.visible(concern['record_id'],event.scope):raise CoreError('STALE_OR_UNSUPPORTED_WORLD_CONCERN')
            records.append(concern['record_id']);memories.extend(self.records.support(concern['record_id']))
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
        growth_change=None
        if event.growth_assessment_id:
            from .growth_life import project,availability
            from .opportunities import ConcernCue
            growth_change=project(self.store,event.growth_assessment_id,scope=event.scope,privacy_classes=self.privacy_classes)
            if growth_change is None:raise CoreError('GROWTH_CHANGE_SOURCE_RETIRED')
            records.extend(growth_change.source_record_ids);memories.extend(growth_change.source_memory_ids)
            available,availability_refs=availability(self.store,event.entity_id,scope=event.scope,privacy_classes=self.privacy_classes)
            memories.extend(availability_refs)
            cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='COMPETENCE',topic_key=growth_change.topic,possible_behaviors=('SOCIALIZE','WATCH') if available=='AVAILABLE' else ('WATCH',),availability=available)
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
        private_interests=()
        if self.store.schema_target>=13 and event.retention!='DO_NOT_REMEMBER':
            from ..autonomy.private_intent import decision_support
            private_privacy=tuple(p for p in self.privacy_classes if PRIVACY_RANK[p]<=PRIVACY_RANK[event.privacy_class])
            private_topic = cue.topic_key if cue else event.topic or (
                event.interaction_signal.topic_key if event.interaction_signal else None
            )
            private_interests=decision_support(self.store,event.scope,private_privacy,topic=private_topic)
            if continued is not None and continued[0] not in private_interests:private_interests=(*private_interests,continued[0])
            records.extend(private_interests)
            for rid in private_interests:memories.extend(self.records.support(rid))
            if cue and cue.private_intent_ref:
                if event.origin!='SELF_WAKE':raise CoreError('PRIVATE_INTENT_REVIEW_SELF_ONLY')
                from ..autonomy.private_intent import review_target
                rid,_=review_target(self.store,cue.private_intent_ref,scope=event.scope,
                    privacy_classes=private_privacy,topic=cue.topic_key)
                records.append(rid);memories.extend(self.records.support(rid))
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
        appetite=None
        if self.store.schema_target>=10:
            from ..relational.projections import social_appetite
            appetite=social_appetite(self.store,scope=event.scope,privacy_classes=self.privacy_classes)
            records.extend(appetite.source_record_ids);memories.extend(appetite.source_memory_ids)
            if unresolved in {'social_exploration','social_connection','social_play'} and cue is None:unresolved=None
        voluntary=[]
        if self.store.schema_target>=10 and cue and cue.behavior_domain:
            from ..relational.contracts import VoluntaryTerms
            for cid in commitments:
                row=self.store.one('commitments',cid);body=self.records.read(row['record_id'])['payload']
                if body.get('voluntary'):
                    terms=VoluntaryTerms.model_validate_json(canonical(body['voluntary']))
                    if terms.operation=='REFRAIN' and terms.behavior_domain==cue.behavior_domain and terms.start_us<=now<min(terms.end_us,terms.review_at_us):voluntary.append(cid)
        from .context_fit import assess,plan_binding
        contextual_event=event
        if event.goal_step or event.goal_review:
            binding=plan_binding(self.store,event.goal_step,scope=event.scope,privacy_classes=self.privacy_classes,goal_id=event.goal_review.goal_id if event.goal_review else None)
            if binding:contextual_event=event.model_copy(update={'topic':binding['topic_key'],'entity_id':binding['entity_id']})
        context_fit=assess(self.store,contextual_event,source,topic=contextual_event.topic or (cue.topic_key if cue else None),privacy_classes=self.privacy_classes)
        if context_fit:
            records.extend(context_fit.source_record_ids);memories.extend(context_fit.source_memory_ids)
        need=None
        if self.store.schema_target>=13 and event.task_class and cue and cue.motivation_source=='CAPABILITY_GAP':
            from .experience_need import project_need
            need=project_need(self.store,event.task_class,scope=event.scope,privacy_classes=self.privacy_classes,source_memory_ids=event.source_memory_ids)
            records.extend(need.source_record_ids)
            for rid in need.source_record_ids:memories.extend(self.records.support(rid))
            if need.state=='SETTLED':
                cue=cue.model_copy(update={'possible_behaviors':('WATCH',)})
        frame=None
        if event.problem_frame:
            from .framing import evaluate
            frame=evaluate(event.problem_frame,self.records,scope=event.scope,privacy_classes=self.privacy_classes)
        return Situation(private_interest_records=private_interests,experience_need=need,problem_frame=frame,context_fit=context_fit,scope=event.scope, memory_ids=tuple(sorted(set(memories))),
            project_ids=tuple(projects), commitment_ids=tuple(commitments), due_commitment_ids=tuple(due),
            adopted_interests=interests, unresolved_interest=unresolved,
            familiar=relation['familiarity'] == 'FAMILIAR', allowed_methods=tuple(sorted(set(methods))),
            lesson_ids=tuple(r['lesson_id'] for r in lesson_rows), lesson_record_ids=tuple(r['record_id'] for r in lesson_rows),
            support_record_ids=tuple(dict.fromkeys(records)), pending_count=len(pending),
            idle=event.kind == 'WAKE',cue=cue,prohibited_behaviors=prohibited,
            interaction_style=relation.get('interaction_style','RESPECTFUL_EXPLICIT'),last_social_act=last_act,
            reflection_experience_id=event.reflection_experience_id,manager_outcomes=manager_outcomes,
            relationship_influence=influence,social_privacy=privacy,autonomy_semantics=self.store.schema_target>=9,social_appetite=appetite,voluntary_restraints=tuple(voluntary))

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
        if event.relational_request and self.store.schema_target<10:raise CoreError('RELATIONAL_SCHEMA_REQUIRED')
        if event.preference_signal and event.preference_signal.kind=='PERSONALITY_TENDENCY' and self.store.schema_target<10:raise CoreError('RELATIONAL_SCHEMA_REQUIRED')
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
            if self.store.schema_target>=11:
                adopted=[];plan_refs=[]
                for goal in self.store.db.execute("SELECT * FROM goals WHERE state IN ('ACTIVE','BLOCKED','SUSPENDED') LIMIT 16"):
                    rid=json.loads(goal['body_json']).get('plan_record_id')
                    if rid and self.visible(rid,event.scope):
                        plan=self.records.read(rid)['payload'];adopted.append(plan['program']['program_id'])
                        if self.store.schema_target<12:plan_refs.append(rid)
                if self.store.schema_target>=13:
                    # The same C concern can already be represented by adopted
                    # I work, not only an F goal. It must not manufacture another
                    # pending desire while the existing work runs or has finished.
                    for work in self.store.db.execute("SELECT j.record_id FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id WHERE j.work_kind='CODE_DEVELOPMENT' AND j.state!='CANCELLED' AND r.scope=? AND r.lifecycle='ACTIVE' ORDER BY j.rowid DESC LIMIT 16",(event.scope,)):
                        if self.visible(work['record_id'],event.scope):
                            program=self.records.read(work['record_id'])['payload'].get('source_program_id')
                            if program:adopted.append(program)
                situation=situation.model_copy(update={'separate_delivery':self.store.schema_target>=12,'adopted_program_ids':tuple(adopted),'support_record_ids':tuple(dict.fromkeys((*situation.support_record_ids,*plan_refs)))})
            if event.goal_review:
                goal=self.store.one('goals',event.goal_review.goal_id)
                if self.store.schema_target<12 or not goal or goal['version']!=event.goal_review.version or goal['state'] not in {'FAILED','BLOCKED','ACTIVE','SUSPENDED'}:raise CoreError('STALE_GOAL_REVIEW')
                rid=json.loads(goal['body_json'])['record_id']
                if not self.visible(rid,event.scope):raise CoreError('GOAL_SOURCE_UNAVAILABLE')
                situation=situation.model_copy(update={'goal_review_id':goal['goal_id'],'support_record_ids':tuple(dict.fromkeys((*situation.support_record_ids,rid)))})
            if event.memory_review_id:
                from ..maintenance import MaintenanceService
                head,body=MaintenanceService(self.store,scopes=self.scopes,entity_id=event.entity_id,privacy_classes=self.privacy_classes).candidate(event.memory_review_id)
                situation=situation.model_copy(update={'memory_review_id':event.memory_review_id,
                    'memory_ids':tuple(dict.fromkeys((*situation.memory_ids,*body['memory_ids']))),
                    'support_record_ids':tuple(dict.fromkeys((*situation.support_record_ids,event.memory_review_id)))})
            if event.goal_step:
                from ..agency import step_view
                view=step_view(self.store,event.goal_step,scope=event.scope,privacy_classes=self.privacy_classes)
                if event.realization_target!=view.target:raise CoreError('GOAL_STEP_TARGET_MISMATCH')
                situation=situation.model_copy(update={'plan_step':view,'memory_ids':tuple(dict.fromkeys((*situation.memory_ids,*view.source_memory_ids))),
                    'support_record_ids':tuple(dict.fromkeys((*situation.support_record_ids,view.record_id)))})
            if _deliberation is not None and _deliberation.proposal.preferred_behavior is not None:
                situation=situation.model_copy(update={'preferred_behavior':_deliberation.proposal.preferred_behavior})
            appraisal = appraise(event, situation)
            motives = motivate(event, situation, appraisal)
            attention, judgment, intention = decide(event, situation, appraisal, motives)
            if self.store.schema_target>=12 and situation.lesson_ids and event.task_class:
                from ..open_agency.learning import MethodStrategyRule
                for lid in situation.lesson_ids:
                    payload=self.records.read(self.store.one('lessons',lid)['record_id'])['payload']['rule']
                    rule=MethodStrategyRule.model_validate_json(canonical(payload)) if payload.get('kind')=='METHOD_SELECTION' else None
                    if isinstance(rule,MethodStrategyRule):
                        judgment=judgment.model_copy(update={'selected_method':rule.method,'lesson_ids':situation.lesson_ids})
                        break
            request_decision=None
            if self.store.schema_target>=9 and event.positive_request and event.retention!='DO_NOT_REMEMBER':
                from ..autonomy.requests import evaluate_request
                from .contracts import Intention,Judgment
                request_decision=evaluate_request(event,situation,self.store.clock.utc_now_us(),source_memory_id=source['memory_id'])
                choice=request_decision.decision
                judgment=Judgment(stance='AGREE' if choice=='ACCEPT' else 'ALTERNATIVE' if choice=='NEGOTIATE' else 'DISAGREE',reason=request_decision.reason,source_ids=situation.memory_ids)
                intention=Intention(kind='GOAL_CANDIDATE' if choice=='ACCEPT' else 'SOCIAL_INTERACTION' if choice=='NEGOTIATE' else 'NO_ACTION',
                    purpose='Propose, discuss or decline a commitment; this is not adoption',slot_key='request-'+digest(event.source_key)[:24],source_ids=situation.memory_ids,self_generated=False)
            from ..autonomy.evaluation import unbound_private_choice
            if self.store.schema_target>=9 and situation.cue and situation.social_privacy and not unbound_private_choice(event,situation,intention):
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
            relational=None
            if self.store.schema_target>=10 and event.relational_request and event.retention!='DO_NOT_REMEMBER':
                from ..relational.deliberation import deliberate
                from .contracts import Intention,Judgment
                relational=deliberate(self.store,event,situation,source_record_id=source['record_id'],privacy_classes=self.privacy_classes)
                if relational:
                    choice=relational.response.decision
                    refs=tuple(dict.fromkeys((*relational.deference.relationship_refs,*relational.deference.personality_refs)))
                    situation=situation.model_copy(update={'support_record_ids':tuple(dict.fromkeys((*situation.support_record_ids,*refs))),
                        'memory_ids':tuple(sorted({*situation.memory_ids,*(m for r in refs for m in self.records.support(r))}))})
                    attention='FOCUS_NOW'
                    judgment=Judgment(stance='AGREE' if choice=='ACCEPT' else 'ALTERNATIVE' if choice=='NEGOTIATE' else 'DISAGREE',
                        reason='Subject-owned relational tradeoff; retained desire is not rewritten and no authority is created',source_ids=situation.memory_ids)
                    intention=Intention(kind='GOAL_CANDIDATE' if choice=='ACCEPT' else 'SOCIAL_INTERACTION' if choice=='NEGOTIATE' else 'NO_ACTION',
                        purpose='Consider bounded accommodation or discuss its scope',slot_key='relational-'+digest(event.source_key)[:24],source_ids=situation.memory_ids,self_generated=False)
            conversation=None
            if event.conversation_proposal:
                from ..person_self import consider
                from .contracts import Intention, Judgment
                conversation=consider(self.store,event,situation,self.privacy_classes)
                choice=conversation.choice
                attention='FOCUS_NOW'
                judgment=Judgment(stance='AGREE' if choice in {'ADOPT','WITHDRAW','PLAY_ONLY'} else 'DISAGREE' if choice=='DECLINE' else 'ASK' if choice=='ASK' else 'WATCH',reason=conversation.reason,source_ids=situation.memory_ids)
                intention=Intention(kind='NO_ACTION' if choice=='DECLINE' else 'SOCIAL_INTERACTION',purpose=conversation.reason,slot_key='conversation-'+digest(event.source_key)[:24],source_ids=situation.memory_ids,self_generated=False)
            review_event=event
            if self.store.schema_target>=10 and event.kind=='WAKE' and not event.commitment_check_id and not situation.cue:
                # A deferred due review can be reconsidered on an ordinary later
                # wake. C selects the concern; Scheduler neither adopts nor sends.
                for cid in situation.due_commitment_ids:
                    row=self.store.one('commitments',cid)
                    if self.records.read(row['record_id'])['payload'].get('voluntary'):
                        review_event=event.model_copy(update={'task_class':'relational.accommodation.review','commitment_check_id':cid,'entity_id':row['entity_id']})
                        break
            if self.store.schema_target>=10 and review_event.task_class=='relational.accommodation.review':
                from ..relational.accommodation import review
                from .contracts import Intention,Judgment
                review_situation=situation if review_event is event else self.situation(review_event,source)
                relational=review(self.store,review_event,review_situation,privacy_classes=self.privacy_classes)
                attention='FOCUS_NOW'
                judgment=Judgment(stance='ALTERNATIVE' if relational.review_choice=='MODIFY' else 'AGREE',reason='Reconsider bounded accommodation from current sources; timer is not authority',source_ids=situation.memory_ids)
                intention=Intention(kind='GOAL_CANDIDATE',purpose='Apply the sourced voluntary review choice',slot_key='voluntary-review-'+digest(event.source_key)[:24],source_ids=situation.memory_ids,self_generated=True)
            private_question=None;private_plan=None
            if _deliberation is not None:
                # Model uncertainty may inhibit ordinary interaction; it cannot
                # overrule a sourced conflict, obligation or tested lesson.
                operations = _deliberation.proposal.proposed_operations
                from ..autonomy.private_intent import consider_question,consider_plan
                private_question=(consider_question(event,situation,judgment,intention,_deliberation.proposal.private_question)
                    if self.store.schema_target>=13 else None)
                private_plan=(consider_plan(event,situation,judgment,intention,_deliberation.proposal.private_plan)
                    if self.store.schema_target>=13 else None)
                formation=private_question or private_plan
                if formation is not None:
                    label='question' if private_question is not None else 'plan'
                    from .contracts import Intention,Judgment
                    judgment=judgment.model_copy(update={'stance':'REFLECT',
                        'reason':f'Consider an own private {label}, without treating it as an observation or a permission',
                        'source_ids':situation.memory_ids})
                    intention=Intention(kind='REFLECTION',purpose=f'Consider an own private {label}; contents remain private',
                        slot_key='private-'+label+'-'+digest(formation.model_dump(mode='json'))[:32],
                        source_ids=situation.memory_ids,self_generated=True,behavior='REFLECT')
                elif judgment.stance in {'WATCH','REMEMBER','THINK_MORE'} and not judgment.lesson_ids and any(x in operations for x in ('ASK','WAIT')):
                    from .contracts import Intention, Judgment
                    judgment = Judgment(stance='ASK' if 'ASK' in operations else 'DEFER',
                        reason='Cognitive proposal requests clarification or waiting; no unsupported truth is adopted',
                        source_ids=situation.memory_ids)
                    if event.private_thought_ref is not None:
                        # An unresolved private thought is not another external
                        # task or an outward request for clarification.
                        intention = Intention(kind='NO_ACTION', purpose='Keep the private concern open without allocating a task or asking outwardly',
                            slot_key='quiet', source_ids=situation.memory_ids, self_generated=True, behavior='DEFER')
                    else:
                        intention = Intention(kind='WAIT', purpose='Hold the concern pending clarification',
                            slot_key='clarify', source_ids=situation.memory_ids, self_generated=event.origin == 'SELF_WAKE')
            pending = self.pending(event.scope)
            duplicate_slot = any(r['slot_key'] == intention.slot_key for r in pending)
            global_pending = self.store.db.execute(
                "SELECT count(*) FROM subject_intentions i JOIN continuity_records r ON r.record_id=i.record_id "
                "WHERE i.state='PENDING' AND i.expires_at_us>? AND r.lifecycle='ACTIVE'",
                (self.store.clock.utc_now_us(),)).fetchone()[0]
            # An accepted own question/plan has no pending execution binding. Its
            # formation is completed in this same transaction after recording;
            # it does not consume the asynchronous intention queue's capacity.
            if private_question is None and private_plan is None and intention.kind!='NO_ACTION' and (global_pending >= MAX_PENDING or duplicate_slot):
                from .contracts import Intention, Judgment
                attention = 'DEFER'
                judgment = Judgment(stance='DEFER', reason='A matching concern is already pending or attention is full', source_ids=situation.memory_ids)
                intention = Intention(kind='NO_ACTION', purpose='Keep existing concern without duplicate initiative',
                    slot_key='quiet', source_ids=situation.memory_ids, self_generated=event.origin == 'SELF_WAKE')
            social=None
            if request_decision and request_decision.decision=='NEGOTIATE':
                social=propose_social(topic='commitment.scope',style='RESPECTFUL_EXPLICIT',available=True,source_ids=situation.memory_ids)
            if situation.context_fit and event.interaction_signal:
                from .context_fit import social_candidate
                social=social_candidate(situation.context_fit,style=situation.interaction_style,source_ids=situation.memory_ids,available=event.observed_availability!='BUSY')
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
            if event.growth_assessment_id and intention.kind=='SOCIAL_INTERACTION' and situation.cue.availability=='AVAILABLE':
                from .social import SocialInteractionProposal
                social=SocialInteractionProposal(act='REPORT_DISCOVERY',topic_key=situation.cue.topic_key,approach='CHECK_RECEPTION',source_memory_ids=situation.memory_ids)
            if social and situation.context_fit and not situation.context_fit.allow_delivery:
                from .social import SocialInteractionProposal
                social=SocialInteractionProposal(act='STAY_SILENT',topic_key=situation.context_fit.topic_key,approach='NO_INTERRUPTION',source_memory_ids=situation.memory_ids)
            action=None
            if intention.kind=='EXPLORE' and situation.cue and situation.cue.resource_ref:
                action=SyntheticActionProposal(resource_ref=situation.cue.resource_ref,resource_class=situation.cue.resource_class,source_memory_ids=situation.memory_ids)
            target=event.realization_target if evaluation and evaluation.normative=='ENDORSED' else None
            if target and situation.cue and situation.cue.resource_ref and not situation.plan_step:
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
            from .context_fit import consider_communication
            communication,communication_proposal=consider_communication(self.store,event,situation,intention,evaluation,privacy_classes=self.privacy_classes)
            result = CycleResult(communication_choice=communication,conversation_decision=conversation,context_fit=situation.context_fit,cycle_id=cycle_id, event_id=source['subject_event_id'], revision=expected_revision + 1,
                admission=source['admission'], appraisal=appraisal, motivations=motives, attention=attention,
                judgment=judgment, intention=intention, intention_id=intention_id, goal_candidate_id=candidate_id,
                barrier='NO_ACTION' if intention.kind == 'NO_ACTION' else 'SHADOW_BLOCKED', record_id=None,social_proposal=social,action_proposal=action,
                evaluation=evaluation,disclosure=disclosure,request_decision=request_decision,selected_disposition_id=event.disposition_reflection_id,
                realization_target=target,relational_decision=relational,
                proposed_program_id=(situation.problem_frame.program_id if situation.problem_frame and judgment.stance=='ALTERNATIVE' and intention.purpose==situation.problem_frame.considered_problem else situation.cue.program_id if situation.cue else None) if candidate_id else None,
                problem_frame=situation.problem_frame,
                experience_need=situation.experience_need,
                selected_memory_candidate_id=event.memory_review_id,
                deliberation=None if _deliberation is None else {
                    'model_descriptor': _deliberation.model_descriptor,
                    'context_digest': _deliberation.context_digest, 'raw_proposal_json':
                        canonical(_deliberation.proposal.model_copy(update={'private_question':None,'private_plan':None,'passing_thought':None,
                            'interpretation':'Private deliberation contents withheld from the ordinary cycle trace'}).model_dump(mode='json'))
                        if _deliberation.proposal.passing_thought or _deliberation.proposal.private_question or _deliberation.proposal.private_plan
                            or _deliberation.proposal.preferred_behavior is not None or situation.private_interest_records else _deliberation.raw_proposal_json})
            record = None
            if parents or supports:
                record = self.records.create(tx, kind='SUBJECT_CYCLE', scope=event.scope,
                    payload=result.model_dump(mode='json'), records=parents, memories=supports)
                if evaluation:
                    from ..autonomy.history import record_disposition
                    record_disposition(self.store,tx,cycle_id=cycle_id,intention_id=intention_id,intention_revision=1,
                        scope=event.scope,parent_record=record,stage='SUBJECT',code=evaluation.disposition,
                        normative=evaluation.normative,wanted=evaluation.wanted,reason_refs=evaluation.reason_refs)
            if conversation and record:
                from ..person_self import commit
                commit(self.store,tx,event,conversation,record)
            tx.put('subject_cycles', {'cycle_id': cycle_id, 'subject_event_id': source['subject_event_id'],
                'revision': expected_revision + 1, 'record_id': record, 'judgment': judgment.stance,
                'attention': attention, 'barrier': result.barrier, 'created_at_us': self.store.clock.utc_now_us()})
            tx.put('core_meta', {'key': 'self.subject_revision', 'value_json': canonical(expected_revision + 1)})
            if self.store.schema_target>=13:
                from ..autonomy.private_intent import after_choice
                after_choice(self.store,tx,event,result.model_copy(update={'record_id':record}),privacy_classes=self.privacy_classes,
                    selected_topic=situation.cue.topic_key if situation.cue else event.topic,
                    private_intent_ref=situation.cue.private_intent_ref if situation.cue else None,private_question=private_question,private_plan=private_plan)
                from .context_fit import record_communication_strategy
                record_communication_strategy(self.store,tx,event,result.model_copy(update={'record_id':record}),communication_proposal,
                    privacy_classes=self.privacy_classes)
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

    def reflect(self, experience_id, *, authority, expected_revision=None, apply=False,intention_id=None):
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
        if intention_id:
            intention=self.store.one('subject_intentions',intention_id)
            if not intention or intention['kind']!='REFLECTION':raise CoreError('REFLECTION_INTENTION_MISMATCH')
            source=self.store.one('subject_events',intention['subject_event_id'])
            recorded=self.records.read(source['record_id'])['payload']['input']
            if recorded.get('reflection_experience_id')!=experience_id or not self.records.current_support(row['record_id']):raise CoreError('REFLECTION_INTENTION_MISMATCH')
            if intention['state']=='PENDING':
                # Proposing the traceable reflection fulfilled thinking; it did
                # not adopt the proposed lesson, change identity or learn a rule.
                with self.store.transaction('subject.reflection_intention_completed',{'intention_id':intention_id,'reflection_id':reflection_id,'experience_id':experience_id}) as tx:
                    tx.update('subject_intentions',intention_id,state='COMPLETED',revision=intention['revision']+1)
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
        if attention == 'IGNORE' or (situation.context_fit and not situation.context_fit.allow_deepening):
            return self.run(event, expected_revision=revision)
        from .contracts import DeliberationFrame
        frame = DeliberationFrame(subject_event_id=source['subject_event_id'], scope=event.scope,
            appraisal=appraisal,motivations=motives,attention=attention,
            source_memory_ids=situation.memory_ids,source_record_ids=situation.support_record_ids,
            behavior_options=tuple(dict.fromkeys(directions(situation.cue))) if situation.cue else ())
        assembler = ContextAssembler(self.store, authority)
        request = ContextRequest(entity_id=event.entity_id, scopes=(event.scope,),
            task_class=event.task_class or 'subject_deliberation',
            task=event.text or 'Assess current concerns; silence is allowed', task_privacy_class=event.privacy_class,
            max_input_tokens=65536, output_reserve_tokens=4096)
        context = assembler.assemble(request, policy, subject_frame=frame,capabilities=capabilities,limitations=limitations)
        result = DeliberationSession(assembler).run(model, context, request, policy)
        assembler.validate(context, request, policy)
        if self.store.schema_target>=13 and not situation.memory_ids and not situation.support_record_ids:
            from ..autonomy.private_intent import consider_question,consider_plan,anchor_own_occurrence
            _,judgment,intention=decide(event,situation,appraisal,motives)
            if (consider_question(event,situation,judgment,intention,result.proposal.private_question) is not None
                    or consider_plan(event,situation,judgment,intention,result.proposal.private_plan) is not None):
                # The recorded fact is this validated candidate occurrence. It
                # is not a new external observation or an adopted world belief.
                event=anchor_own_occurrence(self.store,event,authority=authority)
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
