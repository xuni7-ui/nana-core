"""Explicit model-catalog reads with host-bound credentials; no inference.

Registered OpenAI-compatible and native Anthropic catalogs are supported. A model in
the remote catalog is not a qualified capability or a routing configuration.
No credentials, remote bodies or catalog text enter Subject memory or logs.
"""

import json
import math
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlencode

from ...continuity.provider_config import ProviderConfigService, ProviderConfigurationAuthority
from ...continuity.privacy import _json_object
from ...continuity.world_loop.cognition import _NoRedirect
from ...contracts import CoreError
from ..config import load_config
from .contracts import ApiError, Role

MODEL_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}')
PAGE_LIMIT = 256


def _catalog_result(ids, truncated, cursor=None):
    result = {'models': sorted(ids)[:PAGE_LIMIT], 'truncated': truncated}
    if truncated and cursor is not None:
        result['next_after_id'] = cursor
    return result


def read_catalog(profile, credential, *, after_id=None):
    """Bounded explicit catalog GETs, never inference or automatic retries.

    Native Anthropic pagination stays on the configured URL and shares a ten
    second opportunity window, eight-page/256KiB envelope and 256 visible IDs.
    Missing/invalid/repeated cursors return partial truth. A validated cursor at
    an exhausted bound permits a later explicit read, never an automatic retry.
    """
    native=profile.protocol=='ANTHROPIC'
    if profile.protocol not in {'OPENAI_COMPATIBLE_CHAT','ANTHROPIC'}:
        raise ApiError('PROVIDER_CATALOG_PROTOCOL_UNSUPPORTED',409)
    if after_id is not None and (not native or type(after_id) is not str
            or not MODEL_ID.fullmatch(after_id) or credential in after_id):
        raise ApiError('PROVIDER_CATALOG_QUERY_REQUIRED',400)
    headers={'Accept':'application/json'}
    if native:
        from ...continuity.world_loop.anthropic import API_VERSION
        headers.update({'x-api-key':credential,'anthropic-version':API_VERSION})
    else:headers['Authorization']='Bearer '+credential
    base=profile.base_url.rstrip('/')+'/models'
    opener=urllib.request.build_opener(_NoRedirect())
    deadline=time.monotonic()+10
    ids,seen_cursors=set(),set() if after_id is None else {after_id}
    total_bytes=0;cursor=after_id
    try:
        for page in range(8):
            remaining=10 if page==0 else deadline-time.monotonic()
            if remaining<=0:return _catalog_result(ids,True,cursor)
            # Asking for remaining capacity prevents a valid upstream page from
            # advancing past IDs that this response cannot display.
            limit=PAGE_LIMIT-len(ids)
            query={'limit':str(limit)}
            if cursor is not None:query['after_id']=cursor
            url=base+'?'+urlencode(query) if native else base
            request=urllib.request.Request(url,headers=headers)
            with opener.open(request,timeout=remaining) as response:
                if response.status!=200 or response.headers.get_content_type()!='application/json':
                    raise ApiError('PROVIDER_CATALOG_FORMAT',502)
                raw=response.read(262145-total_bytes)
                total_bytes+=len(raw)
                if total_bytes>262144:raise ApiError('PROVIDER_CATALOG_BOUND',502)
            value=json.loads(raw,object_pairs_hook=_json_object)
            rows=value.get('data') if type(value) is dict else None
            if type(rows) is not list or len(rows)>2048:raise ApiError('PROVIDER_CATALOG_FORMAT',502)
            for row in rows:
                model_id=row.get('id') if type(row) is dict else None
                if type(model_id) is not str or not MODEL_ID.fullmatch(model_id) or credential in model_id:
                    raise ApiError('PROVIDER_CATALOG_MODEL_INVALID',502)
                ids.add(model_id)
            has_more=value.get('has_more',False)
            if not native:
                # Compatible endpoints have no universal cursor protocol.
                return _catalog_result(ids,len(ids)>PAGE_LIMIT or has_more is True)
            if type(has_more) is not bool:raise ApiError('PROVIDER_CATALOG_FORMAT',502)
            if len(rows)>limit:
                # Nonconforming upstream ignored the requested limit. Preserve
                # A's bounded partial result, without inventing a safe cursor.
                return _catalog_result(ids,True)
            if not has_more:return _catalog_result(ids,len(ids)>PAGE_LIMIT)
            next_cursor=value.get('last_id')
            if (type(next_cursor) is not str or not MODEL_ID.fullmatch(next_cursor) or credential in next_cursor
                    or not rows or next_cursor!=rows[-1]['id'] or next_cursor in seen_cursors):
                return _catalog_result(ids,True)
            if len(ids)>=PAGE_LIMIT or total_bytes>=262144 or page==7:
                return _catalog_result(ids,True,next_cursor)
            # A server-provided cursor is data, never a URL or a new credential
            # destination. It may advance one page, never retry an old page.
            seen_cursors.add(next_cursor);cursor=next_cursor
        return _catalog_result(ids,True)
    except urllib.error.HTTPError as exc:
        status=exc.code
        exc.close()
        raise ApiError('PROVIDER_CATALOG_AUTH' if status in {401,403} else 'PROVIDER_CATALOG_HTTP',502) from None
    except (OSError,ValueError,TypeError,RecursionError):
        raise ApiError('PROVIDER_CATALOG_UNAVAILABLE',502) from None


def discover(service, principal, provider_id, revision, *, after_id=None):
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
        if after_id is not None and profile.protocol != 'ANTHROPIC':
            raise ApiError('PROVIDER_CATALOG_PROTOCOL_UNSUPPORTED',409)
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
            value = secret.reveal_for_header()
            result = read_catalog(profile,value) if after_id is None else read_catalog(profile,value,after_id=after_id)
        finally:
            secret.clear()
        if config_service.load().revision!=config.revision:
            raise ApiError('PROVIDER_CONFIG_REVISION_CONFLICT', 409)
        return service.envelope({**result, 'provider_profile_id':provider_id,
            'profile_revision':revision, 'source':'PROVIDER_CATALOG',
            'retry_after_ms':min(10000, math.ceil(max(0,service.provider_catalog_after-time.monotonic())*1000)),
            'qualification':'NOT_ESTABLISHED', 'inference_calls':0,
            'configuration_changed':False}, principal=principal)
    except CoreError as exc:
        raise ApiError(exc.code, 409) from None
