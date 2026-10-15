"""Normative interpretation within C; no Manager, Grant or execution queries."""
from ...contracts import CoreError
from ..subject.opportunities import directions
from .contracts import SubjectEvaluation

def evaluate(event,situation,attention,judgment,intention):
    motive=bool(situation.cue or situation.unresolved_interest or situation.due_commitment_ids)
    hard_unavailable=bool(situation.cue and situation.cue.resource_ref and situation.cue.resource_class!='ORDINARY')
    restrained=bool(situation.cue and (set(directions(situation.cue))<=set(situation.prohibited_behaviors)
        or (situation.social_privacy and situation.social_privacy.assessment in {'EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN'} and intention.kind=='NO_ACTION')))
    if restrained and not hard_unavailable:
        normative,code='RESTRAINED','SUBJECT_RESTRAINED'
    elif intention.kind not in {'NO_ACTION','WAIT'}:
        normative,code='ENDORSED','SUBJECT_ENDORSED'
    else:normative,code='UNDECIDED','SUBJECT_DEFERRED' if attention in {'DEFER','RECALL_LATER'} or hard_unavailable else 'SUBJECT_DROPPED'
    return SubjectEvaluation(normative=normative,disposition=code,considered=motive or normative=='ENDORSED',wanted=motive or normative=='ENDORSED',
        reason_refs=situation.memory_ids)
