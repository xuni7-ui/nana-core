"""Source-backed views. Appetite deliberately has no dependency on anchors."""
from ...contracts import CoreError
from ...storage import canonical
from ..records import RecordService
from ..revision import state_token
from ..subject.growth import Growth
from ..autonomy.relationships import relationship_influence
from .bootstrap import read_current
from .contracts import SubjectPersonalitySeed,TendencyFacet,PersonalityTendencyView,SocialAppetiteView,SelfNarrativeItem,SelfNarrativeView


def personality_tendencies(store,*,scope,privacy_classes,entity_id=None):
    token=state_token(store);now=store.clock.utc_now_us();records=RecordService(store)
    source=read_current(store,scope,'seed',privacy_classes)
    seed=SubjectPersonalitySeed.model_validate_json(canonical(source[1])) if source else None
    facets=[];refs=[source[0]] if source else []
    assertions=Growth(store).assertions(scope,'PERSONALITY_TENDENCY',privacy_classes=privacy_classes)
    for name in ('self_direction_sensitivity','relational_accommodation','commitment_seriousness','conflict_style','social_exploration_tendency','conviction_persistence','repair_orientation','uncertainty_style'):
        row=next((a for a in assertions if a['topic']=='personality.'+name and a['state']!='SUPERSEDED'),None)
        support=tuple(row['source_record_ids']) if row else ()
        baseline=getattr(seed,name) if seed else 'UNKNOWN'
        assessment,basis=baseline,'BOOTSTRAP' if seed else 'UNKNOWN'
        if row and row['state']=='ADOPTED':
            assessment={'conflict_style':'NEGOTIATE','uncertainty_style':'COMPARE'}.get(name,'HIGH');basis='EVIDENCE'
        elif row and row['counter_evidence']:
            assessment='CONTESTED';basis='CONTESTED'
        refs.extend(support)
        facets.append(TendencyFacet(name=name,assessment=assessment,basis=basis,support_refs=tuple(dict.fromkeys((*(source[:1] if source else ()),*support))),
            counter_refs=tuple(row['counter_evidence']) if row else (),independent_support_count=row['independent_support_count'] if row else 0))
    modifiers=[]
    # Reviewed lessons contribute context, not automatic new independent traits.
    for row in store.db.execute("SELECT l.* FROM lessons l JOIN continuity_records r ON r.record_id=l.record_id WHERE l.state='ACTIVE' AND l.task_class IN ('disposition.review','interaction.shared_discovery') AND r.scope=? ORDER BY r.created_at_us DESC LIMIT 32",(scope,)):
        head=store.one('continuity_records',row['record_id'])
        if head['scope']==scope and head['privacy_class'] in privacy_classes and head['lifecycle']=='ACTIVE' and records.current_support(head['record_id']):
            refs.append(head['record_id']);modifiers.append('REVIEWED_LESSON_AVAILABLE')
    if entity_id is not None:
        relation=relationship_influence(store,entity_id,scope=scope,privacy_classes=privacy_classes)
        refs.extend(relation.source_record_ids)
        if relation.repair_tension.assessment=='UNRESOLVED':modifiers.append('UNRESOLVED_RELATIONAL_REPAIR')
        if relation.boundary_salience.assessment=='EXPLICIT':modifiers.append('EXPLICIT_RELATIONAL_BOUNDARY')
    if state_token(store)!=token:raise CoreError('STATE_CHANGED_DURING_PERSONALITY_PROJECTION')
    return PersonalityTendencyView(facets=tuple(facets),context_modifiers=tuple(dict.fromkeys(modifiers)),source_record_ids=tuple(dict.fromkeys(refs)),as_of_us=now,state_token=token)


def social_appetite(store,*,scope,privacy_classes):
    """No entity/anchor input: familiar company does not satisfy a desire by fiat."""
    token=state_token(store);now=store.clock.utc_now_us();records=RecordService(store)
    assertions=Growth(store).assertions(scope,privacy_classes=privacy_classes)
    adopted=[a for a in assertions if a['state']=='ADOPTED' and a['topic'] in {'social_exploration','social_connection','social_play'}]
    refs=[r for a in adopted for r in a['source_record_ids']];mids=[]
    state='SEEKING' if adopted else 'UNKNOWN'
    from ..subject.opportunities import cues_from,directions
    rows=store.db.execute("SELECT memory_id FROM memories WHERE scope=? AND predicate_key LIKE 'concern.%' AND lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') ORDER BY created_at_us DESC LIMIT 64",(scope,)).fetchall()
    for mid,cue in cues_from(store,tuple(x[0] for x in rows),scope=scope,privacy_classes=privacy_classes):
        if cue.cue_kind!='CONSTRAINT' and 'SOCIALIZE' in directions(cue):
            mids.append(mid)
            if state=='UNKNOWN':state='OPEN'
    # A seed can predispose openness, not certify a lived stable preference.
    seed=read_current(store,scope,'seed',privacy_classes)
    if seed and seed[1]['social_exploration_tendency']=='HIGH':
        refs.append(seed[0]);state='OPEN' if state=='UNKNOWN' else state
    pending=store.db.execute("SELECT count(*) FROM subject_intentions i JOIN continuity_records r ON r.record_id=i.record_id WHERE i.scope=? AND i.state='PENDING' AND i.expires_at_us>? AND r.lifecycle='ACTIVE'",(scope,now)).fetchone()[0]
    available=pending<6
    # Specific observed social saturation/recovery is evidence, never elapsed
    # silence or the mere existence/online status of a particular relationship.
    for a in assertions:
        if a['state']=='ADOPTED' and a['topic'] in {'social_recovery_needed','social_satiation'}:
            state='RECOVERING' if a['topic']=='social_recovery_needed' else 'SATURATED';refs.extend(a['source_record_ids'])
    if state_token(store)!=token:raise CoreError('STATE_CHANGED_DURING_APPETITE_PROJECTION')
    return SocialAppetiteView(state=state,source_record_ids=tuple(dict.fromkeys(refs)),source_memory_ids=tuple(mids),available=available,as_of_us=now,state_token=token)


def self_narrative(store,*,scope,privacy_classes,entity_id=None):
    view=personality_tendencies(store,scope=scope,privacy_classes=privacy_classes,entity_id=entity_id)
    items=[]
    for f in view.facets:
        if f.basis not in {'EVIDENCE','CONTESTED'}:continue
        items.append(SelfNarrativeItem(semantic='TENDENCY.'+f.name.upper(),assessment='CONTESTED' if f.basis=='CONTESTED' else 'SUPPORTED',support_refs=f.support_refs,counter_refs=f.counter_refs))
    for a in Growth(store).assertions(scope,'SELF_BELIEF',privacy_classes=privacy_classes):
        if a['state'] in {'ADOPTED','DISPUTED'}:
            items.append(SelfNarrativeItem(semantic='SELF_BELIEF.'+a['topic'],assessment='SUPPORTED' if a['state']=='ADOPTED' else 'CONTESTED',support_refs=a['source_record_ids'],counter_refs=a['counter_evidence']))
    if entity_id is not None:
        relation=relationship_influence(store,entity_id,scope=scope,privacy_classes=privacy_classes)
        if relation.familiarity.assessment=='FAMILIAR':items.append(SelfNarrativeItem(semantic='SHARED_RELATIONAL_HISTORY',assessment='SUPPORTED',support_refs=relation.familiarity.support_refs,counter_refs=()))
    return SelfNarrativeView(entries=tuple(items[:32]),as_of_us=view.as_of_us,state_token=view.state_token)
