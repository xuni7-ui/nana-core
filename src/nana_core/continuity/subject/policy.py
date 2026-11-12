"""Pure, inspectable initial C policy. No clock, storage, random or executor."""
from ...contracts import DTO
from .contracts import Appraisal, Intention, Judgment, Motivation, SubjectInput
from .opportunities import ConcernCue,directions
from ..relational.contracts import SocialAppetiteView
from ..autonomy.contracts import RelationshipInfluenceView,SocialPrivacyExpectation
from ..agency_contracts import PlanStepView
from .context_fit import ContextFitAssessment
from .framing import FrameAssessment
from .experience_need import ExperienceNeed


class Situation(DTO):
    experience_need: ExperienceNeed | None = None
    problem_frame: FrameAssessment | None = None
    context_fit: ContextFitAssessment | None = None
    scope: str
    memory_ids: tuple[str, ...]
    project_ids: tuple[str, ...]
    commitment_ids: tuple[str, ...]
    due_commitment_ids: tuple[str, ...]
    adopted_interests: tuple[str, ...]
    unresolved_interest: str | None
    familiar: bool
    allowed_methods: tuple[str, ...]
    lesson_ids: tuple[str, ...]
    lesson_record_ids: tuple[str, ...]
    support_record_ids: tuple[str, ...]
    pending_count: int
    idle: bool
    cue: ConcernCue | None = None
    prohibited_behaviors: tuple[str,...] = ()
    interaction_style: str = 'RESPECTFUL_EXPLICIT'
    last_social_act: str | None = None
    reflection_experience_id: str | None = None
    manager_outcomes: tuple[dict,...] = ()
    relationship_influence: RelationshipInfluenceView | None = None
    social_privacy: SocialPrivacyExpectation | None = None
    autonomy_semantics: bool = False
    social_appetite: SocialAppetiteView | None = None
    voluntary_restraints: tuple[str,...] = ()
    plan_step: PlanStepView | None = None
    memory_review_id: str | None = None
    adopted_program_ids: tuple[str,...] = ()
    separate_delivery: bool = False
    goal_review_id: str | None = None


def appraise(event: SubjectInput, situation: Situation):
    conflict = bool(event.proposed_method and situation.allowed_methods and event.proposed_method not in situation.allowed_methods)
    norm_conflict=bool(situation.cue and set(directions(situation.cue))&set(situation.prohibited_behaviors))
    reasons = []
    if conflict:
        reasons.append('proposal conflicts with a current sourced project constraint')
    if situation.due_commitment_ids:
        reasons.append('an adopted commitment is due')
    if situation.unresolved_interest:
        reasons.append('supported interest remains unresolved')
    if not reasons:
        reasons.append('evaluate input without assuming it is an adopted goal')
    if situation.context_fit:reasons.append(situation.context_fit.reason)
    if situation.cue:
        reasons.append('a current source-backed concern offers options; it is not an adopted intention')
    assessment=situation.cue.opportunity_assessment if situation.cue else None
    return Appraisal(novelty='LOW' if assessment and assessment.novelty=='REPEATED' else event.novelty,
        goal_relevance='RELEVANT' if situation.project_ids or situation.plan_step or situation.adopted_program_ids else 'NONE',
        relationship_relevance='RELEVANT' if situation.familiar or event.relationship_kind else 'LOW',
        self_relevance='RELEVANT' if event.preference_signal else 'LOW',
        unfinished_tension='HIGH' if situation.due_commitment_ids else 'RELEVANT' if situation.unresolved_interest else 'NONE',
        interest_relevance='HIGH' if situation.unresolved_interest else 'LOW', risk=event.risk,
        conflict='HIGH' if conflict or norm_conflict else 'NONE', urgency='HIGH' if situation.due_commitment_ids else event.urgency,
        expected_value=assessment.value if assessment else 'RELEVANT' if situation.unresolved_interest or situation.project_ids else 'LOW',
        uncertainty=event.uncertainty, privacy_relevance='HIGH' if event.privacy_class in {'PERSONAL','SECRET'} else 'LOW',
        source_ids=situation.memory_ids, reasons=tuple(reasons))


def motivate(event, situation, appraisal):
    motives = []
    if situation.plan_step:
        motives.append(Motivation(source='ADOPTED_GOAL',strength='RELEVANT',source_ids=(situation.plan_step.goal_id,situation.plan_step.record_id)))
    if situation.due_commitment_ids:
        motives.append(Motivation(source='COMMITMENT', strength='PRESSING', source_ids=situation.due_commitment_ids))
    if situation.project_ids:
        motives.append(Motivation(source='PROJECT_COMPLETION', strength='RELEVANT', source_ids=situation.project_ids))
    if situation.unresolved_interest:
        motives.append(Motivation(source='EXPLORATION', strength='RELEVANT', source_ids=situation.memory_ids))
    if event.novelty == 'HIGH':
        motives.append(Motivation(source='CURIOSITY', strength='AVAILABLE', source_ids=situation.memory_ids))
    if (situation.social_appetite and situation.social_appetite.state in {'OPEN','SEEKING'}) or (situation.social_appetite is None and event.kind == 'INTERACTION' and situation.familiar):
        motives.append(Motivation(source='SOCIAL_CONNECTION', strength='AVAILABLE', source_ids=situation.memory_ids))
    if appraisal.risk == 'HIGH':
        motives.insert(0, Motivation(source='CARE', strength='PRESSING', source_ids=situation.memory_ids))
    if situation.cue:
        motives.append(Motivation(source=situation.cue.motivation_source,strength='RELEVANT',source_ids=situation.memory_ids))
        if situation.cue.cognitive_load=='HIGH' and situation.cue.motivation_source!='REST':
            motives.append(Motivation(source='REST',strength='RELEVANT',source_ids=situation.memory_ids))
    if situation.problem_frame and situation.problem_frame.state=='REFRAME':
        motives.append(Motivation(source='UNRESOLVED_QUESTION',strength='RELEVANT',source_ids=situation.problem_frame.source_memory_ids))
    if not motives:
        motives.append(Motivation(source='REST', strength='AVAILABLE', source_ids=()))
    return tuple(motives)


def decide(event, situation, appraisal, motives):
    """Source-backed obligations, constraints and interests; no execution power."""
    sources, self_generated = situation.memory_ids, event.origin == 'SELF_WAKE'
    if event.retention == 'DO_NOT_REMEMBER':
        return ('IGNORE', Judgment(stance='IGNORE', reason='Honor non-retention; do not form a long-term inference', source_ids=()),
            Intention(kind='NO_ACTION', purpose='Let this input pass without retention', slot_key='quiet', source_ids=(), self_generated=self_generated))
    from .context_fit import choose
    context_choice=choose(event,situation)
    if context_choice and (situation.context_fit.mode in {'RESPECT_BOUNDARY','VENT','SHARE','CHAT','CORRECTION','FOCUS','UNCLEAR','PROJECT_STATUS'}):return context_choice
    if appraisal.risk == 'HIGH' and appraisal.uncertainty in {'RELEVANT','HIGH'}:
        return ('FOCUS_NOW', Judgment(stance='ASK', reason='Risk needs clarification, not unsupported escalation', source_ids=sources),
            Intention(kind='WAIT', purpose='Hold concern without contacting anyone', slot_key='clarify', source_ids=sources, self_generated=self_generated))
    if appraisal.conflict == 'HIGH' and event.proposed_method and situation.allowed_methods:
        return ('FOCUS_NOW', Judgment(stance='ALTERNATIVE', reason='Prefer the method consistent with recorded project constraints',
            source_ids=sources, selected_method=situation.allowed_methods[0]),
            Intention(kind='DISAGREE', purpose='Explain a sourced alternative without overriding the user', slot_key='project-alternative', source_ids=sources, self_generated=False,behavior='DISAGREE'))
    if situation.problem_frame and not situation.due_commitment_ids and not (situation.cue and situation.cue.cognitive_load=='HIGH') and 'CONTINUE_PROJECT' not in situation.prohibited_behaviors and (not situation.context_fit or situation.context_fit.allow_new_work):
        frame=situation.problem_frame
        if frame.state=='REFRAME':
            return ('FOCUS_NOW',Judgment(stance='ALTERNATIVE',reason=frame.reason,source_ids=sources),
                Intention(kind='GOAL_CANDIDATE',purpose=frame.considered_problem,slot_key='frame-'+frame.program_id,source_ids=sources,self_generated=self_generated,behavior='CONTINUE_PROJECT'))
        if frame.state=='INSUFFICIENT_EVIDENCE':
            return ('FOCUS_NOW',Judgment(stance='ASK',reason=frame.reason,source_ids=sources),
                Intention(kind='WAIT',purpose='Clarify the premise before choosing a different problem',slot_key='frame-clarify',source_ids=sources,self_generated=self_generated))
    if context_choice:return context_choice
    # A due promise remains a pressing motive, not a permanent ban on an
    # already adopted personal interest. An explicit promise review still wins;
    # ordinary interest cues continue through the same norm/load/value guards.
    personal_interest = bool(situation.cue
        and situation.cue.topic_key in situation.adopted_interests)
    options=[x for x in directions(situation.cue) if x not in situation.prohibited_behaviors] if situation.cue else []
    quiet_choice=bool(options and options[0] in {'REST','WITHDRAW','IGNORE','WATCH','STAY_SILENT','DO_NOTHING','DEFER'})
    # A due promise remains visible/pressing without making rest or silence
    # unavailable. An explicit promise review still takes its original route;
    # quiet choices later pass the same norm/privacy/resource admission.
    if situation.due_commitment_ids and (event.commitment_check_id or not (personal_interest or quiet_choice)):
        return ('FOCUS_NOW', Judgment(stance='DEFER', reason='An adopted due commitment takes priority over optional exploration', source_ids=sources),
            Intention(kind='GOAL_CANDIDATE', purpose='Review a due commitment; no execution has been authorized', slot_key='commitment-review', source_ids=sources, self_generated=self_generated))
    if situation.reflection_experience_id:
        return ('FOCUS_NOW',Judgment(stance='REFLECT',reason='An independently recorded experience is eligible for reflection',source_ids=sources),
            Intention(kind='REFLECTION',purpose='Examine the recorded outcome without inventing new history',slot_key='reflect-'+situation.reflection_experience_id,
                source_ids=sources,self_generated=self_generated,behavior='REFLECT'))
    if situation.goal_review_id and event.goal_review and event.goal_review.purpose=='LIFECYCLE':
        # Ending a sourced adopted goal does not start more work. Attention
        # load can defer continuation, but must not turn withdrawal into a pause.
        # Current load is a rest motive, not a compulsory pause of every
        # urgent, supported continuation. Conversely urgency cannot invent a
        # continuation when the current cue only offers rest. Norms still apply.
        can_continue=('CONTINUE_PROJECT' not in situation.prohibited_behaviors
            and (situation.cue is None or 'CONTINUE_PROJECT' in options))
        loaded=bool(situation.cue and situation.cue.cognitive_load=='HIGH')
        urgent=bool(situation.cue and situation.cue.urgency=='HIGH')
        if 'WITHDRAW' in options:behavior='WITHDRAW'
        elif not can_continue or (loaded and not urgent):
            behavior='REST' if 'REST' not in situation.prohibited_behaviors else None
        else:behavior='CONTINUE_PROJECT'
        quiet=behavior in {'REST',None}
        return ('DEFER' if quiet else 'FOCUS_NOW',Judgment(stance='DEFER' if quiet else 'AGREE',reason='Review sourced goal ownership, current load and urgency without inventing work or replaying its plan',source_ids=sources),
            Intention(kind='GOAL_CANDIDATE' if behavior=='CONTINUE_PROJECT' else 'NO_ACTION',purpose='Review the existing goal lifecycle without creating a new goal or permission',slot_key='lifecycle-'+situation.goal_review_id,source_ids=sources,self_generated=self_generated,behavior=behavior))
    if situation.goal_review_id and not (situation.cue and situation.cue.cognitive_load=='HIGH'):
        return ('FOCUS_NOW',Judgment(stance='ALTERNATIVE',reason='A checked new method warrants reconsidering a supported goal; no old action is retried',source_ids=sources,lesson_ids=situation.lesson_ids),Intention(kind='GOAL_CANDIDATE',purpose='Reconsider the plan using independently checked learning',slot_key='revise-'+situation.goal_review_id,source_ids=sources,self_generated=self_generated,behavior='LEARN'))
    if situation.memory_review_id and (situation.pending_count>=6 or (situation.cue and situation.cue.cognitive_load=='HIGH')):
        return ('DEFER',Judgment(stance='DEFER',reason='Current sourced commitments or attention load outweigh optional consolidation; keep its sources and review after conditions change',source_ids=sources),
            Intention(kind='NO_ACTION',purpose='Rest or finish existing intentions before optional memory work',slot_key='quiet',source_ids=sources,self_generated=True,behavior='REST'))
    if situation.memory_review_id:
        return ('BACKGROUND_WATCH',Judgment(stance='REMEMBER',reason='Preserve a source-linked bounded summary as derived memory, never a new observation',source_ids=sources),Intention(kind='MEMORY_CANDIDATE',purpose='Admit a traceable derived summary',slot_key='summary-'+situation.memory_review_id,source_ids=sources,self_generated=True,behavior='MAINTAIN'))
    if situation.voluntary_restraints and situation.cue and 'SOCIALIZE' in directions(situation.cue) and event.urgency!='HIGH':
        return ('DEFER',Judgment(stance='DEFER',reason='Honor a current bounded self-chosen accommodation; retain desire and permit later review',source_ids=sources),
            Intention(kind='NO_ACTION',purpose='Choose temporary restraint without losing social desire',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='STAY_SILENT'))
    if situation.plan_step:
        if situation.cue and (situation.cue.cognitive_load=='HIGH' or set(directions(situation.cue))<=set(situation.prohibited_behaviors)):
            return ('DEFER',Judgment(stance='DEFER',reason='Pause an adopted plan while a sourced load or norm deserves attention',source_ids=sources),Intention(kind='NO_ACTION',purpose='Wait before continuing the plan',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='REST'))
        ref=situation.plan_step.reference
        return ('FOCUS_NOW',Judgment(stance='AGREE',reason='Continue one supported adopted-plan step; execution authority is checked separately',source_ids=sources,lesson_ids=situation.lesson_ids),Intention(kind='ACTION_PROPOSAL',purpose='Propose the next reviewed plan step',slot_key='step-'+ref.work_id+'-'+str(ref.cursor),source_ids=sources,self_generated=self_generated,behavior='CONTINUE_PROJECT'))
    if situation.cue:
        cue=situation.cue
        if cue.program_id and cue.program_id in situation.adopted_program_ids:
            return ('BACKGROUND_WATCH',Judgment(stance='WATCH',reason='An adopted goal already carries this concern; do not duplicate it',source_ids=sources),Intention(kind='NO_ACTION',purpose='Let the existing plan progress',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='WATCH'))
        if not options or (cue.resource_ref and cue.resource_class!='ORDINARY' and not situation.autonomy_semantics):
            return ('IGNORE',Judgment(stance='IGNORE',reason='A sourced norm/privacy constraint inhibits the possible opportunity',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Honor constraints rather than act merely because it is possible',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='IGNORE'))
        behavior=options[0]
        # Quiet/withdrawal options start no work and do not need instrumental
        # value, novelty or spare capacity. Norm/privacy filtering still precedes them.
        if quiet_choice:
            return ('BACKGROUND_WATCH' if behavior=='WATCH' else 'DEFER',Judgment(stance='WATCH' if behavior=='WATCH' else 'DEFER',reason='An available concern does not require activity',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Respect the current priority without external action',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior=behavior))
        assessment=cue.opportunity_assessment
        # Generic utility/novelty does not erase a current source-backed personal
        # interest. Enjoyment need not promise learning or task productivity.
        interested_learning = (cue.learning_value is not None
            and cue.learning_value.interest in {'RELEVANT', 'HIGH'}
            and bool(set(options) & {'LEARN', 'SEEK_CAPABILITY'}))
        interested_activity = personal_interest and bool(set(options) & {'EXPLORE', 'CREATE'})
        # A current independent social preference/seed can support ordinary
        # company without instrumental or relationship value. OPEN from this
        # same cue alone has no such record support. Actual reception/authority
        # remains the existing separate DeliveryAdmission/Kernel consideration.
        interested_social = bool(situation.separate_delivery and 'SOCIALIZE' in options
            and situation.social_appetite and situation.social_appetite.state in {'OPEN','SEEKING'}
            and situation.social_appetite.source_record_ids)
        demanding = cue.attention_demand=='HEAVY' or bool(cue.learning_value and cue.learning_value.time_compute_cost=='HEAVY')
        supported_light_interest = not demanding and (interested_learning or interested_activity or interested_social)
        # Current load remains a sourced rest motive. It does not require the
        # Subject to stop every light, supported interest or private wish to
        # connect. Actual execution and reception are admitted separately.
        if cue.cognitive_load=='HIGH' and cue.urgency!='HIGH' and not supported_light_interest:
            return ('DEFER',Judgment(stance='DEFER',reason='Current load outweighs this demanding or unsupported optional direction',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Keep the option while choosing rest for now',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='REST'))
        if assessment and (assessment.value=='LOW' or assessment.novelty=='REPEATED') and not (interested_learning or interested_activity or interested_social):
            return ('BACKGROUND_WATCH',Judgment(stance='IGNORE',reason='Current low value or repeated low-stimulation evidence does not warrant another activity; this is the Subject decision, not a Runtime veto',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Consider the motive and choose not to act on this opportunity',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='IGNORE'))
        if cue.attention_demand=='HEAVY' and cue.urgency!='HIGH' and not (interested_learning or interested_activity or interested_social):
            return ('DEFER',Judgment(stance='DEFER',reason='A demanding optional activity has no current supported interest outweighing its demand; this is not evidence of fatigue',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Leave this costly optional activity for a later choice',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='REST'))
        value=cue.learning_value
        if value and set(options)&{'LEARN','SEEK_CAPABILITY'}:
            low_value=value.goal_value=='LOW' and value.future_reuse=='LOW' and value.interest=='LOW' and value.relationship_relevance=='LOW'
            # An existing capability does not cancel a sourced interest in learning.
            if low_value or (value.alternative=='AVAILABLE' and value.interest=='LOW'):
                return ('BACKGROUND_WATCH',Judgment(stance='WATCH',reason='NOT_WORTH_LEARNING: limited reuse/value or an available existing capability makes new learning unnecessary',source_ids=sources),
                    Intention(kind='NO_ACTION',purpose='Keep the gap visible without compulsory learning or creating a redundant plugin',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='WATCH'))
            if value.risk=='HIGH' or (value.time_compute_cost=='HEAVY' and cue.urgency!='HIGH' and not interested_learning):
                return ('DEFER',Judgment(stance='DEFER',reason='Learning value does not currently justify its cost or risk',source_ids=sources),
                    Intention(kind='NO_ACTION',purpose='Defer learning while retaining the original interest',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='REST'))
        share=cue.share_assessment
        if share and 'SOCIALIZE' in options:
            low=share.relational_relevance=='LOW' and share.affect_relevance=='LOW' and share.urgency=='LOW'
            redundant=share.novelty=='REPEATED' and share.recent_delivery_frequency=='HIGH' and share.urgency!='HIGH'
            if share.user_preference=='DECLINED' or redundant or (low and not interested_social):
                return ('BACKGROUND_WATCH',Judgment(stance='WATCH',reason='A real wish to share can remain private: limited relevance, declined topic or repeated interruption does not warrant expression',source_ids=sources),Intention(kind='NO_ACTION',purpose='Keep the sourced experience without manufacturing a notification',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='STAY_SILENT'))
        if behavior=='SOCIALIZE' and cue.availability!='AVAILABLE' and not situation.separate_delivery:
            return ('DEFER',Judgment(stance='DEFER',reason='Availability is unknown/busy; prefer silence over interruption',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Wait for a receptive context',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='STAY_SILENT'))
        kind='SOCIAL_INTERACTION' if behavior=='SOCIALIZE' else 'EXPLORE' if behavior=='EXPLORE' else 'GOAL_CANDIDATE'
        reason='A supported light interest can coexist with current load; rest remains available and execution is separately admitted' if cue.cognitive_load=='HIGH' else 'Current evidence supports considering this direction within constraints'
        return ('FOCUS_NOW',Judgment(stance='THINK_MORE',reason=reason,source_ids=sources,lesson_ids=situation.lesson_ids),
            Intention(kind=kind,purpose='Consider '+behavior.lower()+' for the unresolved topic '+cue.topic_key,
                slot_key='concern-'+cue.topic_key,source_ids=sources,self_generated=self_generated,behavior=behavior))
    if event.task_class == 'reading_card' and situation.lesson_ids:
        return ('FOCUS_NOW', Judgment(stance='ALTERNATIVE', reason='Verified earlier failure makes source location a necessary planning step',
            source_ids=sources, selected_method='locate_then_draft', lesson_ids=situation.lesson_ids),
            Intention(kind='GOAL_CANDIDATE', purpose='Locate source before drafting the next reading card', slot_key='reading-card', source_ids=sources, self_generated=self_generated))
    if event.task_class == 'reading_card':
        return ('FOCUS_NOW', Judgment(stance='THINK_MORE', reason='Draft a card with available evidence; no learned locator requirement is active',
            source_ids=sources, selected_method='draft'),
            Intention(kind='GOAL_CANDIDATE', purpose='Prepare a reading-card proposal', slot_key='reading-card', source_ids=sources, self_generated=self_generated))
    if situation.unresolved_interest and situation.idle and situation.pending_count < 8:
        return ('FOCUS_NOW', Judgment(stance='THINK_MORE', reason='Supported interest and available attention justify an optional exploration candidate', source_ids=sources),
            Intention(kind='EXPLORE', purpose=f'Explore the unresolved interest: {situation.unresolved_interest}',
                slot_key='explore-' + situation.unresolved_interest, source_ids=sources, self_generated=self_generated))
    if event.kind == 'WAKE':
        return ('BACKGROUND_WATCH', Judgment(stance='WATCH', reason='No worthwhile new intention; staying quiet is a valid choice', source_ids=sources),
            Intention(kind='NO_ACTION', purpose='Remain present without demanding interaction', slot_key='quiet', source_ids=sources, self_generated=True))
    return ('RECALL_LATER' if event.significance == 'HIGH' else 'BACKGROUND_WATCH',
        Judgment(stance='REMEMBER' if event.significance in {'RELEVANT','HIGH'} else 'WATCH',
            reason='Retain relevant context without treating a request as execution authority', source_ids=sources),
        Intention(kind='NO_ACTION', purpose='Attend without external action', slot_key='quiet', source_ids=sources, self_generated=False))
