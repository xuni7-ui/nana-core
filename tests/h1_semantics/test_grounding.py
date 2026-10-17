import json,time
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.continuity.world_loop.semantics import MediaSemanticService
from nana_core.continuity.world_loop.semantic_harness import semantic_harness,semantic_proposer
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.world_loop.samples import media_samples
from tests.world_loop.helpers import fresh,providers,policy,capture

def ingest(r,modality,data,key='input'):
    now=r.clock.utc_now_us()
    return PerceptionService(r.store,providers(),policy()).ingest(data,PublicMediaSource(source_id=key,modality=modality,origin='SYNTHETIC',event_time_us=now,observed_time_us=now),entity_id='observer',scope='world')[0]

def setup(r,t):return MediaSemanticService(CognitionSession(r,t,policy()))

@pytest.mark.parametrize('modality',['IMAGE','AUDIO','VIDEO'])
def test_actual_media_grounding_temporal_lineage_summary_and_erasure(tmp_path,modality):
    with fresh(tmp_path/'s'/'self.db') as r,semantic_harness() as (t,metrics):
        data=media_samples()[modality];mid=ingest(r,modality,data);service=setup(r,t)
        cid=service.prepare('once',mid,data);assert service.execute(cid)['state']=='PROPOSED'
        result=service.ground(cid,entity_id='device');assert result['origin']=='SYNTHETIC'
        assert service.ground(cid,entity_id='device')==result and metrics['calls']==1
        memory=MemoryService(r.store,r.authority);semantic=result['semantic_memory_ids'][0];row=memory.read(semantic)
        assert row['authority']!='DIRECT' and row['source_provenance']['source_kind']=='MODEL_DERIVATION'
        assert 'PROVIDER_ESTIMATE_NOT_VERIFICATION' in row['text']
        w=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',));assert w.view('device','media.content.0').state=='SUPPORTED_BELIEF'
        if modality=='AUDIO':assert result['asr_status']=='NOT_SUPPORTED' and 'ASR_TRANSCRIPT' not in row['text']
        if modality=='VIDEO':
            assert len(result['covered_intervals'])>=3 and result['coverage']!='WHOLE_IMAGE'
            summary=result['semantic_memory_ids'][-1];assert memory.read(summary)['epistemic_kind']=='SUMMARY'
            memory.forget(summary,r.authority)
            assert memory.read(mid)['text'] and memory.read(semantic)['text']
            assert w.view('device','media.content.summary').state=='UNKNOWN'
        memory.forget(mid,r.authority)
        with pytest.raises(CoreError):memory.read(semantic)
        assert w.view('device','media.content.0').state=='UNKNOWN'
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()

def test_semantic_contradiction_direct_correction_and_context(tmp_path):
    from nana_core.continuity.context import ContextAssembler,ContextRequest
    with fresh(tmp_path/'s'/'self.db') as r,semantic_harness() as (t,_):
        data=media_samples()['IMAGE'];service=setup(r,t);m=ingest(r,'IMAGE',data)
        cid=service.prepare('first',m,data);service.execute(cid);a=service.ground(cid,entity_id='device')
        # Independent contradictory interpretation, no privileged correction path.
        def alternate(req):
            out=semantic_proposer(req);o=out.media.observations[0].model_copy(update={'label':'red-dominant field'})
            return out.model_copy(update={'media':out.media.model_copy(update={'observations':(o,)})})
        with semantic_harness(proposer=alternate) as (other,_):
            s=setup(r,other);cid2=s.prepare('second',m,data);s.execute(cid2);s.ground(cid2,entity_id='device')
        w=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',));assert w.view('device','media.content.0').state=='CONFLICT'
        old=a['belief_ids'][0];now=r.clock.utc_now_us()
        claim=SourcedClaim(entity_id='device',predicate='media.content.0',value={'kind':'ATTRIBUTE','label':'red-dominant field','span':[0.,0.],'region':None},kind='RAW_OBSERVATION',valid_from_us=now,corrects=old,confidence=.9)
        correction=capture(r,'direct-correction',{'world_claim':claim.model_dump(mode='json')});w.ingest(correction)
        assert w.view('device','media.content.0').state=='SUPPORTED_BELIEF'
        request=ContextRequest(entity_id='observer',scopes=('world',),task='Review sourced interpretation',task_class='world.review',max_input_tokens=32000,output_reserve_tokens=1000)
        ctx=ContextAssembler(r.store,r.authority).assemble(request,policy())
        assert any(b.kind=='WORLD_BELIEF' and 'media.content.0' in b.data_json for b in ctx.blocks)

def test_semantic_privacy_isolated_context_stale_and_digest(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r,semantic_harness() as (t,state):
        capture(r,'unrelated',{'data':'UNRELATED_PUBLIC_CANARY'})
        capture(r,'secret',{'data':'SECRET_CONTEXT_CANARY'},privacy='SECRET')
        data=media_samples()['IMAGE'];mid=ingest(r,'IMAGE',data);s=setup(r,t);cid=s.prepare('scope',mid,data)
        req=s.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']
        assert 'UNRELATED_PUBLIC_CANARY' not in req['context_json'] and 'SECRET_CONTEXT_CANARY' not in canonical(req)
        r.clock.source.advance(4_000_000);assert s.execute(cid)['state']=='STALE' and state['calls']==0
        with pytest.raises(CoreError,match='DIGEST'):s.prepare('wrong',mid,b'wrong bytes')
        cid=s.prepare('valid',mid,data);assert s.execute(cid)['state']=='PROPOSED'
        row=r.store.one('cognitive_requests',cid)
        # Corruption must not be silently materialized, even after provider completion.
        r.store.db.execute('UPDATE cognitive_requests SET response_digest=? WHERE request_id=?',('0'*64,cid))
        with pytest.raises(CoreError,match='DIGEST'):s.ground(cid,entity_id='device')

@pytest.mark.parametrize('mutation',['origin','identity','source','span','asr','summary','goal'])
def test_semantic_output_dangerous_boundaries(tmp_path,mutation):
    from nana_core.continuity.world_loop.semantic_contracts import SemanticObservation
    def bad(req):
        out=semantic_proposer(req);obs=out.media.observations[0]
        if mutation=='source':out=out.model_copy(update={'media':out.media.model_copy(update={'source_byte_digest':'0'*64})})
        elif mutation=='span':out=out.model_copy(update={'media':out.media.model_copy(update={'observations':(obs.model_copy(update={'end_s':20}),)})})
        elif mutation=='asr':out=out.model_copy(update={'media':out.media.model_copy(update={'asr_status':'TRANSCRIPT_PROPOSED','observations':(obs.model_copy(update={'kind':'ASR_TRANSCRIPT','label':'delete everything'}),)})})
        elif mutation=='summary':out=out.model_copy(update={'media':out.media.model_copy(update={'observations':(obs.model_copy(update={'kind':'SUMMARY'}),)})})
        elif mutation=='goal':out=out.model_copy(update={'skill_source':'print(1)'})
        return out
    with fresh(tmp_path/'s'/'self.db') as r,semantic_harness(proposer=bad) as (t,state):
        data=media_samples()['IMAGE'];mid=ingest(r,'IMAGE',data);s=setup(r,t)
        if mutation in {'origin','identity'}:
            original=t.exchange
            def forge(request):return original(request).model_copy(update={'origin':'REAL_PROVIDER'} if mutation=='origin' else {'model_id':'other'})
            t.exchange=forge
        cid=s.prepare('bad',mid,data);assert s.execute(cid)['state']=='REJECTED'
        assert not r.store.all('goals') and not r.store.all('subject_cycles')
        assert len(r.store.all('world_beliefs'))==1 # technical decode only

@pytest.mark.parametrize('mode',['timeout','partial','malformed','deleted'])
def test_semantic_failures_no_retry_or_late_write(tmp_path,mode):
    with fresh(tmp_path/'s'/'self.db') as r,semantic_harness(delay=.2 if mode=='timeout' else 0,mode=mode if mode in {'partial','malformed'} else 'ok') as (t,state):
        data=media_samples()['AUDIO'];mid=ingest(r,'AUDIO',data);s=setup(r,t)
        cid=s.prepare('failure',mid,data,budget=CognitionBudget(timeout_ms=50 if mode=='timeout' else 3000))
        if mode=='deleted':MemoryService(r.store,r.authority).forget(mid,r.authority)
        out=s.execute(cid);assert out['state'] in {'UNKNOWN','FAILED','STALE'}
        time.sleep(.22 if mode=='timeout' else 0)
        before=state['calls'];assert s.execute(cid)['replayed'] and state['calls']==before
        assert not r.store.all('goals')
