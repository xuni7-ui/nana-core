"""The decoded samples must belong to the stream whose metadata we report."""
import json
import subprocess
import pytest
from nana_core.continuity.world_loop.perception import MediaDecoder,PerceptionService,PublicMediaSource
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.presence.authority import VirtualClock
from tests.world_loop.helpers import fresh,providers,policy
from tools.nana_vision_first.demo import cue


@pytest.fixture(scope='module')
def multitrack(tmp_path_factory):
    root=tmp_path_factory.mktemp('native-media-tracks');path=root/'fixture.mkv'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_complex_threads','1',
        '-f','lavfi','-i','color=c=red:s=32x24:r=4:d=1',
        '-f','lavfi','-i','color=c=blue:s=64x48:r=8:d=1',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono',
        '-f','lavfi','-i','sine=frequency=1000:sample_rate=48000:duration=1',
        '-map','0:v','-map','1:v','-map','2:a','-map','3:a','-t','1',
        '-c:v','ffv1','-c:a','pcm_s16le','-ac:a:1','2',
        '-disposition:v:0','0','-disposition:v:1','default',
        '-disposition:a:0','0','-disposition:a:1','default',str(path)],check=True,timeout=20)
    return path.read_bytes()


@pytest.mark.parametrize('modality',['VIDEO','AUDIO'])
def test_bounded_decoder_binds_samples_to_the_same_first_stream_as_its_metadata(multitrack,modality):
    decoded=MediaDecoder().decode(multitrack,modality)
    if modality=='VIDEO':
        assert (decoded['width'],decoded['height'],decoded['source_frame_count'])==(32,24,4)
        assert [f['sample_s'] for f in decoded['frames']]==[0,.25,.5,.75]
        assert all(f['mean_rgb'][0]>200 and f['mean_rgb'][2]<20 for f in decoded['frames'])
        assert decoded['semantic_interpretation']=='UNKNOWN'
    else:
        assert (decoded['source_sample_rate'],decoded['source_channels'])==(16000,1)
        assert decoded['samples']==16000
        assert all(item['rms']==0 and item['activity']=='LOW_ENERGY' for item in decoded['segments'])
        assert decoded['transcript'] is None and decoded['speech']=='UNKNOWN'


@pytest.mark.parametrize('encoding',['multitrack','transport'])
def test_source_technical_perception_reaches_the_same_c_private_question_without_semantic_claim(multitrack,transport_video,tmp_path,encoding):
    multitrack=multitrack if encoding=='multitrack' else transport_video
    clock=VirtualClock()
    with fresh(tmp_path/'subject/self.db',clock) as r:
        source=PublicMediaSource(source_id='synthetic-multitrack',modality='VIDEO',origin='SYNTHETIC',event_time_us=clock.utc_now_us(),observed_time_us=clock.utc_now_us())
        mid,observation=PerceptionService(r.store,providers(),policy()).ingest(multitrack,source,entity_id='observer',scope='world')
        m=cue(r,'technical-pixels',ConcernCue(cue_kind='DISCOVERY',motivation_source='CREATIVE_INTEREST',topic_key='own-pixel-question',possible_behaviors=('REFLECT','WATCH')),parents=(mid,))
        class ConsiderPixels:
            descriptor='SYNTHETIC_TECHNICAL_STATS_NOT_SEMANTIC_VIDEO_MODEL'
            def propose(self,request):
                values=[json.loads(json.loads(b['data_json'])['text']) for b in json.loads(request.context_json)['blocks'] if b['kind']=='MEMORY']
                decoded=next(v['decoded'] for v in values if 'decoded' in v and v['decoded']['modality']=='VIDEO')
                red=decoded['frames'][0]['mean_rgb'][0]>decoded['frames'][0]['mean_rgb'][2]
                choice=json.loads(AnalyticalFixturePort().propose(request));choice.update(preferred_behavior='REFLECT',proposed_operations=['DRAFT'],
                    private_question={'topic':'own-pixel-question','question':'SYNTHETIC Why are the sampled first-track pixels '+('red' if red else 'blue')+'?'})
                return json.dumps(choice)
        event=SubjectInput(source_key='synthetic.multitrack-consideration',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',privacy_class='PUBLIC',observed_at_us=clock.utc_now_us(),source_memory_ids=(m,))
        result=r.subject.cognize(event,model=ConsiderPixels(),authority=r.authority,policy=policy())
        own=[(rid,v) for rid,v in candidates(r.store,'world',('PUBLIC',)) if v.category=='PRIVATE_QUESTION']
        assert len(own)==1 and 'pixels red?' in own[0][1].content_summary
        assert m in RecordService(r.store).support(own[0][0])
        assert r.store.db.execute("SELECT 1 FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY' AND parent_id=?",(m,mid)).fetchone()
        assert RecordService(r.store).current_support(own[0][0])
        body=json.loads(MemoryService(r.store).read(mid)['text']);assert body['decoded']['semantic_interpretation']=='UNKNOWN'
        assert not r.store.all('actions') and not r.store.all('goals') and not r.store.all('grants')
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        assert not RecordService(r.store).current_support(observation) and not RecordService(r.store).current_support(own[0][0])


def test_audio_source_memory_uses_decoded_audio_length_not_another_tracks_duration(tmp_path):
    from nana_core.continuity.world_loop.world import WorldModel
    path=tmp_path/'short-audio-long-video.mkv'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_complex_threads','1',
        '-f','lavfi','-i','color=c=red:s=32x24:r=4:d=2',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=1',
        '-map','0:v','-map','1:a','-t','2','-c:v','ffv1','-c:a','pcm_s16le',str(path)],check=True,timeout=20)
    clock=VirtualClock()
    with fresh(tmp_path/'subject/self.db',clock) as r:
        source=PublicMediaSource(source_id='synthetic-short-audio',modality='AUDIO',origin='SYNTHETIC',event_time_us=clock.utc_now_us(),observed_time_us=clock.utc_now_us())
        mid,observation=PerceptionService(r.store,providers(),policy()).ingest(path.read_bytes(),source,entity_id='observer',scope='world')
        data=json.loads(MemoryService(r.store).read(mid)['text'])['decoded']
        assert data['samples']==16000 and data['segments'][-1]['end_s']==1
        view=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',)).view('media.synthetic-short-audio','media.technical')
        assert view.alternatives[0]['value']['technical']['segments']==2
        assert data['duration_s']==data['samples']/data['sample_rate']==1
        assert data['transcript'] is None and data['speech']=='UNKNOWN'


@pytest.fixture(scope='module')
def transport_video(tmp_path_factory):
    root=tmp_path_factory.mktemp('native-transport-time');path=root/'fixture.ts'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-f','lavfi','-i',
        'color=c=red:s=32x24:r=25:d=1','-c:v','mpeg2video','-threads','1','-f','mpegts',str(path)],
        check=True,timeout=20)
    return path.read_bytes()


def test_transport_timestamps_are_relative_to_container_origin_not_absolute_pts(transport_video):
    decoded=MediaDecoder().decode(transport_video,'VIDEO')
    assert decoded['duration_s']==1 and decoded['source_frame_count']==25
    assert decoded['frames'][0]['sample_s']==0
    assert decoded['frames'][-1]['source_interval_s']==pytest.approx([.96,1.])
    for frame in decoded['frames']:
        assert frame['sample_s']==pytest.approx(frame['source_pts_ticks']/90000-frame['timeline_origin_s'])
        assert frame['source_time_base']=='1/90000'
        assert frame['timeline_origin_s']>1
    assert decoded['semantic_interpretation']=='UNKNOWN' and decoded['unobserved_between_samples']


def test_quantized_container_origin_uses_the_matching_exact_stream_tick(tmp_path):
    path=tmp_path/'fractional-origin.ts'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-f','lavfi','-i',
        'color=c=red:s=32x24:r=24:d=1','-c:v','mpeg2video','-threads','1','-f','mpegts',str(path)],
        check=True,timeout=20)
    decoded=MediaDecoder().decode(path.read_bytes(),'VIDEO');first=decoded['frames'][0]
    assert decoded['source_frame_count']==24 and first['sample_s']==0
    assert first['timeline_origin_s']==first['source_pts_ticks']/90000
    assert first['timeline_origin_s']!=round(first['timeline_origin_s'],6)
    assert decoded['frames'][-1]['source_interval_s'][-1]==1.


def _write_irregular_video(path,dense_first):
    dense='lt(n,60)' if dense_first else 'gte(n,60)'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_threads','1','-f','lavfi','-i',
        'testsrc=size=32x24:rate=10:duration=12','-vf',f"select='{dense}+not(mod(n,10))'",'-fps_mode','vfr',
        '-c:v','ffv1','-threads','1',str(path)],check=True,timeout=20)


@pytest.mark.parametrize('dense_first',[True,False])
def test_video_skeleton_spans_wall_time_under_uneven_frame_density(tmp_path,dense_first):
    import hashlib
    import time

    path=tmp_path/'synthetic-irregular.mkv'
    _write_irregular_video(path,dense_first)
    class MeasuredDecoder(MediaDecoder):
        native_processes=0
        def _run(self,*args,**kwargs):
            self.native_processes+=1
            return super()._run(*args,**kwargs)
    data=path.read_bytes();decoder=MeasuredDecoder();start=time.perf_counter()
    observed=decoder.decode(data,'VIDEO');wall=time.perf_counter()-start
    times=[f['sample_s'] for f in observed['frames']]
    maximum=max(right-left for left,right in zip(times,times[1:]))
    print(json.dumps({'dense_first':dense_first,'sample_times':times,'largest_internal_sampling_gap_s':maximum,
        'frame_count':observed['source_frame_count'],'selected_frames':len(times),'source_bytes':len(data),
        'source_sha256':hashlib.sha256(data).hexdigest(),'native_processes':decoder.native_processes,'wall_s':wall}))
    assert observed['source_frame_count']==66 and len(times)==8
    assert times[0]==0 and times[-1]==pytest.approx(11.9 if not dense_first else 11.)
    assert maximum<=2.1
    assert decoder.native_processes==3
    assert observed['unobserved_between_samples'] and observed['semantic_interpretation']=='UNKNOWN'


def test_video_packet_gap_cannot_ground_a_semantic_observation(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.world_loop.semantic_harness import semantic_harness,semantic_proposer
    from nana_core.continuity.world_loop.semantics import MediaSemanticService

    path=tmp_path/'synthetic-irregular.mkv'
    _write_irregular_video(path,True)
    data=path.read_bytes()
    inspected=[]

    def propose(request):
        out=semantic_proposer(request)
        parts=request.role_input['parts']
        index=next(i for i,part in enumerate(parts) if part['start_s']==6.)
        inspected.append(parts[index]['end_s'])
        start,end=(6.3,6.5) if len(inspected)==1 else (6.,6.05)
        observation=out.media.observations[0].model_copy(update={
            'part_indices':(index,),'start_s':start,'end_s':end})
        return out.model_copy(update={'media':out.media.model_copy(update={'observations':(observation,)})})

    clock=VirtualClock()
    with fresh(tmp_path/'subject/self.db',clock) as r,semantic_harness(proposer=propose) as (transport,state):
        now=clock.utc_now_us()
        source=PublicMediaSource(source_id='synthetic-video-gap',modality='VIDEO',origin='SYNTHETIC',
            event_time_us=now,observed_time_us=now)
        mid,_=PerceptionService(r.store,providers(),policy()).ingest(data,source,entity_id='observer',scope='world')
        service=MediaSemanticService(CognitionSession(r,transport,policy()))
        gap=service.prepare('gap',mid,data)
        assert service.execute(gap)['state']=='REJECTED'
        observed=service.prepare('observed',mid,data)
        assert service.execute(observed)['state']=='PROPOSED'
        result=service.ground(observed,entity_id='device')
        assert inspected==[6.1,6.1] and state['calls']==2
        assert any(start==6.1 and end>=7. for start,end in result['unobserved_gaps'])


def test_historical_video_does_not_support_new_inference_across_frame_gaps(tmp_path):
    from nana_core.contracts import CoreError
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.world_loop.semantic_harness import semantic_harness,semantic_proposer
    from nana_core.continuity.world_loop.semantics import MediaSemanticService
    from nana_core.presence.runtime import NanaRuntime

    class HistoricalDecoder(MediaDecoder):
        def decode(self,data,modality):
            decoded=super().decode(data,modality)
            for frame in decoded['frames']:
                frame.pop('source_interval_basis',None)
                if frame['sample_s']==6.:
                    frame['source_interval_s']=[6.,7.]
            return decoded

    path=tmp_path/'synthetic-irregular.mkv'
    _write_irregular_video(path,True)
    data=path.read_bytes()
    db=tmp_path/'subject/self.db'
    clock=VirtualClock()
    with fresh(db,clock) as r:
        now=clock.utc_now_us()
        source=PublicMediaSource(source_id='synthetic-historical-gap',modality='VIDEO',origin='SYNTHETIC',
            event_time_us=now,observed_time_us=now)
        mid,record=PerceptionService(r.store,providers(),policy(),decoder=HistoricalDecoder()).ingest(
            data,source,entity_id='observer',scope='world')
        before=MemoryService(r.store).read(mid)['text']
        archived=RecordService(r.store).read(record)
        config,identity=r.config,r.identity_id
    with NanaRuntime(db,config,clock=clock) as r:
        proposed=[]
        def propose(request):
            out=semantic_proposer(request)
            parts=request.role_input['parts']
            index=next(i for i,part in enumerate(parts) if part['start_s']==6.)
            proposed.append(parts[index]['end_s'])
            start,end=(6.3,6.5) if len(proposed)==1 else (6.,6.)
            observation=out.media.observations[0].model_copy(update={
                'part_indices':(index,),'start_s':start,'end_s':end})
            return out.model_copy(update={'media':out.media.model_copy(update={'observations':(observation,)})})
        with semantic_harness(proposer=propose) as (transport,state):
            assert r.identity_id==identity
            service=MediaSemanticService(CognitionSession(r,transport,policy()))
            gap=service.prepare('legacy-gap',mid,data)
            assert service.execute(gap)['state']=='REJECTED'
            observed=service.prepare('legacy-observed',mid,data)
            assert service.execute(observed)['state']=='PROPOSED'
            assert service.prepare('legacy-observed',mid,data)==observed
            assert service.execute(observed)['replayed']
            result=service.ground(observed,entity_id='device')
            assert [6.,6.] in result['covered_intervals']
            assert proposed==[6.,6.] and state['calls']==2
            assert MemoryService(r.store).read(mid)['text']==before
            assert RecordService(r.store).read(record)==archived
            MemoryService(r.store,r.authority).forget(mid,r.authority)
            with pytest.raises(CoreError):service.ground(observed,entity_id='device')
