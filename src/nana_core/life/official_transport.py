"""Official QQ compatibility over the same account-bound HTTP/Kernel path."""
import re
from .platform_bridge import OneBotHTTPTransport
from ..contracts import CoreError, Verification
from ..storage import digest


def qq_event_id(transport, message_id):
    return 'qqo:' + digest(str(message_id)) if type(transport) is OfficialQQHTTPTransport else 'qq:' + str(message_id)


class OfficialQQHTTPTransport(OneBotHTTPTransport):
    platform = 'qq.official'

    def get_message(self, message_id):
        if not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', str(message_id)):
            raise CoreError('QQ_OFFICIAL_MESSAGE_ID_INVALID')
        row = self._call('get_msg', {'message_id': str(message_id)})
        if row.get('message_id') != message_id:
            raise CoreError('QQ_OFFICIAL_MESSAGE_CORRELATION_MISMATCH')
        return row

    def send(self, target_kind, target_id, text, echo):
        if target_kind not in {'private', 'group'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(target_id)):
            raise CoreError('QQ_OFFICIAL_TARGET_INVALID')
        if type(text) is not str or not 1 <= len(text) <= 2048:
            raise CoreError('QQ_OFFICIAL_MESSAGE_BOUND')
        self.account()
        row = self._call('send_' + target_kind + '_msg', {
            'user_id' if target_kind == 'private' else 'group_id': str(target_id),
            'message': [{'type': 'text', 'data': {'text': text}}], 'echo': echo})
        mid = row.get('message_id')
        if not isinstance(mid, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', mid):
            raise CoreError('QQ_OFFICIAL_ACK_UNKNOWN_NO_RETRY')
        return {'message_id': mid, 'target_kind': target_kind, 'target_id': str(target_id),
                'account_id': self.account_id, 'text_digest': digest(text), 'platform_origin': self.realm,
                'platform_ack': True, 'independent_delivery': False}

    def verify_receipt(self, receipt):
        return Verification(verdict='INCONCLUSIVE', evidence={
            'reason': 'QQ_OFFICIAL_C2C_GROUP_READBACK_UNSUPPORTED', 'message_id': receipt['message_id'],
            'platform_ack': True, 'no_retry': True})
