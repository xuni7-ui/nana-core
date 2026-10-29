"""Explicit host-local provider configuration and credential transitions.

The host opts in independently of Subject relationship or Manager rules. This
updates host configuration or its opted-in vault, not live authorization, budget
or identity. Credential values never enter Subject data or receipt payloads.
"""

from ...continuity.provider_config import ProviderCommand, ProviderConfigService, ProviderConfigurationAuthority
from ...contracts import CoreError
from .contracts import WriteRequest, Role, ApiError
from pydantic import Field, model_validator
from typing import Literal


class CredentialBindingRequest(WriteRequest):
    model_config = {"hide_input_in_errors": True}
    provider_profile_id: str = Field(min_length=1, max_length=128)
    profile_revision: int = Field(ge=1)
    action: Literal["BIND", "REVOKE"] = "BIND"
    expected_vault_revision: int | None = Field(default=None, ge=0)
    credential: str | None = Field(default=None, min_length=1, max_length=4096, repr=False, exclude=True)

    @model_validator(mode="after")
    def action_shape(self):
        if (self.action == "BIND") != (self.credential is not None):
            raise ValueError("credential action shape invalid")
        return self


def credential_status(service, principal):
    principal.require(Role.HOST_ADMIN)
    resolver = service.credential_resolver
    vault = resolver.metadata() if resolver is not None else {"configured": False, "storage": "UNAVAILABLE", "revision": None}
    document = projection(service.supervisor.home)
    authority = ProviderConfigurationAuthority()
    try:
        config = ProviderConfigService(service.supervisor.home / "providers.json", authority).load()
        profiles = [{"provider_profile_id": p.provider_profile_id, "profile_revision": p.revision, "enabled": p.enabled,
                     "secret_state": "UNCONFIGURED" if not p.secret_ref else "AVAILABLE" if resolver and resolver.available(p.secret_ref) else "MISSING"}
                    for p in config.providers]
    except CoreError as exc:
        if exc.code != "PROVIDER_CONFIG_UNAVAILABLE":
            raise
        profiles = []
    return service.envelope({"vault": vault, "profiles": profiles, "configuration_revision": document["revision"],
                             "live_permission_granted": False, "network_calls": 0})


def _disable_shared_profiles(config_service, config, reference, authority):
    affected = []
    for item in config.providers:
        if item.secret_ref == reference:
            affected.append(item.provider_profile_id)
            if item.enabled:
                config = config_service.update(ProviderCommand(operation="DISABLE_PROVIDER", expected_revision=config.revision,
                                                               target_id=item.provider_profile_id), authority)
    return affected


def _mutate_binding(resolver, body, profile, config_service, config, authority):
    persistent = bool(getattr(resolver, "persistent", False))
    if persistent:
        if body.expected_vault_revision is None:
            raise CoreError("PROVIDER_VAULT_REVISION_REQUIRED")
        if resolver.metadata()["revision"] != body.expected_vault_revision:
            raise CoreError("PROVIDER_VAULT_REVISION_CONFLICT")
    kwargs = {"expected_revision": body.expected_vault_revision} if persistent else {}
    if body.action == "REVOKE":
        affected = _disable_shared_profiles(config_service, config, profile.secret_ref, authority)
        resolver.revoke(profile.secret_ref, **kwargs)
    else:
        affected = []
        resolver.bind(profile.secret_ref, body.credential, **kwargs)
    return persistent, affected


def bind_credential(service, principal, body):
    """Native/admin/host opt-in only; value never enters receipts or DTO dumps."""
    principal.require(Role.HOST_ADMIN)
    if principal.kind != "NATIVE":
        raise ApiError("NATIVE_SECRET_INPUT_REQUIRED", 403)
    if not service.allow_provider_configuration or service.credential_resolver is None:
        raise ApiError("PROVIDER_CONFIGURATION_DISABLED", 403)
    with service.write_lock:
        if body.run_generation != service.generation:
            raise ApiError("STALE_RUN_NO_REPLAY", 409)
        if body.owner_epoch != service.supervisor.status()["owner_epoch"]:
            raise ApiError("STALE_EPOCH", 409)
        if body.expected_revision != service.ledger.revision:
            raise ApiError("REVISION_CONFLICT", 409)
        authority = ProviderConfigurationAuthority()
        config_service = ProviderConfigService(service.supervisor.home / "providers.json", authority)
        config = config_service.load()
        profile = next((p for p in config.providers if p.provider_profile_id == body.provider_profile_id), None)
        if profile is None or profile.revision != body.profile_revision:
            raise ApiError("PROVIDER_CONFIG_REVISION_CONFLICT", 409)
        if profile.locality != "REMOTE" or not profile.secret_ref:
            raise ApiError("EXPLICIT_SECRET_REFERENCE_REQUIRED", 409)
        resolver = service.credential_resolver
        try:
            # Fence future selection before revocation. An already dispatched
            # request cannot be cancelled or replayed by changing a vault.
            persistent, affected = _mutate_binding(resolver, body, profile, config_service, config, authority)
        except CoreError as exc:
            raise ApiError(exc.code, 409 if "CONFLICT" in exc.code or exc.code == "PROVIDER_VAULT_REVISION_REQUIRED" else 400) from None
        return service.envelope({"state": "REVOKED_PROVIDER_DISABLED" if body.action == "REVOKE" else "BOUND_IN_HOST_VAULT" if persistent else "BOUND_IN_HOST_MEMORY",
                                 "provider_profile_id": profile.provider_profile_id,
                                 "secret_state": "MISSING" if body.action == "REVOKE" else "AVAILABLE", "credential_persisted": persistent and body.action == "BIND",
                                 "vault": resolver.metadata(), "disabled_provider_profile_ids": affected,
                                 "in_flight_requests_cancelled": False,
                                 "runtime_rebind": "EXPLICIT_RESTART_REQUIRED", "network_calls": 0,
                                 "live_permission_granted": False})


class ProviderConfigurationRequest(WriteRequest):
    command: ProviderCommand


def configure(service, principal, body):
    principal.require(Role.HOST_ADMIN)
    if not service.allow_provider_configuration:
        raise ApiError("PROVIDER_CONFIGURATION_DISABLED", 403)
    authority = ProviderConfigurationAuthority()
    config = ProviderConfigService(service.supervisor.home / "providers.json", authority)

    def before():
        try:
            if config.load().revision != body.command.expected_revision:
                raise ApiError("PROVIDER_CONFIG_REVISION_CONFLICT", 409)
        except CoreError as exc:
            if exc.code == "PROVIDER_CONFIG_UNAVAILABLE" and body.command.expected_revision == 0:
                return  # Explicit command may create host config, never a Subject.
            raise ApiError("PROVIDER_CONFIG_INVALID", 409) from None

    def call():
        config.initialize(authority)
        updated = config.update(body.command, authority)
        # A config change affects future routes only. Runtime ceilings and safe
        # resolver binding remain separate; no call or secret lookup happens here.
        return {
            "configuration_revision": updated.revision,
            "network_calls": 0,
            "live_permission_granted": False,
            "subject_history_changed": False,
            "runtime_rebind": "EXPLICIT_RESTART_OR_EXISTING_RUNTIME_ROUTER_REFRESH",
        }

    return service._call(
        principal, body, "PROVIDER_CONFIGURATION", Role.HOST_ADMIN, call, lambda row: isinstance(row, dict), before
    )


def projection(home):
    """Missing host config is explicit revision0, never initialize on a read."""
    from ..provider import provider_status
    path = home / "providers.json"
    try:
        path.lstat()
    except FileNotFoundError:
        return {"schema_version": 1, "revision": 0, "providers": [], "models": [], "routes": [],
                "configured": False, "storage_class": "HOST_LOCAL_NOT_SUBJECT_MEMORY", "execution_authority": False}
    return provider_status(home)["provider_settings"]
