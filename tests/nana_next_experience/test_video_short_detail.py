from pathlib import Path
import shutil
import subprocess
import pytest

from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe


def test_brief_text_appearance_survives_noisy_one_second_bucket(tmp_path):
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe') or not font.exists():
        pytest.skip('FFmpeg and DejaVu Sans needed for this synthetic fixture')
    path=tmp_path/'detail.mp4'
    filters=(f"eq=brightness='0.1*sin(2*PI*t)':eval=frame,"
             f"drawtext=fontfile={font}:text=CODE7:fontcolor=white:fontsize=16:"
             "x=20:y=20:enable='gte(t,3)*lt(t,3.25)'")
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=c=0x202020:s=320x180:r=4:d=12','-vf',filters,'-c:v','mpeg4',
        '-threads','1','-y',str(path)],check=True,timeout=20)
    result=probe(path)
    assert result['scan_complete']
    # At 3.25s the text has disappeared; retaining only its disappearance
    # cannot supply the visual model the frame on which the letters existed.
    assert 3.0 in {candidate.seconds for candidate in result['candidates']}
