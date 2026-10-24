"""Real anchor replacement/corruption must invalidate warmed read optimizations."""
import os
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import uid
from nana_core.continuity.privacy import _atomic
from tests.continuous_self.conftest import cognitive,evidence
from tests.continuous_self.test_memory import add


def test_external_durable_erasure_invalidates_warmed_anchor(cognitive):
    store,memory,authority=cognitive
    mid=add(memory,evidence(memory,'warm','Synthetic removable source'),'Synthetic removable source')
    assert memory.read(mid)['text']=='Synthetic removable source'
    body=store.privacy.read();source=store.one('memories',mid)['source_evidence_id']
    body['intents'].append({'intent_id':uid(),'memory_ids':[mid],'evidence_ids':[source],'created_at_us':store.clock.utc_now_us()})
    _atomic(store.privacy.path,body) # another trusted process's durable delete intent
    with pytest.raises(CoreError,match='MEMORY_UNAVAILABLE'):memory.read(mid)
    assert store.one('memories',mid)['lifecycle']=='DELETED'


def test_same_size_corruption_with_restored_mtime_cannot_use_validity_cache(cognitive):
    store,memory,authority=cognitive
    mid=add(memory,evidence(memory,'cache','Synthetic readable source'),'Synthetic readable source')
    memory.read(mid)
    anchor=store.privacy.path;old=anchor.read_bytes();stamp=anchor.stat()
    try:
        anchor.write_bytes(b'!'+old[1:])
        os.utime(anchor,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        with pytest.raises(CoreError,match='PRIVACY_ANCHOR_INVALID'):memory.read(mid)
    finally:anchor.write_bytes(old)
    assert memory.read(mid)['text']=='Synthetic readable source'
