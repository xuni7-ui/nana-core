"""Explicit local recovery of interrupted attempts, never provider reconciliation.

The trusted host operator must run this on the actual Store-owning host after
the previous owner has exited. The original Store lock and a fresh RuntimeLease
fence the previous epoch. No network, model, effect, or new Subject is started.
"""
import os
import sqlite3
import hashlib
import json
from pathlib import Path

from ..clock import Clock
from ..contracts import CoreError
from ..continuity import ContinuityStore
from ..presence.authority import RuntimeClock, RuntimeLease, process_identity
from .application import runtime_config
from .config import load_config


def recover_interrupted(home, *, expected_epoch, expected_subject, expected_lineage):
    home = Path(home).absolute()
    path = home / 'subject/self.db'
    if (type(expected_epoch) is not int or expected_epoch < 1 or home.resolve() != home
            or path.resolve() != path or not path.is_file() or path.stat().st_uid != os.geteuid()):
        raise CoreError('INTERRUPTED_RECOVERY_BINDING_REQUIRED')
    from .live_api.supervisor import existing_identity
    identity,lineage,_ = existing_identity(home)
    if (identity,lineage)!=(expected_subject,expected_lineage):
        raise CoreError('INTERRUPTED_RECOVERY_IDENTITY_MISMATCH')
    config = runtime_config(load_config(home))
    # Never let this maintenance path bootstrap or migrate an identity/schema.
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA user_version').fetchone()[0] != 13:
            raise CoreError('INTERRUPTED_RECOVERY_SCHEMA_REQUIRED')
        lease_rows = db.execute('SELECT epoch,pid,process_start,boot_id FROM runtime_lease').fetchall()
        if len(lease_rows) != 1 or lease_rows[0][0] != expected_epoch:
            raise CoreError('INTERRUPTED_RECOVERY_EPOCH_CHANGED')
    with ContinuityStore(path, Clock(), schema_target=13) as store:
        observed_lineage = hashlib.sha256(json.dumps({'identity_id':store.identity['identity_id'],
            'created_event_id':store.identity['created_event_id']},sort_keys=True).encode()).hexdigest()
        if (store.identity['identity_id'],observed_lineage)!=(expected_subject,expected_lineage):
            raise CoreError('INTERRUPTED_RECOVERY_IDENTITY_MISMATCH')
        previous = store.one('runtime_lease', store.identity['identity_id'])
        if not previous or previous['epoch'] != expected_epoch:
            raise CoreError('INTERRUPTED_RECOVERY_EPOCH_CHANGED')
        world = store.db.execute("SELECT request_id,owner_epoch FROM cognitive_requests WHERE state IN ('PREPARED','CALLING')").fetchall()
        legacy = store.db.execute("SELECT call_id,owner_epoch FROM runtime_cognition_calls WHERE state='RESERVED'").fetchall()
        if any(row['owner_epoch'] > expected_epoch for row in (*world, *legacy)):
            raise CoreError('INTERRUPTED_RECOVERY_FUTURE_EPOCH')
        if not world and not legacy:
            return {'state':'NO_INTERRUPTED_ATTEMPTS','changed':0,'provider_calls':0,'retries':0}
        # A still-live process must not lose its lease merely to clear a gate.
        try:
            actual = process_identity(previous['pid'])
        except FileNotFoundError:
            actual = None
        except (OSError, ValueError):
            raise CoreError('INTERRUPTED_OWNER_UNVERIFIED') from None
        if actual == (previous['process_start'], previous['boot_id']):
            raise CoreError('INTERRUPTED_OWNER_STILL_ALIVE')
        high = max(previous['clock_high_water_us'], store.db.execute('SELECT coalesce(max(recorded_at_us),0) FROM events').fetchone()[0])
        store.clock = RuntimeClock(store.clock, high)
        lease = RuntimeLease(store, config)
        lease.acquire()
        try:
            lease.assert_current()
            with store.transaction('runtime.interrupted_attempts_quarantined',
                    {'cognitive_count':len(world),'runtime_count':len(legacy),'previous_epoch':expected_epoch,
                     'billing':'UNKNOWN','automatic_retry':False}) as tx:
                for row in world:
                    tx.update('cognitive_requests',row['request_id'],state='UNKNOWN',error_code='INTERRUPTED_NO_AUTOMATIC_RETRY')
                for row in legacy:
                    tx.update('runtime_cognition_calls',row['call_id'],state='UNKNOWN')
                lease.assert_current()
            return {'state':'INTERRUPTED_ATTEMPTS_UNKNOWN','changed':len(world)+len(legacy),
                    'cognitive_requests':len(world),'runtime_calls':len(legacy),
                    'provider_calls':0,'retries':0,'billing':'UNKNOWN','reservations_refunded':False,
                    'provider_reconciliation':'NOT_ESTABLISHED'}
        finally:
            lease.release()
