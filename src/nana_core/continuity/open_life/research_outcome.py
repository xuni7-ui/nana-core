"""Checked research-operation outcome, never verification of a world's truth."""
import json
from ...contracts import CoreError
from ...storage import digest
from ..records import RecordService
from ..world_loop.world import WorldModel
from ..learning import ExperienceService,ExperienceInput
from .sources import remember

def record_outcome(runtime,comparison_id,opportunity_id,query,semantic_ids):
    records=RecordService(runtime.store);head=records.read(comparison_id);b=head['payload']
    if b.get('kind')!='RESEARCH_RESULT' or not records.current_support(comparison_id):raise CoreError('RESEARCH_OUTCOME_SOURCE_REQUIRED')
    # Recompute current coverage from original raw bytes/semantic dependencies,
    # independently of the comparison's declared result. This checks study work,
    # explicitly NOT whether a model's interpretation is objectively true.
    raw_digests=set()
    for mid in semantic_ids:
        m=records.memory.read(mid);claim=json.loads(m['text'])['world_claim']
        if m['source_provenance']['source_kind']!='MODEL_DERIVATION' or (claim['entity_id'],claim['predicate'])!=(query['entity_id'],query['predicate']):raise CoreError('RESEARCH_OUTCOME_CORRELATION')
        for parent in runtime.store.db.execute("SELECT parent_id FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY'",(mid,)):
            raw=records.memory.read(parent[0]);body=json.loads(raw['text'])
            if raw['authority']=='DIRECT' and raw['source_provenance']['source_kind']=='DIRECT_OBSERVATION' and body.get('source_digest'):raw_digests.add(body['source_digest'])
    view=WorldModel(runtime.store,scopes=(head['scope'],),privacy_classes=runtime.config.privacy_classes).view(query['entity_id'],query['predicate'])
    expected='CONTRADICTION' if view.state=='CONFLICT' else 'ENOUGH_FOR_BOUNDED_BELIEF' if view.state=='SUPPORTED_BELIEF' and len(raw_digests)>=2 else 'INSUFFICIENT_EVIDENCE'
    actual={'state':b['state'],'independent_source_count':b['independent_source_count'],'comparison_completed':True,'world_truth_verified':False,'skill_learned':False}
    expected_data={**actual,'state':expected,'independent_source_count':len(raw_digests)}
    mid=remember(runtime,'research-operation:'+comparison_id,{'data':actual,'origin':'CHECKED_LOCAL_RESEARCH_OPERATION_NOT_WORLD_TRUTH'},scope=head['scope'],privacy=head['privacy_class'],kind='SYSTEM_VERIFICATION',parents=tuple(semantic_ids))
    old=runtime.store.db.execute('SELECT experience_id FROM experiences WHERE result_memory_id=?',(mid,)).fetchone()
    if old:return old[0]
    service=ExperienceService(runtime.store,runtime.authority);checked=service.verify_structured_result(mid,digest(expected_data),runtime.authority)
    return service.record(ExperienceInput(context_memory_ids=records.support(comparison_id)[:32],scope=head['scope'],task_class='research.comparison',decision='Check completed evidence comparison; insufficient/conflicting findings remain uncertainty, not failed research or truth',result_memory_id=mid,verification_memory_id=checked))
