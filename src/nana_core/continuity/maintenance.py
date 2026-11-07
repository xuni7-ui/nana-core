"""Bounded interruptible source work; candidates are not facts or personality."""
import json
import re
import sqlite3
import time
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
                tx.put('jobs',{'job_id':uid(),'occurrence_key':key,'due_at_us':now+self.interval,'state':'WAITING','body_json':canonical({'scope':scope,'last_deep_review_us':now,'deep_cursor':0}),
                    'work_kind':'SCAN','record_id':None,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
    def slice(self):
        self.discover();now=self.store.clock.utc_now_us()
        job=self.store.db.execute("SELECT * FROM jobs WHERE work_kind='SCAN' AND state='WAITING' AND due_at_us<=? ORDER BY due_at_us LIMIT 1",(now,)).fetchone()
        if not job:return None
        metadata=json.loads(job['body_json']);scope=metadata['scope']
        metadata.setdefault('last_deep_review_us',now);metadata.setdefault('deep_cursor',0)
        # Cursors are resumable source work, not another memory authority. One
        # bounded weekly pass alternates with new material rather than blocking
        # foreground input or rereading the whole Store on every wake.
        deep_due=now-metadata['last_deep_review_us']>=7*86_400_000_000
        mode='WEEKLY_REVIEW' if deep_due and metadata.get('last_scan_mode')!='WEEKLY_REVIEW' else 'INCREMENTAL'
        def read_after(cursor):
            return self.store.db.execute('SELECT rowid AS source_row,* FROM memories WHERE rowid>? AND scope=? ORDER BY rowid LIMIT ?',
                (cursor,scope,self.batch)).fetchall()
        rows=read_after(metadata['deep_cursor'] if mode=='WEEKLY_REVIEW' else job['cursor'])
        if not rows and mode=='INCREMENTAL' and deep_due:
            mode='WEEKLY_REVIEW';rows=read_after(metadata['deep_cursor'])
        if not rows and mode=='WEEKLY_REVIEW':
            metadata.update(last_deep_review_us=now,deep_cursor=0)
        if not rows and self.operational_guard is not None:
            self.operational_guard();self.store.db.execute('BEGIN IMMEDIATE')
            try:
                self.operational_guard()
                # Empty SCAN due time is a reconstructible timer checkpoint.
                # Cursor/revision/support and all learning/action jobs remain intact.
                self.store.db.execute("UPDATE jobs SET due_at_us=?,body_json=? WHERE job_id=? AND work_kind='SCAN' AND cursor=? AND state='WAITING'",
                    (now+self.interval,canonical(metadata),job['job_id'],job['cursor']))
                self.operational_guard();self.store.db.execute('COMMIT')
            except BaseException:
                if self.store.db.in_transaction:self.store.db.execute('ROLLBACK')
                raise
            return {'candidate_record_id':None,'work_id':job['job_id'],'read_count':0,'operational_only':True}
        selected=self._select(rows,scope)
        candidates=[]
        for privacy in dict.fromkeys(r['privacy_class'] for r in selected):
            group=tuple(r for r in selected if r['privacy_class']==privacy)
            offered=self._offer(group,scope,mode)
            if offered:candidates.append(offered)
        candidate=candidates[0] if candidates else None
        cursor=job['cursor']
        more=len(rows)==self.batch
        if mode=='WEEKLY_REVIEW':
            if more:metadata['deep_cursor']=rows[-1]['source_row']
            else:metadata.update(last_deep_review_us=now,deep_cursor=0)
        elif rows:cursor=rows[-1]['source_row']
        metadata['last_scan_mode']=mode
        continuing_deep=now-metadata['last_deep_review_us']>=7*86_400_000_000
        with self.store.transaction('living.maintenance_slice',{'work_id':job['job_id'],'read_count':len(rows),'candidate_record_id':candidate}) as tx:
            tx.update('jobs',job['job_id'],cursor=cursor,body_json=canonical(metadata),revision=job['revision']+1,due_at_us=now+100_000 if more or continuing_deep else now+self.interval,updated_at_us=now)
        return {'candidate_record_id':candidate,'candidate_record_ids':tuple(candidates),'mode':mode,'work_id':job['job_id'],'read_count':len(rows)}
    def _offer(self,selected,scope,mode):
        mids=tuple(r['memory_id'] for r in selected)
        candidate=None
        if mids:
            stamp=source_stamp(self.store,mids);key=digest([mids,stamp])
            old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='living.consolidation' AND source_key=?",(key,)).fetchone()
            if old:candidate=json.loads(old[0])['data']['record_id']
            else:
                fragments=tuple(self._fragment(r) for r in selected)
                text='\n'.join('['+f['memory_id']+'] '+f['excerpt'] for f in fragments)
                data={'target_id':key}
                with self.store.transaction('living.consolidation_candidate',data,source_namespace='living.consolidation',source_key=key) as tx:
                    candidate=self.records.create(tx,kind='MAINTENANCE_CANDIDATE',scope=scope,target_id=key,
                        payload={'kind':'SUMMARY_CANDIDATE','memory_ids':mids,'source_stamp':stamp,'text':text,
                            'coverage':'PARTIAL_EXCERPTS','authority':'INFERRED_NOT_FACT','state':'PROPOSED',
                            'method':'SOURCE_EXCERPTS_V1','fragments':fragments,'mode':mode,
                            'selection':'CURRENT_SUPPORT_IMPORTANCE_SIGNIFICANCE_THEN_SOURCE_TIME',
                            'model_calls':0,'original_sources_preserved':True},memories=mids)
                    data['record_id']=candidate
        return candidate

    def _select(self,rows,scope):
        """Choose existing source value, not sentiment or an invented experience.

        A raw local receipt is not retained conversation. Different privacy
        groups are consolidated separately so a private item cannot taint the
        whole otherwise public batch. Cursor progress never deletes sources.
        """
        candidates=[]
        for row in rows:
            if (not self._visible(row['memory_id']) or row['epistemic_kind'] not in {'OBSERVATION','STATEMENT'}
                    or (row['predicate_key'] or '').startswith('concern.')):continue
            source=self.records.memory.read(row['memory_id'])
            if source['source_provenance']['domain']=='LOCAL_INTERACTION_METADATA':continue
            candidates.append(source)
        important=set()
        for table,states in (('commitments',('ADOPTED','ACTIVE')),('projects',('ACTIVE','PAUSED'))):
            placeholders=','.join('?' for _ in states)
            for head in self.store.db.execute(f"SELECT record_id FROM {table} WHERE scope=? AND state IN ({placeholders}) LIMIT 16",(scope,*states)):
                record=self.store.one('continuity_records',head[0])
                if record and record['lifecycle']=='ACTIVE' and record['privacy_class'] in self.privacy_classes and self.records.current_support(head[0]):
                    important.update(self.records.support(head[0]))
        candidates.sort(key=lambda r:(r['memory_id'] in important,r['importance'],r['significance'],
            r['event_time_us'] if r['event_time_us'] is not None else r['observed_time_us']),reverse=True)
        if not candidates:return ()
        # No eligibility decision promotes reported speech to a world fact.
        return tuple(candidates)[:4]

    @staticmethod
    def _fragment(memory,terms=()):
        text=memory['text'];start=0
        hits=[match for term in terms if (match:=re.search(re.escape(term),text,re.IGNORECASE))]
        if hits:start=max(0,min(match.start() for match in hits)-96)
        excerpt=text[start:start+512]
        return {'memory_id':memory['memory_id'],'excerpt':excerpt,'start':start,'end':start+len(excerpt),
            'full_characters':len(text),'source_kind':memory['source_provenance']['source_kind'],
            'epistemic_kind':memory['epistemic_kind'],'assessment':memory['assessment'],
            'event_time_us':memory['event_time_us'],'observed_time_us':memory['observed_time_us'],
            'ingested_time_us':memory['ingested_time_us']}

    def _recall_candidates(self,terms,deadline):
        self.store.ensure_privacy_current()
        if not self.scopes or not self.privacy_classes:return ()
        if self.store.db.in_transaction:raise CoreError('CONSOLIDATION_RECALL_SAFE_POINT_REQUIRED')
        where,args=self.records.memory._query_filter((self.entity_id,),self.scopes,self.privacy_classes,False,('SEMANTIC',))
        where+=" AND substr(m.predicate_key,1,17)='consolidation.v1.'"
        db=self.store.db
        db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
        try:
            hits=db.execute("SELECT DISTINCT m.memory_id,m.rowid FROM memory_terms t INDEXED BY memory_terms_term_lookup "
                "JOIN memory_dependencies d INDEXED BY memory_dependency_parent_lookup ON d.parent_kind='MEMORY' AND d.parent_id=t.memory_id "
                "JOIN memories m ON m.memory_id=d.memory_id WHERE t.term IN ("+','.join('?' for _ in terms)+") AND "+where+
                " ORDER BY m.rowid DESC LIMIT 16",(*[t.casefold() for t in terms],*args)).fetchall()
            # Bounded recent fallback supports substring queries not represented
            # as an exact lexical term. Never scans every archived text payload.
            ids=[row[0] for row in hits]
            if len(ids)<16:
                recent=db.execute('SELECT m.memory_id FROM memories m INDEXED BY memory_consolidated_lookup WHERE '+where+
                    ' ORDER BY m.rowid DESC LIMIT 16',args).fetchall()
                ids=list(dict.fromkeys((*ids,*(row[0] for row in recent))))[:16]
        except sqlite3.OperationalError as exc:
            if 'interrupt' in str(exc).lower():raise CoreError('CONSOLIDATION_RECALL_TIME_BOUND') from None
            raise
        finally:db.set_progress_handler(None,0)
        return tuple(self.records.memory.read(mid) for mid in ids)

    def recall(self,terms,*,limit=2):
        """Query only original C-adopted extractive memory, checking parents now.

        Read at most16 summary payloads; every returned excerpt is read again
        from its current original source. No cached summary becomes authority.
        """
        terms=tuple(t for t in terms if type(t) is str and 2<=len(t)<=64)[:8]
        if not terms:return ()
        deadline=time.monotonic()+.1
        summaries=self._recall_candidates(terms,deadline)
        found=[]
        for summary in summaries:
            if time.monotonic()>deadline:raise CoreError('CONSOLIDATION_RECALL_TIME_BOUND')
            rid=summary['source_provenance']['source_reference']
            try:head,body=self.candidate(rid)
            except CoreError:continue
            if body.get('method')!='SOURCE_EXCERPTS_V1':continue
            adopted=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='living.consolidation-adopted' AND source_key=?",(rid,)).fetchone()
            if not adopted or json.loads(adopted[0])['data'].get('memory_id')!=summary['memory_id']:continue
            fragments=[]
            for mid in body['memory_ids']:
                original=self.records.memory.read(mid)
                if any(re.search(re.escape(t),original['text'],re.IGNORECASE) for t in terms):
                    fragments.append(self._fragment(original,terms))
            if not fragments:continue
            found.append({'summary_memory_id':summary['memory_id'],'candidate_record_id':rid,
                'source_memory_ids':tuple(body['memory_ids']),'fragments':tuple(fragments),
                'authority':'DERIVED_EXCERPTS_NOT_NEW_FACT','coverage':'PARTIAL_EXCERPTS',
                'source_stamp':body['source_stamp'],'execution_authority':False})
            if len(found)>=limit:break
        return tuple(found)

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
        mid=self.records.memory.add(MemoryCandidate(entity_id=self.entity_id,scope=head['scope'],memory_type=MemoryType.SEMANTIC,epistemic_kind='SUMMARY',source_evidence_id=e,text=body['text'],derived_from=tuple(body['memory_ids']),confidence=.5,
            predicate_key='consolidation.v1.'+rid if body.get('method')=='SOURCE_EXCERPTS_V1' else None))
        with self.store.transaction('living.consolidation_adopted',{'candidate_record_id':rid,'memory_id':mid},source_namespace='living.consolidation-adopted',source_key=rid):pass
        if cycle.intention_id:self._complete(cycle.intention_id)
        return mid
    def _complete(self,iid):
        i=self.store.one('subject_intentions',iid)
        if i and i['state']=='PENDING':
            with self.store.transaction('living.memory_review_completed') as tx:tx.update('subject_intentions',iid,state='COMPLETED',revision=i['revision']+1)
