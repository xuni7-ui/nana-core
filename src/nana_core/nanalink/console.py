"""Read-only sidecar health into the ORIGINAL authenticated Nana Space panel."""
import json
import urllib.request
from pydantic import Field, model_validator
from ..contracts import DTO, CoreError
from ..life.platform_bridge import NoRedirect
from .contracts import SessionHealth, Capability
from .onebot import safe_endpoint


class ObservationBinding(DTO):
    platform: str = Field(pattern=r'^qq$')
    account_id: str = Field(pattern=r'^[0-9]{1,20}$')
    channel_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    endpoint: str = Field(max_length=256, repr=False)
    credential_ref: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')

    @model_validator(mode='after')
    def safe(self):
        safe_endpoint(self.endpoint, schemes=('http', 'https'))
        from urllib.parse import urlsplit
        if urlsplit(self.endpoint).path not in {'', '/'}:
            raise ValueError('origin required')
        return self


class NanaLinkObserver:
    def __init__(self, bindings, resolver):
        self.bindings, self.resolver = tuple(bindings), resolver
        if len(bindings) > 16:
            raise ValueError('observation bound')

    def _one(self, binding):
        if self.resolver is None or not self.resolver.available(binding.credential_ref):
            raise CoreError('NANALINK_CREDENTIAL_UNAVAILABLE')
        credential = self.resolver.resolve(binding.credential_ref)
        try:
            headers = {'Authorization': 'Bearer ' + credential.reveal_for_header()}
        finally:
            credential.clear()
        # Loopback must never inherit the cloud/provider credential proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        req = urllib.request.Request(binding.endpoint.rstrip('/') + '/nanalink/status', headers=headers)
        with opener.open(req, timeout=0.5) as response:
            raw = response.read(16385)
            if response.status != 200 or len(raw) > 16384:
                raise ValueError()
        value = json.loads(raw)
        if value.get('schema_version') != 1 or value.get('platform') != binding.platform:
            raise ValueError()
        from .contracts import Account
        expected = Account(platform='qq', adapter_id='qq.onebot', account_id=binding.account_id).key
        if value.get('account_key') != expected:
            raise CoreError('NANALINK_OBSERVED_ACCOUNT_MISMATCH')
        health = SessionHealth.model_validate(value['health'])
        caps = value.get('capabilities')
        if type(caps) is not list or len(caps) > 32:
            raise ValueError()
        return {'platform': binding.platform, 'channel_id': binding.channel_id,
                'health': health.model_dump(), 'capabilities': [Capability.model_validate(c).model_dump() for c in caps]}

    def view(self):
        # Finite explicit probes; no account API/login/model/send calls. Bound
        # total wall time without leaving background network workers behind.
        rows = []
        for binding in self.bindings[:4]:
            try:
                rows.append(self._one(binding))
            except Exception:
                rows.append({'platform': binding.platform, 'channel_id': binding.channel_id,
                             'health': SessionHealth(connection='DISCONNECTED', error='SIDECAR_UNAVAILABLE').model_dump(),
                             'capabilities': []})
        return {'schema_version': 1, 'sessions': rows, 'coverage': 'EXPLICIT_SIDECAR_OBSERVATIONS',
                'unobserved_count': max(0, len(self.bindings) - 4)}
