"""Real RSS/Atom source adapter: fixed public URL, finite reads, no account.

Provides a third platform without touching the Core. The owner may consume its
observations through an explicitly PUBLIC SurfaceBinding; it chooses whether
anything warrants reading or cognition. Feed polling itself invokes no model.
"""
import hashlib
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict
from .contracts import Account, Capability, Event, Segment, OperationReceipt, Outcome, SessionHealth
from .sdk import AdapterManifest
from .onebot import safe_endpoint
from ..contracts import CoreError


class FeedAdapter:
    manifest = AdapterManifest(adapter_id='web.feed', version='1.0.0', platforms=('webfeed',),
                                license='Nana original; Python standard library XML parser')

    def __init__(self, url, *, authorized=False, max_bytes=262144, interval=300, fetch=None):
        safe_endpoint(url, schemes=('https', 'http'))
        if not 1024 <= max_bytes <= 1048576 or not 30 <= interval <= 86400:
            raise ValueError('feed budget')
        self.account = Account(platform='webfeed', account_id=hashlib.sha256(url.encode()).hexdigest(), adapter_id='web.feed')
        self.url, self.authorized, self.max_bytes, self.interval = url, authorized, max_bytes, interval
        self._fetch = fetch
        self._health = SessionHealth(compatibility='RSS_ATOM')
        self.seen, self.pending = OrderedDict(), []
        self.session = None
        self.next_at = 0
        self.etag = self.modified = None
        self.metrics = dict(requests=0, bytes=0, events=0, duplicates=0)

    def health(self):
        return self._health

    def capabilities(self):
        return (Capability(name='feed.receive', available=self.authorized),
                Capability(name='message.send', available=False, reason='READ_ONLY_SOURCE'),
                Capability(name='media.reference', available=True))

    async def connect(self):
        if not self.authorized:
            raise CoreError('FEED_READ_NOT_AUTHORIZED')
        import aiohttp
        if self._fetch is None and self.session is None:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5), trust_env=False)

    async def _get(self):
        if self._fetch:
            return await self._fetch(self.url, self.max_bytes)
        headers = {'Accept': 'application/atom+xml, application/rss+xml, application/xml'}
        if self.etag:
            headers['If-None-Match'] = self.etag
        if self.modified:
            headers['If-Modified-Since'] = self.modified
        async with self.session.get(self.url, headers=headers, allow_redirects=False) as response:
            if response.status == 304:
                return None
            if response.status != 200:
                raise CoreError('FEED_HTTP_FAILED')
            raw = await response.content.read(self.max_bytes + 1)
            # Validators are bounded, never copied to evidence or model context.
            self.etag = response.headers.get('ETag', '')[:256] or None
            self.modified = response.headers.get('Last-Modified', '')[:128] or None
            return raw

    async def receive(self):
        if not self.authorized:
            raise CoreError('FEED_READ_NOT_AUTHORIZED')
        if self.pending:
            return self.pending.pop(0)
        if time.monotonic() < self.next_at:
            return None
        self.next_at = time.monotonic() + self.interval
        self.metrics['requests'] += 1
        try:
            raw = await self._get()
            if raw is not None:
                self.metrics['bytes'] += len(raw)
                self.pending = self.parse(raw)
            self._health = self._health.model_copy(update={'connection': 'CONNECTED', 'receive': 'HEALTHY', 'error': None})
        except Exception:
            self._health = self._health.model_copy(update={'connection': 'DEGRADED', 'error': 'FEED_READ_FAILED'})
            raise
        return self.pending.pop(0) if self.pending else None

    def parse(self, raw):
        if not isinstance(raw, bytes) or len(raw) > self.max_bytes or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise CoreError('FEED_XML_BOUND_OR_DTD_DENIED')
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            raise CoreError('FEED_XML_INVALID') from None
        if root.tag not in {'rss', '{http://www.w3.org/2005/Atom}feed'}:
            raise CoreError('FEED_FORMAT_UNSUPPORTED')
        atom = '{http://www.w3.org/2005/Atom}'
        rows = root.findall('./channel/item') if root.tag == 'rss' else root.findall(atom + 'entry')
        events, stamp = [], time.time_ns() // 1000
        for row in rows[:32]:
            prefix = '' if row.tag == 'item' else atom
            ident = row.findtext(prefix + ('guid' if not prefix else 'id'))
            link = row.findtext('link') if not prefix else next((x.get('href') for x in row.findall(atom + 'link') if x.get('rel', 'alternate') == 'alternate'), None)
            # Do not dedupe by headline/nickname; require an actual stable ID.
            ident = ident or link
            if not ident:
                continue
            eid = hashlib.sha256(ident.encode()).hexdigest()
            if eid in self.seen:
                self.metrics['duplicates'] += 1
                continue
            title = (row.findtext(prefix + 'title') or '').strip()[:512]
            if not title:
                continue
            raw_hash = hashlib.sha256(ET.tostring(row)).hexdigest()
            self.seen[eid] = raw_hash
            while len(self.seen) > 1024:
                self.seen.popitem(last=False)
            events.append(Event(account=self.account, event_id=eid, kind='feed.item', conversation_kind='feed',
                          conversation_id=self.account.account_id, observed_at_us=stamp, privacy='PUBLIC',
                          origin='ACCOUNT_API_UNATTESTED', segments=(Segment(kind='text', text=title),
                          Segment(kind='page', reference=link[:512] if link else None)), raw_sha256=raw_hash,
                          raw_reference='feed:' + eid))
        self.metrics['events'] += len(events)
        return events

    async def send(self, invocation):
        return OperationReceipt(operation_id=getattr(invocation, 'action_id', 'unsupported'),
                                outcome=Outcome.UNSUPPORTED, reason='FEED_IS_READ_ONLY')

    async def disconnect(self):
        if self.session:
            await self.session.close()
            self.session = None
        self.pending.clear()
        self._health = self._health.model_copy(update={'connection': 'DISABLED'})

    async def shutdown(self):
        await self.disconnect()


class FeedCoreBridge:
    """Use on the original owner only, with an explicit PUBLIC surface binding."""
    def __init__(self, app, adapter, binding_id):
        binding = app.surfaces._binding(binding_id)
        if binding.platform != 'web.feed' or 'PUBLIC' not in binding.permitted_privacy:
            raise CoreError('FEED_PUBLIC_SURFACE_REQUIRED')
        self.app, self.adapter, self.binding_id = app, adapter, binding_id

    def receive(self, event):
        from ..continuity.open_life.sources import remember
        from ..continuity.subject.contracts import SubjectInput
        from ..continuity.extensions import SurfaceEnvelope
        from ..presence.contracts import RuntimeEvent, Cause
        if event.account != self.adapter.account or event.privacy != 'PUBLIC' or event.kind != 'feed.item':
            raise CoreError('FEED_SOURCE_BINDING_MISMATCH')
        binding = self.app.surfaces._binding(self.binding_id)
        runtime = self.app.runtime
        now = runtime.clock.utc_now_us()
        # Publication is ENVIRONMENT data, never the primary user's command.
        # Retain only bounded source metadata in the ORIGINAL MemoryService;
        # original C sees a source-backed opportunity and may ignore/defer it.
        body = {'platform': 'web.feed', 'account_key': event.account.key,
                'event_id': event.event_id, 'source_digest': event.raw_sha256,
                'origin': event.origin, 'source_observed_at_us': event.observed_at_us,
                'title': '\n'.join(s.text for s in event.segments if s.text)[:512],
                'references': [s.reference for s in event.segments if s.reference][:8],
                'publication_is_not_authority': True}
        memory_id = remember(runtime, 'nanalink.feed.' + event.key, body,
                             scope=binding.scope, privacy='PUBLIC')
        key = 'local.nanalink.feed.' + event.key
        surface = SurfaceEnvelope(domain='LOCAL_INTERACTION', subject_id=runtime.identity_id,
                platform='web.feed', surface=binding.surface, adapter=binding.adapter,
                entity_id=binding.entity_id, conversation_id=event.conversation_id,
                session_id=binding.binding_id, event_kind=event.kind,
                occurred_at_us=event.occurred_at_us, observed_at_us=now,
                correlation_id=event.event_id, privacy_class='PUBLIC',
                source_reference='local:nanalink:feed:' + event.key,
                source_event_key=event.key)
        from ..continuity.surfaces import source_key
        key = source_key(surface)
        previous = runtime.store.db.execute('SELECT queue_id FROM runtime_queue WHERE source_key=?', (key,)).fetchone()
        if previous:
            return {'state': 'SOURCE_QUEUED_NOT_JUDGED', 'queue_id': previous[0],
                    'source_key': key, 'source_memory_id': memory_id,
                    'external_delivery': False, 'execution_authority': False}
        inp = SubjectInput(domain='SOURCED_LIFE', source_key=key, kind='WAKE', origin='SELF_WAKE',
                entity_id=binding.entity_id, scope=binding.scope, observed_at_us=now,
                occurred_at_us=event.occurred_at_us, privacy_class='PUBLIC',
                source_memory_ids=(memory_id,), surface=surface)
        queue_id = runtime.submit(RuntimeEvent(event_type='WORLD_EVENT', trigger='ENVIRONMENT_CHANGE',
                input=inp, causes=(Cause(kind='MEMORY', reference_id=memory_id),), due_at_us=now))
        return {'state': 'SOURCE_QUEUED_NOT_JUDGED', 'queue_id': queue_id,
                'source_key': key, 'source_memory_id': memory_id,
                'external_delivery': False, 'execution_authority': False}
