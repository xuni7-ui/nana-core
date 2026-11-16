import pytest
Image=pytest.importorskip('PIL.Image')
ImageDraw=pytest.importorskip('PIL.ImageDraw')
from tools.nana_next_experience.experiments.video_local_change import local_change


def test_local_detail_retained_despite_global_brightness_change():
    before=Image.new('L',(120,80),40);after=Image.new('L',(120,80),60)
    ImageDraw.Draw(after).rectangle((18,15,38,22),fill=230)
    result=local_change(before,after,padding=2)
    assert result['box']==(16,13,41,25)
    assert result['global_luminance_shift']==20
    assert result['changed_pixels']==21*8


def test_brightness_shift_and_broad_motion_do_not_become_local_crop():
    before=Image.new('L',(120,80),40)
    assert local_change(before,Image.new('L',(120,80),70)) is None
    assert local_change(before,Image.new('L',(120,80),220)) is None


def test_dispersed_noise_is_not_claimed_as_one_local_region():
    before=Image.new('L',(120,80),40);after=before.copy();d=ImageDraw.Draw(after)
    d.rectangle((1,1,4,4),fill=230);d.rectangle((110,70,115,75),fill=230)
    assert local_change(before,after) is None


def test_mismatched_or_too_large_images_fail_closed():
    before=Image.new('L',(12,8))
    with pytest.raises(ValueError):local_change(before,Image.new('L',(8,12)))
    with pytest.raises(ValueError):local_change(Image.new('L',(1024,1024)),Image.new('L',(1024,1024)))


def test_moving_cursor_is_a_change_not_proof_of_text():
    before=Image.new('L',(120,80),40);after=before.copy()
    ImageDraw.Draw(after).rectangle((20,20,28,28),fill=230)
    result=local_change(before,after)
    assert result is not None and 'no text' in result['meaning']


def test_decoded_short_text_region_with_global_brightness_change(tmp_path):
    from pathlib import Path
    import shutil
    import subprocess
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if not shutil.which('ffmpeg') or not font.exists():
        pytest.skip('FFmpeg and DejaVu Sans needed for this synthetic fixture')
    clip=tmp_path/'text.mp4'
    filters=(f"eq=brightness='0.1*sin(2*PI*t)':eval=frame,"
             f"drawtext=fontfile={font}:text=CODE7:fontcolor=white:fontsize=16:"
             "x=20:y=20:enable='gte(t,3)*lt(t,3.25)'")
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=c=0x202020:s=320x180:r=4:d=12','-vf',filters,'-c:v','mpeg4',
        '-threads','1','-y',str(clip)],check=True,timeout=20)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(clip),
        '-vf',"select='eq(n,11)+eq(n,12)'",'-fps_mode','passthrough',
        '-y',str(tmp_path/'%02d.png')],check=True,timeout=20)
    with Image.open(tmp_path/'01.png') as before, Image.open(tmp_path/'02.png') as after:
        result=local_change(before,after)
    assert result is not None
    left,top,right,bottom=result['box']
    assert left<=20 and top<=24 and right>=70 and bottom>=30


def test_original_region_crop_preserves_coordinates_and_enlarges():
    from tools.nana_next_experience.experiments.video_local_change import crop_local_change
    before=Image.new('L',(120,80),40);after=before.copy()
    ImageDraw.Draw(after).rectangle((18,15,38,22),fill=230)
    proposal=local_change(before,after,padding=2)
    crop,metadata=crop_local_change(after,proposal,scale=3)
    assert crop.size==(75,36) and metadata['source_box']==(16,13,41,25)
    assert max(crop.getextrema())>200
    with pytest.raises(ValueError):crop_local_change(after,{'coordinate_space':'input_pixels','box':(-1,0,10,10)})
    with pytest.raises(ValueError):crop_local_change(after,proposal,scale=5)


def test_identical_gray_content_never_creates_a_change_proposal():
    image=Image.new('RGB',(120,80),(80,30,100))
    assert local_change(image,image.copy()) is None
    # Identical grayscale images are already indistinguishable to the original
    # luminance-only baseline, regardless of their source image mode.
    assert local_change(image,image.convert('L')) is None
