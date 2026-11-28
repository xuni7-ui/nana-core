"""Original-store Bilibili video history must filter before its bounded window."""
from types import SimpleNamespace

import pytest

from nana_core.clock import Clock
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


def test_existing_storyboard_handoff_preserves_time_privacy_and_withdrawal(tmp_path):
    import pytest
    from nana_core.contracts import CoreError
    from nana_core.continuity.memory import MemoryService
    from nana_core.life.bilibili import BilibiliPublicTransport
    from nana_core.life.bilibili_frames import BilibiliFrameService
    from nana_core.nanalink.video_handoff import storyboard_samples
    from tests.living_release_v4.bilibili_loopback import counterpart
    with counterpart() as (opener, platform), fresh(tmp_path/'subject.db', Clock()) as runtime:
        platform['video_duration'] = 12
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9,
                                            loopback_endpoint=opener.endpoint)
        reading = transport.read_video('BV1t55v6DE2v', visual=True)
        app = SimpleNamespace(runtime=runtime, policy=policy())
        source = BilibiliSourceAdapter(app).ingest(reading)
        frame_ids = BilibiliFrameService(app).capture(source, reading.frames)
        calls = transport.calls
        result = storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))
        assert result['candidate_seconds'] == [0., 5., 10.]
        assert [row['source_memory_id'] for row in result['samples']] == list(frame_ids)
        assert result['duration_seconds'] == 12 and result['duration_status'] == 'KNOWN'
        assert result['bounded_sample_input_valid'] and result['planning_blockers'] == []
        assert result['cut_motion'] == 'NOT_MEASURED' and not result['full_video_watched']
        assert result['subtitle_ranges'] == [{'from_seconds': 1., 'to_seconds': 2.,
            'source_memory_id': source, 'segment_index': 0, 'source': 'PUBLISHER_SUBTITLE'}]
        assert result['subtitle_text'] == 'OMITTED_SOURCE_REFERENCE_ONLY'
        assert 'Synthetic timestamped subtitle' not in str(result)
        assert result['account_key'] is None and result['network_calls'] == result['model_calls'] == 0
        assert transport.calls == calls and 'png_b64' not in str(result)
        with pytest.raises(CoreError, match='NANALINK_VIDEO_SOURCE_DENIED'):
            storyboard_samples(app, source, scope='world', privacy_classes=('PUBLIC',))
        MemoryService(runtime.store, runtime.authority).forget(frame_ids[1], runtime.authority)
        assert storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))['candidate_seconds'] == [0., 10.]
        MemoryService(runtime.store, runtime.authority).forget(source, runtime.authority)
        with pytest.raises(CoreError):
            storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))


@pytest.mark.parametrize('duration', [None, 1, 5, '12'])
def test_invalid_or_inconsistent_duration_never_claims_planning_readiness(tmp_path, duration):
    from nana_core.life.bilibili import BilibiliPublicTransport
    from nana_core.life.bilibili_frames import BilibiliFrameService
    from nana_core.nanalink.video_handoff import storyboard_samples
    from tests.living_release_v4.bilibili_loopback import counterpart
    with counterpart() as (opener, platform), fresh(tmp_path/'subject.db', Clock()) as runtime:
        if duration is not None:
            platform['video_duration'] = duration
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9,
                                            loopback_endpoint=opener.endpoint)
        reading = transport.read_video('BV1t55v6DE2v', visual=True)
        app = SimpleNamespace(runtime=runtime, policy=policy())
        source = BilibiliSourceAdapter(app).ingest(reading)
        BilibiliFrameService(app).capture(source, reading.frames)
        result = storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))
        assert result['duration_seconds'] == (duration if type(duration) is int else None) and not result['bounded_sample_input_valid']
        expected = (['SAMPLE_OUTSIDE_DURATION', 'SUBTITLE_OUTSIDE_DURATION'] if duration == 1 else
                    ['SAMPLE_OUTSIDE_DURATION'] if duration == 5 else
                    ['DURATION_MISSING'] if duration is None else ['DURATION_INVALID'])
        assert result['planning_blockers'] == expected
        assert result['candidate_seconds'] == [0., 5., 10.]


@pytest.mark.parametrize('withdraw_target', ['source', 'frame'])
def test_storyboard_projection_rechecks_source_after_last_frame_read(tmp_path, monkeypatch, withdraw_target):
    from nana_core.contracts import CoreError
    from nana_core.continuity.memory import MemoryService
    from nana_core.life.bilibili import BilibiliPublicTransport
    from nana_core.life.bilibili_frames import BilibiliFrameService
    from nana_core.nanalink.video_handoff import storyboard_samples
    from tests.living_release_v4.bilibili_loopback import counterpart
    with counterpart() as (opener, platform), fresh(tmp_path/'subject.db', Clock()) as runtime:
        platform['video_duration'] = 12
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9,
                                            loopback_endpoint=opener.endpoint)
        reading = transport.read_video('BV1t55v6DE2v', visual=True)
        app = SimpleNamespace(runtime=runtime, policy=policy())
        source = BilibiliSourceAdapter(app).ingest(reading)
        frames = BilibiliFrameService(app).capture(source, reading.frames)
        original = MemoryService.read
        calls = {'last_frame': 0}
        def read_and_withdraw(self, memory_id, *args, **kwargs):
            row = original(self, memory_id, *args, **kwargs)
            if memory_id == frames[-1]:
                calls['last_frame'] += 1
                if calls['last_frame'] == 2:
                    target = source if withdraw_target == 'source' else frames[-1]
                    MemoryService(runtime.store, runtime.authority).forget(target, runtime.authority)
            return row
        monkeypatch.setattr(MemoryService, 'read', read_and_withdraw)
        with pytest.raises(CoreError):
            storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))
        assert calls['last_frame'] == 2


def test_multipart_video_uses_duration_for_the_cid_requested_by_media(tmp_path):
    from nana_core.life.bilibili import BilibiliPublicTransport
    from nana_core.life.bilibili_frames import BilibiliFrameService
    from nana_core.nanalink.video_handoff import storyboard_samples
    from tests.living_release_v4.bilibili_loopback import counterpart

    with counterpart() as (opener, platform), fresh(tmp_path/'subject.db', Clock()) as runtime:
        platform['video_duration'] = 600
        platform['video_pages'] = [{'cid': 9, 'duration': 595}, {'cid': 8, 'duration': 5}]
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9,
                                            loopback_endpoint=opener.endpoint)
        reading = transport.read_video('BV1t55v6DE2v', visual=True)
        assert reading.payload['cid'] == 8 and reading.payload['duration_seconds'] == 5
        assert {frame.cid for frame in reading.frames} == {8}
        app = SimpleNamespace(runtime=runtime, policy=policy())
        source = BilibiliSourceAdapter(app).ingest(reading)
        BilibiliFrameService(app).capture(source, reading.frames)
        projection = storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))
        assert projection['planning_blockers'] == ['SAMPLE_OUTSIDE_DURATION']

        platform['video_pages'] = [{'cid': 9, 'duration': 595}, {'cid': 10, 'duration': 5}]
        before = transport.calls
        missing = transport.read_video('BV1t55v6DE2v', visual=True)
        assert missing.payload['notes'] == ['MATERIAL_IDENTITY_UNAVAILABLE']
        assert not missing.frames and transport.calls == before + 1
