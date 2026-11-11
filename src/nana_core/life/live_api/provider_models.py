"""Explicit model-catalog reads with host-bound credentials; no inference.

Registered OpenAI-compatible and native Anthropic catalogs are supported. A model in
the remote catalog is not a qualified capability or a routing configuration.
No credentials, remote bodies or catalog text enter Subject memory or logs.
"""

import json
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from ...continuity.provider_config import ProviderConfigService, ProviderConfigurationAuthority
from ...continuity.privacy import _json_object
from ...continuity.world_loop.cognition import _NoRedirect
from ...contracts import CoreError
from ..config import load_config
from .contracts import ApiError, Role

MODEL_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}')


def read_catalog(profile, credential):
    """One bounded HTTPS GET, TLS verified, redirects forbidden, no retries."""
    native=profile.protocol=='ANTHROPIC'
    if profile.protocol not in {'OPENAI_COMPATIBLE_CHAT','ANTHROPIC'}:
        raise ApiError('PROVIDER_CATALOG_PROTOCOL_UNSUPPORTED',409)
    headers={'Accept':'application/json'}
    if native:
        from ...continuity.world_loop.anthropic import API_VERSION
        headers.update({'x-api-key':credential,'anthropic-version':API_VERSION})
    else:headers['Authorization']='Bearer '+credential
    request = urllib.request.Request(profile.base_url.rstrip('/')+'/models', headers=headers)
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=10) as response:
            if response.status != 200 or response.headers.get_content_type() != 'application/json':
                raise ApiError('PROVIDER_CATALOG_FORMAT', 502)
            raw = response.read(262145)
            if len(raw)>262144:
                raise ApiError('PROVIDER_CATALOG_BOUND', 502)
        value = json.loads(raw, object_pairs_hook=_json_object)
        rows = value.get('data') if type(value) is dict else None
        if type(rows) is not list or len(rows)>2048:
            raise ApiError('PROVIDER_CATALOG_FORMAT', 502)
        ids = set()
        for row in rows:
            model_id = row.get('id') if type(row) is dict else None
            if type(model_id) is not str or not MODEL_ID.fullmatch(model_id) or credential in model_id:
                raise ApiError('PROVIDER_CATALOG_MODEL_INVALID', 502)
            ids.add(model_id)
        has_more=value.get('has_more',False)
        if native and type(has_more) is not bool:
            raise ApiError('PROVIDER_CATALOG_FORMAT',502)
        return {'models': sorted(ids)[:256], 'truncated': len(ids)>256 or (native and has_more)}
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()  # Never include untrusted upstream bodies or request headers.
        raise ApiError('PROVIDER_CATALOG_AUTH' if status in {401,403} else 'PROVIDER_CATALOG_HTTP', 502) from None
    except (OSError, ValueError, TypeError, RecursionError):
        raise ApiError('PROVIDER_CATALOG_UNAVAILABLE', 502) from None


def discover(service, principal, provider_id, revision):
    principal.require(Role.HOST_ADMIN)
    if not service.allow_provider_configuration or service.credential_resolver is None:
        raise ApiError('PROVIDER_CONFIGURATION_DISABLED', 403)
    config_service = ProviderConfigService(service.supervisor.home/'providers.json', ProviderConfigurationAuthority())
    try:
        config = config_service.load()
        profile = next((p for p in config.providers if p.provider_profile_id==provider_id), None)
        if profile is None or profile.revision!=revision:
            raise ApiError('PROVIDER_CONFIG_REVISION_CONFLICT', 409)
        if not profile.enabled or profile.protocol not in {'OPENAI_COMPATIBLE_CHAT','ANTHROPIC'} or profile.locality!='REMOTE':
            raise ApiError('PROVIDER_CATALOG_PROTOCOL_UNSUPPORTED', 409)
        host = urlsplit(profile.base_url).hostname
        if host not in load_config(service.supervisor.home).provider_hosts:
            raise ApiError('PROVIDER_HOST_NOT_AUTHORIZED', 403)
        if not profile.secret_ref:
            raise ApiError('EXPLICIT_SECRET_REFERENCE_REQUIRED', 409)
        with service.read_lock:
            now = time.monotonic()
            if now < service.provider_catalog_after:
                raise ApiError('PROVIDER_CATALOG_WAIT', 429)
            # Throttle explicit reads without blocking Core/normal conversation.
            service.provider_catalog_after = now+10
        secret = service.credential_resolver.resolve(profile.secret_ref)
        try:
            result = read_catalog(profile, secret.reveal_for_header())
        finally:
            secret.clear()
        if config_service.load().revision!=config.revision:
            raise ApiError('PROVIDER_CONFIG_REVISION_CONFLICT', 409)
        return service.envelope({**result, 'provider_profile_id':provider_id,
            'profile_revision':revision, 'source':'PROVIDER_CATALOG',
            'qualification':'NOT_ESTABLISHED', 'inference_calls':0,
            'configuration_changed':False}, principal=principal)
    except CoreError as exc:
        raise ApiError(exc.code, 409) from None
