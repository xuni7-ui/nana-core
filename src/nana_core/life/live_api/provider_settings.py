"""Explicit host-local provider configuration and credential transitions.

The host opts in independently of Subject relationship or Manager rules. This
updates host configuration or its opted-in vault, not live authorization, budget
or identity. Credential values never enter Subject data or receipt payloads.
"""

from ...continuity.provider_config import ProviderCommand, ProviderConfigService, ProviderConfigurationAuthority
from ...contracts import CoreError
from .contracts import WriteRequest, Role, ApiError
from pydantic import Field, model_validator, field_validator
from typing import Literal
from urllib.parse import urlsplit
from ..config import load_config, update_config


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


class ProviderRuntimeBudgetRequest(WriteRequest):
    provider_profile_id: str = Field(min_length=1,max_length=128)
    profile_revision: int = Field(ge=1)
    configuration_revision: int = Field(ge=1)
    calls_per_day: int = Field(ge=1,le=128)
    calls_per_hour: int = Field(ge=1,le=128)
    per_provider_calls_per_day: int = Field(ge=1,le=128)
    output_tokens: int = Field(ge=64,le=4096)
    context_tokens: int = Field(ge=1024,le=65536)
    per_call_reserved_cost_micro: int = Field(ge=1,le=100000)
    consent: Literal[True]

    @field_validator('consent',mode='before')
    @classmethod
    def explicit_runtime_consent(cls,value):
        if value is not True:raise ValueError('explicit model runtime consent required')
        return value


def runtime_configuration_allowed(service):
    return (service.allow_provider_configuration is True
        and service.allow_provider_runtime_budget is True
        and service.supervisor.provider_live_authorized is True)


def runtime_status(service,principal):
    principal.require(Role.HOST_ADMIN)
    service.supervisor.verify_binding()
    config=load_config(service.supervisor.home)
    try:
        providers=ProviderConfigService(service.supervisor.home/'providers.json',ProviderConfigurationAuthority()).load().providers
    except CoreError as exc:
        if exc.code!='PROVIDER_CONFIG_UNAVAILABLE':raise
        providers=()
    from ..readiness import budget_limits
    return service.envelope({'configuration_revision':config.revision,
        'can_configure':runtime_configuration_allowed(service),
        'provider_hosts':list(config.provider_hosts),'remote_privacy':list(config.remote_privacy),
        'limits':budget_limits(config),'output_tokens':config.provider_output_tokens,'context_tokens':config.provider_context_tokens,
        'profiles':[{'provider_profile_id':p.provider_profile_id,'profile_revision':p.revision,
            'display_name':p.display_name,'host':urlsplit(p.base_url).hostname,
            'enabled':p.enabled,'locality':p.locality,'protocol':p.protocol,
            'per_call_reserved_cost_micro':p.default_cost_ceiling} for p in providers],
        'network_calls':0,'credential_resolved':False,'live_model_test':'NOT_RUN',
        'budget_accounting':'CONSERVATIVE_RESERVATIONS_NOT_PROVIDER_BILLING',
        'runtime_rebind':'EXPLICIT_RESTART_REQUIRED','existing_mission_caps_preserved':True},principal=principal)


def configure_runtime(service,principal,body):
    principal.require(Role.HOST_ADMIN)
    if not runtime_configuration_allowed(service):
        raise ApiError('PROVIDER_RUNTIME_CONFIGURATION_DISABLED',403)

    def selected_profile():
        document=ProviderConfigService(service.supervisor.home/'providers.json',ProviderConfigurationAuthority()).load()
        profile=next((p for p in document.providers if p.provider_profile_id==body.provider_profile_id),None)
        if profile is None or profile.revision!=body.profile_revision:
            raise ApiError('PROVIDER_CONFIG_REVISION_CONFLICT',409)
        if not profile.enabled or profile.locality!='REMOTE' or profile.protocol!='OPENAI_COMPATIBLE_CHAT':
            raise ApiError('PROVIDER_RUNTIME_PROFILE_UNSUPPORTED',409)
        return profile

    def before():
        if load_config(service.supervisor.home).revision!=body.configuration_revision:
            raise ApiError('LIFE_CONFIG_REVISION_CONFLICT',409)
        selected_profile()

    def call():
        profile=selected_profile();host=urlsplit(profile.base_url).hostname
        current=load_config(service.supervisor.home)
        updated=current.model_copy(update={'revision':current.revision+1,
            'provider_hosts':tuple(dict.fromkeys((*current.provider_hosts,host))),
            'remote_privacy':tuple(dict.fromkeys((*current.remote_privacy,'PUBLIC','PROJECT'))),
            'provider_calls_per_day':body.calls_per_day,'provider_calls_per_hour':body.calls_per_hour,
            'per_provider_calls_per_day':body.per_provider_calls_per_day,
            'provider_output_tokens':body.output_tokens,'provider_context_tokens':body.context_tokens,
            'provider_cost_ceiling_micro':body.per_call_reserved_cost_micro})
        # Only original host settings CAS; no Store write, key lookup, network
        # operation or new live launch. Existing total mission caps stay intact.
        update_config(service.supervisor.home,updated,expected_revision=body.configuration_revision)
        return {'configuration_revision':updated.revision,'provider_profile_id':profile.provider_profile_id,
            'profile_revision':profile.revision,'provider_host':host,'network_calls':0,'credential_resolved':False,
            'runtime_applied':False,'restart_required':True,'subject_history_changed':False,
            'existing_mission_caps_preserved':True,'live_model_test':'NOT_RUN',
            'budget_scope':'HOST_GLOBAL_LIMITS_WITH_EXISTING_ROUTE_PROFILE_INTERSECTION',
            'budget_accounting':'CONSERVATIVE_RESERVATIONS_NOT_PROVIDER_BILLING'}

    try:
        return service._call(principal,body,'PROVIDER_RUNTIME_CONFIGURATION',Role.HOST_ADMIN,call,
            lambda row:isinstance(row,dict) and row.get('configuration_revision') is not None,before)
    except CoreError as exc:
        raise ApiError(exc.code,409) from None
