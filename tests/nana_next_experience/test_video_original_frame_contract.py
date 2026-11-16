"""Current Core frame provenance must not be claimed for decoded video frames."""
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.life.bilibili import BilibiliSourceAdapter, PublicReading
from nana_core.life.bilibili_frames import BilibiliFrameService, VideoFrame
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh
from tests.nana_next_experience.test_video_selected_images import selection
from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_selected_images import selected_images


pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe')),
                              reason='optional local media tools required')


def test_original_frame_capture_revokes_children_but_labels_any_input_as_storyboard(tmp_path):
    # A real decoded frame from synthetic red video, not a publisher storyboard.
    # Direct capture below is only a temporary counterexample.
    path=tmp_path/'synthetic.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=red:s=32x32:r=2:d=2','-c:v','mpeg4','-threads','1','-y',str(path)],
        check=True,timeout=20)
    decoded=decode('synthetic.video',path,width=32,height=32,start_seconds=0,end_seconds=2)
    candidate=next(selected_images(decoded,selection(decoded)))
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app=SimpleNamespace(runtime=runtime)
        reading=PublicReading('synthetic.video','VIDEO_READING',runtime.clock.utc_now_us(),
            {'bvid':'BV1t55v6DE2v','cid':123,'duration_seconds':2},'SYNTHETIC_FIXTURE')
        source=BilibiliSourceAdapter(app).ingest(reading)
        input_frame=VideoFrame('BV1t55v6DE2v',123,candidate.source_seconds,candidate.png,'SYNTHETIC_FIXTURE')
        child,=BilibiliFrameService(app).capture(source,(input_frame,))
        body=json.loads(MemoryService(runtime.store).read(child)['text'])
        assert body['source']['coverage']=='PUBLISHER_STORYBOARD_SAMPLE_NOT_FULL_WATCH'
        assert runtime.store.db.execute(
            "SELECT 1 FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY' AND parent_id=?",
            (child,source)).fetchone()
        MemoryService(runtime.store,runtime.authority).forget(source,runtime.authority)
        with pytest.raises(CoreError):MemoryService(runtime.store).read(child)


def test_cache_source_reference_alone_does_not_bind_video_bytes_to_platform_receipt(tmp_path):
    videos=[]
    for color in ('red','blue'):
        path=tmp_path/(color+'.mp4')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            f'color={color}:s=32x32:r=2:d=2','-c:v','mpeg4','-threads','1','-y',str(path)],
            check=True,timeout=20)
        videos.append(path.read_bytes())
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app=SimpleNamespace(runtime=runtime)
        reading=PublicReading('synthetic.video','VIDEO_READING',runtime.clock.utc_now_us(),
            {'bvid':'BV1t55v6DE2v','cid':123,'duration_seconds':2},'SYNTHETIC_FIXTURE')
        source=BilibiliSourceAdapter(app).ingest(reading);memory=MemoryService(runtime.store)
        def current(ref):
            try:memory.read(ref);return True
            except CoreError:return False
        cache=MediaCache(tmp_path/'cache',source_current=current)
        try:
            handles=[cache.put([video],source_ref=source,media_type='video/mp4') for video in videos]
            assert handles[0].sha256!=handles[1].sha256
            assert all(cache.resolve(source_ref=source,sha256=h.sha256).sha256==h.sha256 for h in handles)
            # The current source namespace and two valid cached hashes alone
            # cannot establish which media, if either, was actually acquired.
            MemoryService(runtime.store,runtime.authority).forget(source,runtime.authority)
            for handle in handles:
                with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):
                    cache.resolve(source_ref=source,sha256=handle.sha256)
        finally:cache.close()
