import shutil
import subprocess

import pytest

from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_global_budget import select_windows,project_window
from tools.nana_next_experience.experiments.video_selected_images import selected_images
from nana_core.continuity.world_loop.perception import MediaDecoder
from tests.nana_next_experience.test_video_selected_images import selection


pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe','bwrap')),
                              reason='optional local media tools unavailable')


def test_global_budget_deduplicates_real_overlapping_windows_and_preserves_pts(tmp_path):
    source=tmp_path/'video.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=32x32:r=1:d=6','-c:v','mpeg4','-g','1','-threads','1',
        '-y',str(source)],check=True,timeout=20)
    windows=[decode('synthetic.source',source,width=32,height=32,start_seconds=a,end_seconds=b)
             for a,b in ((0,4),(2,6))]
    results=[selection(w) for w in windows]
    selected=select_windows('synthetic.source',6,results,budget=3,max_gap=2)
    assert sum(len(r['selected_frames']) for r in results)==6
    assert selected['candidate_count']<6 and len(selected['selected_frames'])<=3
    assert selected['unrequested_intervals']==[] and not selected['whole_video_observed']
    assert selected['candidate_deduplication']=='PTS_ONLY_BYTES_UNVERIFIED'
    for item in selected['selected_frames']:
        assert item['window_indices']
        assert all(any(f['pts_tick']==item['pts_tick'] and f['seconds']==item['seconds']
                       for f in results[i]['selected_frames']) for i in item['window_indices'])
    assert selected['model_calls']==0 and selected['state']=='CANDIDATES_NOT_DELIVERED'
    images=[image for i,(decoded,result) in enumerate(zip(windows,results))
            for image in selected_images(decoded,project_window(selected,result,i))]
    assert len(images)==len(selected['selected_frames'])<=3
    assert len({image.pts_tick for image in images})==len(images)
    assert all(MediaDecoder().decode(image.png,'IMAGE')['pixel_digest']==image.pixel_sha256 for image in images)


def test_missing_windows_and_empty_window_remain_explicitly_unobserved():
    empty={'status':'NO_NEW_FRAME_DECODED_NOT_OBSERVED','source_ref':'synthetic.source',
           'requested_window':(2,4),'selected_frames':[],'whole_window_observed':False}
    result=select_windows('synthetic.source',10,[empty],budget=3,max_gap=2)
    assert result['unrequested_intervals']==[(0,2),(4,10)]
    assert result['sampling_gaps_over_threshold']==((0.,10),)
    assert not result['sampling_gap_target_met'] and not result['whole_video_observed']


def test_cross_source_and_forged_empty_selection_are_rejected():
    empty={'status':'NO_NEW_FRAME_DECODED_NOT_OBSERVED','source_ref':'other',
           'requested_window':(0,1),'selected_frames':[],'whole_window_observed':False}
    with pytest.raises(ValueError,match='window result'):
        select_windows('synthetic.source',1,[empty],budget=1,max_gap=1)
    empty['source_ref']='synthetic.source';empty['selected_frames']=[{}]
    with pytest.raises(ValueError,match='empty window'):
        select_windows('synthetic.source',1,[empty],budget=1,max_gap=1)


def test_small_global_budget_can_drop_an_earlier_event_candidate():
    # Current global planner has no cue scores; its coverage preference may
    # drop a local cut candidate. This is a retained limitation, not recall proof.
    window={'source_ref':'synthetic.source','status':'WINDOW_CANDIDATES_ONLY',
        'whole_window_observed':False,'requested_window':(0,10),
        'selection_state':'CANDIDATES_NOT_DELIVERED','timestamp_basis':'container_relative',
        'coordinate_space':'decoded_scaled_pixels_no_rotation','decoded_size':(32,32),
        'source_size':(32,32),'timeline_origin':'0',
        'selected_frames':[{'seconds':1.,'pts_tick':1,'time_base':(1,1)},
                           {'seconds':5.,'pts_tick':5,'time_base':(1,1)}]}
    result=select_windows('synthetic.source',10,[window],budget=1,max_gap=10)
    assert [x['seconds'] for x in result['selected_frames']]==[5.]
    assert result['candidate_count']==2 and not result['whole_video_observed']
    window['selected_cues']=[{'seconds':1.,'cues':['dsh_cut']},{'seconds':5.,'cues':[]}]
    candidate=select_windows('synthetic.source',10,[window],budget=1,max_gap=10)
    assert [x['seconds'] for x in candidate['selected_frames']]==[1.]
    assert candidate['selected_frames'][0]['cues']==['dsh_cut']
    assert candidate['sampling_gap_target_met']


def test_global_cue_must_refer_to_a_selected_frame():
    window={'source_ref':'synthetic.source','status':'WINDOW_CANDIDATES_ONLY',
        'whole_window_observed':False,'requested_window':(0,10),
        'selection_state':'CANDIDATES_NOT_DELIVERED','timestamp_basis':'container_relative',
        'coordinate_space':'decoded_scaled_pixels_no_rotation','decoded_size':(32,32),
        'source_size':(32,32),'timeline_origin':'0',
        'selected_frames':[{'seconds':1.,'pts_tick':1,'time_base':(1,1)}],
        'selected_cues':[{'seconds':2.,'cues':['dsh_cut']}]}
    with pytest.raises(ValueError,match='cue is not a selected frame'):
        select_windows('synthetic.source',10,[window],budget=1,max_gap=10)
