"""Normative interpretation within C; no Manager, Grant or execution queries."""
from ...contracts import CoreError
from ..subject.opportunities import directions
from .contracts import SubjectEvaluation

def unbound_private_choice(event,situation,intention):
    """Reception expectations do not prohibit an own, unbound mental choice.

    This classifies the selected C intention, not execution authority. Resource,
    program and goal bindings still follow the existing restraint path.
    """
    return bool(event.origin=='SELF_WAKE' and intention.self_generated and situation.cue
        and intention.behavior in {'CREATE','LEARN','EXPLORE','REFLECT','WATCH','REST','WITHDRAW','IGNORE','DEFER','STAY_SILENT','DO_NOTHING'}
        and intention.behavior in directions(situation.cue)
        and not any((event.realization_target,event.goal_step,event.goal_review,
            situation.cue.resource_ref,situation.cue.program_id,situation.plan_step)))

def evaluate(event,situation,attention,judgment,intention):
    motive=bool(situation.cue or situation.unresolved_interest or situation.due_commitment_ids)
    hard_unavailable=bool(situation.cue and situation.cue.resource_ref and situation.cue.resource_class!='ORDINARY')
    restrained=bool(situation.cue and (set(directions(situation.cue))<=set(situation.prohibited_behaviors)
        or (situation.social_privacy and situation.social_privacy.assessment in {'EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN'}
            and intention.kind=='NO_ACTION' and not unbound_private_choice(event,situation,intention))))
    restrained=restrained or bool(situation.context_fit and situation.context_fit.mode=='RESPECT_BOUNDARY' and motive and intention.kind=='NO_ACTION')
    from ..subject.policy import current_directions,voluntary_restraint_applies
    restrained=restrained or bool(intention.kind=='NO_ACTION' and intention.behavior=='STAY_SILENT'
        and voluntary_restraint_applies(event,situation,current_directions(situation)))
    if restrained and not hard_unavailable:
        normative,code='RESTRAINED','SUBJECT_RESTRAINED'
    elif intention.kind not in {'NO_ACTION','WAIT'}:
        normative,code='ENDORSED','SUBJECT_ENDORSED'
    else:normative,code='UNDECIDED','SUBJECT_DEFERRED' if attention in {'DEFER','RECALL_LATER'} or hard_unavailable else 'SUBJECT_DROPPED'
    return SubjectEvaluation(normative=normative,disposition=code,considered=motive or normative=='ENDORSED',wanted=motive or normative=='ENDORSED',
        reason_refs=situation.memory_ids)
