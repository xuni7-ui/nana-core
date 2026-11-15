"""Owned loopback qualification against B's explicitly pinned prototype.

Developer-only: needs test fixtures and a separately obtained pinned B file.
No real account, network platform, model, external effect, or Core mutation.
"""
import argparse
import hashlib
import importlib.util
import json
import resource
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from nana_core.clock import Clock
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
    if hashlib.sha256(args.b_planner.read_bytes()).hexdigest() != B_FILE_SHA256:
        raise SystemExit('B_PLANNER_FINGERPRINT_MISMATCH')
    spec = importlib.util.spec_from_file_location('nanalink_pinned_b_planner', args.b_planner)
    planner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = planner
    spec.loader.exec_module(planner)
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
        timings.sort()
        print(json.dumps({'scope': 'SYNTHETIC_OWNED_ONLY', 'b_planner_sha': B_SHA,
            'b_planner_file_sha256': B_FILE_SHA256, 'iterations': 100,
            'median_ms': round((timings[49]+timings[50])/2, 4), 'p95_ms': round(timings[94], 4),
            'cpu_seconds': round(cpu, 5), 'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'sample_times': view['candidate_seconds'], 'subtitle_ranges': len(view['subtitle_ranges']),
            'selected_times': result['timestamps'], 'gaps': result['gaps'], 'extra_network': transport.calls-calls,
            'model_calls': 0, 'actual_provider_tokens': 'NOT_MEASURED'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
