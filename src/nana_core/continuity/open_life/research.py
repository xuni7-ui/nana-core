"""C-selected, evidence-dependent research episodes. Research is not learning."""
import json
from ...contracts import CoreError
from ...storage import digest
from ..records import RecordService
from ..subject.opportunities import ConcernCue
from ..world_loop.world import WorldModel
from .opportunities import LifeOpportunity


class ResearchService:
    def __init__(self,runtime,queue,intake):
        self.runtime,self.queue,self.intake=runtime,queue,intake;self.records=RecordService(runtime.store)
    def notice(self,topic,source_memory_ids):
        return self.queue.offer(LifeOpportunity(kind='CURIOSITY',topic=topic,source_memory_ids=source_memory_ids,
            cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=topic,motivation_source='UNRESOLVED_QUESTION',possible_behaviors=('EXPLORE','WATCH','REST'),resource_class='ORDINARY'),expires_at_us=self.runtime.clock.utc_now_us()+86400_000_000))
    def gather(self,opportunity_id,source_id):
        s=self.runtime.store;job=s.one('jobs',opportunity_id)
        if not job or job['work_kind']!='LIFE_OPPORTUNITY' or job['state']!='DONE':raise CoreError('RESEARCH_C_JUDGMENT_REQUIRED')
        head=self.records.read(job['record_id']);body=head['payload']
        if body.get('behavior')!='EXPLORE' or body.get('normative')!='ENDORSED' or not self.records.current_support(head['record_id']):raise CoreError('RESEARCH_NOT_ENDORSED')
        key='research:'+digest([opportunity_id,source_id])
        old=s.db.execute("SELECT record_id,lifecycle FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=? ORDER BY rowid DESC LIMIT 1",(key,)).fetchone()
        if old:
            if old['lifecycle']!='ACTIVE' or not self.records.current_support(old['record_id']):raise CoreError('RESEARCH_SOURCE_RETIRED')
            return self.records.read(old['record_id'])['payload']['source_memory_id']
        # Per episode bound is explicit, independent of a model's request count.
        existing=s.db.execute("SELECT count(*) FROM record_dependencies d JOIN continuity_records r ON d.record_id=r.record_id JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE d.parent_id=? AND d.parent_kind='RECORD' AND r.record_kind='RUNTIME_WORK' AND json_extract(CAST(a.payload AS TEXT),'$.kind')='RESEARCH_EPISODE'",(head['record_id'],)).fetchone()[0]
        if existing>=4:raise CoreError('RESEARCH_SOURCE_BUDGET')
        mid=self.intake.read(source_id,observation_id=opportunity_id)
        with s.transaction('life.research_source_gathered',{'opportunity_id':opportunity_id}) as tx:
            self.records.create(tx,kind='RUNTIME_WORK',scope=head['scope'],payload={'kind':'RESEARCH_EPISODE','state':'GATHERED_NOT_CONCLUDED','source_memory_id':mid,'cycle_id':body['cycle_id'],'not_learning':True},memories=(mid,),records=(head['record_id'],),target_id=key)
        return mid
    def compare(self,opportunity_id,entity,predicate,semantic_memory_ids):
        job=self.runtime.store.one('jobs',opportunity_id)
        if not job or job['state']!='DONE':raise CoreError('RESEARCH_C_JUDGMENT_REQUIRED')
        head=self.records.read(job['record_id']);b=head['payload']
        if b.get('behavior')!='EXPLORE' or b.get('normative')!='ENDORSED' or not self.records.current_support(head['record_id']):raise CoreError('RESEARCH_NOT_ENDORSED')
        if not 1<=len(semantic_memory_ids)<=4:raise CoreError('RESEARCH_SOURCE_BUDGET')
        independent=set()
        for mid in semantic_memory_ids:
            m=self.records.memory.read(mid)
            if m['scope']!=head['scope'] or m['source_provenance']['source_kind']!='MODEL_DERIVATION':raise CoreError('RESEARCH_SEMANTIC_SOURCE_REQUIRED')
            claim=json.loads(m['text']).get('world_claim',{})
            if (claim.get('entity_id'),claim.get('predicate'))!=(entity,predicate):raise CoreError('RESEARCH_CORRELATION_DENIED')
            for parent in self.runtime.store.db.execute("SELECT parent_id FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY'",(mid,)):
                source=self.records.memory.read(parent[0]);body=json.loads(source['text'])
                if body.get('source_id') in self.intake.sources and source['authority']=='DIRECT' and source['source_provenance']['source_kind']=='DIRECT_OBSERVATION':independent.add(body.get('source_digest'))
        world=WorldModel(self.runtime.store,scopes=(head['scope'],),privacy_classes=self.runtime.config.privacy_classes).view(entity,predicate)
        state='CONTRADICTION' if world.state=='CONFLICT' else 'ENOUGH_FOR_BOUNDED_BELIEF' if world.state=='SUPPORTED_BELIEF' and len(independent)>=2 else 'INSUFFICIENT_EVIDENCE'
        key='research-result:'+digest([opportunity_id,sorted(semantic_memory_ids)])
        old=self.runtime.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=?",(key,)).fetchone()
        if old:return old[0]
        with self.runtime.store.transaction('life.research_compared',{'state':state}) as tx:
            return self.records.create(tx,kind='RUNTIME_WORK',scope=head['scope'],payload={'kind':'RESEARCH_RESULT','state':state,'cycle_id':b['cycle_id'],'belief_not_truth':True,'independent_source_count':len(independent),'not_learning':True},memories=semantic_memory_ids,records=(head['record_id'],*world.support_records),target_id=key)
