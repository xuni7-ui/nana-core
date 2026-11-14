"""Bounded volatile delivery, not a second EventBus or durable source ledger.

Persistence/deduplication/UNKNOWN across restart belong to the original Core.
An event is removed BEFORE dispatch; a lost result never requeues an effect.
Per conversation order wins over priority; priority selects only queue heads.
"""
import asyncio
from collections import OrderedDict, deque
from .contracts import Event, OperationReceipt, Outcome
from ..contracts import CoreError


class EventTransport:
    def __init__(self, *, capacity=64, per_account=16, dedupe=512):
        if not 1 <= per_account <= capacity <= 4096 or not capacity <= dedupe <= 65536:
            raise ValueError('transport bounds')
        self.capacity, self.per_account, self.dedupe = capacity, per_account, dedupe
        self.queues, self.seen, self.counts = OrderedDict(), OrderedDict(), {}
        self.size = 0
        self.metrics = dict(accepted=0, duplicate=0, rejected=0, dispatched=0, unknown=0)
        self.closed = False
        self._draining = False
        self._ticket = 0

    def offer(self, event):
        if self.closed:
            return 'CANCELLED'
        event = Event.model_validate_json(event.model_dump_json())
        if event.key in self.seen:
            if self.seen[event.key] != event.raw_sha256:
                raise CoreError('NANALINK_EVENT_ID_COLLISION')
            self.metrics['duplicate'] += 1
            return 'DUPLICATE'
        count = self.counts.get(event.account.key, 0)
        if self.size >= self.capacity or count >= self.per_account:
            self.metrics['rejected'] += 1
            return 'BACKPRESSURE'
        self._ticket += 1
        self.queues.setdefault(event.ordering_key, deque()).append((self._ticket, event))
        self.size += 1
        self.counts[event.account.key] = count + 1
        self.seen[event.key] = event.raw_sha256
        # Pending identities are never evicted; dedupe >= capacity.
        pending = {e.key for q in self.queues.values() for _, e in q}
        for key in tuple(self.seen):
            if len(self.seen) <= self.dedupe:
                break
            if key not in pending:
                del self.seen[key]
        self.metrics['accepted'] += 1
        return 'QUEUED'

    async def drain_once(self, handler):
        if self._draining:
            raise CoreError('NANALINK_SINGLE_DRAINER_REQUIRED')
        if not self.size:
            return None
        self._draining = True
        # Priority is bounded by an aging ticket to prevent starvation.
        key = min(self.queues, key=lambda k: (self.queues[k][0][0] // self.capacity,
                   self.queues[k][0][1].priority, self.queues[k][0][0]))
        _, event = self.queues[key].popleft()
        if not self.queues[key]:
            del self.queues[key]
        self.size -= 1
        self.counts[event.account.key] -= 1
        try:
            result = await handler(event)
            receipt = OperationReceipt.model_validate(result.model_dump())
        except asyncio.CancelledError:
            self.metrics['unknown'] += 1
            raise
        except Exception:
            receipt = OperationReceipt(operation_id=event.key, outcome=Outcome.UNKNOWN,
                                       reason='CORE_COMPLETION_UNKNOWN_NO_RETRY')
        finally:
            self._draining = False
        self.metrics['dispatched'] += 1
        self.metrics['unknown'] += receipt.outcome == Outcome.UNKNOWN
        return receipt

    def close(self):
        """Stop admission; caller can drain or explicitly cancel unsent inputs."""
        self.closed = True
        cancelled = [OperationReceipt(operation_id=e.key, outcome=Outcome.CANCELLED,
                                     reason='SHUTDOWN_BEFORE_DISPATCH') for q in self.queues.values() for _, e in q]
        self.queues.clear()
        self.size = 0
        self.counts.clear()
        return cancelled
