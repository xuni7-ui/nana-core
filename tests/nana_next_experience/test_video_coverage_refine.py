from tools.nana_next_experience.experiments.video_coverage import Candidate
from tools.nana_next_experience.experiments.video_coverage_refine import refine


def test_change_can_replace_redundant_frame_without_breaking_gap():
    candidates=[Candidate(float(i),cut=10 if i in (4,8) else 0) for i in range(12)]
    result=refine(12,candidates,4,max_gap=4)
    assert {4,8}<=set(result['timestamps'])
    assert result['coverage_target_met'] and result['change_swaps']>0


def test_impossible_simultaneous_cut_and_strict_coverage_is_honest():
    candidates=[Candidate(float(i),cut=10 if i in (4,8) else 0) for i in range(12)]
    result=refine(12,candidates,4,max_gap=3)
    assert not ({4,8}<=set(result['timestamps']))
    assert result['coverage_target_met']


def test_sparse_input_cannot_be_made_to_look_complete():
    result=refine(100,[Candidate(1),Candidate(2),Candidate(90,cut=100)],3,max_gap=15)
    assert not result['coverage_target_met'] and (2,90) in result['gaps']


def test_ffmpeg_measurements_obey_real_cut_and_gap_tradeoff(tmp_path):
    import shutil
    import subprocess
    import pytest
    from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('optional FFmpeg unavailable')
    path=tmp_path/'cuts.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','color=black:s=160x90:r=4:d=4',
        '-f','lavfi','-i','color=white:s=160x90:r=4:d=4',
        '-f','lavfi','-i','testsrc2=s=160x90:r=4:d=4',
        '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0',
        '-c:v','mpeg4','-threads','1','-y',str(path)],check=True,timeout=20)
    measured=probe(path)
    strict=refine(12,measured['candidates'],4,max_gap=3)
    relaxed=refine(12,measured['candidates'],4,max_gap=4)
    assert strict['coverage_target_met'] and not {4,8}<=set(strict['timestamps'])
    assert relaxed['coverage_target_met'] and {4,8}<=set(relaxed['timestamps'])
