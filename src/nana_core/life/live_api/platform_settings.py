"""Host-admin channel switches, never grants/account credentials/a brain.

Operator binds peers/endpoints/activation separately. Phone can switch existing
bindings with CAS. Core refresh cannot replay UNKNOWN or old incoming messages.
"""

from typing import Literal
from pydantic import Field
from ...contracts import CoreError
from ..config import load_config, update_config
from ..control import request
from .contracts import WriteRequest, Role, ApiError


class PlatformConfigurationRequest(WriteRequest):
    platform: Literal["qq", "bilibili"]
    channel_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    enabled: bool
    configuration_revision: int = Field(ge=1)


def status(service, principal):
    principal.require(Role.READER)
    with service.read_lock:
        service.supervisor.verify_binding()
        result = request(service.supervisor.home, {"operation": "platform-status"}, timeout=2)
        if result.get("ok") is not True:
            raise ApiError("PLATFORM_OWNER_UNAVAILABLE", 503)
        value = result["result"]
        current = load_config(service.supervisor.home)
        value['configuration_revision'] = current.revision
        existing = {(r['platform'], r['channel_id']) for r in value['channels']}
        for platform, channels in (('qq', current.qq_channels), ('bilibili', current.bilibili_channels)):
            for channel in channels:
                if (platform, channel.channel_id) not in existing:
                    value['channels'].append({'platform': platform, 'channel_id': channel.channel_id,
                        'enabled': False, 'read_authorized': False, 'send_configured': False,
                        'secret_state': 'MISSING', 'state': 'PENDING_OWNER_RESTART', 'grants_created': False})
        for row in value['channels']:
            items = current.qq_channels if row['platform'] == 'qq' else current.bilibili_channels
            channel = next((c for c in items if c.channel_id == row['channel_id']), None)
            if channel is not None:
                row['account_label'] = '账号尾号 ' + str(channel.account_id)[-4:]
                row['conversation_kind'] = channel.target_kind if row['platform'] == 'qq' else channel.kind
        value["event_ingress"] = service.platform_events.view()
        observer = getattr(service, "nanalink_observer", None)
        if observer is not None and observer.bindings:
            value["nanalink"] = observer.view()
        if Role.HOST_ADMIN in principal.roles and service.credential_resolver is not None:
            meta=service.credential_resolver.metadata()
            value['vault_revision']=meta.get('revision')
            value['vault_persistent']=bool(getattr(service.credential_resolver,'persistent',False))
        return service.envelope(value)


def configure(service, principal, body):
    principal.require(Role.HOST_ADMIN)
    if not service.allow_provider_configuration:
        raise ApiError("HOST_CONFIGURATION_DISABLED", 403)

    def before():
        current = load_config(service.supervisor.home)
        if current.revision != body.configuration_revision:
            raise ApiError("PLATFORM_CONFIG_REVISION_CONFLICT", 409)
        items = current.qq_channels if body.platform == "qq" else current.bilibili_channels
        if not any(c.channel_id == body.channel_id for c in items):
            raise ApiError("PLATFORM_CHANNEL_UNBOUND", 409)
        if any(c.channel_id == body.channel_id and body.enabled and not c.read_authorized for c in items):
            raise ApiError("PLATFORM_READ_NOT_AUTHORIZED", 403)

    def call():
        current = load_config(service.supervisor.home)
        field = "qq_channels" if body.platform == "qq" else "bilibili_channels"
        items = getattr(current, field)
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                field: tuple(
                    c.model_copy(update={"enabled": body.enabled}) if c.channel_id == body.channel_id else c
                    for c in items
                ),
            }
        )
        update_config(service.supervisor.home, updated, expected_revision=body.configuration_revision)
        refreshed = request(service.supervisor.home, {"operation": "platform-refresh"}, timeout=2)
        return {
            "configuration_revision": updated.revision,
            "enabled": body.enabled,
            "runtime_applied": refreshed.get("ok") is True,
            "restart_required": refreshed.get("ok") is not True,
            "grants_created": False,
            "network_calls": 0,
            "unknown_replayed": False,
        }

    try:
        return service._call(
            principal,
            body,
            "PLATFORM_CONFIGURATION",
            Role.HOST_ADMIN,
            call,
            lambda row: isinstance(row, dict) and row.get("configuration_revision") is not None,
            before,
        )
    except CoreError as exc:
        raise ApiError(exc.code, 409) from None
