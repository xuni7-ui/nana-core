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
    if (row.get('authority')!='DIRECT' or row.get('epistemic_kind')!='OBSERVATION'
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
