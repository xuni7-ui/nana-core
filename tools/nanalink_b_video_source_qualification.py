"""Owned synthetic source-gate check against B's explicitly pinned video decoder.

Developer-only: accepts an archived B checkout, verifies both Python files before
execution, and uses a temporary Store and generated video. No platform access.
"""
import argparse
import hashlib
import json
import resource
import statistics
import time
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace

from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.perception import PerceptionService, PublicMediaSource
from nana_core.nanalink.media import MediaCache
from nana_core.nanalink.video_handoff import public_video_cache_handle, with_current_public_video
from tests.world_loop.helpers import fresh, policy, providers

B_COMMIT = 'bbc3ba7325bf0c30b7966e5e24f21ed34c321c7c'
FILES = (
    ('video_pts_decode', 'd71acdf436c5fda86e37fcb519dd9d4a26ee88dbf58e6194ace49d67c77bf718'),
    ('video_nanalink_cache', '7aa9e0e590ec16fe2756b32eada54cc195598f14d5a99afe4afc13aec0c9e23b'),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--b-source', type=Path, required=True)
    args = parser.parse_args()
    modules = {}
    # Read and verify both complete inputs before executing either of them.
    verified = []
    for name, expected in FILES:
        path = args.b_source / 'tools/nana_next_experience/experiments' / (name + '.py')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('B_SOURCE_FINGERPRINT_MISMATCH')
        verified.append((name, path, data))
    for name, path, data in verified:
        key = 'tools.nana_next_experience.experiments.' + name
        module = ModuleType(key)
        module.__file__ = str(path)
        sys.modules[key] = module
        exec(compile(data, str(path), 'exec'), module.__dict__)
        modules[name] = module
    adapter = modules['video_nanalink_cache']
    with tempfile.TemporaryDirectory(prefix='nanalink-b-source-') as root:
        root = Path(root)
        video = root / 'synthetic.mp4'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
            'testsrc2=s=32x32:r=4:d=2', '-c:v', 'mpeg4', '-threads', '1', '-y', str(video)],
            check=True, timeout=20)
        data = video.read_bytes()
        with fresh(root/'subject.db') as runtime:
            app = SimpleNamespace(runtime=runtime, policy=policy())
            now = runtime.clock.utc_now_us()
            source = PublicMediaSource(source_id='synthetic-video', modality='VIDEO', origin='SYNTHETIC',
                                       event_time_us=now, observed_time_us=now)
            mid, _ = PerceptionService(runtime.store, providers(), app.policy).ingest(
                data, source, entity_id='observer', scope='world')
            cache = MediaCache(root/'cache', source_current=lambda _: True,
                               max_bytes=16*1024*1024, item_bytes=16*1024*1024)
            try:
                cache.put([data], source_ref=mid, media_type='video/mp4')
                timings = []
                cpu_start = time.process_time()
                for _ in range(100):
                    started = time.perf_counter_ns()
                    handle = public_video_cache_handle(app, cache, mid, scope='world')
                    timings.append((time.perf_counter_ns() - started) / 1_000_000)
                gate_cpu = time.process_time() - cpu_start
                timings.sort()
                first = with_current_public_video(app, cache, mid, scope='world',
                    operation=lambda selected: adapter.decode_cached_window(cache, selected, privacy='PUBLIC',
                        start_seconds=.5, end_seconds=1.5, width=32, height=32))
                assert first.source_ref == mid and first.source_sha256 == hashlib.sha256(data).hexdigest()
                assert first.decoded.timestamps == (.5, .75, 1., 1.25)
                # Original Store source, not the cache callback, is authoritative.
                original = adapter.decode
                def revoke_during_decode(*decode_args, **decode_kwargs):
                    result = original(*decode_args, **decode_kwargs)
                    MemoryService(runtime.store, runtime.authority).forget(mid, runtime.authority)
                    return result
                adapter.decode = revoke_during_decode
                try:
                    with_current_public_video(app, cache, mid, scope='world',
                        operation=lambda selected: adapter.decode_cached_window(cache, selected, privacy='PUBLIC',
                            start_seconds=.5, end_seconds=1.5, width=32, height=32))
                except CoreError:
                    pass
                else:
                    raise AssertionError('WITHDRAWN_SOURCE_PASSED_HANDOFF')
            finally:
                cache.close()
        print(json.dumps({'scope':'SYNTHETIC_OWNED_ONLY', 'b_commit':B_COMMIT,
                          'source_sha256_verified':True, 'original_store_and_perception':True,
                          'selected_window_pts':[.5,.75,1.,1.25], 'revoked_candidate_delivered':False,
                          'cache_callback_deliberately_non_authoritative':True,
                          'gate_iterations':100, 'gate_median_ms':round(statistics.median(timings),4),
                          'gate_p95_ms':round(timings[94],4), 'gate_cpu_seconds':round(gate_cpu,5),
                          'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          'provider':'LOCAL_TECHNICAL_PROCESSOR_ONLY', 'platform_network':0, 'external_send':0}))


if __name__ == '__main__':
    main()
