import json
import pytest
from nana_core.storage import Store
from nana_core.contracts import CoreError
from nana_core.integration.host_observation import AstrBotObservationAdapter
from nana_core.integration.contracts import HostEvent, Attachment, RuntimeIntegrationContext, ShadowCapabilityPort

def event(**kw):
    return HostEvent(host_instance='synthetic-host',platform='qq',channel='group',sender_id='synthetic-sister',
        event_id=kw.pop('event_id','m1'),conversation_id='synthetic-chat',content='Fictional message',
        raw_content_reference='synthetic://message/m1',**kw)

def test_event_dedup_restart_order_and_source(tmp_path):
    a=AstrBotObservationAdapter(); db=tmp_path/'core.db'
    with Store(db) as s:
        identity=s.identity; e=event(timestamp='2026-10-01T10:00:00Z',reply_to='m0',attachments=(Attachment(kind='image',source_reference='synthetic://image/1'),))
        eid=a.ingest(s,e);assert a.ingest(s,e)==eid
        earlier=a.ingest(s,event(event_id='m0',timestamp='2026-09-30T10:00:00Z'))
        assert s.event(earlier)['occurred_at_us']<s.event(eid)['occurred_at_us']
        assert a.ingest(s,event().model_copy(update={'platform':'bilibili'}))!=eid
        missing=a.ingest(s,event(event_id='missing'));assert s.event(missing)['occurred_at_us'] is None
        raw=json.loads(s.artifact(s.event(eid)['artifact_id']))['host_event'];assert raw['reply_to']=='m0' and raw['event_id']=='m1'
        assert all(json.loads(m['body_json'])['assessment']=='UNASSESSED' for m in s.all('memory_items'))
        assert not s.all('actions') and not s.all('grants')
    with Store(db) as s:
        assert s.identity==identity and a.ingest(s,e)==eid
        with pytest.raises(CoreError,match='SOURCE_KEY_COLLISION'):a.ingest(s,e.model_copy(update={'content':'changed'}))

def test_shadow_contract_cannot_enable_execute():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):RuntimeIntegrationContext(host_instance='s',expected_identity_id='i',external_execute=True)
    with pytest.raises(CoreError,match='SHADOW_BLOCKED'):ShadowCapabilityPort().execute(None)
