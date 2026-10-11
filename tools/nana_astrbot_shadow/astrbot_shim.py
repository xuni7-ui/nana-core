"""AstrBot 4.28.0 lifecycle shim from Nana's source audit (NOT dispatcher).

Evidence: shared commit 652a72fde12dcb4786491a6a0f73b06e8675fe1a,
docs/nana_shadow_astrbot_dispatcher_audit_20261011.md sections1,2,Q4,Q5,Q7.
filter aliases: astrbot/api/event/filter/__init__.py:30-31.
registry: astrbot/core/star/star_handler.py get_handlers_by_module_name:191,
remove:205; manager lifecycle direct awaits:1421-1434/2044-2056.
No framework imports/Star registration/reload/queue/event mutation in this module.
Operator supplies already-authorized SDK handles; Codex only exercises fixtures.
"""
import re
from tools.nana_host_shadow.safety import digest

AUDIT_COMMIT='652a72fde12dcb4786491a6a0f73b06e8675fe1a'
MODULE='data.plugins.astrbot_plugin_nana_shadow_observer.main'
NAMES=('nana_core_metadata_on_plugin_loaded','nana_core_metadata_on_plugin_unloaded')

class AstrBotLifecycleBinding:
    def __init__(self, *, filter_api, registry, observed_version, observer, metadata):
        if observed_version!='4.28.0':raise ValueError('BLOCKED_API_DRIFT')
        for owner,name in ((filter_api,'on_plugin_loaded'),(filter_api,'on_plugin_unloaded'),
                            (registry,'get_handlers_by_module_name'),(registry,'remove')):
            if not callable(getattr(owner,name,None)):raise ValueError('BLOCKED_API_DRIFT')
        # Accept only already-sanitizable operator metadata; do not inspect the
        # StarMetadata passed by AstrBot. Lifecycle events themselves have no
        # source timestamp/message ID; synthetic IDs are explicitly operator-set.
        checked=observer.sanitizer.sanitize(metadata)
        if checked.metadata is None:raise ValueError('INTERNAL_PROBE_METADATA_REQUIRED')
        self.filter_api,self.registry,self.observer=filter_api,registry,observer
        # Retain only entrance allowlisted fields, never supplied body/attachment.
        self.metadata={k:metadata[k] for k in ('platform','type','event_id','timestamp','conversation_id','sender_id','event_source','synthetic','probe_id') if k in metadata}
        self.permit=observer.issue_local_permit(checked.metadata.probe_id)
        self._armed=False;self.active=False
        self._callbacks=[]
        for name in NAMES:
            async def callback(_star_metadata, _self=self):
                try:
                    if _self.active and _self._armed:
                        _self._armed=False
                        await _self.observer.callback(_self.metadata,permit=_self.permit)
                except BaseException:
                    # No repr / handler exception / production reply / logs.
                    pass
                return None
            callback.__name__=name;callback.__module__=MODULE
            self._callbacks.append(callback)

    def _owned(self):
        try:
            handlers=self.registry.get_handlers_by_module_name(MODULE)
            if type(handlers) not in {list,tuple}:raise ValueError()
            result=[]
            for h in handlers:
                f=getattr(h,'handler',None)
                if getattr(f,'__module__',None)==MODULE and getattr(f,'__name__',None) in NAMES:
                    result.append(h)
            if len(result)>2:raise ValueError()
            return result
        except Exception:raise ValueError('BLOCKED_API_DRIFT') from None

    def registry_probe(self):
        owned=self._owned()
        names=sorted(h.handler.__name__ for h in owned)
        return {'callback_present':bool(owned),'registry_digest':digest(names),
                'callback_count':len(owned),'scope':'exact observer callbacks only',
                'probe_class':'C','dispatcher_proven':False}

    def register(self):
        if self.active or self._owned():raise ValueError('REGISTRATION_ALREADY_PRESENT')
        try:
            self.filter_api.on_plugin_loaded()(self._callbacks[0])
            self.filter_api.on_plugin_unloaded()(self._callbacks[1])
            if len(self._owned())!=2:raise ValueError('BLOCKED_API_DRIFT')
            self.active=True
        except BaseException:
            # Clean only our two named callback metadata entries.
            for h in self._owned():self.registry.remove(h)
            raise
        return self.registry_probe()

    def arm_operator_probe(self):
        if not self.active:raise ValueError('OBSERVER_NOT_ACTIVE')
        self._armed=True

    async def unregister(self):
        self.active=False;self._armed=False
        try:
            for h in self._owned():self.registry.remove(h)
            after=self.registry_probe()
            if after['callback_present']:raise ValueError('OBSERVER_UNLOAD_NOT_PROVEN')
            return after
        finally:
            await self.observer.close()
