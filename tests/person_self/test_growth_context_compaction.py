"""Equivalent verification bodies shrink only a current original growth SELF."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.context import ContextAssembler,ContextRequest,_verification_groups
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source
from .test_growth_inner_choice import grown
from .test_private_method_continuation import bind


def test_normal_growth_self_keeps_all_report_occurrences_dependencies_and_c_choice(tmp_path,monkeypatch):
    clock=VirtualClock();received=[];mids=[]
    def propose(request):
        data=json.loads(request.context_json);received.append(request)
        return StructuredProposal(interpretation='SYNTHETIC actual checked growth remains available',
            subject_cognition=CognitiveProposal(identity_id=data['manifest']['identity_id'],
                identity_revision=data['manifest']['identity_revision'],interpretation='SYNTHETIC I choose a private question',
                preferred_behavior='REFLECT',proposed_operations=('DRAFT',),
                private_question={'topic':'own-compact-growth','question':'SYNTHETIC Could this verified method help an own creative experiment?'}))
    with grown(tmp_path/'life',clock) as (r,view,origin,reuse,lesson),provider_harness(proposer=propose) as (transport,state):
        memory=MemoryService(r.store);review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        for i in range(32):
            mid=source(r,'repeat-report-'+str(i),{'strategy_episode':{'episode_key':'repeat-report-'+str(i),
                'lesson_id':lesson,'case':numeric_learning().practice[0].model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
            review.assess(lesson,mid,authority=r.authority);mids.append(mid)
        before={mid:dict(memory.read(mid)) for mid in mids}
        counts={t:len(r.store.all(t)) for t in ('actions','goals','grants')}
        assemble_current=ContextAssembler.assemble;checked=[]
        def inspect(assembler,request,policy,**kwargs):
            package=assemble_current(assembler,request,policy,**kwargs)
            grouped=[b for b in package.blocks if 'equivalent_verification_reports' in b.data_json]
            if grouped and not checked:
                counter=assembler.counter
                class ExpensiveGrouping:
                    descriptor='SYNTHETIC_GROUPING_COST_COUNTER_NOT_PROVIDER_TOKENIZER'
                    def count(self,text):
                        return counter.count(text)+(500000 if 'equivalent_verification_reports' in text else 0)
                try:
                    assembler.counter=ExpensiveGrouping()
                    literal=assemble_current(assembler,request,policy,**kwargs)
                    assembler.validate(literal,request,policy)
                    reports=[b for b in literal.blocks if b.kind=='MEMORY' and set(b.source_memory_ids)&set(mids)]
                    assert len(reports)==32 and all('equivalent_verification_reports' not in b.data_json for b in reports)
                finally:assembler.counter=counter
                tight=request.model_copy(update={'max_input_tokens':24000})
                reduced=assemble_current(assembler,tight,policy,**kwargs);assembler.validate(reduced,tight,policy)
                retained=[b for b in reduced.blocks if b.kind=='MEMORY' and set(b.source_memory_ids)&set(mids)]
                assert retained and all('equivalent_verification_reports' not in b.data_json for b in retained)
                assert any(':OTHER_REPORT_OCCURRENCES' in item for item in reduced.manifest.omitted_ids)
                assert reduced.manifest.input_tokens<=reduced.manifest.input_limit
                class CappedBatchCounter:
                    descriptor='SYNTHETIC_COUNTER_RANGE_NOT_PROVIDER_TOKENIZER'
                    def count(self,text):
                        if text.count('strategy_episode')>=32:raise CoreError('MODEL_TOKEN_COUNTER_RESULT_INVALID')
                        return counter.count(text)
                try:
                    assembler.counter=CappedBatchCounter()
                    bounded=assemble_current(assembler,tight,policy,**kwargs)
                    assembler.validate(bounded,tight,policy)
                    reports=[b for b in bounded.blocks if b.kind=='MEMORY' and set(b.source_memory_ids)&set(mids)]
                    assert reports and all('equivalent_verification_reports' not in b.data_json for b in reports)
                finally:assembler.counter=counter
                checked.append(True)
            return package
        monkeypatch.setattr(ContextAssembler,'assemble',inspect)
        session=bind(r,transport,context_policy());clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
        for _ in range(12):r.step()
        assert state['calls']==1 and len(received)==1 and checked==[True]
        package=json.loads(received[0].context_json)
        blocks=[b for b in package['blocks'] if b['kind']=='MEMORY' and set(b['source_memory_ids'])&set(mids)]
        assert len(blocks)==1  # The original produces 32 separate bodies.
        block=blocks[0];data=json.loads(block['data_json']);reports=data['equivalent_verification_reports']
        assert reports['count_in_retrieved_window']==32
        assert reports['additional_independent_contexts_established'] is False
        assert set(block['source_memory_ids'])==set(mids)
        assert set(block['source_evidence_ids'])=={m['source_evidence_id'] for m in before.values()}
        assert set(block['source_event_ids'])=={m['event_id'] for m in before.values()}
        for item in reports['reports']:
            original=before[item['memory_id']]
            reconstructed=json.loads(data['text'])
            reconstructed['strategy_episode']['episode_key']=item['episode_key']
            assert reconstructed==json.loads(original['text'])
            for field in ('event_time_us','observed_time_us','ingested_time_us'):
                assert item[field]==original[field]
            assert item['source_evidence_id']==original['source_evidence_id'] and item['source_event_id']==original['event_id']
        assert {mid:dict(memory.read(mid)) for mid in mids}==before
        assert counts=={t:len(r.store.all(t)) for t in counts}
        request_id=received[0].request_id;row=r.store.one('cognitive_requests',request_id)
        assert set(mids)<=set(RecordService(r.store).support(row['record_id']))
        print(json.dumps({'self_calls':state['calls'],'report_bodies':len(blocks),'reports_retained':32,
            'input_bytes':row['input_bytes'],'reserved_bytes':row['reserved_bytes'],'real_provider_calls':0}))
        # An ordinary read remains literal; this is not a global history rule.
        assembler=ContextAssembler(r.store,r.authority)
        req=ContextRequest(entity_id=r.config.entity_id,scopes=('world',),task_class='plain_context',
            task='Inspect permitted current context',task_privacy_class='PUBLIC',max_input_tokens=65536)
        ordinary=assembler.assemble(req,context_policy());assembler.validate(ordinary,req,context_policy())
        plain=[b for b in ordinary.blocks if b.kind=='MEMORY' and set(b.source_memory_ids)&set(mids)]
        assert len(plain)==32 and all('equivalent_verification_reports' not in b.data_json for b in plain)
        MemoryService(r.store,r.authority).forget(mids[0],r.authority)
        with pytest.raises(CoreError,match='STALE_CONTEXT'):assembler.validate(ordinary,req,context_policy())
        assert not RecordService(r.store).current_support(row['record_id'])
        fresh=assembler.assemble(req,context_policy());assembler.validate(fresh,req,context_policy())
        assert mids[0] not in {mid for b in fresh.blocks for mid in b.source_memory_ids}


def test_projection_equivalence_keeps_real_differences_and_pinned_sources_literal():
    from copy import deepcopy
    def row(key):
        return {'memory_id':key,'entity_id':'observer','scope':'world','privacy_class':'PUBLIC',
            'memory_type':'EPISODIC','epistemic_kind':'OBSERVATION','assessment':'CURRENT','confidence':.8,
            'authority':'DIRECT','importance':.4,'significance':.4,'predicate_key':None,
            'source_provenance':{'domain':'SYNTHETIC_ONLY','source_namespace':'synthetic.report',
                'source_kind':'SYSTEM_VERIFICATION','source_revision':1},
            'text':json.dumps({'strategy_episode':{'lesson_id':'synthetic-lesson','episode_key':key,
                'case':{'case_id':'synthetic-case','context':'test-only','data':[2,3],'expected':5}}})}
    first,second=row('one'),row('two')
    assert len(_verification_groups([first,second],()))==1
    assert len(_verification_groups([first,second],('two',)))==2
    for field,value in [('privacy_class','PERSONAL'),('confidence',.3),('scope','other-scope'),('memory_type','SEMANTIC')]:
        changed=deepcopy(second);changed[field]=value
        assert len(_verification_groups([first,changed],()))==2,field
    changed=deepcopy(second);changed['source_provenance']['source_kind']='USER_STATEMENT'
    assert len(_verification_groups([first,changed],()))==2
    for field,value in [('action_id','different-action'),('actual_result_digest','different-result')]:
        changed=deepcopy(second);body=json.loads(changed['text']);body['strategy_episode'][field]=value
        changed['text']=json.dumps(body)
        assert len(_verification_groups([first,changed],()))==2,field
    changed=deepcopy(second);body=json.loads(changed['text']);body['strategy_episode']['case']['expected']=6
    changed['text']=json.dumps(body)
    assert len(_verification_groups([first,changed],()))==2
    changed=deepcopy(second);changed['text']='not a typed report'
    assert len(_verification_groups([first,changed],()))==2
