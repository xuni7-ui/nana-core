"""Nana original opt-in shim; install alongside an independently licensed AstrBot.

No LLM, response generation, native module, high-level send or account login.
Disabled by default. A host cutover must separately authorize these exact routes.
"""
import json
from pathlib import Path
from aiohttp import ClientSession
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.nanalink.official_host import OfficialHostBridge, gateway_message


@register('astrbot_plugin_nanalink_official', 'Nana', 'Explicit official QQ gateway handoff to one Nana Core', '1.0.0')
class NanaLinkOfficial(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config, self.session = config, None
        self.last_state = 'DISABLED'

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100000)
    async def receive(self, event: AstrMessageEvent):
        if not self.config.get('enabled') or not self.config.get('read_authorized'):
            return
        if event.get_platform_name() != 'qq_official':
            return
        # Host-selected data file contains endpoints/refs/routes, never secrets.
        path = Path(self.config['host_config'])
        if path.is_symlink() or path.stat().st_size > 65536:
            self.last_state = 'HOST_CONFIG_INVALID'
            return
        host = json.loads(path.read_bytes())
        routes = tuple((r['sender_id'], r['conversation_kind'], r['conversation_id']) for r in host['routes'])
        bridge = OfficialHostBridge(host['origin'], host['application_id'], host['bot_id'], lambda: '',
                     routes=routes, enabled=True, read_authorized=True)
        row = gateway_message(host['application_id'], event.message_obj.raw_message)
        if not bridge.matches(row):
            return
        # Fence BEFORE credentials/version/I/O so a selected ambiguous handoff
        # never starts a second response. This runtime switch needs host consent.
        event.stop_event()
        resolver = None
        try:
            platforms = [p for p in self.context.platform_manager.get_insts()
                         if p.meta().name == 'qq_official' and str(p.appid) == host['application_id']]
            if len(platforms) != 1:
                raise ValueError('host account mismatch')
            client = platforms[0].get_client()
            # botpy currently exposes no public token snapshot. Guard this single
            # compatibility read; an upstream change fails closed, never relogins.
            token = client.http._token
            if str(token.app_id) != host['application_id'] or str(client.robot.id) != host['bot_id']:
                raise ValueError('host identity mismatch')
            resolver = DurableSecretResolver(host['adapter_vault'], initialize=False)
            credential = resolver.resolve(host['ingress_secret_ref'])
            try:
                key = credential.reveal_for_header()
            finally:
                credential.clear()
            bridge.signing_key = key
            if self.session is None or self.session.closed:
                self.session = ClientSession(trust_env=False)
            self.last_state = await bridge.forward(self.session, row, token=token.access_token,
                      expires_at=token.expires_in, stop_legacy=lambda: None)
        except Exception:
            # No exception body/raw session/token logging, retry or fallback send.
            self.last_state = 'HOST_HANDOFF_UNKNOWN_NO_RETRY'
        finally:
            if resolver is not None:
                resolver.clear()
            bridge.signing_key = lambda: ''

    async def terminate(self):
        if self.session is not None:
            await self.session.close()
