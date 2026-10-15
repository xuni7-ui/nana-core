"""Local Store ownership. Availability yields to the existing writer lock."""
import os
from pathlib import Path
from ..contracts import CoreError
from ..storage import uid


def process_identity(pid=None):
    pid = pid or os.getpid()
    raw=Path(f'/proc/{pid}/stat').read_text()
    # Comm may contain spaces/parentheses; fields begin after the last ')'.
    start=raw.rsplit(')',1)[1].split()[19]
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    return start,boot


class RuntimeClock:
    def __init__(self, source, high_water=0):
        self.source=source
        self.base_utc=max(source.utc_now_us(),high_water)
        self.base_mono=source.monotonic_ns()
        self.last=self.base_utc

    def utc_now_us(self):
        elapsed=max(0,self.source.monotonic_ns()-self.base_mono)//1000
        self.last=max(self.last,self.source.utc_now_us(),self.base_utc+elapsed)
        return self.last

    def monotonic_ns(self):
        return self.source.monotonic_ns()


class VirtualClock:
    def __init__(self, now_us=1_791_590_400_000_000):
        self.now_us,self.mono=now_us,0

    def utc_now_us(self): return self.now_us
    def monotonic_ns(self): return self.mono
    def advance(self, microseconds):
        if microseconds < 0: raise ValueError('use explicit wall rollback injection')
        self.now_us+=microseconds;self.mono+=microseconds*1000


class RuntimeLease:
    def __init__(self, store, config):
        self.store,self.config=store,config
        self.instance_id,self.pid=uid(),os.getpid()
        self.start,self.boot=process_identity()
        self.identity_id=store.identity['identity_id']
        self.epoch=None

    def acquire(self):
        quarantine=self.store.one('core_meta','recovery_quarantine')
        if quarantine and quarantine['value_json']=='true':
            raise CoreError('RUNTIME_RESTORE_QUARANTINED')
        # Store already holds exclusive flock. Unexpired old lease cannot keep a
        # dead/released local process alive; new epoch fences stale handles.
        old=self.store.one('runtime_lease',self.identity_id)
        self.epoch=(old['epoch'] if old else 0)+1
        now=self.store.clock.utc_now_us()
        row={'identity_id':self.identity_id,'instance_id':self.instance_id,'epoch':self.epoch,
            'state':'ACTIVE','pid':self.pid,'process_start':self.start,'boot_id':self.boot,
            'acquired_at_us':now,'heartbeat_at_us':now,'expires_at_us':now+self.config.lease_us,'clock_high_water_us':now}
        self.store.db.execute('BEGIN IMMEDIATE')
        try:
            self.store._put('runtime_lease',row)
            self.store._put('core_meta',{'key':'runtime.managed','value_json':'true'})
            self.store.db.execute('COMMIT')
        except BaseException:
            self.store.db.execute('ROLLBACK');raise
        self.store._runtime_guard=self.assert_current
        return self.epoch

    def assert_current(self):
        row=self.store.one('runtime_lease',self.identity_id)
        if (not row or row['instance_id']!=self.instance_id or row['epoch']!=self.epoch or row['state']!='ACTIVE'
            or row['pid']!=os.getpid() or (row['process_start'],row['boot_id'])!=(self.start,self.boot)
            or self.store.clock.utc_now_us()>=row['expires_at_us']):
            raise CoreError('RUNTIME_LEASE_LOST')
        return row

    def heartbeat(self, *, force=False):
        row=self.assert_current()
        now=self.store.clock.utc_now_us()
        if not force and now-row['heartbeat_at_us']<self.config.heartbeat_us:
            return
        # Operational updates do not invalidate a frozen cognitive context.
        self.store.db.execute('BEGIN IMMEDIATE')
        try:
            self.assert_current()
            self.store._put('runtime_lease',{**row,'heartbeat_at_us':now,
                'expires_at_us':now+self.config.lease_us,'clock_high_water_us':now})
            self.store.db.execute('COMMIT')
        except BaseException:
            self.store.db.execute('ROLLBACK');raise

    def release(self):
        row=self.store.one('runtime_lease',self.identity_id)
        if row and (row['instance_id'],row['epoch'])==(self.instance_id,self.epoch):
            now=self.store.clock.utc_now_us()
            self.store.db.execute('BEGIN IMMEDIATE')
            try:
                self.store._put('runtime_lease',{**row,'state':'STOPPED','expires_at_us':now,'clock_high_water_us':now})
                self.store.db.execute('COMMIT')
            except BaseException:
                self.store.db.execute('ROLLBACK');raise
