"""Bounded real local process/scheduler/lease/restart evidence, synthetic data."""

import json
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from ..clock import Clock
from ..actions import OperatorAuthority
from ..continuity import ContinuityStore, IdentityService
from ..continuity.memory import MemoryService
from ..continuity.subject.opportunities import ConcernCue
from .runtime import NanaRuntime
from .contracts import RuntimeConfig, RuntimeEvent, Cause, SECOND, HOUR
from ..continuity.subject import SubjectInput
from .fixtures import concern
from .cli import status


def checked_prctl(libc, option, *args):
    """Always execute the syscall, including under python -O; fail explicitly."""
    result = libc.prctl(option, *args)
    if result != 0:
        raise OSError(ctypes.get_errno(), "PROCESS_SUBREAPER_CONTROL_FAILED")


def wait_until(test, seconds=10, process=None):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if test():
            return
        if process is not None and process.poll() is not None:
            break
        time.sleep(0.02)
    raise AssertionError("bounded process checkpoint not reached")


def init(path, config):
    with ContinuityStore(path, schema_target=8) as store:
        IdentityService(store, OperatorAuthority())
        MemoryService(store).entity(config.entity_id, "PERSON")


def start(path, config_path, seconds=4):
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "nana_core.presence.cli",
            "run",
            "--db",
            str(path),
            "--config",
            str(config_path),
            "--max-seconds",
            str(seconds),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_owned(process, kill=False):
    if process.poll() is None:
        os.kill(process.pid, signal.SIGKILL if kill else signal.SIGTERM)
    out, err = process.communicate(timeout=10)
    return {"returncode": process.returncode, "stdout": out, "stderr_bytes": len(err.encode())}


def wall_soak(directory, *, sample_count=8):
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True)
    config = RuntimeConfig(
        scopes=("synthetic-wall",),
        entity_id="synthetic-person",
        lease_us=SECOND,
        heartbeat_us=100_000,
        review_interval_us=200_000,
        idle_recall_us=200_000,
        poll_seconds=0.02,
    )
    path = directory / "self.db"
    config_path = directory / "config.json"
    config_path.write_text(config.model_dump_json())
    init(path, config)
    # Seed genuine C concern + deferred queue event in this dev DB, never a host.
    with NanaRuntime(path, config) as rt:
        concern(
            rt,
            "unfinished",
            ConcernCue(
                cue_kind="OPEN_LOOP",
                motivation_source="UNRESOLVED_QUESTION",
                topic_key="pending_question",
                possible_behaviors=("EXPLORE",),
            ),
        )
        end = time.monotonic() + 3
        while not rt.subject.pending(config.scopes[0]) and time.monotonic() < end:
            rt.drain()
            time.sleep(0.03)
        if not (len(rt.subject.pending(config.scopes[0])) == 1):
            raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
        inp = SubjectInput(
            source_key="synthetic.wall.deferred",
            kind="WAKE",
            origin="SELF_WAKE",
            entity_id=config.entity_id,
            scope=config.scopes[0],
            observed_at_us=rt.clock.utc_now_us(),
        )
        deferred = rt.submit(
            RuntimeEvent(
                event_type="TIME_EVENT",
                trigger="TIME_TRIGGER",
                input=inp,
                causes=(Cause(kind="CANONICAL_SELF", reference_id=rt.store.identity["identity_id"]),),
                due_at_us=rt.clock.utc_now_us() + HOUR,
            )
        )
        identity = rt.store.identity["identity_id"]
        intentions = [x["intention_id"] for x in rt.subject.pending(config.scopes[0])]
    process = start(path, config_path, seconds=max(4, sample_count * 0.1 + 5))
    samples = []
    try:
        wait_until(
            lambda: status(path).get("process_alive") and status(path).get("lease", {}).get("pid") == process.pid,
            process=process,
        )
        epoch = status(path)["lease"]["epoch"]
        for _ in range(sample_count):
            time.sleep(0.1)
            report = status(path)
            stat = Path(f"/proc/{process.pid}/status").read_text().splitlines()
            rss = next(int(x.split()[1]) for x in stat if x.startswith("VmRSS:"))
            samples.append(
                {
                    "epoch": report["lease"]["epoch"],
                    "heartbeat_at_us": report["lease"]["heartbeat_at_us"],
                    "fd_count": len(list(Path(f"/proc/{process.pid}/fd").iterdir())),
                    "rss_kib": rss,
                    "queue": report["queue"],
                }
            )
        # A second process must be blocked, never increment authority.
        duplicate = start(path, config_path, 0.1)
        dup_out, dup_err = duplicate.communicate(timeout=5)
        if not (duplicate.returncode == 2):
            raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
        first_exit = stop_owned(process, kill=True)
        if not (first_exit["returncode"] == -signal.SIGKILL):
            raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
        restarted = start(path, config_path)
        try:
            wait_until(lambda: status(path).get("lease", {}).get("pid") == restarted.pid, process=restarted)
            restored = status(path)
            if not (restored["lease"]["epoch"] == epoch + 1):
                raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
            time.sleep(0.3)
            final_exit = stop_owned(restarted)
            if not (final_exit["returncode"] == 0):
                raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
        finally:
            if restarted.poll() is None:
                stop_owned(restarted, kill=True)
    finally:
        if process.poll() is None:
            stop_owned(process, kill=True)
    with NanaRuntime(path, config) as check:
        recovered = [x["intention_id"] for x in check.subject.pending(config.scopes[0])]
        healthy = {
            "same_identity": check.store.identity["identity_id"] == identity,
            "same_pending_intention": recovered == intentions,
            "deferred_preserved": check.store.one("runtime_queue", deferred)["state"] == "DEFERRED",
            "no_duplicate_goal": len(check.store.all("subject_goal_candidates")) == 1,
            "no_duplicate_reflection": not check.store.all("subject_reflections"),
            "zero_actions": not any(check.store.all(t) for t in ("actions", "attempts", "grants", "budgets")),
        }
    after = status(path)
    return {
        "origin": "REAL_LOCAL_PROCESS_SYNTHETIC_STORE",
        "wall_seconds": round(time.monotonic() - started, 3),
        "sample_count": len(samples),
        "samples": samples,
        "heartbeat_progressed": samples[-1]["heartbeat_at_us"] > samples[0]["heartbeat_at_us"],
        "fd_growth": samples[-1]["fd_count"] - samples[0]["fd_count"],
        "max_rss_kib": max(x["rss_kib"] for x in samples),
        "double_start_blocked": duplicate.returncode == 2,
        "sigkill_exit": first_exit["returncode"],
        "graceful_shutdown": final_exit["returncode"] == 0,
        "final_lease_state": after["lease"]["state"],
        "no_active_worker": not after["runtime_active"] and process.poll() is not None and restarted.poll() is not None,
        "checks": healthy,
        "real_external_actions": 0,
    }


CRASH_SCRIPT = r"""
import signal,sys,os
from pathlib import Path
from nana_core.presence import NanaRuntime,RuntimeConfig
config=RuntimeConfig.model_validate_json(Path(sys.argv[2]).read_text())
with NanaRuntime(sys.argv[1],config) as r:
 cut=sys.argv[4]
 def pause():
  Path(sys.argv[3]).write_text('ready')
  while True:signal.pause()
 if cut=='before_cycle':
  original=r.subject.run
  def run(*args,**kwargs):pause();return original(*args,**kwargs)
  r.subject.run=run
 elif cut=='after_cycle':
  original=r.queue.finish
  def finish(*args,**kwargs):pause();return original(*args,**kwargs)
  r.queue.finish=finish
 elif cut=='during_model':
  original=r.cognition.port
  def port(*args,**kwargs):
   resource=original(*args,**kwargs)
   heartbeat=resource.progress
   def progress():
    heartbeat()
    if resource.process_pid:Path(sys.argv[3]).write_text(str(resource.process_pid))
   resource.progress=progress
   return resource
  r.cognition.port=port
 elif cut=='after_reservation':
  original=r.cognition.port
  def port(*args,**kwargs):pause();return original(*args,**kwargs)
  r.cognition.port=port
 r.step()
"""


def crash_matrix(directory):
    reports = []
    for cut in ("before_cycle", "after_cycle", "after_reservation", "during_model"):
        root = Path(directory) / cut
        root.mkdir(mode=0o700, parents=True)
        path, conf, marker = root / "self.db", root / "config.json", root / "ready"
        config = RuntimeConfig(
            scopes=("synthetic-crash",),
            entity_id="synthetic-person",
            model="timeout" if cut == "during_model" else "analytical" if cut == "after_reservation" else None,
        )
        conf.write_text(config.model_dump_json())
        init(path, config)
        with NanaRuntime(path, config) as rt:
            mid = concern(
                rt,
                "one",
                ConcernCue(
                    cue_kind="OPEN_LOOP",
                    motivation_source="SELF_DEVELOPMENT",
                    topic_key="one",
                    possible_behaviors=("LEARN",),
                ),
            )
            inp = SubjectInput(
                source_key="synthetic.crash.one",
                kind="WAKE",
                origin="SELF_WAKE",
                entity_id=config.entity_id,
                scope=config.scopes[0],
                source_memory_ids=(mid,),
                observed_at_us=rt.clock.utc_now_us(),
                significance="HIGH",
                uncertainty="HIGH",
            )
            qid = rt.submit(
                RuntimeEvent(
                    event_type="SELF_EVENT",
                    trigger="SELF_TRIGGER",
                    input=inp,
                    causes=(Cause(kind="MEMORY", reference_id=mid),),
                    due_at_us=rt.clock.utc_now_us(),
                    priority=3,
                )
            )
            identity = rt.store.identity["identity_id"]
        libc = ctypes.CDLL(None, use_errno=True)
        old_reaper = ctypes.c_int()
        if cut == "during_model":
            checked_prctl(libc, 37, ctypes.byref(old_reaper), 0, 0, 0)
            checked_prctl(libc, 36, 1, 0, 0, 0)  # fixture adopts only its tracked orphan
        child = subprocess.Popen(
            [sys.executable, "-c", CRASH_SCRIPT, str(path), str(conf), str(marker), cut],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            wait_until(marker.exists, process=child)
            resource_pid = int(marker.read_text()) if cut == "during_model" else None
            killed = stop_owned(child, kill=True)
            if not (killed["returncode"] == -signal.SIGKILL):
                raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
            if resource_pid:
                reaped = []

                def reap():
                    pid, status = os.waitpid(resource_pid, os.WNOHANG)
                    if pid:
                        reaped.append(status)
                    return bool(pid)

                wait_until(reap, seconds=5)
                if not (os.WIFSIGNALED(reaped[0]) or os.WIFEXITED(reaped[0])):
                    raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
        finally:
            if child.poll() is None:
                stop_owned(child, kill=True)
            if cut == "during_model":
                checked_prctl(libc, 36, old_reaper.value, 0, 0, 0)
        with NanaRuntime(path, config) as restored:
            restored.drain()
            queue = restored.store.one("runtime_queue", qid)
            facts = {
                "cut": cut,
                "identity_stable": restored.store.identity["identity_id"] == identity,
                "queue_state": queue["state"],
                "cycles": len(restored.store.all("subject_cycles")),
                "intentions": len(restored.store.all("subject_intentions")),
                "candidates": len(restored.store.all("subject_goal_candidates")),
                "call_states": [x["state"] for x in restored.store.all("runtime_cognition_calls")],
                "integrity": restored.store.db.execute("PRAGMA integrity_check").fetchone()[0],
                "zero_actions": not any(restored.store.all(t) for t in ("actions", "attempts", "grants", "budgets")),
            }
            if not (
                facts["cycles"] == facts["intentions"] == facts["candidates"] == 1 and facts["queue_state"] == "DONE"
            ):
                raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
            if cut in {"after_reservation", "during_model"}:
                if not (facts["call_states"] == ["UNKNOWN"]):
                    raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
            if cut == "during_model":
                facts["resource_child_reaped"] = True
            restored.drain()
            if not (len(restored.store.all("subject_cycles")) == 1):
                raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
            reports.append(facts)
    return reports
