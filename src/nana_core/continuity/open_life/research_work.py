"""C-endorsed research, one original D background slice at a time.

Not a new loop/planner: indexed original jobs and the original ResearchService.
Only explicitly configured owned sources and deterministic typed feed adapters.
"""
import json
from ...contracts import CoreError
from ...storage import digest,uid
from ..records import RecordService
from ..world_loop.world import SourcedClaim
from .research import ResearchService


class ResearchWork:
    def __init__(self,runtime,queue,intake):
        self.runtime,self.queue,self.intake=runtime,queue,intake
        self.records=RecordService(runtime.store);self.research=ResearchService(runtime,queue,intake)

    def reconcile(self):
        s=self.runtime.store
        for row in s.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH' AND state='DONE' ORDER BY updated_at_us DESC LIMIT 16"):
            h=s.one('continuity_records',row['record_id'])
            if h and h['lifecycle']=='ACTIVE' and h['scope'] in self.runtime.config.scopes and h['privacy_class'] in self.runtime.config.privacy_classes and self.records.current_support(h['record_id']):self._ack(self.records.read(h['record_id'])['payload'])
        # Also closes the crash gap between C acknowledgment and scheduling.
        for row in s.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_OPPORTUNITY' AND state='DONE' ORDER BY updated_at_us DESC LIMIT 16"):
            key='life-research:'+digest(row['job_id'])
            if s.db.execute('SELECT 1 FROM jobs WHERE occurrence_key=?',(key,)).fetchone():continue
            h=s.one('continuity_records',row['record_id'])
            if not h or h['lifecycle']!='ACTIVE' or h['scope'] not in self.runtime.config.scopes or h['privacy_class'] not in self.runtime.config.privacy_classes or not self.records.current_support(h['record_id']):continue
            b=self.records.read(h['record_id'])['payload']
            if b.get('behavior')!='EXPLORE' or b.get('normative')!='ENDORSED' or b['candidate']['kind'] not in {'WORLD_CHANGE','CURIOSITY'}:continue
            if not self.intake.sources:continue
            if s.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_RESEARCH' AND state IN ('WAITING','UNKNOWN')").fetchone()[0]>=4:return None
            query=None
            for mid in b['candidate']['source_memory_ids']:
                try:body=json.loads(self.records.memory.read(mid)['text'])
                except ValueError:continue
                c=body.get('world_claim') if isinstance(body,dict) else None
                if c:query={'entity_id':c['entity_id'],'predicate':c['predicate']};break
            sources=tuple(self.intake.sources)[:4];now=self.runtime.clock.utc_now_us();jid=uid()
            with s.transaction('life.research_selected',{'job_id':jid,'original_cycle_id':b['cycle_id']}) as tx:
                rid=self.records.create(tx,kind='RUNTIME_WORK',scope=h['scope'],payload={'kind':'RESEARCH_WORK','opportunity_id':row['job_id'],'cycle_id':b['cycle_id'],'query':query,'sources':sources,'source_bindings':{n:digest(self.intake.sources[n].model_dump(mode='json')) for n in sources},'semantic_memory_ids':[],'state':'GATHER','not_learning':True},records=(h['record_id'],),target_id=key)
                tx.put('jobs',{'job_id':jid,'occurrence_key':key,'due_at_us':now,'state':'WAITING','body_json':'{}','work_kind':'LIFE_RESEARCH','record_id':rid,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
            return jid
        return None

    def _ack(self,body):
        s=self.runtime.store;cycle=s.one('subject_cycles',body['cycle_id'])
        iid=self.runtime.subject.result(cycle).intention_id if cycle else None
        intention=s.one('subject_intentions',iid) if iid else None
        if intention and intention['state']=='PENDING':self.runtime.subject.transition_intention(iid,expected_revision=intention['revision'],state='COMPLETED')

    def slice(self):
        r=self.runtime;s=r.store
        if r.work.paused:return None
        self.reconcile()
        scopes=','.join('?' for _ in r.config.scopes);privacy=','.join('?' for _ in r.config.privacy_classes)
        row=s.db.execute(f"SELECT j.* FROM jobs j JOIN continuity_records h ON h.record_id=j.record_id WHERE j.work_kind='LIFE_RESEARCH' AND j.state='WAITING' AND h.scope IN ({scopes}) AND h.privacy_class IN ({privacy}) ORDER BY j.due_at_us LIMIT 1",(*r.config.scopes,*r.config.privacy_classes)).fetchone()
        if not row:return None
        head=s.one('continuity_records',row['record_id'])
        if not head or head['lifecycle']!='ACTIVE' or not self.records.current_support(row['record_id']):
            with s.transaction('life.research_source_retired',{'job_id':row['job_id']}) as tx:tx.update('jobs',row['job_id'],state='CANCELLED',revision=row['revision']+1)
            return {'research_job_id':row['job_id'],'state':'SOURCE_RETIRED'}
        b=self.records.read(row['record_id'])['payload'];new=dict(b);parents=[];memories=[]
        try:
            if row['cursor']<len(b['sources']):
                source_id=b['sources'][row['cursor']];source=self.intake.sources.get(source_id)
                if not source or digest(source.model_dump(mode='json'))!=b['source_bindings'][source_id]:raise CoreError('RESEARCH_HOST_SOURCE_REBIND_REQUIRED')
                raw=self.research.gather(b['opportunity_id'],source_id);memories.append(raw)
                if source.semantic_format=='SOURCED_CLAIM_JSON':
                    body=json.loads(self.records.memory.read(raw)['text'])
                    claim=SourcedClaim.model_validate_json(json.dumps(json.loads(body['content'])['world_claim']))
                    mid,_=self.intake.interpret(raw,claim)
                    if b['query'] and (claim.entity_id,claim.predicate)==(b['query']['entity_id'],b['query']['predicate']):new['semantic_memory_ids']=list(dict.fromkeys((*b['semantic_memory_ids'],mid)));memories.append(mid)
                cursor=row['cursor']+1;state='WAITING'
            else:
                mids=tuple(b['semantic_memory_ids']);query=b['query']
                if mids and query:
                    comparison=self.research.compare(b['opportunity_id'],query['entity_id'],query['predicate'],mids);parents.append(comparison)
                    new['comparison_record_id']=comparison
                    new['state']=self.records.read(comparison)['payload']['state']
                else:new['state']='GATHERED_ONLY_INSUFFICIENT_SEMANTICS'
                cursor=row['cursor'];state='DONE'
        except (CoreError,ValueError,KeyError) as exc:
            if isinstance(exc,CoreError) and exc.code in {'RUNTIME_LEASE_LOST','PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE'}:raise
            with s.transaction('life.research_parked',{'job_id':row['job_id'],'reason':exc.code if isinstance(exc,CoreError) else 'INVALID_SEMANTIC_FEED'}) as tx:tx.update('jobs',row['job_id'],state='UNKNOWN' if isinstance(exc,CoreError) and 'UNKNOWN' in exc.code else 'BLOCKED',revision=row['revision']+1)
            return {'research_job_id':row['job_id'],'state':'PARKED_NO_RETRY'}
        with s.transaction('life.research_slice',{'job_id':row['job_id'],'state':new['state']}) as tx:
            rid=self.records.create(tx,kind='RUNTIME_WORK',scope=head['scope'],payload=new,records=(row['record_id'],*parents),memories=memories,supersedes=row['record_id'],target_id=head['target_id'])
            tx.update('jobs',row['job_id'],record_id=rid,state=state,cursor=cursor,revision=row['revision']+1,updated_at_us=r.clock.utc_now_us())
        if state=='DONE':
            self._ack(b)
        return {'research_job_id':row['job_id'],'state':new['state'],'cursor':cursor,'not_learning':True}
