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
    # A source or individual frame may be withdrawn during projection.
    # Recheck each original memory immediately before returning metadata.
    for sample in samples:
        memory.read(sample['source_memory_id'])
    memory.read(source_memory_id)
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


def public_video_cache_handle(app, cache, source_memory_id, *, scope):
    """Return the cache handle for one current original public observation."""
    handle, _ = _public_video_cache_binding(app, cache, source_memory_id, scope=scope)
    return handle


def _public_video_cache_binding(app, cache, source_memory_id, *, scope):
    """Resolve original public VIDEO evidence to a cache handle, without granting use.

    This does not fetch, decode, authenticate a platform, or prove raw bytes.
    A consumer must verify the content hash and recheck this source at handoff.
    """
    from ..continuity.records import RecordService
    from .media import MediaCache
    if (type(cache) is not MediaCache or type(source_memory_id) is not str
            or not 1 <= len(source_memory_id) <= 128 or type(scope) is not str
            or scope not in app.policy.allowed_scopes or 'PUBLIC' not in app.policy.readable_privacy):
        raise CoreError('NANALINK_VIDEO_SOURCE_DENIED')
    memory = MemoryService(app.runtime.store)
    row = memory.read(source_memory_id)
    provenance = row.get('source_provenance') or {}
    if (row.get('scope') != scope or row.get('entity_id') != app.runtime.config.entity_id
            or row.get('privacy_class') != 'PUBLIC' or row.get('authority') != 'DIRECT'
            or row.get('epistemic_kind') != 'OBSERVATION' or type(provenance) is not dict
            or (provenance.get('domain'), provenance.get('source_namespace')) not in {
                ('SYNTHETIC_ONLY', 'synthetic.public-media'), ('RECORDED_PUBLIC', 'recorded.public-media')}
            or provenance.get('source_kind') != 'DIRECT_OBSERVATION'):
        raise CoreError('NANALINK_VIDEO_SOURCE_DENIED')
    try:
        body = json.loads(row['text'])
        source, decoded, sha = body['source'], body['decoded'], body['source_byte_digest']
        if (type(source) is not dict or type(decoded) is not dict or source.get('modality') != 'VIDEO'
                or source.get('privacy') != 'PUBLIC' or decoded.get('modality') != 'VIDEO'
                or (provenance.get('domain'), source.get('origin')) not in {
                    ('SYNTHETIC_ONLY', 'SYNTHETIC'), ('RECORDED_PUBLIC', 'RECORDED')}
                or decoded.get('decoded') is not True or source.get('source_id') != provenance.get('source_reference')
                or type(sha) is not str or not re.fullmatch(r'[0-9a-f]{64}', sha)):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise CoreError('NANALINK_VIDEO_SOURCE_INVALID') from None
    store = app.runtime.store
    observations = store.db.execute(
        "SELECT record_id FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id=? "
        "AND scope=? AND privacy_class='PUBLIC' AND lifecycle='ACTIVE' LIMIT 2",
        (source_memory_id, scope)).fetchall()
    records = RecordService(store)
    if len(observations) != 1:
        raise CoreError('NANALINK_VIDEO_OBSERVATION_NOT_CURRENT')
    observation_id = observations[0]['record_id']
    observation = records.read(observation_id)
    if (observation['payload'].get('source_memory_id') != source_memory_id
            or not records.current_support(observation_id)):
        raise CoreError('NANALINK_VIDEO_OBSERVATION_NOT_CURRENT')
    handle = cache.resolve(source_ref=source_memory_id, sha256=sha)
    if not 1 <= handle.size <= 16 * 1024 * 1024:
        raise CoreError('NANALINK_VIDEO_BYTE_BOUND')
    memory.read(source_memory_id)
    head = store.one('continuity_records', observation_id)
    if not head or head['lifecycle'] != 'ACTIVE' or not records.current_support(observation_id):
        raise CoreError('NANALINK_VIDEO_OBSERVATION_NOT_CURRENT')
    return handle, observation_id


def with_current_public_video(app, cache, source_memory_id, *, scope, operation):
    """Run a trusted local candidate operation only while original evidence is current.

    This guards the returned candidate, not arbitrary effects inside a callback.
    The caller remains responsible for the original C/Grant/Kernel decision and
    the operation must independently check cached bytes against the handle hash.
    """
    from collections.abc import AsyncIterator, Iterator
    import inspect
    if not callable(operation):
        raise CoreError('NANALINK_VIDEO_OPERATION_REQUIRED')
    before, before_observation = _public_video_cache_binding(app, cache, source_memory_id, scope=scope)
    result = operation(before)
    if inspect.isawaitable(result) or isinstance(result, (Iterator, AsyncIterator)):
        if inspect.iscoroutine(result):
            result.close()
        raise CoreError('NANALINK_VIDEO_MATERIALIZED_RESULT_REQUIRED')
    after, after_observation = _public_video_cache_binding(app, cache, source_memory_id, scope=scope)
    if (before_observation, before.source_ref, before.sha256, before.size) != (
            after_observation, after.source_ref, after.sha256, after.size):
        raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
    if (getattr(result, 'source_ref', None), getattr(result, 'source_sha256', None)) != (before.source_ref, before.sha256):
        raise CoreError('NANALINK_VIDEO_OUTPUT_SOURCE_MISMATCH')
    return result
