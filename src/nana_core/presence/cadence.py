"""One owner-thread arbiter; producers never touch SQLite or decide Subject will."""
from collections import deque
from dataclasses import dataclass,field
import threading
from ..contracts import CoreError
from .contracts import RuntimeEvent

class CognitionPreempted(CoreError):
    def __init__(self):super().__init__('COGNITION_PREEMPTED')

@dataclass
class IngressReceipt:
    """Pending is volatile; durable acknowledgement only after queue commit."""
    ready: threading.Event = field(default_factory=threading.Event)
    queue_id: str | None = None
    error: str | None = None
    def wait(self,timeout=5):
        if not self.ready.wait(timeout):raise TimeoutError('INGRESS_NOT_YET_DURABLE')
        if self.error:raise CoreError(self.error)
        return self.queue_id

class Cadence:
    def __init__(self,capacity,max_wait):
        self.owner=threading.get_ident();self.condition=threading.Condition()
        self.mailbox=deque();self.capacity=capacity;self.max_wait=max_wait
        self.generation=0;self.idle_rounds=0;self.closed=False
    def assert_owner(self):
        if threading.get_ident()!=self.owner:raise CoreError('RUNTIME_OWNER_THREAD_REQUIRED_USE_POST')
    def post(self,event):
        if type(event) is not RuntimeEvent:raise CoreError('TYPED_RUNTIME_EVENT_REQUIRED')
        raw=event.model_dump_json()
        if len(raw.encode())>65536:raise CoreError('RUNTIME_INGRESS_TOO_LARGE')
        receipt=IngressReceipt()
        with self.condition:
            if self.closed:raise CoreError('RUNTIME_STOPPED')
            if len(self.mailbox)>=self.capacity:raise CoreError('RUNTIME_MAILBOX_BACKPRESSURE')
            self.mailbox.append((raw,receipt));self.generation+=1;self.condition.notify_all()
        return receipt
    def drain(self,submit):
        self.assert_owner()
        for _ in range(self.capacity):
            with self.condition:
                if not self.mailbox:break
                raw,receipt=self.mailbox.popleft()
            try:receipt.queue_id=submit(RuntimeEvent.model_validate_json(raw))
            except Exception:receipt.error='RUNTIME_INGRESS_REJECTED'
            finally:receipt.ready.set()
    def notify(self):
        with self.condition:self.generation+=1;self.condition.notify_all()
    def stamp(self):
        with self.condition:return self.generation
    def wait(self,seconds,stamp):
        self.assert_owner()
        with self.condition:
            if self.mailbox or self.closed or self.generation!=stamp:return
            self.condition.wait(max(0,min(seconds,self.max_wait)))
    def close(self):
        with self.condition:
            self.closed=True
            for _,r in self.mailbox:r.error='RUNTIME_STOPPED';r.ready.set()
            self.mailbox.clear();self.generation+=1;self.condition.notify_all()
