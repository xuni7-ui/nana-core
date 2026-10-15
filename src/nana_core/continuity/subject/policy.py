"""Pure, inspectable initial C policy. No clock, storage, random or executor."""
from ...contracts import DTO
from .contracts import Appraisal, Intention, Judgment, Motivation, SubjectInput
from .opportunities import ConcernCue


class Situation(DTO):
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


def appraise(event: SubjectInput, situation: Situation):
    conflict = bool(event.proposed_method and situation.allowed_methods and event.proposed_method not in situation.allowed_methods)
    norm_conflict=bool(situation.cue and set(situation.cue.possible_behaviors)&set(situation.prohibited_behaviors))
    reasons = []
    if conflict:
        reasons.append('proposal conflicts with a current sourced project constraint')
    if situation.due_commitment_ids:
        reasons.append('an adopted commitment is due')
    if situation.unresolved_interest:
        reasons.append('supported interest remains unresolved')
    if not reasons:
        reasons.append('evaluate input without assuming it is an adopted goal')
    if situation.cue:
        reasons.append('a current source-backed concern offers options; it is not an adopted intention')
    return Appraisal(novelty=event.novelty,
        goal_relevance='RELEVANT' if situation.project_ids else 'NONE',
        relationship_relevance='RELEVANT' if situation.familiar or event.relationship_kind else 'LOW',
        self_relevance='RELEVANT' if event.preference_signal else 'LOW',
        unfinished_tension='HIGH' if situation.due_commitment_ids else 'RELEVANT' if situation.unresolved_interest else 'NONE',
        interest_relevance='HIGH' if situation.unresolved_interest else 'LOW', risk=event.risk,
        conflict='HIGH' if conflict or norm_conflict else 'NONE', urgency='HIGH' if situation.due_commitment_ids else event.urgency,
        expected_value='RELEVANT' if situation.unresolved_interest or situation.project_ids else 'LOW',
        uncertainty=event.uncertainty, privacy_relevance='HIGH' if event.privacy_class in {'PERSONAL','SECRET'} else 'LOW',
        source_ids=situation.memory_ids, reasons=tuple(reasons))


def motivate(event, situation, appraisal):
    motives = []
    if situation.due_commitment_ids:
        motives.append(Motivation(source='COMMITMENT', strength='PRESSING', source_ids=situation.due_commitment_ids))
    if situation.project_ids:
        motives.append(Motivation(source='PROJECT_COMPLETION', strength='RELEVANT', source_ids=situation.project_ids))
    if situation.unresolved_interest:
        motives.append(Motivation(source='EXPLORATION', strength='RELEVANT', source_ids=situation.memory_ids,
            inhibited_by=('COMMITMENT',) if situation.due_commitment_ids else ()))
    if event.novelty == 'HIGH':
        motives.append(Motivation(source='CURIOSITY', strength='AVAILABLE', source_ids=situation.memory_ids,
            inhibited_by=('COMMITMENT',) if situation.due_commitment_ids else ()))
    if event.kind == 'INTERACTION' and situation.familiar:
        motives.append(Motivation(source='SOCIAL_CONNECTION', strength='AVAILABLE', source_ids=situation.memory_ids))
    if appraisal.risk == 'HIGH':
        motives.insert(0, Motivation(source='CARE', strength='PRESSING', source_ids=situation.memory_ids))
    if situation.cue:
        motives.append(Motivation(source=situation.cue.motivation_source,strength='RELEVANT',source_ids=situation.memory_ids,
            inhibited_by=('COMMITMENT',) if situation.due_commitment_ids else ()))
    if not motives:
        motives.append(Motivation(source='REST', strength='AVAILABLE', source_ids=()))
    return tuple(motives)


def decide(event, situation, appraisal, motives):
    """Lexicographic obligations/constraints/interest arbitration, not a mood trigger."""
    sources, self_generated = situation.memory_ids, event.origin == 'SELF_WAKE'
    if event.retention == 'DO_NOT_REMEMBER':
        return ('IGNORE', Judgment(stance='IGNORE', reason='Honor non-retention; do not form a long-term inference', source_ids=()),
            Intention(kind='NO_ACTION', purpose='Let this input pass without retention', slot_key='quiet', source_ids=(), self_generated=self_generated))
    if appraisal.risk == 'HIGH' and appraisal.uncertainty in {'RELEVANT','HIGH'}:
        return ('FOCUS_NOW', Judgment(stance='ASK', reason='Risk needs clarification, not unsupported escalation', source_ids=sources),
            Intention(kind='WAIT', purpose='Hold concern without contacting anyone', slot_key='clarify', source_ids=sources, self_generated=self_generated))
    if appraisal.conflict == 'HIGH' and event.proposed_method and situation.allowed_methods:
        return ('FOCUS_NOW', Judgment(stance='ALTERNATIVE', reason='Prefer the method consistent with recorded project constraints',
            source_ids=sources, selected_method=situation.allowed_methods[0]),
            Intention(kind='DISAGREE', purpose='Explain a sourced alternative without overriding the user', slot_key='project-alternative', source_ids=sources, self_generated=False))
    if situation.due_commitment_ids:
        return ('FOCUS_NOW', Judgment(stance='DEFER', reason='An adopted due commitment takes priority over optional exploration', source_ids=sources),
            Intention(kind='GOAL_CANDIDATE', purpose='Review a due commitment; no execution has been authorized', slot_key='commitment-review', source_ids=sources, self_generated=self_generated))
    if situation.reflection_experience_id:
        return ('FOCUS_NOW',Judgment(stance='REFLECT',reason='An independently recorded experience is eligible for reflection',source_ids=sources),
            Intention(kind='REFLECTION',purpose='Examine the recorded outcome without inventing new history',slot_key='reflect-'+situation.reflection_experience_id,
                source_ids=sources,self_generated=self_generated,behavior='REFLECT'))
    if situation.cue:
        cue=situation.cue
        options=[x for x in cue.possible_behaviors if x not in situation.prohibited_behaviors]
        if not options or (cue.resource_ref and cue.resource_class!='ORDINARY'):
            return ('IGNORE',Judgment(stance='IGNORE',reason='A sourced norm/privacy constraint inhibits the possible opportunity',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Honor constraints rather than act merely because it is possible',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='IGNORE'))
        if cue.cognitive_load=='HIGH' and cue.urgency!='HIGH':
            return ('DEFER',Judgment(stance='DEFER',reason='Current load and lack of urgent duty make rest appropriate',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Rest instead of creating meaningless work',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='REST'))
        behavior=options[0]
        if behavior in {'REST','WITHDRAW','IGNORE','WATCH','STAY_SILENT','DO_NOTHING','DEFER'}:
            return ('BACKGROUND_WATCH' if behavior=='WATCH' else 'DEFER',Judgment(stance='WATCH' if behavior=='WATCH' else 'DEFER',reason='An available concern does not require activity',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Respect the current priority without external action',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior=behavior))
        if behavior=='SOCIALIZE' and cue.availability!='AVAILABLE':
            return ('DEFER',Judgment(stance='DEFER',reason='Availability is unknown/busy; prefer silence over interruption',source_ids=sources),
                Intention(kind='NO_ACTION',purpose='Wait for a receptive context',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='STAY_SILENT'))
        kind='SOCIAL_INTERACTION' if behavior=='SOCIALIZE' else 'EXPLORE' if behavior=='EXPLORE' else 'GOAL_CANDIDATE'
        return ('FOCUS_NOW',Judgment(stance='THINK_MORE',reason='Current evidence supports considering this direction within constraints',source_ids=sources,lesson_ids=situation.lesson_ids),
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
