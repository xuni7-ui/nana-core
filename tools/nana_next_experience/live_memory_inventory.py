"""Explicit read-only SQL metadata inventory. No payloads, secrets or index claims.

Run under the already authorized host identity, with an operator-selected live
Store path. This does not open NanaRuntime, acquire a writer or import history.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import stat


def inventory(path):
    path = Path(path).absolute()
    before = path.lstat()
    if path.resolve() != path or not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid():
        raise ValueError('OWNED_REGULAR_LIVE_STORE_REQUIRED')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.5)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        identity = db.execute('SELECT identity_id FROM identities LIMIT 2').fetchall()
        if len(identity) != 1:
            raise ValueError('SINGLE_IDENTITY_REQUIRED')
        result = {
            'evidence': 'EXPLICIT_READ_ONLY_STORE_METADATA_NOT_VECTOR_QUALIFICATION',
            'identity_id': identity[0][0],
            'schema': db.execute('PRAGMA user_version').fetchone()[0],
            'memory_groups': [list(r) for r in db.execute(
                'SELECT lifecycle,assessment,privacy_class,count(*) FROM memories GROUP BY lifecycle,assessment,privacy_class')],
            'index_rows': db.execute('SELECT count(*) FROM memory_terms').fetchone()[0],
            'orphan_lexical_rows': db.execute('SELECT count(*) FROM memory_terms t LEFT JOIN memories m ON m.memory_id=t.memory_id WHERE m.memory_id IS NULL').fetchone()[0],
            'physical_indexes': [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name IN ('memories','memory_terms') ORDER BY name")],
            'db_bytes': before.st_size,
            'vector_binding': 'NOT_VERIFIED_REQUIRES_ACTIVE_RUNTIME_INDEX_METADATA',
            'private_payloads_read': False,
        }
        after = path.lstat()
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError('STORE_REPLACED_DURING_INVENTORY')
        return result
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.store), indent=2))
