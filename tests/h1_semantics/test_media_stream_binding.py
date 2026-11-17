"""Technical ingress and semantic wire must observe the same source samples."""
import base64,io,json,subprocess,wave
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.world_loop.semantic_harness import semantic_harness
from tests.world_loop.helpers import fresh
from tests.world_loop.test_media_stream_binding import multitrack,transport_video
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


def test_last_video_frame_does_not_claim_the_unobserved_audio_tail(tmp_path):
    path=tmp_path/'short-video-long-audio.mkv'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_complex_threads','1',
        '-f','lavfi','-i','color=c=red:s=32x24:r=4:d=1',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=3',
        '-map','0:v','-map','1:a','-t','3','-c:v','ffv1','-c:a','pcm_s16le',str(path)],check=True,timeout=20)
    data=path.read_bytes()
    with fresh(tmp_path/'subject/self.db') as r,semantic_harness() as (t,state):
        mid=ingest(r,'VIDEO',data);service=setup(r,t)
        request_id=service.prepare('video-tail',mid,data)
        assert service.execute(request_id)['state']=='PROPOSED'
        result=service.ground(request_id,entity_id='device')
        # A three-second container does not establish that its last video frame
        # spans the remaining audio. Preserve that unobserved interval in H1.
        assert [1.,3.] in result['unobserved_gaps']
        decoded=json.loads(MemoryService(r.store).read(mid)['text'])['decoded']
        assert decoded['duration_s']==3
        assert decoded['frames'][-1]['source_interval_s']==[.75,1.]
        assert result['covered_intervals'][-1]==[.75,1.]
        assert result['coverage']=='EXPLICIT_SEGMENTS' and state['calls']==1
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError):service.ground(request_id,entity_id='device')
        assert not r.store.all('actions') and not r.store.all('goals')


@pytest.mark.parametrize('duration_value,legacy,end',[(None,False,.75),('N/A',False,.75),('N/A',True,1.)])
def test_final_packet_duration_uses_available_metadata_or_a_point(tmp_path,multitrack,monkeypatch,duration_value,legacy,end):
    from nana_core.continuity.world_loop.perception import MediaDecoder
    run=MediaDecoder._run
    def unknown_duration(self,args,**kwargs):
        raw=run(self,args,**kwargs)
        if args[0]=='ffprobe' and '-show_frames' in args:
            metadata=json.loads(raw);last=metadata['frames'][-1]
            known=last.get('duration_time',last.get('pkt_duration_time'))
            last.pop('duration_time',None);last.pop('pkt_duration_time',None)
            if legacy:last['pkt_duration_time']=known
            if duration_value is not None:last['duration_time']=duration_value
            return json.dumps(metadata).encode()
        return raw
    # Controlled metadata availability ablation over actual encoded bytes;
    # no simulated pixels, fake Provider success or unsandboxed decoder.
    monkeypatch.setattr(MediaDecoder,'_run',unknown_duration)
    with fresh(tmp_path/'subject/self.db') as r,semantic_harness() as (t,state):
        mid=ingest(r,'VIDEO',multitrack);service=setup(r,t)
        cid=service.prepare('unknown-final-duration',mid,multitrack)
        assert service.execute(cid)['state']=='PROPOSED'
        result=service.ground(cid,entity_id='device')
        assert result['covered_intervals'][-1]==[.75,end]
        assert result['unobserved_gaps']==([] if legacy else [[.75,1.]])
        assert state['calls']==1 and not r.store.all('actions') and not r.store.all('goals')


def test_normalized_transport_timeline_reaches_original_semantic_parts_and_withdrawal(tmp_path,transport_video):
    with fresh(tmp_path/'subject/self.db') as r,semantic_harness() as (t,state):
        mid=ingest(r,'VIDEO',transport_video);service=setup(r,t)
        cid=service.prepare('transport-time',mid,transport_video)
        request=service.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']
        parts=request['role_input']['parts']
        assert parts[0]['start_s']==0 and parts[-1]['end_s']==1.
        assert service.execute(cid)['state']=='PROPOSED'
        result=service.ground(cid,entity_id='device')
        assert result['covered_intervals'][0]==[0.,.04] and result['covered_intervals'][-1]==[.96,1.]
        assert result['unobserved_gaps'] and result['coverage']=='EXPLICIT_SEGMENTS'
        assert state['calls']==1
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError):service.ground(cid,entity_id='device')
        assert not r.store.all('actions') and not r.store.all('goals')


def test_container_origin_preserves_a_real_leading_video_gap(tmp_path):
    path=tmp_path/'delayed-video.ts'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_complex_threads','1',
        '-itsoffset','0.5','-f','lavfi','-i','color=c=red:s=32x24:r=25:d=1',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=1.5',
        '-map','0:v','-map','1:a','-c:v','mpeg2video','-c:a','mp2','-b:a','32k','-threads','1',
        '-f','mpegts',str(path)],check=True,timeout=20)
    data=path.read_bytes()
    with fresh(tmp_path/'subject/self.db') as r,semantic_harness() as (t,state):
        mid=ingest(r,'VIDEO',data);service=setup(r,t)
        decoded=json.loads(MemoryService(r.store).read(mid)['text'])['decoded'];first=decoded['frames'][0]['sample_s']
        assert first>.4
        cid=service.prepare('leading-video-gap',mid,data);assert service.execute(cid)['state']=='PROPOSED'
        result=service.ground(cid,entity_id='device')
        assert result['unobserved_gaps'][0]==pytest.approx([0.,first])
        assert result['covered_intervals'][0][0]==first and state['calls']==1
        assert not r.store.all('actions') and not r.store.all('goals')
