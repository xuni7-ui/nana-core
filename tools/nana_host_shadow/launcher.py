"""Single-command bounded start/stop; no SSH, shell, host SDK or pip operations."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import sys
import time
import uuid
from .metadata import preflight, schema_only
from .safety import APPROVED_SHA, CORE_FINGERPRINT, canonical, checked_path, digest, private_file, read_json, verify_bundle

MARKER = {'source_commit': APPROVED_SHA, 'core_fingerprint': CORE_FINGERPRINT, 'mode': 'PROBE_ONLY_SHADOW', 'schema': 1}
PROTECTED = {'shadow.db', 'shadow.db.lock', 'shadow.db-wal', 'shadow.db-shm', 'session.lock',
             'workspace_manifest.json', 'identity_metadata.json', 'probe_metadata.json', 'session.json', 'stop_request.json', 'reports'}


def workspace(path, *, create=False):
    p = checked_path(path, directory=True, missing=create)
    if not p.exists():
        p.mkdir(mode=0o700)
        private_file(p / 'workspace_manifest.json', MARKER)
        (p / 'reports').mkdir(mode=0o700)
    st = p.stat()
    if st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise ValueError('PRIVATE_OWNED_SHADOW_DIRECTORY_REQUIRED')
    if read_json(p / 'workspace_manifest.json') != MARKER:
        raise ValueError('UNKNOWN_WORKSPACE_BLOCKED')
    if set(x.name for x in p.iterdir()) - PROTECTED:
        raise ValueError('UNEXPECTED_WORKSPACE_FILES')
    for name in PROTECTED:
        item = p / name
        if item.exists() or item.is_symlink():
            checked_path(item, directory=name == 'reports')
    return p


def lock_session(w, *, nonblocking=True):
    p = checked_path(w / 'session.lock', missing=True)
    fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
        return fd
    except BaseException:
        os.close(fd)
        raise


def active(w):
    try:
        fd = lock_session(w)
    except BlockingIOError:
        return True
    os.close(fd)
    return False


def start(bundle, path, *, host_instance='operator-host', window_seconds=30):
    if type(window_seconds) is not int or not 0 <= window_seconds <= 600:
        raise ValueError('BOUNDED_WINDOW_REQUIRED')
    m = verify_bundle(bundle)
    pf = preflight(bundle)
    if not pf['adapter_local_probe_ready']:
        raise ValueError('PREFLIGHT_INCOMPATIBLE')
    # Ignore ambient PYTHONPATH for Core selection and verify actual module path.
    # Use the host's existing compatible dependencies; no install/restart required.
    src = str(Path(bundle) / 'src')
    sys.path.insert(0, src)
    import nana_core
    if Path(nana_core.__file__).resolve().parent != Path(src).resolve() / 'nana_core':
        raise ValueError('APPROVED_CORE_IMPORT_REQUIRED')
    w = workspace(path, create=True)
    fd = lock_session(w)
    state_path = w / 'session.json'
    previous = read_json(state_path) if state_path.exists() else None
    run_id = uuid.uuid4().hex
    state = {'run_id': run_id, 'phase': 'RUNNING', 'pid': os.getpid(), 'host_instance': host_instance,
             'source_commit': m['source_commit'], 'bundle_manifest_hash': digest((Path(bundle) / 'bundle_manifest.json').read_bytes()),
             'prior_termination': 'UNKNOWN' if previous and previous['phase'] == 'RUNNING' else 'CLEAN_OR_FIRST_START',
             'started_at_unix_ns': time.time_ns(), 'window_seconds': window_seconds, 'observer_kind': 'adapter_local_probe_only'}
    stopped = [False]
    def stop_signal(signum, frame):
        stopped[0] = True
    prior_handlers = {sig: signal.signal(sig, stop_signal) for sig in (signal.SIGTERM, signal.SIGINT)}
    def requested():
        if stopped[0]:
            return True
        p = w / 'stop_request.json'
        return p.exists() and read_json(p).get('run_id') == run_id
    report = None
    try:
        private_file(state_path, state, replace=True)
        from .runtime import probe_session
        report = probe_session(w, host_instance=host_instance, window_seconds=window_seconds, stop_requested=requested)
        report.update({'run_id': run_id, 'source_commit': APPROVED_SHA, 'core_fingerprint': CORE_FINGERPRINT,
                       'bundle_manifest_hash': state['bundle_manifest_hash'], 'prior_termination': state['prior_termination'],
                       'store_closed': True, 'shadow_runtime_stopped': True})
        private_file(w / 'reports' / (run_id + '.json'), report)
        state.update(phase='STOPPED', report='reports/' + run_id + '.json')
        return report
    except BaseException as exc:
        state.update(phase='FAILED', failure=exc.code if hasattr(exc, 'code') else type(exc).__name__,
                     observer_and_store_cleanup='finally blocks attempted; validate next startup')
        raise
    finally:
        try:
            private_file(state_path, state, replace=True)
            stop = w / 'stop_request.json'
            if stop.exists() and read_json(stop).get('run_id') == run_id:
                stop.unlink()
        finally:
            for sig, handler in prior_handlers.items():
                signal.signal(sig, handler)
            os.close(fd)


def stop(path):
    w = workspace(path)
    if not active(w):
        return {'status': 'INACTIVE', 'signals_sent': 0, 'files_deleted': 0}
    state = read_json(w / 'session.json')
    private_file(w / 'stop_request.json', {'run_id': state['run_id'], 'reason': 'operator_stop'}, replace=True)
    return {'status': 'STOP_REQUESTED', 'run_id': state['run_id'], 'signals_sent': 0}


def rollback(path):
    w = workspace(path)
    stop(w)
    deadline = time.monotonic() + 10
    while active(w) and time.monotonic() < deadline:
        time.sleep(.05)
    if active(w):
        return {'status': 'BLOCKED_RUNTIME_STILL_ACTIVE', 'signals_sent': 0, 'evidence_deleted': 0}
    state = read_json(w / 'session.json') if (w / 'session.json').exists() else None
    if (w / 'stop_request.json').exists():
        checked_path(w / 'stop_request.json').unlink()
    return {'status': 'PASS' if state and state['phase'] == 'STOPPED' else 'UNKNOWN_UNCLEAN_TERMINATION',
            'runtime_active': False, 'observer_registration': 'adapter-local only; no host hook installed',
            'evidence_deleted': 0, 'database_deleted': False, 'production_files_modified': 0,
            'execution_owner_changed': False, 'memory_authority_changed': False, 'legacy_health': 'UNKNOWN'}


def collect(path):
    w = workspace(path)
    if active(w):
        raise ValueError('STOP_BEFORE_COLLECT')
    reports = []
    for p in sorted((w / 'reports').glob('*.json')):
        r = read_json(p)
        reports.append({'run_id': r['run_id'], 'sha256': digest(p.read_bytes()), 'status': r['status'],
                        'scope': r['scope'], 'FIRST_REAL_CLOUD_SHADOW': r['FIRST_REAL_CLOUD_SHADOW']})
    return {'source_commit': APPROVED_SHA, 'status': 'ENGINEERING_EVIDENCE_ONLY', 'reports': reports,
            'identity': read_json(w / 'identity_metadata.json') if (w / 'identity_metadata.json').exists() else None,
            'runtime_active': False, 'private_content_included': False,
            'database_exported': False, 'real_host_binding': 'UNVERIFIED',
            'session': read_json(w / 'session.json') if (w / 'session.json').exists() else None}


def main():
    sys.dont_write_bytecode = True
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', default=str(Path(__file__).parents[2]))
    sub = p.add_subparsers(dest='command', required=True)
    pf = sub.add_parser('preflight'); pf.add_argument('--path', action='append', default=[])
    run = sub.add_parser('start'); run.add_argument('--workdir', required=True); run.add_argument('--host-instance', default='operator-host'); run.add_argument('--window-seconds', type=int, default=30)
    for cmd in ('stop', 'rollback', 'collect'):
        parser = sub.add_parser(cmd); parser.add_argument('--workdir', required=True)
    schema = sub.add_parser('schema-only'); schema.add_argument('--frozen-snapshot', required=True)
    a = p.parse_args()
    try:
        if a.command == 'preflight':
            report = preflight(a.bundle, [s.split('=', 1) for s in a.path])
        elif a.command == 'start':
            report = start(a.bundle, a.workdir, host_instance=a.host_instance, window_seconds=a.window_seconds)
        elif a.command == 'stop':
            report = stop(a.workdir)
        elif a.command == 'rollback':
            report = rollback(a.workdir)
        elif a.command == 'collect':
            report = collect(a.workdir)
        else:
            report = schema_only(a.frozen_snapshot)
        print(canonical(report))
    except Exception as exc:
        # No exception message/path/body is echoed: provider/errors can contain
        # sensitive material. No network/API endpoint is ever loaded here.
        print(canonical({'status': 'BLOCKED', 'error_category': exc.code if hasattr(exc, 'code') else type(exc).__name__,
                         'production_calls': 0, 'private_records_read': 0}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
