"""Isolated keyless local transport candidate; never an installed route.

It reuses original OpenAIJSONTransport serialization, parser, timeout and
CognitionSession ledger. The caller is trusted host test code; the production
factory, configuration, deployment policy and credentials are not changed.
"""
import re
from urllib.parse import urlsplit
import urllib.request

from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport,_NoRedirect


class KeylessLoopbackPrototype(OpenAIJSONTransport):
    """Explicit literal IPv4 loopback and exact host-controlled base allowlist.

    This experiment intentionally does not grant inference or bypass the
    original CognitionSession privacy, reservation, ledger or UNKNOWN handling.
    A local HTTP service can see any data sent to it; authorization and service
    identity after port reuse remain host responsibilities. Not production code.
    """
    def __init__(self,base_url,model_id,*,provider_id,explicit_authorized,allowed_bases):
        if (type(base_url) is not str or len(base_url)>256 or explicit_authorized is not True or
                type(allowed_bases) is not tuple or not 1<=len(allowed_bases)<=64 or
                base_url not in allowed_bases or
                any(type(x) is not str or not 1<=len(x)<=256 for x in allowed_bases)):
            raise ValueError('explicit loopback authorization required')
        try:
            url=urlsplit(base_url);port=url.port
            if (url.scheme!='http' or url.netloc!=f'127.0.0.1:{port}' or
                    url.hostname!='127.0.0.1' or port is None or not 1<=port<=65535 or
                    url.username is not None or url.password is not None or url.query or url.fragment or
                    not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)*',url.path) or url.path.endswith('/')):
                raise ValueError()
        except (TypeError,ValueError):raise ValueError('literal loopback base URL required') from None
        path=url.path+'/chat/completions'
        # Original initializer performs its validation and establishes all
        # request/accounting fields. A same-port HTTPS placeholder causes no I/O;
        # the validated exact loopback HTTP endpoint is used only in this lab.
        super().__init__(f'https://127.0.0.1:{port}{path}',model_id,provider_id=provider_id,credential=None)
        self.endpoint=base_url+'/chat/completions'
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
