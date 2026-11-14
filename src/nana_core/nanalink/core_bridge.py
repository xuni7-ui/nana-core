"""Minimal compatibility around original platform work; no new Core contract."""
import re
from dataclasses import dataclass
from .contracts import Event, OperationReceipt, Outcome
from ..contracts import CoreError


@dataclass(frozen=True)
class ChannelRoute:
    account_key: str
    channel_id: str
    conversation_id: str
    sender_id: str
    privacy: str
    conversation_kind: str


def receipt_from_core(operation_id, value):
    """Only original independent Verify SUCCEEDED attests an external effect."""
    state = value.get('delivery', value.get('state', 'UNKNOWN'))
    action = value.get('action_id')
    if state == 'SUCCEEDED' and value.get('external_delivery') is True:
        outcome, reason = Outcome.CONFIRMED_SUCCESS, 'ORIGINAL_KERNEL_VERIFIED'
    elif state in {'FAILED', 'FAILED_EFFECT', 'NOT_APPLIED', 'REJECTED', 'BLOCKED_MANAGER'}:
        outcome, reason = Outcome.CONFIRMED_FAILURE, state
    elif state in {'CANCELLED', 'NO_SOCIAL_DISPATCH_REPLY_NOT_REPLAYED', 'C_SILENCE_OR_REPLY_UNAVAILABLE',
                   'NOT_AUTHORIZED_OR_NO_MODEL_WORDING'}:
        outcome, reason = Outcome.CANCELLED, 'ORIGINAL_ACTION_CANCELLED'
    else:
        # C silence/source review is not a successful SEND. Preserve an honest
        # UNKNOWN social outcome even when input processing itself succeeded.
        outcome = Outcome.UNKNOWN
        reason = state if type(state) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}', state) else 'CORE_RESULT_UNKNOWN'
    return OperationReceipt(operation_id=operation_id, outcome=outcome, reason=reason,
                            action_id=action, source_key=value.get('source_key'),
                            external_delivery=outcome == Outcome.CONFIRMED_SUCCESS)


class CoreBridge:
    """Call on the ORIGINAL owner thread/safe point; never in a connector thread.

    Both QQ and Bilibili use the same envelope and map to existing workflows.
    routes are host configuration, never selected by untrusted nicknames/text.
    """
    def __init__(self, platform_runtime, routes):
        if len(routes) > 64 or len({(r.account_key, r.conversation_id, r.sender_id) for r in routes}) != len(routes):
            raise CoreError('NANALINK_ROUTE_BOUND_OR_DUPLICATE')
        self.platforms, self.routes = platform_runtime, tuple(routes)

    def receive(self, event: Event):
        matches = [r for r in self.routes if r.account_key == event.account.key
                   and r.conversation_id == event.conversation_id and r.sender_id == event.sender_id
                   and r.privacy == event.privacy and r.conversation_kind == event.conversation_kind]
        if len(matches) != 1:
            raise CoreError('NANALINK_SOURCE_ROUTE_UNBOUND')
        supported = {'message.created'}
        if event.account.platform == 'bilibili':
            supported.update({'notification.reply', 'notification.at'})
        if event.kind not in supported or not event.message_id:
            return OperationReceipt(operation_id=event.key, outcome=Outcome.UNSUPPORTED,
                                    reason='CORE_EVENT_CAPABILITY_UNAVAILABLE')
        callback = {'qq': self.platforms.qq, 'bilibili': self.platforms.bilibili}.get(event.account.platform)
        if callback is None:
            return OperationReceipt(operation_id=event.key, outcome=Outcome.UNSUPPORTED,
                                    reason='CORE_PLATFORM_CAPABILITY_UNAVAILABLE')
        # Raw segments are NOT trusted as authoritative input. Original ingress
        # independently fetches and validates account/peer/content and consent.
        return receipt_from_core(event.key, callback(matches[0].channel_id, event.message_id))


    def receipt(self, action_id):
        """Query the existing authoritative action, never repeat its dispatch."""
        store = self.platforms.app.runtime.store
        row = store.one('actions', action_id)
        if row is None:
            raise CoreError('NANALINK_RECEIPT_NOT_FOUND')
        return receipt_from_core(action_id, {'delivery': row['state'], 'action_id': action_id,
                                 'external_delivery': row['state'] == 'SUCCEEDED'})
