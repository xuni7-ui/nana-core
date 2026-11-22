"""Minimal compatibility around original platform work; no new Core contract."""
import re
from dataclasses import dataclass
from .contracts import Event, OperationReceipt, Outcome
from ..contracts import CoreError
from ..life.bilibili_account import bilibili_delivery_status


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
    elif state == 'MEDIA_ACTION_UNSUPPORTED':
        outcome, reason = Outcome.UNSUPPORTED, state
    elif state in {'FAILED', 'FAILED_EFFECT', 'NOT_APPLIED', 'REJECTED', 'BLOCKED_MANAGER'}:
        outcome, reason = Outcome.CONFIRMED_FAILURE, state
    elif state == 'PLATFORM_MESSAGE_PREEXISTED_NO_SEND':
        outcome, reason = Outcome.CANCELLED, state
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
        result = callback(matches[0].channel_id, event.message_id)
        if event.account.platform == 'bilibili' and result.get('delivery') == 'SUCCEEDED':
            try:
                checked = self.receipt(result.get('action_id'))
                source_key = result.get('source_key')
                return OperationReceipt.model_validate({**checked.model_dump(), 'operation_id': event.key,
                    'source_key': source_key if type(source_key) is str and len(source_key) <= 128 else None})
            except (CoreError, AttributeError, TypeError):
                action_id = result.get('action_id')
                return OperationReceipt(operation_id=event.key, outcome=Outcome.UNKNOWN,
                    reason='ORIGINAL_CONFIRMATION_NOT_AVAILABLE',
                    action_id=action_id if type(action_id) is str and 1 <= len(action_id) <= 128 else None)
        return receipt_from_core(event.key, result)


    def receipt(self, action_id):
        """Query the existing authoritative action, never repeat its dispatch."""
        import json
        from .contracts import Account
        from ..continuity.records import RecordService
        store = self.platforms.app.runtime.store
        row = store.one('actions', action_id)
        if row is None:
            raise CoreError('NANALINK_RECEIPT_NOT_FOUND')
        config = self.platforms.app.config
        bound = None
        for route in self.routes:
            for channel in config.qq_channels:
                account = Account(platform='qq', account_id=str(channel.account_id), adapter_id='qq.'+channel.backend)
                if (route.account_key == account.key and route.channel_id == channel.channel_id
                        and route.conversation_kind == channel.target_kind and route.conversation_id == str(channel.target_id)
                        and route.sender_id == str(channel.sender_id) and route.privacy == channel.privacy_class
                        and row['capability'] == 'world.contact' and row['resource'] == 'project://qq/'+channel.channel_id):
                    bound = ('qq', str(channel.account_id), str(channel.target_id))
            for channel in config.bilibili_channels:
                account = Account(platform='bilibili', account_id=str(channel.account_id), adapter_id='bilibili.account')
                if (route.account_key == account.key and route.channel_id == channel.channel_id
                        and route.conversation_id == str(channel.target_id) and route.sender_id == str(channel.sender_id)
                        and route.privacy == ('PERSONAL' if channel.kind == 'dm' else 'PUBLIC')
                        and row['capability'] == 'bilibili.'+channel.kind+'.send'
                        and row['resource'] == 'project://bilibili/'+channel.kind+'/'+str(channel.target_id)):
                    bound = ('bilibili', str(channel.account_id), str(channel.target_id))
        if bound is None:
            raise CoreError('NANALINK_RECEIPT_NOT_FOUND')
        if bound[0] == 'bilibili' and row['state'] == 'SUCCEEDED':
            delivery = bilibili_delivery_status(store, row, bound[1])
            return receipt_from_core(action_id, {'delivery': delivery, 'action_id': action_id,
                                                 'external_delivery': delivery == 'SUCCEEDED'})
        verified = False
        if row['state'] == 'SUCCEEDED':
            try:
                event = store.event(json.loads(row['body_json'])['verification_event_id'])
                data = json.loads(event['data_json'])['data']
                if event['kind'] != 'action.verified' or data['action_id'] != action_id:
                    raise ValueError()
                link = store.db.execute('SELECT record_id FROM continuity_records WHERE payload_artifact_id=?',
                                        (event['artifact_id'],)).fetchone()
                if not link:
                    raise ValueError()
                records = RecordService(store)
                if not records.current_support(link[0]):
                    raise ValueError()
                result = records.read(link[0])['payload']
                evidence = result['evidence']
                verified = (result['verdict'] == 'MATCH' and type(evidence) is dict
                            and evidence.get('independent_readback') is True
                            and evidence.get('account_id') == bound[1] and evidence.get('target_id') == bound[2])
            except (CoreError, ValueError, KeyError, TypeError):
                verified = False
        if row['state'] == 'SUCCEEDED' and not verified:
            return OperationReceipt(operation_id=action_id, outcome=Outcome.UNKNOWN,
                                    reason='ORIGINAL_CONFIRMATION_NOT_AVAILABLE', action_id=action_id)
        return receipt_from_core(action_id, {'delivery': row['state'], 'action_id': action_id,
                                 'external_delivery': verified})
