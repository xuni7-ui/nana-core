"""SDK wrappers over existing QQ/Bilibili workflows and media services.

The supplied workflow and its port already enforce original C/Grant/Kernel.
Nothing here creates or owns another LifeApplication, account agent or Store.
"""
from .contracts import Account, Capability, OperationReceipt, Outcome, SessionHealth
from .sdk import AdapterManifest
from .core_bridge import receipt_from_core
from ..contracts import Invocation, CoreError


class CoreWorkflowAdapter:
    def __init__(self, workflow, *, platform, account_id, adapter_id, capabilities):
        self.workflow = workflow
        self.account = Account(platform=platform, account_id=str(account_id), adapter_id=adapter_id)
        self.manifest = AdapterManifest(adapter_id=adapter_id, version='1.0.0', platforms=(platform,),
                                        license='Original Nana Core workflow')
        self._capabilities = tuple(capabilities)
        self._health = SessionHealth(compatibility='NATIVE_CORE')
        self.enabled = False

    async def connect(self):
        # No I/O or login is inferred by merely installing a Core wrapper.
        self.enabled = True

    async def disconnect(self):
        self.enabled = False
        self._health = self._health.model_copy(update={'connection': 'DISABLED'})

    def health(self):
        return self._health

    def capabilities(self):
        return self._capabilities

    async def receive(self):
        # Input is pushed by original owner through receive_event; no new poller.
        return None

    def receive_event(self, event):
        if (not self.enabled or event.account != self.account or not event.message_id
                or event.kind not in ({'message.created', 'notification.reply', 'notification.at'}
                                     if self.account.platform == 'bilibili' else {'message.created'})):
            raise CoreError('NANALINK_ORIGINAL_WORKFLOW_EVENT_REQUIRED')
        result = self.workflow.receive(event.message_id)
        self._health = self._health.model_copy(update={'connection': 'CONNECTED', 'login': 'AUTHENTICATED',
                                                       'receive': 'HEALTHY', 'last_event_us': event.observed_at_us})
        return receipt_from_core(event.key, result)

    async def send(self, invocation):
        """Only an ORIGINAL ActionKernel invocation reaches the original port.

        execute() is not confirmed success: independent original verify() owns
        that. The authoritative durable receipt stays in the existing Store.
        """
        if not self.enabled or type(invocation) is not Invocation:
            raise CoreError('NANALINK_ORIGINAL_KERNEL_INVOCATION_REQUIRED')
        port = getattr(self.workflow, 'port', None) or self.workflow.realization.port
        port.execute(invocation)
        return OperationReceipt(operation_id=invocation.action_id, action_id=invocation.action_id,
                                outcome=Outcome.UNKNOWN, reason='ORIGINAL_KERNEL_VERIFY_PENDING')

    async def shutdown(self):
        await self.disconnect()


def qq_adapter(workflow):
    return CoreWorkflowAdapter(workflow, platform='qq', account_id=workflow.channel.account_id,
                               adapter_id='qq.onebot', capabilities=(
        Capability(name='message.receive', available=workflow.channel.read_authorized),
        Capability(name='message.text.send', available=workflow.channel.send_authorized),
        Capability(name='message.readback', available=True),
        Capability(name='media.reference', available=True),
    ))


def bilibili_adapter(workflow):
    return CoreWorkflowAdapter(workflow, platform='bilibili', account_id=workflow.channel.account_id,
                               adapter_id='bilibili.account', capabilities=(
        Capability(name='message.receive', available=workflow.channel.read_authorized),
        Capability(name='message.text.send', available=workflow.channel.send_authorized),
        Capability(name='message.readback', available=True),
        Capability(name='video.metadata', available=True),
        Capability(name='video.subtitles', available=True),
        Capability(name='video.frames', available=bool(workflow.app.config.bilibili_life
                   and workflow.app.config.bilibili_life.visual_samples), reason='ORIGINAL_OPTIONAL_FRAME_SERVICE'),
        Capability(name='notification.reply', available=workflow.channel.read_authorized),
        Capability(name='dynamic.publish', available=False, reason='NO_EXISTING_GOVERNED_PORT'),
    ))


def bilibili_notification(account, channel, item, *, now_us):
    """Reuse C.4 pure normalizer; NEVER start legacy agent/pump/LLM/send loop."""
    from ._c4_source import normalize
    from .contracts import Event, Segment
    from ..storage import digest
    row = normalize(channel, item, my_mid=int(account.account_id))
    if row is None or row['is_mine']:
        return None
    return Event(account=account, event_id=row['eid'], kind='notification.' + channel,
                 conversation_id=str(row.get('aid') or row['bvid']), conversation_kind='channel',
                 sender_id=str(row['author_mid']) if row['author_mid'] else None,
                 message_id=str(row['source_id']), parent_id=str(row['root_id']) if row['root_id'] else None,
                 occurred_at_us=row['ctime'] * 1000000 if row['ctime'] else None,
                 observed_at_us=now_us, privacy='PERSONAL', origin='ACCOUNT_API_UNATTESTED',
                 segments=(Segment(kind='video', reference=row['bvid']),),
                 raw_sha256=digest(item), raw_reference='bilibili:msgfeed:' + row['eid'])


class BilibiliEventsAdapter(CoreWorkflowAdapter):
    """C.4 notification pump on the original owner; no legacy Agent/LLM loop.

    The caller invokes receive() at an infrastructure safe point. A finite page
    enters the unified event contract; receive_event() independently refetches
    the bound comment/DM through the original C/Kernel workflow. No auto reply.
    """
    def __init__(self, workflow, *, interval_seconds=300):
        if not 300 <= interval_seconds <= 86400:
            raise ValueError('notification poll budget')
        original = bilibili_adapter(workflow)
        super().__init__(workflow, platform='bilibili', account_id=workflow.channel.account_id,
                         adapter_id='bilibili.account', capabilities=original.capabilities())
        from collections import deque, OrderedDict
        self.pending, self.seen = deque(), OrderedDict()
        self.interval_seconds = interval_seconds
        self.metrics = dict(polls=0, duplicate=0, backpressure=0, unsupported=0)

    async def connect(self):
        c = self.workflow.channel
        if not c.enabled or not c.read_authorized or not c.private_read_authorized:
            raise CoreError('BILIBILI_NOTIFICATION_PRIVATE_READ_NOT_AUTHORIZED')
        await super().connect()

    async def receive(self):
        if not self.enabled:
            return None
        if self.pending:
            return self.pending.popleft()
        w, c = self.workflow, self.workflow.channel
        if not c.enabled or not c.read_authorized or not c.private_read_authorized:
            raise CoreError('BILIBILI_NOTIFICATION_PRIVATE_READ_NOT_AUTHORIZED')
        w._authority()
        now = w.store.clock.utc_now_us()
        from ..storage import digest
        key = digest(['nanalink.bili.notification', self.account.key, now // (self.interval_seconds * 1000000)])
        if w.store.db.execute("SELECT 1 FROM events WHERE source_namespace='platform.bilibili.ingress' AND source_key=?", (key,)).fetchone():
            return None
        poll_id = 'nanalink.' + c.channel_id
        count = w.store.db.execute("SELECT count(*) FROM events WHERE kind='platform.bilibili.ingress_reserved' AND recorded_at_us>=? AND json_extract(data_json,'$.data.channel_id')=?",
                                  (now - 3600000000, poll_id)).fetchone()[0]
        if count >= 12:
            raise CoreError('BILIBILI_NOTIFICATION_HOURLY_CEILING')
        from ..life.platform_runtime import reserve_inbound_read
        reserve_inbound_read(w.realization.kernel, 3, 'bilibili', poll_id, key)
        w.transport.calls = 0
        try:
            w.transport.account()
            pages = {channel: w.transport.notification_rows(channel) for channel in ('reply', 'at')}
        except Exception:
            self._health = self._health.model_copy(update={'connection': 'DEGRADED',
                       'receive': 'STALE', 'error': 'NOTIFICATION_READ_FAILED'})
            raise
        pressure_before = self.metrics['backpressure']
        self.metrics['polls'] += 1
        for channel, items in pages.items():
            for item in items:
                event = bilibili_notification(self.account, channel, item, now_us=now)
                if event is None:
                    self.metrics['unsupported'] += 1
                    continue
                if (event.sender_id != str(c.sender_id) or event.conversation_id != str(c.target_id)
                        or c.kind != 'comment'):
                    continue
                if event.key in self.seen:
                    self.metrics['duplicate'] += 1
                    continue
                if len(self.pending) >= 32:
                    self.metrics['backpressure'] += 1
                    self._health = self._health.model_copy(update={'receive': 'BACKPRESSURE'})
                    continue
                self.pending.append(event.model_copy(update={'origin': w.transport.realm}))
                self.seen[event.key] = event.raw_sha256
                while len(self.seen) > 512:
                    self.seen.popitem(last=False)
        self._health = self._health.model_copy(update={'connection': 'CONNECTED', 'login': 'AUTHENTICATED',
                   'receive': 'BACKPRESSURE' if self.metrics['backpressure'] > pressure_before else 'HEALTHY', 'error': None,
                   'last_event_us': now if self.pending else self._health.last_event_us})
        return self.pending.popleft() if self.pending else None

    async def disconnect(self):
        self.pending.clear()
        await super().disconnect()
