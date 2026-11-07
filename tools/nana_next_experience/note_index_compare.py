"""Compare one known lookup index only on the exact disposable scale corpus.

Reject other scopes/entities/privacy/namespaces before opening a writer. Never
point this at a live Subject: the experiment drops/rebuilds a physical index.
No semantic rows, permissions, sources or provider state are changed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import time

from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.store import REBUILDABLE_LOOKUP_INDEXES


def compare(root):
    root = Path(root).absolute()
    path = root / "self.db"
    if root.resolve() != root or path.resolve() != path or not list(root.glob("result-*.json")):
        raise ValueError("EXACT_DISPOSABLE_SCALE_CORPUS_REQUIRED")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as read:
        count = read.execute("SELECT count(*) FROM memories").fetchone()[0]
        bad = read.execute(
            "SELECT 1 FROM memories WHERE scope!='bench' OR entity_id NOT IN ('bench','other') OR privacy_class!='PROJECT' LIMIT 1"
        ).fetchone()
        other = read.execute(
            "SELECT 1 FROM continuity_evidence WHERE source_namespace NOT IN ('synthetic.scale','recorded.conversation.input') OR (source_namespace='recorded.conversation.input' AND source_reference NOT LIKE 'note:synthetic-scale-%') LIMIT 1"
        ).fetchone()
        if not 1000 <= count <= 500000 or bad or other:
            raise ValueError("EXACT_DISPOSABLE_SCALE_CORPUS_REQUIRED")
    ddl = REBUILDABLE_LOOKUP_INDEXES["memory_user_note_lookup"]
    timings = {"without_note_index": [], "with_note_index": []}
    results = {k: {"correct": 0, "wrong": 0, "timeout": 0} for k in timings}
    builds = []
    with ContinuityStore(path, ManualClock(), schema_target=13) as store:
        db = store.db
        wanted = db.execute(
            "SELECT memory_id FROM memories WHERE entity_id='bench' AND predicate_key='user-note.synthetic-scale'"
        ).fetchone()[0]
        query = dict(entity_ids=("bench",), scopes=("bench",), privacy_classes=("PROJECT",), terms=("虹光约定",))
        memory = MemoryService(store)
        from nana_core.contracts import CoreError

        try:
            for n in range(9):
                order = tuple(timings) if n % 2 == 0 else tuple(reversed(timings))
                for arm in order:
                    shape = db.execute("SELECT sql FROM sqlite_master WHERE name='memory_user_note_lookup'").fetchone()
                    if shape and shape[0] != ddl:
                        raise ValueError("INDEX_SUBSTITUTION_REFUSED")
                    if arm == "without_note_index":
                        db.execute("DROP INDEX IF EXISTS memory_user_note_lookup")
                    elif not shape:
                        started = time.perf_counter()
                        db.execute(ddl)
                        builds.append((time.perf_counter() - started) * 1000)
                    started = time.perf_counter()
                    try:
                        ids = [m["memory_id"] for m in memory.literal_notes(**query)]
                    except CoreError as exc:
                        if exc.code != "NOTE_RECALL_TIME_BOUND":
                            raise
                        results[arm]["timeout"] += 1
                        ids = []
                    timings[arm].append((time.perf_counter() - started) * 1000)
                    results[arm]["correct"] += ids == [wanted]
                    results[arm]["wrong"] += bool(ids and ids != [wanted])
        finally:
            db.execute(ddl.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1))
    # Cold SQLite connection only; this does not claim an OS-cache cold boot.
    opened = time.perf_counter()
    with ContinuityStore(path, ManualClock(), schema_target=13) as store:
        open_ms = (time.perf_counter() - opened) * 1000
        started = time.perf_counter()
        ids = [m["memory_id"] for m in MemoryService(store).literal_notes(**query)]
        cold_ms = (time.perf_counter() - started) * 1000
        cold_correct = ids == [wanted]
    return {
        "scope": "OWNED_SYNTHETIC_ORIGINAL_STORE_ONLY",
        "memory_rows": count,
        "distinct_query_fixtures": 1,
        "timing_repetitions_per_arm": 9,
        "arms": {k: {**results[k], "p50_ms": statistics.median(v), "p95_ms": max(v)} for k, v in timings.items()},
        "index_build_p50_ms": statistics.median(builds) if builds else None,
        "fresh_connection_open_ms": open_ms,
        "fresh_connection_first_lookup_ms": cold_ms,
        "fresh_connection_correct": cold_correct,
        "os_cache_cold": False,
        "semantic_or_live_qualification": "NOT_RUN",
        "provider_calls": 0,
        "runtime_source_sha256": hashlib.sha256(
            Path(__import__(MemoryService.__module__, fromlist=["x"]).__file__).read_bytes()
        ).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.root), indent=2))
