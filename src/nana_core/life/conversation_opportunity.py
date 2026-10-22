"""Offer a retained unfinished topic to original C once; never send a message."""
from ..storage import digest
from ..continuity.person_self import adopted
from ..continuity.records import RecordService
from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..continuity.subject import SubjectInput
from ..continuity.subject.context_fit import depth_boundary
from ..continuity.subject.growth_life import availability
from ..continuity.subject.opportunities import ConcernCue
from ..presence.contracts import RuntimeEvent,Cause


def opportunity(app):
    r=app.runtime;s=r.store;scope=r.config.scopes[0];entity=r.config.entity_id
    for item in adopted(s,scope,entity,r.config.privacy_classes):
        p=item['payload']['decision']['proposal']
        if p['kind']!='UNFINISHED_TOPIC':continue
        key='local.unfinished.'+item['record_id']
        if s.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',(key,)).fetchone():continue
        # Use the original conversation topic for refusal/busy checks; a hashed
        # new concern key must not bypass a user's existing topic boundary.
        cycle=next((e['parent_id'] for e in s.db.execute("SELECT * FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD' AND relation_kind='SUPPORT'",(item['record_id'],))),None)
        row=s.db.execute('SELECT e.record_id FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id WHERE c.record_id=?',(cycle,)).fetchone()
        body=RecordService(s).read(row[0])['payload']['input'] if row and row[0] else {}
        topic=(body.get('interaction_signal') or {}).get('topic_key','daily')
        if depth_boundary(s,entity,scope,topic,r.config.privacy_classes)[0]:continue
        state,parents=availability(s,entity,scope=scope,privacy_classes=r.config.privacy_classes)
        if state=='BUSY':continue
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=topic,motivation_source='UNFINISHED_CONVERSATION',possible_behaviors=('SOCIALIZE','STAY_SILENT','REST'),resource_class='ORDINARY',availability=state,behavior_domain='COMPANIONSHIP')
        memory=RecordService(s).memory;now=r.clock.utc_now_us()
        previous=s.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace='recorded.conversation.concern' AND source_reference=?",(item['record_id'],)).fetchone()
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.concern',source_reference=item['record_id'],source_kind='MODEL_DERIVATION'),retention_consent_ref=item['record_id'],text=cue.model_dump_json(),privacy_class=item['privacy_class'],observed_time_us=previous[0] if previous else now))
        mid=memory.add(MemoryCandidate(entity_id=entity,scope=scope,memory_type=MemoryType.EPISODIC,epistemic_kind='INFERENCE',source_evidence_id=eid,text=cue.model_dump_json(),predicate_key='concern.conversation.'+digest(item['record_id'])[:24],derived_from=tuple(dict.fromkeys((*RecordService(s).support(item['record_id']),*parents)))))
        event=SubjectInput(domain='SOURCED_LIFE',source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=entity,scope=scope,privacy_class=item['privacy_class'],observed_at_us=now,source_memory_ids=(mid,))
        qid=r.submit(RuntimeEvent(event_type='RELATIONSHIP_EVENT',trigger='RELATIONSHIP_TRIGGER',input=event,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=now))
        return {'unfinished_topic_candidate':item['record_id'],'queue_id':qid,'not_delivery':True}
    return None
