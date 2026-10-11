"""Normalize an operator-captured AstrBot event without importing AstrBot.

get_sender_id/unified_msg_origin linkage follows saved conversation_flow.py.
Message ids, timestamp and attachment metadata must be supplied by the host hook;
we do not invent them or perform attachment/network reads.
"""
from ..contracts import Observation
from ..storage import canonical, digest
from .contracts import HostEvent

class AstrBotObservationAdapter:
    def adapt(self, event):
        event = HostEvent.model_validate(event.model_dump())
        return Observation(source_namespace='host.'+digest([event.host_instance,event.platform]),
            object_id=digest([event.conversation_id, event.event_id]), revision=event.revision,
            channel=event.channel, kind='unrelated', occurred_at=event.timestamp,
            raw_text=canonical({'host_event': event.model_dump(mode='json'),
                'trust': 'UNTRUSTED_HOST_DATA', 'attachments_fetched': False}))
    def ingest(self, store, event):
        return store.ingest(self.adapt(event))
