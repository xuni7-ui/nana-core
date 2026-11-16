"""Owned loopback qualification against B's explicitly pinned prototype.

Developer-only: needs test fixtures and a separately obtained pinned B file.
No real account, network platform, model, external effect, or Core mutation.
"""
import argparse
import hashlib
import json
import resource
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.life.bilibili import BilibiliPublicTransport, BilibiliSourceAdapter
from nana_core.life.bilibili_frames import BilibiliFrameService
from nana_core.nanalink.video_handoff import storyboard_samples
from tests.living_release_v4.bilibili_loopback import counterpart
from tests.world_loop.helpers import fresh, policy

B_SHA = '86d1edb572fdeadd43cc110a174f9d83509c18ca'
B_FILE_SHA256 = '6b11af1e8ee253ef987e5cceb0284e2ba4427fa710411d930466a6f15ee201fd'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--b-planner', required=True, type=Path)
    args = parser.parse_args()
    source = args.b_planner.read_bytes()
    if hashlib.sha256(source).hexdigest() != B_FILE_SHA256:
        raise SystemExit('B_PLANNER_FINGERPRINT_MISMATCH')
    planner = ModuleType('nanalink_pinned_b_planner')
    planner.__file__ = str(args.b_planner)
    sys.modules[planner.__name__] = planner
    exec(compile(source, str(args.b_planner), 'exec'), planner.__dict__)
    with tempfile.TemporaryDirectory() as root, counterpart() as (opener, state), fresh(Path(root)/'subject.db', Clock()) as runtime:
        state['video_duration'] = 12
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9)
        transport.opener = opener
        reading = transport.read_video('BV1t55v6DE2v', visual=True)
        app = SimpleNamespace(runtime=runtime, policy=policy())
        source = BilibiliSourceAdapter(app).ingest(reading)
        BilibiliFrameService(app).capture(source, reading.frames)
        calls = transport.calls
        timings, cpu = [], time.process_time()
        for _ in range(100):
            start = time.perf_counter()
            view = storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))
            timings.append((time.perf_counter() - start)*1000)
        cpu = time.process_time() - cpu
        result = planner.plan(view['duration_seconds'], [planner.Candidate(seconds=t) for t in view['candidate_seconds']],
                              3, max_gap=4)
        assert view['bounded_sample_input_valid'] and view['cut_motion'] == 'NOT_MEASURED'
        assert result['gaps'] and not result['coverage_target_met']
        assert set(result['timestamps']) <= set(view['candidate_seconds']) and transport.calls == calls and not state['posts']
        source_refs = {sample['seconds']: sample['source_memory_id'] for sample in view['samples']}
        selected_refs = [source_refs[t] for t in result['timestamps']]
        assert len(selected_refs) == len(result['timestamps']) and all(MemoryService(runtime.store).read(mid) for mid in selected_refs)
        MemoryService(runtime.store, runtime.authority).forget(source, runtime.authority)
        try:
            storyboard_samples(app, source, scope='world', privacy_classes=('PROJECT',))
        except CoreError:
            withdrawn = True
        else:
            raise AssertionError('SOURCE_WITHDRAWAL_DID_NOT_INVALIDATE_HANDOFF')
        timings.sort()
        print(json.dumps({'scope': 'SYNTHETIC_OWNED_ONLY', 'b_planner_sha': B_SHA,
            'b_planner_file_sha256': B_FILE_SHA256, 'iterations': 100,
            'median_ms': round((timings[49]+timings[50])/2, 4), 'p95_ms': round(timings[94], 4),
            'cpu_seconds': round(cpu, 5), 'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'sample_times': view['candidate_seconds'], 'subtitle_ranges': len(view['subtitle_ranges']),
            'selected_times': result['timestamps'], 'gaps': result['gaps'], 'extra_network': transport.calls-calls,
            'model_calls': 0, 'source_mapping_verified': True, 'withdrawal_invalidates_projection': withdrawn,
            'actual_provider_tokens': 'NOT_MEASURED'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
