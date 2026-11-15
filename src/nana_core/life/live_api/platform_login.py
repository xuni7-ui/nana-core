"""User-invoked QR login. Tickets and credentials never enter the receipt ledger."""
from typing import Literal
from pydantic import Field, model_validator
from ...contracts import CoreError
from ..config import load_config
from .contracts import WriteRequest, Role, ApiError


class PlatformLoginRequest(WriteRequest):
    action: Literal['BEGIN','POLL','COMMIT','CANCEL']
    channel_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    configuration_revision: int = Field(ge=1)
    session_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{24,64}$', repr=False)
    expected_vault_revision: int | None = Field(default=None, ge=0)
    consent: bool = False

    @model_validator(mode='after')
    def shape(self):
        if (self.action == 'BEGIN') != (self.session_id is None):
            raise ValueError('login session required')
        return self


def command(service, principal, body):
    principal.require(Role.HOST_ADMIN)
    if not service.allow_provider_configuration or not service.allow_platform_login or service.credential_resolver is None:
        raise ApiError('PLATFORM_LOGIN_HOST_OPT_IN_REQUIRED',403)
    with service.write_lock:
        service.supervisor.verify_binding()
        if body.run_generation != service.generation or body.owner_epoch != service.supervisor.status()['owner_epoch']:
            raise ApiError('STALE_RUN_NO_REPLAY',409)
        if body.expected_revision != service.ledger.revision:
            raise ApiError('REVISION_CONFLICT',409)
        config = load_config(service.supervisor.home)
        if config.revision != body.configuration_revision:
            raise ApiError('PLATFORM_CONFIG_REVISION_CONFLICT',409)
        channel = next((c for c in config.bilibili_channels if c.channel_id == body.channel_id),None)
        if channel is None:
            raise ApiError('BILIBILI_LOGIN_CHANNEL_REQUIRED',400)
        owner = (principal.principal_id,principal.generation,principal.kind,principal.device_id)
        broker = service.platform_login
        try:
            if body.action == 'CANCEL':
                result = broker.cancel(body.session_id, owner)
            elif body.action == 'POLL':
                session = broker.session(body.session_id,owner)
                if session['channel'] != channel.channel_id:
                    raise CoreError('NANALINK_LOGIN_CHANNEL_MISMATCH')
                result = broker.poll(body.session_id,owner,channel.account_id)
            else:
                refs = {channel.cookie_ref,channel.csrf_ref}
                if None in refs or len(refs) != 2:
                    raise CoreError('NANALINK_LOGIN_CREDENTIAL_REFS_REQUIRED')
                if any(c.enabled and refs.intersection({c.cookie_ref,c.csrf_ref}) for c in config.bilibili_channels):
                    raise CoreError('NANALINK_LOGIN_PAUSE_SHARED_CHANNELS_FIRST')
                if not body.consent:
                    raise CoreError('NANALINK_LOGIN_EXPLICIT_CONSENT_REQUIRED')
                if body.action == 'BEGIN':
                    result = broker.begin(owner,channel.channel_id)
                else:
                    resolver = service.credential_resolver
                    if resolver.persistent and body.expected_vault_revision is None:
                        raise CoreError('PROVIDER_VAULT_REVISION_REQUIRED')
                    result = broker.commit(body.session_id,owner,channel,resolver,body.expected_vault_revision)
                    result['vault_revision'] = resolver.metadata()['revision']
            return service.envelope(result,principal=principal)
        except CoreError as exc:
            raise ApiError(exc.code,409) from None
        except Exception:
            raise ApiError('NANALINK_LOGIN_RESULT_UNKNOWN_NO_RETRY',503) from None
