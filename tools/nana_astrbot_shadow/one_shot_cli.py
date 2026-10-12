"""Metadata-only operator tools. No production loader/auth/network/messages.

Default command is read-only status. There is no fixture trust, force, unsafe,
environment override, Dashboard/JWT, or event ingress command in this CLI.
"""
import argparse
import json
import secrets
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from tools.nana_host_shadow.safety import checked_path,canonical,read_json
from .one_shot import ReceiptLedger,ProductionTrustStore,parse_receipt
from .one_shot_ingress import OneShotCoreSink,OneShotSanitizer,OneShotObserver
from .one_shot_proof import collect,verify_first_real_message_shadow,mark_verified
from .sanitize import MetadataSanitizer
from .core_sink import MetadataCoreSink

class ReadOnlyStoreView:
    """Approved Store readback methods on a metadata-only read transaction.

    No recovery/init/checkpoint/migration writes, no new lock/WAL creation. Explicit
    Shadow file required. Live read-only view is safe; never use immutable on WAL.
    """
    def __init__(self,path):
        from nana_core.storage.sqlite_store import Store
        p=checked_path(path)
        if sqlite3.sqlite_version_info<(3,51,3):raise ValueError('SQLITE_VERSION_UNSUPPORTED')
        self.db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA query_only=ON');self.db.execute('BEGIN')
    def close(self):self.db.close()
    def one(self,*a):
        from nana_core.storage.sqlite_store import Store
        return Store.one(self,*a)
    def all(self,*a):
        from nana_core.storage.sqlite_store import Store
        return Store.all(self,*a)
    def event(self,*a):
        from nana_core.storage.sqlite_store import Store
        return Store.event(self,*a)
    def artifact(self,*a):
        from nana_core.storage.sqlite_store import Store
        return Store.artifact(self,*a)
    @property
    def identity(self):return self.all('identities')[0]
    def transaction(self,*a,**k):raise ValueError('READ_ONLY_OPERATOR_COMMAND')

@contextmanager
def operator_ledger(directory,*,write=False):
    directory=checked_path(directory,directory=True)
    if directory.stat().st_mode & 0o077:raise ValueError('PRIVATE_SHADOW_DIRECTORY_REQUIRED')
    path=checked_path(directory/'observer-shadow.db')
    for suffix in ('-wal','-shm','.lock'):checked_path(str(path)+suffix,missing=True)
    if write:
        from nana_core.storage import Store
        store=Store(path)
    else:store=ReadOnlyStoreView(path)
    try:
        if not store.one('core_meta','r04.store_binding') or not store.one('core_meta','cloud.shadow_runtime'):
            raise ValueError('INITIALIZED_SHADOW_ONLY')
        if any(store.all(t) for t in ('actions','attempts','grants','budgets','strategies','goals','plans')):
            raise ValueError('EXECUTION_STORE_BLOCKED')
        yield ReceiptLedger(store,ProductionTrustStore())
    finally:store.close()


def initialize(directory):
    directory=checked_path(directory,directory=True)
    if (directory/'observer-shadow.db').exists():raise ValueError('NEW_SHADOW_STORE_REQUIRED')
    s=MetadataSanitizer(scope='r04-host',hash_key=secrets.token_bytes(32),probe_ids=frozenset({'nana-probe-r04-init'}))
    sink=MetadataCoreSink(directory,s)
    try:
        l=ReceiptLedger(sink._open(),ProductionTrustStore())
        with l.store.transaction('r04.hash_domain_initialized') as tx:
            tx.put('core_meta',{'key':'r04.hash_key','value_json':canonical(s._key.hex())})
            tx.put('core_meta',{'key':'r04.hash_scope','value_json':canonical(s.scope)})
        return {'status':'INITIALIZED','store_binding':l.binding,'identity_id':l.store.identity['identity_id'],
                'hash_scope':s.scope,'production_trust_pins':0,'real_arm_ready':False}
    finally:sink.close()


def build_operator_observer(directory,receipt_id,*,timeout=.2,logger=None):
    """For future source-audited host wiring, not auto-installed/invoked by CLI."""
    with operator_ledger(directory) as l:
        r,v=l.record(receipt_id)
        if v['state']!='ARMED' or not l._review_valid(r,v['review']):raise ValueError('RECEIPT_NOT_TRUSTED_ARMED')
        key=json.loads(l.store.one('core_meta','r04.hash_key')['value_json'])
        scope=json.loads(l.store.one('core_meta','r04.hash_scope')['value_json'])
        if scope!=r.hash_scope:raise ValueError('HASH_SCOPE_MISMATCH')
    s=OneShotSanitizer(scope=scope,hash_key=bytes.fromhex(key),receipt_id=receipt_id)
    sink=OneShotCoreSink(directory,s,receipt_id)
    observer=OneShotObserver(s,sink,timeout=timeout,logger=logger)
    observer.operator_binding_verified=True
    return observer


class _SafeParser(argparse.ArgumentParser):
    def error(self,message):
        # argparse defaults echo invalid values; metadata tools must not do so.
        raise ValueError('CLI_CONTRACT')

def main(argv=None):
    p=_SafeParser(description=__doc__)
    p.add_argument('family',choices=('receipt','observer'))
    p.add_argument('command',nargs='?',default='status',choices=('init','create','inspect','review','arm','status','disarm','verify','collect','finalize'))
    p.add_argument('--directory',required=True)
    p.add_argument('--receipt-id');p.add_argument('--input');p.add_argument('--dry-run',action='store_true')
    try:
        args=p.parse_args(argv)
        if args.dry_run:
            result={'status':'DRY_RUN','files_written':0,'real_arm_ready':False}
        elif args.family=='receipt' and args.command=='init':result=initialize(args.directory)
        else:
            write=args.family=='receipt' and args.command in ('create','review','arm','disarm','finalize')
            with operator_ledger(args.directory,write=write) as l:
                if args.family=='observer' and args.command in ('collect','verify'):
                    if not args.receipt_id:raise ValueError('RECEIPT_ID_REQUIRED')
                    if args.command=='collect':result=collect(l,args.receipt_id)  # absent host claims stay UNKNOWN
                    else:
                        if not args.input:raise ValueError('EVIDENCE_FILE_REQUIRED')
                        result=verify_first_real_message_shadow(read_json(args.input),l)
                elif args.family=='receipt':
                    if args.command=='create':
                        if not args.input:raise ValueError('CANONICAL_RECEIPT_FILE_REQUIRED')
                        file=checked_path(args.input)
                        if file.stat().st_size>4096:raise ValueError('RECEIPT_SIZE')
                        raw=file.read_text();result=l.create(parse_receipt(raw))
                    elif args.command=='review':
                        if not args.input:raise ValueError('REVIEW_FILE_REQUIRED')
                        result=l.review(args.receipt_id,read_json(args.input))
                    elif args.command=='arm':result=l.arm(args.receipt_id)
                    elif args.command=='finalize':
                        if not args.input:raise ValueError('EVIDENCE_FILE_REQUIRED')
                        report=read_json(args.input)
                        if report.get('receipt_id')!=args.receipt_id:raise ValueError('RECEIPT_SCOPE')
                        result=mark_verified(report,l)
                    elif args.command=='disarm':result=l.disarm(args.receipt_id)
                    elif args.command in ('inspect','status','verify'):
                        result=l.status(args.receipt_id)
                        r,v=l.record(args.receipt_id)
                        if args.command=='verify':result={**result,'review_trusted':l._review_valid(r,v['review'])}
                    else:raise ValueError('COMMAND_SCOPE_BLOCKED')
                else:raise ValueError('COMMAND_SCOPE_BLOCKED')
        print(canonical(result));return 0
    except BaseException:
        print(canonical({'status':'BLOCKED','reason':'R04_OPERATOR_POLICY_OR_STATE','host_binding':'UNVERIFIED'}));return 2

if __name__=='__main__':raise SystemExit(main())
