"""Read-only sidecar health into the ORIGINAL authenticated Nana Space panel."""
import json
import urllib.error
import urllib.request
from typing import Literal
from pydantic import Field, model_validator, model_serializer
from ..contracts import DTO, CoreError
from ..life.platform_bridge import NoRedirect
from .contracts import SessionHealth, Capability
from .onebot import safe_endpoint


class ObservationBinding(DTO):
    platform: str = Field(pattern=r'^qq$')
    backend: Literal['onebot', 'official'] = 'onebot'
    account_id: str = Field(pattern=r'^[0-9]{1,20}$')
    channel_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    endpoint: str = Field(max_length=256, repr=False)
    credential_ref: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')

    @model_serializer(mode='wrap')
    def compatible_wire(self, handler):
        value = handler(self)
        if self.backend == 'onebot':
            value.pop('backend', None)
        return value

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

    def _probe(self, binding, path, *, body=None):
        if self.resolver is None or not self.resolver.available(binding.credential_ref):
            raise CoreError('NANALINK_CREDENTIAL_UNAVAILABLE')
        credential = self.resolver.resolve(binding.credential_ref)
        try:
            headers = {'Authorization': 'Bearer ' + credential.reveal_for_header()}
        finally:
            credential.clear()
        # Loopback must never inherit the cloud/provider credential proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        req = urllib.request.Request(binding.endpoint.rstrip('/') + path, headers={**headers,'Content-Type':'application/json'},
                                     data=None if body is None else json.dumps(body).encode())
        with opener.open(req, timeout=17 if body is not None else 0.5) as response:
            raw = response.read(16385)
            if response.status != 200 or len(raw) > 16384:
                raise ValueError()
        return json.loads(raw)

    def _one(self, binding):
        value = self._probe(binding, '/nanalink/status')
        if value.get('schema_version') != 1 or value.get('platform') != binding.platform:
            raise ValueError()
        from .contracts import Account
        expected = Account(platform='qq', adapter_id='qq.' + binding.backend, account_id=binding.account_id).key
        if value.get('account_key') != expected:
            raise CoreError('NANALINK_OBSERVED_ACCOUNT_MISMATCH')
        health = SessionHealth.model_validate(value['health'])
        caps = value.get('capabilities')
        if type(caps) is not list or len(caps) > 32:
            raise ValueError()
        try:
            management = self._management(binding, self._probe(binding, '/nanalink/manage'))
        except Exception:
            management = None
        return {'platform': binding.platform, 'channel_id': binding.channel_id, 'management':management,
                'health': health.model_dump(), 'capabilities': [Capability.model_validate(c).model_dump() for c in caps]}

    def _management(self, binding, value):
        from .contracts import Account
        class View(DTO):
            schema_version: Literal[1]
            revision: int = Field(ge=1)
            persistent: bool
            adapter_id: str
            current: str = Field(pattern=r'^[0-9]+\.[0-9]+\.[0-9]+$')
            previous: str | None
            installed: bool
            enabled: bool
            uncertain: bool
            approved_versions: tuple[str,...] = Field(max_length=16)
            account_key: str
            downloads_supported: Literal[False]
            source: Literal['HOST_APPROVED_INSTALLED_FACTORIES']
            state: str | None = None
            external_delivery: Literal[False] = False
        row = View.model_validate(value)
        account = Account(platform=binding.platform,adapter_id='qq.'+binding.backend,account_id=binding.account_id)
        import re
        if row.account_key != account.key or row.adapter_id != account.adapter_id or any(
                not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',v) for v in (*row.approved_versions, *([row.previous] if row.previous else []))):
            raise CoreError('NANALINK_OBSERVED_ACCOUNT_MISMATCH')
        return row.model_dump(mode='json')

    def manage(self, platform, channel_id, body):
        matches = [b for b in self.bindings if (b.platform,b.channel_id)==(platform,channel_id)]
        if len(matches) != 1:
            raise CoreError('NANALINK_MANAGEMENT_BINDING_REQUIRED')
        return self._management(matches[0],self._probe(matches[0],'/nanalink/manage',body=body))

    def view(self):
        # Finite explicit probes; no account API/login/model/send calls. Bound
        # total wall time without leaving background network workers behind.
        rows = []
        for binding in self.bindings[:4]:
            try:
                rows.append(self._one(binding))
            except CoreError as exc:
                # Only expose a short allowlisted diagnostic, never endpoint,
                # credential, or raw connector exception text.
                error = {'NANALINK_OBSERVED_ACCOUNT_MISMATCH': 'ACCOUNT_MISMATCH',
                         'NANALINK_CREDENTIAL_UNAVAILABLE': 'CREDENTIAL_UNAVAILABLE'}.get(exc.code, 'SIDECAR_UNAVAILABLE')
                rows.append({'platform': binding.platform, 'channel_id': binding.channel_id,
                             'health': SessionHealth(connection='DISCONNECTED', error=error).model_dump(),
                             'capabilities': []})
            except urllib.error.HTTPError as exc:
                error = 'CREDENTIAL_REJECTED' if exc.code in {401, 403} else 'SIDECAR_UNAVAILABLE'
                rows.append({'platform': binding.platform, 'channel_id': binding.channel_id,
                             'health': SessionHealth(connection='DISCONNECTED', error=error).model_dump(),
                             'capabilities': []})
            except Exception:
                rows.append({'platform': binding.platform, 'channel_id': binding.channel_id,
                             'health': SessionHealth(connection='DISCONNECTED', error='SIDECAR_UNAVAILABLE').model_dump(),
                             'capabilities': []})
        return {'schema_version': 1, 'sessions': rows, 'coverage': 'EXPLICIT_SIDECAR_OBSERVATIONS',
                'unobserved_count': max(0, len(self.bindings) - 4)}
