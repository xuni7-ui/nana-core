"""Finite approved installed versions, on the adapter's OWN event loop.

Infrastructure metadata uses the original AtomicDocument, never a new Store.
No pip, module name, credential, endpoint, cognition or effect can enter commands.
The host supplies factories and pins BEFORE starting this control surface.
"""
import asyncio
import copy
from ..contracts import CoreError
from ..life.live_api.state import AtomicDocument
from .sdk import AdapterRegistry


class AdapterManagement:
    def __init__(self, adapters, catalogs, *, state_path=None):
        self.registry = AdapterRegistry()
        self.catalogs, self.keys, self.lock = catalogs, {}, asyncio.Lock()
        rows = {}
        for alias, adapter in adapters.items():
            key = self.registry.install(adapter);self.keys[alias] = key
            version = adapter.manifest.version
            if version not in catalogs.get(alias, {}):
                raise CoreError('NANALINK_HOST_CATALOG_REQUIRED')
            self.registry.slots[key].enabled = True
            rows[alias] = {'current':version,'previous':None,'installed':True,'enabled':True,'uncertain':False}
        initial = {'schema_version':1,'revision':1,'adapters':rows}
        self.document = AtomicDocument(state_path, initial) if state_path else None
        self.state = initial if self.document is None else self.document.read()
        if set(self.state) != {'schema_version','revision','adapters'} or set(self.state['adapters']) != set(rows):
            raise CoreError('NANALINK_MANAGEMENT_CONFIG_CHANGED_REVIEW_REQUIRED')
        for alias, row in self.state['adapters'].items():
            if (set(row) != set(rows[alias]) or any(type(row[k]) is not bool for k in ('installed','enabled','uncertain'))
                    or row['current'] not in catalogs[alias]
                    or row['previous'] is not None and row['previous'] not in catalogs[alias]):
                raise CoreError('NANALINK_APPROVED_VERSION_UNAVAILABLE')
            key = self.keys[alias]
            if row['current'] != adapters[alias].manifest.version:
                self.registry.slots[key].adapter = self._candidate(alias,row['current'])
            self.registry.slots[key].enabled = row['installed'] and row['enabled'] and not row['uncertain']
            if row['previous']:
                self.registry.previous[key] = self._candidate(alias,row['previous'])

    def _candidate(self, alias, version):
        candidate = self.catalogs[alias][version]()
        base = self.registry.slots[self.keys[alias]].adapter
        if candidate.account != base.account or candidate.manifest.version != version or candidate.manifest.adapter_id != base.manifest.adapter_id:
            raise CoreError('NANALINK_HOST_CATALOG_IDENTITY_MISMATCH')
        return candidate

    def adapter(self, alias):
        return self.registry.slots[self.keys[alias]].adapter

    def enabled(self, alias):
        return self.registry.slots[self.keys[alias]].enabled

    def _save(self, rows):
        if self.document:
            def change(data):
                if data['revision'] != self.state['revision']:
                    raise CoreError('NANALINK_MANAGEMENT_REVISION_CONFLICT')
                data['adapters'] = rows
            self.document.update(change)
            self.state = self.document.read()
        else:
            self.state = {**self.state,'revision':self.state['revision']+1,'adapters':rows}

    def view(self, alias):
        row = self.state['adapters'][alias]
        return {'schema_version':1,'revision':self.state['revision'],'persistent':self.document is not None,
                'adapter_id':self.adapter(alias).manifest.adapter_id,**row,'enabled':self.enabled(alias),
                'approved_versions':list(self.catalogs[alias]),'account_key':self.adapter(alias).account.key,
                'downloads_supported':False,'source':'HOST_APPROVED_INSTALLED_FACTORIES'}

    async def command(self, alias, operation, version, revision):
        async with self.lock:
            if revision != self.state['revision']:
                raise CoreError('NANALINK_MANAGEMENT_REVISION_CONFLICT')
            if operation not in {'INSTALL','UNINSTALL','ENABLE','DISABLE','UPGRADE','ROLLBACK'}:
                raise CoreError('NANALINK_MANAGEMENT_OPERATION_UNSUPPORTED')
            row = copy.deepcopy(self.state['adapters'][alias]);key=self.keys[alias]
            if operation in {'INSTALL','UPGRADE'} and version not in self.catalogs[alias]:
                raise CoreError('NANALINK_APPROVED_VERSION_UNAVAILABLE')
            if operation in {'INSTALL','UNINSTALL','UPGRADE','ROLLBACK'} and self.enabled(alias):
                raise CoreError('NANALINK_PAUSE_BEFORE_PACKAGE_CHANGE')
            if operation == 'INSTALL' and row['installed'] or operation != 'INSTALL' and not row['installed']:
                raise CoreError('NANALINK_PACKAGE_STATE_CONFLICT')
            if operation == 'ROLLBACK' and not row['previous']:
                raise CoreError('NANALINK_OFFLINE_ROLLBACK_REQUIRED')
            # Durable uncertain marker BEFORE effect. Crash never auto-enables a
            # partly changed connector or silently rolls a failed version forward.
            rows=copy.deepcopy(self.state['adapters']);rows[alias]['uncertain']=True
            self._save(rows)
            try:
                if operation == 'DISABLE':
                    await self.registry.disable(key);row['enabled']=False
                elif operation == 'ENABLE':
                    if not await self.registry.enable(key):
                        raise CoreError('NANALINK_CONNECT_FAILED')
                    row['enabled']=True
                elif operation == 'UNINSTALL':
                    await self.registry.disable(key);row.update(installed=False,enabled=False)
                elif operation in {'INSTALL','UPGRADE'}:
                    await self.registry.replace(key,self._candidate(alias,version))
                    row.update(previous=row['current'],current=version,installed=True,enabled=False)
                else:
                    await self.registry.rollback(key)
                    row['current'],row['previous']=row['previous'],row['current']
                row['uncertain']=False
                rows=copy.deepcopy(self.state['adapters']);rows[alias]=row;self._save(rows)
                return {'state':'APPLIED','external_delivery':False,**self.view(alias)}
            except Exception:
                await self.registry.disable(key)
                return {'state':'UNKNOWN_NO_AUTORETRY','external_delivery':False,**self.view(alias)}


class AdapterHandle:
    """Keep HTTP route closures pointed at the current offline-selected version."""
    def __init__(self, owner, alias):
        self.owner, self.alias = owner, alias

    def __getattr__(self, name):
        return getattr(self.owner.adapters[self.alias], name)
