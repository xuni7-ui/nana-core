"""A transient chat receipt must not contaminate an independent owned observation."""
import json
import pytest
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal,InterestProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.concern_source import source_domains


@pytest.mark.parametrize('primary_receipt',[False,True])
def test_independent_interpretation_preserves_primary_retention_without_incidental_chat_receipts(app,primary_receipt):
    app.chat('PROJECT 请按现有来源说明当前状态',privacy='PROJECT',message_id='receipt-before-owned-source')
    r=app.runtime;s=r.store
    rows=MemoryService(s).query(scopes=r.config.scopes,privacy_classes=r.config.privacy_classes,limit=64)
    receipt=next(row['memory_id'] for row in rows if row['source_provenance']['domain']=='LOCAL_INTERACTION_METADATA')
    own=capture(r,'independent.owned-source',{'state':'SYNTHETIC_OWNED_INPUT_CANARY','opportunities':['a bounded independently observed development question']})
    primary=receipt if primary_receipt else own
    def propose(request):
        return StructuredProposal(interpretation='SYNTHETIC a sourced attention candidate, not a new fact',source_refs=(primary,),
            interests=(InterestProposal(topic='independent-note',motivation_source='CURIOSITY',source_memory_ids=(primary,),
                interpretation='SYNTHETIC consider the actual primary input',expected_value='HIGH',possible_behaviors=('EXPLORE','WATCH')),),
            uncertainty='RELEVANT',confidence=.4)
    with provider_harness(propose) as (transport,metrics):
        session=CognitionSession(r,transport,app.policy)
        cid=session.prepare('independent-owned-source','INTERPRET',(primary,),budget=CognitionBudget(timeout_ms=2000,cost_ceiling_micro=0))
        reply=session.execute(cid);assert reply['state']=='PROPOSED'
        request=session.records.read(s.one('cognitive_requests',cid)['record_id'])['payload']['request']
        service=ConcernService(r,resources=('synthetic://independent/note',));ids=service.offer(reply['record_id'])
        offered=service.opportunity(concern_ids=ids)
        if primary_receipt:
            assert offered is None
            assert 'LOCAL_INTERACTION_METADATA' in source_domains(s,s.one('open_concerns',ids[0])['record_id'])
            assert primary in request['source_context_refs']
        else:
            assert offered is not None
            assert 'LOCAL_INTERACTION_METADATA' not in source_domains(s,s.one('open_concerns',ids[0])['record_id'])
            assert 'SYNTHETIC_OWNED_INPUT_CANARY' in request['context_json']
            assert receipt not in request['source_context_refs']
            before=len(s.all('subject_cycles'));decision=r.subject.run(offered.input)
            assert not decision.replayed and len(s.all('subject_cycles'))==before+1
        assert metrics['calls']==1 and session.execute(cid)['replayed']
        assert not s.all('actions') and not s.all('goals')


def test_primary_conflicting_observations_remain_complete_and_source_bound(app):
    from nana_core.continuity.context import ContextAssembler,ContextRequest
    from nana_core.contracts import CoreError
    r=app.runtime
    first=capture(r,'interpret.color-first','SYNTHETIC the owned marker is red',predicate='independent.color')
    second=capture(r,'interpret.color-second','SYNTHETIC the owned marker is blue',predicate='independent.color')
    primary=capture(r,'interpret.current-source','SYNTHETIC consider the conflicting owned marker reports')
    request=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='world.interpret',task='Interpret the supplied owned observation',task_privacy_class='PROJECT')
    assembler=ContextAssembler(r.store,r.authority)
    context=assembler.assemble(request,app.policy,required_memory_ids=(primary,))
    conflicts=[b for b in context.blocks if b.kind=='UNRESOLVED_CONFLICT']
    assert conflicts and {first,second}<=set(conflicts[0].source_memory_ids)
    assert 'marker is red' in conflicts[0].data_json and 'marker is blue' in conflicts[0].data_json
    MemoryService(r.store,r.authority).forget(second,r.authority)
    with pytest.raises(CoreError,match='STALE_CONTEXT'):assembler.validate(context,request,app.policy)
