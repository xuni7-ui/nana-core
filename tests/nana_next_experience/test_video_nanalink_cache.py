import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest

from nana_core.contracts import CoreError
from nana_core.nanalink.media import MediaCache
from tools.nana_next_experience.experiments import video_nanalink_cache as adapter


pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),
                              reason='optional FFmpeg unavailable')


@pytest.fixture
def cached_video(tmp_path):
    path=tmp_path/'video.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=32x32:r=4:d=2','-c:v','mpeg4','-threads','1','-y',str(path)],
        check=True,timeout=20)
    data=path.read_bytes();current={'value':True}
    cache=MediaCache(tmp_path/'cache',source_current=lambda ref:current['value'] and ref=='synthetic.video')
    handle=cache.put([data],source_ref='synthetic.video',media_type='video/mp4')
    yield cache,handle,data,current
    cache.close()


def test_original_cache_source_bytes_and_decoded_pts_match(cached_video):
    cache,handle,data,_=cached_video
    result=adapter.decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=.5,end_seconds=1.5,
                                         width=32,height=32)
    assert result.source_sha256==hashlib.sha256(data).hexdigest()==handle.sha256
    assert result.decoded.timestamps==(.5,.75,1.,1.25)
    assert result.decoded.source_ref==handle.source_ref
    assert result.state=='VERIFIED_SNAPSHOT_NOT_INGESTED'
    assert result.source_lifetime=='RECHECK_REQUIRED_AT_USE'
    assert data.hex() not in repr(result)


def test_cached_bytes_tampering_is_rejected_before_decode(cached_video,monkeypatch):
    cache,handle,_,_=cached_video
    path=cache.items[handle.sha256][0]
    data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
    monkeypatch.setattr(adapter,'decode',lambda *a,**kw:pytest.fail('must not decode modified bytes'))
    with pytest.raises(CoreError,match='MEDIA_CACHE_CONTENT_MISMATCH'):
        adapter.decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=0,end_seconds=1)
    from tools.nana_next_experience.experiments.video_cached_snapshot import public_snapshot
    with pytest.raises(CoreError,match='MEDIA_CACHE_CONTENT_MISMATCH'):
        with public_snapshot(cache,handle,privacy='PUBLIC'):pytest.fail('tampered snapshot must not be yielded')


def test_revoked_during_decode_cannot_return_a_candidate(cached_video,monkeypatch):
    cache,handle,_,current=cached_video;original=adapter.decode;snapshots=[]
    def revoking_decode(*args,**kwargs):
        snapshots.append(Path(args[1]).parent)
        result=original(*args,**kwargs);current['value']=False;return result
    monkeypatch.setattr(adapter,'decode',revoking_decode)
    with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):
        adapter.decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=0,end_seconds=1)
    assert snapshots and all(not path.exists() for path in snapshots)


def test_revoked_after_last_read_is_rechecked_before_decode(cached_video,monkeypatch):
    cache,handle,_,current=cached_video;original=cache.read
    def revoking_read(*args,**kwargs):
        data=original(*args,**kwargs);current['value']=False;return data
    monkeypatch.setattr(cache,'read',revoking_read)
    monkeypatch.setattr(adapter,'decode',lambda *a,**kw:pytest.fail('retired source must not decode'))
    with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):
        adapter.decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=0,end_seconds=1)


def test_private_media_never_enters_temporary_video_decoder(cached_video,monkeypatch):
    cache,handle,_,_=cached_video
    monkeypatch.setattr(adapter,'decode',lambda *a,**kw:pytest.fail('private decode must not run'))
    with pytest.raises(ValueError,match='public media'):
        adapter.decode_cached_window(cache,handle,privacy='PERSONAL',start_seconds=0,end_seconds=1)


def test_shared_snapshot_removes_temporary_bytes_after_withdrawal(cached_video):
    from tools.nana_next_experience.experiments.video_cached_snapshot import public_snapshot
    cache,handle,data,current=cached_video
    with public_snapshot(cache,handle,privacy='PUBLIC') as path:
        assert path.read_bytes()==data
    assert not path.exists()
    with pytest.raises(ValueError,match='public media'):
        with public_snapshot(cache,handle,privacy='PERSONAL'):pytest.fail('private media denied')
    with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):
        with public_snapshot(cache,handle,privacy='PUBLIC') as withdrawn:
            current['value']=False
    assert not withdrawn.exists()


def test_original_cache_to_global_image_candidates_preserves_source_digest(cached_video):
    from nana_core.continuity.world_loop.perception import MediaDecoder
    from tests.nana_next_experience.test_video_selected_images import selection
    from tools.nana_next_experience.experiments.video_global_budget import select_windows,project_window
    from tools.nana_next_experience.experiments.video_selected_images import selected_images
    cache,handle,data,_=cached_video
    windows=[adapter.decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=a,end_seconds=b,
                                          width=32,height=32) for a,b in ((0,1.5),(.5,2))]
    assert all(item.source_sha256==hashlib.sha256(data).hexdigest() for item in windows)
    selections=[selection(item.decoded) for item in windows]
    global_selection=select_windows(handle.source_ref,2,selections,budget=3,max_gap=1)
    images=[image for i,(item,selected) in enumerate(zip(windows,selections))
            for image in selected_images(item.decoded,project_window(global_selection,selected,i))]
    assert len(images)==len(global_selection['selected_frames'])<=3
    assert len({image.pts_tick for image in images})==len(images)
    assert all(MediaDecoder().decode(image.png,'IMAGE')['pixel_digest']==image.pixel_sha256 for image in images)
    assert all(item.source_lifetime=='RECHECK_REQUIRED_AT_USE' for item in windows)
