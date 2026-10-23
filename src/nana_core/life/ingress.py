"""Bounded concurrent transport inbox; original owner alone enters C.

Queue bodies are volatile. Receipt ACCEPTED means queued, not judged/delivered.
After a crash, an uncommitted volatile input is UNKNOWN, never replayed. Durable
idempotency is the existing SurfaceSession/subject event source key.
"""
import threading,heapq
from ..contracts import CoreError
from ..storage import digest
from .surfaces import SurfaceObservation

class SurfaceIngress:
    def __init__(self,app,*,capacity=32):
        if not 1<=capacity<=64:raise CoreError('SURFACE_INGRESS_BOUND')
        self.app=app;self.capacity=capacity;self._owner=threading.get_ident();self._lock=threading.Lock();self._queue=[];self._keys={};self._serial=0;self._delivering=False;self._closed=False
    def offer(self,observation,*,urgency='USER'):
        if type(observation) is not SurfaceObservation or urgency not in {'USER','BACKGROUND'}:raise CoreError('SURFACE_TYPED_INPUT_REQUIRED')
        o=SurfaceObservation.model_validate_json(observation.model_dump_json());self.app.surfaces._binding(o.binding_id)
        key=(o.binding_id,o.event_id);sha=digest(o.model_dump(mode='json'))
        with self._lock:
            if self._closed:raise CoreError('SURFACE_INGRESS_CLOSED')
            if key in self._keys:
                if self._keys[key]!=sha:raise CoreError('SURFACE_EVENT_COLLISION')
                return {'state':'ALREADY_QUEUED','not_delivered':True}
            if len(self._queue)>=self.capacity:raise CoreError('SURFACE_INGRESS_BACKPRESSURE')
            self._serial+=1;heapq.heappush(self._queue,(0 if urgency=='USER' else 1,self._serial,o));self._keys[key]=sha
            return {'state':'QUEUED_NOT_JUDGED','ingress_sequence':self._serial,'not_delivered':True,'ordering':'USER_PRIORITY_THEN_HOST_ARRIVAL_SEQUENCE'}
    def drain(self):
        if threading.get_ident()!=self._owner:raise CoreError('SURFACE_SINGLE_OWNER_REQUIRED')
        if self._delivering:return None
        with self._lock:
            if not self._queue:return None
            _,sequence,o=heapq.heappop(self._queue);self._keys.pop((o.binding_id,o.event_id))
        self._delivering=True
        try:return {'sequence':sequence,'binding_id':o.binding_id,'event_id':o.event_id,'result':self.app.surfaces.receive(o)}
        finally:self._delivering=False
    def pending(self):
        with self._lock:return len(self._queue)
    def close(self):
        with self._lock:self._closed=True;self._queue.clear();self._keys.clear()
