"""R04 packaging entry: message-only dormant Observer, NOT installed by Codex.

AstrBot4.28.0 OnDecoratingResultEvent source refs: R03 audit stage158-189.
No lifecycle metadata logger, no background autostart, no env/config arm.
Operator must bind a reviewed one-shot adapter; empty production pins prohibit it.
"""
from astrbot.api.event import filter
from astrbot.api.star import Star, register

_ADAPTER=None

def bind_reviewed_adapter(adapter):
    global _ADAPTER
    if adapter is not None:
        from tools.nana_astrbot_shadow.one_shot import ProductionTrustStore, PRODUCTION_REVIEW_PINS
        from tools.nana_astrbot_shadow.one_shot_ingress import OneShotObserver
        from .message_hook_adapter import OneShotMessageHookAdapter
        if (type(adapter) is not OneShotMessageHookAdapter
            or type(adapter.observer) is not OneShotObserver
            or type(adapter.observer._sink.trust) is not ProductionTrustStore
            or not PRODUCTION_REVIEW_PINS
            or adapter.observer.operator_binding_verified is not True):
            raise ValueError('TRUSTED_PRODUCTION_ONE_SHOT_ADAPTER_REQUIRED')
    previous=_ADAPTER;_ADAPTER=adapter
    return previous

@filter.on_decorating_result()
async def nana_shadow_r04_on_decorating_result(event):
    try:
        adapter=_ADAPTER
        if adapter is not None:await adapter.on_decorating_result(event)
    except BaseException:
        pass  # Never traceback/repr/error reply into result pipeline.
    return None

@register('astrbot_plugin_nana_shadow_observer','nana-core','R04 metadata-only one-shot development observer','0.0.4')
class NanaShadowOneShotObserver(Star):
    async def terminate(self):
        global _ADAPTER
        adapter=_ADAPTER;_ADAPTER=None
        try:
            if adapter is not None:await adapter.close()
        except BaseException:pass
        return None
