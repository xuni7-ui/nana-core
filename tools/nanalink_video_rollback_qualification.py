"""Isolated synthetic old-reader qualification for source-bound video frames.

Explicitly supply an old Git archive; never opens a user or production Store.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from nana_core.clock import Clock
from nana_core.continuity.memory import MemoryService
from nana_core.life.bilibili import BilibiliSourceAdapter, PublicReading
from nana_core.life.bilibili_frames import BilibiliFrameService, VideoFrame
from tests.person_self.test_nanalink_media_choice import picture
from tests.world_loop.helpers import capture, fresh, policy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-source', type=Path, required=True)
    args = parser.parse_args()
    old = args.old_source.resolve()
    if not (old/'src/nana_core/continuity/store.py').is_file():
        raise SystemExit('OLD_SOURCE_ARCHIVE_REQUIRED')
    script = '''import sys
sys.path.insert(0,sys.argv[1])
from nana_core.clock import Clock
from nana_core.continuity import ContinuityStore
from nana_core.continuity.memory import MemoryService
from nana_core.contracts import CoreError
with ContinuityStore(sys.argv[2], Clock(), schema_target=13) as store:
 assert store.identity['identity_id'] == sys.argv[3]
 parent, video, frame, mode = sys.argv[4:]
 edge=store.db.execute("SELECT 1 FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY' AND parent_id=?",(video,parent)).fetchone()
 assert edge
 for mid in (video,frame):
  if mode=='before':
   assert MemoryService(store).read(mid)['memory_id']==mid
  else:
   try: MemoryService(store).read(mid); raise AssertionError('withdrawn source visible')
   except CoreError as exc: assert exc.code=='MEMORY_UNAVAILABLE'
   assert store.one('memories',mid)['lifecycle']=='DELETED'
 print('IDENTITY_MATCH_DEPENDENCY_OK_'+mode.upper())
'''
    with tempfile.TemporaryDirectory(prefix='nanalink-video-rollback-') as root:
        old_package = old/'src/nana_core'
        if any(path.is_symlink() for path in old_package.rglob('*')):
            raise SystemExit('OLD_SOURCE_SYMLINK_DENIED')
        reader = Path(root)/'reader'
        shutil.copytree(old_package, reader/'nana_core', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        copied = reader/'nana_core'
        files = sorted(path for path in copied.rglob('*') if path.is_file())
        fingerprint = hashlib.sha256()
        for source_file in files:
            fingerprint.update(source_file.relative_to(copied).as_posix().encode()+b'\0'+hashlib.sha256(source_file.read_bytes()).digest())
        if len(files) != 322 or fingerprint.hexdigest() != '0049c39500db44ca2dbcb089bd022502799db44f3aa1a967efae2e469062419d':
            raise SystemExit('OLD_SOURCE_FINGERPRINT_MISMATCH')
        path = Path(root)/'subject.db'
        with fresh(path, Clock()) as runtime:
            identity = runtime.identity_id
            parent = capture(runtime, 'rollback-parent', {'synthetic':'source'})
            app = SimpleNamespace(runtime=runtime, policy=policy())
            reading = PublicReading('synthetic-video', 'VIDEO_READING', runtime.clock.utc_now_us(),
                {'bvid':'BV1t55v6DE2v', 'cid':8, 'duration_seconds':12}, 'SYNTHETIC_FIXTURE')
            video = BilibiliSourceAdapter(app).ingest(reading, parents=(parent,))
            frame = BilibiliFrameService(app).capture(video, (VideoFrame('BV1t55v6DE2v', 8, 3.0, picture(), 'SYNTHETIC_FIXTURE'),))[0]
        def old_check(mode):
            result = subprocess.run([sys.executable, '-I', '-c', script, str(reader), str(path), identity, parent, video, frame, mode],
                                    cwd='/tmp', text=True, capture_output=True, timeout=30)
            if result.returncode or result.stdout.strip() != 'IDENTITY_MATCH_DEPENDENCY_OK_'+mode.upper():
                raise RuntimeError('OLD_READER_QUALIFICATION_FAILED')
            return result.stdout.strip()
        def schema_version():
            with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
                return db.execute('PRAGMA user_version').fetchone()[0]
        version_before = schema_version()
        before = old_check('before')
        with fresh(path, Clock()) as runtime:
            assert runtime.identity_id == identity
            MemoryService(runtime.store, runtime.authority).forget(parent, runtime.authority)
        after = old_check('after')
        version_after = schema_version()
        assert version_after == version_before
        print(json.dumps({'scope':'SYNTHETIC_OWNED_ONLY','old_reader':'cfd11be158a3f0fa36abf93f42d5e4fde1f55bf0',
                          'old_source_tree_sha256':fingerprint.hexdigest(),'old_source_files':len(files),
                          'before':before,'after':after,'schema_version_before':version_before,
                          'schema_version_after':version_after,'network_calls':0,'model_calls':0}))


if __name__ == '__main__':
    main()
