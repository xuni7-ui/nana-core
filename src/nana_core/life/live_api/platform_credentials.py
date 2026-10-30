"""Native/admin credential binding to existing typed platform references only.

No caller-selected secret reference, plaintext serialization, Grant, live call or
new memory. Revocation disables all channels sharing a reference before changing
the original host vault; its existing FD epoch fence protects active children.
"""

import re
from typing import Literal
from pydantic import Field, model_validator
from ...contracts import CoreError
from ..config import load_config, update_config
from ..control import request
from .contracts import WriteRequest, Role, ApiError


class PlatformCredentialRequest(WriteRequest):
    platform: Literal["qq", "bilibili"]
    channel_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    slot: Literal["AUTH", "COOKIE", "CSRF"]
    action: Literal["BIND", "REVOKE"]
    configuration_revision: int = Field(ge=1)
    expected_vault_revision: int | None = Field(default=None, ge=0)
    credential: str | None = Field(default=None, min_length=1, max_length=4096, repr=False, exclude=True)

    @model_validator(mode="after")
    def exact_shape(self):
        if (self.action == "BIND") != (self.credential is not None):
            raise ValueError("credential action shape")
        if self.platform == "qq" and self.slot != "AUTH" or self.platform == "bilibili" and self.slot == "AUTH":
            raise ValueError("platform credential slot")
        return self


def normalized(value, slot):
    if any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise CoreError("PLATFORM_CREDENTIAL_INVALID")
    if slot == "COOKIE":
        parts = []
        for entry in value.split(";"):
            entry = entry.strip(" ")
            if not entry:
                continue
            key, separator, content = entry.partition("=")
            if not separator or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", key) or " " in content:
                raise CoreError("PLATFORM_COOKIE_INVALID")
            parts.append(entry)
        if not parts:
            raise CoreError("PLATFORM_COOKIE_INVALID")
        value = ";".join(parts)  # Only optional cookie separator whitespace is removed.
    elif slot == "CSRF" and not re.fullmatch(r"[A-Za-z0-9]{16,64}", value):
        raise CoreError("PLATFORM_CSRF_INVALID")
    return value


def _reference(config, body):
    items = config.qq_channels if body.platform == "qq" else config.bilibili_channels
    channel = next((c for c in items if c.channel_id == body.channel_id), None)
    if channel is None:
        raise CoreError("PLATFORM_CHANNEL_UNBOUND")
    reference = (
        channel.credential_ref
        if body.platform == "qq"
        else channel.cookie_ref
        if body.slot == "COOKIE"
        else channel.csrf_ref
    )
    if not reference:
        raise CoreError("PLATFORM_CREDENTIAL_REFERENCE_UNBOUND")
    return reference


def _disable_shared(home, config, reference):
    def used(c, platform):
        return reference == c.credential_ref if platform == "qq" else reference in {c.cookie_ref, c.csrf_ref}

    updated = config.model_copy(
        update={
            "revision": config.revision + 1,
            "qq_channels": tuple(
                c.model_copy(update={"enabled": False}) if used(c, "qq") else c for c in config.qq_channels
            ),
            "bilibili_channels": tuple(
                c.model_copy(update={"enabled": False}) if used(c, "bilibili") else c for c in config.bilibili_channels
            ),
        }
    )
    return update_config(home, updated, expected_revision=config.revision)


def bind(service, principal, body):
    principal.require(Role.HOST_ADMIN)
    if principal.kind != "NATIVE":
        raise ApiError("NATIVE_SECRET_INPUT_REQUIRED", 403)
    resolver = service.credential_resolver
    if not service.allow_provider_configuration or resolver is None:
        raise ApiError("HOST_CONFIGURATION_DISABLED", 403)
    with service.write_lock:
        service.supervisor.verify_binding()
        if body.run_generation != service.generation:
            raise ApiError("STALE_RUN_NO_REPLAY", 409)
        if body.owner_epoch != service.supervisor.status()["owner_epoch"]:
            raise ApiError("STALE_EPOCH", 409)
        if body.expected_revision != service.ledger.revision:
            raise ApiError("REVISION_CONFLICT", 409)
        config = load_config(service.supervisor.home)
        if config.revision != body.configuration_revision:
            raise ApiError("PLATFORM_CONFIG_REVISION_CONFLICT", 409)
        try:
            ref = _reference(config, body)
            persistent = bool(getattr(resolver, "persistent", False))
            kwargs = {"expected_revision": body.expected_vault_revision} if persistent else {}
            if persistent and (
                body.expected_vault_revision is None or resolver.metadata()["revision"] != body.expected_vault_revision
            ):
                raise CoreError("PROVIDER_VAULT_REVISION_CONFLICT")
            if body.action == "BIND":
                resolver.bind(ref, normalized(body.credential, body.slot), **kwargs)
            else:
                config = _disable_shared(service.supervisor.home, config, ref)
                resolver.revoke(ref, **kwargs)
                request(service.supervisor.home, {"operation": "platform-refresh"}, timeout=2)
            return service.envelope(
                {
                    "state": "REVOKED_CHANNELS_DISABLED"
                    if body.action == "REVOKE"
                    else "BOUND_IN_HOST_VAULT"
                    if persistent
                    else "BOUND_IN_HOST_MEMORY",
                    "configuration_revision": config.revision,
                    "vault_revision": resolver.metadata()["revision"],
                    "credential_persisted": persistent and body.action == "BIND",
                    "credential_exposed": False,
                    "runtime_rebind": "EXPLICIT_RESTART_REQUIRED",
                    "network_calls": 0,
                    "grants_created": False,
                }
            )
        except CoreError as exc:
            raise ApiError(exc.code, 409 if "CONFLICT" in exc.code else 400) from None
