"""Original-store Bilibili video history must filter before its bounded window."""
from types import SimpleNamespace

from nana_core.life.bilibili import BilibiliSourceAdapter, PublicReading
from tests.world_loop.helpers import capture, fresh, policy


def test_private_video_population_does_not_hide_eligible_project_video(tmp_path):
    with fresh(tmp_path/'subject.db') as runtime:
        adapter = BilibiliSourceAdapter(SimpleNamespace(runtime=runtime, policy=policy()))
        now = runtime.clock.utc_now_us()
        base = adapter.ingest(PublicReading('project-video', 'VIDEO_METADATA', now,
            {'bvid': 'BV1t55v6DE2v', 'title': 'visible source'}, 'SYNTHETIC_FIXTURE'))
        private = capture(runtime, 'private-source', {'text': 'synthetic private dependency'}, privacy='PERSONAL')
        for i in range(65):
            adapter.ingest(PublicReading('other-video-'+str(i), 'VIDEO_METADATA', now,
                {'bvid': 'BV1t55v6DE2v', 'title': 'unrelated private '+str(i)}, 'SYNTHETIC_FIXTURE'),
                parents=(private,))
        result = adapter.history(privacy=('PROJECT',))
        assert [row['source_memory_id'] for row in result['items']] == [base]
        assert result['network_calls'] == 0 and result['second_memory_authority'] is False
        assert adapter.history(privacy=())['items'] == []
        assert adapter.history(privacy=('PROJECT',), scope='other-scope')['items'] == []
        from nana_core.continuity.memory import MemoryService
        MemoryService(runtime.store, runtime.authority).forget(base, runtime.authority)
        assert adapter.history(privacy=('PROJECT',))['items'] == []
