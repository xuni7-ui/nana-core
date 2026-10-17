"""Single-owner, bounded capture slices. D calls this service; H never judges."""
import json
from ...contracts import CoreError
from ...storage import canonical,digest
from ..provider_routing import RouteRequest
from ..records import RecordService
from ..world_loop.perception import PerceptionService,MediaSourceDescriptor
from ..world_loop.semantics import MediaSemanticService
from .contracts import *

class PerceptionCoordinator:
    def __init__(self,runtime,configuration,resolver,providers,context_policy,*,router=None,host_allow=None,concern_callback=None):
        self.runtime,self.store,self.configuration,self.resolver=runtime,runtime.store,configuration,resolver
        self.policy,self.router,self.host_allow=context_policy,router,host_allow or (lambda p:False)
        self.records=RecordService(self.store);self.perception=PerceptionService(self.store,providers,context_policy)
        self.concern_callback=concern_callback
        self.state=runtime.oper.setdefault('perception',{'requests':{},'sources':{},'budget':{},'dropped':0,'coalesced':0})
        self._busy=False
        self.recover()
    def _save(self):self.runtime._save_oper()
    def _checkpoint(self,stage):pass
    def _source(self,sid):
        p=next((p for p in self.configuration.load().sources if p.source_profile_id==sid),None)
        if p is None:raise CoreError('SOURCE_UNAVAILABLE')
        return p
    def _safe_point(self,request,stage):
        self.runtime.lease.heartbeat();self.runtime.cadence.drain(self.runtime.submit)
        self._checkpoint(stage)
        self.runtime.cadence.drain(self.runtime.submit)
        if not request.foreground and self.runtime.queue.has_reactive():raise CoreError('PERCEPTION_PREEMPTED')
    def request(self,sid,*,request_id,reason='USER_REQUEST',foreground=False,semantic=True,operations=(),sample_key=None,records=()):
        p=self._source(sid);now=self.store.clock.utc_now_us()
        return ObservationRequest(request_id=request_id,source_profile_id=sid,source_revision=p.revision,requested_modality=p.modality,reason_kind=reason,requested_at_us=now,deadline_us=now+30000000,foreground=foreground,privacy_class=p.privacy_class,max_capture_bytes=p.max_capture_bytes,semantic_requested=semantic,requested_operations=operations or p.semantic_operations,sample_key=sample_key,source_record_ids=records)
    def _allowed(self,req,p):
        if not p.enabled or not self.host_allow(p):raise CoreError('BLOCKED_BY_HOST')
        if self.store.one('core_meta','governance.registry'):
            from ..autonomy.governance import snapshot
            _,roots=snapshot(self.store)
            denied=[(event,c) for event,c,active in roots if active and c.scope==p.scope and any(t.capability=='perception.capture' and t.operation=='READ' and t.resource=='synthetic://perception/'+p.source_profile_id for t in c.targets)]
            if denied:
                refs=[{'constraint_id':c.constraint_id,'revision':c.revision,'source_event_id':event} for event,c in denied]
                self.state['sources'].setdefault(p.source_profile_id,{})['last_block']={'stage':'MANAGER','constraint_refs':refs,'actual_capture':'NONE'}
                self._save()
                raise CoreError('CAPTURE_MANAGER_BLOCKED')
        if (req.source_revision,req.requested_modality,req.privacy_class)!=(p.revision,p.modality,p.privacy_class):raise CoreError('SOURCE_REVISION_STALE')
        if p.scope not in self.policy.allowed_scopes or p.privacy_class not in self.policy.readable_privacy:raise CoreError('PERCEPTION_PRIVACY_DENIED')
        if p.entity_id!=self.runtime.config.entity_id:raise CoreError('SOURCE_ENTITY_DENIED')
        if not set(req.requested_operations)<=set(p.semantic_operations):raise CoreError('SOURCE_OPERATION_DENIED')
        if req.max_capture_bytes!=p.max_capture_bytes:raise CoreError('SOURCE_SIZE_MISMATCH')
        if self.store.clock.utc_now_us()>req.deadline_us:raise CoreError('CAPTURE_DEADLINE_EXPIRED')
        for rid in req.source_record_ids:
            r=self.records.read(rid)
            if r['scope']!=p.scope or r['privacy_class'] not in self.policy.readable_privacy or not self.records.current_support(rid):raise CoreError('SOURCE_SUPPORT_RETIRED')
        port=self.resolver.resolve(p)
        try:health=port.health()
        except Exception:raise CoreError('SOURCE_UNAVAILABLE') from None
        if health not in {'AVAILABLE','DEGRADED'}:raise CoreError('SOURCE_UNAVAILABLE')
        return port
    def _reserve(self,req,p):
        now=self.store.clock.utc_now_us();policy=self.configuration.load().policy
        b=self.state['budget']
        if b.get('minute')!=now//60000000:b.clear();b.update(minute=now//60000000,captures=0,bytes=0,background_bytes=0,semantic_calls=0)
        src=self.state['sources'].get(p.source_profile_id,{})
        last_attempt=src.get('last_attempt_us',src.get('last_capture_us'))
        if last_attempt is not None and now-last_attempt<p.min_interval_ms*1000:raise CoreError('SOURCE_MIN_INTERVAL')
        if b['captures']>=policy.max_captures_per_minute or b['bytes']+p.max_capture_bytes>policy.max_bytes_per_minute:raise CoreError('CAPTURE_BUDGET_DENIED')
        if not req.foreground and (b['background_bytes']+p.max_capture_bytes)*100>policy.max_bytes_per_minute*policy.background_percent:raise CoreError('BACKGROUND_CAPTURE_RESERVE')
        self.state['sources'].setdefault(p.source_profile_id,{})['last_attempt_us']=now
        b['captures']+=1;b['bytes']+=p.max_capture_bytes
        if not req.foreground:b['background_bytes']+=p.max_capture_bytes
    def _set(self,key,**changes):
        self.state['requests'][key].update(changes);self._save();return dict(self.state['requests'][key])
    def _visible_result(self,value):
        mid=value.get('memory_id')
        if mid:
            try:self.records.memory.read(mid)
            except CoreError:return {'state':'FAILED','reason':'SOURCE_RETIRED','request_id':value['request_id']}
        return dict(value)
    def observe(self,request):
        self.runtime.cadence.assert_owner();self.runtime.lease.assert_current()
        if type(request) is not ObservationRequest:raise CoreError('CAPTURE_TYPED_REQUEST_REQUIRED')
        req=ObservationRequest.model_validate_json(request.model_dump_json());key=digest(req.request_id)
        old=self.state['requests'].get(key)
        if old:
            if old['request_digest']!=digest(req.model_dump(mode='json')):raise CoreError('CAPTURE_REQUEST_COLLISION')
            return self._visible_result(old)
        if self._busy:raise CoreError('CAPTURE_CONCURRENCY_BOUND')
        prior=self.store.db.execute("SELECT 1 FROM events WHERE kind='h2.request_reserved' AND json_extract(data_json,'$.data.target_id')=? LIMIT 1",(key,)).fetchone()
        if prior:return {'request_id':req.request_id,'state':'UNKNOWN','reason':'HISTORICAL_CAPTURE_NOT_RETRIED'}
        p=self._source(req.source_profile_id);port=self._allowed(req,p)
        self._reserve(req,p)
        while len(self.state['requests'])>=64:
            oldest=next(iter(self.state['requests']));del self.state['requests'][oldest]
        self.state['requests'][key]={'request_id':req.request_id,'request_digest':digest(req.model_dump(mode='json')),'source_profile_id':p.source_profile_id,'state':'CAPTURING','semantic':{},'memory_id':None,'record_id':None}
        with self.store.transaction('h2.request_reserved',{'target_id':key}):pass
        self._save();self._busy=True
        try:
            self._safe_point(req,'BEFORE_SOURCE_OPEN')
            try:cap=port.capture(req)
            except (OSError,TimeoutError):raise CoreError('SOURCE_UNAVAILABLE') from None
            if type(cap) is not CapturedMedia:raise CoreError('CAPTURE_TYPED_RESULT_REQUIRED')
            cap.verify(p,self.store.clock.utc_now_us())
            self._set(key,state='CAPTURED',capture_id=cap.capture_id)
            self._safe_point(req,'AFTER_CAPTURE_BEFORE_INGEST')
            self._allowed(req,self._source(p.source_profile_id))
            prior=self.store.db.execute("SELECT evidence_id,state FROM continuity_evidence WHERE source_namespace='synthetic.public-media' AND source_reference=?",('capture.'+cap.capture_id,)).fetchone()
            if prior:
                if prior['state']=='DELETED':raise CoreError('SOURCE_DELETED')
                old_mid=self.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(prior['evidence_id'],)).fetchone()
                if old_mid:
                    self.records.memory.read(old_mid[0])
                    old_rec=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id=?",(old_mid[0],)).fetchone()
                    if old_rec:return self._set(key,state='DECODED',reason='CAPTURE_ID_REPLAY',memory_id=old_mid[0],record_id=old_rec[0])
            source=MediaSourceDescriptor(source_id='capture.'+cap.capture_id,modality=cap.modality,event_time_us=cap.event_time_us,observed_time_us=cap.observed_time_us,privacy=p.privacy_class,source_profile_id=p.source_profile_id,source_revision=p.revision,source_kind=p.source_kind,capture_id=cap.capture_id,adapter_identity=port.describe().adapter_identity,byte_length=cap.byte_length,capture_coverage=cap.coverage,sequence=cap.sequence)
            mid,rid=self.perception.ingest(cap.data,source,entity_id=p.entity_id,scope=p.scope)
            previous=self.state['sources'].get(p.source_profile_id,{})
            routing_revision=self.router.config.load().revision if self.router is not None else None
            same=(previous.get('semantic_route_revision')==routing_revision and previous.get('digest')==cap.byte_digest and cap.observed_time_us-previous.get('last_capture_us',0)<=self.configuration.load().policy.debounce_us)
            self.state['sources'][p.source_profile_id]={**previous,'digest':cap.byte_digest,'last_capture_us':cap.observed_time_us,'last_memory_id':mid,'last_record_id':rid,'health':'AVAILABLE'}
            self._set(key,state='DECODED',memory_id=mid,record_id=rid)
            self._safe_point(req,'AFTER_TECHNICAL_INGEST')
            if not req.semantic_requested or not req.requested_operations:return self._set(key,state='DECODED',reason='TECHNICAL_ONLY')
            if same:return self._set(key,state='DECODED',reason='EXACT_DIGEST_DEBOUNCE',semantic={op:'SUPPRESSED_EXACT_DIGEST' for op in req.requested_operations})
            for op in req.requested_operations:
                self._safe_point(req,'BEFORE_SEMANTIC_DISPATCH')
                self._allowed(req,self._source(p.source_profile_id))
                if self.router is None:
                    self.state['requests'][key]['semantic'][op]='DEFERRED_PROVIDER_UNAVAILABLE';continue
                try:
                    b=self.state['budget']
                    if b['semantic_calls']>=self.configuration.load().policy.max_semantic_calls_per_minute:raise CoreError('SEMANTIC_BUDGET_DENIED')
                    target=self.router.resolve(RouteRequest(operation=op,input_modalities=(p.modality,),privacy_class=p.privacy_class,output_limit=4096),self.policy)
                    session=target.cognition_session(self.runtime);service=MediaSemanticService(session)
                    cid=service.prepare('capture:'+cap.capture_id+':'+op,mid,cap.data,ephemeral=True)
                    # Persist correlation before dispatch; recovery never creates a new request key.
                    self._set(key,current_request_id=cid,current_operation=op)
                    b['semantic_calls']+=1;self._save()
                    outcome=service.execute(cid)
                    self._safe_point(req,'AFTER_SEMANTIC_RESPONSE')
                    if outcome['state']=='PROPOSED':
                        result=service.ground(cid,entity_id='media.capture.'+cap.capture_id,predicate='capture.'+cap.capture_id+'.'+{'VISION':'vision','AUDIO_UNDERSTAND':'audio','STT':'stt','VIDEO_UNDERSTAND':'video'}[op])
                        self.state['requests'][key]['semantic'][op]={'state':'GROUNDED','request_id':cid,'belief_ids':result['belief_ids']}
                        self.state['sources'][p.source_profile_id]['semantic_route_revision']=target.snapshot.config_revision
                        self._set(key,state='GROUNDED')
                        self._safe_point(req,'BEFORE_CONCERN')
                        if self.concern_callback:self.concern_callback(result,cid)
                    else:self.state['requests'][key]['semantic'][op]={'state':outcome['state'],'request_id':cid}
                    session._volatile_inputs.clear()
                except CoreError as exc:
                    if exc.code in {'RUNTIME_LEASE_LOST','PERCEPTION_PREEMPTED'}:raise
                    self.state['requests'][key]['semantic'][op]='DENIED' if 'PRIVACY' in exc.code else 'DEFERRED_PROVIDER_UNAVAILABLE'
                    self._set(key,state='DEFERRED',reason=exc.code)
                finally:self._save()
            value=self.state['requests'][key]
            return self._set(key,state='GROUNDED' if any(isinstance(v,dict) and v['state']=='GROUNDED' for v in value['semantic'].values()) else 'DEFERRED',reason=value.get('reason','SEMANTIC_FINISHED'))
        except CoreError as exc:
            if exc.code=='RUNTIME_LEASE_LOST':raise
            return self._set(key,state='DEFERRED' if self.state['requests'][key]['memory_id'] else 'FAILED',reason='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED' if exc.code=='PERCEPTION_PREEMPTED' else exc.code)
        finally:
            self._busy=False
            # No retained data/capture object is stored in the coordinator.
    def recover(self):
        self.runtime.lease.assert_current()
        for value in self.state['requests'].values():
            if value['state'] not in {'CAPTURING','CAPTURED','DECODED','SEMANTIC_PROPOSED','GROUNDED'}:continue
            if value.get('reason') in {'TECHNICAL_ONLY','EXACT_DIGEST_DEBOUNCE','CAPTURE_ID_REPLAY'}:continue
            cid=value.get('current_request_id')
            if cid:
                row=self.store.one('cognitive_requests',cid)
                if row and row['state'] in {'CALLING','PREPARED'}:
                    with self.store.transaction('h2.semantic_interrupted',{'request_id':cid}) as tx:tx.update('cognitive_requests',cid,state='UNKNOWN' if row['state']=='CALLING' else 'STALE',error_code='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED')
                elif row and row['state']=='PROPOSED':
                    # Resume grounding using digest-only accepted metadata. No bytes/provider needed.
                    try:
                        head=self.records.read(row['record_id']);request=head['payload']['request'];route=request['route_snapshot'];op=route['operation']
                        target=self.router.resolve(RouteRequest(operation=op,exact_provider_profile_id=route['provider_profile_id'],exact_model_profile_id=route['model_profile_id']),self.policy)
                        service=MediaSemanticService(target.cognition_session(self.runtime));cap=value['capture_id']
                        result=service.ground(cid,entity_id='media.capture.'+cap,predicate='capture.'+cap+'.'+{'VISION':'vision','AUDIO_UNDERSTAND':'audio','STT':'stt','VIDEO_UNDERSTAND':'video'}[op])
                        if self.concern_callback:self.concern_callback(result,cid)
                        value['semantic'][op]={'state':'GROUNDED','request_id':cid,'belief_ids':result['belief_ids']};value['state']='GROUNDED';continue
                    except CoreError:pass
            if value['state'] in {'CAPTURING','CAPTURED','DECODED','SEMANTIC_PROPOSED'}:value.update(state='DEFERRED',reason='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED' if value.get('memory_id') else 'SOURCE_SAMPLE_EXPIRED')
        self._save()

    def watch_from_cycle(self,cycle_id,source_id,*,duration_us=60000000):
        self.runtime.cadence.assert_owner()
        if not 100000<=duration_us<=3600000000:raise CoreError('WATCH_DURATION_BOUND')
        row=self.store.one('subject_cycles',cycle_id)
        if not row:raise CoreError('WATCH_CYCLE_REQUIRED')
        cycle=self.runtime.subject.result(row)
        if cycle.judgment.stance!='WATCH' or not self.records.current_support(row['record_id']):raise CoreError('WATCH_CYCLE_REQUIRED')
        profile=self._source(source_id);supported=False
        for mid in self.records.support(row['record_id']):
            m=self.records.memory.read(mid)
            try:body=json.loads(m['text'])
            except ValueError:continue
            if (body.get('source',{}).get('source_profile_id'),body.get('source',{}).get('source_revision'))==(source_id,profile.revision):supported=True
        if not supported:raise CoreError('WATCH_SOURCE_REQUIRED')
        self.state['sources'].setdefault(source_id,{})['watch']={'record_id':row['record_id'],'cycle_id':cycle_id,'source_revision':profile.revision,'until_us':self.store.clock.utc_now_us()+duration_us}
        self._save()
    def interval_ms(self,p):
        w=self.state['sources'].get(p.source_profile_id,{}).get('watch')
        if w and w.get('source_revision')==p.revision and w['until_us']>self.store.clock.utc_now_us() and self.records.current_support(w['record_id']):
            return max(p.min_interval_ms,min(p.base_interval_ms,5000))
        return p.base_interval_ms
    def attach(self):
        self.runtime.cadence.assert_owner()
        if self.runtime.perception is not None and self.runtime.perception is not self:raise CoreError('PERCEPTION_ALREADY_ATTACHED')
        self.runtime.perception=self;return self
    def enqueue(self,request):
        from ...presence.contracts import RuntimeEvent,Cause
        from ..subject.contracts import SubjectInput
        self.runtime.cadence.assert_owner()
        p=self._source(request.source_profile_id);self._allowed(request,p)
        pending=self.state.setdefault('pending',{})
        if request.request_id in pending:
            if pending[request.request_id]!=request.model_dump(mode='json'):raise CoreError('CAPTURE_REQUEST_COLLISION')
            return request.request_id
        if len(pending)>=self.configuration.load().policy.pending_capacity:
            self.state['dropped']+=1;self._save();raise CoreError('PERCEPTION_BACKPRESSURE')
        pending[request.request_id]=request.model_dump(mode='json');self._save()
        inp=SubjectInput(source_key='synthetic.h2.'+digest(request.request_id),kind='WAKE',origin='SELF_WAKE',entity_id=self.runtime.config.entity_id,scope=p.scope,observed_at_us=request.requested_at_us)
        event=RuntimeEvent(event_type='DEVICE_EVENT',trigger='DEVICE_TRIGGER',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=self.runtime.identity_id),),due_at_us=request.requested_at_us,priority=3 if request.foreground else 0)
        try:self.runtime.submit(event)
        except CoreError:
            pending.pop(request.request_id,None);self._save();raise
        return request.request_id
    def poll(self):
        from ...presence.contracts import RuntimeEvent,Cause,ScheduleSpec
        from ..subject.contracts import SubjectInput
        try:c=self.configuration.load()
        except CoreError:
            self.state['config_status']='UNAVAILABLE'
            for row in self.store.db.execute("SELECT * FROM runtime_schedules WHERE dedupe_key LIKE 'h2.%' AND state='ACTIVE' LIMIT 64").fetchall():self.runtime.scheduler.cancel(row['schedule_id'])
            self._save();return
        self.state['config_status']='AVAILABLE';active=set();now=self.store.clock.utc_now_us()
        for p in c.sources:
            if not p.enabled or p.capture_mode!='PERIODIC':continue
            interval=self.interval_ms(p);key='h2.'+digest([p.source_profile_id,p.revision,interval])
            active.add(key)
            src=self.state['sources'].setdefault(p.source_profile_id,{})
            # One active timer per source; changes cancel rather than multiply cadence.
            old=src.get('schedule_key')
            if old and old!=key:
                row=self.store.db.execute("SELECT * FROM runtime_schedules WHERE dedupe_key=? AND state='ACTIVE'",(old,)).fetchone()
                if row:self.runtime.scheduler.cancel(row['schedule_id'])
            src['schedule_key']=key
            existing=self.store.db.execute('SELECT * FROM runtime_schedules WHERE dedupe_key=?',(key,)).fetchone()
            if existing and existing['state']=='CANCELLED':
                # A renewed interest is a new timer occurrence, not a replay of the old template.
                with self.store.transaction('h2.schedule_reenabled') as tx:tx.update('runtime_schedules',existing['schedule_id'],state='ACTIVE',due_at_us=now+interval*1000)
            elif not existing:
                inp=SubjectInput(source_key='synthetic.h2.template',kind='WAKE',origin='SELF_WAKE',entity_id=self.runtime.config.entity_id,scope=p.scope,observed_at_us=now)
                event=RuntimeEvent(event_type='DEVICE_EVENT',trigger='DEVICE_TRIGGER',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=self.runtime.identity_id),),due_at_us=now+interval*1000,priority=0)
                self.runtime.scheduler.add(ScheduleSpec(dedupe_key=key,kind='PERIODIC',due_at_us=event.due_at_us,interval_us=interval*1000,event=event))
        for row in self.store.db.execute("SELECT * FROM runtime_schedules WHERE dedupe_key LIKE 'h2.%' AND state='ACTIVE' LIMIT 64").fetchall():
            if row['dedupe_key'] not in active:self.runtime.scheduler.cancel(row['schedule_id'])
        existing_ids={p.source_profile_id for p in c.sources}
        self.state['sources']={k:v for k,v in self.state['sources'].items() if k in existing_ids}
        self._save()
    def handle_queue(self,row):
        pending=self.state.setdefault('pending',{});req=None;request_key=None
        for rid,body in pending.items():
            if row['source_key']=='synthetic.h2.'+digest(rid):req=ObservationRequest.model_validate_json(canonical(body));request_key=rid;break
        if req is None:
            schedule=self.store.db.execute("SELECT * FROM runtime_schedules WHERE last_queue_id=? AND dedupe_key LIKE 'h2.%'",(row['queue_id'],)).fetchone()
            if not schedule:return None
            for p in self.configuration.load().sources:
                if self.state['sources'].get(p.source_profile_id,{}).get('schedule_key')==schedule['dedupe_key']:
                    req=self.request(p.source_profile_id,request_id='schedule.'+row['queue_id'],reason='SCHEDULED');break
            if req is None:return {'state':'FAILED','reason':'CONFIG_REMOVED'}
            self.state['coalesced']+=max(0,(self.store.clock.utc_now_us()-row['due_at_us'])//max(1,schedule['interval_us']))
        try:return self.observe(req)
        except CoreError as exc:return {'state':'FAILED','reason':exc.code}
        finally:
            if request_key:pending.pop(request_key,None)
            self._save()
    def status(self,context):
        c=self.configuration.load();sources=[]
        for p in c.sources:
            if p.scope not in context.allowed_scopes or p.privacy_class not in context.readable_privacy:continue
            last=self.state['sources'].get(p.source_profile_id,{})
            try:health='DISABLED' if not p.enabled else self.resolver.resolve(p).health()
            except Exception:health='UNKNOWN'
            if health not in {'AVAILABLE','DEGRADED','UNAVAILABLE','DISABLED','UNKNOWN'}:health='UNKNOWN'
            last_mid=last.get('last_memory_id')
            if last_mid:
                try:self.records.memory.read(last_mid)
                except CoreError:last_mid=None
            sources.append({'source_profile_id':p.source_profile_id,'health':health,'last_capture_us':last.get('last_capture_us'),'last_technical_observation':last_mid,'last_semantic_state':next((v.get('semantic') for v in reversed(tuple(self.state['requests'].values())) if v['source_profile_id']==p.source_profile_id),None),'last_block':last.get('last_block'),'effective_interval_ms':self.interval_ms(p)})
        return {'sources':sources,'enabled_source_count':sum(p.enabled and p.scope in context.allowed_scopes and p.privacy_class in context.readable_privacy for p in c.sources),'pending_background_observations':len(self.state.get('pending',{})),'dropped':self.state['dropped'],'coalesced':self.state['coalesced'],'will':False,'raw_media':False}
