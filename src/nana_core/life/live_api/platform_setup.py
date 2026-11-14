"""Prepare disabled platform channels from the phone using existing config CAS.

No login, account I/O, read permission, activation, Grant or send authorization.
Those remain original explicit host/account gates. No second configuration Store.
"""
from typing import Literal
from pydantic import Field, model_validator
from ...contracts import CoreError
from ...storage import digest
from ..config import load_config, update_config
from ..surfaces import SurfaceBinding
from ..platform_runtime import QQChannelBinding
from ..bilibili_runtime import BilibiliChannelBinding
from .contracts import WriteRequest, Role, ApiError


class PlatformSetupRequest(WriteRequest):
    method: Literal['qq.onebot', 'bilibili.account']
    account_id: str = Field(pattern=r'^[0-9]{1,20}$')
    peer_id: str = Field(pattern=r'^[0-9]{1,20}$')
    sender_id: str = Field(pattern=r'^[0-9]{1,20}$')
    kind: Literal['private', 'group', 'dm', 'comment']
    endpoint: str = Field(default='http://127.0.0.1:18790', max_length=256)
    configuration_revision: int = Field(ge=1)

    @model_validator(mode='after')
    def compatible(self):
        from ...nanalink.onebot import safe_endpoint
        if self.method == 'qq.onebot':
            if self.kind not in {'private', 'group'} or self.kind == 'private' and self.sender_id != self.peer_id:
                raise ValueError('QQ peer binding')
            safe_endpoint(self.endpoint, schemes=('http', 'https'))
            from urllib.parse import urlsplit
            if urlsplit(self.endpoint).path not in {'', '/'}:
                raise ValueError('OneBot origin required')
        elif self.kind not in {'dm', 'comment'} or min(int(self.account_id), int(self.peer_id), int(self.sender_id)) < 1:
            raise ValueError('Bilibili peer binding')
        elif self.kind == 'dm' and self.peer_id != self.sender_id:
            raise ValueError('private peer binding')
        return self


def setup(service, principal, body):
    principal.require(Role.HOST_ADMIN)
    if not service.allow_provider_configuration:
        raise ApiError('HOST_CONFIGURATION_DISABLED', 403)
    channel_id = 'link.' + digest([body.method, body.account_id, body.kind, body.peer_id, body.sender_id])[:24]
    binding_id = 'nanalink.' + channel_id

    def before():
        current = load_config(service.supervisor.home)
        if current.revision != body.configuration_revision:
            raise ApiError('PLATFORM_CONFIG_REVISION_CONFLICT', 409)
        if len(current.surface_bindings) >= 16:
            raise ApiError('PLATFORM_BINDING_CAPACITY', 409)
        channels = current.qq_channels if body.method == 'qq.onebot' else current.bilibili_channels
        if len(channels) >= 16 or any(c.channel_id == channel_id for c in channels):
            raise ApiError('PLATFORM_CHANNEL_ALREADY_PREPARED_OR_CAPACITY', 409)

    def call():
        current = load_config(service.supervisor.home)
        privacy = 'PUBLIC' if body.kind == 'comment' else 'PERSONAL'
        binding = SurfaceBinding(binding_id=binding_id, platform=body.method,
                   surface='chat.' + body.kind, adapter=body.method,
                   entity_id=service.binding.entity_id, scope=service.binding.scope,
                   mode='PLATFORM_ADAPTER_NO_SEND', permitted_privacy=(privacy,))
        if body.method == 'qq.onebot':
            channel = QQChannelBinding(channel_id=channel_id, binding_id=binding_id, endpoint=body.endpoint,
                       account_id=body.account_id, sender_id=body.sender_id, target_id=body.peer_id,
                       target_kind=body.kind, privacy_class=privacy,
                       credential_ref='nanalink.qq.' + body.account_id)
            field = 'qq_channels'
        else:
            channel = BilibiliChannelBinding(channel_id=channel_id, binding_id=binding_id, kind=body.kind,
                       account_id=int(body.account_id), sender_id=int(body.sender_id), target_id=int(body.peer_id),
                       cookie_ref='nanalink.bili.cookie.' + body.account_id,
                       csrf_ref='nanalink.bili.csrf.' + body.account_id)
            field = 'bilibili_channels'
        updated = current.model_copy(update={'revision': current.revision + 1,
                         'surface_bindings': (*current.surface_bindings, binding),
                         field: (*getattr(current, field), channel)})
        update_config(service.supervisor.home, updated, expected_revision=body.configuration_revision)
        return {'channel_id': channel_id, 'configuration_revision': updated.revision,
                'state': 'PREPARED_DISABLED_PENDING_ACCOUNT_AUTHORIZATION', 'enabled': False,
                'read_authorized': False, 'send_authorized': False, 'network_calls': 0,
                'grants_created': False, 'restart_required': True}

    try:
        return service._call(principal, body, 'PLATFORM_SETUP', Role.HOST_ADMIN, call,
                             lambda result: isinstance(result, dict) and result.get('enabled') is False, before)
    except CoreError as exc:
        raise ApiError(exc.code, 409) from None
