"""Optional host-local configuration transition; never resolves credentials.

The host opts in independently of Subject relationship or Manager rules. This
updates the existing CAS document only, not live authorization, budget or identity.
"""

from ...continuity.provider_config import ProviderCommand, ProviderConfigService, ProviderConfigurationAuthority
from ...contracts import CoreError
from .contracts import WriteRequest, Role, ApiError


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
