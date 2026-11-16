"""Read-only candidate handoff from original Bilibili storyboard memories.

This is a source projection, not a video decoder, scheduler, Grant, or claim
that the unobserved timeline was seen. It performs no network or model calls.
"""
import json
import math
import re

from ..contracts import CoreError
from ..continuity.memory import MemoryService
from ..life.bilibili_frames import BilibiliFrameService


def storyboard_samples(app, source_memory_id, *, scope, privacy_classes):
    """Project only already-observed, current frame timestamps and provenance.

    `candidate_seconds` can feed a separately supplied planner's Candidate
    objects; cut/motion scores are unknown, not measured zeros. Frame IDs are
    opaque original Memory references. Public video provides no account binding.
    """
    policy = app.policy
    if (type(source_memory_id) is not str or not 1 <= len(source_memory_id) <= 128
            or type(scope) is not str or scope not in policy.allowed_scopes
            or type(privacy_classes) not in (tuple, list)
            or not privacy_classes or any(type(p) is not str for p in privacy_classes)
            or not set(privacy_classes) <= set(policy.readable_privacy)):
        raise CoreError('NANALINK_VIDEO_SCOPE_DENIED')
    memory = MemoryService(app.runtime.store)
    source = memory.read(source_memory_id)
    if (source['scope'] != scope or source['privacy_class'] not in privacy_classes
            or source['entity_id'] != app.runtime.config.entity_id
            or source['source_provenance']['source_namespace'] not in {
                'recorded.project.bilibili', 'recorded.bilibili.public'}):
        raise CoreError('NANALINK_VIDEO_SOURCE_DENIED')
    try:
        body = json.loads(source['text'])
        data = body['data']
        bvid, cid = data['bvid'], data['cid']
        if (body['kind'] != 'VIDEO_READING' or type(bvid) is not str
                or not re.fullmatch(r'BV[A-Za-z0-9]{10}', bvid) or type(cid) is not int or cid < 1):
            raise ValueError()
        duration = data.get('duration_seconds')
        duration_status = 'MISSING' if duration is None else 'KNOWN'
        if duration is not None and (type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= 86400):
            duration, duration_status = None, 'INVALID'
    except (KeyError, TypeError, ValueError):
        raise CoreError('NANALINK_VIDEO_SOURCE_INVALID') from None
    subtitles = data.get('subtitle_segments', [])
    if type(subtitles) is not list or len(subtitles) > 20:
        raise CoreError('NANALINK_VIDEO_SUBTITLE_INVALID')
    subtitle_ranges = []
    for index, segment in enumerate(subtitles):
        if type(segment) is not dict:
            raise CoreError('NANALINK_VIDEO_SUBTITLE_INVALID')
        start, end = segment.get('from_seconds'), segment.get('to_seconds')
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start <= end <= 86400
                or segment.get('source') != 'PUBLISHER_SUBTITLE'):
            raise CoreError('NANALINK_VIDEO_SUBTITLE_INVALID')
        subtitle_ranges.append({'from_seconds': float(start), 'to_seconds': float(end),
                                'source_memory_id': source_memory_id, 'segment_index': index,
                                'source': 'PUBLISHER_SUBTITLE'})
    frames = BilibiliFrameService(app).coverage(source_memory_id)['frame_samples']
    samples = []
    for frame in frames:
        item = memory.read(frame['source_memory_id'])
        if (item['scope'] != scope or item['privacy_class'] not in privacy_classes
                or item['entity_id'] != source['entity_id']):
            raise CoreError('NANALINK_VIDEO_FRAME_DENIED')
        try:
            descriptor = json.loads(item['text'])['source']
            seconds = descriptor['at_seconds']
            if (descriptor['bvid'] != bvid or descriptor['cid'] != cid or descriptor['origin'] != body['origin']
                    or type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 86400):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise CoreError('NANALINK_VIDEO_FRAME_INVALID') from None
        samples.append({'seconds': float(seconds), 'source_memory_id': item['memory_id']})
    samples.sort(key=lambda item: (item['seconds'], item['source_memory_id']))
    seconds = [sample['seconds'] for sample in samples]
    blockers = []
    if duration is None:
        blockers.append('DURATION_' + duration_status)
    if not seconds:
        blockers.append('NO_CURRENT_SAMPLES')
    if duration is not None and seconds and max(seconds) > duration:
        blockers.append('SAMPLE_OUTSIDE_DURATION')
    if duration is not None and any(item['to_seconds'] > duration for item in subtitle_ranges):
        blockers.append('SUBTITLE_OUTSIDE_DURATION')
    if len(set(seconds)) != len(seconds):
        blockers.append('DUPLICATE_SAMPLE_TIME')
    return {'schema_version': 1, 'platform': 'bilibili', 'account_key': None,
            'account_binding': 'PUBLIC_SOURCE_NOT_ACCOUNT_ATTRIBUTED', 'source_memory_id': source_memory_id,
            'scope': scope, 'privacy_class': source['privacy_class'], 'origin': body['origin'],
            'bvid': bvid, 'cid': cid, 'event_time_us': source['event_time_us'],
            'observed_at_us': source['observed_time_us'],
            'duration_seconds': duration, 'duration_status': duration_status, 'samples': samples, 'candidate_seconds': seconds,
            'subtitle_ranges': subtitle_ranges, 'subtitle_text': 'OMITTED_SOURCE_REFERENCE_ONLY',
            'bounded_sample_input_valid': not blockers, 'planning_blockers': blockers, 'cut_motion': 'NOT_MEASURED',
            'coverage': 'EXISTING_STORYBOARD_SAMPLES_ONLY', 'full_video_watched': False,
            'unobserved_intervals': 'NOT_INFERRED', 'network_calls': 0, 'model_calls': 0}
