"""Project eligible original media observations to bounded C choices.

Descriptors carry no local path, bytes, permission or recipient authority.
The caller supplies already privacy-checked original MemoryService rows.
"""
import json
from ..continuity.autonomy.contracts import MediaSelection


def candidate(row):
    provenance=row.get('source_provenance') or {}
    if type(provenance) is not dict:
        return None
    if (row.get('privacy_class')!='PUBLIC' or row.get('authority')!='DIRECT' or row.get('epistemic_kind')!='OBSERVATION'
            or provenance.get('source_namespace') not in {'synthetic.public-media','recorded.public-media'}):
        return None
    try:
        data=json.loads(row['text']);source=data['source'];decoded=data['decoded']
        if (type(source) is not dict or type(decoded) is not dict or source.get('modality')!='IMAGE'
                or decoded.get('modality')!='IMAGE' or decoded.get('decoded') is not True
                or provenance.get('source_reference') != source.get('source_id')
                or provenance.get('source_kind') != 'DIRECT_OBSERVATION'
                or (provenance.get('domain'), provenance.get('source_namespace')) not in {
                    ('SYNTHETIC_ONLY', 'synthetic.public-media'), ('RECORDED_PUBLIC', 'recorded.public-media')}):
            return None
        return MediaSelection(kind='image',source_memory_id=row['memory_id'],
                              content_sha256=data['source_byte_digest'],reference=source['source_id'])
    except (ValueError,TypeError,KeyError):
        return None


def current_image_observation(store, source_memory_id, *, scope):
    """Resolve the unique observation a memory-only image choice can bind."""
    from ..continuity.records import RecordService

    observations = store.db.execute(
        "SELECT record_id, lifecycle FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id=? "
        "AND scope=? AND privacy_class='PUBLIC' LIMIT 2",
        (source_memory_id, scope),
    ).fetchall()
    # A replacement under the same memory ID is ambiguous for an existing
    # choice. A new observation needs its own source reference.
    if len(observations) != 1 or observations[0]['lifecycle'] != 'ACTIVE':
        return None
    records = RecordService(store)
    observation_id = observations[0]['record_id']
    observation = records.read(observation_id)
    if (observation['payload'].get('source_memory_id') != source_memory_id
            or not records.current_support(observation_id)):
        return None
    return observation_id


def resolve_image(store, cache, selection, *, max_bytes=8192):
    """Read a bounded source-bound image; this does not grant a send.

    The original memory, original perception record, cache association and
    content hash must all still agree. Never accept a URL or local path.
    """
    import hashlib
    from ..contracts import CoreError
    from ..continuity.memory import MemoryService
    from .media import MediaCache

    if type(selection) is not MediaSelection or selection.kind != 'image' or type(cache) is not MediaCache:
        raise CoreError('MEDIA_SELECTED_IMAGE_REQUIRED')
    if type(max_bytes) is not int or not 1 <= max_bytes <= 8192:
        raise CoreError('MEDIA_SEND_BYTE_BOUND')
    row = MemoryService(store).read(selection.source_memory_id)
    if candidate(row) != selection:
        raise CoreError('MEDIA_SELECTION_SOURCE_MISMATCH')
    observation_id = current_image_observation(store, selection.source_memory_id, scope=row['scope'])
    if observation_id is None:
        raise CoreError('MEDIA_OBSERVATION_NOT_CURRENT')
    handle = cache.resolve(source_ref=selection.source_memory_id, sha256=selection.content_sha256)
    if not 1 <= handle.size <= max_bytes:
        raise CoreError('MEDIA_SEND_BYTE_BOUND')
    data = cache.read(handle, length=max_bytes)
    if len(data) != handle.size or hashlib.sha256(data).hexdigest() != selection.content_sha256:
        raise CoreError('MEDIA_CACHE_CONTENT_MISMATCH')
    # Recheck source at the end of the read, including owner consent safe point.
    if candidate(MemoryService(store).read(selection.source_memory_id)) != selection:
        raise CoreError('MEDIA_SELECTION_SOURCE_MISMATCH')
    after = current_image_observation(store, selection.source_memory_id, scope=row['scope'])
    if after is None:
        raise CoreError('MEDIA_OBSERVATION_NOT_CURRENT')
    if after != observation_id:
        raise CoreError('MEDIA_SELECTION_SOURCE_MISMATCH')
    return data
