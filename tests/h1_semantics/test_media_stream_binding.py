"""Technical ingress and semantic wire must observe the same source samples."""
import base64,io,json,subprocess,wave
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.world_loop.semantic_harness import semantic_harness
from tests.world_loop.helpers import fresh
from tests.world_loop.test_media_stream_binding import multitrack
from .test_grounding import ingest,setup

@pytest.mark.parametrize('modality',['VIDEO','AUDIO'])
def test_actual_semantic_wire_uses_the_technically_observed_first_stream(tmp_path,multitrack,modality,monkeypatch):
    from nana_core.continuity.world_loop.perception import MediaDecoder
    run=MediaDecoder._run;calls=[]
    def observed_run(self,args,**kwargs):
        calls.append(tuple(args));return run(self,args,**kwargs)
    monkeypatch.setattr(MediaDecoder,'_run',observed_run)
    with fresh(tmp_path/'subject/self.db') as r,semantic_harness() as (t,state):
        mid=ingest(r,modality,multitrack);service=setup(r,t)
        decoded_calls=len(calls)
        request_id=service.prepare('first-stream',mid,multitrack)
        assert decoded_calls==(3 if modality=='VIDEO' else 2)
        assert len(calls)==decoded_calls+1
        assert ('-map','0:v:0' if modality=='VIDEO' else '0:a:0')==tuple(calls[-1][calls[-1].index('-map'):calls[-1].index('-map')+2])
        request=service.records.read(r.store.one('cognitive_requests',request_id)['record_id'])['payload']['request']
        assert request['role_input']['source_memory_id']==mid
        raw=base64.b64decode(request['role_input']['parts'][0]['data_b64'])
        if modality=='VIDEO':
            from PIL import Image,ImageStat
            mean=ImageStat.Stat(Image.open(io.BytesIO(raw)).convert('RGB')).mean
            assert mean[0]>240 and mean[2]<10
        else:
            with wave.open(io.BytesIO(raw),'rb') as w:
                assert w.getframerate()==16000 and w.getnchannels()==1
                assert not any(w.readframes(w.getnframes()))
        assert service.execute(request_id)['state']=='PROPOSED'
        result=service.ground(request_id,entity_id='device')
        assert result['origin']=='SYNTHETIC' and state['calls']==1
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError):service.ground(request_id,entity_id='device')
        assert not r.store.all('actions') and not r.store.all('goals')


def test_same_container_unequal_tracks_are_linked_without_claiming_temporal_alignment(tmp_path,multitrack):
    path=tmp_path/'unequal.mkv'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_complex_threads','1',
        '-f','lavfi','-i','color=c=red:s=32x24:r=4:d=2',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=1',
        '-map','0:v','-map','1:a','-t','2','-c:v','ffv1','-c:a','pcm_s16le',str(path)],check=True,timeout=20)
    data=path.read_bytes()
    with fresh(tmp_path/'subject/self.db') as r,semantic_harness() as (t,state):
        service=setup(r,t);ids=[];mids=[]
        for modality in ('VIDEO','AUDIO'):
            mid=ingest(r,modality,data,key=modality.lower());mids.append(mid)
            cid=service.prepare(modality,mid,data);assert service.execute(cid)['state']=='PROPOSED'
            service.ground(cid,entity_id='device',predicate='media.'+modality.lower());ids.append(cid)
        linked=service.associate_audio(*ids)
        assert linked['video_duration_s']==2 and linked['audio_duration_s']==1
        assert linked['temporal_alignment']=='NOT_ESTABLISHED'
        assert linked['linkage_not_identity_or_command']
        before=(len(r.store.all('continuity_records')),state['calls'])
        assert service.associate_audio(*ids)==linked
        assert (len(r.store.all('continuity_records')),state['calls'])==before
        with pytest.raises(CoreError,match='MEDIA_AUDIO_ASSOCIATION_MISMATCH'):service.associate_audio(*ids[::-1])
        # Same duration is insufficient: a different encoded container stays distinct.
        other=ingest(r,'AUDIO',multitrack,key='other');foreign=service.prepare('other',other,multitrack)
        assert service.execute(foreign)['state']=='PROPOSED';service.ground(foreign,entity_id='device',predicate='media.other')
        with pytest.raises(CoreError,match='MEDIA_AUDIO_ASSOCIATION_MISMATCH'):service.associate_audio(ids[0],foreign)
        header=r.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id LIKE 'semantic-audio:%'").fetchone()[0]
        assert RecordService(r.store).current_support(header)
        MemoryService(r.store,r.authority).forget(mids[1],r.authority)
        assert not RecordService(r.store).current_support(header)
        with pytest.raises(CoreError):service.associate_audio(*ids)
        assert MemoryService(r.store).read(mids[0])
        assert not r.store.all('actions') and not r.store.all('goals') and not r.store.all('grants')
