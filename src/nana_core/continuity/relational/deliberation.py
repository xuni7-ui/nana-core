"""Qualitative context-sensitive tradeoff, no score, authority or extra loop."""
from ...contracts import CoreError
from ...storage import digest
from .contracts import (DAY,WillingDeferenceView,SelfAuthorshipAppraisal,DeliberationFactor,RelationalResponsePlan,RelationalDecision)
from .bootstrap import anchor_view
from .projections import personality_tendencies


def willing_deference(request,*,relationship,anchor,personality,appetite,commitments,request_refs):
    trait={f.name:f.assessment for f in personality.facets}
    trust=next((f for f in relationship.trust if f.domain==request.trust_domain),None)
    related=bool(anchor or relationship.familiarity.assessment=='FAMILIAR')
    counters=[]
    if relationship.repair_tension.assessment=='UNRESOLVED':counters.append('UNRESOLVED_REPAIR')
    if request.depends_on_statement and (not trust or trust.assessment not in {'SUPPORTED','RECOVERING'}):counters.append('DOMAIN_TRUST_INSUFFICIENT')
    if request.consequence=='HIGH':counters.append('SIGNIFICANT_CONSEQUENCE')
    if commitments:counters.append('EXISTING_COMMITMENTS')
    if not appetite.available:counters.append('COGNITIVE_LOAD')
    if appetite.state=='SEEKING' and request.operation=='REFRAIN':counters.append('RETAINED_SOCIAL_DESIRE')
    if trait['self_direction_sensitivity']=='HIGH':counters.append('SCOPE_SENSITIVITY')
    if anchor and anchor.spec.deference_baseline=='HIGH':level='STRONG'
    elif related and trust and trust.assessment=='SUPPORTED' and relationship.care_salience.assessment=='SALIENT':level='STRONG'
    elif related:level='MODERATE'
    else:level='UNKNOWN'
    if any(x in counters for x in ('DOMAIN_TRUST_INSUFFICIENT','UNRESOLVED_REPAIR')):level='LIMITED'
    return WillingDeferenceView(assessment=level,relationship_refs=tuple(dict.fromkeys((*relationship.source_record_ids,*((anchor.source_record_id,) if anchor else ())))),
        personality_refs=personality.source_record_ids,request_refs=request_refs,reason_refs=tuple(dict.fromkeys((*request_refs,*relationship.source_record_ids))),
        counterconsiderations=tuple(counters),domain=request.trust_domain)


def deliberate(store,event,situation,*,source_record_id,privacy_classes):
    request=event.relational_request
    if request is None:return None
    if not source_record_id or event.retention=='DO_NOT_REMEMBER':return None
    if request.requesting_entity!=event.entity_id:raise CoreError('RELATIONAL_REQUEST_ENTITY_MISMATCH')
    relation=situation.relationship_influence
    anchor=anchor_view(store,event.entity_id,scope=event.scope,privacy_classes=privacy_classes)
    person=personality_tendencies(store,scope=event.scope,privacy_classes=privacy_classes)
    appetite=situation.social_appetite
    willingness=willing_deference(request,relationship=relation,anchor=anchor,personality=person,appetite=appetite,commitments=situation.commitment_ids,request_refs=(source_record_id,))
    traits={f.name:f.assessment for f in person.facets}
    desired=appetite.state=='SEEKING'
    related=bool(anchor or relation.familiarity.assessment=='FAMILIAR')
    now=store.clock.utc_now_us()
    duration=request.duration_us
    if duration is None and request.review_at_us is not None:duration=request.review_at_us-now
    indefinite=duration is None or duration>30*DAY or duration<=0
    broad=request.scope=='GLOBAL'
    conflict=bool(situation.commitment_ids and request.operation in {'DO','ASK_FOR_TIME','ASK_FOR_ATTENTION'})
    own_boundary=situation.social_privacy and situation.social_privacy.assessment=='EXPLICITLY_FORBIDDEN'
    # Every option stays possible in its context. Personality changes sensitivity,
    # bounded compromise and review threshold, not an unconditional winning rank.
    if own_boundary:choice='DECLINE'
    elif indefinite:
        choice='DECLINE' if traits['conflict_style']=='FIRM' and traits['conviction_persistence']=='HIGH' else 'NEGOTIATE'
    elif request.consequence=='HIGH' and (willingness.assessment in {'UNKNOWN','LIMITED'} or traits['conviction_persistence']=='HIGH'):choice='DECLINE'
    elif not appetite.available:choice='NEGOTIATE'
    elif conflict and traits['commitment_seriousness']=='HIGH':choice='NEGOTIATE'
    elif 'DOMAIN_TRUST_INSUFFICIENT' in willingness.counterconsiderations:choice='NEGOTIATE'
    elif not desired and request.consequence=='LOW' and (related or request.operation!='REFRAIN'):choice='ACCEPT'
    elif desired and request.operation=='REFRAIN' and traits['self_direction_sensitivity']=='HIGH' and (broad or duration>DAY):choice='NEGOTIATE'
    elif willingness.assessment in {'STRONG','MODERATE'} and traits['relational_accommodation'] in {'HIGH','MODERATE'} and request.consequence!='HIGH':choice='ACCEPT'
    elif request.operation=='PREFER' and request.consequence=='LOW':choice='ACCEPT'
    else:choice='NEGOTIATE'
    accepted=None if choice=='DECLINE' else min(duration if duration and duration>0 else 3*DAY,3*DAY if indefinite else 30*DAY)
    if choice=='NEGOTIATE' and desired and traits['self_direction_sensitivity']=='HIGH':accepted=min(accepted,DAY)
    boundary=now+accepted if accepted else None
    review=min(boundary,request.review_at_us) if boundary and request.review_at_us and request.review_at_us>now else boundary
    factors=[]
    def factor(kind,direction,salience,refs,options,counters=()):
        factors.append(DeliberationFactor(kind=kind,direction=direction,salience=salience,source_refs=tuple(refs),supports=tuple(options),counter_refs=tuple(counters)))
    factor('RELATIONAL_REQUEST','SUPPORT','HIGH',(source_record_id,),('ACCEPT','NEGOTIATE'))
    factor('SOCIAL_APPETITE','COUNTER' if desired and request.operation=='REFRAIN' else 'CONTEXT','HIGH' if desired else 'LOW',(*appetite.source_record_ids,*appetite.source_memory_ids),('NEGOTIATE','DECLINE') if desired else ('ACCEPT',))
    factor('RELATIONAL_DEFERENCE','SUPPORT','HIGH' if willingness.assessment=='STRONG' else 'MODERATE',willingness.relationship_refs,('ACCEPT','NEGOTIATE'))
    factor('PERSONALITY_TENDENCY','CONTEXT','HIGH',person.source_record_ids,(choice,))
    factor('TEMPORAL_SCOPE','COUNTER' if indefinite else 'CONTEXT','HIGH' if indefinite else 'MODERATE',(source_record_id,),('NEGOTIATE','DECLINE') if indefinite else ('ACCEPT','NEGOTIATE'))
    if conflict:factor('COMMITMENT','COUNTER','HIGH',situation.commitment_ids,('NEGOTIATE','DECLINE'))
    if request.consequence!='LOW':factor('RISK_OR_CONSEQUENCE','COUNTER','HIGH',(source_record_id,),('NEGOTIATE','DECLINE'))
    if own_boundary:factor('VALUE_OR_NORM','COUNTER','HIGH',situation.social_privacy.support_refs,('DECLINE',))
    factor('ALTERNATIVE_AVAILABLE','SUPPORT','MODERATE',(source_record_id,),('NEGOTIATE',))
    factor('SELF_AUTHORSHIP','CONTEXT','HIGH',(source_record_id,),(choice,))
    response=RelationalResponsePlan(decision=choice,retained_preference='SOCIALIZE' if desired else 'UNSPECIFIED',temporal_boundary_us=boundary,
        warmth='HIGH' if related else 'MODERATE',firmness='HIGH' if choice=='DECLINE' else 'MODERATE' if choice=='NEGOTIATE' else 'LOW',retained_care=related)
    authorship=SelfAuthorshipAppraisal(state='INFLUENCED' if related else 'CLEAR_CHOICE',reason_refs=tuple(dict.fromkeys((source_record_id,*willingness.relationship_refs))))
    return RelationalDecision(request=request,deference=willingness,authorship=authorship,factors=tuple(factors),response=response,
        prior_behavior_disposition='VOLUNTARILY_RESTRAINED' if choice=='ACCEPT' and desired and request.operation=='REFRAIN' else 'RETAINED',accepted_duration_us=accepted,review_at_us=review)
