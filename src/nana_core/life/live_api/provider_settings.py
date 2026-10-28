"""Optional host-local configuration transition; never resolves credentials.

The host opts in independently of Subject relationship or Manager rules. This
updates the existing CAS document only, not live authorization, budget or identity.
"""

from ...continuity.provider_config import ProviderCommand, ProviderConfigService, ProviderConfigurationAuthority
from ...contracts import CoreError
from .contracts import WriteRequest, Role, ApiError
from pydantic import Field


class CredentialBindingRequest(WriteRequest):
    model_config = {"hide_input_in_errors": True}
    provider_profile_id: str = Field(min_length=1, max_length=128)
    profile_revision: int = Field(ge=1)
    credential: str = Field(min_length=1, max_length=4096, repr=False, exclude=True)


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
        config = ProviderConfigService(service.supervisor.home / "providers.json", authority).load()
        profile = next((p for p in config.providers if p.provider_profile_id == body.provider_profile_id), None)
        if profile is None or profile.revision != body.profile_revision:
            raise ApiError("PROVIDER_CONFIG_REVISION_CONFLICT", 409)
        if profile.locality != "REMOTE" or not profile.secret_ref:
            raise ApiError("EXPLICIT_SECRET_REFERENCE_REQUIRED", 409)
        try:
            service.credential_resolver.bind(profile.secret_ref, body.credential)
        except CoreError as exc:
            raise ApiError(exc.code, 400) from None
        return service.envelope({"state": "BOUND_IN_HOST_MEMORY", "provider_profile_id": profile.provider_profile_id,
                                 "secret_state": "AVAILABLE", "credential_persisted": False,
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
