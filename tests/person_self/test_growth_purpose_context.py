"""Optional old proofs can be referenced without replaying their full bodies."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import digest
from nana_core.continuity.context import ContextAssembler,ContextRequest
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.subject import growth_life
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source
from .test_growth_inner_choice import grown
from .test_private_method_continuation import bind


def test_normal_self_keeps_current_and_explicit_proofs_full_while_other_proof_refs_remain_revocable(tmp_path,monkeypatch):
    clock=VirtualClock();received=[];index_ids=[];checked=[]
    def propose(request):
        received.append(request);package=json.loads(request.context_json);identity=package['manifest']
        return StructuredProposal(interpretation='SYNTHETIC checked skill can inform own choice',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],
            interpretation='SYNTHETIC own experiment question',preferred_behavior='REFLECT',proposed_operations=('DRAFT',),
            private_question={'topic':'own-indexed-growth','question':'SYNTHETIC Could this checked method inform an own experiment?'}))
    with grown(tmp_path/'life',clock) as (r,view,origin,reuse,lesson),provider_harness(proposer=propose) as (transport,state):
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',));memory=MemoryService(r.store);mids=[]
        for i in range(32):
            clock.advance(SECOND);r.lease.heartbeat()
            episode={'episode_key':'purpose-case-'+str(i),'lesson_id':lesson,
                'case':LearningCase(case_id='purpose-case-'+str(i),context='different-check-'+str(i),data=[100+i,.25],expected=100.25+i).model_dump(mode='json')}
            mid=source(r,'purpose-case-'+str(i),{'strategy_episode':episode},kind='SYSTEM_VERIFICATION');review.assess(lesson,mid,authority=r.authority);mids.append(mid)
        extra=source(r,'proof-with-extra-context',{'strategy_episode':episode,
            'important_context':'SYNTHETIC_EXTRA_OBSERVATION_KEEP_FULL'},kind='SYSTEM_VERIFICATION')
        before={mid:dict(memory.read(mid)) for mid in mids};assemble=ContextAssembler.assemble
        def inspect(assembler,request,policy,**kwargs):
            package=assemble(assembler,request,policy,**kwargs)
            if kwargs.get('subject_frame') is not None and not checked:
                refs=[b for b in package.blocks if b.kind=='MEMORY_REFERENCE_INDEX']
                assert refs  # Original replays every different proof body.
                assert extra in {mid for b in package.blocks if b.kind=='MEMORY' for mid in b.source_memory_ids}
                assert extra not in {mid for b in refs for mid in b.source_memory_ids}
                selected=set(kwargs['subject_frame'].source_memory_ids)
                current=next(b for b in package.blocks if b.kind=='GROWTH_CHANGE')
                assert set(current.source_memory_ids)<=selected
                for block in refs:
                    data=json.loads(block.data_json)
                    assert data['report_bodies_included'] is False and data['establishes_independent_growth'] is False
                    assert not set(block.source_memory_ids)&selected
                    assert set(block.source_memory_ids)=={item['memory_id'] for item in data['reports']}
                    for item in data['reports']:
                        original=memory.read(item['memory_id'])
                        assert item['body_digest']==digest(original['text'])
                        assert item['source_evidence_id']==original['source_evidence_id'] and item['source_event_id']==original['event_id']
                        for field in ('event_time_us','observed_time_us','ingested_time_us'):assert item[field]==original[field]
                    index_ids.extend(block.source_memory_ids)
                protected=selected&set(mids)
                assert protected and protected<={mid for b in package.blocks if b.kind=='MEMORY' for mid in b.source_memory_ids}
                pinned=index_ids[0]
                options={**kwargs,'required_memory_ids':tuple(dict.fromkeys((*kwargs.get('required_memory_ids',()),pinned)))}
                explicit=assemble(assembler,request,policy,**options);assembler.validate(explicit,request,policy)
                assert pinned in {mid for b in explicit.blocks if b.kind=='MEMORY' for mid in b.source_memory_ids}
                assert pinned not in {mid for b in explicit.blocks if b.kind=='MEMORY_REFERENCE_INDEX' for mid in b.source_memory_ids}
                query=request.model_copy(update={'query_terms':('different-check-',)})
                queried=assemble(assembler,query,policy,**kwargs);assembler.validate(queried,query,policy)
                assert not any(b.kind=='MEMORY_REFERENCE_INDEX' for b in queried.blocks)
                counter=assembler.counter
                class ExpensiveReferences:
                    descriptor='SYNTHETIC_REFERENCE_COST_NOT_PROVIDER_TOKENIZER'
                    def count(self,text):return counter.count(text)+(500000 if 'MEMORY_REFERENCE_INDEX' in text else 0)
                try:
                    assembler.counter=ExpensiveReferences();literal=assemble(assembler,request,policy,**kwargs);assembler.validate(literal,request,policy)
                    assert not any(b.kind=='MEMORY_REFERENCE_INDEX' for b in literal.blocks)
                finally:assembler.counter=counter
                checked.append(True)
            return package
        monkeypatch.setattr(ContextAssembler,'assemble',inspect);bind(r,transport,context_policy())
        counts={t:len(r.store.all(t)) for t in ('actions','goals','grants')};clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
        for _ in range(12):r.step()
        assert state['calls']==1 and checked==[True] and len(received)==1
        assert counts=={t:len(r.store.all(t)) for t in counts}
        assert {mid:dict(memory.read(mid)) for mid in mids}==before
        records=RecordService(r.store);request=r.store.one('cognitive_requests',received[0].request_id)
        assert set(index_ids)<=set(records.support(request['record_id'])) and records.current_support(request['record_id'])
        # Ordinary context retains raw text; a source can still be explicitly recalled.
        req=ContextRequest(entity_id=r.config.entity_id,scopes=('world',),task_class='ordinary_proof_recall',task='Inspect prior proof sources',task_privacy_class='PUBLIC',max_input_tokens=65536)
        assembler=ContextAssembler(r.store,r.authority);plain=assembler.assemble(req,context_policy())
        assert not any(b.kind=='MEMORY_REFERENCE_INDEX' for b in plain.blocks)
        victim=mids[15];assert victim in index_ids
        context_canary=json.loads(before[victim]['text'])['strategy_episode']['case']['context'].encode()
        files=[r.store.path,r.store.path.with_name(r.store.path.name+'-wal')]
        assert any(context_canary in path.read_bytes() for path in files if path.exists())
        MemoryService(r.store,r.authority).forget(victim,r.authority)
        assert not records.current_support(request['record_id'])
        assert all(context_canary not in path.read_bytes() for path in files if path.exists())
        assert r.store.one('lessons',lesson)['state']=='ACTIVE'
        with pytest.raises(CoreError,match='STALE_CONTEXT'):assembler.validate(plain,req,context_policy())
        print(json.dumps({'self_calls':state['calls'],'indexed_occurrences':len(set(index_ids)),
            'current_proofs_literal':True,'explicit_recall_literal':True,'raw_store_unchanged_before_withdrawal':True,
            'input_bytes':request['input_bytes'],'real_provider_calls':0}))
