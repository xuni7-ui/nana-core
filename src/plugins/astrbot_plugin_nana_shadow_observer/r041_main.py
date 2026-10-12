"""Dormant message-only UDS observer, no private runtime import or autostart."""
from astrbot.api.event import filter
from astrbot.api.star import Star,register
from .bridge_client import OneShotBridgeClient
_CLIENT=None

def bind_local_client(client):
    global _CLIENT
    if client is not None and type(client) is not OneShotBridgeClient:raise ValueError('BRIDGE_CLIENT_REQUIRED')
    old=_CLIENT;_CLIENT=client;return old

@filter.on_decorating_result()
async def nana_shadow_r041_on_decorating_result(event):
    try:
        if _CLIENT is not None:await _CLIENT.on_decorating_result(event)
    except BaseException:pass
    return None

@register('astrbot_plugin_nana_shadow_bridge','nana-core','R041 temporary metadata UDS observer','0.0.41')
class NanaShortLivedShadowBridge(Star):
    async def terminate(self):
        global _CLIENT
        client=_CLIENT;_CLIENT=None
        try:
            if client is not None:await client.close()
        except BaseException:pass
        return None
