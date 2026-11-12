"""C-owned sourced concern/interest/goal formation; D only offers a time slice."""
import json
from ...contracts import CoreError
from ...storage import canonical,digest,uid
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..records import RecordService
from ..subject.opportunities import ConcernCue
from ..subject.contracts import SubjectInput
from ..open_agency.contracts import Objective
from ..open_agency.world import LocalWorldRegistry
from .cognition import CognitionReply
from .concern_source import binding as concern_binding

class ConcernService:
    def __init__(self,runtime,*,resources,max_hot=16,revisit_us=3600_000_000,cognition=None):
        self.runtime,self.store=runtime,runtime.store;self.records=RecordService(self.store)
        self.cognition=cognition  # Existing coordinator session, never another thinker.
        self.resources=frozenset(resources);self.max_hot=max_hot;self.revisit=revisit_us
        if not 1<=max_hot<=32 or not 1<=len(self.resources)<=128:raise CoreError('CONCERN_POLICY_BOUND')
    def _fresh_attention_can_return(self, old, previous):
        """New evidence may reopen attention, never replay a parked execution.

        An interpreted interest without an objective/skill used to remain
        PROPOSED forever, even after a new independent encounter. The original
        C must be allowed to reconsider that new evidence. Goal/skill recovery
        and ambiguous provider/effect completion retain their existing fences.
        """
        if old['state'] not in {'TRANSIENT','INTEREST','DEFERRED','PROPOSED','EXPIRED'} or old['goal_id'] or previous.get('objective') or previous.get('skill_task'):
            return False
        if self.store.db.execute("SELECT 1 FROM cognitive_requests WHERE state IN ('PREPARED','CALLING','UNKNOWN') LIMIT 1").fetchone():
            return False
        return not self.store.db.execute("SELECT 1 FROM actions WHERE state IN ('DISPATCHING','UNKNOWN','PENDING_VERIFY') LIMIT 1").fetchone()
    def _changed_world_review(self, proposal_record, previous):
        """A current semantic revision can reopen judgment, not add an encounter.

        Compare the original session's sourced world snapshots. New wording or
        a new memory ID alone is not novelty. The same session validates owner,
        deadline, context, route and live support before C can see the revision.
        """
        if self.cognition is None:
            return False
        try:
            reply=self.cognition.proposal(proposal_record)
            prior=self.records.read(previous['proposal_record_id'])['payload']['reply']
            requests=[]
            for request_id in (prior['request_id'],reply.request_id):
                row=self.store.one('cognitive_requests',request_id)
                if not row or row['state']!='PROPOSED':return False
                requests.append(self.records.read(row['record_id'])['payload']['request'])
            before,after=requests
            return (before['cognitive_role']==after['cognitive_role']
                    and after['cognitive_role'] in {'GOALS','INTERPRET'}
                    and before['world_stamp']!=after['world_stamp'])
        except (CoreError,KeyError):
            return False
    def offer(self,proposal_record):
        record=self.records.read(proposal_record)
        if record['record_kind']!='COGNITION_PROPOSAL' or not self.records.current_support(proposal_record):raise CoreError('CONCERN_PROPOSAL_SOURCE_REQUIRED')
        if record['scope'] not in self.runtime.config.scopes or record['privacy_class'] not in self.runtime.config.privacy_classes:raise CoreError('CONCERN_PRIVACY_DENIED')
        reply=CognitionReply.model_validate_json(canonical(record['payload']['reply']));accepted=[]
        for idea in reply.proposal.interests:
            if not set(idea.source_memory_ids)<=set(self.records.support(proposal_record)):raise CoreError('CONCERN_SOURCE_MISMATCH')
            obj=idea.objective
            if obj:
                if obj.scope!=record['scope'] or obj.motivation_source!=idea.motivation_source:raise CoreError('GOAL_CANDIDATE_SCOPE_MISMATCH')
                for op in obj.operators:
                    if op.resource not in self.resources:raise CoreError('GOAL_RESOURCE_NOT_DESCRIBED')
                    LocalWorldRegistry().validate(op.capability,op.resource,op.args)
            key=digest([record['scope'],self.runtime.config.entity_id,idea.topic]);old=self.store.db.execute('SELECT * FROM open_concerns WHERE concern_key=?',(key,)).fetchone()
            if old and old['state']=='ABANDONED':continue
            faded=bool(old and old['state']=='EXPIRED')
            same_encounter=False
            if old:
                try:previous=self.records.read(old['record_id'])['payload']
                except CoreError:continue
                if set(idea.source_memory_ids)<=set(previous['encounter_sources']):continue
                # New Memory IDs can merely be interpretations/summaries of the
                # same occurrence. They must not inflate interest or keep an old
                # thought alive. Share original S3's evidence-root resolution;
                # fresh raw sources and different topics retain their choices.
                from ..subject.growth import Growth
                roots=Growth(self.store)
                try:
                    incoming=roots.source_roots(idea.source_memory_ids,max_nodes=128)
                    encountered=roots.source_roots(previous['encounter_sources'],max_nodes=128)
                except CoreError:
                    continue  # Retired/ambiguous ancestry is not novelty.
                same_encounter=not set(incoming)-set(encountered)
                if same_encounter:
                    if (obj or idea.skill_task or faded
                            or not self._fresh_attention_can_return(old,previous)
                            or not self._changed_world_review(proposal_record,previous)):
                        continue
                if faded and not self._fresh_attention_can_return(old,previous):continue
                # An adopted objective cannot be silently changed by new prose.
                if previous.get('objective') and obj and previous['objective']!=obj.model_dump(mode='json'):raise CoreError('CONCERN_OBJECTIVE_REVISION_REQUIRED')
                sources=tuple(dict.fromkeys((*previous['encounter_sources'],*idea.source_memory_ids)))
                if len(sources)>32:continue  # Do not count encounters we cannot retain/trace.
            if not old or faded:
                # Erased records are opaque historical headers, not live
                # attention. Keeping them must not permanently consume capacity.
                if self.store.db.execute("SELECT count(*) FROM open_concerns c JOIN continuity_records r ON c.record_id=r.record_id WHERE c.state NOT IN ('ABANDONED','EXPIRED') AND r.lifecycle='ACTIVE'").fetchone()[0]>=self.max_hot:continue
                if not old:sources=idea.source_memory_ids
            # Time fading is not a permanent ban on curiosity. Fresh support
            # opens one new review, without carrying a previous excitement count,
            # re-adopting a goal or forgetting the original privacy dependencies.
            count=1 if not old or faded else old['encounters']+(0 if same_encounter else 1)
            reconsider = bool(old and self._fresh_attention_can_return(old, previous))
            state=('INTEREST' if idea.expected_value=='HIGH' or count>=2 else 'TRANSIENT') if not old or old['state'] in {'TRANSIENT','INTEREST','DEFERRED'} or reconsider else old['state']
            if idea.expected_value=='LOW' and old and old['goal_id']:state='INTEREST'
            body={**idea.model_dump(mode='json'),'encounter_sources':sources,'proposal_record_id':proposal_record,'goal_candidate_not_adopted':True,'last_enqueued_revision':None}
            cid=old['concern_id'] if old else uid();now=self.store.clock.utc_now_us()
            with self.store.transaction('world.concern_formed',{'concern_id':cid,'state':state}) as tx:
                rid=self.records.create(tx,kind='OPEN_CONCERN',scope=record['scope'],payload=body,memories=sources,records=(proposal_record,*((old['record_id'],) if old else ())),supersedes=old['record_id'] if old else None,target_id=cid)
                if old:tx.update('open_concerns',cid,record_id=rid,state=state,revision=old['revision']+1,encounters=count,next_review_us=now,updated_at_us=now)
                else:tx.put('open_concerns',{'concern_id':cid,'concern_key':key,'record_id':rid,'state':state,'revision':1,'encounters':count,'next_review_us':now,'updated_at_us':now,'goal_id':None})
            accepted.append(cid)
        return tuple(accepted)
    def restore_descriptions(self):
        # Reconstruct descriptive plans only, not old Grants or execution handles.
        for row in self.store.db.execute("SELECT * FROM open_concerns WHERE state NOT IN ('ABANDONED','EXPIRED') LIMIT 32"):
            try:
                body=self.records.read(row['record_id'])['payload']
                if not self.records.current_support(row['record_id']):continue
                if body['objective']:self.runtime.work.agency.policy.offer(Objective.model_validate_json(canonical(body['objective'])))
            except CoreError:continue
    def opportunity(self, *, concern_ids=None):
        r=self.runtime;now=self.store.clock.utc_now_us()
        selected, args = '', [now]
        if concern_ids is not None:
            if type(concern_ids) is not tuple or not 1 <= len(concern_ids) <= 16 or any(type(c) is not str for c in concern_ids):
                raise CoreError('CONCERN_SELECTION_BOUND')
            selected = ' AND concern_id IN (' + ','.join('?' for _ in concern_ids) + ')'
            args.extend(concern_ids)
        for row in self.store.db.execute("SELECT * FROM open_concerns WHERE state IN ('TRANSIENT','INTEREST','DEFERRED','PROPOSED') AND next_review_us<=?" + selected + " ORDER BY encounters DESC,updated_at_us LIMIT 16",args):
            try:body=self.records.read(row['record_id'])['payload']
            except CoreError:continue
            if not self.records.current_support(row['record_id']):continue
            age=now-row['updated_at_us']
            if row['state']=='PROPOSED':
                # A considered pure thought must not consume hot capacity forever.
                # Never re-enqueue its committed decision or retire goal/skill work;
                # expiry changes only this opportunity, not identity or relationship.
                if age<=3*86400_000_000 or row['goal_id'] or body['objective'] or body['skill_task']:
                    continue
            if age>3*86400_000_000:
                with self.store.transaction('world.concern_expired',{'concern_id':row['concern_id']}) as tx:tx.update('open_concerns',row['concern_id'],state='EXPIRED',revision=row['revision']+1)
                continue
            if row['state']=='TRANSIENT':
                with self.store.transaction('world.concern_deferred',{'concern_id':row['concern_id']}) as tx:tx.update('open_concerns',row['concern_id'],next_review_us=now+self.revisit)
                continue
            if body['objective'] and body['expected_value']!='LOW':r.work.agency.policy.offer(Objective.model_validate_json(canonical(body['objective'])))
            behavior=('IGNORE',) if body['expected_value']=='LOW' else ('SEEK_CAPABILITY',) if body['skill_task'] else ('EXPLORE',) if body['motivation_source']=='CURIOSITY' else tuple(body.get('possible_behaviors',()))
            cue=ConcernCue(cue_kind='DISCOVERY',motivation_source=body['motivation_source'],topic_key=body['topic'],program_id=body['objective']['objective_id'] if body['objective'] and body['expected_value']!='LOW' else None,possible_behaviors=behavior)
            key=digest([row['concern_id'],row['revision']]);source_ids=tuple(body['source_memory_ids'])
            try:event_key, domain, namespace, event_domain = concern_binding(self.store, row)
            except CoreError as exc:
                if exc.code=='CONCERN_EXPLICIT_RETENTION_REQUIRED':continue
                raise
            prior=self.store.db.execute('SELECT * FROM subject_events WHERE source_key=?',(event_key,)).fetchone()
            if prior:
                accepted=self.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(prior['subject_event_id'],)).fetchone()
                if accepted:
                    # Queue recovery may already acknowledge a committed C cycle.
                    # Finish its idempotent post-commit work instead of resubmitting
                    # the DONE envelope forever or generating a second decision.
                    source_event=SubjectInput.model_validate_json(canonical(self.records.read(prior['record_id'])['payload']['input']))
                    try:r.work.after_cycle(r.subject.result(dict(accepted)),source_event)
                    except CoreError as exc:
                        # A committed judgment is not permission to retry a failed
                        # provider forever. Preserve it and park realization until
                        # fresh reviewed input, never invent a second C decision.
                        if exc.code not in {'INSUFFICIENT_CONTEXT_BUDGET','INSUFFICIENT_CONTRADICTION_CONTEXT','COGNITION_SOURCE_OUTSIDE_CONTEXT_BUDGET','COGNITION_DAILY_BUDGET','COGNITION_PROPOSAL_UNAVAILABLE','COGNITION_BYTE_BUDGET','COGNITION_COST_BUDGET','STALE_COGNITION_PROPOSAL'}:raise
                        with self.store.transaction('world.concern_recovery_parked',{'concern_id':row['concern_id'],'cycle_id':accepted['cycle_id'],'reason':exc.code}) as tx:
                            tx.update('open_concerns',row['concern_id'],state='PROPOSED',revision=row['revision']+1)
                    return None
            memory=self.records.memory;source=memory.read(source_ids[0]);when=row['updated_at_us']
            eid=memory.capture(EvidenceInput(retention_consent_ref=key if domain=='CONSENTED_INTERACTION' else None,provenance=Provenance(domain=domain,source_namespace=namespace,source_reference=key,source_kind='MODEL_DERIVATION'),text=cue.model_dump_json(),privacy_class=self.records.read(row['record_id'])['privacy_class'],observed_time_us=when,event_time_us=source['event_time_us']))
            prior=self.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(eid,)).fetchone()
            mid=prior[0] if prior else memory.add(MemoryCandidate(entity_id=r.config.entity_id,scope=source['scope'],memory_type=MemoryType.PROSPECTIVE,epistemic_kind='INFERENCE',source_evidence_id=eid,text=cue.model_dump_json(),derived_from=tuple(self.records.support(row['record_id'])),predicate_key='concern.'+body['topic'],confidence=.4))
            from ...presence.contracts import RuntimeEvent,Cause
            inp=SubjectInput(domain=event_domain,source_key=event_key,world_concern_id=row['concern_id'],kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=source['scope'],source_memory_ids=(mid,),observed_at_us=when,privacy_class=self.records.read(row['record_id'])['privacy_class'],novelty='RELEVANT')
            return RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=when,priority=1)
        return None
    def after_cycle(self,cycle,event,result):
        cid=event.world_concern_id
        if not cid:return
        row=self.store.one('open_concerns',cid)
        if not row:return
        if event.source_key!=concern_binding(self.store,row)[0]:raise CoreError('STALE_CONCERN_CYCLE')
        body=self.records.read(row['record_id'])['payload'];goal=result if isinstance(result,str) and self.store.one('goals',result) else row['goal_id']
        state='ADOPTED' if goal else 'PROPOSED' if cycle.intention.kind not in {'NO_ACTION','WAIT'} and cycle.evaluation and cycle.evaluation.normative=='ENDORSED' else 'DEFERRED'
        if body['expected_value']=='LOW' and goal:state='DEFERRED'
        if body['expected_value']=='LOW' and cycle.intention.kind=='NO_ACTION' and cycle.intention.behavior=='IGNORE':
            if goal:
                g=self.store.one('goals',goal);cause=next((m for m in body['encounter_sources'] if self.records.memory.read(m)['authority']=='DIRECT'),None)
                if g['state'] in {'ACTIVE','SUSPENDED','BLOCKED','FAILED'} and cause:self.runtime.work.agency.transition(goal,'ABANDONED',expected_version=g['version'],authority=self.runtime.authority,cause_memory_id=cause)
            state='ABANDONED'
        with self.store.transaction('world.concern_judged',{'concern_id':cid,'cycle_id':cycle.cycle_id,'state':state}) as tx:tx.update('open_concerns',cid,state=state,goal_id=goal,next_review_us=self.store.clock.utc_now_us()+self.revisit,revision=row['revision']+1)
    def view(self,*,scopes=None,privacy_classes=None):
        scopes=tuple(scopes or self.runtime.config.scopes);privacy=tuple(privacy_classes or self.runtime.config.privacy_classes)
        out=[]
        for row in self.store.db.execute('SELECT * FROM open_concerns ORDER BY updated_at_us DESC LIMIT 32'):
            head=self.store.one('continuity_records',row['record_id'])
            if head['scope'] not in scopes or head['privacy_class'] not in privacy or head['lifecycle']!='ACTIVE' or not self.records.current_support(row['record_id']):continue
            b=self.records.read(row['record_id'])['payload']
            from .concern_source import source_domains
            private='SELF_COGNITION' in source_domains(self.store,row['record_id'])
            item={'concern_id':row['concern_id'],'topic':'private-content-withheld' if private else b['topic'],
                'motivation':'PRIVATE_CONTENT_WITHHELD' if private else b['motivation_source'],
                'state':row['state'],'encounters':row['encounters'],'goal_id':row['goal_id'],'source_record_id':row['record_id']}
            if private:item['private_content_withheld']=True
            out.append(item)
        return tuple(out)
