"""Persistent, bounded source queue using C admission and deletable records."""
import json
from ..contracts import CoreError
from ..storage import canonical,digest,uid
from ..continuity.records import RecordService
from ..continuity.subject.contracts import SubjectInput
from ..continuity.subject.ingress import SubjectIngress
from .contracts import RuntimeEvent,Cause


class EventQueue:
    def __init__(self,store,config,lease):
        self.store,self.config,self.lease=store,config,lease
        self.records,self.ingress=RecordService(store),SubjectIngress(store)
        self._transient_interactions={}

    def depth(self):
        return self.store.db.execute("SELECT count(*) FROM runtime_queue WHERE state IN ('READY','DEFERRED','PROCESSING')").fetchone()[0]

    def has_reactive(self):
        return bool(self.store.db.execute("SELECT 1 FROM runtime_queue WHERE state IN ('READY','DEFERRED') AND event_type='USER_EVENT' AND due_at_us<=? LIMIT 1",(self.store.clock.utc_now_us(),)).fetchone())

    def cause_memories(self, causes, scope):
        memories=[]
        for cause in causes:
            ref=cause.reference_id
            if cause.kind=='CANONICAL_SELF':
                if ref!=self.store.identity['identity_id']: raise CoreError('RUNTIME_CAUSE_IDENTITY_MISMATCH')
                continue
            if cause.kind=='MEMORY':
                row=self.store.one('memories',ref)
                if not row or row['scope']!=scope or row['privacy_class'] not in self.config.privacy_classes:
                    raise CoreError('RUNTIME_CAUSE_UNAVAILABLE')
                self.records.memory.read(ref);memories.append(ref);continue
            mapping={'COMMITMENT':('commitments','commitment_id'),'PROJECT':('projects','project_id'),
                'EXPERIENCE':('experiences','experience_id'),'INTENTION':('subject_intentions','intention_id'),
                'ASSERTION':('self_assertions','assertion_id')}
            row=self.store.one(mapping[cause.kind][0],ref)
            if row and cause.revision is not None and row.get('revision')!=cause.revision:
                raise CoreError('RUNTIME_CAUSE_STALE')
            if row and cause.kind=='COMMITMENT' and row['state'] not in {'ADOPTED','ACTIVE'}:
                raise CoreError('RUNTIME_CAUSE_STALE')
            if row and cause.kind=='PROJECT' and row['state']!='ACTIVE':
                raise CoreError('RUNTIME_CAUSE_STALE')
            record=self.store.one('continuity_records',row['record_id']) if row else None
            if not record or record['scope']!=scope or record['privacy_class'] not in self.config.privacy_classes:
                raise CoreError('RUNTIME_CAUSE_UNAVAILABLE')
            self.records.read(record['record_id'])
            if not self.records.current_support(record['record_id']):raise CoreError('RUNTIME_CAUSE_STALE')
            memories.extend(self.records.support(record['record_id']))
        return tuple(dict.fromkeys(memories))

    def enqueue(self,event:RuntimeEvent):
        self.lease.assert_current()
        if event.input.scope not in self.config.scopes or event.input.privacy_class not in self.config.privacy_classes:
            raise CoreError('RUNTIME_INGRESS_SCOPE_DENIED')
        old=self.store.db.execute('SELECT * FROM runtime_queue WHERE source_key=?',(event.input.source_key,)).fetchone()
        if old:
            existing=dict(old)
            # C performs exact retained-input collision checks; unretained text
            # is deliberately neither saved nor hashed for dedup.
            self.ingress.ingest(event.input)
            if (existing['event_type'],existing['wake_trigger'],existing['cause_json'])!=(event.event_type,event.trigger,canonical([c.model_dump() for c in event.causes])):
                raise CoreError('RUNTIME_EVENT_COLLISION')
            return existing['queue_id']
        if self.depth()>=self.config.queue_capacity:raise CoreError('RUNTIME_QUEUE_BACKPRESSURE')
        if event.stream_key:
            duplicate=self.store.db.execute('SELECT 1 FROM runtime_queue WHERE stream_key=? AND source_sequence=?',
                (event.stream_key,event.source_sequence)).fetchone()
            if duplicate:raise CoreError('RUNTIME_STREAM_SEQUENCE_COLLISION')
        parents=self.cause_memories(event.causes,event.input.scope)
        source=self.ingress.ingest(event.input)
        record=source['record_id']
        retained=event.input.model_dump(mode='json')
        if not record and not (parents and event.input.retention!='DO_NOT_REMEMBER'):
            # No durable body/interpretation for discarded input. Timers can
            # retain typed metadata via existing, erasable memory dependencies.
            retained.update(text=None,topic=None,proposed_method=None,preference_signal=None,relationship_kind=None)
            retained.update(interaction_signal=None,growth_assessment_id=None,positive_request=None,relationship_details=None,disclosure_request=None,realization_target=None,goal_step=None,goal_review=None,world_concern_id=None,memory_review_id=None,surface=None)
        safe=SubjectInput.model_validate_json(canonical(retained))
        now=self.store.clock.utc_now_us()
        with self.store.transaction('runtime.event_enqueued') as tx:
            if not record and parents and event.input.retention!='DO_NOT_REMEMBER':
                record=self.records.create(tx,kind='SUBJECT_EVENT',scope=event.input.scope,
                    payload={'input':retained,'semantics':'WAKE_ENVELOPE_NOT_NEW_EXPERIENCE'},memories=parents)
            queue_id=uid()
            seq=self.store.db.execute('SELECT coalesce(max(sequence_no),0)+1 FROM runtime_queue').fetchone()[0]
            metadata=safe.model_dump(mode='json');metadata['text']=None
            # Structured semantic fields only survive via deletable record.
            for field in ('interaction_signal','growth_assessment_id','topic','proposed_method','preference_signal','relationship_kind','positive_request','relationship_details','disclosure_request','realization_target','relational_request','goal_step','goal_review','memory_review_id','surface'):
                metadata[field]=None
            tx.put('runtime_queue',{'queue_id':queue_id,'source_key':event.input.source_key,'sequence_no':seq,
                'event_type':event.event_type,'wake_trigger':event.trigger,'subject_event_id':source['subject_event_id'],
                'record_id':record,'metadata_json':canonical(metadata),'cause_json':canonical([c.model_dump() for c in event.causes]),
                'state':'READY' if event.due_at_us<=now else 'DEFERRED','priority':event.priority,
                'due_at_us':event.due_at_us,'expires_at_us':event.expires_at_us,'owner_epoch':None,'cycle_id':None,
                'outcome_code':None,'stream_key':event.stream_key,'source_sequence':event.source_sequence,
                'attempts':0,'created_at_us':now,'updated_at_us':now})
        if not record and event.input.interaction_signal:
            # Admission remains TEMPORARY: the current process may understand
            # this input without permanently remembering ordinary conversation.
            for key in tuple(self._transient_interactions):
                old=self.store.one('runtime_queue',key)
                if not old or old['state'] not in {'READY','DEFERRED','PROCESSING'}:self._transient_interactions.pop(key,None)
            self._transient_interactions[queue_id]=(event.input,now+30_000_000)
        return queue_id

    def clear_transient(self):self._transient_interactions.clear()

    def input(self,row):
        transient=self._transient_interactions.get(row['queue_id'])
        if transient:
            if self.store.clock.utc_now_us()<transient[1]:return transient[0]
            self._transient_interactions.pop(row['queue_id'],None)

        if row['record_id']:
            record=self.records.read(row['record_id'])
            if not self.records.current_support(row['record_id']):raise CoreError('RUNTIME_CAUSE_STALE')
            return SubjectInput.model_validate_json(canonical(record['payload']['input']))
        return SubjectInput.model_validate_json(row['metadata_json'])

    def recover(self):
        self.lease.assert_current()
        in_flight=[r for r in self.store.all('runtime_queue') if r['state']=='PROCESSING']
        unresolved=[r for r in self.store.all('runtime_cognition_calls') if r['state']=='RESERVED']
        if not in_flight and not unresolved:return
        with self.store.transaction('runtime.crash_recovered') as tx:
            for call in unresolved:
                tx.update('runtime_cognition_calls',call['call_id'],state='UNKNOWN')
            for row in in_flight:
                cycle=self.store.db.execute('SELECT cycle_id FROM subject_cycles WHERE subject_event_id=?',(row['subject_event_id'],)).fetchone()
                tx.update('runtime_queue',row['queue_id'],state='DONE' if cycle else 'READY',
                    cycle_id=cycle[0] if cycle else None,owner_epoch=None,updated_at_us=self.store.clock.utc_now_us(),
                    outcome_code='RECOVERED_COMMITTED_CYCLE' if cycle else 'SAFE_RESUME_NO_MODEL_RETRY')

    def claim(self,*,user_only=False,ready=None):
        self.lease.assert_current()
        now=self.store.clock.utc_now_us()
        candidates=self.store.db.execute("SELECT * FROM runtime_queue WHERE state IN ('READY','DEFERRED') AND due_at_us<=? "
            "AND (expires_at_us IS NULL OR expires_at_us>?) "
            "ORDER BY CASE WHEN event_type='USER_EVENT' THEN 0 ELSE 1 END,priority DESC,due_at_us,sequence_no LIMIT ?",
            (now,now,self.config.queue_capacity)).fetchall()
        # A read-only resource offer can leave a source ready. Do not journal
        # identical failed admissions on every normal D step.
        candidates=[dict(row) for row in candidates if (not user_only or row['event_type']=='USER_EVENT')
            and (ready is None or ready(dict(row)))]
        expired=self.store.db.execute("SELECT 1 FROM runtime_queue WHERE state IN ('READY','DEFERRED') AND expires_at_us<=? LIMIT 1",(now,)).fetchone()
        if not candidates and not expired:return None
        with self.store.transaction('runtime.queue_checked') as tx:
            for row in self.store.db.execute("SELECT * FROM runtime_queue WHERE state IN ('READY','DEFERRED') AND expires_at_us<=?",(now,)).fetchall():
                tx.update('runtime_queue',row['queue_id'],state='EXPIRED',outcome_code='EXPIRED',updated_at_us=now)
            for raw in candidates:
                row=dict(raw)
                if user_only and row['event_type']!='USER_EVENT':continue
                if row['stream_key']:
                    earlier=self.store.db.execute("SELECT 1 FROM runtime_queue WHERE stream_key=? AND source_sequence<? AND state IN ('READY','DEFERRED','PROCESSING')",(row['stream_key'],row['source_sequence'])).fetchone()
                    if earlier:continue
                    stale=self.store.db.execute("SELECT 1 FROM runtime_queue WHERE stream_key=? AND source_sequence>? AND state='DONE'",(row['stream_key'],row['source_sequence'])).fetchone()
                    if stale:
                        tx.update('runtime_queue',row['queue_id'],state='IGNORED',outcome_code='STALE_STREAM_SEQUENCE',updated_at_us=now);continue
                row=tx.update('runtime_queue',row['queue_id'],state='PROCESSING',owner_epoch=self.lease.epoch,
                    attempts=row['attempts']+1,updated_at_us=now)
                return row
        return None

    def finish(self,row,state,code,cycle_id=None,*,defer_until_us=None):
        if state not in {'DONE','IGNORED','EXPIRED','DEFERRED'}:raise CoreError('INVALID_RUNTIME_QUEUE_TRANSITION')
        if defer_until_us is not None and (state!='DEFERRED' or type(defer_until_us) is not int or defer_until_us<=self.store.clock.utc_now_us()):raise CoreError('INVALID_RUNTIME_DEFERRAL')
        if state!='DEFERRED':self._transient_interactions.pop(row['queue_id'],None)
        with self.store.transaction('runtime.event_finished') as tx:
            old=self.store.one('runtime_queue',row['queue_id'])
            if old['state']!='PROCESSING' or old['owner_epoch']!=self.lease.epoch:raise CoreError('RUNTIME_QUEUE_OWNER_LOST')
            updates={'state':state,'outcome_code':code,'cycle_id':cycle_id,'owner_epoch':None,'updated_at_us':self.store.clock.utc_now_us()}
            if defer_until_us is not None:updates['due_at_us']=defer_until_us
            tx.update('runtime_queue',row['queue_id'],**updates)
