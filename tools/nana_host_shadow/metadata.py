"""Operator-selected metadata only; no discovery, private records, or repairs."""
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import time
from .safety import checked_path, digest


def preflight(bundle, paths=()):
    from .safety import verify_bundle
    checks = []
    def add(name, status, detail):
        checks.append({'check': name, 'status': status, 'detail': detail})
    add('python', 'PASS' if sys.version_info >= (3, 12) else 'BLOCKED', platform.python_version())
    add('sqlite', 'PASS' if sqlite3.sqlite_version_info >= (3, 51, 3) else 'BLOCKED', sqlite3.sqlite_version)
    try:
        version = importlib.metadata.version('pydantic')
        add('pydantic', 'PASS' if version == '2.13.4' else 'BLOCKED', version)
    except importlib.metadata.PackageNotFoundError:
        add('pydantic', 'BLOCKED', 'missing; no automatic install')
    m = verify_bundle(bundle)
    add('approved_package', 'PASS', {'commit': m['source_commit'], 'core_fingerprint': m['core_fingerprint']})
    for package in ('astrbot', 'astrbot-plugin-iris-chat-memory'):
        try:
            add(package, 'WARN', {'distribution_version': importlib.metadata.version(package), 'runtime_version': 'UNKNOWN'})
        except importlib.metadata.PackageNotFoundError:
            add(package, 'UNKNOWN', 'distribution metadata absent; no host module imported')
    for label, path in paths:
        try:
            p = checked_path(path, directory=Path(path).is_dir()); st = p.stat()
            add('path:' + label, 'PASS', {'exists': True, 'uid': st.st_uid, 'gid': st.st_gid,
                                        'mode': oct(st.st_mode & 0o777), 'contents_read': False})
        except FileNotFoundError:
            add('path:' + label, 'BLOCKED', 'absent')
        except (OSError, ValueError):
            add('path:' + label, 'UNKNOWN', 'unavailable or unsafe path; no contents read')
    add('disk', 'PASS' if shutil.disk_usage(bundle).free >= 64 * 1024**2 else 'BLOCKED',
        {'free_bytes': shutil.disk_usage(bundle).free})
    # uname/syscalls disclose metadata only. No /etc/os-release, configuration or
    # process argument/environment reads, which could expose secrets.
    add('os', 'PASS', {'system': platform.system(), 'release': platform.release(), 'distro': 'UNKNOWN'})
    add('host', 'PASS', {'hostname_hash': digest(platform.node()), 'uid': os.getuid(), 'gid': os.getgid(),
                         'filesystem_type': 'UNKNOWN', 'process_id': os.getpid(), 'container_identity': 'UNKNOWN'})
    add('dynamic_observer', 'UNKNOWN', {'registration': 'UNVERIFIED', 'unregistration': 'UNVERIFIED',
                                      'restart_required': 'UNKNOWN', 'message_stream_attached': False})
    add('production_health', 'UNKNOWN', 'no production process channel inspected')
    return {'status': 'BLOCKED' if any(c['status'] == 'BLOCKED' for c in checks) else 'UNKNOWN',
            'checks': checks, 'adapter_local_probe_ready': not any(c['status'] == 'BLOCKED' for c in checks),
            'astrbot_hook_ready': False, 'automatic_repairs': False, 'files_written': 0,
            'private_records_read': 0, 'secret_values_read': 0}


def schema_only(path):
    """A frozen SQLite file only. No SELECT of application rows or SQL defaults.

    immutable=1 avoids creation/modification of WAL/SHM. An existing journal/WAL
    is BLOCKED rather than silently inspecting a possibly inconsistent database.
    The caller must supply a reviewed frozen file, never an implicit live DB.
    """
    p = checked_path(path)
    if any(Path(str(p) + suffix).exists() for suffix in ('-wal', '-journal')):
        raise ValueError('FROZEN_SCHEMA_SNAPSHOT_REQUIRED')
    db = sqlite3.connect(p.as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 256 * 1024)
        deadline = time.monotonic() + 2
        db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        def metadata_only(action, table, column, database, trigger):
            if action == sqlite3.SQLITE_READ and table not in {'sqlite_master', 'sqlite_schema', 'pragma_table_info', 'pragma_index_list'}:
                return sqlite3.SQLITE_DENY
            if action in {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        db.set_authorizer(metadata_only)
        tables = db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name IN ('memories','nodes','edges') ORDER BY name").fetchall()
        # Column/index identifiers are exposed metadata, never default values or
        # stored SQL definitions (defaults can contain sensitive strings).
        result = []
        for (name,) in tables:
            cols = db.execute('SELECT name,type,"notnull",pk FROM pragma_table_info(?)', (name,)).fetchall()
            indexes = db.execute('SELECT name,"unique",origin,partial FROM pragma_index_list(?)', (name,)).fetchall()
            result.append({'table': name, 'columns': [{'name': c[0], 'type': c[1], 'not_null': bool(c[2]), 'primary_key': c[3]} for c in cols],
                           'indexes': [{'name': i[0], 'unique': bool(i[1]), 'origin': i[2], 'partial': bool(i[3])} for i in indexes]})
        return {'status': 'UNASSESSED', 'schema_hash': digest(result), 'tables': result,
                'user_version': db.execute('PRAGMA user_version').fetchone()[0],
                'private_records_read': 0, 'application_row_queries': 0, 'writes': 0,
                'scope': 'schema metadata only; compatibility needs source-version comparison; JSON/FAISS not opened'}
    finally:
        db.close()
