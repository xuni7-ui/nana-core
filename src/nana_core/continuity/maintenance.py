"""Bounded interruptible source work; candidates are not facts or personality."""
import json
from ..contracts import CoreError
from ..storage import canonical,digest,uid
from .records import RecordService
from .contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType


def source_stamp(store,mids):
    records=RecordService(store);values=[]
    for mid in mids:
        m=records.memory.read(mid)
        values.append((mid,m['updated_at_us'],m['source_evidence_id'],m['assessment'],m['privacy_class']))
    return digest(values)

class MaintenanceService:
    def __init__(self,store,*,scopes,entity_id,privacy_classes,slice_items=4,interval_us=3600000000,operational_guard=None):
        self.store,self.scopes,self.entity_id,self.privacy_classes=store,scopes,entity_id,privacy_classes
        self.records=RecordService(store);self.batch=slice_items;self.interval=interval_us;self.operational_guard=operational_guard
    def _visible(self,mid):
        r=self.store.one('memories',mid)
        return bool(r and r['scope'] in self.scopes and r['entity_id'] in {self.entity_id,self.store.identity['identity_id']} and r['privacy_class'] in self.privacy_classes and r['lifecycle']=='ACTIVE' and r['assessment'] in {'CURRENT','UNASSESSED'})
    def discover(self):
        for scope in self.scopes:
            key='maintenance-scan:'+scope
            if self.store.db.execute('SELECT 1 FROM jobs WHERE occurrence_key=?',(key,)).fetchone():continue
            now=self.store.clock.utc_now_us()
            with self.store.transaction('living.maintenance_scheduled') as tx:
                tx.put('jobs',{'job_id':uid(),'occurrence_key':key,'due_at_us':now+self.interval,'state':'WAITING','body_json':canonical({'scope':scope}),
                    'work_kind':'SCAN','record_id':None,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
    def slice(self):
        self.discover();now=self.store.clock.utc_now_us()
        job=self.store.db.execute("SELECT * FROM jobs WHERE work_kind='SCAN' AND state='WAITING' AND due_at_us<=? ORDER BY due_at_us LIMIT 1",(now,)).fetchone()
        if not job:return None
        scope=json.loads(job['body_json'])['scope']
        # Cursor is operational row progress, never a second memory fact.
        rows=self.store.db.execute('SELECT rowid AS source_row,* FROM memories WHERE rowid>? AND scope=? ORDER BY rowid LIMIT ?',(job['cursor'],scope,self.batch)).fetchall()
        if not rows and self.operational_guard is not None:
            self.operational_guard();self.store.db.execute('BEGIN IMMEDIATE')
            try:
                self.operational_guard()
                # Empty SCAN due time is a reconstructible timer checkpoint.
                # Cursor/revision/support and all learning/action jobs remain intact.
                self.store.db.execute("UPDATE jobs SET due_at_us=? WHERE job_id=? AND work_kind='SCAN' AND cursor=? AND state='WAITING'",
                    (now+self.interval,job['job_id'],job['cursor']))
                self.operational_guard();self.store.db.execute('COMMIT')
            except BaseException:
                if self.store.db.in_transaction:self.store.db.execute('ROLLBACK')
                raise
            return {'candidate_record_id':None,'work_id':job['job_id'],'read_count':0,'operational_only':True}
        mids=tuple(r['memory_id'] for r in rows if self._visible(r['memory_id']) and r['epistemic_kind'] in {'OBSERVATION','STATEMENT'} and not (r['predicate_key'] or '').startswith('concern.'))
        candidate=None
        if len(mids)>=2:
            stamp=source_stamp(self.store,mids);key=digest([mids,stamp])
            old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='living.consolidation' AND source_key=?",(key,)).fetchone()
            if old:candidate=json.loads(old[0])['data']['record_id']
            else:
                text='\n'.join('['+mid+'] '+self.records.memory.read(mid)['text'][:256] for mid in mids)
                data={'target_id':key}
                with self.store.transaction('living.consolidation_candidate',data,source_namespace='living.consolidation',source_key=key) as tx:
                    candidate=self.records.create(tx,kind='MAINTENANCE_CANDIDATE',scope=scope,target_id=key,payload={'kind':'SUMMARY_CANDIDATE','memory_ids':mids,'source_stamp':stamp,'text':text,'coverage':'PARTIAL_EXCERPTS','authority':'INFERRED_NOT_FACT','state':'PROPOSED'},memories=mids)
                    data['record_id']=candidate
        cursor=rows[-1]['source_row'] if rows else job['cursor']
        more=len(rows)==self.batch
        with self.store.transaction('living.maintenance_slice',{'work_id':job['job_id'],'read_count':len(rows),'candidate_record_id':candidate}) as tx:
            tx.update('jobs',job['job_id'],cursor=cursor,revision=job['revision']+1,due_at_us=now+100_000 if more else now+self.interval,updated_at_us=now)
        return {'candidate_record_id':candidate,'work_id':job['job_id'],'read_count':len(rows)}
    def candidate(self,rid):
        head=self.store.one('continuity_records',rid)
        if not head or head['record_kind']!='MAINTENANCE_CANDIDATE' or head['scope'] not in self.scopes or head['privacy_class'] not in self.privacy_classes or not self.records.current_support(rid):raise CoreError('MAINTENANCE_SOURCE_UNAVAILABLE')
        body=self.records.read(rid)['payload']
        if any(not self._visible(mid) for mid in body['memory_ids']) or source_stamp(self.store,body['memory_ids'])!=body['source_stamp']:raise CoreError('MAINTENANCE_SOURCE_STALE')
        return head,body
    def adopt(self,rid,cycle):
        if cycle.selected_memory_candidate_id!=rid or cycle.intention.kind!='MEMORY_CANDIDATE' or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED':return None
        head,body=self.candidate(rid)
        old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='living.consolidation-adopted' AND source_key=?",(rid,)).fetchone()
        if old:return json.loads(old[0])['data']['memory_id']
        # Legacy provenance name denotes derivation; no real model was called.
        e=self.records.memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.consolidation',source_reference=rid,source_kind='MODEL_DERIVATION',coverage='EXCERPT'),text=body['text'],privacy_class=head['privacy_class'],observed_time_us=head['created_at_us']))
        mid=self.records.memory.add(MemoryCandidate(entity_id=self.entity_id,scope=head['scope'],memory_type=MemoryType.SEMANTIC,epistemic_kind='SUMMARY',source_evidence_id=e,text=body['text'],derived_from=tuple(body['memory_ids']),confidence=.5))
        with self.store.transaction('living.consolidation_adopted',{'candidate_record_id':rid,'memory_id':mid},source_namespace='living.consolidation-adopted',source_key=rid):pass
        if cycle.intention_id:self._complete(cycle.intention_id)
        return mid
    def _complete(self,iid):
        i=self.store.one('subject_intentions',iid)
        if i and i['state']=='PENDING':
            with self.store.transaction('living.memory_review_completed') as tx:tx.update('subject_intentions',iid,state='COMPLETED',revision=i['revision']+1)
