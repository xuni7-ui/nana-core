"""Explicit installation and per-account failure isolation, no plugin autoexec."""
import asyncio
from dataclasses import dataclass
from typing import Protocol
from pydantic import Field
from ..contracts import DTO, CoreError
from .contracts import Account, Capability, Event, OperationReceipt, SessionHealth


class AdapterManifest(DTO):
    adapter_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    version: str = Field(pattern=r'^[0-9]+\.[0-9]+\.[0-9]+$')
    sdk_version: int = Field(default=1, ge=1, le=1)
    platforms: tuple[str, ...] = Field(min_length=1, max_length=8)
    license: str = Field(min_length=1, max_length=128)
    isolation: str = 'PROCESS_OR_EXPLICIT_IN_PROCESS'


class Adapter(Protocol):
    manifest: AdapterManifest
    account: Account

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    def health(self) -> SessionHealth: ...
    def capabilities(self) -> tuple[Capability, ...]: ...
    async def receive(self) -> Event | None: ...
    async def send(self, invocation) -> OperationReceipt: ...
    async def shutdown(self) -> None: ...


@dataclass
class Installed:
    adapter: Adapter
    enabled: bool = False
    fault: str | None = None


class AdapterRegistry:
    """A finite host-owned registry. Install is not account login/authorization.

    Factories are supplied explicitly by the host. Importing arbitrary module
    names from incoming events or phone input is deliberately unsupported.
    Package installation uses the ordinary pinned package manager outside Core.
    """
    def __init__(self, *, limit=16):
        if not 1 <= limit <= 64:
            raise ValueError('registry bound')
        self.limit, self.slots, self.previous = limit, {}, {}

    def install(self, adapter):
        manifest = AdapterManifest.model_validate(adapter.manifest.model_dump())
        if adapter.account.adapter_id != manifest.adapter_id or adapter.account.platform not in manifest.platforms:
            raise CoreError('NANALINK_MANIFEST_ACCOUNT_MISMATCH')
        key = adapter.account.key
        if key in self.slots or len(self.slots) >= self.limit:
            raise CoreError('NANALINK_ACCOUNT_DUPLICATE_OR_CAPACITY')
        self.slots[key] = Installed(adapter)
        return key

    async def enable(self, key):
        slot = self.slots[key]
        try:
            await asyncio.wait_for(slot.adapter.connect(), 15)
            slot.enabled, slot.fault = True, None
        except Exception:
            slot.enabled, slot.fault = False, 'CONNECT_FAILED'
            try:
                await asyncio.wait_for(slot.adapter.disconnect(), 3)
            except Exception:
                pass
            return False
        return True

    async def disable(self, key):
        slot = self.slots[key]
        slot.enabled = False
        try:
            await asyncio.wait_for(slot.adapter.disconnect(), 3)
        except Exception:
            slot.fault = 'SHUTDOWN_INCOMPLETE'

    async def replace(self, key, candidate):
        """Only offline replacement; preserve the last implementation for rollback."""
        slot = self.slots[key]
        if slot.enabled or candidate.account != slot.adapter.account:
            raise CoreError('NANALINK_OFFLINE_SAME_ACCOUNT_REQUIRED')
        AdapterManifest.model_validate(candidate.manifest.model_dump())
        if (candidate.manifest.adapter_id != slot.adapter.manifest.adapter_id
                or candidate.account.platform not in candidate.manifest.platforms):
            raise CoreError('NANALINK_ADAPTER_ID_MISMATCH')
        self.previous[key] = slot.adapter
        slot.adapter, slot.fault = candidate, None

    async def rollback(self, key):
        if self.slots[key].enabled or key not in self.previous:
            raise CoreError('NANALINK_OFFLINE_ROLLBACK_REQUIRED')
        self.slots[key].adapter, self.previous[key] = self.previous[key], self.slots[key].adapter
        self.slots[key].fault = None

    async def uninstall(self, key):
        await self.disable(key)
        self.slots.pop(key)
        self.previous.pop(key, None)

    async def poll_once(self, key):
        slot = self.slots[key]
        if not slot.enabled:
            return None
        try:
            return await asyncio.wait_for(slot.adapter.receive(), 15)
        except TimeoutError:
            return None
        except Exception:
            slot.fault = 'RECEIVE_FAILED'
            return None

    def view(self):
        return [{'account_key': key, 'platform': slot.adapter.account.platform,
                 'adapter_id': slot.adapter.manifest.adapter_id, 'version': slot.adapter.manifest.version,
                 'enabled': slot.enabled, 'error': slot.fault,
                 'health': slot.adapter.health().model_dump(),
                 'capabilities': [c.model_dump() for c in slot.adapter.capabilities()],
                 'rollback_available': key in self.previous}
                for key, slot in self.slots.items()]

    async def shutdown(self):
        await asyncio.gather(*(self.disable(key) for key in tuple(self.slots)))


def installed_adapters():
    """Discover installed package metadata only; no module import or network."""
    from importlib.metadata import entry_points
    return [{'name': point.name, 'entrypoint': point.value,
             'distribution': point.dist.name if point.dist else None,
             'version': point.dist.version if point.dist else None}
            for point in entry_points(group='nanalink.adapters')]


def install_adapter(registry, name, settings, *, allowed):
    """Explicit host allowlist, ordinary separately installed pinned packages.

    Neither a platform event nor phone text may provide Python module names.
    Upgrades still use registry offline replace/rollback, never auto-download.
    """
    if name not in allowed or type(settings) is not dict:
        raise CoreError('NANALINK_INSTALL_NOT_ALLOWED')
    from importlib.metadata import entry_points
    matches = [p for p in entry_points(group='nanalink.adapters') if p.name == name]
    if len(matches) != 1:
        raise CoreError('NANALINK_INSTALLED_PLUGIN_MISSING_OR_AMBIGUOUS')
    return registry.install(matches[0].load()(**settings))


async def subscribe(adapter):
    """One async subscriber, explicit caller lifetime; no independent cognition.

    receive() preserves platform event semantics. Subscribers cancel this iterator
    at graceful shutdown and close the adapter; no event is dispatched twice.
    """
    while True:
        event = await adapter.receive()
        if event is not None:
            yield event
        else:
            await asyncio.sleep(0.05)
