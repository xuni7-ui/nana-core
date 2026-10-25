"""Small same-interpreter host-cost comparison on a fresh synthetic Store."""

import argparse
import json
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time


def measure(source, root):
    source = Path(source).resolve()
    root = Path(root).absolute()
    if root.exists():
        raise ValueError("FRESH_MEASUREMENT_ROOT_REQUIRED")
    root.mkdir(mode=0o700, parents=True)
    sys.path.insert(0, str(source / "src"))
    import sqlite3
    import nana_core
    from nana_core.continuity import ContinuityStore
    from nana_core.continuity.open_agency.code_skills import IsolatedSkillRunner

    if not Path(nana_core.__file__).resolve().is_relative_to(source / "src"):
        raise ValueError("SOURCE_IMPORT_MISMATCH")
    path = root / "state/self.db"
    with ContinuityStore(path, schema_target=13):
        pass
    samples = []
    cpu = time.process_time()
    started = time.monotonic()
    for _ in range(15):
        begin = time.perf_counter()
        with ContinuityStore(path, schema_target=13):
            pass
        samples.append((time.perf_counter() - begin) * 1000)
    store_wall = time.monotonic() - started
    store_cpu = time.process_time() - cpu
    with ContinuityStore(path, schema_target=13) as store:
        started = time.perf_counter()
        for _ in range(1000):
            store.ensure_privacy_current()
        privacy_ms = (time.perf_counter() - started) * 1000
    sandbox = []
    runner = IsolatedSkillRunner()
    for _ in range(7):
        start = time.perf_counter()
        value = runner.run("def transform(data):\n return sum(data)\n", [1.25, 2.5])
        if value != 3.75:
            raise RuntimeError("INDEPENDENT_SANDBOX_OUTPUT_MISMATCH")
        sandbox.append((time.perf_counter() - start) * 1000)
    probe_ms = None
    if hasattr(runner, "qualify"):
        start = time.perf_counter()
        probe = runner.qualify()
        probe_ms = (time.perf_counter() - start) * 1000
        if probe["state"] != "AVAILABLE":
            raise RuntimeError("PROBE_UNAVAILABLE")
    return {
        "source": str(source),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip(),
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "scope": "FRESH_SYNTHETIC_HOST_COST_NOT_FULL_LIFE_SPEEDUP",
        "store_reopen_samples": 15,
        "store_reopen_median_ms": statistics.median(samples),
        "store_wall_seconds": store_wall,
        "store_cpu_seconds": store_cpu,
        "privacy_1000_checks_ms": privacy_ms,
        "sandbox_calls": 7,
        "sandbox_median_ms": statistics.median(sandbox),
        "optional_qualification_ms": probe_ms,
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "new_provider_calls": 0,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    value = measure(a.source, a.root)
    a.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value))
