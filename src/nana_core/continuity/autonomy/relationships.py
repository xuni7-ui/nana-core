"""Bounded, privacy-first multi-facet projection. No total score or authority."""
import json
from ...contracts import CoreError
from ..records import RecordService
from ..revision import state_token
from .contracts import RelationshipDetails,RelationshipFacet,RelationshipInfluenceView,SocialPrivacyExpectation
from .disclosure import expectation

def relationship_influence(store,entity_id,*,scope,privacy_classes):
    store.ensure_privacy_current();token=state_token(store);records=RecordService(store);now=store.clock.utc_now_us()
    allowed=tuple(privacy_classes)
    if not allowed:raise CoreError('RELATIONSHIP_PRIVACY_POLICY_REQUIRED')
    marks=','.join('?' for _ in allowed)
    rows=store.db.execute("SELECT e.* FROM relationship_events e JOIN continuity_records r ON r.record_id=e.record_id WHERE e.to_entity_id=? AND r.scope=? AND r.privacy_class IN ("+marks+") AND r.lifecycle='ACTIVE' ORDER BY e.occurred_at_us DESC,e.rowid DESC LIMIT 97",(entity_id,scope,*allowed)).fetchall()
    coverage='PARTIAL' if len(rows)>96 else 'FULL' if rows else 'UNKNOWN';events=[]
    for raw in reversed(rows[:96]):
        r=dict(raw)
        if not records.current_support(r['record_id']):continue
        body=records.read(r['record_id'])['payload']
        try:d=RelationshipDetails.model_validate_json(json.dumps(body.get('details',{})))
        except ValueError:continue
        if d.valid_until_us is not None and now>=d.valid_until_us:continue
        events.append((r,d))
    valid_ids={r['relationship_event_id'] for r,d in events}
    # Normalized revision refs survive erasure without retaining private prose.
    # An erased later interpretation cannot resurrect an old boundary version.
    superseded={r['related_event_id'] for r in rows if r['relation_kind']=='BOUNDARY' and r['relation_effect'] in {'WITHDRAWN','SUPERSEDES'}}
    boundaries=[r for r,d in events if r['relation_kind']=='BOUNDARY' and r['relationship_event_id'] not in superseded and d.boundary_state!='WITHDRAWN']
    conflicts=[(r,d) for r,d in events if r['relation_kind']=='CONFLICT']
    repaired={d.target_event_id for r,d in events if r['relation_kind']=='REPAIR' and any(c['relationship_event_id']==d.target_event_id and cd.domain==d.domain and c['occurred_at_us']<=r['occurred_at_us'] for c,cd in conflicts)}
    unresolved=[r for r,d in conflicts if r['relationship_event_id'] not in repaired]
    refs=tuple(r['record_id'] for r,d in events)
    def facet(assessment,support=(),counter=(),domain='interaction'):
        if coverage=='PARTIAL' and not counter:assessment='UNKNOWN'
        return RelationshipFacet(domain=domain,assessment=assessment,support_refs=tuple(dict.fromkeys(support)),counter_refs=tuple(dict.fromkeys(counter)),
            coverage=coverage,confidence='CONTESTED' if counter else 'SOURCE_BACKED' if support and assessment!='UNKNOWN' else 'INSUFFICIENT')
    history=[r for r,d in events if r['relation_kind'] in {'SHARED_HISTORY','SHARED_PROJECT','SHARED_JOKE'}]
    familiar=len({r['relation_kind'] for r in history})>=2
    trusts=[];order={r['relationship_event_id']:i for i,(r,d) in enumerate(events)}
    for domain in sorted({d.domain for r,d in events})[:16]:
        support=[r for r,d in events if d.domain==domain and r['relation_kind']=='TRUST']
        counter=[r for r,d in conflicts if d.domain==domain and d.trust_breach]
        active=[r for r in counter if r['relationship_event_id'] not in repaired]
        latest_breach=max((order[r['relationship_event_id']] for r in counter),default=-1)
        fresh=[r for r in support if order[r['relationship_event_id']]>latest_breach]
        assessment='CONTESTED' if active else 'RECOVERING' if counter and not fresh else 'SUPPORTED' if len(fresh)>=2 else 'CONTEXTUAL' if fresh else 'UNKNOWN'
        trusts.append(facet(assessment,[r['record_id'] for r in support],[r['record_id'] for r in counter],domain))
    projects=[];promises=[]
    for table,states,out in (('projects',('ACTIVE','PAUSED'),projects),('commitments',('ADOPTED','ACTIVE'),promises)):
        for r in store.db.execute('SELECT * FROM '+table+' WHERE entity_id=? AND scope=? ORDER BY updated_at_us DESC LIMIT 64',(entity_id,scope)):
            rr=store.one('continuity_records',r['record_id'])
            if r['state'] in states and rr['privacy_class'] in allowed and records.current_support(r['record_id']) and rr['lifecycle']=='ACTIVE':out.append(r['record_id'])
    recent=[r['record_id'] for r,d in events if 0<=now-r['occurred_at_us']<=7*86_400_000_000]
    shared=tuple(promises+projects)
    view=RelationshipInfluenceView(entity_id=entity_id,scope=scope,as_of_us=now,state_token=token,
        familiarity=facet('FAMILIAR' if familiar else 'ACQUAINTED' if history else 'UNKNOWN',[r['record_id'] for r in history]),trust=tuple(trusts),
        care_salience=facet('SALIENT' if promises or recent else 'BACKGROUND' if history else 'UNKNOWN',(*promises,*recent)),
        boundary_salience=facet('EXPLICIT' if boundaries else 'UNKNOWN',[r['record_id'] for r in boundaries]),
        repair_tension=facet('UNRESOLVED' if unresolved else 'RESOLVED' if conflicts else 'UNKNOWN',[r['record_id'] for r,d in events if r['relation_kind']=='REPAIR'],[r['record_id'] for r in unresolved]),
        interaction_latitude=facet('LIMITED' if boundaries or unresolved else 'CONTEXTUAL' if familiar and any(r['relation_kind']=='SHARED_JOKE' for r,d in events) else 'UNKNOWN',refs,[r['record_id'] for r in (*boundaries,*unresolved)]),
        shared_commitment_relevance=facet('CURRENT' if shared else 'UNKNOWN',shared),source_record_ids=tuple(dict.fromkeys((*refs,*shared))))
    if state_token(store)!=token:raise CoreError('STATE_CHANGED_DURING_RELATIONSHIP_PROJECTION')
    return view

def social_privacy(store,event,*,topic,privacy_classes):
    facts=expectation(store,scope=event.scope,entity_id=event.entity_id,topic=topic,privacy_classes=privacy_classes)
    ranks={'UNKNOWN':0,'OPEN':1,'ORDINARILY_VISIBLE':2,'CONTEXT_SENSITIVE':3,'EXPLICITLY_PRIVATE':4,'EXPLICITLY_FORBIDDEN':5}
    values={s.expectation for mid,s in facts}
    # Conflicting current sources remain context-sensitive, not a confidence vote.
    value=max(values,key=ranks.get) if values else 'UNKNOWN'
    return SocialPrivacyExpectation(scope=event.scope,topic=topic,assessment=value,
        support_refs=tuple(mid for mid,s in facts),as_of_us=store.clock.utc_now_us(),state_token=state_token(store))

def legacy_style(view):
    """Compatibility expression fields from the same facet projector."""
    familiar=view.familiarity.assessment=='FAMILIAR'
    limited=view.interaction_latitude.assessment=='LIMITED'
    repair=view.repair_tension.assessment=='UNRESOLVED'
    return {'entity_id':view.entity_id,'familiarity':view.familiarity.assessment,
        'social_distance':'CAUTIOUS' if repair else 'NEAR' if familiar else 'RESPECTFUL',
        'playfulness_permission':'WITHHELD' if limited else 'CONTEXTUAL' if view.interaction_latitude.assessment=='CONTEXTUAL' else 'UNESTABLISHED',
        'self_disclosure_comfort':'LIMITED' if limited or not familiar else 'CONTEXTUAL',
        'challenge_comfort':'DIRECT_WITH_CARE' if familiar and not repair else 'EXPLAIN_FIRST',
        'interaction_style':'REPAIR_FIRST' if repair else 'WARM_PLAYFUL' if view.interaction_latitude.assessment=='CONTEXTUAL' else 'WARM_DIRECT' if familiar else 'RESPECTFUL_EXPLICIT',
        'source_record_ids':view.source_record_ids}
