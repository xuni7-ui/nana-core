"""API-neutral no-response callback. Real projection/registration is source-gated.

A transport marker is insufficient: only a privately issued permit attached by an
operator-controlled internal dispatch can enter. Never attach to private traffic.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from .sanitize import Metadata

@dataclass(frozen=True, slots=True)
class ProbePermit:
    probe_id: str

class ShadowObserver:
    def __init__(self, sanitizer, sink, *, timeout=.2, logger=None):
        if not 0 < timeout <= 2: raise ValueError('INVALID_OBSERVER_DEADLINE')
        self.sanitizer, self._sink = sanitizer, sink
        self.timeout, self._logger = timeout, logger
        self._permits = {}
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='nana-shadow-metadata')
        self._pending = None
        self.active = True
        self.last_result = {'status': 'IDLE'}

    def issue_local_permit(self, probe_id):
        if probe_id not in self.sanitizer.probe_ids: raise ValueError('PROBE_SCOPE_BLOCKED')
        permit = ProbePermit(probe_id)
        self._permits[id(permit)] = permit
        return permit

    def _record(self, code):
        self.last_result = {'status': code}
        try:
            if self._logger is not None: self._logger(code)  # fixed code only, never event/exception
        except Exception:
            pass

    async def callback(self, metadata_input, *, permit=None):
        # No generator/no return-value response/no calls to event mutation/reply.
        try:
            if not self.active or self._permits.get(id(permit)) is not permit or type(permit) is not ProbePermit:
                self._record('DROP_UNAUTHORIZED_PROBE'); return None
            result = self.sanitizer.sanitize(metadata_input)
            if result.status != 'ACCEPT': self._record(result.status); return None
            metadata = self.sanitizer.validate_output(result.metadata)
            if metadata.probe_id != permit.probe_id: self._record('DROP_PERMIT_SCOPE'); return None
            if self._pending is not None and not self._pending.done():
                self._record('DROP_BUSY'); return None
            # Serial worker owns Store; never performs SQLite on AstrBot event loop.
            # Timeout does not kill a local transaction. Completion may be UNKNOWN;
            # durable dedup resolves it, and no executor exists in this sink.
            self._pending = self._worker.submit(self._sink.accept, metadata)
            wrapped = asyncio.wrap_future(self._pending)
            wrapped.add_done_callback(_consume_exception)
            value = await asyncio.wait_for(asyncio.shield(wrapped), self.timeout)
            if type(value) is not dict or value.get('barrier_result') != 'SHADOW_BLOCKED':
                self._record('DROP_CORE_CONTRACT'); return None
            self.last_result = {'status': 'RECORDED', 'core': value}
        except asyncio.CancelledError:
            self._record('DROP_CANCELLED')
        except TimeoutError:
            self._record('UNKNOWN_LOCAL_STORE_COMPLETION')
        except Exception:
            self._record('DROP_SHADOW_FAILURE')
        return None

    async def close(self):
        self.active = False
        self._permits.clear()
        # FIFO close runs after an already-started bounded local transaction.
        future = self._worker.submit(self._sink.close)
        try:
            wrapped = asyncio.wrap_future(future)
            wrapped.add_done_callback(_consume_exception)
            await asyncio.wait_for(asyncio.shield(wrapped), 2.)
        except (Exception, asyncio.CancelledError):
            self._record('UNKNOWN_CLOSE')
        finally:
            self._worker.shutdown(wait=False, cancel_futures=False)


def _consume_exception(future):
    # Prevent asyncio's unhandled-future logger from printing private exception
    # messages when completion arrives AFTER cancellation/timeout.
    if not future.cancelled():
        future.exception()
