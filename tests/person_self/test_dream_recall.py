"""Original maintenance/C/source dependencies, not a real dream or human review."""
import json
import pytest
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import SubjectInput
from nana_core.life.application import LifeApplication
from tests.independent_life.test_dialogue import relay


def source(app,key,text,*,privacy='PROJECT',domain='SYNTHETIC_ONLY',namespace='synthetic.dream',**values):
    memory=MemoryService(app.runtime.store)
    eid=memory.capture(EvidenceInput(provenance=Provenance(domain=domain,source_namespace=namespace,
        source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,privacy_class=privacy,
        event_time_us=11,observed_time_us=app.clock.utc_now_us()))
    return memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,
        epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,**values))


def consolidate(app,needed):
    maintenance=app.runtime.work.maintenance;maintenance.interval=1_000_000
    maintenance.discover();found=[]
    for _ in range(32):
        app.clock.advance(1_000_000);app.runtime.lease.heartbeat()
        result=maintenance.slice()
        if not result or not result.get('candidate_record_id'):continue
        rid=result['candidate_record_id'];head,body=maintenance.candidate(rid)
        cycle=app.runtime.subject.run(SubjectInput(kind='WAKE',origin='SELF_WAKE',source_key='synthetic.dream-review.'+rid,
            entity_id='project-user',scope='project-work',observed_at_us=head['created_at_us'],
            source_memory_ids=tuple(body['memory_ids']),memory_review_id=rid))
        mid=maintenance.adopt(rid,cycle)
        if mid:found.append(mid)
        if needed in body['memory_ids']:
            assert cycle.judgment.stance=='REMEMBER' and mid
            return rid,mid,body,found
    pytest.fail('original bounded maintenance did not reach expected source')


def test_consolidated_original_sources_reach_render_after_restart_and_withdraw(app):
    long='SYNTHETIC observed line. '*32+'LANTERN_MEETING Friday afternoon at north gate.'
    mid=source(app,'source',long,importance=.9,significance=.8)
    from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
    assembler=ContextAssembler(app.runtime.store,app.runtime.authority)
    request=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='world.social',
        task='SYNTHETIC query LANTERN_MEETING',task_privacy_class='PROJECT',query_terms=('LANTERN_MEETING',),max_input_tokens=8192)
    policy=ContextPolicy(policy_id='synthetic-dream-probe',allowed_scopes=('project-work',),readable_privacy=('PROJECT',))
    before=assembler.assemble(request,policy,pinned_only=True,conversation_topic='daily')
    assert not any('Friday afternoon' in b.data_json for b in before.blocks)
    rid,summary,body,_=consolidate(app,mid)
    after=assembler.assemble(request,policy,pinned_only=True,conversation_topic='daily')
    assert any(b.kind=='CONSOLIDATED_RECALL' and 'Friday afternoon' in b.data_json for b in after.blocks)
    store=app.runtime.store
    assert body['method']=='SOURCE_EXCERPTS_V1' and body['model_calls']==0
    memory=MemoryService(store).read(summary)
    assert memory['authority']=='INFERRED' and memory['epistemic_kind']=='SUMMARY'
    fragment=next(f for f in body['fragments'] if f['memory_id']==mid)
    assert fragment['excerpt']==long[fragment['start']:fragment['end']]
    assert fragment['event_time_us']==11 and fragment['observed_time_us']!=11
    assert not store.all('cognitive_requests')
    home=app.home;clock=app.clock;identity=app.runtime.identity_id;app.close();clock.advance(72*3_600_000_000)
    with relay(home,'CHAT',recall_query_terms=('LANTERN_MEETING',)) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause()
            recalls=current.runtime.work.maintenance.recall(('LANTERN_MEETING',))
            assert recalls and recalls[0]['fragments'][0]['start']>0
            assert 'Friday afternoon' in str(recalls)
            answer=current.chat('When was LANTERN_MEETING?',message_id='dream-recall',topic='daily')
            assert answer['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
            context=json.loads(requests[-1]['context_json'])
            blocks=[b for b in context['blocks'] if b['kind']=='CONSOLIDATED_RECALL']
            assert blocks and 'Friday afternoon' in str(blocks)
            assert summary in blocks[0]['source_memory_ids'] and mid in blocks[0]['source_memory_ids']
            assert current.runtime.identity_id==identity
            current.forget(mid)
            assert not current.runtime.work.maintenance.recall(('LANTERN_MEETING',))
            assert current.runtime.store.one('memories',summary)['lifecycle']=='DELETED'
            current.chat('When was LANTERN_MEETING?',message_id='dream-withdrawn',topic='daily')
            assert len(requests)==4 and 'Friday afternoon' not in requests[-1]['context_json']


def test_consolidation_excludes_transient_receipts_and_separates_privacy(app):
    high=source(app,'high','SYNTHETIC important public memory',privacy='PROJECT',importance=.9)
    low=source(app,'low','SYNTHETIC less important memory',privacy='PROJECT',importance=.1)
    secret=source(app,'private','SYNTHETIC private fixture not real private data',privacy='PERSONAL',importance=.4)
    from nana_core.continuity.contracts import PENDING_LOCAL_RECEIPT
    receipt=source(app,'receipt',PENDING_LOCAL_RECEIPT,domain='LOCAL_INTERACTION_METADATA',namespace='recorded.local.message')
    rows=[app.runtime.store.one('memories',mid) for mid in (receipt,secret,low,high)]
    selected=app.runtime.work.maintenance._select(rows,'project-work')
    assert [m['memory_id'] for m in selected]==[high,secret,low]
    maintenance=app.runtime.work.maintenance
    public=maintenance._offer(tuple(m for m in selected if m['privacy_class']=='PROJECT'),'project-work','INCREMENTAL')
    private=maintenance._offer(tuple(m for m in selected if m['privacy_class']=='PERSONAL'),'project-work','INCREMENTAL')
    public_head,public_body=maintenance.candidate(public)
    private_head,private_body=maintenance.candidate(private)
    assert public_head['privacy_class']=='PROJECT' and private_head['privacy_class']=='PERSONAL'
    assert secret not in public_body['memory_ids'] and receipt not in str(public_body)+str(private_body)
    assert MemoryService(app.runtime.store).read(secret)['text'].startswith('SYNTHETIC private')


def test_corrected_source_invalidates_old_dream_until_original_c_reviews_new_evidence(app):
    old=source(app,'claim-first','SYNTHETIC MEETING_SLOT Friday',predicate_key='meeting.slot')
    _,summary,_,_=consolidate(app,old)
    assert app.runtime.work.maintenance.recall(('MEETING_SLOT',))
    current=source(app,'claim-corrected','SYNTHETIC MEETING_SLOT Saturday',predicate_key='meeting.slot',correction_of=old)
    assert not app.runtime.work.maintenance.recall(('MEETING_SLOT',))
    assert app.runtime.store.one('memories',summary)['assessment'] not in {'CURRENT','UNASSESSED'}
    _,new_summary,_,_=consolidate(app,current)
    result=app.runtime.work.maintenance.recall(('MEETING_SLOT',))
    assert result and result[0]['summary_memory_id']==new_summary
    assert 'Saturday' in str(result) and 'Friday' not in str(result)
