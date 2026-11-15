"""Original host-admin ledger controls a bound sidecar's approved catalog."""
from typing import Literal
from pydantic import Field
from ...contracts import CoreError
from ..config import load_config
from .contracts import WriteRequest, Role, ApiError


class AdapterCommandRequest(WriteRequest):
    channel_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    operation: Literal['INSTALL','UNINSTALL','ENABLE','DISABLE','UPGRADE','ROLLBACK']
    version: str | None = Field(default=None,pattern=r'^[0-9]+\.[0-9]+\.[0-9]+$')
    management_revision: int = Field(ge=1)
    configuration_revision: int = Field(ge=1)


def command(service, principal, body):
    principal.require(Role.HOST_ADMIN)
    if not service.allow_provider_configuration:
        raise ApiError('HOST_CONFIGURATION_DISABLED',403)
    def before():
        config = load_config(service.supervisor.home)
        if config.revision != body.configuration_revision:
            raise ApiError('PLATFORM_CONFIG_REVISION_CONFLICT',409)
        channel = next((c for c in config.qq_channels if c.channel_id == body.channel_id),None)
        if channel is None:
            raise ApiError('PLATFORM_CHANNEL_UNBOUND',409)
        matches = [b for b in service.nanalink_observer.bindings if b.channel_id == channel.channel_id
                   and b.platform == 'qq' and b.account_id == channel.account_id and b.backend == channel.backend]
        if len(matches) != 1:
            raise ApiError('NANALINK_MANAGEMENT_BINDING_REQUIRED',409)
        if body.operation == 'ENABLE' and not channel.read_authorized:
            raise ApiError('PLATFORM_READ_NOT_AUTHORIZED',403)
    def call():
        return service.nanalink_observer.manage('qq',body.channel_id,{
            'operation':body.operation,'version':body.version,'revision':body.management_revision})
    try:
        return service._call(principal,body,'NANALINK_ADAPTER_'+body.operation,Role.HOST_ADMIN,call,
                             lambda result:result.get('state')=='APPLIED',before)
    except CoreError as exc:
        raise ApiError(exc.code,409) from None
