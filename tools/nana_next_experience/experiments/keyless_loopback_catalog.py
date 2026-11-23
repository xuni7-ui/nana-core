"""Explicit local catalog experiment; no installed provider or model authority."""
import json
import urllib.error
import urllib.request

from nana_core.continuity.privacy import _json_object
from nana_core.continuity.world_loop.cognition import _NoRedirect
from nana_core.life.live_api.contracts import ApiError
from nana_core.life.live_api.provider_models import MODEL_ID
from tools.nana_next_experience.experiments.keyless_loopback_prototype import validate_loopback_base


def read_keyless_loopback_catalog(base_url, *, explicit_authorized, allowed_bases, timeout=3):
    """Read bounded OpenAI-compatible IDs from a trusted host-owned endpoint.

    Results are unqualified candidates; this makes no inference, persists no
    state, and does not authenticate the process that owns a reusable port.
    The host must authorize the literal address and protect local access.
    """
    validate_loopback_base(base_url,explicit_authorized=explicit_authorized,allowed_bases=allowed_bases)
    if type(timeout) not in (int,float) or not 0 < timeout <= 10:
        raise ValueError('invalid local catalog timeout')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    request=urllib.request.Request(base_url+'/models',headers={'Accept':'application/json'})
    try:
        with opener.open(request,timeout=timeout) as response:
            if response.status!=200 or response.headers.get_content_type()!='application/json':
                raise ApiError('PROVIDER_CATALOG_FORMAT',502)
            raw=response.read(262145)
            if len(raw)>262144:raise ApiError('PROVIDER_CATALOG_BOUND',502)
        value=json.loads(raw,object_pairs_hook=_json_object)
        rows=value.get('data') if type(value) is dict else None
        if type(rows) is not list or len(rows)>2048:raise ApiError('PROVIDER_CATALOG_FORMAT',502)
        ids=set()
        for row in rows:
            model_id=row.get('id') if type(row) is dict else None
            if type(model_id) is not str or not MODEL_ID.fullmatch(model_id):
                raise ApiError('PROVIDER_CATALOG_MODEL_INVALID',502)
            ids.add(model_id)
        return {'models':sorted(ids)[:256],
                'truncated':len(ids)>256 or value.get('has_more',False) is not False,
                'qualification':'NOT_ESTABLISHED','inference_calls':0}
    except urllib.error.HTTPError as exc:
        status=exc.code;exc.close()
        raise ApiError('PROVIDER_CATALOG_AUTH' if status in (401,403) else 'PROVIDER_CATALOG_HTTP',502) from None
    except (OSError,ValueError,TypeError,RecursionError):
        raise ApiError('PROVIDER_CATALOG_UNAVAILABLE',502) from None
