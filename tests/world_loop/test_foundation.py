import json,time
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.continuity.world_loop.samples import media_samples
from nana_core.continuity.memory import MemoryService
from .helpers import *

def test_real_http_transport_correlation_stale_duplicate_and_erasure(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (port,state):
        mid=capture(r,'source',{'data':'public synthetic context'})
        session=CognitionSession(r,port,policy());cid=session.prepare('once','INTERPRET',(mid,));out=session.execute(cid)
        assert out['state']=='PROPOSED' and state['calls']==1
        assert session.execute(cid)['state']=='PROPOSED' and state['calls']==1
        assert session.accept(cid,session.proposal(out['record_id']))['replayed']
        late=session.prepare('late','GOALS',(mid,));r.clock.source.advance(4_000_000)
        assert session.execute(late)['state']=='STALE' and state['calls']==1
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError):session.proposal(out['record_id'])
        assert 'public synthetic context' not in canonical(session.journal())

@pytest.mark.parametrize('mode,expected',[('malformed','FAILED'),('partial','FAILED'),('refusal','FAILED'),('rate_limit','FAILED'),('context_overflow','FAILED')])
def test_provider_failure_is_not_empty_success(tmp_path,mode,expected):
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness(mode=mode) as (port,state):
        mid=capture(r,'source',{'data':'context'});s=CognitionSession(r,port,policy());cid=s.prepare('failure','INTERPRET',(mid,));assert s.execute(cid)['state']==expected
        assert s.execute(cid)['replayed'] and state['calls']==1

def test_provider_timeout_does_not_accept_late_completion(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness(delay=.2) as (port,state):
        mid=capture(r,'source',{'data':'context'});s=CognitionSession(r,port,policy());cid=s.prepare('timeout','INTERPRET',(mid,),budget=CognitionBudget(timeout_ms=50));assert s.execute(cid)['state']=='UNKNOWN'
        time.sleep(.22);assert s.execute(cid)['state']=='UNKNOWN' and state['calls']==1

def test_world_temporal_conflict_correction_and_no_resurrection(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        w=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',));start=r.clock.utc_now_us()
        a=capture(r,'a',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=True,kind='RAW_OBSERVATION',valid_from_us=start,confidence=.9).model_dump(mode='json')});ba=w.ingest(a)
        r.clock.source.advance(1_000_000);known=r.clock.utc_now_us()
        b=capture(r,'b',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=False,kind='RAW_OBSERVATION',valid_from_us=start,confidence=.9).model_dump(mode='json')});bb=w.ingest(b)
        assert w.view('device','available').state=='CONFLICT'
        assert w.view('device','available',known_at_us=start).state=='SUPPORTED_BELIEF'
        r.clock.source.advance(1_000_000)
        c=capture(r,'c',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=False,kind='RAW_OBSERVATION',valid_from_us=start,corrects=ba,confidence=.9).model_dump(mode='json')});bc=w.ingest(c)
        view=w.view('device','available');assert view.state=='SUPPORTED_BELIEF' and view.alternatives[0]['event_time_us']>start and view.alternatives[0]['valid_from_us']==start
        MemoryService(r.store,r.authority).forget(c,r.authority)
        assert w.view('device','available').state=='UNKNOWN'
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()

def test_actual_image_audio_video_decode_spans_and_source_erasure(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        p=PerceptionService(r.store,providers(),policy());reports={}
        for modality,data in media_samples().items():
            mid,rid=p.ingest(data,PublicMediaSource(source_id=modality.lower(),modality=modality,origin='SYNTHETIC',event_time_us=r.clock.utc_now_us(),observed_time_us=r.clock.utc_now_us()),entity_id='observer',scope='world')
            decoded=json.loads(MemoryService(r.store).read(mid)['text'])['decoded'];reports[modality]=decoded
            assert decoded['decoded'];MemoryService(r.store,r.authority).forget(mid,r.authority)
            with pytest.raises(CoreError):p.records.read(rid)
        assert len(reports['VIDEO']['frames'])>=3 and len(reports['VIDEO']['changes'])>=2
        assert reports['AUDIO']['samples']==16000 and reports['AUDIO']['transcript_status']=='NOT_RUN_NO_ASR'
        assert reports['VIDEO']['unobserved_between_samples']
        with pytest.raises(CoreError):p.decoder.decode(b'not a video','VIDEO')
